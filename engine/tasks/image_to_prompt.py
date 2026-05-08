import os
import time
import base64
import mimetypes
import json
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

def process_image_to_prompt(driver, image_path, json_path, stt, timecode, content, log_callback=print):
    """
    Paste 1 ảnh lên Gemini, gửi kèm Timecode + Content để AI tạo prompt.
    Kết quả được append vào file JSON.
    """
    try:
        wait = WebDriverWait(driver, 30)

        # --- DỌN ẢNH CŨ ---
        try:
            cancel_btns = driver.find_elements(By.XPATH, "//uploader-file-preview//button[2]")
            if cancel_btns:
                log_callback(f"🧹 Xóa {len(cancel_btns)} ảnh cũ...")
                for btn in cancel_btns:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.2)
                    except: pass
                time.sleep(1)
        except Exception as e:
            log_callback(f"⚠️ Lỗi dọn ảnh cũ: {e}")

        abs_path = os.path.abspath(image_path)
        filename = os.path.basename(abs_path)

        # --- ĐỌC ẢNH -> BASE64 ---
        mime_type, _ = mimetypes.guess_type(abs_path)
        if not mime_type: mime_type = 'image/png'
        with open(abs_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')

        log_callback(f"📋 Paste ảnh: {filename}...")

        # --- TÌM Ô CHAT ---
        try:
            textbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true'], div[role='textbox']")))
            textbox.click()
            time.sleep(0.5)
        except Exception as e:
            log_callback(f"⚠️ Không tìm thấy ô chat: {e}")
            return False
        # --- GỬI KÈM TIMECODE + CONTENT BẰNG SHIFT+ENTER ĐỂ TRÁNH GỬI SỚM ---
        context_text = f"Timecode: {timecode}\nContent: {content}"
        for line in context_text.split('\n'):
            textbox.send_keys(line)
            textbox.send_keys(Keys.SHIFT, Keys.ENTER)
        time.sleep(0.5)

        # --- JS PASTE ẢNH ---
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
                    for (var i = 0; i < slice.length; i++) { byteNumbers[i] = slice.charCodeAt(i); }
                    byteArrays.push(new Uint8Array(byteNumbers));
                }
                var blob = new Blob(byteArrays, {type: fileType});
                return new File([blob], fileName, {type: fileType, lastModified: new Date().getTime()});
            }
            var file = b64toFile(b64Data, fileName, fileType);
            var dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            var pasteEvent = new ClipboardEvent('paste', {bubbles: true, cancelable: true, clipboardData: dataTransfer});
            target.dispatchEvent(pasteEvent);
        """
        driver.execute_script(js_paste_script, textbox, b64_data, filename, mime_type)
        log_callback("✅ Đã paste ảnh.")

        # --- CHỜ PREVIEW VÀ THỬ GỬI NHIỀU LẦN ---
        log_callback("⏳ Đang đợi hệ thống xử lý ảnh và thử gửi...")
        RESPONSE_SELECTOR = "div.markdown-main-panel[id^='model-response-message-content']"
        old_count = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR))
        
        sent_successfully = False
        for attempt in range(15):
            # Thử gửi bằng Enter
            try:
                textbox.send_keys(Keys.ENTER)
            except: pass
            
            # Thử gửi bằng click JS (tìm nút Send)
            try:
                driver.execute_script("""
                    let btns = document.querySelectorAll('button');
                    for(let b of btns){
                        let aria = b.getAttribute('aria-label');
                        if(aria && aria.toLowerCase().includes('send')){
                            b.click();
                        }
                    }
                """)
            except: pass

            time.sleep(2)
            
            # 1. Nếu có response mới -> Chắc chắn đã gửi
            new_count = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR))
            if new_count > old_count:
                sent_successfully = True
                log_callback("🚀 Đã gửi thành công (AI bắt đầu trả lời)!")
                break
                
            # 2. Nếu textbox bị xoá rỗng -> Chắc chắn đã gửi
            try:
                previews = len(driver.find_elements(By.XPATH, "//uploader-file-preview"))
                if previews == 0 and textbox.text.strip() == "":
                    sent_successfully = True
                    log_callback("🚀 Đã gửi thành công (Textbox đã dọn trống)!")
                    break
            except: pass
            


        if not sent_successfully:
            log_callback("❌ Timeout: Không thể gửi lệnh (Có thể do mạng hoặc ảnh lỗi).")
            return False

        # --- CHỜ RESPONSE HOÀN TẤT ---
        log_callback("⏳ Đang đợi Gemini trả lời...")
        try:
            WebDriverWait(driver, config.global_settings["system"]["wait_time"]).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)) > old_count
            )
            el = driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)[-1]
        except:
            log_callback("❌ Timeout: Gemini không trả lời.")
            return False

        # Smart wait ổn định
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

        final_text = last_text.strip()
        if not final_text:
            log_callback("❌ Gemini trả về rỗng.")
            return False

        # --- LƯU JSON ---
        data = []
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except: pass

        data.append({
            "STT": stt,
            "timecode": timecode,
            "content": content,
            "prompt": final_text
        })

        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        log_callback(f"💾 Đã lưu STT {stt} vào: {os.path.basename(json_path)}")
        return True

    except Exception as e:
        log_callback(f"❌ Lỗi ngoại lệ: {e}")
        return False
