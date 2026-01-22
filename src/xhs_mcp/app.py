import click
from mcp.server.fastmcp import FastMCP

from .auth.auth_manager import AuthManager
from .tools.rednote_tools import RedNoteTools
from .logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

mcp = FastMCP("RedNote MCP Server")

@mcp.tool(name="search_notes")
async def search_notes(keywords: str, limit: int = 10) -> str:
    """
    根据关键词搜索小红书笔记
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制 (默认为 10)
        
    Returns:
        str: 格式化后的笔记列表，包含标题、作者、内容摘要、互动数据等
    """
    await logger.ainfo(f"Searching notes with keywords: {keywords}, limit: {limit}")
    try:
        tools = RedNoteTools()
        notes = await tools.search_notes(keywords, limit)
        await logger.ainfo(f"Found {len(notes)} notes")
        
        # Format the result similarly to the TS implementation
        formatted_notes = []
        for note in notes:
            formatted_notes.append(
                f"标题: {note.get('title')}\n"
                f"作者: {note.get('author')}\n"
                f"内容: {note.get('content')}\n"
                f"点赞: {note.get('likes')}\n"
                f"评论: {note.get('comments')}\n"
                f"链接: {note.get('url')}\n"
                "---"
            )
        
        return "\n".join(formatted_notes)
    except Exception as e:
        await logger.aerror(f"Error searching notes: {e}")
        raise Exception(str(e))

@mcp.tool(name="login")
async def login_tool() -> str:
    """
    登录小红书账号并保存 Cookie
    
    功能:
        启动浏览器打开小红书主页
        等待用户扫码登录
        登录成功后自动保存 Cookie 到本地
        
    Returns:
        str: 登录结果消息
    """
    await logger.ainfo("Starting login process via tool")
    auth_manager = AuthManager()
    try:
        await auth_manager.login()
        await auth_manager.cleanup()
        return "Login successful! Cookie has been saved."
    except Exception as e:
        await logger.aerror(f"Login failed: {e}")
        await auth_manager.cleanup()
        raise Exception(str(e))  # Re-raise stringified error for MCP tool

@mcp.tool(name="get_note_content")
async def get_note_content(url: str) -> str:
    """
    获取小红书笔记详细内容
    
    Args:
        url: 笔记链接
        
    Returns:
        str: 笔记详情，包含标题、全文、标签、所有互动数据等
    """
    await logger.ainfo(f"Get note content tool called with url: {url}")
    tools = RedNoteTools()
    try:
        note = await tools.get_note_content(url)
        # Format result
        result = (
            f"标题: {note.get('title')}\n"
            f"作者: {note.get('author')}\n"
            f"内容: {note.get('content')}\n"
            f"点赞: {note.get('likes')}\n"
            f"评论: {note.get('comments')}\n"
            f"标签: {', '.join(note.get('tags', []))}\n"
            f"链接: {note.get('url')}\n"
        )
        return result
    except Exception as e:
        await logger.aerror(f"Get note content failed: {e}")
        return f"Get note content failed: {str(e)}"
    finally:
        await tools.cleanup()

@mcp.tool(name="get_note_comments")
async def get_note_comments(url: str) -> str:
    """
    获取小红书笔记评论列表
    
    Args:
        url: 笔记链接
        
    Returns:
        str: 评论列表，包含评论用户、内容、点赞数、时间等信息
    """
    await logger.ainfo(f"Get note comments tool called with url: {url}")
    tools = RedNoteTools()
    try:
        comments = await tools.get_note_comments(url)
        # Format result
        formatted = []
        for c in comments:
            formatted.append(
                f"用户: {c.get('author')}\n"
                f"点赞: {c.get('likes')}\n"
                f"时间: {c.get('time')}\n"
                f"内容: {c.get('content')}\n"
                "---"
            )
        return "\n".join(formatted) if formatted else "暂无评论"
    except Exception as e:
        await logger.aerror(f"Get note comments failed: {e}")
        return f"Get note comments failed: {str(e)}"
    finally:
        await tools.cleanup()


@mcp.tool(name="publish_note")
async def publish_note(files: list[str], title: str = "", content: str = "") -> str:
    """
    发布小红书笔记 (上传图片并发布)
    
    Args:
        files: 图片文件路径列表 (绝对路径)
        title: 笔记标题
        content: 笔记正文
        
    Returns:
        str: 发布结果消息
    """
    await logger.ainfo(f"Publish note tool called with {len(files)} files, title: {title}")
    tools = RedNoteTools()
    try:
        result = await tools.publish_note(files, title, content)
        return result
    except Exception as e:
        await logger.aerror(f"Publish note failed: {e}")
        # Cleanup on failure
        await tools.cleanup()
        return f"Publish note failed: {str(e)}"

@click.command()
def serve():
    """Start the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
