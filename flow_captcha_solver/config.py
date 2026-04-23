# -*- coding: utf-8 -*-
"""
Configuration constants for Flow Captcha Solver
"""

# Timeout (milliseconds)
TIMEOUT_PAGE_LOAD = 20000
TIMEOUT_DOM_LOAD = 8000
TIMEOUT_RECAPTCHA_READY = 20000
TIMEOUT_READY_CALLBACK = 30000

# Retry and auto-reset
MAX_RETRIES = 2
RETRY_WAIT = 1
MAX_CONSECUTIVE_FAILURES = 3

# Delay between requests (seconds)
MIN_REQUEST_DELAY = 0.5
MAX_REQUEST_DELAY = 1.5

# reCAPTCHA config for Google Labs Flow
RECAPTCHA_WEBSITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
RECAPTCHA_ACTION = "FLOW_GENERATION"
RECAPTCHA_SCRIPT_URL = f"https://www.google.com/recaptcha/api.js?render={RECAPTCHA_WEBSITE_KEY}"

# Browser args
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-infobars',
    '--disable-extensions',
    '--disable-gpu',
    '--disable-software-rasterizer',
    '--ignore-certificate-errors',
    '--window-size=1920,1080',
    '--disable-notifications',
    '--disable-popup-blocking',
    '--disable-translate',
    '--disable-background-networking',
    '--disable-sync',
    '--disable-default-apps',
    '--mute-audio',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--disable-background-timer-throttling',
]

# Random User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
]

# Random Viewports
VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1680, 'height': 1050},
    {'width': 1600, 'height': 900},
    {'width': 1440, 'height': 900},
]

# Random Timezones
TIMEZONES = [
    'America/New_York',
    'America/Chicago',
    'America/Los_Angeles',
    'Europe/London',
]
