import os
import time
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
            time.sleep(1)
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
            time.sleep(1.5)

            # 4. Chọn "Tạo video từ các thành phần"
            print("🎯 Chọn chế độ Thành phần...")
            component_icon = wait.until(EC.presence_of_element_located((
                By.XPATH, "/html/body/div[3]/div/div/div[3]/div/i"
            )))
            driver.execute_script("arguments[0].click();", component_icon)
            print("✅ Đã chọn chế độ: Tạo video từ các thành phần")
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️ Lỗi chọn chế độ: {e}")

        # 5. Mở Cấu hình (Settings)
        try:
            settings_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[1]/div[2]/button[2]")))
            robust_click(driver, settings_btn)
            time.sleep(1.5) # Chờ bảng settings hiện ra

            # --- MỚI: CẤU HÌNH KHỔ NGANG (LANDSCAPE) ---
            print("🎯 Cấu hình Khổ ngang (Landscape)...")
            # Click Dropdown Tỷ lệ khung hình (Nút bên trái)
            ratio_dropdown = wait.until(EC.element_to_be_clickable((
                By.XPATH, "/html/body/div[3]/div/div/div[1]/div[1]/button"
            )))
            robust_click(driver, ratio_dropdown)
            time.sleep(1) # Chờ menu tỷ lệ nảy ra ở div[4]

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
            time.sleep(1) # Chờ menu số lượng nảy ra ở div[4]

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



# --- HÀM 3: UPLOAD TÀNG HÌNH (CẬP NHẬT LOGIC CHỜ) ---
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
                time.sleep(1)
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
            time.sleep(5) # Chờ ảnh load lên UI
            
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

# --- HÀM 4: XỬ LÝ 1 FILE (MAIN LOGIC) ---
def generate_video_for_file(driver, image_path, prompt_text, output_folder):
    # 2. CẤU HÌNH GIAO DIỆN (NẾU CẦN)
    setup_video_creation_mode(driver) 
    
    filename = os.path.basename(image_path)
    name_no_ext = os.path.splitext(filename)[0]
    final_video_name = f"{name_no_ext}_8s.mp4"
    save_path = os.path.join(output_folder, final_video_name)

    if os.path.exists(save_path):
        print(f"⏭️ Đã tồn tại: {final_video_name}")
        return True

    print(f"===============\n🎬 Bắt đầu xử lý: {filename}")
    wait = WebDriverWait(driver, 10)
    
    # 1. LẤY DANH SÁCH SRC CŨ (Lưu tất cả src video đang có trên màn hình)
    old_srcs = []
    try:
        videos = driver.find_elements(By.TAG_NAME, "video")
        for v in videos:
            src = v.get_attribute("src")
            if src: old_srcs.append(src)
        print(f"ℹ️ Đã ghi nhớ {len(old_srcs)} video cũ.")
    except: pass


    
    # 3. NHẬP PROMPT & UPLOAD ẢNH
    try:
        # 1. Upload ảnh (Chỉ gọi 1 lần duy nhất ở đây)
        if not upload_stealth(driver, image_path):
            print("⛔ Lỗi upload, dừng file này.")
            return False
            
        # Tìm ô nhập liệu (XPath textarea của bạn)
        text_xpath = "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/textarea"
        textbox = wait.until(EC.element_to_be_clickable((By.XPATH, text_xpath)))


        
        # 3. Nhập Prompt mới
        textbox.click()
        for line in prompt_text.split('\n'):
            textbox.send_keys(line)
            time.sleep(0.1)
        
        time.sleep(1)

        # 4. Bấm nút TẠO
        generate_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, 
            "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[2]/button[2][not(@disabled)]"
        )))
        robust_click(driver, generate_btn)
        print("🚀 Đã bấm TẠO! Đang chờ video render...")

    except Exception as e:
        print(f"❌ Lỗi thao tác nhập liệu: {e}")
        return False

    # 4. --- CHỜ VIDEO MỚI & ÉP TẢI (FORCE LOAD) ---
    try:
        new_video_element = None
        start_wait = time.time()
        
        # Chờ 5 phút
        while time.time() - start_wait < 120:
            try:
                # 1. Tìm TẤT CẢ thẻ video trên trang
                current_videos = driver.find_elements(By.TAG_NAME, "video")
                
                found_new = False
                for vid in current_videos:
                    src = vid.get_attribute("src")
                    
                    # LOGIC LỌC:
                    # - Phải có src
                    # - Src phải chứa http hoặc blob
                    # - Src KHÔNG ĐƯỢC nằm trong danh sách cũ (old_srcs)
                    if src and ("blob:" in src or "http" in src) and (src not in old_srcs):
                        
                        # In ra để debug xem bắt được cái gì
                        # print(f"🔎 Nghi vấn video mới: ...{src[-15:]}")

                        # --- KIỂM TRA READY STATE ---
                        rs = driver.execute_script("return arguments[0].readyState;", vid)
                        
                        if rs >= 1:
                            print(f"✅ Video mới đã SẴN SÀNG! (ReadyState: {rs})")
                            new_video_element = vid
                            found_new = True
                            break # Thoát vòng lặp for (tìm thấy video)
                        else:
                            # Kích hoạt tải (Force Load)
                            print(f"⚠️ Thấy video mới nhưng chưa load (RS={rs}). Kích hoạt...")
                            driver.execute_script("""
                                var v = arguments[0];
                                v.muted = true;
                                v.play().then(()=>{ v.pause(); }).catch(()=>{});
                            """, vid)
                
                if found_new:
                    break # Thoát vòng lặp while (đã có kết quả)

            except Exception as e:
                # print(f"Lỗi nhẹ trong loop: {e}")
                pass
            
            time.sleep(3)

        if not new_video_element:
            print("❌ Timeout: Không tìm thấy video mới nào xuất hiện.")
            return False

        # 4. Tải Video
        print(f"💾 Đang tải video: ...{new_video_element.get_attribute('src')[-15:]}")
        if download_blob_video(driver, new_video_element, save_path):
            print(f"✅ Đã lưu thành công: {save_path}")
            return True
        else:
            print("❌ Tải thất bại.")
            return False

    except Exception as e:
        print(f"❌ Lỗi quy trình: {e}")
        return False
