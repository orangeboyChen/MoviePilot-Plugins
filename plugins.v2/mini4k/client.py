# -*- coding: utf-8 -*-
import html
import re
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests
from pyquery import PyQuery

from app.core.config import settings
from app.core.context import TorrentInfo
from app.log import logger
from app.schemas.types import MediaType
from app.utils.string import StringUtils


class Mini4kClient:
    """HTTP client and parser for mini4k.io."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        cookie: str,
        timeout: int,
        use_proxy: bool,
        auto_relogin: bool,
        ua: str,
        on_cookie: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[bool, str], None]] = None,
    ):
        self.base_url = (base_url or "https://mini4k.io").strip().rstrip("/")
        self.username = (username or "").strip()
        self.password = password or ""
        self.cookie = cookie or ""
        self.timeout = max(5, int(timeout or 20))
        self.use_proxy = bool(use_proxy)
        self.auto_relogin = bool(auto_relogin)
        self.ua = ua or settings.USER_AGENT
        self.on_cookie = on_cookie
        self.on_status = on_status

    def absolute_url(self, url: str) -> str:
        return urljoin(f"{self.base_url}/", url or "")

    @staticmethod
    def cookie_dict_to_header(cookie_dict: Dict[str, str]) -> str:
        return "; ".join(f"{key}={value}" for key, value in cookie_dict.items() if key and value)

    def _new_session(self, cookie: Optional[str] = None) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        if cookie:
            session.headers.update({"Cookie": cookie})
        return session

    def _request_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            "timeout": self.timeout,
            "allow_redirects": True,
        }
        if self.use_proxy and settings.PROXY:
            kwargs["proxies"] = settings.PROXY
        return kwargs

    def login(self) -> Tuple[bool, str]:
        if not self.username or not self.password:
            return self._status(False, "未配置 Mini4k 用户名或密码")

        try:
            session = self._new_session()
            login_url = self.absolute_url("/user/login")
            logger.info("【Mini4k】开始登录 Mini4k")
            login_page = session.get(login_url, **self._request_kwargs())
            if not login_page:
                return self._status(False, "无法访问登录页")

            doc = PyQuery(login_page.text)
            form = doc("form#user-login-form")
            if not form:
                form = doc('form[action*="/user/login"]').eq(0)

            payload = {}
            for item in form("input[name]").items():
                name = item.attr("name")
                value = item.attr("value") or ""
                if name:
                    payload[name] = value
            payload.update({
                "name": self.username,
                "pass": self.password,
                "form_id": payload.get("form_id") or "user_login_form",
                "op": payload.get("op") or "登录",
            })

            post_url = self.absolute_url(form.attr("action") or "/user/login")
            response = session.post(post_url, data=payload, **self._request_kwargs())
            text = response.text if response is not None else ""
            if response is not None and self.is_logged_in(text, response.url):
                cookie = self.cookie_dict_to_header(requests.utils.dict_from_cookiejar(session.cookies))
                self.cookie = cookie
                if self.on_cookie:
                    self.on_cookie(cookie)
                return self._status(True, "")

            message = self.extract_login_error(text) or "登录失败，请检查用户名、密码或站点防护"
            return self._status(False, message)
        except Exception as err:
            logger.error(f"【Mini4k】登录异常：{err}\n{traceback.format_exc()}")
            return self._status(False, f"登录异常：{err}")

    def _status(self, ok: bool, message: str) -> Tuple[bool, str]:
        if self.on_status:
            self.on_status(ok, message)
        return ok, message or ("登录成功" if ok else "登录失败")

    @staticmethod
    def extract_login_error(text: str) -> str:
        if not text:
            return ""
        doc = PyQuery(text)
        for selector in (".messages--error", ".messages.error", "[role='alert']"):
            msg = doc(selector).text()
            if msg:
                return " ".join(msg.split())
        return ""

    @staticmethod
    def is_logged_in(text: str, final_url: str = "") -> bool:
        if not text:
            return False
        if "/user/login" in (final_url or "") and "user_login_form" in text:
            return False
        return (
            "user-logged-in" in text
            or "/user/logout" in text
            or "我的帐户" in text
            or "我的账户" in text
        )

    @staticmethod
    def needs_login(response: requests.Response) -> bool:
        if response is None:
            return False
        if response.status_code in (401, 403):
            return True
        text = response.text or ""
        url = response.url or ""
        if "/user/login" in url and "user_login_form" in text:
            return True
        return "user_login_form" in text or ('name="pass"' in text and 'name="name"' in text)

    def get_with_auth(self, path_or_url: str, retry: bool = True) -> Optional[requests.Response]:
        url = path_or_url if str(path_or_url).startswith("http") else self.absolute_url(path_or_url)
        response = self._new_session(self.cookie).get(url, **self._request_kwargs())
        if response is not None and self.needs_login(response) and retry and self.auto_relogin:
            logger.info("【Mini4k】Cookie 失效，尝试自动重新登录")
            ok, message = self.login()
            if not ok:
                logger.warning(f"【Mini4k】自动重新登录失败：{message}")
                return response
            response = self._new_session(self.cookie).get(url, **self._request_kwargs())
        return response

    def search_movies(self, keyword: str, page: int = 0) -> List[Dict[str, Any]]:
        try:
            page = max(0, int(page or 0))
        except (TypeError, ValueError):
            page = 0
        response = self.get_with_auth(f"/search?page={page}&text={quote(keyword)}")
        if response is None or response.status_code >= 400:
            logger.warning(f"【Mini4k】搜索请求失败：{getattr(response, 'status_code', None)}")
            return []

        doc = PyQuery(response.text)
        movies = []
        for item in doc("ul.metadata-list > li.item").items():
            link = item(".head a[href^='/movies/']").attr("href") or item(".poster a[href^='/movies/']").attr("href")
            if not link:
                continue
            meta_nodes = item(".detail .info > .meta")
            poster = item(".poster img").attr("src") or ""
            movies.append({
                "title": item(".header").eq(0).text().strip(),
                "original_title": meta_nodes.eq(0).text().strip() if meta_nodes else "",
                "year": item(".meta-item.year").eq(0).text().strip(),
                "duration": item(".meta-item.duration").eq(0).text().strip(),
                "rating": item(".rating-star").text().replace("\n", " ").strip(),
                "poster": self.absolute_url(poster),
                "page_url": self.absolute_url(link),
            })
        return movies

    def parse_movie(self, movie_url: str) -> List[TorrentInfo]:
        if not movie_url:
            return []
        response = self.get_with_auth(movie_url)
        if response is None or response.status_code >= 400:
            logger.warning(f"【Mini4k】详情请求失败：{movie_url}")
            return []

        doc = PyQuery(response.text)
        movie_title = doc(".ch-title").eq(0).text().strip()
        movie_year = doc(".node-year").eq(0).text().strip("() ")
        imdbid = self.extract_imdbid(doc("a.imdb-link").attr("href") or "")

        torrents: List[TorrentInfo] = []
        for section in doc(".reference-torrent .views-element-container").items():
            quality = section("h3.block-title").eq(0).text().strip()
            for row in section("tbody tr").items():
                torrent = self._parse_resource_row(row, movie_title, movie_year, quality, imdbid, movie_url)
                if torrent:
                    torrents.append(torrent)
        return torrents

    def _parse_resource_row(
        self,
        row: PyQuery,
        movie_title: str,
        movie_year: str,
        quality: str,
        imdbid: str,
        movie_url: str
    ) -> Optional[TorrentInfo]:
        title_link = row("td.views-field-title a").eq(0)
        title = (title_link.attr("title") or title_link.text() or "").strip()
        if not title:
            return None

        download_url = row('a[download][href]').eq(0).attr("href") or ""
        magnet_url = (
            row(".magnet-link").eq(0).attr("data-link")
            or row(".copy-link").eq(0).attr("data-clipboard-text")
            or ""
        )
        enclosure = self.clean_link(download_url or magnet_url)
        if not enclosure:
            return None
        if not enclosure.startswith("magnet:"):
            enclosure = self.absolute_url(enclosure)

        size_text = row("td").eq(2).text().strip()
        date_elapsed = row("td").eq(3).text().strip()
        page_url = title_link.attr("href") or movie_url
        description_parts = [part for part in [movie_title, movie_year, quality] if part]

        return TorrentInfo(
            title=title,
            description=" ".join(description_parts),
            enclosure=enclosure,
            page_url=self.absolute_url(page_url),
            size=StringUtils.num_filesize(size_text) if size_text else 0,
            date_elapsed=date_elapsed,
            imdbid=imdbid,
            site_name="Mini4k",
            site_cookie=self.cookie,
            site_ua=self.ua,
            site_proxy=self.use_proxy,
            downloadvolumefactor=1.0,
            uploadvolumefactor=1.0,
            category=MediaType.MOVIE.value,
        )

    @staticmethod
    def clean_link(value: str) -> str:
        if not value:
            return ""
        old = value
        for _ in range(5):
            new = html.unescape(old)
            if new == old:
                break
            old = new
        return old.strip()

    @staticmethod
    def extract_imdbid(value: str) -> str:
        match = re.search(r"tt\d+", value or "")
        return match.group(0) if match else ""
