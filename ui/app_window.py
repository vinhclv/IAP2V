# ui/app_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime
import sv_ttk
import queue

# Import từ các file khác
from config import DEFAULT_PROFILES
from ui.profile_tab import ProfileManagerTab  # File cũ của bạn
from ui.dashboard_tab import DashboardTab      # File mới tách ra
from engine.batch_processor import BatchProcessor # Logic xử lý

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
        # Truyền callback log và update UI vào Processor
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
        self.tab_dashboard = DashboardTab(self.notebook, self) # Truyền self để gọi ngược lại
        self.notebook.add(self.tab_dashboard, text="📂 Danh sách Dự án")
        
        # TAB 2: Profiles
        self.tab_profiles = ProfileManagerTab(self.notebook, DEFAULT_PROFILES)
        self.notebook.add(self.tab_profiles, text="👥 Quản lý Profiles")

        # LOGS
        frame_log = ttk.LabelFrame(self.root, text="📜 Nhật ký hoạt động", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_area = scrolledtext.ScrolledText(frame_log, height=10, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        self._config_log_tags()

    # --- CÁC HÀM GỌI TỪ UI ---
    def on_start_batch(self):
        # Lấy dữ liệu từ UI
        queue_data = self.tab_dashboard.project_queue
        if not queue_data:
            messagebox.showwarning("Trống", "Thêm dự án vào list trước!")
            return
        
        # Lấy settings
        try:
            limit = int(self.tab_dashboard.spin_limit.get())
            threads = int(self.tab_dashboard.spin_threads.get())
            mode = self.tab_dashboard.selected_mode.get()
        except:
            limit, threads = 5, 3
            mode = "Image ➡ Prompt"

        loop_type = "text" if mode == "Image ➡ Prompt" else "video"

        # Lấy profiles
        profiles = self.tab_profiles.get_selected_profiles()
        if not profiles:
            self.log("❌ Chưa chọn Profile!", "ERROR")
            return

        # Setup trạng thái
        self.is_running = True
        self.stop_event.clear()
        self.tab_dashboard.toggle_buttons(is_running=True)

        # Chạy logic ở luồng riêng (Gọi sang engine)
        threading.Thread(
            target=self.processor.run_batch_logic,
            args=(queue_data, loop_type, limit, threads, profiles, self.on_batch_finished),
            daemon=True
        ).start()

        # Bắt đầu luồng monitor UI (Gọi sang engine)
        # Truyền callback để update 3 số liệu trên dashboard
        threading.Thread(
            target=self.processor.monitor_loop,
            args=(self.tab_dashboard.update_dashboard_stats,),
            daemon=True
        ).start()

    def stop_process(self):
        if self.is_running:
            self.log("🛑 Đang dừng...", "WARNING")
            self.stop_event.set()
            self.processor.clear_task_queue() # Clear queue bên trong processor

    def on_batch_finished(self):
        """Callback khi toàn bộ batch chạy xong"""
        self.is_running = False
        self.stop_event.clear()
        self.root.after(0, lambda: self.tab_dashboard.toggle_buttons(is_running=False))
        
        if not self.stop_event.is_set():
             self.log("🎉 ĐÃ XONG TẤT CẢ!", "SUCCESS")
             messagebox.showinfo("Xong", "Hoàn thành toàn bộ danh sách!")

    def update_project_status_callback(self, index, status):
        """Callback cập nhật trạng thái từng dòng dự án"""
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