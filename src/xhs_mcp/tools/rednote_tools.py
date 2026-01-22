import asyncio
import random
import urllib.parse
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from ..auth.auth_manager import AuthManager
from ..logger import get_logger

logger = get_logger(__name__)

class RedNoteTools:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def initialize(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        
        try:
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            # Load cookies if available
            cookies = await self.auth_manager.cookie_manager.load_cookies()
            if cookies:
                await self.context.add_cookies(cookies)

            # Check login status
            await self.page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
            
            is_logged_in = await self.page.evaluate("""() => {
                const sidebarUser = document.querySelector('.user.side-bar-component .channel');
                return sidebarUser?.textContent?.trim() === '我';
            }""")

            if not is_logged_in:
                await logger.aerror("Not logged in, please login first")
                # We do not throw error here to allow public search if possible, 
                # but TS implies login is required. TS throws error.
                # "Not logged in, please login first"
                raise Exception("Not logged in")
            
        except Exception as e:
            await self.cleanup()
            raise e

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

    async def random_delay(self, min_seconds: float, max_seconds: float) -> None:
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def search_notes(self, keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        await logger.ainfo(f"Searching notes with keywords: {keywords}, limit: {limit}")
        try:
            await self.initialize()
            if not self.page:
                raise Exception("Page not initialized")

            # Navigate to search page
            # TypeScript used: `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keywords)}`
            encoded_keyword = urllib.parse.quote(keywords)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}"
            await self.page.goto(search_url)

            # Wait for search results
            await self.page.wait_for_selector(".feeds-container", timeout=30000)

            # Get all note items
            # We fetch handles to elements
            note_items = await self.page.query_selector_all(".feeds-container .note-item")
            await logger.ainfo(f"Found {len(note_items)} note items")
            
            notes: List[Dict[str, Any]] = []
            
            count_to_process = min(len(note_items), limit)
            
            for i in range(count_to_process):
                try:
                    item = note_items[i]
                    
                    cover = await item.query_selector("a.cover.mask.ld")
                    if cover:
                        await cover.click()
                    else:
                        continue

                    # Wait for note page (modal) to load
                    await self.page.wait_for_selector("#noteContainer", timeout=30000)

                    await self.random_delay(0.5, 1.5)

                    # Extract content
                    note_data = await self.page.evaluate("""() => {
                        const article = document.querySelector('#noteContainer');
                        if (!article) return null;

                        const titleElement = article.querySelector('#detail-title');
                        const title = titleElement?.textContent?.trim() || '';

                        const contentElement = article.querySelector('#detail-desc .note-text');
                        const content = contentElement?.textContent?.trim() || '';

                        const authorElement = article.querySelector('.author-wrapper .username');
                        const author = authorElement?.textContent?.trim() || '';

                        const engageBar = document.querySelector('.engage-bar-style');
                        const likesElement = engageBar?.querySelector('.like-wrapper .count');
                        const likes = parseInt(likesElement?.textContent?.replace(/[^\\d]/g, '') || '0');

                        const collectElement = engageBar?.querySelector('.collect-wrapper .count');
                        const collects = parseInt(collectElement?.textContent?.replace(/[^\\d]/g, '') || '0');

                        const commentsElement = engageBar?.querySelector('.chat-wrapper .count');
                        const comments = parseInt(commentsElement?.textContent?.replace(/[^\\d]/g, '') || '0');

                        return {
                            title,
                            content,
                            url: window.location.href,
                            author,
                            likes,
                            collects,
                            comments
                        };
                    }""")

                    if note_data:
                        notes.append(note_data)

                    # Add random delay
                    await self.random_delay(0.5, 1.0)

                    # Close note
                    close_button = await self.page.query_selector(".close-circle")
                    if close_button:
                        await close_button.click()
                        
                        # Wait for detached
                        await self.page.wait_for_selector(
                            "#noteContainer", 
                            state="detached", 
                            timeout=30000
                        )
                
                except Exception as e:
                    await logger.aerror(f"Error processing note {i + 1}: {e}")
                    # Attempt to close if stuck
                    try:
                        close_button = await self.page.query_selector(".close-circle")
                        if close_button:
                            await close_button.click()
                            await self.page.wait_for_selector(
                                "#noteContainer", 
                                state="detached", 
                                timeout=30000
                            )
                    except Exception:
                         pass

                finally:
                    await self.random_delay(0.5, 1.5)

            await logger.ainfo(f"Successfully processed {len(notes)} notes")
            return notes

        except Exception as e:
            await logger.aerror(f"Error searching notes: {e}")
            raise e
        finally:
            await self.cleanup()

    async def get_note_content(self, url: str) -> Dict[str, Any]:
        await logger.ainfo(f"Getting note content for URL: {url}")
        try:
            await self.initialize()
            if not self.page:
                raise Exception("Page not initialized")

            await self.page.goto(url)

            try:
                await logger.ainfo("Waiting for content to load")
                await self.page.wait_for_selector(".note-container", timeout=30000)
            except Exception:
                raise Exception("Note container not found")

            # Extract content using evaluate, ported from noteDetail.ts
            note_data = await self.page.evaluate("""() => {
                function ChineseUnitStrToNumber(str) {
                    if (!str) return 0;
                    if (str.includes('万')) {
                        return parseFloat(str.replace('万', '').trim()) * 10000;
                    } else {
                        return parseInt(str.replace(/[^\\d]/g, '') || '0');
                    }
                }

                const article = document.querySelector('.note-container');
                if (!article) return null;

                // Get title
                const title = 
                    article.querySelector('#detail-title')?.textContent?.trim() ||
                    article.querySelector('.title')?.textContent?.trim() || 
                    '';

                // Get content
                // TS uses .note-scroller -> .note-content .note-text span
                const contentBlock = article.querySelector('.note-scroller');
                const contentText = contentBlock?.querySelector('.note-content .note-text')?.textContent?.trim() || '';

                // Get tags
                const tags = Array.from(contentBlock?.querySelectorAll('.note-content .note-text a') || []).map(tag => {
                    return tag.textContent?.trim().replace('#', '') || '';
                });

                // Get author info
                const authorElement = article.querySelector('.author-container .info');
                const author = authorElement?.querySelector('.username')?.textContent?.trim() || '';

                // Get stats
                const interactContainer = document.querySelector('.interact-container');
                const commentsNumber = interactContainer?.querySelector('.chat-wrapper .count')?.textContent?.trim() || '';
                const likesNumber = interactContainer?.querySelector('.like-wrapper .count')?.textContent?.trim() || '';

                return {
                    title,
                    content: contentText,
                    tags,
                    author,
                    likes: ChineseUnitStrToNumber(likesNumber),
                    comments: ChineseUnitStrToNumber(commentsNumber),
                    url: window.location.href
                };
            }""")

            if not note_data:
                raise Exception("Failed to extract note data")

            await logger.ainfo(f"Successfully extracted note: {note_data.get('title')}")
            return note_data

        except Exception as e:
            await logger.aerror(f"Error getting note content: {e}")
            raise e
        finally:
            await self.cleanup()

    async def get_note_comments(self, url: str) -> List[Dict[str, Any]]:
        await logger.ainfo(f"Getting comments for URL: {url}")
        try:
            await self.initialize()
            if not self.page:
                raise Exception("Page not initialized")

            await self.page.goto(url)

            # Wait for comments to load
            await logger.ainfo("Waiting for comments to load")
            try:
                await self.page.wait_for_selector('.comments-container', timeout=10000)
            except Exception:
                await logger.awarn("Comments container not found, trying fallback or empty")

            # Scroll to load all comments
            await logger.ainfo("Scrolling to load all comments...")
            await self.page.evaluate("""async () => {
                const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
                
                // Find visible scrollable container
                const getScrollContainer = () => {
                    return document.querySelector('.note-scroller') || 
                           document.querySelector('.note-content-container') || 
                           document.documentElement;
                };

                const container = getScrollContainer();
                let lastHeight = 0;
                let sameHeightCount = 0;
                const maxSameHeightCount = 3;

                while (true) {
                    const currentHeight = container.scrollHeight;
                    if (currentHeight === lastHeight) {
                        sameHeightCount++;
                        if (sameHeightCount >= maxSameHeightCount) {
                            break;
                        }
                    } else {
                        sameHeightCount = 0;
                    }
                    lastHeight = currentHeight;

                    container.scrollTo(0, currentHeight);
                    await sleep(1500);
                }
            }""")

            # Extract comments
            comments = await self.page.evaluate("""() => {
                const items = document.querySelectorAll('.comment-item');
                const results = [];

                items.forEach((item) => {
                    const author = item.querySelector('.author-wrapper .name')?.textContent?.trim() || '';
                    const content = item.querySelector('.content .note-text')?.textContent?.trim() || '';
                    
                    let likesStr = item.querySelector('.like-wrapper .count')?.textContent?.trim() || '0';
                    if (likesStr === '赞' || likesStr === '点赞') likesStr = '0';
                    const likes = parseInt(likesStr.replace(/[^\\d]/g, '') || '0');
                    
                    // Date extraction
                    const dateEl = item.querySelector('.info .date');
                    let time = '';
                    if (dateEl) {
                         const spans = dateEl.querySelectorAll('span');
                         if (spans.length > 0) {
                            time = spans[0].textContent?.trim() || '';
                         } else {
                            time = dateEl.textContent?.trim() || '';
                         }
                    }

                    results.push({ author, content, likes, time });
                });

                return results;
            }""")

            await logger.ainfo(f"Successfully extracted {len(comments)} comments")
            return comments

        except Exception as e:
            await logger.aerror(f"Error getting note comments: {e}")
            raise e
        finally:
            await self.cleanup()

    async def publish_note(self, files: List[str], title: str = "", content: str = "") -> str:
        try:
            await self.initialize()
            if not self.page:
                raise Exception("Page not initialized")

            # Navigate to publish page
            publish_url = "https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch&target=image"
            await logger.ainfo(f"Navigating to {publish_url}")
            await self.page.goto(publish_url)
            
            # Wait for upload input
            await logger.ainfo("Waiting for upload input")
            upload_input_selector = "input.upload-input"
            try:
                await self.page.wait_for_selector(upload_input_selector, state="attached", timeout=30000)
            except Exception:
                await logger.aerror("Upload input not found")
                raise Exception("Upload input not found. Please ensure you are logged in.")

            await self.page.locator(upload_input_selector).set_input_files(files)

            img_container_selector = ".img-upload-area .img-container"
            try:
                await self.page.wait_for_selector(img_container_selector, state="visible", timeout=60000)

                if len(files) > 1:
                     await self.page.wait_for_function(
                        f"document.querySelectorAll('{img_container_selector}').length === {len(files)}",
                        timeout=60000
                    )
                await logger.ainfo(f"Confirmed {len(files)} images uploaded and visible")
            except Exception as e:
                await logger.awarn(f"Timeout waiting for image previews: {e}. Proceeding anyway...")

            title_selector = "input.d-text[placeholder*='标题']"
            
            try:
                await self.page.wait_for_selector(title_selector, state="visible", timeout=60000)
            except Exception:
                # Fallback to just .d-text if placeholder differs
                title_selector = "input.d-text"
                await self.page.wait_for_selector(title_selector, state="visible", timeout=10000)

            # 1. Fill Title
            if title:
                await logger.ainfo(f"Filling title: {title}")
                await self.page.click(title_selector)
                await self.page.fill(title_selector, title)
                await self.random_delay(0.5, 1.0)
            
            # 2. Fill Content
            if content:
                await logger.ainfo("Filling content")
                content_selector = ".tiptap.ProseMirror"
                await self.page.click(content_selector)
                await self.page.fill(content_selector, content)
                await self.random_delay(0.5, 1.0)
            
            # Wait 2 seconds before publishing as requested
            await logger.ainfo("Waiting 2s before publishing...")
            await asyncio.sleep(2)
                
            # 3. Click Publish with Retry Logic
            # Retry clicking publish every 2s until success or timeout
            publish_btn_selector = ".publishBtn"
            success_selector = ".success-container"
            
            max_retries = 30 # 30 * 2 = 60 seconds max wait
            for i in range(max_retries):
                try:
                    await logger.ainfo(f"Clicking publish button (Attempt {i+1}/{max_retries})")
                    await self.page.click(publish_btn_selector)
                    
                    # Check for success immediately with short timeout (2s)
                    try:
                        await self.page.wait_for_selector(success_selector, state="visible", timeout=2000)
                        
                        # Verify text
                        success_text = await self.page.text_content(success_selector)
                        if "发布成功" in success_text:
                            await logger.ainfo("Publish verified successfully")
                            return "Note published successfully (Verified '发布成功')."
                    except Exception:
                        # Success not found yet
                        pass
                    
                except Exception as e:
                    await logger.awarn(f"Publish attempt {i+1} failed (click error?): {e}")
                    await asyncio.sleep(2)
            
            return "Publish timed out after multiple attempts. Please check browser."

        except Exception as e:
            await logger.aerror(f"Error publishing note: {e}")
            raise e
        finally:
            await self.cleanup()

