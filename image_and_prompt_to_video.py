import os
import time
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random
from selenium.webdriver.common.action_chains import ActionChains # <--- Nhớ thêm import này
# --- HÀM 1: ROBUST CLICK (Ưu tiên JS Click nếu Click thường tạch) ---

# --- HÀM 1: ROBUST CLICK (BẤT TỬ) ---
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
            robust_click(driver, mode_dropdown)
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
            robust_click(driver, settings_btn)
            time.sleep(random.uniform(1, 2)) # Chờ bảng settings hiện ra

            # --- MỚI: CẤU HÌNH KHỔ NGANG (LANDSCAPE) ---
            print("🎯 Cấu hình Khổ ngang (Landscape)...")
            # Click Dropdown Tỷ lệ khung hình (Nút bên trái)
            ratio_dropdown = wait.until(EC.element_to_be_clickable((
                By.XPATH, "/html/body/div[3]/div/div/div[1]/div[1]/button"
            )))
            robust_click(driver, ratio_dropdown)
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
            robust_click(driver, quantity_dropdown)
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
            robust_click(driver, cut_and_save_button)
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
    time.sleep(4)
    # 1. Cấu hình giao diện một lần cho cả batch
    setup_video_creation_mode(driver)
    
    # [FIX LỖI] Khai báo wait
    wait = WebDriverWait(driver, 15)
    
    tasks = {} # Sổ theo dõi
    
    # --- GIAI ĐOẠN 1: SUBMIT (GỬI LỆNH LIÊN TỤC) ---
    log_callback(f"🚀 Bắt đầu gửi Batch gồm {len(file_batch)} file...")
    
    for index, item_path in enumerate(file_batch):
        file_name = os.path.basename(item_path)
        name_no_ext = os.path.splitext(file_name)[0]
        
        # === [LOGIC MỚI] TÍNH TOÁN ĐƯỜNG DẪN TRƯỚC ===
        # 1. Lấy thư mục cha của file ảnh
        parent_dir = os.path.dirname(item_path)
        
        # 2. Định nghĩa thư mục video nằm trong đó
        video_output_dir = os.path.join(parent_dir, "video")
        
        # 3. Định nghĩa tên file output (8s)
        final_video_name = f"{name_no_ext}_8s.mp4"
        save_full_path = os.path.join(video_output_dir, final_video_name)
        print(f"🚀 Đang gửi: {save_full_path}...")
        # 4. Kiểm tra tồn tại -> SKIP nếu đã có
        if os.path.exists(save_full_path):
            log_callback(f"⏭️ Đã tồn tại: {final_video_name} -> Bỏ qua.")
            continue # Nhảy sang file tiếp theo, không upload nữa
        
        # Tạo ID
        short_id = f"ID_{int(time.time())}_{index}"
        
        # Đọc prompt
        prompt_path = os.path.join(os.path.dirname(item_path), "prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f: base_prompt = f.read().strip()
        else:
            base_prompt = "Cinematic video, high quality"

        # [QUAN TRỌNG] Tiêm ID vào ĐẦU Prompt (để tránh bị cắt)
        injected_prompt = f"||{short_id}|| {base_prompt}"
        
        # Lưu tasks (Lưu kèm đường dẫn save_full_path đã tính ở trên)
        tasks[short_id] = {
            "file_name": file_name,
            "save_path_final": save_full_path, # <--- Lưu đường dẫn đích vào đây
            "done": False,
            "id_tag": f"||{short_id}||",
            "full_input_path": item_path # Lưu lại để trả về nếu lỗi
        }
        
        log_callback(f"📤 [{index+1}/{len(file_batch)}] Đang gửi: {file_name}...")

        try:
            # 1. Upload ảnh
            if not upload_stealth(driver, item_path):
                log_callback(f"❌ Upload thất bại: {file_name}")
                del tasks[short_id]; continue
            
            time.sleep(random.uniform(1, 2))
            # 2. Tìm ô nhập liệu
            text_xpath = "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/textarea"
            textbox = wait.until(EC.element_to_be_clickable((By.XPATH, text_xpath)))
            # 3. Nhập Prompt mới
            textbox.click()
            log_callback(f"Đang nhập prompt: {injected_prompt[3:]}...")
            for line in injected_prompt.split('\n'):
                textbox.send_keys(line)
                time.sleep(0.1)
            
            time.sleep(random.uniform(1, 2))

            # 4. Bấm nút TẠO
            btn_gen = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[2]/button[2]")
            robust_click(driver, btn_gen)
            
            log_callback(f"⏳ Đã bấm tạo. Nghỉ 5s trước khi gửi file tiếp theo...")
            time.sleep(random.uniform(3, 5)) 

        except Exception as e:
            log_callback(f"❌ Lỗi khi gửi {file_name}: {e}")
            if short_id in tasks: del tasks[short_id]

    # --- GIAI ĐOẠN 2: COLLECT (CHỜ VÀ GẶT LÚA) ---
    if not tasks: return False, file_batch 

    log_callback(f"⏳ Đã gửi xong. Đang chờ kết quả cho {len(tasks)} video...")
    
    start_wait = time.time()
    max_wait_time = 120 
    
    while time.time() - start_wait < max_wait_time:
        if all(t["done"] for t in tasks.values()):
            log_callback("✅ Batch hoàn thành 100%!")
            return True, []

        # Quét từng ID đang chờ
        for uid, info in tasks.items():
            if info["done"]: continue 
            
            try:
                # XPath "Thần thánh"
                xpath_dynamic = f"//*[contains(text(), '{info['id_tag']}')]/ancestor::div[.//video][1]//video"
                
                video_matches = driver.find_elements(By.XPATH, xpath_dynamic)
                
                if video_matches:
                    video_el = video_matches[0]
                    rs = driver.execute_script("return arguments[0].readyState;", video_el)
                    
                    if rs == 4: # HAVE_ENOUGH_DATA
                        # [LOGIC MỚI] Tạo folder output nếu chưa có
                        os.makedirs(os.path.dirname(info["save_path_final"]), exist_ok=True)
                        
                        log_callback(f"💾 Tải về: {info['file_name']}")
                        
                        # Tải về đúng đường dẫn đã tính từ đầu
                        if download_blob_video(driver, video_el, info["save_path_final"]):
                            log_callback(f"✅ OK: {os.path.basename(info['save_path_final'])}")
                            info["done"] = True
                        else:
                            log_callback(f"⚠️ Lỗi tải file: {info['file_name']}")
                    
                    elif rs == 0: 
                        driver.execute_script("arguments[0].play().then(()=>arguments[0].pause()).catch(()=>{});", video_el)

            except Exception as e:
                pass 
        
        time.sleep(3) # Quét lại mỗi 3s

    # --- KẾT THÚC ---
    failed_files = []
    for uid, info in tasks.items():
        if not info["done"]:
            log_callback(f"❌ Timeout: {info['file_name']}")
            original = next((p for p in file_batch if os.path.basename(p) == info["file_name"]), None)
            if original: failed_files.append(original)

    return len(failed_files) == 0, failed_files


# def process_video_batch(driver, file_batch, ignored_output_folder, log_callback=print):

#     """
#     Xử lý Batch có kiểm tra file tồn tại và lưu vào folder /video/ riêng của từng ảnh.
#     Lưu ý: Tham số thứ 3 (ignored_output_folder) sẽ bị bỏ qua để dùng logic đường dẫn tương đối.
#     """
#     setup_video_creation_mode(driver)
    
#     # [FIX LỖI] Khai báo wait
#     wait = WebDriverWait(driver, 15)
    
#     tasks = {} # Sổ theo dõi
    
#     # --- GIAI ĐOẠN 1: SUBMIT (GỬI LỆNH LIÊN TỤC) ---
#     log_callback(f"🚀 Bắt đầu gửi Batch gồm {len(file_batch)} file...")
    
#     for index, item_path in enumerate(file_batch):
#         file_name = os.path.basename(item_path)
#         name_no_ext = os.path.splitext(file_name)[0]
        
#         # === [LOGIC MỚI] TÍNH TOÁN ĐƯỜNG DẪN TRƯỚC ===
#         # 1. Lấy thư mục cha của file ảnh
#         parent_dir = os.path.dirname(item_path)
        
#         # 2. Định nghĩa thư mục video nằm trong đó
#         video_output_dir = os.path.join(parent_dir, "video")
        
#         # 3. Định nghĩa tên file output (8s)
#         final_video_name = f"{name_no_ext}_8s.mp4"
#         save_full_path = os.path.join(video_output_dir, final_video_name)
        
#         # 4. Kiểm tra tồn tại -> SKIP nếu đã có
#         if os.path.exists(save_full_path):
#             log_callback(f"⏭️ Đã tồn tại: {final_video_name} -> Bỏ qua.")
#             continue # Nhảy sang file tiếp theo, không upload nữa
            
#         # ===============================================
        
#         # Tạo ID ngắn gọn
#         short_id = f"ID_{int(time.time())}_{index}"
        
#         # Đọc prompt
#         prompt_path = os.path.join(parent_dir, "prompt.txt")
#         if os.path.exists(prompt_path):
#             with open(prompt_path, "r", encoding="utf-8") as f: base_prompt = f.read().strip()
#         else:
#             base_prompt = "Cinematic video, high quality"

#         # [QUAN TRỌNG] Tiêm ID vào ĐẦU Prompt
#         injected_prompt = f"||{short_id}|| {base_prompt}"
        
#         # Lưu tasks (Lưu kèm đường dẫn save_full_path đã tính ở trên)
#         tasks[short_id] = {
#             "file_name": file_name,
#             "save_path_final": save_full_path, # <--- Lưu đường dẫn đích vào đây
#             "done": False,
#             "id_tag": f"||{short_id}||",
#             "full_input_path": item_path # Lưu lại để trả về nếu lỗi
#         }
        
#         log_callback(f"📤 [{index+1}/{len(file_batch)}] Đang gửi: {file_name}...")

#         try:
#             # 1. Upload ảnh
#             if not upload_stealth(driver, item_path):
#                 log_callback(f"❌ Upload thất bại: {file_name}")
#                 del tasks[short_id]; continue

#             # 2. Tìm ô nhập liệu
#             text_xpath = "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/textarea"
#             textbox = wait.until(EC.element_to_be_clickable((By.XPATH, text_xpath)))
            
#             # 3. Nhập Prompt (Giả lập hành vi người dùng + JS)
#             textbox.click()
#             time.sleep(0.5)
#             driver.execute_script("""
#                 var el = arguments[0];
#                 el.value = arguments[1];
#                 el.dispatchEvent(new Event('input', { bubbles: true }));
#                 el.dispatchEvent(new Event('change', { bubbles: true }));
#             """, textbox, injected_prompt)
            
#             time.sleep(random.uniform(1, 2))

#             # 4. Bấm nút TẠO
#             btn_gen = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[2]/button[2]")
#             robust_click(driver, btn_gen)
            
#             # 5. Nghỉ 5s (random chút) trước khi gửi file tiếp theo
#             log_callback(f"⏳ Đã bấm tạo. Nghỉ một chút...")
#             time.sleep(random.uniform(4, 6)) 

#         except Exception as e:
#             log_callback(f"❌ Lỗi khi gửi {file_name}: {e}")
#             if short_id in tasks: del tasks[short_id]

#     # --- GIAI ĐOẠN 2: COLLECT (CHỜ VÀ GẶT LÚA) ---
#     # Nếu tasks rỗng (do đã skip hết hoặc lỗi hết), trả về ngay
#     if not tasks: 
#         return True, [] 

#     log_callback(f"⏳ Đã gửi xong. Đang chờ kết quả cho {len(tasks)} video...")
    
#     start_wait = time.time()
#     max_wait_time = 300 # 5 phút timeout cho cả mẻ
    
#     while time.time() - start_wait < max_wait_time:
#         if all(t["done"] for t in tasks.values()):
#             log_callback("✅ Batch hoàn thành 100%!")
#             return True, []

#         # Quét từng ID đang chờ
#         for uid, info in tasks.items():
#             if info["done"]: continue 
            
#             try:
#                 # XPath "Thần thánh"
#                 xpath_dynamic = f"//*[contains(text(), '{info['id_tag']}')]/ancestor::div[.//video][1]//video"
                
#                 video_matches = driver.find_elements(By.XPATH, xpath_dynamic)
                
#                 if video_matches:
#                     video_el = video_matches[0]
#                     rs = driver.execute_script("return arguments[0].readyState;", video_el)
                    
#                     if rs == 4: # HAVE_ENOUGH_DATA
#                         # [LOGIC MỚI] Tạo folder output nếu chưa có
#                         os.makedirs(os.path.dirname(info["save_path_final"]), exist_ok=True)
                        
#                         log_callback(f"💾 Tải về: {info['file_name']}")
                        
#                         # Tải về đúng đường dẫn đã tính từ đầu
#                         if download_blob_video(driver, video_el, info["save_path_final"]):
#                             log_callback(f"✅ OK: {os.path.basename(info['save_path_final'])}")
#                             info["done"] = True
#                         else:
#                             log_callback(f"⚠️ Lỗi tải file: {info['file_name']}")
                    
#                     elif rs == 0: 
#                         driver.execute_script("arguments[0].play().then(()=>arguments[0].pause()).catch(()=>{});", video_el)

#             except Exception as e:
#                 pass 
        
#         time.sleep(3) # Quét lại mỗi 3s

#     # --- KẾT THÚC ---
#     failed_files = []
#     for uid, info in tasks.items():
#         if not info["done"]:
#             log_callback(f"❌ Timeout: {info['file_name']}")
#             # Trả về đường dẫn input gốc để retry
#             failed_files.append(info['full_input_path'])

#     return len(failed_files) == 0, failed_files


