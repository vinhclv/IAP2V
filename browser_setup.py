import os
import threading
import undetected_chromedriver as uc
import random # Để fake user-agent nếu cần

ROOT_PATH = os.path.dirname(os.path.abspath(__file__)) 
ORBITA_PATH = os.path.join(ROOT_PATH, "orbita-browser-141", "chrome.exe")
DRIVER_PATH = os.path.join(ROOT_PATH, "orbita-browser-141", "chromedriver.exe")
DRIVER_INIT_LOCK = threading.Lock()

def init_driver_from_profile(profile_folder_path, log_callback=print, download_dir=None):
    """
    Hàm khởi tạo Driver trực tiếp từ Folder Profile (Không cần JSON).
    """
    
    # 1. Xác định thư mục profile
    # Giả sử profile_folder_path chính là folder chứa dữ liệu User Data
    if not os.path.exists(profile_folder_path):
        os.makedirs(profile_folder_path, exist_ok=True)
        log_callback(f"⚠️ Folder chưa tồn tại, đã tạo mới: {profile_folder_path}")

    folder_name = os.path.basename(profile_folder_path)
    log_callback(f"🚀 Khởi động Orbita Profile: {folder_name}")

    # 2. CẤU HÌNH ORBITA OPTIONS
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_folder_path}")
    options.add_argument(f"--profile-directory=Default")
    
    # --- Cấu hình tối ưu ---
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument('--no-first-run')
    # options.add_argument('--disable-gpu') # Bật nếu cần tiết kiệm GPU
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-popup-blocking')
    options.page_load_strategy = 'eager'

    # --- Cấu hình Download (Nếu có) ---
    if download_dir:
        if not os.path.exists(download_dir): os.makedirs(download_dir)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0
        }
        options.add_experimental_option("prefs", prefs)

    # --- LƯU Ý VỀ PROXY ---
    # Vì bỏ file JSON, code không biết Proxy của profile này là gì.
    # Nếu profile này đã được login và lưu proxy vào extension từ trước -> OK.
    # Nếu chưa, bạn cần cơ chế khác để nạp proxy (ví dụ file proxy.txt riêng).
    # Hiện tại code sẽ chạy Direct (IP thật của máy).

    # 3. KHỞI TẠO DRIVER
    with DRIVER_INIT_LOCK:
        try:
            driver = uc.Chrome(
                options=options,
                browser_executable_path=ORBITA_PATH,
                driver_executable_path=DRIVER_PATH,
                use_subprocess=True,
                headless=False,
            )
            return driver
        except Exception as e:
            log_callback(f"❌ Lỗi khởi tạo Chrome ({folder_name}): {e}")
            return None