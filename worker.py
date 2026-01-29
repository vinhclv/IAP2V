import os
import time
import shutil
from browser_setup import init_driver_from_profile
from image_to_prompt import process_image_to_prompt
from image_and_prompt_to_video import generate_video_for_file

def run_worker_task(profile_folder, file_batch, loop_type, assets_path, profiles_dir, stop_event, log_callback):
    """
    Hàm worker chạy trong luồng riêng.
    Trả về: (is_healthy, failed_items)
      - is_healthy: True (Profile khỏe), False (Cần thay thế).
      - failed_items: Danh sách file chưa hoàn thành (để trả về Queue).
    """
    p_path = os.path.join(profiles_dir, profile_folder)
    
    def task_log(msg, level="INFO"):
        log_callback(f"[{profile_folder}] {msg}", level)

    is_profile_healthy = True 
    consecutive_errors = 0 
    MAX_CONSECUTIVE_ERRORS = 3

    # [QUAN TRỌNG] Tạo danh sách bản sao để theo dõi file nào thất bại/chưa làm
    # Ban đầu giả định tất cả đều thất bại. Làm xong cái nào thì xóa cái đó đi.
    failed_items = list(file_batch)

    # 1. Khởi tạo Driver
    task_log("Đang khởi động trình duyệt...", "INFO")
    driver = init_driver_from_profile(p_path, log_callback=lambda m: task_log(m, "INFO"))
    
    if not driver:
        task_log("❌ Không mở được Driver -> Trả lại toàn bộ batch", "ERROR")
        return False, failed_items # Trả về False + Toàn bộ file chưa làm

    try:
        if loop_type == "text":
            url = "https://gemini.google.com/gem/1SxwK59ZujL2Y3DgrooTlI8IUzor7TMSq?usp=sharing"
        else:
            url = "https://labs.google/fx/tools/video-fx"
            
        driver.get(url)
        time.sleep(5)

        if "accounts.google.com" in driver.current_url:
             task_log("⚠️ Bị văng ra trang Login -> Profile hết hạn!", "ERROR")
             is_profile_healthy = False

        if is_profile_healthy:
            for item_path in file_batch:
                if stop_event.is_set(): 
                    task_log("🛑 Nhận lệnh dừng.", "WARNING")
                    break
                
                # Kiểm tra ngưỡng lỗi liên tiếp
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    task_log(f"💀 Lỗi {consecutive_errors} lần liên tiếp -> Dừng Batch, trả lại file thừa.", "ERROR")
                    is_profile_healthy = False # Đánh dấu hỏng
                    break 
                
                file_name = os.path.basename(item_path)
                task_log(f"▶️ Xử lý: {file_name}", "INFO")
                success = False

                try:
                    if loop_type == "text":
                        sub_name = os.path.splitext(file_name)[0]
                        dest_folder = os.path.join(assets_path, sub_name)
                        os.makedirs(dest_folder, exist_ok=True)
                        dest_img = os.path.join(dest_folder, file_name)
                        if not os.path.exists(dest_img): shutil.copy2(item_path, dest_img)
                        
                        success = process_image_to_prompt(driver, dest_img, dest_folder, log_callback=lambda m: task_log(m))

                    else: # VIDEO
                        parent_folder = os.path.dirname(item_path)
                        prompt_path = os.path.join(parent_folder, "prompt.txt")
                        video_out_dir = os.path.join(parent_folder, "video")
                        if not os.path.exists(video_out_dir): os.makedirs(video_out_dir)

                        if os.path.exists(prompt_path):
                            with open(prompt_path, "r", encoding="utf-8") as f: 
                                prompt_text = f.read().strip()
                            generate_video_for_file(driver, item_path, prompt_text, video_out_dir)
                            success = True
                        else:
                            task_log(f"⚠️ Bỏ qua {file_name}: Thiếu prompt.txt", "WARNING")
                            success = True 
                            pass

                except Exception as e:
                    task_log(f"❌ Lỗi xử lý file {file_name}: {e}", "ERROR")
                
                # --- CẬP NHẬT TRẠNG THÁI ---
                if success:
                    task_log(f"✅ Xong: {file_name}", "SUCCESS")
                    consecutive_errors = 0
                    # [QUAN TRỌNG] Xóa khỏi danh sách nợ vì đã làm xong
                    if item_path in failed_items:
                        failed_items.remove(item_path)
                else:
                    consecutive_errors += 1
                    task_log(f"⚠️ Lỗi liên tiếp: {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}", "WARNING")

    except Exception as e:
        task_log(f"🔥 CRASH TRÌNH DUYỆT: {e}", "ERROR")
        is_profile_healthy = False
        
    finally:
        try: driver.quit()
        except: pass
        task_log("Đã đóng session.", "INFO")
    
    # Trả về: Trạng thái Profile + Danh sách các file chưa xong
    return is_profile_healthy, failed_items