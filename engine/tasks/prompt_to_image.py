import os
import time
import requests
import base64
from PIL import Image # Thêm thư viện này
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def process_prompt_to_image(driver, item, log_callback=print):
    try:
        wait = WebDriverWait(driver, 45)
        stt = item['id']
        prompt_text = item['prompt']
        save_path = item['save_path']
        output_folder = item['output_folder']

        os.makedirs(output_folder, exist_ok=True)

        # --- 1. ĐỊNH NGHĨA XPATH VÀ ĐẾM ẢNH CŨ ---
        IMG_XPATH = "//generated-image//single-image//img"
        old_images = driver.find_elements(By.XPATH, IMG_XPATH)
        old_count = len(old_images)

        # --- 1.1. CHỌN MODEL PRO (Giữ nguyên logic của bạn) ---
        # Lưu ý: Nên đưa phần này ra ngoài loop ở handler.py như đã thảo luận
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

        # --- 2. NHẬP PROMPT VÀ GỬI ---
        input_box = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))

        driver.execute_script("arguments[0].textContent = arguments[1];", input_box, prompt_text)
        input_box.send_keys(" ") 
        time.sleep(1)
        
        send_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send') or .//mat-icon[text()='send']]")
        driver.execute_script("arguments[0].click();", send_button)

        # --- 3. ĐỢI ẢNH MỚI ---
        log_callback(f"⏳ Đang tạo ảnh STT {stt}...")
        try:
            wait.until(lambda d: len(d.find_elements(By.XPATH, IMG_XPATH)) > old_count)
        except:
            log_callback(f"❌ Timeout: Không thấy ảnh mới cho STT {stt}.")
            return False

        time.sleep(6)

        # --- 4. LẤY ẢNH MỚI NHẤT ---
        current_images = driver.find_elements(By.XPATH, IMG_XPATH)
        new_img_element = current_images[-1]
        img_url = new_img_element.get_attribute("src")

        # --- 5. TẢI ẢNH VỀ ---
        # (Logic tải ảnh giữ nguyên như của bạn...)
        download_success = False
        if img_url.startswith("data:image"):
            _, encoded = img_url.split(",", 1)
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(encoded))
            download_success = True
        else:
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            user_agent = driver.execute_script("return navigator.userAgent;")
            headers = {
                "User-Agent": user_agent,
                "Referer": "https://gemini.google.com/",
            }
            response = session.get(img_url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                download_success = True

        if not download_success: return False

        # --- 6. KIỂM TRA TỈ LỆ ẢNH (LOGIC MỚI) ---
        try:
            with Image.open(save_path) as img:
                width, height = img.size
                aspect_ratio = width / height
                # 16/9 = 1.777. Cho phép sai số nhỏ (1.7 đến 1.8)
                if aspect_ratio < 1.7 or aspect_ratio > 1.85:
                    log_callback(f"⚠️ STT {stt} sai tỉ lệ ({width}x{height} - {aspect_ratio:.2f}). Đang xóa và retry...")
                    img.close() # Đóng file trước khi xóa
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    return False # Trả về False để vòng lặp ngoài xử lý lại
                
                log_callback(f"✅ Ảnh chuẩn 16:9 ({width}x{height})")
        except Exception as e:
            log_callback(f"❌ Lỗi kiểm tra ảnh: {e}")
            return False

        log_callback(f"✅ Đã tải xong ảnh: {os.path.basename(save_path)}")
        return True

    except Exception as e:
        log_callback(f"❌ Lỗi xử lý STT {item.get('id')}: {str(e)}")
        return False