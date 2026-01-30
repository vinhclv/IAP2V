import os
from browser_setup import init_driver_from_profile
import time
from tasks_handler import handle_image_to_prompt, handle_prompt_to_video

def run_worker_task(profile_folder, file_batch, task_type, assets_path, profiles_dir, stop_event, log_callback):
    """
    Worker đa năng: Chỉ lo việc quản lý vòng đời (Lifecycle) của Driver.
    Logic nghiệp vụ đẩy sang tasks_handler.
    """
    p_path = os.path.join(profiles_dir, profile_folder)
    
    def task_log(msg, level="INFO"):
        log_callback(f"[{profile_folder}] {msg}", level)

    # 1. Khởi tạo Driver
    task_log(f"🚀 Khởi động (Task: {task_type})...")
    driver = init_driver_from_profile(p_path, log_callback=lambda m: task_log(m))
    
    if not driver:
        return False, list(file_batch) # Fail ngay từ đầu

    failed_items = list(file_batch)
    is_healthy = True

    try:
        # 2. ĐIỀU HƯỚNG CHIẾN LƯỢC (ROUTING)
        # Đây là chỗ giúp bạn mở rộng dễ dàng. Thêm task mới chỉ cần thêm if/else
        
        if task_type == "text":
            is_healthy, failed_items = handle_image_to_prompt(driver, file_batch, assets_path, task_log)
            
        elif task_type == "video":
            is_healthy, failed_items = handle_prompt_to_video(driver, file_batch, assets_path, task_log)
            
        elif task_type == "youtube": # Ví dụ mở rộng
             is_healthy, failed_items = handle_upload_youtube(...)
             
        else:
            task_log(f"❌ Loại task '{task_type}' chưa được hỗ trợ!", "ERROR")
            return True, failed_items # Trả về nhưng không đánh dấu hỏng profile

    except Exception as e:
        task_log(f"🔥 CRASH WORKER: {e}", "ERROR")
        is_healthy = False
        failed_items = list(file_batch) # Coi như hỏng hết batch này
        
    finally:
        try: driver.quit()
        except: pass
        task_log("Đóng trình duyệt.", "INFO")

    return is_healthy, failed_items