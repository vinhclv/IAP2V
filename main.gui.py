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
        self.root.title("🚀 Batch Auto Tool Pro - Ultimate (Team & Reserve Mode)")
        self.root.geometry("1100x800")
        
        try: sv_ttk.set_theme("dark")
        except: pass

        self.is_running = False
        self.stop_event = threading.Event()
        
        self.profile_health = {} 
        self.MAX_RETRIES = 3     
        
        self.task_queue = queue.Queue()
        self.file_lock = threading.Lock() 

        self._setup_ui()
        self.root.after(1000, self.refresh_dashboard)

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.tab_run = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_run, text="🏃 Chạy Auto")
        self.tab_profiles = ProfileManagerTab(self.notebook, DEFAULT_PROFILES)
        self.notebook.add(self.tab_profiles, text="👥 Quản lý Profiles")

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
        
        ttk.Button(frame_path, text="🔄 Cập nhật Số liệu", command=self.refresh_dashboard).grid(row=0, column=3, rowspan=2, padx=10, sticky="ns")
        frame_path.columnconfigure(1, weight=1)

        frame_stats = ttk.LabelFrame(self.tab_run, text="📊 Thống kê Trạng thái", padding=15)
        frame_stats.pack(fill="x", padx=10, pady=5)
        for i in range(3): frame_stats.columnconfigure(i, weight=1)
        self._create_stat_col(frame_stats, 0, "Profiles (Đã chọn)", "#4cc2ff", "lbl_profile")
        self._create_stat_col(frame_stats, 1, "Tạo Prompt", "#ffaa00", "lbl_txt", True)
        self._create_stat_col(frame_stats, 2, "Tạo Video", "#ff5555", "lbl_vid", True)

        # --- CONTROLS ---
        frame_ctrl = ttk.Frame(self.tab_run, padding=10)
        frame_ctrl.pack(fill="x")
        
        # Cấu hình 1: Limit batch
        lbl_l1 = ttk.Label(frame_ctrl, text="Xử lý / 1 lần:")
        lbl_l1.pack(side="left")
        self.spin_limit = ttk.Spinbox(frame_ctrl, from_=1, to=50, width=5)
        self.spin_limit.set(5)
        self.spin_limit.pack(side="left", padx=5)

        # Cấu hình 2: Max Threads
        lbl_l2 = ttk.Label(frame_ctrl, text="Số luồng chạy cùng lúc:")
        lbl_l2.pack(side="left", padx=(15, 0))
        self.spin_threads = ttk.Spinbox(frame_ctrl, from_=1, to=20, width=5)
        self.spin_threads.set(3) 
        self.spin_threads.pack(side="left", padx=5)

        self.btn_text = ttk.Button(frame_ctrl, text="🚀 CHẠY: Image ➡ Prompt", style="Accent.TButton", command=lambda: self.start_thread("text"))
        self.btn_text.pack(side="left", padx=20)
        
        self.btn_video = ttk.Button(frame_ctrl, text="🎥 CHẠY: Prompt ➡ Video", style="Accent.TButton", command=lambda: self.start_thread("video"))
        self.btn_video.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(frame_ctrl, text="🛑 DỪNG KHẨN CẤP", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="right")

        frame_log = ttk.LabelFrame(self.tab_run, text="📜 Nhật ký hoạt động", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_area = scrolledtext.ScrolledText(frame_log, height=10, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        self._config_log_tags()

        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_dashboard() if self.notebook.index("current") == 0 else None)

    # --- UI HELPERS ---
    def _create_stat_col(self, parent, col, title, color, attr_prefix, detailed=False):
        f = ttk.Frame(parent)
        f.grid(row=0, column=col, padx=10)
        ttk.Label(f, text=title, font=("Segoe UI", 11)).pack()
        if not detailed:
            lbl = ttk.Label(f, text="0", font=("Segoe UI", 28, "bold"), foreground=color)
            lbl.pack(); setattr(self, attr_prefix, lbl)
        else:
            sub = ttk.Frame(f); sub.pack(pady=5)
            lbl_pend = ttk.Label(sub, text="0", font=("Segoe UI", 28, "bold"), foreground=color)
            lbl_pend.grid(row=0, column=1, padx=20); ttk.Label(sub, text="Cần làm").grid(row=1, column=1)
            lbl_tot = ttk.Label(sub, text="0", font=("Segoe UI", 14), foreground="#888")
            lbl_tot.grid(row=0, column=0, padx=10); ttk.Label(sub, text="Tổng").grid(row=1, column=0)
            lbl_done = ttk.Label(sub, text="0", font=("Segoe UI", 14), foreground="#00cc6a")
            lbl_done.grid(row=0, column=2, padx=10); ttk.Label(sub, text="Xong").grid(row=1, column=2)
            setattr(self, f"{attr_prefix}_pending", lbl_pend); setattr(self, f"{attr_prefix}_total", lbl_tot); setattr(self, f"{attr_prefix}_done", lbl_done)

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

    def refresh_dashboard(self): threading.Thread(target=self._calculate_stats, daemon=True).start()
    
    def _calculate_stats(self):
        try:
            inp = self.entry_input.get(); out = self.entry_output.get()
            selected_count = len(self.tab_profiles.get_selected_profiles())
            pend_txt, comp_txt = get_image_status(inp, out)
            pend_vid, comp_vid = get_video_status(out)
            self.root.after(0, lambda: self._update_labels(selected_count, len(pend_txt), len(comp_txt), len(pend_vid), len(comp_vid)))
        except: pass

    def _update_labels(self, n_prof, n_pend_txt, n_comp_txt, n_pend_vid, n_comp_vid):
        self.lbl_profile.config(text=f"{n_prof}")
        self.lbl_txt_total.config(text=f"{n_pend_txt + n_comp_txt}"); self.lbl_txt_pending.config(text=f"{n_pend_txt}"); self.lbl_txt_done.config(text=f"{n_comp_txt}")
        self.lbl_vid_total.config(text=f"{n_pend_vid + n_comp_vid}"); self.lbl_vid_pending.config(text=f"{n_pend_vid}"); self.lbl_vid_done.config(text=f"{n_comp_vid}")

    # ================= LOGIC CHẠY LIÊN TỤC =================
    def continuous_profile_runner(self, profile_name, loop_type, out, limit):
        while not self.stop_event.is_set():
            fails = self.profile_health.get(profile_name, 0)
            if fails >= self.MAX_RETRIES:
                self.log(f"💀 Profile '{profile_name}' ĐÃ CHẾT (Dừng vĩnh viễn).", "ERROR")
                return 

            batch = []
            with self.file_lock: 
                for _ in range(limit):
                    if not self.task_queue.empty():
                        batch.append(self.task_queue.get())
                    else: break
            
            if not batch:
                self.log(f"✅ Profile '{profile_name}' đã hết việc (Nghỉ).", "SUCCESS")
                return 

            self.log(f"▶️ [{profile_name}] Nhận {len(batch)} file...", "INFO")
            is_healthy, failed_items = run_worker_task(profile_name, batch, loop_type, out, DEFAULT_PROFILES, self.stop_event, self.log)

            if failed_items:
                self.log(f"♻️ [{profile_name}] Trả lại {len(failed_items)} file lỗi vào hàng đợi.", "WARNING")
                with self.file_lock:
                    for item in failed_items:
                        self.task_queue.put(item) 

            if is_healthy:
                self.profile_health[profile_name] = 0 
            else:
                self.profile_health[profile_name] += 1
                self.log(f"⚠️ [{profile_name}] Bị lỗi ({self.profile_health[profile_name]}/{self.MAX_RETRIES})", "WARNING")

            self.refresh_dashboard()

    def run_process(self, loop_type):
        inp = self.entry_input.get()
        out = self.entry_output.get()
        
        # --- [FIX LỖI NHẬP LIỆU] ---
        try:
            limit = int(self.spin_limit.get())
        except ValueError:
            limit = 5
            self.spin_limit.set(5)

        try:
            setting_threads = int(self.spin_threads.get())
        except ValueError:
            setting_threads = 3
            self.spin_threads.set(3)
        # ----------------------------

        selected_profiles = self.tab_profiles.get_selected_profiles()
        if not selected_profiles:
            self.log("❌ Chưa chọn Profile nào!", "ERROR"); self._reset_ui(); return

        # === [LOGIC THÔNG MINH] ===
        num_selected = len(selected_profiles)
        max_threads = min(setting_threads, num_selected)
        if setting_threads > num_selected:
            self.log(f"⚠️ Bạn chọn {setting_threads} luồng nhưng chỉ có {num_selected} profiles.", "WARNING")
            self.log(f"⬇️ Hệ thống tự điều chỉnh xuống: {max_threads} luồng.", "WARNING")
        
        self.profile_health = {p: 0 for p in selected_profiles}

        self.log("📦 Đang quét file và tạo hàng đợi...", "INFO")
        if loop_type == "text": pending, _ = get_image_status(inp, out)
        else: pending, _ = get_video_status(out)

        if not pending:
            self.log("🎉 Không có file nào cần xử lý!", "SUCCESS"); messagebox.showinfo("Thông báo", "Tất cả đã hoàn thành!"); self._reset_ui(); return

        while not self.task_queue.empty(): self.task_queue.get()
        for f in pending: self.task_queue.put(f)

        total_files = self.task_queue.qsize()
        self.log(f"🚀 Bắt đầu! Tổng {total_files} files. Đội hình: {num_selected} Profiles.", "INFO")
        self.log(f"⚡ Đang chạy song song: {max_threads} Luồng.", "INFO")

        self.root.after(2000, self._auto_refresh_loop)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for p_name in selected_profiles:
                future = executor.submit(self.continuous_profile_runner, p_name, loop_type, out, limit)
                futures.append(future)

            concurrent.futures.wait(futures)

        if self.stop_event.is_set():
            self.log("🛑 Đã dừng theo yêu cầu.", "WARNING")
        else:
            self.log("🎉 ĐÃ HOÀN THÀNH TOÀN BỘ CÔNG VIỆC!", "SUCCESS")
            messagebox.showinfo("Thành công", "Đã xử lý xong toàn bộ hàng đợi!")

        self._reset_ui()

    def _auto_refresh_loop(self):
        if self.is_running:
            self.refresh_dashboard()
            self.root.after(3000, self._auto_refresh_loop)

    def start_thread(self, loop_type):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.btn_text.config(state="disabled"); self.btn_video.config(state="disabled")
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
        self.root.after(0, lambda: [self.btn_text.config(state="normal"), self.btn_video.config(state="normal"), 
                                    self.btn_stop.config(state="disabled"), self.spin_limit.config(state="normal"),
                                    self.spin_threads.config(state="normal")])

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchApp(root)
    root.mainloop()