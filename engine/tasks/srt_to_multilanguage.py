import os
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

def process_srt_multilanguage(driver, chunk, log_callback=print):
    """
    Cơ chế:
    1. Nhận một "chunk" (lô) các câu SRT cần dịch (bao gồm id, timestamp, text).
    2. Yêu cầu Gemini dịch sang ngôn ngữ đích, GIỮ NGUYÊN format SRT.
    3. Trích xuất nội dung từ Code Block.
    4. Nối (Append) nội dung đã dịch vào file SRT đích.
    """
    try:
        wait = WebDriverWait(driver, 30)
        
        # Lấy thông tin từ item đầu tiên trong chunk (vì chung 1 file và 1 ngôn ngữ)
        if not chunk: return True
        
        first_item = chunk[0]
        target_lang = first_item.get('lang', 'English')
        save_path = first_item.get('safe_save_path') or first_item.get('save_path')
        
        if not save_path:
            log_callback("❌ Không tìm thấy đường dẫn save_path.")
            return False

        # --- 1. TẠO PROMPT CHUẨN SRT ---
        srt_content_block = ""
        for item in chunk:
            # item chứa: 'id', 'timestamp' (nếu bạn có truyền), 'prompt' (nội dung gốc)
            # Vì trong get_srt_multilanguage_status bạn đang lấy 'prompt' là text đã clean,
            # NHƯNG để dịch SRT chuẩn, ta CẦN truyền cả Timestamp. 
            # Giả định item có 'raw_block' chứa toàn bộ (STT + Time + Text).
            # Nếu không có raw_block, ta phải ghép lại.
            if 'raw_block' in item:
                srt_content_block += f"{item['raw_block']}\n\n"
            else:
                # Fallback nếu bạn chỉ truyền ID và Text (Cần cập nhật lại get_status để lấy raw)
                srt_content_block += f"{item['id']}\n00:00:00,000 --> 00:00:00,000\n{item['prompt']}\n\n"

        prefix_instruction = (
            f"COMMAND: Translate the following subtitle blocks into {target_lang}. "
            "You MUST keep the exact same SRT format (Index number and Timestamp). "
            "ONLY translate the text content. "
            "Output the result strictly inside a Markdown code block (```srt ... ```). "
            "Do not include any explanation or text outside the code block."
        )

        user_prompt = f"{prefix_instruction}\n\nSRT Content:\n{srt_content_block}"

        # --- 2. GỬI TIN NHẮN ---
        try:
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            input_box.clear()
            driver.execute_script("arguments[0].textContent = arguments[1];", input_box, user_prompt)
            
            # Gõ một dấu cách để kích hoạt nút Send của Angular/React
            input_box.send_keys(" ") 
            time.sleep(1)
            
            send_button = driver.find_element(By.XPATH, "//button[contains(@class, 'send-button')]")
            driver.execute_script("arguments[0].click();", send_button)
        except Exception as e:
            log_callback(f"❌ Lỗi khi gửi tin nhắn: {e}")
            return False

        # --- 3. ĐỢI PHẢN HỒI ---
        log_callback(f"⏳ Đang đợi Gemini dịch sang {target_lang}...")
        RESPONSE_SELECTOR = "div.markdown-main-panel[id^='model-response-message-content']"
        
        try:
            old_count = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR))
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)) > old_count)
            last_response_el = driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)[-1]
        except:
            log_callback("❌ Timeout: Không nhận được phản hồi.")
            return False
        
        # Đợi typing effect kết thúc
        last_len = -1
        start_wait = time.time()
        wait_time_limit = config.global_settings["system"].get("wait_time", 30) # Lấy cấu hình
        
        while True:
            curr_len = len(last_response_el.text)
            if curr_len == last_len and curr_len > 0: break
            last_len = curr_len
            time.sleep(2)
            if time.time() - start_wait > wait_time_limit: break

        # --- 4. TRÍCH XUẤT CODE BLOCK ---
        code_elements = last_response_el.find_elements(By.XPATH, ".//pre/code")
        if not code_elements:
            log_callback("❌ Thất bại: Gemini không trả về Code Block.")
            return False

        full_code_content = "\n".join([el.text for el in code_elements]).strip()
        
        # Làm sạch chuỗi block code (bỏ ```srt nếu nó bị dính vào trong pre/code)
        clean_str = re.sub(r'^```[a-zA-Z]*\n', '', full_code_content, flags=re.MULTILINE)
        clean_str = re.sub(r'\n```$', '', clean_str).strip()

        if not clean_str:
            log_callback("⚠️ Code Block rỗng.")
            return False

        # --- 5. LƯU DỒN (APPEND) VÀO FILE SRT ĐÍCH ---
        try:
            # Mở file mode 'a' (append) để nối thêm SRT vào cuối file
            with open(save_path, 'a', encoding='utf-8') as f:
                f.write(clean_str + "\n\n")

            # Đếm số dòng vừa dịch để log
            pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})')
            translated_count = len(pattern.findall(clean_str))
            
            log_callback(f"💾 Đã nối thêm {translated_count} câu ({target_lang}) vào file SRT.")
            return True

        except Exception as e:
            log_callback(f"❌ Lỗi ghi file SRT: {e}")
            return False

    except Exception as e:
        log_callback(f"❌ Lỗi hệ thống: {e}")
        return False