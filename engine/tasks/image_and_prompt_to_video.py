import os
import time
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random
from selenium.webdriver.common.action_chains import ActionChains 

def robust_click(driver, element):
    try:
        element.click()
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            print(f"❌ Click thất bại: {e}")
            return False

def human_click_offset(driver, element):
    width = element.size['width']
    height = element.size['height']
    # Click ngẫu nhiên trong phạm vi của nút, không click vào tâm
    offset_x = random.randint(-int(width/4), int(width/4))
    offset_y = random.randint(-int(height/4), int(height/4))

    actions = ActionChains(driver)
    actions.move_to_element_with_offset(element, offset_x, offset_y)
    actions.pause(random.uniform(0.2, 0.5))
    actions.click().perform()
def human_type(driver, element, text):
    element.click()
    time.sleep(random.uniform(0.5, 1.0))

    # Chiến thuật: GÕ THEO CỤM (CHUNKING)
    # Giúp giảm 90% độ trễ giao tiếp giữa Python và Trình duyệt
    
    idx = 0
    while idx < len(text):
        # 1. Lấy một cụm ký tự ngẫu nhiên (từ 4 đến 10 ký tự)
        # Giống như người ta gõ nhanh một từ hoặc một cụm từ
        chunk_size = random.randint(4, 10)
        chunk = text[idx:idx+chunk_size]
        
        # 2. Gửi cả cụm đi một lúc
        element.send_keys(chunk)
        
        idx += chunk_size
        
        # 3. Delay cực ngắn giữa các cụm (0.05 - 0.15s)
        # Tốc độ này tương đương người gõ máy tốc ký
        time.sleep(random.uniform(0.05, 0.15))
        
        # 4. Thỉnh thoảng dừng lại xíu (ngẫu nhiên 10% cơ hội) như đang suy nghĩ
        if random.random() < 0.1:
            time.sleep(random.uniform(0.2, 0.5))

    time.sleep(random.uniform(0.5, 1.0))
# --- HÀM 2: CẤU HÌNH GIAO DIỆN (FULL OPTION: MODE + RATIO + QUANTITY) ---
def setup_video_creation_mode(driver):
    wait = WebDriverWait(driver, 5) 
    print("⚙️ Đang cấu hình giao diện (Mode -> Landscape -> Qty=1)...")

    try:
        # 1. Click nút "Tạo dự án"
        try:
            create_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div/div/button")))
            create_btn.click()
            time.sleep(random.uniform(0.5, 1.5))
        except:
            print("⚠️ Bỏ qua 'Tạo dự án'.")

        # 2. Chuyển sang tab "Video"
        try:
            video_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div/div[1]/button[1]")))
            video_tab.click()
            time.sleep(1)
        except:
            print("⚠️ Bỏ qua Tab Video.")

        # 3. Mở Dropdown chọn chế độ
        try:
            mode_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[1]/div[1]/button")))
            human_click_offset(driver, mode_dropdown)
            time.sleep(random.uniform(1, 2))

            # 4. Chọn "Tạo video từ các thành phần"
            print("🎯 Chọn chế độ Thành phần...")
            component_icon = wait.until(EC.presence_of_element_located((
                By.XPATH, "/html/body/div[3]/div/div/div[3]/div/i"
            )))
            driver.execute_script("arguments[0].click();", component_icon)
            print("✅ Đã chọn chế độ: Tạo video từ các thành phần")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"⚠️ Lỗi chọn chế độ: {e}")

        # 5. Mở Cấu hình (Settings)
        try:
            settings_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[1]/div[2]/button[2]")))
            human_click_offset(driver, settings_btn)
            time.sleep(random.uniform(1, 2)) # Chờ bảng settings hiện ra

            # --- MỚI: CẤU HÌNH KHỔ NGANG (LANDSCAPE) ---
            print("🎯 Cấu hình Khổ ngang (Landscape)...")
            # Click Dropdown Tỷ lệ khung hình (Nút bên trái)
            ratio_dropdown = wait.until(EC.element_to_be_clickable((
                By.XPATH, "/html/body/div[3]/div/div/div[1]/div[1]/button"
            )))
            human_click_offset(driver, ratio_dropdown)
            time.sleep(random.uniform(1, 2)) # Chờ menu tỷ lệ nảy ra ở div[4]

            # Chọn Option (Khổ ngang)
            landscape_option = wait.until(EC.presence_of_element_located((
                By.XPATH, "/html/body/div[4]/div/div/div[1]/div/span"
            )))
            driver.execute_script("arguments[0].click();", landscape_option)
            print("✅ Đã chọn Khổ ngang")
            time.sleep(1) # Chờ menu đóng lại
            
            # --- CẤU HÌNH SỐ LƯỢNG = 1 ---
            print("🎯 Cấu hình Số lượng = 1...")
            # Click Dropdown Số lượng (Nút bên phải)
            quantity_dropdown = wait.until(EC.element_to_be_clickable((
                By.XPATH, "/html/body/div[3]/div/div/div[1]/div[2]/button"
            )))
            human_click_offset(driver, quantity_dropdown)
            time.sleep(random.uniform(1, 2)) 

            # Chọn Option 1
            # (Lưu ý: Bạn dùng chung XPath với landscape vì nó đều là mục đầu tiên trong list)
            option_one = wait.until(EC.presence_of_element_located((
                By.XPATH, "/html/body/div[4]/div/div/div[1]/div/span"
            )))
            driver.execute_script("arguments[0].click();", option_one)
            print("✅ Đã cấu hình Số lượng: 1")
            
            # Đóng bảng Settings
            driver.execute_script("document.body.click();")
            
        except Exception as e:
            print(f"⚠️ Lỗi cấu hình Settings (Ratio/Quantity): {e}")

        return True
    except Exception as e:
        print(f"❌ Lỗi cấu hình tổng: {e}")
        return True

def upload_stealth(driver, file_path):
    try:
        wait = WebDriverWait(driver, 15)
        abs_path = os.path.abspath(file_path)
        
        # 1. Click nút "Thêm" / "Upload" để kích hoạt input file (nếu cần)
        # Trong VideoFX, nút này thường là dấu + to hoặc chữ "Thêm hình ảnh/video"
        try:
            upload_trigger = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[1]/div/div/button")
            if upload_trigger.is_displayed():
                upload_trigger.click()
                time.sleep(random.uniform(1, 2))
        except:
            pass # Có thể input đã có sẵn trong DOM

        # 2. Tìm thẻ input type=file
        # Thử tìm input file. Nếu nó ẩn, Selenium vẫn find_element được nếu nó tồn tại trong DOM.
        try:
            file_inputs = driver.find_elements(By.XPATH, "/html/body/div[1]/div[3]/div/div/input")
            if not file_inputs:
                print("❌ Không tìm thấy thẻ <input type='file'> nào trong DOM.")
                return False
            
            # Lấy input đầu tiên hoặc input đang hiển thị (nếu có)
            file_input = file_inputs[0] 
            

            # 4. Gửi đường dẫn file
            file_input.send_keys(abs_path)
            
            # 5. Kích hoạt sự kiện change
            driver.execute_script("""
                var input = arguments[0];
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('input', { bubbles: true }));
            """, file_input)
            
            print(f"✅ Đã upload thành công: {os.path.basename(file_path)}")
            time.sleep(random.uniform(3, 5)) 
            
            cut_and_save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[3]/div[3]/div/div/div[2]/div/button[3]")))
            
            # Click nút
            human_click_offset(driver, cut_and_save_button)
            print(f"✅ Đã bấm nút Lưu ảnh: {os.path.basename(file_path)}")
            
            return True
        except Exception as e:
            print(f"❌ Lỗi khi tương tác với input file: {e}")
            return False

    except Exception as e:
        print(f"❌ Lỗi Upload tổng quát {os.path.basename(file_path)}: {e}")
        return False 
# --- HÀM 3: TẢI VIDEO (GIỮ NGUYÊN) ---
def download_blob_video(driver, video_element, save_path):
    try:
        video_src = video_element.get_attribute("src")
        if not video_src: return False

        print("📥 Đang tải video blob về máy...")
        
        # Dùng script async để tải blob
        base64_data = driver.execute_async_script("""
            var uri = arguments[0];
            var callback = arguments[1];
            var xhr = new XMLHttpRequest();
            xhr.responseType = 'blob';
            xhr.onload = function() {
                var reader = new FileReader();
                reader.onloadend = function() {
                    callback(reader.result);
                }
                reader.readAsDataURL(xhr.response);
            };
            xhr.onerror = function() {
                callback(null);
            };
            xhr.open('GET', uri);
            xhr.send();
        """, video_src)

        if base64_data:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(base64_data))
            return True
        return False
    except Exception as e:
        print(f"❌ Lỗi download blob: {e}")
        return False

def process_video_batch(driver, file_batch, output_folder, log_callback=print):
    # Khởi tạo môi trường
    setup_video_creation_mode(driver)
    wait = WebDriverWait(driver, 15)
    tasks = {} 
    
    # [MỚI 1] Tập hợp chứa các URL video đã tải trong phiên này
    downloaded_urls = set() 

    # --- GIAI ĐOẠN 1: SUBMIT (Giữ nguyên) ---
    for index, item_path in enumerate(file_batch):
        # ... (Phần code submit giữ nguyên không đổi) ...
        # (Copy lại phần submit của bạn vào đây)
        file_name = os.path.basename(item_path)
        full_name_id = os.path.splitext(file_name)[0]
        parent_dir = os.path.dirname(item_path)
        video_dir = os.path.join(parent_dir, "video")
        save_path = os.path.join(video_dir, f"{full_name_id}_8s.mp4")
        
        if os.path.exists(save_path):
            log_callback(f"⏭️ Bỏ qua: {full_name_id}")
            continue

        id_tag = f"||{full_name_id}||"
        tasks[full_name_id] = {
            "save_path": save_path,
            "id_tag": id_tag,
            "done": False,
            "file_path": item_path
        }
        
        try:
            if not upload_stealth(driver, item_path): continue
            textbox = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/textarea")))
            prompt_path = os.path.join(parent_dir, "prompt.txt")
            base_prompt = open(prompt_path, "r", encoding="utf-8").read().strip() if os.path.exists(prompt_path) else "Cinematic"
            human_type(driver, textbox, f"{id_tag} {base_prompt}")
            xpath_btn = "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[2]/button[2]"
            wait_btn = WebDriverWait(driver, 20)
            btn_gen = wait_btn.until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
            time.sleep(random.uniform(0.5, 1.0))
            human_click_offset(driver, btn_gen)
            log_callback(f"📤 Đã gửi: {full_name_id}")
            time.sleep(random.uniform(5, 8)) 
        except Exception as e:
            log_callback(f"❌ Lỗi gửi {full_name_id}: {e}")
            tasks.pop(full_name_id, None)

    # --- GIAI ĐOẠN 2: COLLECT (CẬP NHẬT LOGIC URL CHECK) ---
    if not tasks: return False, file_batch

    log_callback(f"⏳ Chờ render {len(tasks)} video...")
    start_time = time.time()
    
    while time.time() - start_time < 150:
        active_tasks = [uid for uid, info in tasks.items() if not info["done"]]
        if not active_tasks: 
            log_callback("✅ Tất cả video đã tải xong!")
            break

        for uid in active_tasks:
            info = tasks[uid]
            try:

                xpath_check = f"//*[contains(text(), '{info['id_tag']}')]/ancestor::div[@data-index][1]//video"

                videos = driver.find_elements(By.XPATH, xpath_check)
                
                if videos:
                    video_el = videos[0]
                    current_src = video_el.get_attribute("src")
                    
                    # Nếu src rỗng hoặc null -> Bỏ qua
                    if not current_src or current_src == "null":
                        continue

                    # [QUAN TRỌNG] Kiểm tra xem URL này đã tải chưa
                    if current_src in downloaded_urls:
                        continue 

                    # Kiểm tra readyState
                    rs = driver.execute_script("return arguments[0].readyState;", video_el)
                    
                    if rs == 4: # Video đã tải xong (HAVE_ENOUGH_DATA)
                        os.makedirs(os.path.dirname(info["save_path"]), exist_ok=True)
                        log_callback(f"💾 Phát hiện Video mới: {uid}")
                        
                        if download_blob_video(driver, video_el, info["save_path"]):
                            if os.path.exists(info["save_path"]) and os.path.getsize(info["save_path"]) > 0:
                                log_callback(f"✅ Thành công: {uid}")
                                info["done"] = True
                                
                                # Thêm vào danh sách đen để không tải lại
                                downloaded_urls.add(current_src)
                            else:
                                log_callback(f"⚠️ Lỗi 0KB: {uid}")
                    
                    elif rs == 0: 
                        # Kích hoạt video ngủ (nếu cần)
                        driver.execute_script("arguments[0].play().then(()=>arguments[0].pause()).catch(()=>{});", video_el)
                        
            except Exception as e:
                pass
        time.sleep(3) 

    # --- TỔNG KẾT ---
    failed = [v["file_path"] for k, v in tasks.items() if not v["done"]]
    return len(failed) == 0, failed
