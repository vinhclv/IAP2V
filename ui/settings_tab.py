import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

SETTINGS_FILE = "settings.json"

# Cấu hình mặc định (Đã bỏ URLs thừa)
DEFAULT_SETTINGS = {
    "system": {
        "max_threads": 3,
        "loop_limit": 5,
        "max_retries": 30,
        "wait_time": 5
    },
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

        # --- 1. KHỐI CẤU HÌNH HỆ THỐNG (GỌN GÀNG TRÊN CÙNG) ---
        sys_frame = ttk.LabelFrame(main_container, text="⚙️ Cấu hình Hệ thống", padding=(10, 5))
        sys_frame.pack(fill="x", pady=(0, 10))

        # Dàn các tham số thành 1 hàng ngang (Row 0)
        # Threads
        tk.Label(sys_frame, text="Threads:", fg="white", bg="#2b2b2b").pack(side="left", padx=(5, 2))
        self.var_threads = tk.IntVar(value=self.settings["system"]["max_threads"])
        ttk.Spinbox(sys_frame, from_=1, to=20, textvariable=self.var_threads, width=5).pack(side="left", padx=5)

        # Batch
        tk.Label(sys_frame, text="Batch:", fg="white", bg="#2b2b2b").pack(side="left", padx=(15, 2))
        self.var_limit = tk.IntVar(value=self.settings["system"]["loop_limit"])
        ttk.Spinbox(sys_frame, from_=1, to=100, textvariable=self.var_limit, width=5).pack(side="left", padx=5)

        # Retries
        tk.Label(sys_frame, text="Retries:", fg="white", bg="#2b2b2b").pack(side="left", padx=(15, 2))
        self.var_retries = tk.IntVar(value=self.settings["system"]["max_retries"])
        ttk.Entry(sys_frame, textvariable=self.var_retries, width=5).pack(side="left", padx=5)

        # --- 2. KHỐI QUẢN LÝ GEM (CHIẾM PHẦN CÒN LẠI) ---
        gem_frame = ttk.LabelFrame(main_container, text="💎 Quản lý GEM", padding=10)
        gem_frame.pack(fill="both", expand=True)

        # A. Dòng nhập liệu (Input Row) - Tối ưu diện tích
        input_row = ttk.Frame(gem_frame)
        input_row.pack(fill="x", pady=(0, 10))

        # Tên Gem
        self.entry_name = ttk.Entry(input_row, width=20)
        self.entry_name.pack(side="left", padx=(0, 5))
        self._set_placeholder(self.entry_name, "Tên Gem...")

        # URL Gem (Sẽ giãn hết cỡ chiều ngang còn lại)
        self.entry_url = ttk.Entry(input_row)
        self.entry_url.pack(side="left", fill="x", expand=True, padx=5)
        self._set_placeholder(self.entry_url, "Đường dẫn URL...")

        # Nút Thêm
        ttk.Button(input_row, text="➕ Thêm", command=self.add_gem).pack(side="left", padx=5)

        # B. Bảng dữ liệu (Treeview)
        # Khung chứa bảng và thanh cuộn
        tree_container = ttk.Frame(gem_frame)
        tree_container.pack(fill="both", expand=True)

        self.gem_tree = ttk.Treeview(tree_container, columns=("name", "url"), show="headings", selectmode="browse")
        
        # Cấu hình cột
        self.gem_tree.heading("name", text="Tên Gem")
        self.gem_tree.heading("url", text="URL")
        self.gem_tree.column("name", width=150, minwidth=100, stretch=False) # Cột tên cố định độ rộng
        self.gem_tree.column("url", width=400, minwidth=200, stretch=True)   # Cột URL tự giãn

        # Thanh cuộn dọc
        scrollbar_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.gem_tree.yview)
        self.gem_tree.configure(yscrollcommand=scrollbar_y.set)

        self.gem_tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # C. Thanh công cụ dưới bảng (Xóa)
        action_bar = ttk.Frame(gem_frame)
        action_bar.pack(fill="x", pady=(5, 0))
        ttk.Label(action_bar, text="* Chọn dòng để xóa", font=("Arial", 8), foreground="gray").pack(side="left")
        ttk.Button(action_bar, text="🗑️ Xóa dòng chọn", command=self.delete_gem).pack(side="right")

        # --- 3. THANH NÚT CHỨC NĂNG (DƯỚI CÙNG) ---
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="💾 LƯU CẤU HÌNH", style="Accent.TButton", command=self.save_settings).pack(side="right")
        ttk.Button(btn_frame, text="🔄 Mặc định", command=self.reset_defaults).pack(side="right", padx=10)

        # Load dữ liệu lên bảng
        self._load_gems_to_tree()

    # --- LOGIC XỬ LÝ ---

    def _set_placeholder(self, entry, text):
        entry.insert(0, text)
        entry.config(foreground="grey")
        entry.bind("<FocusIn>", lambda e: self._on_focus_in(entry, text))
        entry.bind("<FocusOut>", lambda e: self._on_focus_out(entry, text))

    def _on_focus_in(self, entry, text):
        if entry.get() == text:
            entry.delete(0, tk.END)
            entry.config(foreground="white") # Hoặc màu mặc định của theme

    def _on_focus_out(self, entry, text):
        if not entry.get():
            entry.insert(0, text)
            entry.config(foreground="grey")

    def _load_gems_to_tree(self):
        # Xóa cũ
        for item in self.gem_tree.get_children():
            self.gem_tree.delete(item)
        # Thêm mới
        for gem in self.settings.get("gems", []):
            self.gem_tree.insert("", "end", values=(gem["name"], gem["url"]))

    def add_gem(self):
        name = self.entry_name.get().strip()
        url = self.entry_url.get().strip()
        
        # Check placeholder
        if name == "Tên Gem..." or url == "Đường dẫn URL..." or not name or not url:
            return # Không làm gì nếu để trống
            
        self.settings["gems"].append({"name": name, "url": url})
        self._load_gems_to_tree()
        
        # Reset inputs
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
                # Đảm bảo cấu trúc đúng (merge với default nếu thiếu key)
                if "gems" not in data: data["gems"] = []
                if "system" not in data: data["system"] = DEFAULT_SETTINGS["system"]
                return data
        except:
            return DEFAULT_SETTINGS

    def save_settings(self):
        # Cập nhật giá trị system từ UI vào biến settings
        self.settings["system"]["max_threads"] = self.var_threads.get()
        self.settings["system"]["loop_limit"] = self.var_limit.get()
        self.settings["system"]["max_retries"] = int(self.var_retries.get())
        
        # Lưu file (Đã tự động loại bỏ các key thừa như gemini_url cũ nếu không có trong self.settings)
        # Tuy nhiên self.settings load từ file cũ có thể vẫn còn key thừa, ta làm sạch:
        clean_settings = {
            "system": self.settings["system"],
            "gems": self.settings["gems"]
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(clean_settings, f, indent=4)
            messagebox.showinfo("Thành công", "Đã lưu cấu hình!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def reset_defaults(self):
        if messagebox.askyesno("Xác nhận", "Về mặc định? Dữ liệu Gem sẽ mất hết."):
            self.settings = json.loads(json.dumps(DEFAULT_SETTINGS)) # Deep copy
            self.var_threads.set(self.settings["system"]["max_threads"])
            self.var_limit.set(self.settings["system"]["loop_limit"])
            self.var_retries.set(self.settings["system"]["max_retries"])
            self._load_gems_to_tree()
            self.save_settings()