import os
import time
import base64
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- HÀM HỖ TRỢ CLICK & TYPE ---

# --- HÀM TÀNG HÌNH THỦ CÔNG (Không cần thư viện) ---
def apply_stealth(page):
    """Giả lập hành vi trình duyệt thật để tránh bị bot detect"""
    try:
        # 1. Xóa thuộc tính navigator.webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # 2. Giả lập Plugins (Chrome thật có plugins, bot thì không)
        page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # 3. Giả lập window.chrome
        page.add_init_script("""
            window.chrome = {
                runtime: {}
            };
        """)
        
        # 4. Giả lập Permissions
        page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: 'denied' }) :
                originalQuery(parameters)
            );
        """)
        print("🥷 Đã kích hoạt chế độ Stealth (Tàng hình)")
    except Exception as e:
        print(f"⚠️ Lỗi kích hoạt Stealth: {e}")
        
def robust_click(page, selector_or_locator):
    """Thay thế robust_click của Selenium"""
    try:
        # Nếu truyền vào là string selector
        if isinstance(selector_or_locator, str):
            locator = page.locator(selector_or_locator).first
        else:
            locator = selector_or_locator

        # Thử click thường (Playwright tự đợi element clickable)
        locator.click(timeout=3000)
        return True
    except:
        try:
            # Fallback: Dùng JS click nếu click thường thất bại
            locator.evaluate("node => node.click()")
            return True
        except Exception as e:
            print(f"❌ Click thất bại: {e}")
            return False

def human_click_offset(page, locator):
    """Thay thế human_click_offset: Click lệch tâm"""
    try:
        box = locator.bounding_box()
        if not box: return
        
        width = box['width']
        height = box['height']
        
        # Random offset từ tâm
        offset_x = random.randint(int(width * 0.2), int(width * 0.8))
        offset_y = random.randint(int(height * 0.2), int(height * 0.8))
        
        # Di chuyển chuột và click
        page.mouse.move(box['x'] + offset_x, box['y'] + offset_y)
        page.wait_for_timeout(random.uniform(200, 500)) # 0.2 - 0.5s
        page.mouse.down()
        page.wait_for_timeout(random.uniform(50, 150))
        page.mouse.up()
    except Exception as e:
        # Fallback click thường nếu lỗi tính toán
        locator.click()

def human_type(page, locator, text):
    """Thay thế human_type: Gõ phím như người thật"""
    locator.click()
    page.wait_for_timeout(random.uniform(500, 1000)) # 0.5 - 1.0s

    text_len = len(text)
    if text_len == 0: return

    target_duration = 4.5
    avg_delay_per_char = target_duration / text_len
    # Clamp giá trị delay
    avg_delay_per_char = max(0.05, min(avg_delay_per_char, 0.3))

    for char in text:
        locator.type(char, delay=0) # delay=0 để mình tự control sleep bên dưới
        
        # Tính toán delay random
        delay = random.uniform(avg_delay_per_char * 0.5, avg_delay_per_char * 1.5)
        
        if char in ' \n.,':
            delay += 0.1 
            
        time.sleep(delay) # Dùng time.sleep của python cho chính xác logic cũ

    page.wait_for_timeout(random.uniform(500, 1000))

# --- HÀM 2: CẤU HÌNH GIAO DIỆN ---
def setup_video_creation_mode(page):
    print("⚙️ Đang cấu hình giao diện (Mode -> Landscape -> Qty=1)...")

    try:
        # 1. Click nút "Tạo dự án"
        try:
            create_btn = page.locator("xpath=/html/body/div[1]/div[2]/div/div/button")
            if create_btn.is_visible(timeout=5000):
                create_btn.click()
                time.sleep(random.uniform(0.5, 1.5))
        except:
            print("⚠️ Bỏ qua 'Tạo dự án'.")

        # 2. Chuyển sang tab "Video"
        try:
            video_tab = page.locator("xpath=/html/body/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div/div[1]/button[1]")
            video_tab.click(timeout=5000)
            time.sleep(1)
        except:
            print("⚠️ Bỏ qua Tab Video.")

        # 3. Mở Dropdown chọn chế độ
        try:
            mode_dropdown = page.locator("xpath=/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[1]/div[1]/button")
            human_click_offset(page, mode_dropdown)
            time.sleep(random.uniform(1, 2))

            # 4. Chọn "Tạo video từ các thành phần"
            print("🎯 Chọn chế độ Thành phần...")
            component_icon = page.locator("xpath=/html/body/div[3]/div/div/div[3]/div/i")
            # Dùng JS click cho chắc ăn như code cũ
            component_icon.evaluate("node => node.click()")
            
            print("✅ Đã chọn chế độ: Tạo video từ các thành phần")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"⚠️ Lỗi chọn chế độ: {e}")

        # 5. Mở Cấu hình (Settings)
        try:
            settings_btn = page.locator("xpath=/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[1]/div[2]/button[2]")
            human_click_offset(page, settings_btn)
            time.sleep(random.uniform(1, 2))

            # --- CẤU HÌNH KHỔ NGANG ---
            print("🎯 Cấu hình Khổ ngang (Landscape)...")
            ratio_dropdown = page.locator("xpath=/html/body/div[3]/div/div/div[1]/div[1]/button")
            human_click_offset(page, ratio_dropdown)
            time.sleep(random.uniform(1, 2))

            landscape_option = page.locator("xpath=/html/body/div[4]/div/div/div[1]/div/span")
            landscape_option.evaluate("node => node.click()")
            print("✅ Đã chọn Khổ ngang")
            time.sleep(1)
            
            # --- CẤU HÌNH SỐ LƯỢNG = 1 ---
            print("🎯 Cấu hình Số lượng = 1...")
            quantity_dropdown = page.locator("xpath=/html/body/div[3]/div/div/div[1]/div[2]/button")
            human_click_offset(page, quantity_dropdown)
            time.sleep(random.uniform(1, 2))

            option_one = page.locator("xpath=/html/body/div[4]/div/div/div[1]/div/span")
            option_one.evaluate("node => node.click()")
            print("✅ Đã cấu hình Số lượng: 1")
            
            # Đóng bảng Settings (Click vào body)
            page.evaluate("document.body.click()")
            
        except Exception as e:
            print(f"⚠️ Lỗi cấu hình Settings: {e}")

        return True
    except Exception as e:
        print(f"❌ Lỗi cấu hình tổng: {e}")
        return True

def upload_stealth(page, file_path):
    try:
        abs_path = os.path.abspath(file_path)
        
        # 1. Click nút Upload (nếu cần)
        try:
            upload_trigger = page.locator("xpath=/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[1]/div/div/button")
            if upload_trigger.is_visible():
                upload_trigger.click()
                time.sleep(random.uniform(1, 2))
        except: pass

        # 2. Set Input Files (Playwright xử lý input file rất đơn giản)
        try:
            # Playwright tự tìm input[type=file] và set file, không cần trick JS phức tạp
            # Nhưng để tôn trọng logic cũ tìm xpath cụ thể:
            file_input = page.locator("xpath=/html/body/div[1]/div[3]/div/div/input").first
            
            # Set file
            file_input.set_input_files(abs_path)
            
            # Dispatch events thủ công như code cũ (dù set_input_files đã làm, nhưng giữ logic cũ)
            file_input.evaluate("""input => {
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }""")
            
            print(f"✅ Đã upload thành công: {os.path.basename(file_path)}")
            time.sleep(random.uniform(3, 5))
            
            # 3. Click nút Cắt & Lưu
            cut_and_save_button = page.locator("xpath=/html/body/div[1]/div[3]/div[3]/div/div/div[2]/div/button[3]")
            # Chờ element ready
            cut_and_save_button.wait_for(state="visible", timeout=15000)
            
            human_click_offset(page, cut_and_save_button)
            print(f"✅ Đã bấm nút Lưu ảnh: {os.path.basename(file_path)}")
            
            return True
        except Exception as e:
            print(f"❌ Lỗi tương tác input file: {e}")
            return False

    except Exception as e:
        print(f"❌ Lỗi Upload tổng quát: {e}")
        return False

# --- HÀM 3: TẢI VIDEO ---
def download_blob_video(page, video_locator, save_path):
    try:
        # Lấy thuộc tính src
        video_src = video_locator.get_attribute("src")
        if not video_src: return False

        print("📥 Đang tải video blob về máy...")
        
        # Dùng script JS để fetch blob (Logic y hệt cũ, chỉ đổi cách gọi API)
        # Playwright evaluate trả về giá trị return của JS
        base64_data = page.evaluate("""async (uri) => {
            const response = await fetch(uri);
            const blob = await response.blob();
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }""", video_src)

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

def process_video_batch(page, file_batch, output_folder, log_callback=print):
    # Khởi tạo môi trường
    setup_video_creation_mode(page)
    
    tasks = {}
    downloaded_urls = set()

    # --- GIAI ĐOẠN 1: SUBMIT ---
    for index, item_path in enumerate(file_batch):
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
            if not upload_stealth(page, item_path): continue
            
            textbox = page.locator("xpath=/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/textarea")
            textbox.wait_for(state="visible", timeout=15000)
            
            prompt_path = os.path.join(parent_dir, "prompt.txt")
            base_prompt = open(prompt_path, "r", encoding="utf-8").read().strip() if os.path.exists(prompt_path) else "Cinematic"
            
            human_type(page, textbox, f"{id_tag} {base_prompt}")
            
            xpath_btn = "/html/body/div[1]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/div[2]/button[2]"
            btn_gen = page.locator(f"xpath={xpath_btn}")
            btn_gen.wait_for(state="visible", timeout=20000)
            
            time.sleep(random.uniform(0.5, 1.0))
            human_click_offset(page, btn_gen)
            
            log_callback(f"📤 Đã gửi: {full_name_id}")
            time.sleep(random.uniform(5, 8)) 
        except Exception as e:
            log_callback(f"❌ Lỗi gửi {full_name_id}: {e}")
            tasks.pop(full_name_id, None)

    # --- GIAI ĐOẠN 2: COLLECT ---
    if not tasks: return False, file_batch

    log_callback(f"⏳ Chờ render {len(tasks)} video...")
    start_time = time.time()
    
    while time.time() - start_time < 300: # 5 phút
        active_tasks = [uid for uid, info in tasks.items() if not info["done"]]
        if not active_tasks:
            log_callback("✅ Tất cả video đã tải xong!")
            break

        for uid in active_tasks:
            info = tasks[uid]
            try:
                # XPath tìm video
                xpath_check = f"//*[contains(text(), '{info['id_tag']}')]/ancestor::div[.//video][1]//video"
                # Playwright locator trả về danh sách nếu có nhiều, ta lấy cái đầu tiên
                videos = page.locator(f"xpath={xpath_check}")
                
                # Kiểm tra có element nào không
                if videos.count() > 0:
                    video_el = videos.first
                    
                    current_src = video_el.get_attribute("src")
                    
                    # Logic URL check
                    if current_src in downloaded_urls:
                        continue 
                    
                    if not current_src or current_src == "null":
                        continue

                    # Check readyState bằng JS
                    rs = video_el.evaluate("node => node.readyState")
                    
                    if rs == 4: # HAVE_ENOUGH_DATA
                        os.makedirs(os.path.dirname(info["save_path"]), exist_ok=True)
                        log_callback(f"💾 Phát hiện Video mới: {uid}")
                        
                        if download_blob_video(page, video_el, info["save_path"]):
                            if os.path.exists(info["save_path"]) and os.path.getsize(info["save_path"]) > 0:
                                log_callback(f"✅ Thành công: {uid}")
                                info["done"] = True
                                downloaded_urls.add(current_src)
                            else:
                                log_callback(f"⚠️ Lỗi 0KB: {uid}")
                    
                    elif rs == 0: 
                        # Kích hoạt video ngủ
                        video_el.evaluate("node => { node.play().then(()=>node.pause()).catch(()=>{}); }")
                        
            except Exception as e:
                pass
        
        time.sleep(3) 

    # --- TỔNG KẾT ---
    failed = [v["file_path"] for k, v in tasks.items() if not v["done"]]
    return len(failed) == 0, failed
