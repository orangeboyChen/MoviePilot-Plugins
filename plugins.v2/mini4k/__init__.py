# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

from app.core.config import settings
from app.core.context import TorrentInfo
from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import MediaType

from .agenttool import LoginMini4kTool, SearchMini4kTool
from .client import Mini4kClient
from .ui import build_form, build_page


class Mini4k(_PluginBase):
    """Mini4k indexer plugin for MoviePilot V2."""

    plugin_name = "Mini4k"
    plugin_desc = "搜索 Mini4k 电影资源并下载种子。"
    plugin_icon = "Mini4k.png"
    plugin_version = "1.0.0"
    plugin_author = "orangeboy"
    author_url = ""
    plugin_config_prefix = "mini4k_"
    plugin_order = 15
    auth_level = 2

    INDEXER_ID = "Mini4k"
    INDEXER_DOMAIN = "mini4k_indexer.orangeboy"
    DATA_COOKIE = "cookies"
    DATA_STATUS = "status"
    DEFAULT_UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )

    _enabled: bool = False
    _username: str = ""
    _password: str = ""
    _base_url: str = "https://mini4k.io"
    _timeout: int = 20
    _use_proxy: bool = False
    _auto_relogin: bool = True
    _result_limit: int = 10
    _ua: str = DEFAULT_UA
    _cookie: str = ""
    _last_login_at: str = ""
    _last_login_ok: bool = False
    _last_error: str = ""
    _sites_helper: Optional[SitesHelper] = None

    def init_plugin(self, config: dict = None):
        logger.info(f"【{self.plugin_name}】开始初始化插件")
        config = config or {}
        self._load_config(config)
        self._load_saved_state()
        self._sites_helper = SitesHelper()

        if config.get("onlyonce"):
            try:
                ok, message = self.login()
                logger.info(f"【{self.plugin_name}】立即运行登录结果：{message}")
            finally:
                self.update_config({**config, "onlyonce": False})

        if not self._enabled:
            logger.info(f"【{self.plugin_name}】插件未启用")
            return

        self._register_indexer()
        logger.info(f"【{self.plugin_name}】初始化完成")

    def _load_config(self, config: Dict[str, Any]):
        self._enabled = bool(config.get("enabled", False))
        self._username = (config.get("username") or "").strip()
        self._password = config.get("password") or ""
        self._base_url = (config.get("base_url") or "https://mini4k.io").strip().rstrip("/")
        self._use_proxy = bool(config.get("use_proxy", False))
        self._auto_relogin = bool(config.get("auto_relogin", True))
        self._ua = config.get("ua") or self.DEFAULT_UA
        self._timeout = self._as_int(config.get("timeout"), 20, minimum=5)
        self._result_limit = self._as_int(config.get("result_limit"), 10, minimum=1)

    @staticmethod
    def _as_int(value: Any, default: int, minimum: int) -> int:
        try:
            return max(minimum, int(value or default))
        except (TypeError, ValueError):
            return default

    def _load_saved_state(self):
        self._cookie = self.get_data(self.DATA_COOKIE) or ""
        status = self.get_data(self.DATA_STATUS) or {}
        if isinstance(status, dict):
            self._last_login_at = status.get("last_login_at") or ""
            self._last_login_ok = bool(status.get("last_login_ok", False))
            self._last_error = status.get("last_error") or ""

    def _save_status(self, ok: bool, error: str = ""):
        self._last_login_ok = ok
        self._last_error = error or ""
        if ok:
            self._last_login_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_data(self.DATA_STATUS, {
            "last_login_at": self._last_login_at,
            "last_login_ok": self._last_login_ok,
            "last_error": self._last_error,
        })

    def _save_cookie(self, cookie: str):
        self._cookie = cookie or ""
        self.save_data(self.DATA_COOKIE, self._cookie)
        if self._enabled:
            self._register_indexer()

    def _client(self) -> Mini4kClient:
        return Mini4kClient(
            base_url=self._base_url,
            username=self._username,
            password=self._password,
            cookie=self._cookie,
            timeout=self._timeout,
            use_proxy=self._use_proxy,
            auto_relogin=self._auto_relogin,
            ua=self._ua,
            on_cookie=self._save_cookie,
            on_status=self._save_status,
        )

    def _build_indexer(self) -> Dict[str, Any]:
        return {
            "id": self.INDEXER_ID,
            "name": self.plugin_name,
            "url": f"{self._base_url}/",
            "domain": self.INDEXER_DOMAIN,
            "encoding": "UTF-8",
            "public": False,
            "proxy": self._use_proxy,
            "timeout": self._timeout,
            "cookie": self._cookie,
            "ua": self._ua or self.DEFAULT_UA,
            "search": {
                "paths": [{"path": "search?text={keyword}", "method": "get", "type": "movie"}]
            },
            "torrents": {
                "list": {"selector": "ul.metadata-list > li.item"},
                "fields": {},
            },
        }

    def _register_indexer(self):
        if not self._sites_helper:
            self._sites_helper = SitesHelper()
        indexer = self._build_indexer()
        self._sites_helper.add_indexer(indexer["domain"], indexer)
        logger.info(f"【{self.plugin_name}】已注册索引器：{indexer['domain']}")

    def _is_our_site(self, site: Dict[str, Any]) -> bool:
        if not isinstance(site, dict):
            return False
        domain = self._clean_domain(site.get("domain"))
        return (
            site.get("id") == self.INDEXER_ID
            or site.get("name") == self.plugin_name
            or domain == self.INDEXER_DOMAIN
        )

    @staticmethod
    def _clean_domain(domain: Any) -> str:
        return str(domain or "").replace("http://", "").replace("https://", "").rstrip("/")

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_module(self) -> Dict[str, Any]:
        if not self._enabled:
            return {}
        return {
            "search_torrents": self.search_torrents,
            "async_search_torrents": self.async_search_torrents,
            "refresh_torrents": self.refresh_torrents,
            "async_refresh_torrents": self.async_refresh_torrents,
        }

    def get_agent_tools(self) -> List[Type]:
        return [SearchMini4kTool, LoginMini4kTool]

    def stop_service(self):
        pass

    def login(self) -> Tuple[bool, str]:
        return self._client().login()

    def search_torrents(
        self,
        site: Dict[str, Any] = None,
        keyword: str = None,
        mtype: Optional[MediaType] = None,
        page: Optional[int] = 0,
    ) -> List[TorrentInfo]:
        if not self._enabled or not keyword:
            return []
        if site and not self._is_our_site(site):
            return []
        if mtype and mtype != MediaType.MOVIE:
            return []

        logger.info(f"【{self.plugin_name}】开始搜索：{keyword}")
        client = self._client()
        results: List[TorrentInfo] = []
        for movie in client.search_movies(keyword, page=page or 0)[:self._result_limit]:
            for torrent in client.parse_movie(movie.get("page_url")):
                torrent.site = site.get("id") if isinstance(site, dict) else self.INDEXER_ID
                torrent.site_name = site.get("name") if isinstance(site, dict) else self.plugin_name
                torrent.site_cookie = self._cookie
                torrent.site_ua = self._ua or self.DEFAULT_UA
                torrent.site_proxy = self._use_proxy
                torrent.category = MediaType.MOVIE.value
                results.append(torrent)
        logger.info(f"【{self.plugin_name}】搜索完成：{keyword}，返回 {len(results)} 个资源")
        return results

    async def async_search_torrents(
        self,
        site: Dict[str, Any] = None,
        keyword: str = None,
        mtype: Optional[MediaType] = None,
        page: Optional[int] = 0,
    ) -> List[TorrentInfo]:
        return self.search_torrents(site=site, keyword=keyword, mtype=mtype, page=page)

    def refresh_torrents(
        self,
        site: Dict[str, Any] = None,
        keyword: Optional[str] = None,
        cat: Optional[str] = None,
        page: Optional[int] = 0,
    ) -> List[TorrentInfo]:
        return []

    async def async_refresh_torrents(
        self,
        site: Dict[str, Any] = None,
        keyword: Optional[str] = None,
        cat: Optional[str] = None,
        page: Optional[int] = 0,
    ) -> List[TorrentInfo]:
        return self.refresh_torrents(site=site, keyword=keyword, cat=cat, page=page)

    def api_login(self) -> Dict[str, Any]:
        ok, message = self.login()
        return {"success": ok, "message": message, "last_login_at": self._last_login_at}

    def api_indexers(self) -> List[Dict[str, Any]]:
        return [self._build_indexer()] if self._enabled else []

    def api_search(self, keyword: str, expand: bool = False, page: int = 0) -> List[Dict[str, Any]]:
        if not keyword:
            return []
        client = self._client()
        if expand:
            return [torrent.to_dict() for torrent in self.search_torrents(keyword=keyword, page=page)]
        return client.search_movies(keyword, page=page)

    def api_movie(self, url: str) -> List[Dict[str, Any]]:
        return [torrent.to_dict() for torrent in self._client().parse_movie(url)]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/login",
                "endpoint": self.api_login,
                "methods": ["POST", "GET"],
                "auth": "bear",
                "summary": "登录 Mini4k",
                "description": "使用插件配置的用户名密码登录 Mini4k 并刷新 Cookie。",
            },
            {
                "path": "/indexers",
                "endpoint": self.api_indexers,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取 Mini4k 索引器",
                "description": "返回 Mini4k 注册到 MoviePilot 的索引器配置。",
            },
            {
                "path": "/search",
                "endpoint": self.api_search,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "搜索 Mini4k",
                "description": "搜索 Mini4k 电影；expand=true 时展开电影详情中的资源。",
            },
            {
                "path": "/movie",
                "endpoint": self.api_movie,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "解析 Mini4k 电影资源",
                "description": "解析指定 Mini4k 电影详情页中的种子和磁力资源。",
            },
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return build_form(self.DEFAULT_UA)

    def get_page(self) -> List[dict]:
        return build_page(
            enabled=self._enabled,
            login_ok=self._last_login_ok,
            has_cookie=bool(self._cookie),
            last_login_at=self._last_login_at,
            last_error=self._last_error,
            base_url=self._base_url,
            indexer_domain=self.INDEXER_DOMAIN,
            use_proxy=self._use_proxy,
        )
