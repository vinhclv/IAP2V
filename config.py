# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.join(BASE_DIR, "profiles")
DEFAULT_INPUT = os.path.join(BASE_DIR, "regen")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "assets")

# Các cấu hình mặc định khác nếu cần
MAX_RETRIES = 30

ORBITA_PATH = os.path.join(BASE_DIR, "orbita-browser-141", "chrome.exe")
DRIVER_PATH = os.path.join(BASE_DIR, "orbita-browser-141", "chromedriver.exe")