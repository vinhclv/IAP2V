# -*- coding: utf-8 -*-
"""
Captcha Pool - Multiple browsers with auto-switching
"""

import asyncio
from typing import Optional, Dict, List, Tuple

from .browser import BrowserInstance


class FlowCaptchaPool:
    """
    Pool of multiple browsers for solving captcha.
    Features:
    - Auto-select best browser (least failures)
    - Auto-switch to another browser on failure
    - Round-robin when browsers have equal failure count
    """

    def __init__(self, num_browsers: int = 2, headless: bool = True):
        """
        Initialize pool.

        Args:
            num_browsers: Number of browser instances
            headless: Run browsers in headless mode
        """
        self.num_browsers = num_browsers
        self.headless = headless
        self._browsers: List[BrowserInstance] = []
        self._initialized = False
        self._round_robin_index = 0
        self._last_used_index: Optional[int] = None

    @property
    def is_initialized(self) -> bool:
        """Check if pool is initialized."""
        return self._initialized

    @property
    def browser_count(self) -> int:
        """Get number of active browsers."""
        return len(self._browsers)

    async def initialize(self) -> bool:
        """
        Initialize all browsers.

        Returns:
            True if at least one browser initialized successfully
        """
        if self._initialized:
            return True

        print(f"[FlowCaptchaPool] Initializing {self.num_browsers} browser(s)...")

        success_count = 0
        for i in range(self.num_browsers):
            browser = BrowserInstance(i, self.headless)
            if await browser.initialize():
                self._browsers.append(browser)
                success_count += 1
            else:
                print(f"[FlowCaptchaPool] Browser {i} FAILED")

        if success_count > 0:
            self._initialized = True
            print(f"[FlowCaptchaPool] {success_count}/{self.num_browsers} browsers ready!")
            return True
        else:
            print("[FlowCaptchaPool] No browsers initialized!")
            return False

    def _get_best_browser(self) -> Tuple[int, BrowserInstance]:
        """
        Select best browser:
        1. Browser with least failures
        2. Round-robin if equal
        """
        if not self._browsers:
            raise RuntimeError("No browsers available")

        # Sort by failure count
        sorted_browsers = sorted(
            enumerate(self._browsers),
            key=lambda x: x[1]._consecutive_failures
        )

        # Find browsers with same lowest failure count
        min_failures = sorted_browsers[0][1]._consecutive_failures
        candidates = [(i, b) for i, b in sorted_browsers if b._consecutive_failures == min_failures]

        # Round-robin among candidates
        selected_idx = self._round_robin_index % len(candidates)
        self._round_robin_index += 1

        idx, browser = candidates[selected_idx]
        return idx, browser

    async def get_token(self, project_id: str, max_retries: int = 2) -> Optional[str]:
        """
        Get token - auto-switch browser on failure.

        Args:
            project_id: Google Labs Flow project ID
            max_retries: Number of retries (with different browsers)

        Returns:
            Token string or None
        """
        if not self._initialized:
            if not await self.initialize():
                return None

        tried_browsers = set()

        for attempt in range(max_retries):
            # Select browser
            idx, browser = self._get_best_browser()

            # Avoid reusing failed browser
            if idx in tried_browsers and len(tried_browsers) < len(self._browsers):
                for i, b in enumerate(self._browsers):
                    if i not in tried_browsers:
                        idx, browser = i, b
                        break

            tried_browsers.add(idx)
            self._last_used_index = idx

            # Show status
            statuses = [f"B{i}:{b._consecutive_failures}" for i, b in enumerate(self._browsers)]
            print(f"[FlowCaptchaPool] Attempt {attempt+1}/{max_retries} | Browser-{idx} | Status: [{', '.join(statuses)}]")

            token, error = await browser.get_token(project_id)

            if token:
                return token

            print(f"[FlowCaptchaPool] Browser-{idx} failed: {error}")

            if len(tried_browsers) >= len(self._browsers):
                print("[FlowCaptchaPool] All browsers tried!")
                break

        return None

    def report_success(self):
        """Report success from API - reset counter for last used browser."""
        if self._last_used_index is not None and self._last_used_index < len(self._browsers):
            self._browsers[self._last_used_index].mark_api_success()

    def report_failure(self, reason: str = ""):
        """Report failure from API - increment counter for last used browser."""
        if self._last_used_index is not None and self._last_used_index < len(self._browsers):
            self._browsers[self._last_used_index].mark_api_failure(reason)

    def get_status(self) -> Dict:
        """Get pool status."""
        return {
            "initialized": self._initialized,
            "num_browsers": len(self._browsers),
            "browsers": [
                {
                    "id": i,
                    "failures": b._consecutive_failures,
                    "resets": b._total_resets,
                    "initialized": b._initialized
                }
                for i, b in enumerate(self._browsers)
            ]
        }

    async def close(self):
        """Close all browsers."""
        print(f"[FlowCaptchaPool] Closing {len(self._browsers)} browser(s)...")
        for browser in self._browsers:
            await browser.close()
        self._browsers.clear()
        self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
