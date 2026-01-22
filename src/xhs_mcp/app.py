import click
from mcp.server.fastmcp import FastMCP

from .auth.auth_manager import AuthManager
from .tools.rednote_tools import RedNoteTools
from .logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

mcp = FastMCP("RedNote MCP Server")

@mcp.tool(name="search_notes", description="根据关键词搜索笔记")
async def search_notes(keywords: str, limit: int = 10) -> str:
    """
    Search notes by keywords.
    Args:
        keywords: Search keywords
        limit: Max number of results (default 10)
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

@mcp.tool(name="login", description="Login to Xiaohongshu account")
async def login_tool() -> str:
    """
    Login to Xiaohongshu account to save cookies.
    This will open a browser window for you to scan the QR code.
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

@mcp.tool(name="get_note_content", description="根据链接获取笔记详情")
async def get_note_content(url: str) -> str:
    """
    Get note content by URL.
    Args:
        url: Note URL
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

@mcp.tool(name="get_note_comments", description="根据链接获取笔记评论")
async def get_note_comments(url: str) -> str:
    """
    Get note comments by URL.
    Args:
        url: Note URL
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



@click.command()
def serve():
    """Start the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
