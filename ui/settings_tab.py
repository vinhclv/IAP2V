import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os

SETTINGS_FILE = "settings.json"

# Cấu hình mặc định
DEFAULT_SETTINGS = {
    "system": {
        "max_threads": 3,
        "loop_limit": 5,
        "max_retries": 30,
        "wait_time": 5
    },
    "projects": [], # Thêm key để lưu danh sách dự án
    "gems": []
}

class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = self.load_settings()
        self._setup_ui()

    def _setup_ui(self):
        # Container chính bọc toàn bộ (có padding để không dính sát viền)
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 1. KHỐI CẤU HÌNH HỆ THỐNG ---
        sys_frame = ttk.LabelFrame(main_container, text="⚙️ Cấu hình Hệ thống", padding=(10, 5))
        sys_frame.pack(fill="x", pady=(0, 10))

        # Dàn các tham số thành 1 hàng ngang
        tk.Label(sys_frame, text="Threads:", fg="white", bg="#2b2b2b").pack(side="left", padx=(5, 2))
        self.var_threads = tk.IntVar(value=self.settings["system"]["max_threads"])
        ttk.Spinbox(sys_frame, from_=1, to=20, textvariable=self.var_threads, width=5).pack(side="left", padx=5)

        tk.Label(sys_frame, text="Batch:", fg="white", bg="#2b2b2b").pack(side="left", padx=(15, 2))
        self.var_limit = tk.IntVar(value=self.settings["system"]["loop_limit"])
        ttk.Spinbox(sys_frame, from_=1, to=100, textvariable=self.var_limit, width=5).pack(side="left", padx=5)

        tk.Label(sys_frame, text="Retries:", fg="white", bg="#2b2b2b").pack(side="left", padx=(15, 2))
        self.var_retries = tk.IntVar(value=self.settings["system"]["max_retries"])
        ttk.Entry(sys_frame, textvariable=self.var_retries, width=5).pack(side="left", padx=5)

        # --- 2. KHỐI QUẢN LÝ DỰ ÁN (MỚI THÊM) ---
        project_frame = ttk.LabelFrame(main_container, text="📁 Quản lý Dự án", padding=(10, 5))
        project_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(project_frame, text="Danh sách dự án hiện có:").pack(side="left", padx=(0, 5))
        
        # Combobox hiển thị nhanh các dự án đang có trong settings
        self.cbo_projects_preview = ttk.Combobox(project_frame, state="readonly", width=30)
        self.cbo_projects_preview.pack(side="left", padx=5)
        self._refresh_project_combobox()

        # Nút tạo dự án mới
        ttk.Button(project_frame, text="✨ Khởi tạo Dự án Mới", command=self.open_create_project_popup).pack(side="right", padx=5)


        # --- 3. KHỐI QUẢN LÝ GEM ---
        gem_frame = ttk.LabelFrame(main_container, text="💎 Quản lý GEM", padding=10)
        gem_frame.pack(fill="both", expand=True)

        # A. Dòng nhập liệu (Input Row)
        input_row = ttk.Frame(gem_frame)
        input_row.pack(fill="x", pady=(0, 10))

        self.entry_name = ttk.Entry(input_row, width=20)
        self.entry_name.pack(side="left", padx=(0, 5))
        self._set_placeholder(self.entry_name, "Tên Gem...")

        self.entry_url = ttk.Entry(input_row)
        self.entry_url.pack(side="left", fill="x", expand=True, padx=5)
        self._set_placeholder(self.entry_url, "Đường dẫn URL...")

        ttk.Button(input_row, text="➕ Thêm", command=self.add_gem).pack(side="left", padx=5)

        # B. Bảng dữ liệu (Treeview)
        tree_container = ttk.Frame(gem_frame)
        tree_container.pack(fill="both", expand=True)

        self.gem_tree = ttk.Treeview(tree_container, columns=("name", "url"), show="headings", selectmode="browse")
        
        self.gem_tree.heading("name", text="Tên Gem")
        self.gem_tree.heading("url", text="URL")
        self.gem_tree.column("name", width=150, minwidth=100, stretch=False)
        self.gem_tree.column("url", width=400, minwidth=200, stretch=True)

        scrollbar_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.gem_tree.yview)
        self.gem_tree.configure(yscrollcommand=scrollbar_y.set)

        self.gem_tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # C. Thanh công cụ dưới bảng
        action_bar = ttk.Frame(gem_frame)
        action_bar.pack(fill="x", pady=(5, 0))
        ttk.Label(action_bar, text="* Chọn dòng để xóa", font=("Arial", 8), foreground="gray").pack(side="left")
        ttk.Button(action_bar, text="🗑️ Xóa dòng chọn", command=self.delete_gem).pack(side="right")

        # --- 4. THANH NÚT CHỨC NĂNG (DƯỚI CÙNG) ---
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="💾 LƯU CẤU HÌNH", style="Accent.TButton", command=self.save_settings).pack(side="right")
        ttk.Button(btn_frame, text="🔄 Mặc định", command=self.reset_defaults).pack(side="right", padx=10)

        self._load_gems_to_tree()

    # --- LOGIC XỬ LÝ PROJECT (MỚI) ---

    def _refresh_project_combobox(self):
        """Cập nhật danh sách dự án trong combobox hiển thị"""
        project_names = [p["name"] for p in self.settings.get("projects", [])]
        self.cbo_projects_preview['values'] = project_names
        if project_names:
            self.cbo_projects_preview.current(len(project_names)-1)

    def open_create_project_popup(self):
        """Mở popup nhập thông tin dự án"""
        popup = tk.Toplevel(self)
        popup.title("Khởi tạo Dự án Mới")
        popup.geometry("500x200")
        popup.resizable(False, False)
        
        # Center popup
        try:
            popup.transient(self.winfo_toplevel())
            popup.grab_set()
        except: pass

        # Layout Popup
        content = ttk.Frame(popup, padding=20)
        content.pack(fill="both", expand=True)

        # Tên dự án
        ttk.Label(content, text="Tên Dự án:").grid(row=0, column=0, sticky="w", pady=5)
        name_var = tk.StringVar()
        ttk.Entry(content, textvariable=name_var, width=40).grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Đường dẫn
        ttk.Label(content, text="Nơi lưu:").grid(row=1, column=0, sticky="w", pady=5)
        path_var = tk.StringVar()
        entry_path = ttk.Entry(content, textvariable=path_var, width=30)
        entry_path.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Nút Browse
        def browse_folder():
            folder_selected = filedialog.askdirectory()
            if folder_selected:
                path_var.set(folder_selected)
        
        ttk.Button(content, text="📂", width=3, command=browse_folder).grid(row=1, column=2, pady=5)

        # Logic Tạo (Được tích hợp từ yêu cầu của bạn)
        def save_project_action():
            p_name = name_var.get().strip()
            p_path = path_var.get().strip()

            if not p_name:
                messagebox.showerror("Lỗi", "Vui lòng nhập tên Dự án!", parent=popup)
                return
            
            # Nếu để trống, lấy đường dẫn mặc định
            if not p_path:
                p_path = os.path.join(os.getcwd(), 'assets', p_name)

            # Tự động tạo cấu trúc chuẩn
            try:
                folders_to_create = [
                    "input",
                    "output",
                    "init_assesst",
                    "voice_process",
                    "process/image_and_prompt_to_video/2_image_and_prompt_to_video",
                    "process/image_and_prompt_to_video/1_image_and_prompt_to_video",
                    "process/image_to_prompt/2_image_to_prompt",
                    "process/image_to_prompt/1_image_to_prompt",
                    "process/srt_to_image",
                    "process/srt_to_prompt/prompt_to_image"
                ]

                # Lặp qua danh sách và tạo thư mục
                for folder in folders_to_create:
                    # Tạo đường dẫn đầy đủ, tương thích mọi OS
                    full_path = os.path.join(p_path, *folder.split("/"))
                    os.makedirs(full_path, exist_ok=True)

            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể tạo cấu trúc thư mục dự án: {e}", parent=popup)
                return

            # Lưu vào settings hiện tại
            new_project = {"name": p_name, "path": p_path}
            
            # Kiểm tra trùng lặp (optional)
            for p in self.settings["projects"]:
                if p["name"] == p_name:
                    messagebox.showwarning("Chú ý", f"Dự án '{p_name}' đã tồn tại trong danh sách.", parent=popup)
                    # Vẫn cho tạo folder nhưng không add trùng vào list
                    popup.destroy()
                    return

            self.settings["projects"].append(new_project)
            
            # Refresh UI
            self._refresh_project_combobox()
            self.save_settings() # Lưu ngay vào file settings.json
            
            messagebox.showinfo("Thành công", f"Đã khởi tạo dự án: {p_name}\nTại: {p_path}", parent=self)
            popup.destroy()

        # Nút Action
        btn_container = ttk.Frame(content)
        btn_container.grid(row=2, column=0, columnspan=3, pady=20)
        ttk.Button(btn_container, text="Hủy", command=popup.destroy).pack(side="left", padx=10)
        ttk.Button(btn_container, text="✅ TẠO DỰ ÁN", style="Accent.TButton", command=save_project_action).pack(side="left", padx=10)

    # --- LOGIC CŨ (GIỮ NGUYÊN) ---

    def _set_placeholder(self, entry, text):
        entry.insert(0, text)
        entry.config(foreground="grey")
        entry.bind("<FocusIn>", lambda e: self._on_focus_in(entry, text))
        entry.bind("<FocusOut>", lambda e: self._on_focus_out(entry, text))

    def _on_focus_in(self, entry, text):
        if entry.get() == text:
            entry.delete(0, tk.END)
            entry.config(foreground="white")

    def _on_focus_out(self, entry, text):
        if not entry.get():
            entry.insert(0, text)
            entry.config(foreground="grey")

    def _load_gems_to_tree(self):
        for item in self.gem_tree.get_children():
            self.gem_tree.delete(item)
        for gem in self.settings.get("gems", []):
            self.gem_tree.insert("", "end", values=(gem["name"], gem["url"]))

    def add_gem(self):
        name = self.entry_name.get().strip()
        url = self.entry_url.get().strip()
        if name == "Tên Gem..." or url == "Đường dẫn URL..." or not name or not url:
            return 
        self.settings["gems"].append({"name": name, "url": url})
        self._load_gems_to_tree()
        self.entry_name.delete(0, tk.END); self._on_focus_out(self.entry_name, "Tên Gem...")
        self.entry_url.delete(0, tk.END); self._on_focus_out(self.entry_url, "Đường dẫn URL...")

    def delete_gem(self):
        sel = self.gem_tree.selection()
        if sel:
            idx = self.gem_tree.index(sel[0])
            del self.settings["gems"][idx]
            self._load_gems_to_tree()

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE): return DEFAULT_SETTINGS
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "gems" not in data: data["gems"] = []
                if "projects" not in data: data["projects"] = [] # Đảm bảo có key projects
                if "system" not in data: data["system"] = DEFAULT_SETTINGS["system"]
                return data
        except:
            return DEFAULT_SETTINGS

    def save_settings(self):
        self.settings["system"]["max_threads"] = self.var_threads.get()
        self.settings["system"]["loop_limit"] = self.var_limit.get()
        self.settings["system"]["max_retries"] = int(self.var_retries.get())
        
        # Lưu toàn bộ self.settings (đã bao gồm projects và gems)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            messagebox.showinfo("Thành công", "Đã lưu cấu hình!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def reset_defaults(self):
        if messagebox.askyesno("Xác nhận", "Về mặc định? Dữ liệu Gem và Dự án sẽ mất hết."):
            self.settings = json.loads(json.dumps(DEFAULT_SETTINGS))
            self.var_threads.set(self.settings["system"]["max_threads"])
            self.var_limit.set(self.settings["system"]["loop_limit"])
            self.var_retries.set(self.settings["system"]["max_retries"])
            self._load_gems_to_tree()
            self._refresh_project_combobox()
            self.save_settings()