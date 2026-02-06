# ui/settings_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

# Đường dẫn file lưu cấu hình
SETTINGS_FILE = "settings.json"

# Cấu hình mặc định (nếu chưa có file json)
DEFAULT_SETTINGS = {
    "system": {
        "max_threads": 3,
        "loop_limit": 5,
        "max_retries": 30,
        "wait_time": 5
    },
    "urls": {
        "gemini_url": "https://gemini.google.com",
        "videofx_url": "https://labs.google/fx/tools/video-fx"
    }
}

class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = self.load_settings()
        self._setup_ui()

    def _setup_ui(self):
        # Tạo canvas để cuộn nếu setting quá dài (Optional, nhưng tốt cho tương lai)
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === GROUP 1: HỆ THỐNG ===
        grp_sys = ttk.LabelFrame(main_frame, text="⚙️ Cấu hình Hệ thống", padding=10)
        grp_sys.pack(fill="x", pady=5)

        # Max Threads
        ttk.Label(grp_sys, text="Số luồng (Threads):").grid(row=0, column=0, sticky="w", pady=5)
        self.var_threads = tk.IntVar(value=self.settings["system"]["max_threads"])
        ttk.Spinbox(grp_sys, from_=1, to=20, textvariable=self.var_threads, width=10).grid(row=0, column=1, sticky="w", padx=10)

        # Loop Limit
        ttk.Label(grp_sys, text="Số lượng file mỗi lần lấy (Batch):").grid(row=1, column=0, sticky="w", pady=5)
        self.var_limit = tk.IntVar(value=self.settings["system"]["loop_limit"])
        ttk.Spinbox(grp_sys, from_=1, to=100, textvariable=self.var_limit, width=10).grid(row=1, column=1, sticky="w", padx=10)

        # Max Retries
        ttk.Label(grp_sys, text="Số lần thử lại tối đa (Retries):").grid(row=2, column=0, sticky="w", pady=5)
        self.var_retries = tk.IntVar(value=self.settings["system"]["max_retries"])
        ttk.Entry(grp_sys, textvariable=self.var_retries, width=12).grid(row=2, column=1, sticky="w", padx=10)

        # === GROUP 2: ĐƯỜNG DẪN URL ===
        grp_url = ttk.LabelFrame(main_frame, text="🌐 Cấu hình URL", padding=10)
        grp_url.pack(fill="x", pady=5)

        # Gemini URL
        ttk.Label(grp_url, text="Gemini URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.var_gemini = tk.StringVar(value=self.settings["urls"]["gemini_url"])
        ttk.Entry(grp_url, textvariable=self.var_gemini, width=50).grid(row=0, column=1, sticky="w", padx=10)

        # VideoFX URL
        ttk.Label(grp_url, text="VideoFX URL:").grid(row=1, column=0, sticky="w", pady=5)
        self.var_videofx = tk.StringVar(value=self.settings["urls"]["videofx_url"])
        ttk.Entry(grp_url, textvariable=self.var_videofx, width=50).grid(row=1, column=1, sticky="w", padx=10)

        # === NÚT LƯU ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=20)
        
        ttk.Button(btn_frame, text="💾 LƯU CẤU HÌNH", style="Accent.TButton", command=self.save_settings).pack(side="right")
        ttk.Button(btn_frame, text="🔄 Đặt lại mặc định", command=self.reset_defaults).pack(side="right", padx=10)

    def load_settings(self):
        """Đọc file json, nếu lỗi hoặc không có thì dùng mặc định"""
        if not os.path.exists(SETTINGS_FILE):
            return DEFAULT_SETTINGS
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_SETTINGS

    def save_settings(self):
        """Lấy giá trị từ UI và lưu vào file"""
        new_settings = {
            "system": {
                "max_threads": self.var_threads.get(),
                "loop_limit": self.var_limit.get(),
                "max_retries": self.var_retries.get(),
                "wait_time": 5
            },
            "urls": {
                "gemini_url": self.var_gemini.get().strip(),
                "videofx_url": self.var_videofx.get().strip()
            }
        }
        
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(new_settings, f, indent=4)
            messagebox.showinfo("Thành công", "Đã lưu cấu hình! Hãy khởi động lại tool để áp dụng triệt để.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def reset_defaults(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn về mặc định?"):
            self.var_threads.set(DEFAULT_SETTINGS["system"]["max_threads"])
            self.var_limit.set(DEFAULT_SETTINGS["system"]["loop_limit"])
            self.var_retries.set(DEFAULT_SETTINGS["system"]["max_retries"])
            self.var_gemini.set(DEFAULT_SETTINGS["urls"]["gemini_url"])
            self.var_videofx.set(DEFAULT_SETTINGS["urls"]["videofx_url"])