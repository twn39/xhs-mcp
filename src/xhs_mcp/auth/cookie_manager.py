import json
from pathlib import Path
from typing import List, Any
import aiofiles

from ..logger import get_logger

logger = get_logger(__name__)

class CookieManager:
    def __init__(self, cookie_path: str):
        self.cookie_path = Path(cookie_path)

    async def save_cookies(self, cookies: List[Any]) -> None:
        """Save cookies to the file."""
        try:
            # Create directory if it doesn't exist
            self.cookie_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(self.cookie_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(cookies, indent=2))
            await logger.ainfo("Cookies saved successfully")
        except Exception as e:
            await logger.aerror(f"Failed to save cookies: {e}")
            raise

    async def load_cookies(self) -> List[Any]:
        """Load cookies from the file."""
        if not self.cookie_path.exists():
            return []
        
        try:
            async with aiofiles.open(self.cookie_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                cookies = json.loads(content)
            await logger.ainfo(f"Loaded {len(cookies)} cookies")
            return cookies
        except Exception as e:
            await logger.aerror(f"Failed to load cookies: {e}")
            return []

    async def clear_cookies(self) -> None:
        """Delete the cookies file."""
        if self.cookie_path.exists():
            try:
                self.cookie_path.unlink()
                await logger.ainfo("Cookies cleared successfully")
            except Exception as e:
                await logger.aerror(f"Failed to clear cookies: {e}")
                raise
        else:
            pass
