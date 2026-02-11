import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from config import DEFAULT_INPUT, DEFAULT_OUTPUT, load_config

class DashboardTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller 
        self.project_queue = []
        
        self._setup_ui()
        self._load_defaults() 

    def _setup_ui(self):
        # 1. Thêm dự án
        frame_add = ttk.LabelFrame(self, text="➕ Thêm Dự án", padding=10)
        frame_add.pack(fill="x", padx=10, pady=5)

        # --- Dòng 1: Input ---
        ttk.Label(frame_add, text="Input:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_in = ttk.Entry(frame_add)
        self.entry_in.insert(0, DEFAULT_INPUT)
        self.entry_in.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Nút chọn Input (Gọi hàm riêng _pick_input để check mode)
        self.btn_in = ttk.Button(frame_add, text="📂", width=3, command=self._pick_input)
        self.btn_in.grid(row=0, column=2, padx=5)

        # --- Dòng 2: Output ---
        ttk.Label(frame_add, text="Output:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_out = ttk.Entry(frame_add)
        self.entry_out.insert(0, DEFAULT_OUTPUT)
        self.entry_out.grid(row=1, column=1, sticky="ew", padx=5)
        
        # Nút chọn Output (Luôn là Folder)
        self.btn_out = ttk.Button(frame_add, text="📂", width=3, command=lambda: self._pick_folder(self.entry_out))
        self.btn_out.grid(row=1, column=2, padx=5)

        # --- Dòng 3: URL và Prompt ---
        
        ttk.Label(frame_add, text="URL:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.entry_url = ttk.Entry(frame_add)
        self.entry_url.grid(row=2, column=1, sticky="ew", padx=5)
        self.entry_url.insert(0, "Nhập URL (Bắt buộc)...")
        self.entry_url.bind("<FocusIn>", lambda event: self._clear_placeholder(event, "Nhập URL (Bắt buộc)..."))
        self.entry_url.bind("<FocusOut>", lambda event: self._add_placeholder(event, "Nhập URL (Bắt buộc)..."))


        # Frame con cho dòng 3
        frame_url_prompt = ttk.Frame(frame_add)
        frame_url_prompt.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)
        frame_url_prompt.columnconfigure(0, weight=3)
        frame_url_prompt.columnconfigure(1, weight=2) 

        self.entry_url = ttk.Entry(frame_url_prompt)
        self.entry_url.grid(row=0, column=0, sticky="ew", padx=(5, 5))
        self._set_placeholder(self.entry_url, "Nhập URL (Bắt buộc)...")

        self.entry_prompt = ttk.Entry(frame_url_prompt)
        self.entry_prompt.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self._set_placeholder(self.entry_prompt, "Nhập Prompt (Tùy chọn)...")

        
        # Nút Thêm (Đặt ở bên phải cùng, trải dài 3 dòng)
        self.btn_add = ttk.Button(frame_add, text="⬇ THÊM", command=self.add_project_to_queue)
        self.btn_add.grid(row=0, column=3, rowspan=3, padx=10, sticky="ns")

        frame_add.columnconfigure(1, weight=1)

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

        # Thêm cột URL và Prompt vào Treeview
        columns = ("stt", "input", "output", "url", "prompt", "status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=6)
        
        self.tree.heading("stt", text="#"); self.tree.column("stt", width=30, anchor="center")
        self.tree.heading("input", text="Input"); self.tree.column("input", width=200)
        self.tree.heading("output", text="Output"); self.tree.column("output", width=200)
        self.tree.heading("url", text="URL"); self.tree.column("url", width=150)
        self.tree.heading("prompt", text="Prompt"); self.tree.column("prompt", width=150)
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
        
        self.cbo_mode['values'] = ("Image ➡ Prompt", "Prompt ➡ Video", "SRT ➡ Prompt", "Prompt ➡ Image", "2_Image ➡ Prompt", "SRT ➡ Image")
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

    # --- Helper Placeholder ---
    def _set_placeholder(self, entry, text):
        entry.insert(0, text)
        entry.configure(foreground="grey")
        entry.bind("<FocusIn>", lambda event: self._clear_placeholder(event, text))
        entry.bind("<FocusOut>", lambda event: self._add_placeholder(event, text))

    def _clear_placeholder(self, event, text):
        if event.widget.get() == text:
            event.widget.delete(0, tk.END)
            event.widget.configure(foreground="black")

    def _add_placeholder(self, event, text):
        if not event.widget.get():
            event.widget.insert(0, text)
            event.widget.configure(foreground="grey")

    # --- INPUT HANDLERS ---
    def _on_mode_change(self, event):
        # Có thể thêm logic thay đổi label Input/Output tùy mode
        pass

    def _pick_input(self):
        """Hàm chọn Input thông minh dựa trên Mode"""
        mode = self.selected_mode.get()
        
        # Các mode cần file input
        file_modes = ["SRT ➡ Prompt", "SRT ➡ Image", "Prompt ➡ Image"]
        
        if mode in file_modes:
            if "SRT" in mode:
                title = "Chọn file phụ đề SRT"
                filetypes = [("SRT Files", "*.srt"), ("All Files", "*.*")]
            else: 
                title = "Chọn file chứa Prompt (JSON/Text)"
                filetypes = [("JSON Files", "*.json"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            
            f = filedialog.askopenfilename(title=title, filetypes=filetypes)
        else:
            # Các mode folder input (Image -> Prompt, 2_Image -> Prompt...)
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
        url_val = self.entry_url.get().strip()
        prompt_val = self.entry_prompt.get().strip()

        # Xử lý placeholder (nếu người dùng không nhập gì mà để nguyên placeholder)
        if url_val == "Nhập URL (Bắt buộc)...": url_val = ""
        if prompt_val == "Nhập Prompt (Tùy chọn)...": prompt_val = ""

        # Validate
        if not inp or not out:
            messagebox.showerror("Lỗi", "Vui lòng chọn Input và Output!")
            return
        
        if not url_val:
            messagebox.showerror("Lỗi", "Vui lòng nhập URL!")
            return

        # Tạo Task Item
        task_item = {
            "input": inp,
            "output": out,
            "url": url_val,
            "prompt": prompt_val, # Optional
            "status": "Waiting"
        }
        
        # Thêm vào hàng đợi
        self.project_queue.append(task_item)
        self.refresh_treeview()
        
        # Reset form (giữ lại URL/Prompt placeholder nếu muốn hoặc xóa trắng)
        # self.entry_url.delete(0, tk.END); self._add_placeholder(type('obj', (object,), {'widget': self.entry_url}), "Nhập URL (Bắt buộc)...")

    def remove_selected_project(self):
        sel = self.tree.selection()
        if sel:
            # Xóa từ dưới lên để tránh lỗi index khi xóa nhiều dòng
            for item in reversed(sel):
                idx = self.tree.index(item)
                del self.project_queue[idx]
            self.refresh_treeview()

    def clear_all_projects(self):
        self.project_queue = []; self.refresh_treeview()

    def refresh_treeview(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, p in enumerate(self.project_queue):
            self.tree.insert("", "end", values=(i+1, p["input"], p["output"], p["url"], p["prompt"], p["status"]))

    def update_project_status(self, index, status):
        if 0 <= index < len(self.project_queue):
            self.project_queue[index]["status"] = status
            child_id = self.tree.get_children()[index]
            self.tree.set(child_id, "status", status)

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