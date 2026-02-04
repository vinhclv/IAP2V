import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import time
import threading
import concurrent.futures
import queue
from datetime import datetime
import sv_ttk

# --- IMPORT MODULES ---
from profile_manager import ProfileManagerTab
from utils import get_image_status, get_video_status
from worker import run_worker_task
# --- CẤU HÌNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.join(BASE_DIR, "profiles")
DEFAULT_INPUT = os.path.join(BASE_DIR, "regen")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "assets")

class BatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Batch Auto Tool Pro - Ultimate (Unified UI)")
        self.root.geometry("1000x800")
        
        try: sv_ttk.set_theme("dark")
        except: pass

        self.is_running = False
        self.stop_event = threading.Event()
        
        self.profile_health = {} 
        self.MAX_RETRIES = 10     
        
        self.task_queue = queue.Queue()
        self.file_lock = threading.Lock() 

        # Biến lưu chế độ đang chọn
        self.selected_mode = tk.StringVar(value="Image ➡ Prompt")

        self._setup_ui()
        self.root.after(1000, self.refresh_dashboard)

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.tab_run = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_run, text="🏃 Chạy Auto")
        self.tab_profiles = ProfileManagerTab(self.notebook, DEFAULT_PROFILES)
        self.notebook.add(self.tab_profiles, text="👥 Quản lý Profiles")

        # --- PATH CONFIG ---
        frame_top = ttk.Frame(self.tab_run, padding=10)
        frame_top.pack(fill="x")
        frame_path = ttk.LabelFrame(frame_top, text="📂 Cấu hình Thư mục", padding=(15, 10))
        frame_path.pack(fill="x", expand=True)

        ttk.Label(frame_path, text="Input Images:").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_input = ttk.Entry(frame_path)
        self.entry_input.insert(0, DEFAULT_INPUT)
        self.entry_input.grid(row=0, column=1, sticky="ew", padx=5, ipady=3)
        ttk.Button(frame_path, text="📂 Chọn", command=self.select_input_folder, width=8).grid(row=0, column=2, padx=5)

        ttk.Label(frame_path, text="Output Assets:").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_output = ttk.Entry(frame_path)
        self.entry_output.insert(0, DEFAULT_OUTPUT)
        self.entry_output.grid(row=1, column=1, sticky="ew", padx=5, ipady=3)
        ttk.Button(frame_path, text="📂 Chọn", command=self.select_output_folder, width=8).grid(row=1, column=2, padx=5)
        
        ttk.Button(frame_path, text="🔄 Refresh", command=self.refresh_dashboard).grid(row=0, column=3, rowspan=2, padx=10, sticky="ns")
        frame_path.columnconfigure(1, weight=1)

        # --- STATS DASHBOARD (GIAO DIỆN MỚI) ---
        frame_stats = ttk.LabelFrame(self.tab_run, text="📊 Trạng thái Công việc", padding=15)
        frame_stats.pack(fill="x", padx=10, pady=5)
        frame_stats.columnconfigure(0, weight=1) # Cột Profile
        frame_stats.columnconfigure(1, weight=2) # Cột Task

        # Cột 1: Số lượng Profile
        self._create_stat_col(frame_stats, 0, "Profiles (Đã chọn)", "#4cc2ff", "lbl_profile")
        
        # Cột 2: Thống kê File (Thay đổi tiêu đề động)
        # Tạo sẵn các label, tiêu đề sẽ được cập nhật trong code
        self.lbl_task_title = ttk.Label(frame_stats, text="Chờ dữ liệu...", font=("Segoe UI", 11))
        self.lbl_task_title.grid(row=0, column=1, padx=10)
        
        # Tạo khung chứa 3 số liệu (Tổng - Cần làm - Xong)
        sub_stat = ttk.Frame(frame_stats)
        sub_stat.grid(row=1, column=1, pady=5)
        
        # Total
        f1 = ttk.Frame(sub_stat); f1.pack(side="left", padx=20)
        self.lbl_task_total = ttk.Label(f1, text="0", font=("Segoe UI", 16), foreground="#888")
        self.lbl_task_total.pack()
        ttk.Label(f1, text="Tổng File").pack()

        # Pending (To nhất)
        f2 = ttk.Frame(sub_stat); f2.pack(side="left", padx=20)
        self.lbl_task_pending = ttk.Label(f2, text="0", font=("Segoe UI", 32, "bold"), foreground="#ffaa00")
        self.lbl_task_pending.pack()
        ttk.Label(f2, text="Cần làm").pack()

        # Done
        f3 = ttk.Frame(sub_stat); f3.pack(side="left", padx=20)
        self.lbl_task_done = ttk.Label(f3, text="0", font=("Segoe UI", 16), foreground="#00cc6a")
        self.lbl_task_done.pack()
        ttk.Label(f3, text="Đã Xong").pack()


        # --- CONTROLS (GIAO DIỆN MỚI) ---
        frame_ctrl = ttk.Frame(self.tab_run, padding=10)
        frame_ctrl.pack(fill="x")
        
        # Cấu hình Limit & Thread
        f_settings = ttk.Frame(frame_ctrl)
        f_settings.pack(side="left")
        
        ttk.Label(f_settings, text="Batch Size:").pack(side="left")
        self.spin_limit = ttk.Spinbox(f_settings, from_=1, to=50, width=5)
        self.spin_limit.set(5); self.spin_limit.pack(side="left", padx=(5, 15))

        ttk.Label(f_settings, text="Threads:").pack(side="left")
        self.spin_threads = ttk.Spinbox(f_settings, from_=1, to=20, width=5)
        self.spin_threads.set(3); self.spin_threads.pack(side="left", padx=5)

        # SEPARATOR
        ttk.Separator(frame_ctrl, orient="vertical").pack(side="left", fill="y", padx=15)

        # SELECT BOX CHỌN CHẾ ĐỘ
        ttk.Label(frame_ctrl, text="Chế độ chạy:").pack(side="left")
        self.cbo_mode = ttk.Combobox(frame_ctrl, textvariable=self.selected_mode, state="readonly", width=25)
        self.cbo_mode['values'] = ("Image ➡ Prompt", "Prompt ➡ Video")
        self.cbo_mode.pack(side="left", padx=10)
        self.cbo_mode.bind("<<ComboboxSelected>>", self.on_mode_change) # Cập nhật số liệu khi chọn

        # NÚT CHẠY CHUNG
        self.btn_run = ttk.Button(frame_ctrl, text="▶ CHẠY NGAY", style="Accent.TButton", command=self.on_start_click)
        self.btn_run.pack(side="left", padx=10)
        
        self.btn_stop = ttk.Button(frame_ctrl, text="🛑 DỪNG", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="right")

        # LOGS
        frame_log = ttk.LabelFrame(self.tab_run, text="📜 Nhật ký hoạt động", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_area = scrolledtext.ScrolledText(frame_log, height=10, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        self._config_log_tags()

        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_dashboard() if self.notebook.index("current") == 0 else None)


    # --- UI HELPERS ---
    def _create_stat_col(self, parent, col, title, color, attr_prefix):
        f = ttk.Frame(parent)
        f.grid(row=0, column=col, padx=10)
        ttk.Label(f, text=title, font=("Segoe UI", 11)).pack()
        lbl = ttk.Label(f, text="0", font=("Segoe UI", 28, "bold"), foreground=color)
        lbl.pack(); setattr(self, attr_prefix, lbl)

    def _config_log_tags(self):
        self.log_area.tag_config("INFO", foreground="#cccccc"); self.log_area.tag_config("SUCCESS", foreground="#6cc644")
        self.log_area.tag_config("ERROR", foreground="#ff5555"); self.log_area.tag_config("WARNING", foreground="#ffb86c")

    def select_input_folder(self):
        f = filedialog.askdirectory()
        if f: self.entry_input.delete(0, tk.END); self.entry_input.insert(0, f); self.refresh_dashboard()
    def select_output_folder(self):
        f = filedialog.askdirectory()
        if f: self.entry_output.delete(0, tk.END); self.entry_output.insert(0, f); self.refresh_dashboard()

    def log(self, message, tag="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{ts}] {message}\n"
        def _u():
            self.log_area.config(state='normal'); self.log_area.insert(tk.END, full_msg, tag)
            self.log_area.see(tk.END); self.log_area.config(state='disabled')
        self.root.after(0, _u)

    # --- DASHBOARD LOGIC (CẬP NHẬT MỚI) ---
    def on_mode_change(self, event=None):
        """Khi thay đổi SelectBox -> Cập nhật lại số liệu hiển thị"""
        self.refresh_dashboard()

    def refresh_dashboard(self): threading.Thread(target=self._calculate_stats, daemon=True).start()
    
    def _calculate_stats(self):
        try:
            inp = self.entry_input.get(); out = self.entry_output.get()
            selected_count = len(self.tab_profiles.get_selected_profiles())
            
            # Lấy chế độ đang chọn từ UI
            mode_str = self.selected_mode.get()
            
            # Tính toán dựa trên chế độ
            if mode_str == "Image ➡ Prompt":
                pend, comp = get_image_status(inp, out)
                title = "Tiến độ: Tạo Prompt từ Ảnh"
                color = "#ffaa00" # Cam
            else: # Prompt -> Video
                pend, comp = get_video_status(out)
                title = "Tiến độ: Tạo Video từ Prompt"
                color = "#ff5555" # Đỏ

            self.root.after(0, lambda: self._update_ui_stats(selected_count, len(pend), len(comp), title, color))
        except: pass

    def _update_ui_stats(self, n_prof, n_pend, n_comp, title_text, main_color):
        # Cập nhật số Profile
        self.lbl_profile.config(text=f"{n_prof}")
        
        # Cập nhật Tiêu đề và Màu sắc
        self.lbl_task_title.config(text=title_text)
        self.lbl_task_pending.config(foreground=main_color)

        # Cập nhật số liệu Task
        self.lbl_task_total.config(text=f"{n_pend + n_comp}")
        self.lbl_task_pending.config(text=f"{n_pend}")
        self.lbl_task_done.config(text=f"{n_comp}")

    def continuous_profile_runner(self, profile_name, loop_type, out, limit):
        while not self.stop_event.is_set():
            # 1. Kiểm tra sức khỏe Profile
            fails = self.profile_health.get(profile_name, 0)
            if fails >= self.MAX_RETRIES:
                self.log(f"💀 Profile '{profile_name}' ĐÃ CHẾT (Dừng vĩnh viễn).", "ERROR")
                return 

            candidates = []
            batch = []
            
            # 2. Lấy ứng viên từ Queue và Đối soát triệt để với ổ đĩa
            with self.file_lock: 
                # Lấy ra các ứng viên tạm thời từ hàng đợi
                for _ in range(limit):
                    if not self.task_queue.empty():
                        candidates.append(self.task_queue.get())
                    else:
                        break
                
                if not candidates:
                    self.log(f"✅ Profile '{profile_name}' đã hết việc (Nghỉ).", "SUCCESS")
                    return 

                inp_path = self.entry_input.get()
                if loop_type == "text":
                    actual_pending, _ = get_image_status(inp_path, out)
                else:
                    actual_pending, _ = get_video_status(out)

                batch = [item for item in candidates if item in actual_pending]
                
                finished_already = len(candidates) - len(batch)
                if finished_already > 0:
                    self.log(f"ℹ️ [{profile_name}] Bỏ qua {finished_already} file đã hoàn thành trước đó.", "INFO")

            if not batch:
                continue

            self.log(f"▶️ [{profile_name}] Xử lý {len(batch)} file thực tế từ ổ đĩa...", "INFO")
            is_healthy, failed_items = run_worker_task(
                profile_name, batch, loop_type, out, DEFAULT_PROFILES, self.stop_event, self.log
            )

            if failed_items:
                self.log(f"♻️ [{profile_name}] Trả lại {len(failed_items)} file lỗi vào hàng đợi.", "WARNING")
                with self.file_lock:
                    for item in failed_items:
                        self.task_queue.put(item) 

            # 6. Cập nhật trạng thái sức khỏe Profile
            if is_healthy: 
                self.profile_health[profile_name] = 0 
            else:
                self.profile_health[profile_name] += 1
                self.log(f"⚠️ [{profile_name}] Lỗi ({self.profile_health[profile_name]}/{self.MAX_RETRIES})", "WARNING")

            self.refresh_dashboard()


    def run_process(self, loop_type):
        # --- 1. LẤY DỮ LIỆU ĐẦU VÀO ---
        inp = self.entry_input.get()
        out = self.entry_output.get()
        
        try: limit = int(self.spin_limit.get())
        except: limit = 5; self.spin_limit.set(5)
        
        try: setting_threads = int(self.spin_threads.get())
        except: setting_threads = 3; self.spin_threads.set(3)

        selected_profiles = self.tab_profiles.get_selected_profiles()
        if not selected_profiles:
            self.log("❌ Chưa chọn Profile nào!", "ERROR")
            self._reset_ui()
            return

        num_selected = len(selected_profiles)
        
        # Khởi tạo bảng theo dõi sức khỏe (0 lỗi ban đầu)
        self.profile_health = {p: 0 for p in selected_profiles}

        self.log(f"🚀 BẮT ĐẦU CHIẾN DỊCH: {self.selected_mode.get()}", "INFO")
        self.root.after(2000, self._auto_refresh_loop)

        # --- 2. VÒNG LẶP CHIẾN DỊCH (MASTER LOOP) ---
        # Vòng lặp này sẽ chạy mãi cho đến khi HẾT VIỆC hoặc HẾT PROFILE
        while not self.stop_event.is_set():
            
            # A. QUÉT DỮ LIỆU THỰC TẾ TRÊN Ổ ĐĨA
            self.log("🔍 Đang đối soát dữ liệu trên ổ đĩa...", "INFO")
            if loop_type == "text": 
                pending, _ = get_image_status(inp, out)
            else: 
                pending, _ = get_video_status(out)

            # B. ĐIỀU KIỆN DỪNG 1: HẾT VIỆC
            if not pending:
                self.log("🎉 XÁC NHẬN: Ổ đĩa đã sạch bóng file cần làm. HOÀN THÀNH 100%!", "SUCCESS")
                messagebox.showinfo("Thành công", "Đã xử lý triệt để toàn bộ file!")
                break 

            # C. ĐIỀU KIỆN DỪNG 2: HẾT QUÂN (PROFILE CHẾT SẠCH)
            # Lọc ra những profile còn sống (số lỗi < MAX_RETRIES)
            living_profiles = [p for p in selected_profiles if self.profile_health.get(p, 0) < self.MAX_RETRIES]
            
            if not living_profiles:
                self.log("❌ TẤT CẢ PROFILE ĐÃ CHẾT! Dừng chiến dịch.", "ERROR")
                messagebox.showerror("Lỗi nghiêm trọng", "Tất cả profile đã bị lỗi quá giới hạn. Tool dừng lại để bảo vệ tài khoản.")
                break

            # D. NẠP ĐẠN (CẬP NHẬT QUEUE)
            # Xóa sạch queue cũ để nạp danh sách mới nhất từ ổ đĩa
            while not self.task_queue.empty(): 
                self.task_queue.get()
            
            for f in pending: 
                self.task_queue.put(f)

            # E. TÍNH TOÁN LUỒNG CHO ĐỢT NÀY
            # Số luồng không được vượt quá số profile đang sống
            current_max_threads = min(setting_threads, len(living_profiles))
            
            self.log(f"⚡ Đợt mới: {len(pending)} files | Quân số: {len(living_profiles)}/{num_selected} | Luồng: {current_max_threads}", "INFO")

            # F. CHẠY EXECUTOR (GIAO VIỆC)
            with concurrent.futures.ThreadPoolExecutor(max_workers=current_max_threads) as executor:
                futures = []
                for p_name in living_profiles:
                    # Gửi các "Tổ trưởng" đi làm việc
                    future = executor.submit(self.continuous_profile_runner, p_name, loop_type, out, limit)
                    futures.append(future)
                
                # Chờ cho đến khi tất cả profile trong đợt này báo nghỉ (hết queue hoặc chết)
                concurrent.futures.wait(futures)

            # G. NGHỈ NGƠI TRƯỚC KHI QUÉT LẠI
            if self.stop_event.is_set(): 
                break
            
            self.log("⏳ Đã xong một đợt. Nghỉ 5s chờ hệ thống file cập nhật...", "INFO")
            time.sleep(5) 

        # --- 3. KẾT THÚC ---
        if self.stop_event.is_set(): 
            self.log("🛑 Đã dừng theo yêu cầu.", "WARNING")
        
        self._reset_ui()


    def _auto_refresh_loop(self):
        if self.is_running:
            self.refresh_dashboard()
            self.root.after(3000, self._auto_refresh_loop)

    def on_start_click(self):
        """Xử lý khi bấm nút CHẠY"""
        if self.is_running: return
        
        # Xác định loop_type dựa trên SelectBox
        mode = self.selected_mode.get()
        loop_type = "text" if mode == "Image ➡ Prompt" else "video"
        
        self.is_running = True
        self.stop_event.clear()
        self.btn_run.config(state="disabled"); self.cbo_mode.config(state="disabled")
        self.btn_stop.config(state="normal"); self.spin_limit.config(state="disabled")
        self.spin_threads.config(state="disabled")
        
        threading.Thread(target=self.run_process, args=(loop_type,), daemon=True).start()

    def stop_process(self):
        if self.is_running:
            self.log("🛑 Đang gửi lệnh dừng...", "WARNING")
            self.stop_event.set()
            with self.task_queue.mutex: self.task_queue.queue.clear()

    def _reset_ui(self):
        self.is_running = False; self.stop_event.clear()
        self.root.after(0, lambda: [self.btn_run.config(state="normal"), self.cbo_mode.config(state="readonly"), 
                                    self.btn_stop.config(state="disabled"), self.spin_limit.config(state="normal"),
                                    self.spin_threads.config(state="normal")])

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchApp(root)
    root.mainloop()