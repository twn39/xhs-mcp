import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .cookie_manager import CookieManager
from ..logger import get_logger

logger = get_logger(__name__)

class AuthManager:
    def __init__(self, cookie_path: Optional[str] = None):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

        # Set default cookie path to ~/.mcp/xhs_mcp/cookies.json
        if not cookie_path:
            home_dir = Path.home()
            mcp_dir = home_dir / ".mcp"
            xhs_dir = mcp_dir / "xhs_mcp"
            
            # Create directories if they don't exist
            if not mcp_dir.exists():
                mcp_dir.mkdir()
            if not xhs_dir.exists():
                xhs_dir.mkdir()
                
            cookie_path = str(xhs_dir / "cookies.json")

        self.cookie_manager = CookieManager(cookie_path)

    async def login(self, timeout_seconds: int = 10) -> None:
        await logger.ainfo(f"Starting login process with timeout: {timeout_seconds}s")
        timeout_ms = timeout_seconds * 1000
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
        )
        
        if not self.browser:
            await logger.aerror("Failed to launch browser")
            raise Exception("Failed to launch browser")

        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                await logger.ainfo(f"Login attempt {retry_count + 1}/{max_retries}")
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

                # Load existing cookies if available
                cookies = await self.cookie_manager.load_cookies()
                if cookies:
                    await self.context.add_cookies(cookies)

                # Navigate to explore page
                try:
                    await self.page.goto(
                        "https://www.xiaohongshu.com/explore", 
                        wait_until="domcontentloaded", 
                        timeout=timeout_ms
                    )
                except Exception:
                    # Ignore navigation timeout, might just be slow load
                    pass

                # Check if already logged in
                # Look for user sidebar
                user_sidebar = await self.page.query_selector(".user.side-bar-component .channel")
                
                is_logged_in = False
                if user_sidebar:
                    text_content = await user_sidebar.text_content()
                    if text_content and text_content.strip() == "我":
                        is_logged_in = True
                
                if is_logged_in:
                    await logger.ainfo("Already logged in")
                    # Already logged in, save cookies and return
                    new_cookies = await self.context.cookies()
                    await self.cookie_manager.save_cookies(new_cookies)
                    return

                # Wait for login dialog
                try:
                    await self.page.wait_for_selector(".login-container", timeout=timeout_ms)
                except Exception:
                    pass

                # Wait for QR code image
                await self.page.wait_for_selector(".qrcode-img", timeout=timeout_ms)

                # Wait for user to complete login
                # Increased timeout for user interaction as per TS implementation (timeout * 6)
                await self.page.wait_for_selector(
                    ".user.side-bar-component .channel", 
                    timeout=timeout_ms * 6
                )

                # Verify the text content
                is_logged_in_after = await self.page.evaluate("""() => {
                    const sidebarUser = document.querySelector('.user.side-bar-component .channel');
                    return sidebarUser?.textContent?.trim() === '我';
                }""")

                if not is_logged_in_after:
                    await logger.aerror("Login verification failed")
                    raise Exception("Login verification failed")

                await logger.ainfo("Login successful, saving cookies")
                new_cookies = await self.context.cookies()
                await self.cookie_manager.save_cookies(new_cookies)
                return

            except Exception as e:
                await logger.aerror(f"Login attempt {retry_count + 1} failed: {e}")
                
                # Close current page/context to clean up
                if self.page:
                    await self.page.close()
                if self.context:
                    await self.context.close()

                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2)
                else:
                    await logger.aerror("Login failed after maximum retries")
                    raise

    async def cleanup(self) -> None:
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
