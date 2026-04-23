# -*- coding: utf-8 -*-
"""
Browser Instance - Single browser with auto-reset capability
"""

import asyncio
import time
import random
from typing import Optional, Dict, Tuple

from .config import (
    TIMEOUT_PAGE_LOAD, TIMEOUT_DOM_LOAD, TIMEOUT_RECAPTCHA_READY,
    TIMEOUT_READY_CALLBACK, MAX_RETRIES, RETRY_WAIT, MAX_CONSECUTIVE_FAILURES,
    MIN_REQUEST_DELAY, MAX_REQUEST_DELAY, RECAPTCHA_WEBSITE_KEY,
    RECAPTCHA_ACTION, RECAPTCHA_SCRIPT_URL, BROWSER_ARGS,
    USER_AGENTS, VIEWPORTS, TIMEZONES
)
from .stealth import STEALTH_SCRIPT

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright, Route
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserInstance:
    """
    A single browser instance with:
    - Auto-reset when consecutive failures exceed threshold
    - Random fingerprint on each initialization
    - Page caching for performance
    """

    def __init__(self, instance_id: int = 0, headless: bool = True):
        """
        Initialize browser instance.

        Args:
            instance_id: Unique identifier for this browser
            headless: Run browser in headless mode
        """
        self.instance_id = instance_id
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._initialized = False
        self._page_cache: Dict[str, Page] = {}

        # Counters
        self._consecutive_failures = 0
        self._total_resets = 0
        self._last_request_time = 0

        # Random fingerprint
        self._user_agent = random.choice(USER_AGENTS)
        self._viewport = random.choice(VIEWPORTS)
        self._timezone = random.choice(TIMEZONES)

        # Lock for thread safety
        self._lock = asyncio.Lock()
        self._needs_reset = False

    @property
    def failures(self) -> int:
        """Get current consecutive failure count."""
        return self._consecutive_failures

    @property
    def resets(self) -> int:
        """Get total reset count."""
        return self._total_resets

    @property
    def is_initialized(self) -> bool:
        """Check if browser is initialized."""
        return self._initialized

    async def initialize(self) -> bool:
        """
        Initialize browser with random fingerprint.

        Returns:
            True if successful
        """
        if self._initialized:
            return True

        if not PLAYWRIGHT_AVAILABLE:
            print(f"[Browser-{self.instance_id}] Playwright not installed!")
            return False

        try:
            # Random fingerprint
            self._user_agent = random.choice(USER_AGENTS)
            self._viewport = random.choice(VIEWPORTS)
            self._timezone = random.choice(TIMEZONES)

            print(f"[Browser-{self.instance_id}] Initializing: "
                  f"VP={self._viewport['width']}x{self._viewport['height']}, TZ={self._timezone}")

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=BROWSER_ARGS
            )

            self.context = await self.browser.new_context(
                viewport=self._viewport,
                user_agent=self._user_agent,
                locale='en-US',
                timezone_id=self._timezone
            )

            await self.context.route("**/*", self._route_handler)
            await self.context.add_init_script(STEALTH_SCRIPT)

            self._initialized = True
            print(f"[Browser-{self.instance_id}] Ready!")
            return True

        except Exception as e:
            print(f"[Browser-{self.instance_id}] Init error: {e}")
            return False

    async def _route_handler(self, route: Route) -> None:
        """Block unnecessary resources."""
        request = route.request
        resource_type = request.resource_type
        url = request.url.lower()

        google_domains = ["recaptcha", "google.com", "googleapis.com", "gstatic.com"]
        if any(domain in url for domain in google_domains):
            await route.continue_()
            return

        if resource_type in {"document", "script", "xhr", "fetch", "websocket"}:
            await route.continue_()
            return

        if resource_type in {"image", "stylesheet", "font", "media"}:
            await route.abort()
            return

        await route.continue_()

    async def _get_or_create_page(self, project_id: str) -> Page:
        """Get or create page from cache."""
        if project_id in self._page_cache:
            page = self._page_cache[project_id]
            try:
                _ = page.url
                return page
            except:
                del self._page_cache[project_id]

        page = await self.context.new_page()
        self._page_cache[project_id] = page
        return page

    async def _apply_delay(self):
        """Apply delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < MIN_REQUEST_DELAY:
            delay = MIN_REQUEST_DELAY + random.uniform(0, MAX_REQUEST_DELAY - MIN_REQUEST_DELAY)
            await asyncio.sleep(delay - elapsed)
        self._last_request_time = time.time()

    async def _load_page(self, page: Page, url: str) -> Tuple[bool, Optional[str]]:
        """Load page and check for errors."""
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_PAGE_LOAD)
            if response and response.status == 403:
                return False, "403 Forbidden"
        except Exception as e:
            if '403' in str(e).lower():
                return False, "403 Forbidden"

        await asyncio.sleep(1)

        # Check login redirect
        current_url = page.url.lower()
        if 'accounts.google.com' in current_url or '/signin' in current_url:
            return False, "Login redirect"

        # Check 403 in content
        try:
            title = await page.title()
            if '403' in title.lower() or 'forbidden' in title.lower():
                return False, "403 in page"

            body = await page.evaluate("() => document.body?.innerText?.substring(0, 300) || ''")
            body_lower = body.lower()
            if '403' in body_lower or 'access denied' in body_lower or 'unusual traffic' in body_lower:
                return False, "403 in content"
        except:
            pass

        # Inject recaptcha
        try:
            has_recaptcha = await page.evaluate(
                "() => window.grecaptcha && typeof window.grecaptcha.execute === 'function'"
            )
            if not has_recaptcha:
                await page.add_script_tag(url=RECAPTCHA_SCRIPT_URL)
        except:
            pass

        return True, None

    async def _wait_for_recaptcha_ready(self, page: Page) -> bool:
        """Wait for recaptcha to be ready."""
        try:
            await page.wait_for_function(
                "() => window.grecaptcha && typeof window.grecaptcha.execute === 'function'",
                timeout=TIMEOUT_RECAPTCHA_READY
            )
            return True
        except:
            pass

        # Polling fallback
        for _ in range(30):
            try:
                ready = await page.evaluate(
                    "() => window.grecaptcha && typeof window.grecaptcha.execute === 'function'"
                )
                if ready:
                    return True
            except:
                pass
            await asyncio.sleep(0.3)

        return False

    async def _execute_recaptcha(self, page: Page) -> Dict:
        """Execute recaptcha to get token."""
        for retry in range(MAX_RETRIES):
            try:
                result = await page.evaluate(f"""
                    async (websiteKey) => {{
                        try {{
                            return await new Promise((resolve) => {{
                                let resolved = false;
                                const timeout = setTimeout(() => {{
                                    if (!resolved) {{ resolved = true; resolve({{error: 'Timeout'}}); }}
                                }}, {TIMEOUT_READY_CALLBACK});

                                const exec = () => {{
                                    if (resolved) return;
                                    if (!window.grecaptcha?.execute) {{
                                        clearTimeout(timeout); resolved = true;
                                        resolve({{error: 'grecaptcha not found'}});
                                        return;
                                    }}
                                    window.grecaptcha.execute(websiteKey, {{action: '{RECAPTCHA_ACTION}'}})
                                        .then(token => {{
                                            if (!resolved) {{ clearTimeout(timeout); resolved = true; resolve({{token}}); }}
                                        }})
                                        .catch(e => {{
                                            if (!resolved) {{ clearTimeout(timeout); resolved = true; resolve({{error: e.message}}); }}
                                        }});
                                }};

                                if (window.grecaptcha?.execute) exec();
                                else if (window.grecaptcha?.ready) window.grecaptcha.ready(exec);
                                else {{
                                    const interval = setInterval(() => {{
                                        if (resolved) {{ clearInterval(interval); return; }}
                                        if (window.grecaptcha?.execute) {{ clearInterval(interval); exec(); }}
                                    }}, 200);
                                }}
                            }});
                        }} catch (e) {{ return {{error: e.message}}; }}
                    }}
                """, RECAPTCHA_WEBSITE_KEY)
                return result

            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_WAIT)
                else:
                    return {"error": str(e)}

        return {"error": "Max retries"}

    async def _handle_failure(self, error_msg: str):
        """Handle failure - increment counter and reset if needed."""
        self._consecutive_failures += 1
        print(f"[Browser-{self.instance_id}] FAIL #{self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}: {error_msg[:50]}")

        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            print(f"[Browser-{self.instance_id}] === TOO MANY FAILURES! RESETTING... ===")
            await self.reset()

    async def get_token(self, project_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get reCAPTCHA token for project.

        Args:
            project_id: Google Labs Flow project ID

        Returns:
            Tuple of (token, error_message)
        """
        async with self._lock:
            # Check if reset needed from API failure
            if self._needs_reset:
                print(f"[Browser-{self.instance_id}] Reset needed from API failures...")
                await self.reset()
                self._needs_reset = False

            # Apply delay
            await self._apply_delay()

            start_time = time.time()
            website_url = f"https://labs.google/fx/tools/flow/project/{project_id}"

            try:
                page = await self._get_or_create_page(project_id)

                # Load page
                print(f"[Browser-{self.instance_id}] Loading...")
                success, error_type = await self._load_page(page, website_url)

                if not success:
                    print(f"[Browser-{self.instance_id}] Load failed: {error_type}")
                    await self._handle_failure(f"Load failed: {error_type}")
                    return None, error_type
                
                # Wait for recaptcha
                ready = await self._wait_for_recaptcha_ready(page)
                if not ready:
                    await self._handle_failure("Recaptcha not ready")
                    return None, "Recaptcha not ready"

                # Execute
                result = await self._execute_recaptcha(page)
                duration_ms = (time.time() - start_time) * 1000

                if isinstance(result, dict) and result.get('token'):
                    old_failures = self._consecutive_failures
                    self._consecutive_failures = 0
                    print(f"[Browser-{self.instance_id}] OK! ({duration_ms:.0f}ms) Failures: {old_failures} -> 0")
                    return result['token'], None
                else:
                    error = result.get('error', 'Unknown') if isinstance(result, dict) else 'Invalid'
                    await self._handle_failure(error)
                    return None, error

            except Exception as e:
                await self._handle_failure(str(e))
                return None, str(e)

    async def reset(self):
        """Reset browser with new fingerprint."""
        self._total_resets += 1
        print(f"[Browser-{self.instance_id}] Resetting... (count: {self._total_resets})")

        await self.close()

        # Delay before reinitializing
        delay = 3 + random.randint(0, 3)
        print(f"[Browser-{self.instance_id}] Waiting {delay}s...")
        await asyncio.sleep(delay)

        success = await self.initialize()
        if success:
            self._consecutive_failures = 0
            print(f"[Browser-{self.instance_id}] Reset OK with new fingerprint!")
        else:
            print(f"[Browser-{self.instance_id}] Reset FAILED!")

    async def close(self):
        """Close browser."""
        try:
            for page in list(self._page_cache.values()):
                try:
                    await page.close()
                except:
                    pass
            self._page_cache.clear()

            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self._initialized = False
        except:
            pass

    def mark_api_success(self):
        """Call when API returns success."""
        if self._consecutive_failures > 0:
            print(f"[Browser-{self.instance_id}] API OK! Failures: {self._consecutive_failures} -> 0")
        self._consecutive_failures = 0
        self._needs_reset = False

    def mark_api_failure(self, reason: str = ""):
        """Call when API returns error (token rejected)."""
        old = self._consecutive_failures
        self._consecutive_failures += 1
        print(f"[Browser-{self.instance_id}] API REJECT! Failures: {old} -> {self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}")

        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            print(f"[Browser-{self.instance_id}] Reset needed from API failures!")
            self._needs_reset = True

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
