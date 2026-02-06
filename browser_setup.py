import os
import threading
import shutil # <--- [MỚI] Cần import cái này để xóa folder rác
import undetected_chromedriver as uc
import random 

ROOT_PATH = os.path.dirname(os.path.abspath(__file__)) 
ORBITA_PATH = os.path.join(ROOT_PATH, "orbita-browser-141", "chrome.exe")
DRIVER_PATH = os.path.join(ROOT_PATH, "orbita-browser-141", "chromedriver.exe")
DRIVER_INIT_LOCK = threading.Lock()
def clean_chrome_cache(profile_path):
    """
    Dọn dẹp triệt để rác, bao gồm cả Crashpad, File System và IndexedDB.
    """
    # 1. Các folder rác nằm ngay ngoài thư mục gốc profile (User Data)
    root_garbage = [
        "Crashpad",          # [QUAN TRỌNG] Nơi chứa file dump báo lỗi (rất nặng)
        "Safe Browsing",     # Dữ liệu check web độc hại (tải lại được)
        "GrShaderCache",     # Cache đồ họa
        "ShaderCache", 
    ]
    
    # 2. Các folder rác nằm trong thư mục Default (User Data/Default)
    default_dir = os.path.join(profile_path, "Default")
    
    default_garbage = [
        "Cache",
        "Code Cache",
        "GPUCache",
        "DawnCache",         # Cache WebGPU mới
        "Service Worker",    # [QUAN TRỌNG] Nơi lưu script chạy ngầm
        "File System",       # [QUAN TRỌNG] Nơi web app lưu video tạm
        "IndexedDB",         # [CẢNH BÁO] Lưu data web. Xóa cái này sạch nhất nhưng KÉM BỀN LOGOUT hơn. 
                             # Nếu bị logout, hãy comment dòng này lại.
        "Local Extension Settings", # Rác extension
        "Trace",             # Log trace
    ]

    # Các file rác lẻ tẻ
    files_to_delete = [
        "chrome_debug.log",  # Log debug (có thể lên tới vài GB)
    ]

    print(f"🧹 Bắt đầu dọn dẹp sâu profile: {os.path.basename(profile_path)}...")

    # Xóa folder ở root
    for folder in root_garbage:
        full_path = os.path.join(profile_path, folder)
        if os.path.exists(full_path):
            try:
                shutil.rmtree(full_path, ignore_errors=True)
            except: pass

    # Xóa folder trong Default
    for folder in default_garbage:
        full_path = os.path.join(default_dir, folder)
        if os.path.exists(full_path):
            try:
                shutil.rmtree(full_path, ignore_errors=True)
            except: pass

    # Xóa file lẻ
    for file in files_to_delete:
        full_path = os.path.join(profile_path, file)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except: pass

    print("✨ Đã dọn dẹp xong.")
def init_driver_from_profile(profile_folder_path, log_callback=print, download_dir=None):
    """
    Hàm khởi tạo Driver trực tiếp từ Folder Profile (Không cần JSON).
    """
    
    # 1. Xác định thư mục profile
    if not os.path.exists(profile_folder_path):
        os.makedirs(profile_folder_path, exist_ok=True)
        log_callback(f"⚠️ Folder chưa tồn tại, đã tạo mới: {profile_folder_path}")

    folder_name = os.path.basename(profile_folder_path)
    
    # --- [MỚI] GỌI HÀM DỌN DẸP TRƯỚC KHI MỞ ---
    log_callback(f"🧹 Đang dọn dẹp Cache cũ cho profile: {folder_name}...")
    clean_chrome_cache(profile_folder_path)

    log_callback(f"🚀 Khởi động Orbita Profile: {folder_name}")

    # 2. CẤU HÌNH ORBITA OPTIONS
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_folder_path}")
    options.add_argument(f"--profile-directory=Default")
    
    # --- Cấu hình tối ưu & CHẶN CACHE ---
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument('--no-first-run')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-popup-blocking')
    
    # --- [MỚI] CÁC DÒNG QUAN TRỌNG ĐỂ KHÔNG LƯU CACHE MỚI ---
    options.add_argument("--disk-cache-size=1")              # Giới hạn cache ổ cứng = 1 byte (Tắt)
    options.add_argument("--media-cache-size=1")             # Không cache video (Quan trọng với tool video)
    options.add_argument("--disable-application-cache")      # Tắt AppCache
    options.add_argument("--disable-gpu-shader-disk-cache")  # Không lưu shader GPU
    options.add_argument("--ash-no-nudges")                  # Tắt vài cái popup rác của Chrome
    
    options.page_load_strategy = 'eager'

    # --- Cấu hình Download (Nếu có) ---
    if download_dir:
        if not os.path.exists(download_dir): os.makedirs(download_dir)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0,
            
            # [MỚI] Thêm prefs để chặn cache cấp độ trình duyệt
            "browser.cache.disk.enable": False,
            "browser.cache.memory.enable": False,
            "browser.cache.offline.enable": False,
            "network.http.use-cache": False,
        }
        options.add_experimental_option("prefs", prefs)

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