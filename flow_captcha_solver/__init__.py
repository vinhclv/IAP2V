# -*- coding: utf-8 -*-
"""
Flow Captcha Solver - reCAPTCHA solver for Google Labs Flow

A Python library to solve reCAPTCHA v3 for Google Labs Flow projects.

Features:
    - Multi-browser pool with auto-switching
    - Auto-reset on consecutive failures
    - Random fingerprint on each browser reset
    - Both sync and async APIs

Installation:
    pip install flow-captcha-solver
    playwright install chromium

Quick Start:
    # Simple usage (sync)
    from flow_captcha_solver import get_token_sync
    token = get_token_sync("your-project-id")

    # With manager (recommended for multiple requests)
    from flow_captcha_solver import FlowCaptchaManager

    manager = FlowCaptchaManager.get_instance()
    manager.start(num_browsers=2)

    token = manager.get_token_sync("your-project-id")
    if token:
        # Use token with API...
        manager.report_success()  # Reset failure counter
    else:
        manager.report_failure("Token failed")  # Increment counter

    manager.stop()

    # Async usage
    from flow_captcha_solver import FlowCaptchaPool

    async with FlowCaptchaPool(num_browsers=2) as pool:
        token = await pool.get_token("your-project-id")
"""

__version__ = "1.0.1"
__author__ = "Nguyen Van Son"
__email__ = "sondev2k@gmail.com"

from .browser import BrowserInstance, PLAYWRIGHT_AVAILABLE
from .pool import FlowCaptchaPool
from .manager import FlowCaptchaManager, get_token_sync
from .config import (
    MAX_CONSECUTIVE_FAILURES,
    RECAPTCHA_WEBSITE_KEY,
    RECAPTCHA_ACTION
)

# Aliases for convenience
FlowCaptchaSolver = BrowserInstance
get_flow_token_sync = get_token_sync

__all__ = [
    # Main classes
    "FlowCaptchaManager",
    "FlowCaptchaPool",
    "BrowserInstance",

    # Simple functions
    "get_token_sync",
    "get_flow_token_sync",

    # Aliases
    "FlowCaptchaSolver",

    # Constants
    "MAX_CONSECUTIVE_FAILURES",
    "RECAPTCHA_WEBSITE_KEY",
    "RECAPTCHA_ACTION",
    "PLAYWRIGHT_AVAILABLE",

    # Version
    "__version__",
]
