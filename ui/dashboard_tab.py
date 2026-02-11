import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from config import DEFAULT_INPUT, DEFAULT_OUTPUT, load_config

# Đường dẫn file settings để đọc danh sách Gem
SETTINGS_FILE = "settings.json"

class DashboardTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller 
        self.project_queue = []
        
        # Load danh sách Gem từ file settings
        self.gems_data = self._load_gems_from_settings()
        
        self._setup_ui()
        self._load_defaults() 

    def _load_gems_from_settings(self):
        """Đọc danh sách Gem từ file json"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("gems", [])
            except: pass
        return []

    def refresh_gem_list(self):
        """Hàm này được gọi khi tab Settings thay đổi để cập nhật lại Combobox"""
        self.gems_data = self._load_gems_from_settings()
        gem_names = [g["name"] for g in self.gems_data]
        
        # Cập nhật values cho Combobox
        if hasattr(self, 'cbo_gem_url'):
            self.cbo_gem_url['values'] = gem_names
            # Nếu danh sách không rỗng và hiện tại chưa chọn gì (hoặc giá trị cũ không còn), chọn cái đầu tiên
            if gem_names:
                current = self.cbo_gem_url.get()
                if not current or current not in gem_names:
                    self.cbo_gem_url.current(0)

    def _setup_ui(self):
        # 1. Thêm dự án
        frame_add = ttk.LabelFrame(self, text="➕ Thêm Dự án", padding=10)
        frame_add.pack(fill="x", padx=10, pady=5)

        # --- Dòng 1: Input ---
        # Sử dụng tk.Label để ép màu chữ trắng (nếu dùng theme tối)
        tk.Label(frame_add, text="Input:", fg="white", bg="#2b2b2b").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.entry_in = ttk.Entry(frame_add)
        self.entry_in.insert(0, DEFAULT_INPUT)
        self.entry_in.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Nút chọn Input
        self.btn_in = ttk.Button(frame_add, text="📂", width=3, command=self._pick_input)
        self.btn_in.grid(row=0, column=2, padx=5)

        # --- Dòng 2: Output ---
        tk.Label(frame_add, text="Output:", fg="white", bg="#2b2b2b").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        self.entry_out = ttk.Entry(frame_add)
        self.entry_out.insert(0, DEFAULT_OUTPUT)
        self.entry_out.grid(row=1, column=1, sticky="ew", padx=5)
        
        # Nút chọn Output
        self.btn_out = ttk.Button(frame_add, text="📂", width=3, command=lambda: self._pick_folder(self.entry_out))
        self.btn_out.grid(row=1, column=2, padx=5)

        # --- Dòng 3: URL (GEM) và Prompt ---
        tk.Label(frame_add, text="GEM:", fg="white", bg="#2b2b2b").grid(row=2, column=0, sticky="w", padx=5, pady=5)

        # Frame con cho dòng 3
        frame_url_prompt = ttk.Frame(frame_add)
        frame_url_prompt.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)
        
        # Chia cột: GEM chiếm ít hơn, Prompt chiếm nhiều hơn
        frame_url_prompt.columnconfigure(0, weight=1) # Cột GEM
        frame_url_prompt.columnconfigure(1, weight=2) # Cột Prompt

        # [THAY ĐỔI] Thay Entry URL bằng Combobox chọn GEM
        gem_names = [g["name"] for g in self.gems_data]
        self.cbo_gem_url = ttk.Combobox(frame_url_prompt, values=gem_names, state="readonly")
        if gem_names: self.cbo_gem_url.current(0)
        self.cbo_gem_url.grid(row=0, column=0, sticky="ew", padx=(5, 5))
        
        # Ô nhập Prompt (Optional)
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

        # Cột URL giờ sẽ hiển thị tên GEM cho gọn (hoặc URL nếu muốn)
        columns = ("stt", "input", "output", "gem", "prompt", "status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=6)
        
        self.tree.heading("stt", text="#"); self.tree.column("stt", width=30, anchor="center")
        self.tree.heading("input", text="Input"); self.tree.column("input", width=200)
        self.tree.heading("output", text="Output"); self.tree.column("output", width=200)
        self.tree.heading("gem", text="GEM"); self.tree.column("gem", width=100) # Đổi tên cột
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

    # --- HELPER FUNCTIONS ---
    def _set_placeholder(self, entry, text):
        entry.insert(0, text)
        entry.config(foreground="grey")
        entry.bind("<FocusIn>", lambda e: self._clear_placeholder(e, text))
        entry.bind("<FocusOut>", lambda e: self._add_placeholder(e, text))

    def _clear_placeholder(self, event, text):
        if event.widget.get() == text:
            event.widget.delete(0, tk.END)
            event.widget.config(foreground="white") # Hoặc màu theme

    def _add_placeholder(self, event, text):
        if not event.widget.get():
            event.widget.insert(0, text)
            event.widget.config(foreground="grey")

    def _load_defaults(self):
        try:
            cfg = load_config()
            self.spin_limit.set(cfg["system"].get("loop_limit", 5))
            self.spin_threads.set(cfg["system"].get("max_threads", 3))
        except: pass

    # --- INPUT HANDLERS ---
    def _on_mode_change(self, event):
        pass

    def _pick_input(self):
        mode = self.selected_mode.get()
        file_modes = ["SRT ➡ Prompt", "SRT ➡ Image", "Prompt ➡ Image"]
        
        if mode in file_modes:
            if "SRT" in mode:
                title = "Chọn file phụ đề SRT"
                filetypes = [("SRT Files", "*.srt"), ("All Files", "*.*")]
            else:
                title = "Chọn file chứa Prompt"
                filetypes = [("JSON Files", "*.json"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            f = filedialog.askopenfilename(title=title, filetypes=filetypes)
        else:
            f = filedialog.askdirectory(title="Chọn thư mục Input")
            
        if f:
            self.entry_in.delete(0, tk.END)
            self.entry_in.insert(0, f)

    def _pick_folder(self, entry):
        d = filedialog.askdirectory(title="Chọn thư mục Output")
        if d: 
            entry.delete(0, tk.END)
            entry.insert(0, d)

    def add_project_to_queue(self):
        inp = self.entry_in.get().strip()
        out = self.entry_out.get().strip()
        gem_name = self.cbo_gem_url.get().strip()
        prompt_val = self.entry_prompt.get().strip()

        if prompt_val == "Nhập Prompt (Tùy chọn)...": prompt_val = ""

        if not inp or not out:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn Input và Output!")
            return
        
        if not gem_name:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn GEM!")
            return

        # Tìm URL thực sự từ tên Gem
        real_url = next((g["url"] for g in self.gems_data if g["name"] == gem_name), "https://gemini.google.com")

        task_item = {
            "input": inp,
            "output": out,
            "url": real_url, # Lưu URL thực để Worker dùng
            "gem_name": gem_name, # Lưu tên để hiển thị
            "prompt": prompt_val,
            "status": "Waiting"
        }
        
        self.project_queue.append(task_item)
        self.refresh_treeview()

    def remove_selected_project(self):
        sel = self.tree.selection()
        if sel:
            for item in reversed(sel):
                idx = self.tree.index(item)
                del self.project_queue[idx]
            self.refresh_treeview()

    def clear_all_projects(self):
        self.project_queue = []; self.refresh_treeview()

    def refresh_treeview(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, p in enumerate(self.project_queue):
            # Hiển thị Tên GEM thay vì URL dài dòng
            self.tree.insert("", "end", values=(i+1, p["input"], p["output"], p["gem_name"], p["prompt"], p["status"]))

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
        
    def refresh_gem_list(self):
        """Reload dữ liệu từ file json và cập nhật Combobox"""
        # 1. Đọc lại file
        self.gems_data = self._load_gems_from_settings()
        gem_names = [g["name"] for g in self.gems_data]
        
        # 2. Cập nhật Combobox
        if hasattr(self, 'cbo_gem_url'):
            current_val = self.cbo_gem_url.get()
            self.cbo_gem_url['values'] = gem_names
            
            # Giữ lại giá trị cũ nếu còn tồn tại, không thì về mặc định
            if current_val not in gem_names and gem_names:
                self.cbo_gem_url.current(0)
            elif not current_val and gem_names:
                self.cbo_gem_url.current(0)