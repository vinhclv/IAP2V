import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os

from config import DEFAULT_INPUT, DEFAULT_OUTPUT, load_config, global_settings

# Đường dẫn file settings để đọc danh sách Gem
SETTINGS_FILE = "settings.json"

class DashboardTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller 
        self.project_queue = []
        
        # Biến lưu trữ checkbox ngôn ngữ
        self.lang_vars = {}
        # Lấy settings từ config global
        self.settings = global_settings
        self.lang_objects = self.settings.get("standardize", {}).get("languages", [])
        
        # Load danh sách Gem từ file settings
        self.gems_data = self._load_gems_from_settings()
        
        self._setup_ui()
        self._load_defaults() 
        
        # Chạy kiểm tra mode lần đầu để ẩn/hiện đúng trạng thái ban đầu
        self._on_mode_change(None)

    def _load_gems_from_settings(self):
        """Lấy danh sách Gem siêu tốc từ RAM thay vì đọc ổ đĩa"""
        return global_settings.get("gems", [])

    def _setup_ui(self):

        # 4. CONTROLS & MULTILANGUAGE OPTION
        self.frame_ctrl = ttk.Frame(self, padding=10)
        self.frame_ctrl.pack(fill="x")
        
        tk.Label(self.frame_ctrl, text="Chế độ chạy:", fg="white", bg="#2b2b2b").pack(side="left", padx=5)
        
        self.selected_mode = tk.StringVar(value="Image ➡ Prompt")
        self.cbo_mode = ttk.Combobox(self.frame_ctrl, textvariable=self.selected_mode, state="readonly", width=25)
        self.cbo_mode['values'] = (
            "Image ➡ Prompt", 
            "Prompt ➡ Video", 
            "SRT ➡ Prompt", 
            "Prompt ➡ Image", 
            "2_Image ➡ Prompt", 
            "SRT ➡ Image",
            "SRT ➡ Multilanguage"
        )
        self.cbo_mode.pack(side="left", padx=5)
        self.cbo_mode.bind("<<ComboboxSelected>>", self._on_mode_change)

        # Khối chọn ngôn ngữ (Mặc định ẩn)
        self.frame_langs = ttk.LabelFrame(self, text="🌐 Chọn ngôn ngữ chuẩn hóa (API)", padding=10)
        
        cb_container = ttk.Frame(self.frame_langs)
        cb_container.pack(fill="x")

        for i, lang in enumerate(self.lang_objects):
            var = tk.BooleanVar(value=False)
            self.lang_vars[lang["code"]] = var
            cb = ttk.Checkbutton(cb_container, text=lang["name"], variable=var)
            cb.grid(row=i // 5, column=i % 5, sticky="w", padx=15, pady=2)

        # Nút chạy đặt ở frame_ctrl
        self.btn_run = ttk.Button(self.frame_ctrl, text="▶ CHẠY LIST", style="Accent.TButton", command=self.controller.on_start_batch)
        self.btn_run.pack(side="left", padx=20)
        
        self.btn_stop = ttk.Button(self.frame_ctrl, text="🛑 DỪNG", command=self.controller.stop_process, state="disabled")
        self.btn_stop.pack(side="right")
        
        # 1. KHỐI THÊM DỰ ÁN
        frame_add = ttk.LabelFrame(self, text="➕ Thêm Dự án", padding=10)
        frame_add.pack(fill="x", padx=10, pady=5)

        # Cấu hình grid cho frame_add
        frame_add.columnconfigure(1, weight=1)
        
        # Input
        tk.Label(frame_add, text="Input:", fg="white", bg="#2b2b2b").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_in = ttk.Entry(frame_add)
        self.entry_in.insert(0, DEFAULT_INPUT)
        self.entry_in.grid(row=0, column=1, sticky="ew", padx=5)
        self.btn_in = ttk.Button(frame_add, text="📂", width=3, command=self._pick_input)
        self.btn_in.grid(row=0, column=2, padx=5)

        # Output
        tk.Label(frame_add, text="Output:", fg="white", bg="#2b2b2b").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_out = ttk.Entry(frame_add)
        self.entry_out.insert(0, DEFAULT_OUTPUT)
        self.entry_out.grid(row=1, column=1, sticky="ew", padx=5)
        self.btn_out = ttk.Button(frame_add, text="📂", width=3, command=lambda: self._pick_folder(self.entry_out))
        self.btn_out.grid(row=1, column=2, padx=5)

        # GEM & Prompt
        tk.Label(frame_add, text="GEM:", fg="white", bg="#2b2b2b").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        frame_url_prompt = ttk.Frame(frame_add)
        frame_url_prompt.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)
        frame_url_prompt.columnconfigure(0, weight=1)
        frame_url_prompt.columnconfigure(1, weight=2)

        gem_names = [g["name"] for g in self.gems_data]
        self.cbo_gem_url = ttk.Combobox(frame_url_prompt, values=gem_names, state="readonly")
        if gem_names: self.cbo_gem_url.current(0)
        self.cbo_gem_url.grid(row=0, column=0, sticky="ew", padx=(5, 5))
        
        self.entry_prompt = ttk.Entry(frame_url_prompt)
        self.entry_prompt.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self._set_placeholder(self.entry_prompt, "Nhập Prompt (Tùy chọn)...")

        self.btn_add = ttk.Button(frame_add, text="⬇ THÊM", command=self.add_project_to_queue)
        self.btn_add.grid(row=0, column=3, rowspan=3, padx=10, sticky="ns")

        # 2. DASHBOARD STATS
        frame_dash = ttk.LabelFrame(self, text="📊 Tiến độ Real-time", padding=15)
        frame_dash.pack(fill="x", padx=10, pady=5)
        for i in range(3): frame_dash.columnconfigure(i, weight=1)

        f1 = ttk.Frame(frame_dash); f1.grid(row=0, column=0)
        self.lbl_total = ttk.Label(f1, text="0", font=("Segoe UI", 24, "bold"), foreground="#888888")
        self.lbl_total.pack(); ttk.Label(f1, text="TỔNG FILE").pack()

        f2 = ttk.Frame(frame_dash); f2.grid(row=0, column=1)
        self.lbl_pending = ttk.Label(f2, text="0", font=("Segoe UI", 32, "bold"), foreground="#ffaa00")
        self.lbl_pending.pack(); ttk.Label(f2, text="CẦN LÀM").pack()

        f3 = ttk.Frame(frame_dash); f3.grid(row=0, column=2)
        self.lbl_done = ttk.Label(f3, text="0", font=("Segoe UI", 24, "bold"), foreground="#00cc6a")
        self.lbl_done.pack(); ttk.Label(f3, text="ĐÃ XONG").pack()

        # 3. HÀNG CHỜ (TREEVIEW)
        frame_list = ttk.LabelFrame(self, text="📋 Hàng chờ", padding=10)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("stt", "input", "output", "gem", "prompt", "status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=6)
        
        titles = {"stt": "#", "input": "Input", "output": "Output", "gem": "GEM", "prompt": "Prompt", "status": "Trạng thái"}
        widths = {"stt": 30, "input": 200, "output": 200, "gem": 100, "prompt": 150, "status": 100}
        for col, txt in titles.items():
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=widths[col], anchor="center" if col in ["stt", "status"] else "w")
        
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame_list, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set)

        frame_act = ttk.Frame(frame_list); frame_act.pack(side="bottom", fill="x", pady=5)
        ttk.Button(frame_act, text="❌ Xóa", command=self.remove_selected_project).pack(side="right")
        ttk.Button(frame_act, text="🧹 Xóa hết", command=self.clear_all_projects).pack(side="right", padx=5)

        

    # --- LOGIC ẨN/HIỆN ---
    def _on_mode_change(self, event):
        """Kiểm tra mode để hiện/ẩn checkbox ngôn ngữ"""
        if self.selected_mode.get() == "SRT ➡ Multilanguage":
            # Hiện khung ngôn ngữ ngay dưới frame_ctrl
            self.frame_langs.pack(fill="x", padx=10, pady=5, after=self.frame_ctrl)
        else:
            # Ẩn khung ngôn ngữ
            self.frame_langs.pack_forget()

    # --- INPUT HANDLERS & PROJECT QUEUE ---
    def _pick_input(self):
        mode = self.selected_mode.get()
        # Chấp nhận file cho các mode liên quan đến SRT hoặc Prompt đơn lẻ
        file_modes = ["SRT ➡ Prompt", "SRT ➡ Image", "Prompt ➡ Image", "SRT ➡ Multilanguage"]
        
        if mode in file_modes:
            if "SRT" in mode:
                f = filedialog.askopenfilename(title="Chọn file SRT", filetypes=[("SRT Files", "*.srt")])
            else:
                f = filedialog.askopenfilename(title="Chọn file Prompt", filetypes=[("JSON/TXT", "*.json *.txt")])
        else:
            f = filedialog.askdirectory(title="Chọn thư mục Input")
            
        if f:
            self.entry_in.delete(0, tk.END); self.entry_in.insert(0, f)

    def add_project_to_queue(self):
        inp = self.entry_in.get().strip()
        out = self.entry_out.get().strip()
        gem_name = self.cbo_gem_url.get().strip()
        prompt_val = self.entry_prompt.get().strip()
        mode = self.selected_mode.get()

        if prompt_val == "Nhập Prompt (Tùy chọn)...": prompt_val = ""
        if not inp or not out or not gem_name:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đầy đủ Input, Output và chọn GEM!")
            return

        # Lấy URL thực tế
        real_url = next((g["url"] for g in self.gems_data if g["name"] == gem_name), "https://gemini.google.com")

        # Nếu là mode Multilanguage, kiểm tra xem đã chọn ngôn ngữ nào chưa
        selected_langs = []
        if mode == "SRT ➡ Multilanguage":
            selected_langs = [code for code, var in self.lang_vars.items() if var.get()]
            if not selected_langs:
                messagebox.showwarning("Thiếu ngôn ngữ", "Vui lòng chọn ít nhất 1 ngôn ngữ để chuẩn hóa!")
                return

        task_item = {
            "input": inp,
            "output": out,
            "url": real_url,
            "gem_name": gem_name,
            "prompt": prompt_val,
            "languages": selected_langs, # Lưu danh sách ngôn ngữ vào task
            "status": "Waiting"
        }
        
        self.project_queue.append(task_item)
        self.refresh_treeview()

    # --- PHẦN CÒN LẠI GIỮ NGUYÊN ---
    def _set_placeholder(self, entry, text):
        entry.insert(0, text); entry.config(foreground="grey")
        entry.bind("<FocusIn>", lambda e: self._clear_placeholder(e, text))
        entry.bind("<FocusOut>", lambda e: self._add_placeholder(e, text))

    def _clear_placeholder(self, event, text):
        if event.widget.get() == text:
            event.widget.delete(0, tk.END); event.widget.config(foreground="white")

    def _add_placeholder(self, event, text):
        if not event.widget.get():
            event.widget.insert(0, text); event.widget.config(foreground="grey")

    def _pick_folder(self, entry):
        d = filedialog.askdirectory(); 
        if d: entry.delete(0, tk.END); entry.insert(0, d)

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
            self.tree.insert("", "end", values=(i+1, p["input"], p["output"], p["gem_name"], p["prompt"], p["status"]))

    def _load_defaults(self):
        pass # Có thể thêm logic load từ config nếu cần

    def refresh_gem_list(self):
        self.gems_data = self._load_gems_from_settings()
        gem_names = [g["name"] for g in self.gems_data]
        if hasattr(self, 'cbo_gem_url'):
            current = self.cbo_gem_url.get()
            self.cbo_gem_url['values'] = gem_names
            if gem_names and (not current or current not in gem_names):
                self.cbo_gem_url.current(0)
    def update_project_status(self, index, status):
        if 0 <= index < len(self.project_queue):
            self.project_queue[index]["status"] = status
            try:
                child_id = self.tree.get_children()[index]
                self.tree.set(child_id, "status", status)
            except: pass

    def update_dashboard_stats(self, total, pending, done):
        self.lbl_total.config(text=f"{total}")
        self.lbl_pending.config(text=f"{pending}")
        self.lbl_done.config(text=f"{done}")

    def toggle_buttons(self, is_running):
        s = "disabled" if is_running else "normal"
        self.btn_run.config(state=s)
        self.btn_stop.config(state="normal" if is_running else "disabled")
        self.cbo_mode.config(state="disabled" if is_running else "readonly")