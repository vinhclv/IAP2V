import os
import shutil
from engine.tasks.image_to_prompt import process_image_to_prompt
from engine.tasks.image_and_prompt_to_video import process_video_batch, setup_video_creation_mode, inject_radar_js
from engine.tasks.srt_to_prompt import process_srt_to_prompt
from engine.tasks.prompt_to_image import process_prompt_to_image
from engine.tasks.pair_image_to_prompt import process_pair_images_to_prompt
from engine.tasks.srt_to_image import process_srt_item_to_image
from engine.tasks.srt_to_multilanguage import process_srt_multilanguage
from engine.tasks.srt_to_shuffle import process_srt_shuffle
import time
import re
import random
import config
from urllib.parse import urlparse

def handle_image_to_prompt(driver, file_batch, assets_path, prefix_prompt, url, log_callback):
    """
    Xử lý danh sách ảnh để tạo prompt.
    Logic sức khỏe: Dừng nếu lỗi liên tiếp hoặc thất bại toàn tập.
    """
    # 1. Vào trang & Check Login
    try:
        driver.get(url)
        time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Lỗi mở trang Gemini: {e}")
        return False, file_batch

    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile bị logout -> Dừng.")
        return False, file_batch # Fail session

    failed_list = list(file_batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5 # Ngưỡng lỗi cho phép liên tiếp
    
    for item_path in file_batch:
        file_name = os.path.basename(item_path)
        log_callback(f"▶️ [Text] Xử lý: {file_name}")
        
        try:
            file_name = os.path.basename(item_path)
            sub_name = os.path.splitext(file_name)[0]
            
            # --- 1. KIỂM TRA SKIP (FILE PHẲNG) ---
            prompt_file = os.path.join(assets_path, f"{sub_name}_prompt.txt")
            
            if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 10:
                log_callback(f"⏭️ Đã có prompt: {sub_name}_prompt.txt -> Skip.")
                if item_path in failed_list: failed_list.remove(item_path)
                continue

            # --- 2. GỌI XỬ LÝ (DÙNG TRỰC TIẾP item_path GỐC) ---
            log_callback(f"▶️ Đang phân tích: {file_name}")

            # 3. Gọi hàm xử lý core
            # Truyền assets_path làm thư mục đích thay vì folder con
            success = process_image_to_prompt(driver, item_path, assets_path, lambda m: log_callback(m))
            if success:
                log_callback(f"✅ Xong: {file_name}")
                if item_path in failed_list: failed_list.remove(item_path)
                consecutive_errors = 0 # Reset lỗi vì vừa thành công
            else:
                consecutive_errors += 1
                log_callback(f"⚠️ Lỗi xử lý ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {file_name}")
                
                # [STOP LOSS] Nếu lỗi liên tiếp quá nhiều -> Dừng Profile
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log_callback("💀 Gemini lỗi liên tiếp -> Đánh dấu Profile hỏng.")
                    return False, failed_list
                driver.refresh()
                time.sleep(5)

        except Exception as e:
            log_callback(f"❌ Exception nghiêm trọng: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                return False, failed_list

    # 4. Kiểm tra tổng kết
    # Nếu chạy hết mà không được cái nào (Fail 100%) -> Profile hỏng
    if len(failed_list) == len(file_batch):
        log_callback("❌ Thất bại toàn tập (0/{}) -> Profile hỏng.".format(len(file_batch)))
        return False, failed_list

    # Nếu làm được ít nhất 1 cái (hoặc skip do đã có) -> Profile OK
    return True, failed_list

async def handle_prompt_to_video_async(context, file_batch, assets_path, prefix_prompt, url, log_callback):
    """
    Xử lý batch prompt sang video.
    Băm nhỏ cục file_batch lớn (VD: 50 object) thành các mẻ nhỏ 4 object để tránh spam.
    Lưu ý: tham số đầu tiên nhận vào là Playwright BrowserContext.
    """
    # 2. THÊM 'await' KHI TẠO TAB MỚI
    page = await context.new_page() 
    # THÊM DÒNG NÀY VÀO HÀM HANDLE CỦA BẠN:
    # 🛡️ TIÊM MÃ XÓA WEBDRIVER (Nhẹ nhàng, không làm vỡ giao diện)
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    try:
        # 3. THÊM 'await' CHO CÁC LỆNH CỦA TRÌNH DUYỆT
        await page.goto(url, timeout=60000) 
        await page.wait_for_timeout(5000)   
        
        # Check current_url bằng page.url (Thuộc tính này không cần await)
        if "accounts.google.com" in page.url:
            log_callback("❌ Profile bị logout -> Dừng.")
            return False, file_batch 


        CHUNK_SIZE = 4
        all_failed_objects = []
        total_items = len(file_batch)
        total_chunks = (total_items + CHUNK_SIZE - 1) // CHUNK_SIZE

        log_callback(f"📦 Bắt đầu xử lý {total_items} video, chia làm {total_chunks} chunk (mỗi chunk {CHUNK_SIZE} video).")

        await setup_video_creation_mode(page)
    
        # 🎯 Tiêm JS Radar vào trang web ngay trước khi bắt đầu nhập prompt
        await inject_radar_js(page)
        
        # 4. VÒNG LẶP CHIA NHỎ VÀ ĐẨY VÀO HÀM CỐT LÕI
        for i in range(0, total_items, CHUNK_SIZE):
            chunk = file_batch[i:i + CHUNK_SIZE]
            chunk_index = (i // CHUNK_SIZE) + 1
            
            log_callback(f"▶️ --- ĐANG CHẠY CHUNK {chunk_index}/{total_chunks} ---")

            # Gọi hàm xử lý cốt lõi cho đúng 4 object này
            is_chunk_ok, failed_in_chunk = await process_video_batch(
                page, 
                chunk, 
                assets_path, 
                log_callback
            )
            
            # Gom những object bị xịt trong chunk này vào danh sách tổng
            all_failed_objects.extend(failed_in_chunk)

            # Nếu có video xịt -> Có khả năng bị Google kẹt reCAPTCHA -> Tẩy trắng
            if len(failed_in_chunk) > 1:
                log_callback("⚠️ Phát hiện kẹt video! Đang tẩy trắng reCAPTCHA và reset giao diện...")
                
                # 1. Bắn tỉa Token
                await page.evaluate("""
                    localStorage.removeItem('_grecaptcha');
                    sessionStorage.clear();
                """)
                
                # 2. Tải lại trang để xóa hoàn toàn trạng thái lỗi đang lưu trên RAM của Web
                await page.reload(timeout=60000)
                await page.wait_for_timeout(4000)
                
                # 3. QUAN TRỌNG: Thiết lập lại Giao diện và Radar vì trang web vừa bị F5
                # await setup_video_creation_mode(page)
                await inject_radar_js(page)
                
                log_callback("✅ Tẩy trắng thành công! Sẵn sàng cho Chunk tiếp theo.")

            # --- NGHỈ NGƠI CHỐNG SPAM ---
            # Nếu chưa phải là chunk cuối cùng thì cho nghỉ 15-25 giây rồi mới chạy chunk tiếp
            if i + CHUNK_SIZE < total_items:
                cooldown = random.randint(5000, 7000)
                log_callback(f"💤 Xong Chunk {chunk_index}. Nghỉ giải lao {cooldown//1000}s trước khi chạy mẻ tiếp theo...")
                await page.wait_for_timeout(cooldown)

        # 5. TỔNG KẾT SAU KHI CHẠY XONG TẤT CẢ CÁC CHUNK
        if len(all_failed_objects) == total_items:
            log_callback("❌ Toàn bộ file trong lượt này đều thất bại.")
            return False, all_failed_objects 

        # Nếu có xịt vài cái thì báo true, và trả về danh sách xịt để sau này retry
        return True, all_failed_objects

    except Exception as e:
        log_callback(f"❌ Lỗi ở handle_prompt_to_video: {e}")
        return False, file_batch
        
    finally:
        # 6. THÊM 'await' KHI ĐÓNG TAB
        try:
            await page.close()
        except:
            pass

def handle_srt_to_prompt(driver, batch, assets_path, prefix_prompt, url, log_callback):
    try:
        if "gemini.google.com" not in driver.current_url:
            driver.get(url)
            time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Error opening Gemini page: {e}")
        return False, batch

    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile logged out -> Stopping.")
        return False, batch

    failed_list = list(batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3  # Ngưỡng lỗi liên tiếp (Refresh 3 lần không được thì dừng)
    CHUNK_SIZE = config.global_settings["system"]["loop_limit"]

    # Chia batch thành các chunk
    chunks = [batch[i:i + CHUNK_SIZE] for i in range(0, len(batch), CHUNK_SIZE)]

    # 2. Duyệt qua từng Chunk
    for chunk in chunks:
        
        # Lấy ID đầu/cuối để log cho dễ nhìn
        chunk_ids = [item['STT'] for item in chunk]
        
        # [QUAN TRỌNG] Vòng lặp While để Retry lại chính Chunk này nếu lỗi
        while True:
            try:
                # 4. Gọi hàm xử lý (Gửi Chunk lên -> Nhận kết quả)
                success = process_srt_to_prompt(driver, chunk, log_callback)

                if success:
                    log_callback(f"✅ Xong chunk ID: {chunk_ids[0]} - {chunk_ids[-1]}")
                    
                    # Xóa các item đã xong khỏi danh sách failed
                    for item in chunk:
                        if item in failed_list: 
                            failed_list.remove(item)
                    
                    consecutive_errors = 0 # Reset lỗi
                    break # [BREAK] Thoát vòng lặp While để sang Chunk tiếp theo
                
                else:
                    # Nếu thất bại
                    consecutive_errors += 1
                    log_callback(f"⚠️ Lỗi xử lý chunk {chunk_ids[0]}-{chunk_ids[-1]} (Lần {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")
                    
                    # Nếu lỗi quá nhiều lần -> Dừng toàn bộ
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        log_callback("💀 Gemini lỗi liên tiếp -> Đánh dấu Profile hỏng.")
                        return False, failed_list
                    
                    # Refresh trang
                    log_callback("♻️ Refresh trang và thử lại chunk cũ...")
                    driver.refresh()
                    time.sleep(5)

            except Exception as e:
                log_callback(f"❌ Exception nghiêm trọng: {e}")
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    return False, failed_list
                driver.refresh()
                time.sleep(5)

    # 4. Kiểm tra tổng kết
    if len(failed_list) == len(batch):
        log_callback("❌ Thất bại toàn tập (0/{}) -> Profile hỏng.".format(len(batch)))
        return False, failed_list

    return True, failed_list

def handle_prompt_to_image(driver, batch, assets_path, prefix_prompt, url, log_callback):
    """
    Xử lý Prompt -> Image. Quản lý vòng lặp và điều phối lỗi.
    """
    # 1. Vào trang & Check Login
    try:
        if "gemini.google.com" not in driver.current_url:
            driver.get(url)
            time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Lỗi mở trang: {e}")
        return False, batch

    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile bị logout -> Dừng.")
        return False, batch

    failed_total = list(batch) # Giả định ban đầu là tất cả đều lỗi
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 7 # Ngưỡng lỗi liên tiếp để hủy Profile

    # 2. Chạy vòng lặp xử lý từng Item đơn lẻ
    for item in batch:
        stt = item['id']
        log_callback(f"🎨 [Image] Đang tạo ảnh cho STT {stt}...")

        # Gọi hàm xử lý đơn lẻ từ gemini_vision.py
        success = process_prompt_to_image(driver, item, log_callback)

        if success:
            log_callback(f"✅ Xong ảnh STT: {stt}")
            if item in failed_total:
                failed_total.remove(item)
            consecutive_errors = 0 # Reset lỗi liên tiếp
        else:
            consecutive_errors += 1
            log_callback(f"⚠️ Lỗi xử lý STT {stt} ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")
            
            # Nếu lỗi liên tiếp quá nhiều -> Dừng Profile ngay lập tức
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                log_callback("💀 Profile lỗi liên tiếp quá nhiều -> Dừng.")
                return False, failed_total
            
            # Refresh trang để giải phóng bộ nhớ hoặc fix kẹt
            driver.refresh()
            time.sleep(5)

    # 3. Kiểm tra tổng kết
    if len(failed_total) == len(batch):
        log_callback("❌ Thất bại toàn bộ batch.")
        return False, failed_total

    return True, failed_total

def handle_2_image_to_prompt(driver, batch, assets_path, prefix_prompt, url, log_callback):
    """
    Xử lý danh sách cặp ảnh (1-2, 2-3...) để tạo prompt nối.
    """
    # 1. Vào trang & Check Login
    try:
        # Dùng URL này để vào thẳng giao diện chat mới (hoặc url mặc định)
        if "gemini.google.com" not in driver.current_url:
            driver.get(url)
            time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Lỗi mở trang Gemini: {e}")
        return False, batch

    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile bị logout -> Dừng.")
        return False, batch

    failed_list = list(batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5 
    
    for item in batch:
        pair_id = item['pair_id']        # Ví dụ: "1-2"
        img1_src = item['img1_path']     # Đường dẫn gốc ảnh 1
        img2_src = item['img2_path']     # Đường dẫn gốc ảnh 2
        
        log_callback(f"▶️ [Pair] Đang phân tích cặp: {pair_id}")
        
        try:
            # --- 1. KIỂM TRA SKIP (FILE PHẲNG) ---
            # File kết quả mong muốn: assets_path / 1-2_prompt.txt
            prompt_file = os.path.join(assets_path, f"{pair_id}_prompt.txt")
            
            if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 10:
                log_callback(f"⏭️ Đã có prompt cặp {pair_id} -> Skip.")
                if item in failed_list: failed_list.remove(item)
                consecutive_errors = 0
                continue

            # --- 2. GỌI XỬ LÝ CORE ---
            # Truyền item_path gốc và thư mục assets_path chung
            success = process_pair_images_to_prompt(driver, img1_src, img2_src, assets_path, pair_id, log_callback)

            if success:
                log_callback(f"✅ Xong cặp: {pair_id}")
                if item in failed_list: failed_list.remove(item)
                consecutive_errors = 0 
            else:
                consecutive_errors += 1
                log_callback(f"⚠️ Lỗi xử lý ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {pair_id}")
                
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log_callback("💀 Gemini lỗi liên tiếp -> Dừng Profile.")
                    return False, failed_list
                
                driver.refresh()
                time.sleep(5)

        except Exception as e:
            log_callback(f"❌ Exception nghiêm trọng tại cặp {pair_id}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                return False, failed_list
            driver.refresh()
            time.sleep(5)

    # 4. Kiểm tra tổng kết
    if len(failed_list) == len(batch):
        log_callback("❌ Thất bại toàn tập.")
        return False, failed_list

    return True, failed_list

def handle_srt_to_image(driver, batch, assets_path, prefix_prompt, url, log_callback):
    """
    Xử lý danh sách task từ SRT -> Image.
    Input: batch là danh sách các dict {'id', 'prompt', 'save_path', ...}
    """
    # 1. Vào trang & Check Login
    try:
        # URL custom bạn cung cấp
        driver.get(url)
        time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Lỗi mở trang: {e}")
        return False, batch

    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile bị logout -> Dừng.")
        return False, batch

    failed_list = list(batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5 
    
    # --- 2. VÒNG LẶP XỬ LÝ TỪNG DÒNG SUB ---
    for item in batch:
        # Lấy dữ liệu từ item (được tạo ra bởi get_srt_image_status)
        item['prompt'] = f"{prefix_prompt} {item['prompt']}"
        stt = item['id']
        text_content = item['prompt'] # Đây là nội dung sub
        save_path = item['save_path']
        output_folder = item['output_folder']
        
        # Hiển thị log
        short_text = (text_content[:40] + '..') if len(text_content) > 40 else text_content
        log_callback(f"▶️ [SRT] STT {stt}: {short_text}")
        
        try:
            # Tạo thư mục nếu chưa có
            os.makedirs(output_folder, exist_ok=True)
            
            # Gọi hàm xử lý core dành riêng cho SRT
            success = process_srt_item_to_image(driver, item, log_callback)

            if success:
                log_callback(f"✅ Xong STT {stt}")
                if item in failed_list: failed_list.remove(item)
                consecutive_errors = 0 
                
                # Refresh định kỳ để tránh lag (cứ 30 ảnh refresh 1 lần)
                if int(stt) % 30 == 0:
                    driver.refresh()
                    time.sleep(4)
            else:
                consecutive_errors += 1
                log_callback(f"⚠️ Lỗi STT {stt} ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")
                
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log_callback("💀 Lỗi liên tiếp quá nhiều -> Dừng.")
                    return False, failed_list
                
                driver.refresh()
                time.sleep(5)

        except Exception as e:
            log_callback(f"❌ Exception tại STT {stt}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                return False, failed_list
            driver.refresh()
            time.sleep(5)

    if len(failed_list) == len(batch):
        return False, failed_list

    return True, failed_list

def handle_srt_multilanguage(driver, batch, assets_path, prefix_prompt, url, log_callback):
    """
    Xử lý danh sách các Task dịch đa ngôn ngữ.
    Mỗi item trong batch đại diện cho 1 ngôn ngữ của 1 file SRT gốc.
    """
    try:
        if "gemini.google.com" not in driver.current_url:
            driver.get(url)
            time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Lỗi mở trang: {e}")
        return False, batch

    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile bị logout -> Dừng.")
        return False, batch

    failed_list = list(batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3 

    # Lặp qua từng Task (Từng yêu cầu dịch file sang 1 ngôn ngữ)
    for task_item in batch:
        srt_path = task_item['srt_path']
        lang = task_item['lang']
        save_path = task_item['save_path']
        
        log_callback(f"▶️ Bắt đầu dịch: {os.path.basename(srt_path)} -> {lang}")

        # 1. Đọc nội dung file gốc để lấy các block SRT
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)', re.DOTALL)
            # Lấy nguyên cục block text
            raw_blocks = [match.group(0) for match in pattern.finditer(content)]
        except Exception as e:
            log_callback(f"❌ Lỗi đọc file gốc: {e}")
            consecutive_errors += 1
            continue

        # Nếu file đích đã có nội dung (do đang dịch dở bị đứt mạng), ta cần tính xem đã dịch đến đâu
        # Để không phải dịch lại từ đầu
        start_index = 0
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r', encoding='utf-8') as f_out:
                    out_content = f_out.read()
                out_matches = pattern.findall(out_content)
                start_index = len(out_matches)
                if start_index > 0:
                    log_callback(f"⏭️ File đã dịch {start_index}/{len(raw_blocks)} câu. Tiếp tục dịch phần còn lại...")
            except: pass

        blocks_to_translate = raw_blocks[start_index:]
        if not blocks_to_translate:
            log_callback(f"✅ File {lang} đã hoàn thành trước đó.")
            if task_item in failed_list: failed_list.remove(task_item)
            continue

        # 2. CHIA CHUNK NỘI DUNG BÊN TRONG FILE
        LINES_PER_CHUNK = config.global_settings["system"].get("chunk_size", 20)
        content_chunks = [blocks_to_translate[i:i + LINES_PER_CHUNK] for i in range(0, len(blocks_to_translate), LINES_PER_CHUNK)]

        task_success = True

        for chunk_idx, content_chunk in enumerate(content_chunks):
            # Tạo data payload cho hàm process core
            # Hàm process_srt_multilanguage yêu cầu đầu vào là list dict có chứa 'lang', 'save_path' và 'raw_block'
            chunk_payload = []
            for block in content_chunk:
                chunk_payload.append({
                    "lang": lang,
                    "save_path": save_path,
                    "raw_block": block
                })

            log_callback(f"🔄 Đang gửi phần {chunk_idx + 1}/{len(content_chunks)} lên Gemini...")
            
            # [QUAN TRỌNG] Vòng lặp Retry cho 1 Chunk nội dung
            chunk_retry = 0
            chunk_ok = False
            while chunk_retry < MAX_CONSECUTIVE_ERRORS:
                # Gọi hàm core bạn đã viết ở bước trước
                success = process_srt_multilanguage(driver, chunk_payload, log_callback)

                if success:
                    consecutive_errors = 0
                    chunk_ok = True
                    break # Thoát vòng lặp retry
                else:
                    chunk_retry += 1
                    consecutive_errors += 1
                    log_callback(f"⚠️ Lỗi phần {chunk_idx + 1} (Lần {chunk_retry}/{MAX_CONSECUTIVE_ERRORS})")
                    
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        log_callback("💀 Profile lỗi liên tục -> Dừng.")
                        return False, failed_list
                    
                    driver.refresh()
                    time.sleep(5)
            
            # Nếu retry đủ 3 lần mà cái phần nhỏ này vẫn fail -> Cả cái Task file này coi như Fail
            if not chunk_ok:
                task_success = False
                break 

        # 3. Kết luận cho Task File này
        if task_success:
            log_callback(f"🎉 Hoàn thành xuất sắc bản dịch: {lang}")
            if task_item in failed_list: failed_list.remove(task_item)
        else:
            log_callback(f"❌ Thất bại khi dịch bản {lang}.")

    # 4. Kiểm tra tổng kết Profile
    if len(failed_list) == len(batch):
        return False, failed_list

    return True, failed_list

def handle_srt_shuffle(driver, batch, assets_path, prompt, url, log_callback):
    """
    Xử lý gửi dữ liệu để xáo trộn (shuffle) SRT.
    """
    
    try:
        if "gemini.google.com" not in driver.current_url:
            driver.get(url)
            time.sleep(5)
    except Exception as e:
        log_callback(f"❌ Error opening Gemini page: {e}")
        return False, batch

    # Kiểm tra trạng thái đăng xuất
    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile đã bị đăng xuất -> Dừng xử lý.")
        return False, batch

    failed_list = list(batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3  

    # 3. Lấy cấu hình Chunk Size
    try:
        CHUNK_SIZE = config.global_settings["system"]["loop_limitt"]
    except Exception:
        CHUNK_SIZE = 10

    # Chia batch thành các chunk
    chunks = [batch[i:i + CHUNK_SIZE] for i in range(0, len(batch), CHUNK_SIZE)]

    # 4. Duyệt qua từng Chunk
    for chunk in chunks:
        chunk_ids = [item.get('STT', 'Unknown') for item in chunk]
        
        while True:
            try:
                # Gọi hàm xử lý UI thực tế (truyền thêm prompt)
                success = process_srt_shuffle(driver, chunk, prompt, log_callback)

                if success:
                    log_callback(f"✅ Xong Shuffle STT: {chunk_ids[0]} - {chunk_ids[-1]}")
                    
                    for item in chunk:
                        if item in failed_list: 
                            failed_list.remove(item)
                    
                    consecutive_errors = 0 
                    break 
                
                else:
                    consecutive_errors += 1
                    log_callback(f"⚠️ Lỗi xử lý Shuffle chunk {chunk_ids[0]}-{chunk_ids[-1]} (Lần {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")
                    
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        log_callback("💀 AI lỗi liên tiếp -> Đánh dấu Profile hỏng.")
                        return False, failed_list
                    
                    log_callback("♻️ Refresh trang và thử lại chunk cũ...")
                    driver.refresh()
                    time.sleep(5)

            except Exception as e:
                log_callback(f"❌ Exception nghiêm trọng: {e}")
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    return False, failed_list
                driver.refresh()
                time.sleep(5)

    # 5. Kiểm tra tổng kết
    if len(failed_list) == len(batch):
        log_callback(f"❌ Thất bại toàn tập (0/{len(batch)}) -> Profile hỏng.")
        return False, failed_list

    return True, failed_list

def handle_shuffle_image(driver, batch, assets_path, prompt, default_url, log_callback):
    """
    Xử lý tạo ảnh từ Prompt đã xáo trộn (Shuffle ➡ Image).
    Mỗi item trong batch có thể có một URL (GEM) khác nhau.
    """
    failed_list = list(batch)
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3 

    # Lặp qua từng Task (Từng yêu cầu tạo 1 ảnh từ 1 Prompt)
    for task_item in batch:

        output_folder = task_item.get('output_folder', '')
        
        # Dùng .get() linh hoạt đề phòng trường hợp key là 'id' hoặc 'STT'
        idx = task_item.get('id')
        
        # [QUAN TRỌNG] Lấy URL cụ thể của riêng Task này
        target_url = task_item.get('gem_url') or default_url
        gem_name = task_item.get('gem_name', 'Default GEM')

        log_callback(f"▶️ Bắt đầu xử lý STT {idx} | GEM: {gem_name}")

        # --- 1. ĐIỀU HƯỚNG THEO TỪNG TASK ---
        try:
            if "gemini.google.com" not in driver.current_url:
                driver.get(target_url)
                time.sleep(5)
        except Exception as e:
            log_callback(f"❌ Lỗi mở trang: {e}")
            return False, batch

        # --- 2. TẠO THƯ MỤC ---
        try:
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
        except Exception as e:
            log_callback(f"❌ Lỗi tạo thư mục {output_folder}: {e}")
            continue

        # --- 3. VÒNG LẶP RETRY CHO 1 TASK ---
        task_retry = 0
        task_ok = False
        
        while task_retry < MAX_CONSECUTIVE_ERRORS:
            # Gọi hàm core xử lý UI (Lưu ý: Bạn có thể cần truyền thêm tham số prompt cấu hình chung nếu muốn)
            success = process_prompt_to_image(driver, task_item,log_callback)

            if success:
                consecutive_errors = 0
                task_ok = True
                break # Thoát vòng lặp retry, qua STT tiếp theo
            else:
                task_retry += 1
                consecutive_errors += 1
                log_callback(f"⚠️ Lỗi tạo ảnh {idx} (Lần {task_retry}/{MAX_CONSECUTIVE_ERRORS})")
                
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log_callback("💀 Lỗi liên tục quá nhiều lần -> Dừng.")
                    return False, failed_list
                
                log_callback("♻️ Refresh lại trang để thử lại...")
                driver.refresh()
                time.sleep(5)
        
        # --- 4. KẾT LUẬN CHO TASK NÀY ---
        if task_ok:
            log_callback(f"🎉 Hoàn thành tạo ảnh: {idx}.jpg")
            if task_item in failed_list: 
                failed_list.remove(task_item)
        else:
            log_callback(f"❌ Thất bại hoàn toàn khi tạo ảnh {idx}.")

    # Kiểm tra tổng kết Profile
    if len(failed_list) == len(batch):
        return False, failed_list

    return True, failed_list