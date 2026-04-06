import os
from engine.browser import init_driver_from_profile
import time
from engine.tasks.handler import handle_image_to_prompt, handle_prompt_to_video, handle_srt_to_prompt, handle_prompt_to_image, handle_2_image_to_prompt, handle_srt_to_image, handle_srt_multilanguage, handle_srt_shuffle, handle_shuffle_image
def run_worker_task(profile_folder, batch, task_type, assets_path, prompt, url, profiles_dir, stop_event, log_callback):
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
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    """
    })
    if not driver:
        return False, list(batch) # Fail ngay từ đầu

    failed_items = list(batch)
    is_healthy = True
    prompt = prompt or ""
    try:
        # 2. ĐIỀU HƯỚNG CHIẾN LƯỢC (ROUTING)
        # Đây là chỗ giúp bạn mở rộng dễ dàng. Thêm task mới chỉ cần thêm if/else
        
        if task_type == "image_prompt":
            is_healthy, failed_items = handle_image_to_prompt(driver, batch, assets_path, prompt, url, task_log)
            
        elif task_type == "prompt_video":
            is_healthy, failed_items = handle_prompt_to_video(driver, batch, assets_path, prompt, url, task_log)
            
        elif task_type == "srt_prompt": 
            is_healthy, failed_items = handle_srt_to_prompt(driver, batch, assets_path, prompt, url, task_log)

        elif task_type == "prompt_image":
            is_healthy, failed_items = handle_prompt_to_image(driver, batch, assets_path, prompt, url, task_log)
            
        elif task_type == "2_image_prompt":
            is_healthy, failed_items = handle_2_image_to_prompt(driver, batch, assets_path, prompt, url, task_log)

        elif task_type == "srt_image":
            is_healthy, failed_items = handle_srt_to_image(driver, batch, assets_path, prompt, url, task_log)

        elif task_type == "srt_multilanguage":
            is_healthy, failed_items = handle_srt_multilanguage(driver, batch, assets_path, prompt, url, task_log)
        
        elif task_type == "srt_shuffle":
            is_healthy, failed_items = handle_srt_shuffle(driver, batch, assets_path, prompt, url, task_log)
        
        elif task_type == "shuffle_image":
            is_healthy, failed_items = handle_shuffle_image(driver, batch, assets_path, prompt, url, task_log)
        else:
            task_log(f"❌ Loại task '{task_type}' chưa được hỗ trợ!", "ERROR")
            return True, failed_items # Trả về nhưng không đánh dấu hỏng profile

    except Exception as e:
        task_log(f"🔥 CRASH WORKER: {e}", "ERROR")
        is_healthy = False
        failed_items = list(batch) # Coi như hỏng hết batch này
        
    finally:
        try: driver.quit()
        except: pass
        task_log("Đóng trình duyệt.", "INFO")

    return is_healthy, failed_items