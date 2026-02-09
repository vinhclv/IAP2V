# ui/app_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime
import sv_ttk
import queue

# Import từ các file khác
from config import DEFAULT_PROFILES
from ui.profile_tab import ProfileManagerTab  
from ui.dashboard_tab import DashboardTab      
from ui.settings_tab import SettingsTab       
from engine.batch_processor import BatchProcessor 

class BatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Batch Auto Tool Pro - Realtime Dashboard")
        self.root.geometry("1100x900")
        
        try: sv_ttk.set_theme("dark")
        except: pass

        # Biến trạng thái UI
        self.is_running = False
        self.stop_event = threading.Event()
        
        # Khởi tạo Logic Processor
        self.processor = BatchProcessor(
            stop_event=self.stop_event,
            log_callback=self.log,
            update_status_callback=self.update_project_status_callback
        )

        self._setup_ui()

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # TAB 1: Dashboard & Queue
        self.tab_dashboard = DashboardTab(self.notebook, self) 
        self.notebook.add(self.tab_dashboard, text="📂 Danh sách Dự án")
        
        # TAB 2: Profiles
        self.tab_profiles = ProfileManagerTab(self.notebook, DEFAULT_PROFILES)
        self.notebook.add(self.tab_profiles, text="👥 Quản lý Profiles")

        # TAB 3: Settings
        self.tab_settings = SettingsTab(self.notebook)
        self.notebook.add(self.tab_settings, text="⚙️ Cài đặt")

        # LOGS
        frame_log = ttk.LabelFrame(self.root, text="📜 Nhật ký hoạt động", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_area = scrolledtext.ScrolledText(frame_log, height=10, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        self._config_log_tags()

    # --- CÁC HÀM GỌI TỪ UI ---
    def on_start_batch(self):
        # 1. Lấy dữ liệu Queue
        queue_data = self.tab_dashboard.project_queue
        if not queue_data:
            messagebox.showwarning("Trống", "Thêm dự án vào list trước!")
            return
        
        try:
            limit = int(self.tab_dashboard.spin_limit.get())
            threads = int(self.tab_dashboard.spin_threads.get())
            mode = self.tab_dashboard.selected_mode.get()
        except:
            limit, threads = 5, 3
            mode = "Image ➡ Prompt"

        if mode == "Image ➡ Prompt":
            loop_type = "image_prompt"   # Logic Image -> Text
        elif mode == "Prompt ➡ Video":
            loop_type = "prompt_video"  # Logic Video Gen
        elif mode == "Prompt ➡ Image":
            loop_type = "prompt_image"  # Logic Image Gen
        elif mode == "2_Image ➡ Prompt":
            loop_type = "2_image_prompt"   # Logic 2Image -> Text  
        else:
            loop_type = "srt_prompt"    # Logic SRT

        # 3. Lấy Profiles
        profiles = self.tab_profiles.get_selected_profiles()
        if not profiles:
            self.log("❌ Chưa chọn Profile!", "ERROR")
            return

        # 4. Setup trạng thái chạy
        self.is_running = True
        self.stop_event.clear()
        self.tab_dashboard.toggle_buttons(is_running=True)

        # 5. Chạy luồng xử lý chính
        threading.Thread(
            target=self.processor.run_batch_logic,
            args=(queue_data, loop_type, limit, threads, profiles, self.on_batch_finished),
            daemon=True
        ).start()

        # 6. Chạy luồng Monitor (Cập nhật số liệu Realtime)
        threading.Thread(
            target=self.processor.monitor_loop,
            args=(self.tab_dashboard.update_dashboard_stats,),
            daemon=True
        ).start()

    def stop_process(self):
        if self.is_running:
            self.log("🛑 Đang dừng...", "WARNING")
            self.stop_event.set()
            self.processor.clear_task_queue()

    def on_batch_finished(self):
        self.is_running = False
        self.stop_event.clear()
        self.root.after(0, lambda: self.tab_dashboard.toggle_buttons(is_running=False))
        
        if not self.stop_event.is_set():
             self.log("🎉 ĐÃ XONG TẤT CẢ!", "SUCCESS")
             messagebox.showinfo("Xong", "Hoàn thành toàn bộ danh sách!")

    def update_project_status_callback(self, index, status):
        self.root.after(0, lambda: self.tab_dashboard.update_project_status(index, status))

    def _config_log_tags(self):
        self.log_area.tag_config("INFO", foreground="#cccccc")
        self.log_area.tag_config("SUCCESS", foreground="#6cc644")
        self.log_area.tag_config("ERROR", foreground="#ff5555")
        self.log_area.tag_config("WARNING", foreground="#ffb86c")

    def log(self, message, tag="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{ts}] {message}\n"
        def _u():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, full_msg, tag)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _u)