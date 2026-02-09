import os
import time
import requests
import base64
from PIL import Image  # Cần cài: pip install Pillow
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def process_srt_item_to_image(driver, item, log_callback=print):
    """
    Hàm Core riêng biệt cho chức năng SRT -> Image.
    Nhận text từ SRT, tự động thêm style điện ảnh và vẽ ảnh.
    """
    try:
        wait = WebDriverWait(driver, 45)
        
        # Giải nén dữ liệu
        stt = item['id']
        raw_text = item['prompt'] # Text gốc của sub
        save_path = item['save_path']
        output_folder = item['output_folder']

        os.makedirs(output_folder, exist_ok=True)

        # --- 1. PROMPT ENGINEERING (QUAN TRỌNG) ---
        final_prompt = f"Illustrate the following sentence with a suitable image: {raw_text}"

        # --- 2. ĐẾM ẢNH CŨ ---
        # XPath này chỉ lấy ảnh do AI sinh ra, bỏ qua avatar
        IMG_XPATH = "//generated-image//single-image//img"
        old_images = driver.find_elements(By.XPATH, IMG_XPATH)
        old_count = len(old_images)

        # --- 2. CHỌN MODEL PRO ---
        try:
            xpath_model_menu = "//bard-mode-switcher//button"
            btn_model_menu = wait.until(EC.presence_of_element_located((By.XPATH, xpath_model_menu)))
            driver.execute_script("arguments[0].click();", btn_model_menu)
            time.sleep(1.5)
            xpath_pro = "/html/body/div[8]/div/div/div/div/div/button[3]"
            btn_pro = wait.until(EC.presence_of_element_located((By.XPATH, xpath_pro)))
            driver.execute_script("arguments[0].click();", btn_pro)
            time.sleep(2)
        except: pass

        # --- 3. GỬI PROMPT ---
        try:
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))

            driver.execute_script("arguments[0].textContent = arguments[1];", input_box, final_prompt)
            time.sleep(0.5)
            
            # Click nút gửi
            send_button = driver.find_element(By.XPATH, "//button[contains(@class, 'send-button')]")
            driver.execute_script("arguments[0].click();", send_button)
        except Exception as e:
            log_callback(f"❌ Lỗi nhập liệu STT {stt}: {e}")
            return False

        # --- 4. ĐỢI ẢNH MỚI (SMART WAIT) ---
        log_callback(f"⏳ Đang vẽ STT {stt}: {raw_text[:30]}...")
        try:
            # Chờ số lượng ảnh tăng lên
            wait.until(lambda d: len(d.find_elements(By.XPATH, IMG_XPATH)) > old_count)
        except:
            log_callback(f"❌ Timeout: Gemini không trả ra ảnh cho STT {stt}.")
            return False

        # Đợi thêm để ảnh load full resolution (tránh lấy thumbnail mờ)
        time.sleep(6)

        # --- 5. LẤY URL ẢNH MỚI NHẤT ---
        current_images = driver.find_elements(By.XPATH, IMG_XPATH)
        if not current_images: return False
        
        new_img_element = current_images[-1]
        img_url = new_img_element.get_attribute("src")

        # --- 6. TẢI ẢNH VỀ ---
        download_success = False
        
        if img_url.startswith("data:image"):
            # Trường hợp Base64
            try:
                _, encoded = img_url.split(",", 1)
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(encoded))
                download_success = True
            except Exception as e:
                log_callback(f"❌ Lỗi lưu Base64: {e}")
        else:
            # Trường hợp URL (HTTP)
            try:
                session = requests.Session()
                # Copy cookies để vượt qua authen của Google
                for cookie in driver.get_cookies():
                    session.cookies.set(cookie['name'], cookie['value'])
                
                headers = {
                    "User-Agent": driver.execute_script("return navigator.userAgent;"),
                    "Referer": "https://gemini.google.com/",
                }
                
                response = session.get(img_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    download_success = True
                else:
                    log_callback(f"❌ HTTP {response.status_code} khi tải ảnh.")
            except Exception as e:
                log_callback(f"❌ Lỗi tải URL: {e}")

        if not download_success: return False

        # --- 7. KIỂM TRA CHẤT LƯỢNG ẢNH (TỈ LỆ 16:9) ---
        try:
            with Image.open(save_path) as img:
                width, height = img.size
                if height == 0: raise ValueError("Height = 0")
                
                aspect_ratio = width / height
                # 16:9 = 1.777
                # Chấp nhận sai số từ 1.7 đến 1.85
                if aspect_ratio < 1.7 or aspect_ratio > 1.85:
                    log_callback(f"⚠️ Sai tỉ lệ ({width}x{height} - {aspect_ratio:.2f}). Đang xóa để retry...")
                    # Đóng file trước khi xóa (quan trọng trên Windows)
                    del img 
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    return False 
                
                # Kiểm tra thêm: Nếu ảnh quá nhỏ (VD: icon lỗi) -> Xóa
                if width < 500 or height < 300:
                    log_callback(f"⚠️ Ảnh quá nhỏ ({width}x{height}). Xóa...")
                    if os.path.exists(save_path): os.remove(save_path)
                    return False

                # log_callback(f"✅ Ảnh OK: {width}x{height}")
        except Exception as e:
            log_callback(f"⚠️ Lỗi check ảnh (Pillow): {e}")
            # Nếu lỗi mở file (file hỏng), return False để tải lại
            return False

        log_callback(f"✅ Hoàn thành STT {stt}")
        return True

    except Exception as e:
        log_callback(f"❌ Lỗi ngoại lệ STT {item.get('id')}: {str(e)}")
        return False