import os
import time
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

def process_srt_shuffle(driver, chunk, prompt, log_callback=print):
    """
    Cơ chế xử lý Điều hướng (Router):
    1. Lấy thông tin SRT từ chunk.
    2. Gửi cho AI kèm theo danh sách GEM hiện có.
    3. AI trả về JSON chứa [STT, GEM].
    4. Parse JSON của AI, ghép trường "GEM" vào dữ liệu gốc của chunk.
    5. Lưu toàn bộ dữ liệu (STT, time_range, text, GEM...) vào file JSON tổng.
    """
    try:
        wait = WebDriverWait(driver, 30)
        
        json_output_path = chunk[0].get('json_path') # Lấy đường dẫn file json từ chunk
        if not json_output_path:
            log_callback("❌ Không tìm thấy đường dẫn json_path.")
            return False

        # --- 1. TẠO PROMPT ---
        
        # 1.1 Gộp nội dung SRT của chunk hiện tại
        srt_content_block = ""
        for item in chunk:
            srt_content_block += f"STT {item['STT']}: {item['text']}\n"

        # 1.2 Lấy danh sách các Gems tạo ảnh TỪ TRONG CHUNK (thay vì lấy từ config tổng)
        available_gems_info = ""
        
        # Trích xuất mảng "shuffle_gems" từ item đầu tiên trong chunk
        target_gems = chunk[0].get("shuffle_gems", [])
        
        if not target_gems:
            log_callback("⚠️ Cảnh báo: Không tìm thấy 'shuffle_gems' trong dữ liệu đầu vào.")
            
        for gem in target_gems:
            g_name = gem.get("name", "Unknown")
            g_desc = gem.get("description", "Không có mô tả cụ thể")
            # Ép AI phải nhìn thấy đúng tên G1_IMAGE, G2_IMAGE...
            available_gems_info += f"- Tên GEM: '{g_name}' | Chuyên môn/Mô tả: {g_desc}\n"

        # 1.3 Xây dựng Prefix Instruction (Đóng vai trò là System Prompt)
        prefix_instruction = f"""Bạn là một chuyên gia phân tích ngữ cảnh và điều hướng luồng công việc (Router). 
Hiện tại tôi đang có các chuyên gia (Gem) sau đây, mỗi Gem có một thế mạnh riêng:

{available_gems_info}

Nhiệm vụ của bạn:
1. Đọc kỹ từng câu thoại (SRT) được cung cấp bên dưới.
2. Phân tích ngữ cảnh, bối cảnh không gian, cảm xúc và tiềm năng hình ảnh của câu thoại.
3. Với mỗi câu thoại, hãy đưa ra quyết định ĐIỀU HƯỚNG: Chọn ra chính xác 1 GEM phù hợp nhất từ danh sách trên để phụ trách tạo ảnh/xử lý cho câu thoại đó.
4. Trả về kết quả CHỈ DUY NHẤT một mảng JSON nằm trong Markdown code block (```json ... ```). Tuyệt đối không giải thích hay viết thêm bất kỳ văn bản ngoài lề.

Cấu trúc JSON bắt buộc:
[
    {{
        "STT": "<Số thứ tự của câu thoại>",
        "GEM": "<Tên chính xác của GEM được chọn>"
    }}
]

COMMAND: You must output the result strictly inside a Markdown code block (```json ... ```). Do not include any text outside the code block."""

        # 1.4 Gộp thành User Prompt hoàn chỉnh
        user_prompt = f"{prefix_instruction}\n\nĐoạn SRT cần xử lý:\n{srt_content_block}"

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

        # --- 3. ĐỢI PHẢN HỒI XONG ---
        log_callback("⏳ Đang đợi AI điều hướng dữ liệu...")
        RESPONSE_SELECTOR = "div.markdown-main-panel[id^='model-response-message-content']"
        old_count = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR))
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)) > old_count)
        
        last_response_el = driver.find_elements(By.CSS_SELECTOR, RESPONSE_SELECTOR)[-1]
        
        last_len = -1
        start_wait = time.time()
        while True:
            curr_len = len(last_response_el.text)
            if curr_len == last_len and curr_len > 0: 
                break 
            last_len = curr_len
            time.sleep(2)
            if time.time() - start_wait > config.global_settings["system"].get("wait_time", 120): 
                log_callback("⚠️ Timeout: Quá thời gian đợi AI phản hồi.")
                break

        # --- 4. TRÍCH XUẤT VÀ LÀM SẠCH CODE BLOCK ---
        code_elements = last_response_el.find_elements(By.XPATH, ".//pre/code")
        if not code_elements:
            log_callback("❌ False: AI không trả về Code Block nào.")
            return False

        full_code_content = "\n\n".join([el.text for el in code_elements]).strip()
        if not full_code_content:
            log_callback("⚠️ Code Block rỗng.")
            return False

        if "```" in full_code_content:
            full_code_content = re.sub(r'^```[a-zA-Z]*\n', '', full_code_content)
            full_code_content = full_code_content.replace('```', '').strip()

        # --- 5. PARSE JSON TỪ AI & GHÉP (MERGE) VÀO CHUNK GỐC ---
        try:
            ai_results = json.loads(full_code_content)
        except Exception as e:
            log_callback(f"❌ Lỗi parse JSON từ AI trả về: {e}")
            return False

        # Biến list kết quả của AI thành 1 Dictionary (Từ điển) dạng: {"1": "Gem A", "2": "Gem B"} để dễ tra cứu
        gem_mapping = {}
        if isinstance(ai_results, list):
            for res in ai_results:
                stt_val = str(res.get("STT", "")).strip()
                gem_val = res.get("GEM", "Chưa xác định")
                if stt_val:
                    gem_mapping[stt_val] = gem_val

        # Tạo danh sách dữ liệu mới: Giữ nguyên các trường của chunk, nhét thêm "GEM" dạng Object
        final_merged_data = []
        for item in chunk:
            stt_val = str(item.get("STT", "")).strip()
            
            # Khởi tạo dict mới để tránh lỗi tham chiếu chéo
            new_item = item.copy() 
            
            # 1. Lấy tên GEM mà AI đã chọn từ dict gem_mapping
            chosen_gem_name = gem_mapping.get(stt_val, "Default")
            chosen_gem_url = ""
            
            # 2. Tìm URL tương ứng trong mảng shuffle_gems của item hiện tại
            shuffle_gems_list = new_item.get("shuffle_gems", [])
            for g in shuffle_gems_list:
                if g.get("name") == chosen_gem_name:
                    chosen_gem_url = g.get("url", "")
                    break
            
            # 3. Đóng gói trường GEM thành 1 Object chứa Name và URL
            new_item["GEM"] = {
                "name": chosen_gem_name,
                "url": chosen_gem_url
            }
            
            # 4. DỌN RÁC: Xóa các trường tạm khỏi file JSON cuối
            if "json_path" in new_item:
                del new_item["json_path"]
                
            if "shuffle_gems" in new_item:
                del new_item["shuffle_gems"]
            
            final_merged_data.append(new_item)

        # --- 6. LƯU DỒN (APPEND) VÀO FILE JSON ---
        try:
            os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
            
            current_data = []
            if os.path.exists(json_output_path):
                try:
                    with open(json_output_path, 'r', encoding='utf-8') as f:
                        current_data = json.load(f)
                except Exception:
                    current_data = []

            # Nối dữ liệu mới vào dữ liệu cũ
            current_data.extend(final_merged_data)

            # Ghi ra file theo chuẩn JSON
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)

            log_callback(f"💾 Đã phân luồng và lưu {len(final_merged_data)} đoạn SRT vào: {os.path.basename(json_output_path)}")
            return True

        except Exception as e:
            log_callback(f"❌ Lỗi khi ghi file tổng hợp: {e}")
            return False

    except Exception as e:
        log_callback(f"❌ Lỗi hệ thống trong process_srt_shuffle: {e}")
        return False