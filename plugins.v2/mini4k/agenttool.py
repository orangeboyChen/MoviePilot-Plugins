# -*- coding: utf-8 -*-
from typing import Optional, Type

from pydantic import BaseModel

from app.agent.tools.base import MoviePilotTool
from app.core.plugin import PluginManager

from .schemas import LoginMini4kToolInput, SearchMini4kToolInput


def _plugin_instance():
    return PluginManager().running_plugins.get("Mini4k")


class SearchMini4kTool(MoviePilotTool):
    """Search Mini4k torrent resources."""

    name: str = "mini4k_search_torrents"
    description: str = (
        "Search Mini4k movie torrent resources. Use this when the user asks to find "
        "Mini4k movie downloads, torrent files, or magnet links. The tool searches "
        "Mini4k search pages and expands movie detail pages into real torrent resources."
    )
    args_schema: Type[BaseModel] = SearchMini4kToolInput

    def get_tool_message(self, **kwargs) -> Optional[str]:
        keyword = kwargs.get("keyword", "")
        page = kwargs.get("page", 0)
        return f"正在搜索 Mini4k：{keyword}（第 {int(page or 0) + 1} 页）"

    async def run(
        self,
        keyword: str,
        page: Optional[int] = 0,
        limit: Optional[int] = 5,
        **kwargs,
    ) -> str:
        plugin = _plugin_instance()
        if not plugin:
            return "Mini4k 插件未运行"
        if not getattr(plugin, "_enabled", False):
            return "Mini4k 插件未启用"

        try:
            page = max(0, int(page or 0))
        except (TypeError, ValueError):
            page = 0
        try:
            limit = max(1, min(20, int(limit or 5)))
        except (TypeError, ValueError):
            limit = 5

        try:
            results = plugin.api_search(keyword=keyword, expand=True, page=page)
        except Exception as err:
            return f"Mini4k 搜索失败：{err}"

        if not results:
            return f"Mini4k 未找到资源：{keyword}（page={page}）"

        lines = [f"Mini4k 找到 {len(results)} 个资源，显示前 {min(len(results), limit)} 个："]
        for index, torrent in enumerate(results[:limit], 1):
            size = _format_size(torrent.get("size") or 0)
            title = torrent.get("title") or "-"
            published = torrent.get("date_elapsed") or "-"
            page_url = torrent.get("page_url") or ""
            enclosure = torrent.get("enclosure") or ""
            link_type = "magnet" if str(enclosure).startswith("magnet:") else "torrent"
            lines.append(f"{index}. {title}")
            lines.append(f"   大小：{size} | 发布：{published} | 类型：{link_type}")
            if page_url:
                lines.append(f"   页面：{page_url}")

        return "\n".join(lines)


class LoginMini4kTool(MoviePilotTool):
    """Refresh Mini4k login cookie."""

    name: str = "mini4k_login"
    description: str = (
        "Login to Mini4k with the username and password configured in the Mini4k plugin "
        "and refresh the saved cookie. Use this when Mini4k cookie is expired or the user "
        "asks to test Mini4k login."
    )
    args_schema: Type[BaseModel] = LoginMini4kToolInput

    def get_tool_message(self, **kwargs) -> Optional[str]:
        return "正在登录 Mini4k 并刷新 Cookie"

    async def run(self, **kwargs) -> str:
        plugin = _plugin_instance()
        if not plugin:
            return "Mini4k 插件未运行"

        try:
            ok, message = plugin.login()
        except Exception as err:
            return f"Mini4k 登录失败：{err}"

        if ok:
            last_login_at = getattr(plugin, "_last_login_at", "") or "-"
            return f"Mini4k 登录成功，Cookie 已刷新。最近登录：{last_login_at}"
        return f"Mini4k 登录失败：{message}"


def _format_size(size: int) -> str:
    try:
        value = float(size or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    return f"{value:.2f}{units[index]}"
