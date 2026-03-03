import os
import time
import base64
import mimetypes
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

def process_pair_images_to_prompt(driver, img1_path, img2_path, output_folder,pair_id, log_callback=print):
    """
    CHIẾN THUẬT: FAKE PASTE 2 ẢNH LIÊN TIẾP
    1. Dọn dẹp input cũ.
    2. Paste ảnh 1 -> Paste ảnh 2.
    3. Gửi lệnh yêu cầu viết prompt nối.
    4. Lọc kết quả và lưu.
    """
    try:
        wait = WebDriverWait(driver, 45)

        # --- BƯỚC 1: DỌN DẸP ẢNH CŨ (NẾU CÓ) ---
        try:
            # Tìm nút xóa ảnh (thường là nút thứ 2 trong uploader preview)
            cancel_xpath = "//uploader-file-preview//button[2]"
            cancel_btns = driver.find_elements(By.XPATH, cancel_xpath)
            
            if len(cancel_btns) > 0:
                log_callback(f"🧹 Phát hiện {len(cancel_btns)} ảnh cũ. Đang xóa...")
                for btn in cancel_btns:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.2)
                    except: pass
                time.sleep(1)
        except Exception as e:
            log_callback(f"⚠️ Lỗi dọn ảnh cũ: {e}")

        # --- BƯỚC 2: TÌM Ô CHAT ---
        try:
            textbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true'], div[role='textbox']")))
            textbox.click()
            time.sleep(0.5)
        except Exception as e:
            log_callback(f"⚠️ Không tìm thấy ô chat: {e}")
            return False

        # --- BƯỚC 3: HÀM JS PASTE (Tái sử dụng) ---
        # Script này nhận vào Base64 và giả lập hành động Ctrl+V của người dùng
        js_paste_script = """
            var target = arguments[0];
            var b64Data = arguments[1];
            var fileName = arguments[2];
            var fileType = arguments[3];

            function b64toFile(b64Data, fileName, fileType) {
                var byteCharacters = atob(b64Data);
                var byteArrays = [];
                for (var offset = 0; offset < byteCharacters.length; offset += 512) {
                    var slice = byteCharacters.slice(offset, offset + 512);
                    var byteNumbers = new Array(slice.length);
                    for (var i = 0; i < slice.length; i++) {
                        byteNumbers[i] = slice.charCodeAt(i);
                    }
                    var byteArray = new Uint8Array(byteNumbers);
                    byteArrays.push(byteArray);
                }
                var blob = new Blob(byteArrays, {type: fileType});
                return new File([blob], fileName, {type: fileType, lastModified: new Date().getTime()});
            }

            var file = b64toFile(b64Data, fileName, fileType);
            var dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);

            var pasteEvent = new ClipboardEvent('paste', {
                bubbles: true,
                cancelable: true,
                clipboardData: dataTransfer
            });

            target.dispatchEvent(pasteEvent);
        """

        # --- BƯỚC 4: XỬ LÝ VÀ PASTE TỪNG ẢNH ---
        images_to_upload = [img1_path, img2_path]
        
        for idx, img_path in enumerate(images_to_upload):
            abs_path = os.path.abspath(img_path)
            filename = os.path.basename(abs_path)
            
            # Đọc file và convert Base64
            mime_type, _ = mimetypes.guess_type(abs_path)
            if not mime_type: mime_type = 'image/png'
            
            with open(abs_path, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')

            log_callback(f"📋 Paste ảnh {idx+1}: {filename}...")
            
            # Thực thi JS Paste
            driver.execute_script(js_paste_script, textbox, b64_data, filename, mime_type)
            
            # Đợi một chút giữa 2 lần paste để tránh xung đột UI
            time.sleep(2) 

        log_callback("⏳ Đang chờ Preview 2 ảnh (5s)...")
        time.sleep(5)

        # --- BƯỚC 5: NHẬP TEXT PROMPT VÀ GỬI ---
        # Prompt yêu cầu nối cảnh
        user_prompt = (
            "I have uploaded 2 consecutive frames. "
            "Write a detailed visual prompt describing the transition and motion from Image 1 to Image 2. "
            "Focus on how the scene evolves. Output only the prompt string."
            " Start word must be 'Prompt:'."
        )
        
        # Nhập text vào ô chat (dùng send_keys vì đã focus từ đầu)
        textbox.send_keys(user_prompt)
        time.sleep(1)

        try:
            textbox.send_keys(Keys.ENTER)
            log_callback("🚀 Đã Enter gửi lệnh.")
        except:
            try:
                driver.find_element(By.CSS_SELECTOR, "button[aria-label^='Send']").click()
            except:
                log_callback("❌ Không bấm được nút gửi!")
                return False

        # --- BƯỚC 6: CHỜ KẾT QUẢ (SMART WAIT - Logic cũ) ---
        log_callback("⏳ Đang đợi Gemini trả lời...")
        
        # Selector khung chat trả lời của Gemini
        RESPONSE_SELECTOR = "div.markdown-main-panel[id^='model-response-message-content']"
        
        try:
            # Đợi số lượng tin nhắn tăng lên
            old_count = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR))
            WebDriverWait(driver, config.global_settings["system"]["wait_time"]).until(lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)) > old_count)
            
            # Lấy tin nhắn mới nhất
            el = driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)[-1]
        except:
            log_callback("❌ Timeout: Gemini không trả lời.")
            return False
        
        # Logic đợi text ổn định (typing effect)
        stable_time = 0
        last_text = ""
        start_wait = time.time()
        while stable_time < 3:
            if time.time() - start_wait > 30: break
            time.sleep(1)
            try:
                curr = el.text.strip()
            except: 
                curr = last_text
                
            if curr == last_text and curr != "": stable_time += 1
            else: stable_time = 0; last_text = curr

        # --- BƯỚC 7: XỬ LÝ TEXT VÀ LỌC (Logic cũ) ---
        final_text = last_text.strip()
        
        # Kiểm tra header "Prompt:"
        if not final_text.lower().startswith("prompt:"):
            # Nếu Gemini không bắt đầu bằng Prompt:, ta thử fix nhẹ bằng cách tìm dòng nào có chữ Prompt:
            # Hoặc báo lỗi tùy bạn. Ở đây giữ nguyên logic cũ là báo lỗi.
            log_callback(f"⚠️ Kết quả không chuẩn format 'Prompt:':\n'{final_text[:50]}...'")
            # return False -> Có thể return False hoặc chấp nhận lưu luôn tùy độ khó tính

        # Tách dòng và lọc footer
        clean_lines = []
        raw_lines = final_text.splitlines()
        
        for index, line in enumerate(raw_lines):
            l = line.strip()
            if not l: continue 

            # Check dừng: Những câu thoại kết thúc của AI
            if l.lower().startswith("would you like") or l.lower().startswith("hope this help"):
                break
            
            # Check dừng 2: Nếu lặp lại chữ "Prompt:" ở giữa
            if index > 0 and l.lower().startswith("prompt:"):
                break
                
            clean_lines.append(l)
        
        final_content = "\n".join(clean_lines)
        # --- BƯỚC 8: LƯU FILE ---
        # Đảm bảo folder output tồn tại
        os.makedirs(output_folder, exist_ok=True)
        
        prompt_file = os.path.join(output_folder, f"{pair_id}_prompt.txt")
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(final_content)

        log_callback(f"💾 Đã lưu prompt nối: {os.path.basename(prompt_file)}")
        return True

    except Exception as e:
        log_callback(f"❌ Lỗi xử lý cặp ảnh: {e}")
        return False