# engine/batch_processor.py
import threading
import queue
import time
import os
import concurrent.futures

from config import MAX_RETRIES, DEFAULT_PROFILES
from utils.file_ops import get_image_status, get_video_status, get_srt_status
from engine.worker import run_worker_task

class BatchProcessor:
    def __init__(self, stop_event, log_callback, update_status_callback):
        self.stop_event = stop_event
        self.log = log_callback
        self.update_status = update_status_callback
        
        self.task_queue = queue.Queue()
        self.file_lock = threading.Lock()
        self.profile_health = {}
        
        self.current_monitoring_info = None 

    def clear_task_queue(self):
        with self.task_queue.mutex:
            self.task_queue.queue.clear()

    def run_batch_logic(self, project_queue, loop_type, limit, threads, profiles, finished_callback):
        self.profile_health = {p: 0 for p in profiles}
        
        self.log(f"🚀 BẮT ĐẦU CHẠY: {len(project_queue)} DỰ ÁN", "INFO")

        for idx, project in enumerate(project_queue):
            if self.stop_event.is_set(): break
            
            input_path = project["input"]
            output_path = project["output"]
            
            self.update_status(idx, "Running ⏳")
            self.log(f"=== DỰ ÁN {idx+1}/{len(project_queue)}: {os.path.basename(input_path)} ===", "INFO")
            
            self.process_one_folder(input_path, output_path, loop_type, limit, threads, profiles)
            
            if self.stop_event.is_set():
                self.update_status(idx, "Stopped 🛑")
            else:
                self.update_status(idx, "Done ✅")
                self.log(f"🏁 Xong dự án {idx+1}. Nghỉ 5s...", "SUCCESS")
                time.sleep(5)

        finished_callback()

    def process_one_folder(self, inp, out, loop_type, limit, threads, profiles):
        self.current_monitoring_info = (inp, out, loop_type)
        
        self.clear_task_queue()
        self.log(f"🔍 Bắt đầu xử lý: {os.path.basename(inp)}", "INFO")

        while not self.stop_event.is_set():
            # [UPDATE] Dùng match/case (Switch của Python)
            match loop_type:
                case "text":
                    pending, _ = get_image_status(inp, out)
                case "srt":
                    pending, _ = get_srt_status(inp, out)
                case _:
                    pending, _ = get_video_status(out)

            if not pending:
                self.log(f"✅ Dự án {os.path.basename(inp)} hoàn thành!", "SUCCESS")
                break 

            living_profiles = [p for p in profiles if self.profile_health.get(p, 0) < MAX_RETRIES]
            if not living_profiles:
                self.log("❌ Hết Profile sống!", "ERROR"); break

            while not self.task_queue.empty(): self.task_queue.get()
            for f in pending: self.task_queue.put(f)

            cur_threads = min(threads, len(living_profiles))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=cur_threads) as executor:
                futures = []
                for p_name in living_profiles:
                    f = executor.submit(self.continuous_profile_runner, p_name, loop_type, inp, out, limit)
                    futures.append(f)
                
                concurrent.futures.wait(futures)

            if self.stop_event.is_set(): break
            time.sleep(3)
        
        self.current_monitoring_info = None

    def continuous_profile_runner(self, profile_name, loop_type, inp_path, out_path, limit):
        while not self.stop_event.is_set():
            fails = self.profile_health.get(profile_name, 0)
            if fails >= MAX_RETRIES:
                self.log(f"💀 Profile '{profile_name}' chết.", "ERROR"); return 

            candidates = []
            
            with self.file_lock: 
                if loop_type == "srt":
                    while not self.task_queue.empty():
                        candidates.append(self.task_queue.get())
                else:
                    for _ in range(limit):
                        if not self.task_queue.empty(): candidates.append(self.task_queue.get())
                        else: break
                
                if not candidates: return

                match loop_type:
                    case "text": 
                        actual_pending, _ = get_image_status(inp_path, out_path)
                        batch = [item for item in candidates if item in actual_pending]
                    
                    case "srt":
                        actual_pending, _ = get_srt_status(inp_path, out_path)
                        batch = actual_pending # Ném cả file vào luôn vì srt rất nhỏ
                        
                    case _: # video 
                        actual_pending, _ = get_video_status(out_path)
                        batch = [item for item in candidates if item in actual_pending]
                
            if not batch: continue

            self.log(f"▶️ [{profile_name}] Nhận {len(batch)} task...", "INFO")
            is_healthy, failed_items = run_worker_task(
                profile_name, batch, loop_type, out_path, DEFAULT_PROFILES, self.stop_event, self.log
            )

            if failed_items:
                self.log(f"♻️ [{profile_name}] Retry {len(failed_items)} items.", "WARNING")
                with self.file_lock:
                    for item in failed_items: self.task_queue.put(item) 

            if is_healthy: self.profile_health[profile_name] = 0 
            else: self.profile_health[profile_name] += 1

    def monitor_loop(self, update_ui_callback):
        while True:
            if self.current_monitoring_info:
                try:
                    inp, out, loop_type = self.current_monitoring_info
                    
                    match loop_type:
                        case "text":
                            pending, completed = get_image_status(inp, out)
                        case "srt":
                            pending, completed = get_srt_status(inp, out)
                        case _:
                            pending, completed = get_video_status(out)

                    t = len(pending) + len(completed)
                    update_ui_callback(t, len(pending), len(completed))
                    
                except Exception as e:
                    print(f"Monitor Error: {e}")
            
            time.sleep(2)