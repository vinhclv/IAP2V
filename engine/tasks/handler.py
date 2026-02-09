import os
import shutil
from engine.tasks.image_to_prompt import process_image_to_prompt
from engine.tasks.image_and_prompt_to_video import process_video_batch
from engine.tasks.srt_to_prompt import process_srt_to_prompt
from engine.tasks.prompt_to_image import process_prompt_to_image
import time
# --- 1. XỬ LÝ ẢNH -> PROMPT ---
def handle_image_to_prompt(driver, file_batch, assets_path, log_callback):
    """
    Xử lý danh sách ảnh để tạo prompt.
    Logic sức khỏe: Dừng nếu lỗi liên tiếp hoặc thất bại toàn tập.
    """
    # 1. Vào trang & Check Login
    try:
        driver.get("https://gemini.google.com/gem/1eGtVu5CR6oCr6OM3Ynf_RCQjvYOHtoEz?usp=sharing")
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
            # 1. Chuẩn bị đường dẫn
            sub_name = os.path.splitext(file_name)[0]
            dest_folder = os.path.join(assets_path, sub_name)
            os.makedirs(dest_folder, exist_ok=True)
            
            dest_img = os.path.join(dest_folder, file_name)
            if not os.path.exists(dest_img): shutil.copy2(item_path, dest_img)
            
            # 2. [SKIP] Kiểm tra nếu đã có prompt.txt rồi thì bỏ qua
            prompt_file = os.path.join(dest_folder, "prompt.txt")
            if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 10:
                log_callback(f"⏭️ Đã có prompt: {file_name} -> Bỏ qua.")
                failed_list.remove(item_path)
                consecutive_errors = 0 # Reset lỗi
                continue

            # 3. Gọi hàm xử lý core
            success = process_image_to_prompt(driver, dest_img, dest_folder, lambda m: log_callback(m))

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

def handle_prompt_to_video(driver, file_batch, assets_path, log_callback):
    # 1. Vào trang & Check Login
    driver.get("https://labs.google/fx/tools/video-fx")
    time.sleep(5)
    
    if "accounts.google.com" in driver.current_url:
        log_callback("❌ Profile bị logout -> Dừng.")
        return False, file_batch # False = Profile Hỏng

    # 2. Chuẩn bị Batch
    CHUNK_SIZE = 3
    chunks = [file_batch[i:i + CHUNK_SIZE] for i in range(0, len(file_batch), CHUNK_SIZE)]
    
    failed_total = []
    consecutive_batch_errors = 0 # Đếm số batch bị lỗi liên tiếp
    
    # 3. Chạy từng Chunk
    for i, chunk in enumerate(chunks):
        # Gọi hàm xử lý cốt lõi
        is_batch_ok, failed_in_chunk = process_video_batch(driver, chunk, None, log_callback)
        
        # Cộng dồn file lỗi vào danh sách tổng
        if failed_in_chunk:
            failed_total.extend(failed_in_chunk)
            
        
        # 1. Tính toán tỷ lệ
        total_items = len(chunk) # Thường là 5
        failed_count = len(failed_in_chunk)
        success_count = total_items - failed_count
        
        if is_batch_ok or (success_count >= total_items / 2):
            
            # Reset bộ đếm lỗi vì Profile vẫn làm việc được
            consecutive_batch_errors = 0
            
            if not is_batch_ok:
                log_callback(f"⚠️ Batch {i+1} không hoàn hảo ({success_count}/{total_items} xong) -> Nhưng >50% nên vẫn giữ Profile.")
        
        else:
            # 3. Trường hợp Fail nặng (< 50% thành công)
            consecutive_batch_errors += 1
            log_callback(f"❌ Batch {i+1} fail (chỉ xong {success_count}/{total_items}).")
            
            if consecutive_batch_errors >= 2:
                log_callback("💀 Profile yếu quá (2 batch fail liên tiếp) -> Dừng.")
                
                # Trả nốt file chưa kịp chạy
                remaining_chunks = chunks[i+1:]
                for c in remaining_chunks:
                    failed_total.extend(c)
                    
                return False, failed_total 
    # 4. Kiểm tra kết quả cuối cùng
    if len(failed_total) == len(file_batch):
        log_callback("❌ Toàn bộ file trong lượt này đều thất bại.")
        return False, failed_total 

    return True, failed_total

def handle_srt_to_prompt(driver, batch, _, log_callback):
    try:
        if "gemini.google.com" not in driver.current_url:
            driver.get("https://gemini.google.com/app")
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
    CHUNK_SIZE = 5

    # Chia batch thành các chunk
    chunks = [batch[i:i + CHUNK_SIZE] for i in range(0, len(batch), CHUNK_SIZE)]

    # 2. Duyệt qua từng Chunk
    for chunk in chunks:
        
        # Lấy ID đầu/cuối để log cho dễ nhìn
        chunk_ids = [item['id'] for item in chunk]
        
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

def handle_prompt_to_image(driver, batch, assets_path, log_callback):
    """
    Xử lý Prompt -> Image. Quản lý vòng lặp và điều phối lỗi.
    """
    # 1. Vào trang & Check Login
    try:
        if "gemini.google.com" not in driver.current_url:
            driver.get("https://gemini.google.com/gem/475dfb0a0b56?usp=sharing")
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
