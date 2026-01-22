# RedNote MCP Server (xhs-mcp)

基于 Model Context Protocol (MCP) 的小红书 (RedNote) 服务端，允许 AI 助手与小红书进行交互。基于 Playwright 实现，支持搜索笔记、获取笔记详情、查看评论以及扫码登录等功能。

## ✨ 功能特性

*   **🔍 搜索笔记** (`search_notes`)
    *   根据关键词搜索小红书笔记
    *   支持指定返回结果数量
    *   返回包含标题、作者、点赞/评论数等摘要信息

*   **📄 获取笔记详情** (`get_note_content`)
    *   通过笔记链接获取详细内容
    *   解析标题、完整正文、标签
    *   获取作者信息及详细互动数据

*   **💬 获取笔记评论** (`get_note_comments`)
    *   获取指定笔记的评论列表
    *   **支持自动滚动**：自动加载页面以获取更多评论（而不仅是首屏评论）
    *   解析评论用户、内容、时间及点赞数

*   **🔑 扫码登录** (`login`)
    *   启动浏览器显示登录二维码
    *   自动捕获并持久化保存 Cookie
    *   支持免由于 Cookie 过期导致的重复登录

## 🛠️ 安装与配置

该项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。

### 前置要求

*   Python >= 3.12
*   Chrome/Chromium 浏览器 (Playwright 会自动安装)

### 安装步骤

1.  **克隆仓库**
    ```bash
    git clone <repository_url>
    cd xhs-mcp
    ```

2.  **安装依赖**
    ```bash
    uv sync
    ```

3.  **安装浏览器驱动**
    ```bash
    uv run playwright install chromium
    ```

## 💻 开发与调试

### 本地运行

直接运行服务进行测试：

```bash
uv run xhs-mcp
```

### 日志

服务运行日志会输出到项目根目录下的 `log.txt` 文件中，方便排查问题。
