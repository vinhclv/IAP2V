import os
import time
import json
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def process_srt_to_prompt(driver, chunk, log_callback=print):
    """
    Xử lý gửi Chunk lên Gemini -> Nhận phản hồi -> Parse -> Lưu thẳng vào JSON.
    Có cơ chế lọc bỏ lời dẫn thừa (Intro/Outro) của Gemini.
    """
    try:
        wait = WebDriverWait(driver, 30)
        
        json_output_path = chunk[0].get('json_path')
        if not json_output_path:
            log_callback("❌ Không tìm thấy đường dẫn json_path.")
            return False

        # --- 1. TẠO PROMPT ---
        srt_content_block = ""
        for item in chunk:
            srt_content_block += f"ID {item['id']}: {item['text']}\n"

        user_prompt = (
            f"I have a list of subtitle lines. For EACH line, describe a highly detailed cinematic scene visualizing the text. "
            f"Do not merge lines. Return the result strictly in this format for every line:\n"
            f"ID [number]: [Visual Description]\n\n"
            f"Here is the list:\n"
            f"{srt_content_block}"
        )

        # --- 2. GỬI GEMINI ---
        try:
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            input_box.clear()
        except:
            log_callback("❌ Không tìm thấy ô nhập liệu.")
            return False

        driver.execute_script("arguments[0].textContent = arguments[1];", input_box, user_prompt)
        input_box.send_keys(" ") 
        time.sleep(1)

        try:
            send_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send') or .//mat-icon[text()='send']]")
            driver.execute_script("arguments[0].click();", send_button)
        except:
            input_box.send_keys(Keys.ENTER)

        # --- 3. ĐỢI KẾT QUẢ ---
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

        # A. Regex tách ID và Prompt thô
        # Regex này sẽ lấy cả phần đuôi thừa của ID cuối cùng
        pattern = re.compile(r'ID\s+(\d+):\s*(.*?)(?=(?:ID\s+\d+:)|$)', re.DOTALL | re.IGNORECASE)
        matches = pattern.findall(final_text)
        
        parsed_results = {}
        
        # Các từ khóa để nhận diện câu thừa ở cuối (Footer garbage)
        stop_phrases = [
            "would you like", "do you want", "let me know", 
            "hope this", "here are", "feel free", "generate an image"
        ]

        for pid, ptext in matches:
            clean_text = ptext.strip()
            
            # Xử lý cắt bỏ phần thừa (đặc biệt là ở ID cuối cùng)
            lines = clean_text.split('\n')
            valid_lines = []
            for line in lines:
                # Nếu dòng chứa từ khóa "hỏi thăm" của AI -> Dừng lấy tiếp
                if any(phrase in line.lower() for phrase in stop_phrases):
                    break
                valid_lines.append(line)
            
            final_prompt = "\n".join(valid_lines).strip()
            parsed_results[pid.strip()] = final_prompt

        # B. Chuẩn bị data
        new_entries = []
        for item in chunk:
            sub_id = str(item['id'])
            if sub_id in parsed_results:
                new_entries.append({
                    "STT": sub_id,
                    "Prompt": parsed_results[sub_id]
                })

        if not new_entries:
            log_callback(f"⚠️ Không parse được ID nào.\nRaw: {last_text[:100]}...")
            return False

        # C. Lưu dồn vào JSON
        try:
            current_data = []
            if os.path.exists(json_output_path):
                try:
                    with open(json_output_path, 'r', encoding='utf-8') as f:
                        current_data = json.load(f)
                except: current_data = []

            current_data.extend(new_entries)

            unique_data = {d['STT']: d for d in current_data}.values()
            final_list = list(unique_data)
            
            try: final_list.sort(key=lambda x: int(x.get("STT", 0)))
            except: pass

            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, ensure_ascii=False, indent=4)

            log_callback(f"💾 Đã lưu {len(new_entries)} dòng vào JSON.")
            return True

        except Exception as e:
            log_callback(f"❌ Lỗi ghi file: {e}")
            return False

    except Exception as e:
        log_callback(f"❌ Lỗi Selenium: {e}")
        return False