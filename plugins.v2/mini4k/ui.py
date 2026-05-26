# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Tuple


def build_form(default_ua: str) -> Tuple[List[dict], Dict[str, Any]]:
    return [
        {
            "component": "VForm",
            "content": [
                {
                    "component": "VRow",
                    "content": [
                        _col(6, _switch("enabled", "启用插件", "开启后注册 Mini4k 索引器并接管搜索")),
                        _col(6, _switch("onlyonce", "立即运行一次", "保存后立即登录 Mini4k 并刷新 Cookie")),
                    ],
                },
                {
                    "component": "VRow",
                    "content": [
                        _col(6, _text("username", "用户名", "Mini4k 用户名")),
                        _col(6, _text("password", "密码", "Mini4k 密码", field_type="password")),
                    ],
                },
                {
                    "component": "VRow",
                    "content": [
                        _col(6, _text("base_url", "站点地址", "https://mini4k.io", "默认 https://mini4k.io")),
                        _col(3, _text("timeout", "超时秒数", field_type="number")),
                        _col(3, _text("result_limit", "展开电影数", field_type="number",
                                      hint="每次搜索最多展开多少个电影详情")),
                    ],
                },
                {
                    "component": "VRow",
                    "content": [
                        _col(6, _switch("use_proxy", "使用代理")),
                        _col(6, _switch("auto_relogin", "Cookie失效自动重登")),
                    ],
                },
                {
                    "component": "VRow",
                    "content": [
                        _col(12, _text("ua", "User-Agent", default_ua, "登录、搜索和下载种子时使用的浏览器 UA")),
                    ],
                },
                {
                    "component": "VAlert",
                    "props": {
                        "type": "info",
                        "variant": "tonal",
                        "border": "start",
                        "text": "保存配置并开启「立即运行一次」后，插件会登录 Mini4k、保存 Cookie，并注册 Mini4k 索引器。系统搜索该站点时会自动展开电影详情页中的真实种子资源。",
                    },
                },
            ],
        }
    ], {
        "enabled": False,
        "onlyonce": False,
        "username": "",
        "password": "",
        "base_url": "https://mini4k.io",
        "timeout": 20,
        "result_limit": 10,
        "use_proxy": False,
        "auto_relogin": True,
        "ua": default_ua,
    }


def build_page(
    enabled: bool,
    login_ok: bool,
    has_cookie: bool,
    last_login_at: str,
    last_error: str,
    base_url: str,
    use_proxy: bool,
) -> List[dict]:
    status = "运行中" if enabled else "已停用"
    login_status = "成功" if login_ok else "未登录或失败"
    cookie_status = "已保存" if has_cookie else "未保存"
    message = f"状态：{status} | 登录：{login_status} | Cookie：{cookie_status} | 最近登录：{last_login_at or '-'}"
    if last_error:
        message += f" | 最近错误：{last_error}"

    return [
        {
            "component": "VAlert",
            "props": {
                "type": "success" if enabled and login_ok else "info",
                "variant": "tonal",
                "text": message,
            },
        },
        {
            "component": "VTable",
            "props": {"hover": True},
            "content": [
                {
                    "component": "thead",
                    "content": [{
                        "component": "tr",
                        "content": [
                            {"component": "th", "text": "名称"},
                            {"component": "th", "text": "Domain"},
                            {"component": "th", "text": "代理"},
                        ],
                    }],
                },
                {
                    "component": "tbody",
                    "content": [{
                        "component": "tr",
                        "content": [
                            {"component": "td", "text": "Mini4k"},
                            {"component": "td", "text": f"{base_url}/"},
                            {"component": "td", "text": "是" if use_proxy else "否"},
                        ],
                    }],
                },
            ],
        },
    ]


def _col(cols: int, component: dict) -> dict:
    return {
        "component": "VCol",
        "props": {"cols": 12, "md": cols},
        "content": [component],
    }


def _switch(model: str, label: str, hint: str = "") -> dict:
    props = {
        "model": model,
        "label": label,
    }
    if hint:
        props.update({
            "hint": hint,
            "persistent-hint": True,
        })
    return {
        "component": "VSwitch",
        "props": props,
    }


def _text(model: str, label: str, placeholder: str = "", hint: str = "", field_type: str = "text") -> dict:
    props = {
        "model": model,
        "label": label,
    }
    if placeholder:
        props["placeholder"] = placeholder
    if hint:
        props.update({
            "hint": hint,
            "persistent-hint": True,
        })
    if field_type != "text":
        props["type"] = field_type
    return {
        "component": "VTextField",
        "props": props,
    }
