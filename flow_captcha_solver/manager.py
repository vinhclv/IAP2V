# -*- coding: utf-8 -*-
"""
Captcha Manager - Singleton with sync API
"""

import asyncio
import threading
from typing import Optional, Dict

from .pool import FlowCaptchaPool
from .browser import BrowserInstance, PLAYWRIGHT_AVAILABLE


class FlowCaptchaManager:
    """
    Main manager - Singleton pattern.
    Provides synchronous (blocking) API for use from main thread.
    """

    _instance: Optional['FlowCaptchaManager'] = None

    def __init__(self, headless: bool = True):
        if FlowCaptchaManager._instance is not None:
            raise RuntimeError("Use get_instance() instead")

        self.headless = headless
        self._pool: Optional[FlowCaptchaPool] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._initialized = False
        self._lock = threading.Lock()

        FlowCaptchaManager._instance = self

    @staticmethod
    def get_instance(headless: bool = True) -> 'FlowCaptchaManager':
        """
        Get singleton instance.

        Args:
            headless: Run browsers in headless mode

        Returns:
            FlowCaptchaManager instance
        """
        if FlowCaptchaManager._instance is None:
            FlowCaptchaManager._instance = FlowCaptchaManager(headless=headless)
        return FlowCaptchaManager._instance

    @staticmethod
    def reset_instance():
        """Reset singleton instance."""
        if FlowCaptchaManager._instance is not None:
            FlowCaptchaManager._instance.stop()
            FlowCaptchaManager._instance = None

    def start(self, num_browsers: int = 2, wait_ready: bool = True, timeout: float = 120) -> bool:
        """
        Start service with N browsers.

        Args:
            num_browsers: Number of browser instances
            wait_ready: Wait until browsers are ready
            timeout: Timeout in seconds

        Returns:
            True if successful
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("[FlowCaptchaManager] Playwright not installed!")
            print("Run: pip install playwright && playwright install chromium")
            return False

        if self._initialized:
            print("[FlowCaptchaManager] Already running!")
            return True

        print(f"[FlowCaptchaManager] Starting {num_browsers} browser(s)...")

        # Create new event loop in separate thread
        ready_event = threading.Event()
        init_result = [False]

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def init_pool():
                self._pool = FlowCaptchaPool(num_browsers=num_browsers, headless=self.headless)
                result = await self._pool.initialize()
                init_result[0] = result
                ready_event.set()

                # Keep loop running
                while self._initialized:
                    await asyncio.sleep(0.1)

            self._loop.run_until_complete(init_pool())

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        if wait_ready:
            ready_event.wait(timeout=timeout)
            self._initialized = init_result[0]
            if self._initialized:
                print("[FlowCaptchaManager] Ready!")
            else:
                print("[FlowCaptchaManager] Initialization failed!")
            return self._initialized

        self._initialized = True
        return True

    def get_token_sync(self, project_id: str, timeout: float = 60) -> Optional[str]:
        """
        Get token (blocking).

        Args:
            project_id: Google Labs Flow project ID
            timeout: Timeout in seconds

        Returns:
            Token string or None
        """
        if not self._initialized or not self._pool or not self._loop:
            print("[FlowCaptchaManager] Not started!")
            return None

        result = [None]
        done_event = threading.Event()

        async def _get():
            result[0] = await self._pool.get_token(project_id)
            done_event.set()

        asyncio.run_coroutine_threadsafe(_get(), self._loop)
        done_event.wait(timeout=timeout)

        return result[0]

    def report_success(self):
        """Report success from API."""
        if self._pool:
            self._pool.report_success()

    def report_failure(self, reason: str = ""):
        """Report failure from API."""
        if self._pool:
            self._pool.report_failure(reason)

    def get_status(self) -> Dict:
        """Get status."""
        if self._pool:
            return self._pool.get_status()
        return {"initialized": False}

    def stop(self):
        """Stop service."""
        print("[FlowCaptchaManager] Stopping...")
        self._initialized = False

        if self._loop and self._pool:
            async def _close():
                await self._pool.close()

            future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
            try:
                future.result(timeout=10)
            except:
                pass

        self._pool = None
        print("[FlowCaptchaManager] Stopped!")

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._initialized

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def get_token_sync(project_id: str, headless: bool = True) -> Optional[str]:
    """
    Simple sync API - creates new browser each time.

    Args:
        project_id: Google Labs Flow project ID
        headless: Run browser in headless mode

    Returns:
        Token string or None
    """
    async def _get():
        browser = BrowserInstance(0, headless)
        try:
            if await browser.initialize():
                token, _ = await browser.get_token(project_id)
                return token
            return None
        finally:
            await browser.close()

    return asyncio.run(_get())
