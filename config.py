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



DEFAULT_CONFIG_DATA = {
    "system": {
        "max_threads": 3,
        "loop_limit": 5,
        "max_retries": 30,
        "wait_time": 5
    },
    "urls": {
        "gemini_url": "https://gemini.google.com",
        "videofx_url": "https://labs.google/fx/tools/video-fx"
    }
}

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

def load_config():
    """
    Đọc file settings.json và merge với cấu hình mặc định.
    Đảm bảo luôn trả về đủ key để code không bị lỗi KeyError.
    """
    # Tạo bản sao sâu (Deep Copy) từ mặc định để làm gốc
    config = json.loads(json.dumps(DEFAULT_CONFIG_DATA))

    # Nếu file không tồn tại -> Trả về mặc định
    if not os.path.exists(SETTINGS_FILE):
        return config

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # MERGE THÔNG MINH:
        # Chỉ cập nhật những key có trong file json, giữ nguyên các key còn thiếu từ default.
        # Điều này giúp file json cũ vẫn chạy được với code mới nếu bạn thêm tính năng.
        
        if "system" in saved_data:
            # Update đè các key trong system (vd: max_threads)
            config["system"].update(saved_data["system"])
        
        if "urls" in saved_data:
            # Update đè các key trong urls
            config["urls"].update(saved_data["urls"])

    except Exception as e:
        print(f"⚠️ Lỗi đọc file config (Dùng mặc định): {e}")
        # Nếu file lỗi format JSON, code sẽ tự dùng bản default đã init ở trên

    return config