import os
import time
import base64
import mimetypes
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def process_image_to_prompt(driver, image_path, output_subfolder, log_callback=print):
    """
    CHIẾN THUẬT: FAKE PASTE (GIẢ LẬP CTRL+V)
    1. Chuyển ảnh sang Base64.
    2. Focus vào ô chat.
    3. Bắn sự kiện 'paste' chứa file ảnh vào ô chat.
    """
    try:
        wait = WebDriverWait(driver, 30)

        try:
            # XPath này tìm nút button thứ 2 bên trong mọi thẻ uploader-file-preview
            cancel_xpath = "//uploader-file-preview//button[2]"
            
            cancel_btns = driver.find_elements(By.XPATH, cancel_xpath)
            
            if len(cancel_btns) > 0:
                log_callback(f"🧹 Phát hiện {len(cancel_btns)} ảnh cũ chưa gửi. Đang xóa...")
                for btn in cancel_btns:
                    try:
                        # Dùng JS click để đảm bảo ăn ngay, bất chấp overlay
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.2)
                    except:
                        pass
                time.sleep(1) # Chờ UI cập nhật sau khi xóa
            else:
                # log_callback("✨ Input sạch, không có ảnh cũ.")
                pass
        except Exception as e:
            log_callback(f"⚠️ Lỗi khi dọn ảnh cũ (không ảnh hưởng process chính): {e}")

        abs_path = os.path.abspath(image_path)
        filename = os.path.basename(abs_path)
        name_no_ext = os.path.splitext(filename)[0]
        
        # 1. Chuẩn bị dữ liệu ảnh
        mime_type, _ = mimetypes.guess_type(abs_path)
        if not mime_type: mime_type = 'image/png'
        
        with open(abs_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')

        log_callback(f"📋 Đang thực hiện Paste (Dán): {filename}...")

        # 2. Tìm ô chat (Nơi sẽ nhận lệnh Paste)
        try:
            # Tìm ô nhập liệu (Rich Text Editor)
            textbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true'], div[role='textbox']")))
            
            # Click vào để chắc chắn nó đang được chọn (Focus)
            textbox.click()
            time.sleep(0.5)
        except Exception as e:
            log_callback(f"⚠️ Không tìm thấy ô chat: {e}")
            return False

        # 3. SCRIPT JS GIẢ LẬP SỰ KIỆN PASTE
        js_paste_script = """
            var target = arguments[0];
            var b64Data = arguments[1];
            var fileName = arguments[2];
            var fileType = arguments[3];

            // Hàm chuyển Base64 -> Blob -> File
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

            // Tạo gói dữ liệu Clipboard (DataTransfer)
            var dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);

            // Tạo sự kiện Paste
            var pasteEvent = new ClipboardEvent('paste', {
                bubbles: true,
                cancelable: true,
                clipboardData: dataTransfer
            });

            // Bắn sự kiện vào ô chat
            target.dispatchEvent(pasteEvent);
        """

        # Thực thi lệnh Paste
        driver.execute_script(js_paste_script, textbox, b64_data, filename, mime_type)
        log_callback("✅ Đã bắn sự kiện Paste.")

        # 4. CHỜ PREVIEW (THUMBNAIL)
        # Nếu Paste thành công, ảnh nhỏ phải hiện ra ngay
        log_callback("⏳ Đang chờ Preview ảnh (5s)...")
        time.sleep(5) 

        
        # 5. GỬI LỆNH
        try:
            textbox.send_keys(Keys.ENTER)
            log_callback("🚀 Đã Enter gửi ảnh.")
        except:
            # Fallback nút gửi
            try:
                driver.find_element(By.CSS_SELECTOR, "button[aria-label^='Send']").click()
            except:
                log_callback("❌ Không bấm được nút gửi!")
                return False

        # --- 6. PHẦN CHỜ KẾT QUẢ (GIỮ NGUYÊN NHƯ CŨ) ---
        log_callback("⏳ Đang đợi Gemini trả lời...")
        RESPONSE_SELECTOR = "div.markdown-main-panel[id^='model-response-message-content']"
        old_count = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR))
        WebDriverWait(driver, 120).until(lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)) > old_count)
        
        el = driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)[-1]
        
        # Smart Wait logic
        stable_time = 0
        last_text = ""
        start_wait = time.time()
        while stable_time < 3:
            if time.time() - start_wait > 180: break
            time.sleep(1)
            try:
                curr = el.text.strip()
            except: 
                curr = last_text
                
            if curr == last_text and curr != "": stable_time += 1
            else: stable_time = 0; last_text = curr

        # --- 7. XỬ LÝ TEXT VÀ LỌC LẤY 1 PROMPT DUY NHẤT ---
        final_text = last_text.strip()
        
        # 1. Kiểm tra điều kiện đầu vào: Phải bắt đầu bằng Prompt:
        if not final_text.lower().startswith("prompt:"):
            log_callback(f"⚠️ Kết quả không hợp lệ (Không có 'Prompt:' ở đầu):\n'{final_text[:50]}...'")
            return False

        # 2. Tách dòng và lọc
        clean_lines = []
        raw_lines = final_text.splitlines()
         
        for index, line in enumerate(raw_lines):
            l = line.strip()
            if not l: continue # Bỏ qua dòng trống

            # Check dừng 1: Những câu thoại kết thúc của AI
            if l.lower().startswith("would you like") or l.lower().startswith("hope this help"):
                break
            
            # [LOGIC MỚI] Check dừng 2: Nếu KHÔNG PHẢI dòng đầu tiên
            # mà lại thấy xuất hiện chữ "Prompt:" lần nữa -> Cắt luôn phần sau
            if index > 0 and l.lower().startswith("prompt:"):
                break
                
            clean_lines.append(l)
        
        # Gộp lại thành văn bản
        final_content = "\n".join(clean_lines)

        # Lưu file
        prompt_file = os.path.join(output_subfolder, f"{name_no_ext}_prompt.txt")
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(final_content)

        log_callback(f"💾 Đã lưu prompt: {os.path.basename(prompt_file)}")
        return True

    except Exception as e:
        log_callback(f"❌ Lỗi xử lý ngoại lệ: {e}")
        return False