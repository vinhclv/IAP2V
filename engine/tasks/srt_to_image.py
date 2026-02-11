import os
import time
import requests
import base64
from PIL import Image  # Cần cài: pip install Pillow
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import glob
import shutil
def download_via_native_button(driver, save_path, download_dir_chrome):
    """ Logic: Dọn file rác -> Bấm tải -> Lấy file -> Move. """
    try:
        wait = WebDriverWait(driver, 15)
        
        # --- 0. DỌN SẠCH FILE (AN TOÀN HƠN RMTREE) ---
        if os.path.exists(download_dir_chrome):
            # Xóa từng file bên trong thay vì xóa cả folder (Tránh lỗi Access Denied)
            for f in glob.glob(os.path.join(download_dir_chrome, "*")):
                try: os.remove(f) 
                except: pass # Kệ file đang bị lock
        else:
            os.makedirs(download_dir_chrome, exist_ok=True)

        # --- 1. CLICK DOWNLOAD ---
        containers = driver.find_elements(By.XPATH, "//generated-image")
        if not containers: return False
        
        target = containers[-1]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
        ActionChains(driver).move_to_element(target).perform()
        time.sleep(1)

        xpath_btn = ".//button[@data-test-id='download-generated-image-button' or .//mat-icon[contains(text(), 'download')]]"
        try:
            btn = WebDriverWait(target, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
            driver.execute_script("arguments[0].click();", btn)
            print("🖱️ Đã click nút Download.")
        except:
            print("⚠️ Không click được nút.")
            return False

        # --- 2. CHỜ FILE (KIÊN NHẪN) ---
        start_time, downloaded_file = time.time(), None
        
        # Giai đoạn 1: Chờ file xuất hiện (max 10s)
        while time.time() - start_time < 60:
            if glob.glob(os.path.join(download_dir_chrome, "*")): break
            time.sleep(0.5)
            
        # Giai đoạn 2: Chờ tải xong (max 30s)
        start_time = time.time()
        while time.time() - start_time < 50:
            # List comprehension lọc file ngon
            files = [f for f in glob.glob(os.path.join(download_dir_chrome, "*")) 
                     if not f.endswith(('.crdownload', '.tmp'))]
            
            # Check size > 0
            if files:
                try:
                    if os.path.getsize(files[0]) > 0:
                        downloaded_file = files[0]
                        break
                except: pass
            time.sleep(1)

        if not downloaded_file:
            print("❌ Timeout: Không tải được file.")
            return False

        # --- 3. MOVE & RENAME (AN TOÀN) ---
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Tự động lấy đuôi file nếu save_path thiếu
        _, ext = os.path.splitext(save_path)
        if not ext:
            save_path += os.path.splitext(downloaded_file)[1] or ".jpg"

        # Thử Move (Retry 3 lần nếu bị Windows Lock)
        for _ in range(3):
            try:
                if os.path.exists(save_path): os.remove(save_path)
                shutil.move(downloaded_file, save_path)
                print(f"✅ Đã Move: {os.path.basename(save_path)}")
                return True
            except Exception as e:
                time.sleep(1) # Chờ 1s rồi thử lại
        
        print("❌ Lỗi không move được file (đang bị lock).")
        return False

    except Exception as e:
        print(f"⚠️ Lỗi: {e}")
        return False     

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
        final_prompt = f"Follow the structured GEM process. Create a Surrealist digital painting that illustrates the following quote (do not include any text), featuring white subjects on a black background: {raw_text}"

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

        time.sleep(3)

        if  download_via_native_button(driver, save_path, driver.my_download_dir) == False:
            log_callback("Lỗi tải về:", stt)
            return False

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