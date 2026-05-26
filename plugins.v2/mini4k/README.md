# Mini4k

Mini4k V2 插件用于把 `https://mini4k.io` 接入 MoviePilot 搜索链路。

## 功能

- 在配置页保存 Mini4k 用户名和密码。
- 允许配置 User-Agent，默认使用 Chrome macOS UA。
- 勾选“立即运行一次”后登录 Mini4k 并保存 Cookie。
- Cookie 失效时自动使用配置的用户名密码重登一次。
- 注册 Mini4k 索引器。
- 通过 `get_module()` 接管 `search_torrents`，把 Mini4k 搜索页中的电影条目展开为详情页中的真实 `.torrent` 或 magnet 资源。
- 通过 `get_agent_tools()` 注册智能体工具，支持 agent 搜索资源和手动刷新 Cookie。

## 使用

1. 安装并启用插件。
2. 填写 Mini4k 用户名、密码。
3. 勾选“立即运行一次”并保存配置。
4. 在 MoviePilot 站点管理中添加并启用 `http://mini4k_indexer.orangeboy/`。
5. 正常使用 MoviePilot 搜索，Mini4k 结果会以种子资源形式返回。

## 说明

Mini4k 的搜索页不是种子列表，而是电影列表；真正的种子资源在电影详情页。插件不会把电影详情页伪装成下载链接，而是在搜索时进入详情页解析资源表，最终只返回真实 `.torrent` 或 magnet。

站点管理里的 Domain 使用虚拟地址 `http://mini4k_indexer.orangeboy/`，和 Prowlarr 插件的 `http://prowlarr_indexer.{num}/` 类似；真实请求仍然访问配置里的 `https://mini4k.io`。

## 智能体工具

- `mini4k_search_torrents`：按关键字搜索 Mini4k，支持 `page` 分页，并展开电影详情页中的真实资源。
- `mini4k_login`：使用配置页保存的用户名密码登录 Mini4k，刷新并保存 Cookie。
