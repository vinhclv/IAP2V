import os
import shutil
from engine.tasks.gemini_vision import process_image_to_prompt
from engine.tasks.videofx_gen import process_video_batch
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

# --- 2. XỬ LÝ PROMPT -> VIDEO (BATCH) ---
def handle_prompt_to_video(driver, file_batch, assets_path, log_callback):
    """
    Xử lý tạo video theo batch, có cơ chế phát hiện lỗi thông minh hơn.
    """
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


# --- 3. (VÍ DỤ MỞ RỘNG) XỬ LÝ UPLOAD YOUTUBE ---
def handle_upload_youtube(driver, file_batch, assets_path, log_callback):
    # Code xử lý youtube ở đây...
    pass