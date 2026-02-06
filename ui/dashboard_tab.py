# ui/dashboard_tab.py
import tkinter as tk
from tkinter import ttk, filedialog
from config import DEFAULT_INPUT, DEFAULT_OUTPUT, load_config

class DashboardTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller 
        self.project_queue = []
        
        self._setup_ui()
        self._load_defaults() # Load config mặc định khi mở

    def _setup_ui(self):
        # 1. Thêm dự án
        frame_add = ttk.LabelFrame(self, text="➕ Thêm Dự án", padding=10)
        frame_add.pack(fill="x", padx=10, pady=5)

        # --- INPUT (SỬA LOGIC CHỌN FILE/FOLDER) ---
        ttk.Label(frame_add, text="Input:").grid(row=0, column=0, sticky="w")
        self.entry_in = ttk.Entry(frame_add)
        self.entry_in.insert(0, DEFAULT_INPUT)
        self.entry_in.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Nút chọn Input (Gọi hàm riêng _pick_input để check mode)
        self.btn_in = ttk.Button(frame_add, text="📂", width=3, command=self._pick_input)
        self.btn_in.grid(row=0, column=2)

        # --- OUTPUT ---
        ttk.Label(frame_add, text="Output:").grid(row=1, column=0, sticky="w")
        self.entry_out = ttk.Entry(frame_add)
        self.entry_out.insert(0, DEFAULT_OUTPUT)
        self.entry_out.grid(row=1, column=1, sticky="ew", padx=5)
        
        # Nút chọn Output (Luôn là Folder)
        ttk.Button(frame_add, text="📂", width=3, command=lambda: self._pick_folder(self.entry_out)).grid(row=1, column=2)

        frame_add.columnconfigure(1, weight=1)
        
        # Nút Thêm
        ttk.Button(frame_add, text="⬇ THÊM", command=self.add_project_to_queue).grid(row=0, column=3, rowspan=2, padx=10, sticky="ns")

        # 2. DASHBOARD REALTIME
        frame_dash = ttk.LabelFrame(self, text="📊 Tiến độ Real-time", padding=15)
        frame_dash.pack(fill="x", padx=10, pady=5)
        
        frame_dash.columnconfigure(0, weight=1)
        frame_dash.columnconfigure(1, weight=1)
        frame_dash.columnconfigure(2, weight=1)

        f1 = ttk.Frame(frame_dash); f1.grid(row=0, column=0)
        self.lbl_total = ttk.Label(f1, text="0", font=("Segoe UI", 24, "bold"), foreground="#888888")
        self.lbl_total.pack(); ttk.Label(f1, text="TỔNG FILE").pack()

        f2 = ttk.Frame(frame_dash); f2.grid(row=0, column=1)
        self.lbl_pending = ttk.Label(f2, text="0", font=("Segoe UI", 32, "bold"), foreground="#ffaa00")
        self.lbl_pending.pack(); ttk.Label(f2, text="CẦN LÀM").pack()

        f3 = ttk.Frame(frame_dash); f3.grid(row=0, column=2)
        self.lbl_done = ttk.Label(f3, text="0", font=("Segoe UI", 24, "bold"), foreground="#00cc6a")
        self.lbl_done.pack(); ttk.Label(f3, text="ĐÃ XONG").pack()

        # 3. Danh sách Treeview
        frame_list = ttk.LabelFrame(self, text="📋 Hàng chờ", padding=10)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("stt", "input", "output", "status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=6)
        self.tree.heading("stt", text="#"); self.tree.column("stt", width=30, anchor="center")
        self.tree.heading("input", text="Input"); self.tree.column("input", width=350)
        self.tree.heading("output", text="Output"); self.tree.column("output", width=350)
        self.tree.heading("status", text="Trạng thái"); self.tree.column("status", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(frame_list, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set)

        frame_act = ttk.Frame(frame_list); frame_act.pack(side="bottom", fill="x", pady=5)
        ttk.Button(frame_act, text="❌ Xóa", command=self.remove_selected_project).pack(side="right")
        ttk.Button(frame_act, text="🧹 Xóa hết", command=self.clear_all_projects).pack(side="right", padx=5)

        # 4. Controls
        frame_ctrl = ttk.Frame(self, padding=10); frame_ctrl.pack(fill="x")
        
        ttk.Label(frame_ctrl, text="Batch:").pack(side="left")
        self.spin_limit = ttk.Spinbox(frame_ctrl, from_=1, to=50, width=5); self.spin_limit.set(5)
        self.spin_limit.pack(side="left", padx=5)

        ttk.Label(frame_ctrl, text="Threads:").pack(side="left")
        self.spin_threads = ttk.Spinbox(frame_ctrl, from_=1, to=20, width=5); self.spin_threads.set(3)
        self.spin_threads.pack(side="left", padx=5)

        ttk.Separator(frame_ctrl, orient="vertical").pack(side="left", fill="y", padx=15)
        
        self.selected_mode = tk.StringVar(value="Image ➡ Prompt")
        self.cbo_mode = ttk.Combobox(frame_ctrl, textvariable=self.selected_mode, state="readonly", width=20)
        
        self.cbo_mode['values'] = ("Image ➡ Prompt", "Prompt ➡ Video", "SRT ➡ Prompt")
        self.cbo_mode.pack(side="left", padx=5)
        
        self.cbo_mode.bind("<<ComboboxSelected>>", self._on_mode_change)

        self.btn_run = ttk.Button(frame_ctrl, text="▶ CHẠY LIST", style="Accent.TButton", command=self.controller.on_start_batch)
        self.btn_run.pack(side="left", padx=20)
        
        self.btn_stop = ttk.Button(frame_ctrl, text="🛑 DỪNG", command=self.controller.stop_process, state="disabled")
        self.btn_stop.pack(side="right")

    def _load_defaults(self):
        """Load setting từ file config"""
        try:
            cfg = load_config()
            self.spin_limit.set(cfg["system"].get("loop_limit", 5))
            self.spin_threads.set(cfg["system"].get("max_threads", 3))
        except: pass

    # --- INPUT HANDLERS [MỚI] ---
    def _on_mode_change(self, event):
        """Khi đổi mode, thay đổi icon hoặc gợi ý (Optional)"""
        # Bạn có thể clear ô input nếu muốn an toàn:
        # self.entry_in.delete(0, tk.END)
        pass

    def _pick_input(self):
        """Hàm chọn Input thông minh dựa trên Mode"""
        mode = self.selected_mode.get()
        
        if mode == "SRT ➡ Prompt":
            # Nếu là mode SRT -> Chọn File .srt
            f = filedialog.askopenfilename(
                title="Chọn file phụ đề SRT",
                filetypes=[("SRT Files", "*.srt"), ("All Files", "*.*")]
            )
        else:
            # Nếu là mode khác -> Chọn Folder
            f = filedialog.askdirectory(title="Chọn thư mục Input")
            
        if f:
            self.entry_in.delete(0, tk.END)
            self.entry_in.insert(0, f)

    def _pick_folder(self, entry):
        """Hàm chọn Folder (cho Output)"""
        d = filedialog.askdirectory(title="Chọn thư mục Output")
        if d: 
            entry.delete(0, tk.END)
            entry.insert(0, d)

    def add_project_to_queue(self):
        inp = self.entry_in.get().strip()
        out = self.entry_out.get().strip()
        
        if not inp or not out: return
        
        # Thêm vào hàng đợi
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
        if 0 <= index < len(self.project_queue):
            self.project_queue[index]["status"] = status
            self.refresh_treeview()

    def update_dashboard_stats(self, total, pending, done):
        self.lbl_total.config(text=f"{total}")
        self.lbl_pending.config(text=f"{pending}")
        self.lbl_done.config(text=f"{done}")

    def toggle_buttons(self, is_running):
        state_run = "disabled" if is_running else "normal"
        state_stop = "normal" if is_running else "disabled"
        self.btn_run.config(state=state_run)
        self.btn_stop.config(state=state_stop)
        self.cbo_mode.config(state="disabled" if is_running else "readonly")