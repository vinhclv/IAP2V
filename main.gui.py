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

# --- CẤU HÌNH MẶC ĐỊNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.join(BASE_DIR, "profiles")
DEFAULT_INPUT = os.path.join(BASE_DIR, "regen")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "assets")

class BatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Batch Auto Tool Pro - Realtime Dashboard")
        self.root.geometry("1100x900")
        
        try: sv_ttk.set_theme("dark")
        except: pass

        self.is_running = False
        self.stop_event = threading.Event()
        
        self.profile_health = {} 
        self.MAX_RETRIES = 30    
        
        self.task_queue = queue.Queue()
        self.file_lock = threading.Lock() 

        self.selected_mode = tk.StringVar(value="Image ➡ Prompt")
        self.project_queue = [] 

        # --- BIẾN ĐỂ MONITOR THEO DÕI ---
        # Luồng monitor sẽ nhìn vào biến này để biết đang chạy folder nào
        self.current_monitoring_info = None # Dạng: (inp, out, loop_type)

        self._setup_ui()

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_queue = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_queue, text="📂 Danh sách Dự án")
        
        self.tab_profiles = ProfileManagerTab(self.notebook, DEFAULT_PROFILES)
        self.notebook.add(self.tab_profiles, text="👥 Quản lý Profiles")

        self._setup_queue_ui()

        # LOGS
        frame_log = ttk.LabelFrame(self.root, text="📜 Nhật ký hoạt động", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_area = scrolledtext.ScrolledText(frame_log, height=10, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        self._config_log_tags()

    def _setup_queue_ui(self):
        # 1. Thêm dự án
        frame_add = ttk.LabelFrame(self.tab_queue, text="➕ Thêm Dự án", padding=10)
        frame_add.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_add, text="Input:").grid(row=0, column=0, sticky="w")
        self.entry_in = ttk.Entry(frame_add)
        self.entry_in.insert(0, DEFAULT_INPUT)
        self.entry_in.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(frame_add, text="📂", width=3, command=lambda: self._pick(self.entry_in)).grid(row=0, column=2)

        ttk.Label(frame_add, text="Output:").grid(row=1, column=0, sticky="w")
        self.entry_out = ttk.Entry(frame_add)
        self.entry_out.insert(0, DEFAULT_OUTPUT)
        self.entry_out.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(frame_add, text="📂", width=3, command=lambda: self._pick(self.entry_out)).grid(row=1, column=2)

        frame_add.columnconfigure(1, weight=1)
        ttk.Button(frame_add, text="⬇ THÊM", command=self.add_project_to_queue).grid(row=0, column=3, rowspan=2, padx=10, sticky="ns")

        # 2. DASHBOARD REALTIME
        frame_dash = ttk.LabelFrame(self.tab_queue, text="📊 Tiến độ Real-time", padding=15)
        frame_dash.pack(fill="x", padx=10, pady=5)
        
        frame_dash.columnconfigure(0, weight=1)
        frame_dash.columnconfigure(1, weight=1)
        frame_dash.columnconfigure(2, weight=1)

        # Tổng
        f1 = ttk.Frame(frame_dash); f1.grid(row=0, column=0)
        self.lbl_total = ttk.Label(f1, text="0", font=("Segoe UI", 24, "bold"), foreground="#888888")
        self.lbl_total.pack(); ttk.Label(f1, text="TỔNG FILE").pack()

        # Pending
        f2 = ttk.Frame(frame_dash); f2.grid(row=0, column=1)
        self.lbl_pending = ttk.Label(f2, text="0", font=("Segoe UI", 32, "bold"), foreground="#ffaa00")
        self.lbl_pending.pack(); ttk.Label(f2, text="CẦN LÀM").pack()

        # Done
        f3 = ttk.Frame(frame_dash); f3.grid(row=0, column=2)
        self.lbl_done = ttk.Label(f3, text="0", font=("Segoe UI", 24, "bold"), foreground="#00cc6a")
        self.lbl_done.pack(); ttk.Label(f3, text="ĐÃ XONG").pack()

        # 3. Danh sách
        frame_list = ttk.LabelFrame(self.tab_queue, text="📋 Hàng chờ", padding=10)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("stt", "input", "output", "status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=6)
        self.tree.heading("stt", text="#")
        self.tree.heading("input", text="Input")
        self.tree.heading("output", text="Output")
        self.tree.heading("status", text="Trạng thái")
        self.tree.column("stt", width=30, anchor="center")
        self.tree.column("input", width=350)
        self.tree.column("output", width=350)
        self.tree.column("status", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(frame_list, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set)

        frame_act = ttk.Frame(frame_list); frame_act.pack(side="bottom", fill="x", pady=5)
        ttk.Button(frame_act, text="❌ Xóa", command=self.remove_selected_project).pack(side="right")
        ttk.Button(frame_act, text="🧹 Xóa hết", command=self.clear_all_projects).pack(side="right", padx=5)

        # 4. Controls
        frame_ctrl = ttk.Frame(self.tab_queue, padding=10); frame_ctrl.pack(fill="x")
        ttk.Label(frame_ctrl, text="Batch:").pack(side="left")
        self.spin_limit = ttk.Spinbox(frame_ctrl, from_=1, to=50, width=5); self.spin_limit.set(5)
        self.spin_limit.pack(side="left", padx=5)

        ttk.Label(frame_ctrl, text="Threads:").pack(side="left")
        self.spin_threads = ttk.Spinbox(frame_ctrl, from_=1, to=20, width=5); self.spin_threads.set(3)
        self.spin_threads.pack(side="left", padx=5)

        ttk.Separator(frame_ctrl, orient="vertical").pack(side="left", fill="y", padx=15)
        self.cbo_mode = ttk.Combobox(frame_ctrl, textvariable=self.selected_mode, state="readonly", width=18)
        self.cbo_mode['values'] = ("Image ➡ Prompt", "Prompt ➡ Video")
        self.cbo_mode.pack(side="left", padx=5)

        self.btn_run = ttk.Button(frame_ctrl, text="▶ CHẠY LIST", style="Accent.TButton", command=self.on_start_batch)
        self.btn_run.pack(side="left", padx=20)
        self.btn_stop = ttk.Button(frame_ctrl, text="🛑 DỪNG", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="right")

    # --- UI HELPERS ---
    def update_dashboard_stats(self, total, pending, done):
        def _update():
            self.lbl_total.config(text=f"{total}")
            self.lbl_pending.config(text=f"{pending}")
            self.lbl_done.config(text=f"{done}")
        self.root.after(0, _update)

    def _pick(self, entry):
        d = filedialog.askdirectory()
        if d: entry.delete(0, tk.END); entry.insert(0, d)

    def add_project_to_queue(self):
        inp = self.entry_in.get(); out = self.entry_out.get()
        if not inp or not out: return
        self.project_queue.append({"input": inp, "output": out, "status": "Waiting"})
        self.refresh_treeview()

    def remove_selected_project(self):
        sel = self.tree.selection()
        if sel:
            del self.project_queue[self.tree.index(sel[0])]
            self.refresh_treeview()

    def clear_all_projects(self):
        self.project_queue = []; self.refresh_treeview()

    def refresh_treeview(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, p in enumerate(self.project_queue):
            self.tree.insert("", "end", values=(i+1, p["input"], p["output"], p["status"]))

    def update_project_status(self, index, status):
        self.project_queue[index]["status"] = status
        self.root.after(0, self.refresh_treeview)

    # --- NEW: LUỒNG GIÁM SÁT REALTIME ---
    def _start_monitor_thread(self):
        """Khởi động luồng giám sát riêng biệt"""
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        """Vòng lặp chạy ngầm, cập nhật UI mỗi 2 giây"""
        while self.is_running:
            # Chỉ cập nhật nếu đang có dự án chạy (biến current_monitoring_info có dữ liệu)
            if self.current_monitoring_info:
                try:
                    inp, out, loop_type = self.current_monitoring_info
                    
                    # Quét nhanh ổ đĩa
                    if loop_type == "text": 
                        pending, done = get_image_status(inp, out)
                    else: 
                        pending, done = get_video_status(out)

                    # Cập nhật UI
                    t = len(pending) + len(done)
                    self.update_dashboard_stats(t, len(pending), len(done))
                    
                except Exception as e:
                    print(f"Monitor Error: {e}")
            
            time.sleep(2)

    # --- WORKER LOGIC ---
    def continuous_profile_runner(self, profile_name, loop_type, inp_path, out_path, limit):
        while not self.stop_event.is_set():
            fails = self.profile_health.get(profile_name, 0)
            if fails >= self.MAX_RETRIES:
                self.log(f"💀 Profile '{profile_name}' chết.", "ERROR"); return 

            candidates = []
            batch = []
            
            with self.file_lock: 
                for _ in range(limit):
                    if not self.task_queue.empty(): candidates.append(self.task_queue.get())
                    else: break
                
                if not candidates: return 

                if loop_type == "text": actual_pending, _ = get_image_status(inp_path, out_path)
                else: actual_pending, _ = get_video_status(out_path)

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

    def process_one_folder(self, inp, out, loop_type, limit, threads, profiles):
        # 1. THÔNG BÁO CHO MONITOR BIẾT ĐỂ BẮT ĐẦU THEO DÕI FOLDER NÀY
        self.current_monitoring_info = (inp, out, loop_type)
        
        with self.task_queue.mutex: self.task_queue.queue.clear()
        self.log(f"🔍 Bắt đầu xử lý: {os.path.basename(inp)}", "INFO")

        while not self.stop_event.is_set():
            # Quét để lấy việc
            if loop_type == "text": pending, _ = get_image_status(inp, out)
            else: pending, _ = get_video_status(out)

            if not pending:
                self.log(f"✅ Dự án {os.path.basename(inp)} hoàn thành!", "SUCCESS")
                break 

            living_profiles = [p for p in profiles if self.profile_health.get(p, 0) < self.MAX_RETRIES]
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
                
                # CHỖ NÀY LÀ CHỖ GÂY ĐỨNG UI CŨ (Blocking Wait)
                # Nhưng giờ đã có luồng Monitor chạy riêng nên UI vẫn nhảy số ầm ầm
                concurrent.futures.wait(futures)

            if self.stop_event.is_set(): break
            time.sleep(3)
        
        # Kết thúc folder này -> Dừng monitor folder này
        self.current_monitoring_info = None

    def run_batch_logic(self, loop_type):
        try: limit = int(self.spin_limit.get())
        except: limit = 5
        try: threads = int(self.spin_threads.get())
        except: threads = 3
        
        profiles = self.tab_profiles.get_selected_profiles()
        if not profiles:
            self.log("❌ Chưa chọn Profile!", "ERROR"); self._reset_ui(); return

        self.profile_health = {p: 0 for p in profiles}

        # --- BẮT ĐẦU LUỒNG MONITOR ---
        self._start_monitor_thread()

        self.log(f"🚀 BẮT ĐẦU CHẠY: {len(self.project_queue)} DỰ ÁN", "INFO")

        for idx, project in enumerate(self.project_queue):
            if self.stop_event.is_set(): break
            
            input_path = project["input"]
            output_path = project["output"]
            
            self.update_project_status(idx, "Running ⏳")
            self.log(f"=== DỰ ÁN {idx+1}/{len(self.project_queue)}: {os.path.basename(input_path)} ===", "INFO")
            
            self.process_one_folder(input_path, output_path, loop_type, limit, threads, profiles)
            
            if self.stop_event.is_set():
                self.update_project_status(idx, "Stopped 🛑")
            else:
                self.update_project_status(idx, "Done ✅")
                self.log(f"🏁 Xong dự án {idx+1}. Nghỉ 5s...", "SUCCESS")
                time.sleep(5)

        if not self.stop_event.is_set():
            self.log("🎉 ĐÃ XONG TẤT CẢ!", "SUCCESS")
            messagebox.showinfo("Xong", "Hoàn thành toàn bộ danh sách!")
        
        self._reset_ui()

    def on_start_batch(self):
        if not self.project_queue:
            messagebox.showwarning("Trống", "Thêm dự án vào list trước!")
            return
        if self.is_running: return
        
        mode = self.selected_mode.get()
        loop_type = "text" if mode == "Image ➡ Prompt" else "video"
        
        self.is_running = True
        self.stop_event.clear()
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        
        threading.Thread(target=self.run_batch_logic, args=(loop_type,), daemon=True).start()

    def stop_process(self):
        if self.is_running:
            self.log("🛑 Đang dừng...", "WARNING")
            self.stop_event.set()
            with self.task_queue.mutex: self.task_queue.queue.clear()

    def _reset_ui(self):
        self.is_running = False
        self.stop_event.clear()
        self.root.after(0, lambda: [self.btn_run.config(state="normal"), self.btn_stop.config(state="disabled")])

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

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchApp(root)
    root.mainloop()