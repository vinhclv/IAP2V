import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import threading
import time

# Import hàm khởi tạo driver từ file setup
from browser_setup import init_driver_from_profile

class ProfileManagerTab(ttk.Frame):
    def __init__(self, parent, profiles_dir):
        super().__init__(parent)
        self.profiles_dir = profiles_dir
        
        # Đảm bảo thư mục profiles tồn tại
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
            
        # Dictionary lưu biến Checkbox của từng profile
        # Key: Tên Profile, Value: tk.BooleanVar
        self.profile_vars = {} 

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # === 1. THANH CÔNG CỤ (TOP BAR) ===
        frame_top = ttk.Frame(self, padding=10)
        frame_top.pack(fill="x")

        # Ô nhập tên tạo mới
        self.entry_name = ttk.Entry(frame_top, width=30)
        self.entry_name.pack(side="left", padx=(0, 5))
        
        ttk.Button(frame_top, text="➕ Tạo Mới", style="Accent.TButton", command=self.add_profile).pack(side="left")
        ttk.Button(frame_top, text="📂 Import", command=self.import_profile).pack(side="right")
        
        # Nút chọn tất cả / Bỏ chọn
        ttk.Button(frame_top, text="☑️ Chọn hết", command=self.select_all).pack(side="right", padx=5)
        ttk.Button(frame_top, text="🔄 Refresh", command=self.refresh_list).pack(side="right", padx=5)

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # === 2. VÙNG CHỨA DANH SÁCH (SCROLLABLE AREA) ===
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.scrollbar.pack(side="right", fill="y")

        # Hỗ trợ cuộn chuột
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def refresh_list(self):
        """Vẽ lại toàn bộ danh sách profile"""
        # Xóa hết widget cũ
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Xóa dữ liệu biến checkbox cũ
        self.profile_vars.clear()

        if os.path.exists(self.profiles_dir):
            folders = sorted([f for f in os.listdir(self.profiles_dir) if os.path.isdir(os.path.join(self.profiles_dir, f))])
            
            if not folders:
                ttk.Label(self.scrollable_frame, text="Chưa có profile nào. Hãy tạo mới hoặc Import!", foreground="#888").pack(pady=20)
                return

            for folder_name in folders:
                self.create_profile_card(folder_name)

    def create_profile_card(self, profile_name):
        """Tạo giao diện thẻ cho 1 profile"""
        card = ttk.LabelFrame(self.scrollable_frame, padding=(5, 5))
        card.pack(fill="x", expand=True, padx=10, pady=2, anchor="n")

        # --- [QUAN TRỌNG] CHECKBOX CHỌN PROFILE ---
        var = tk.BooleanVar(value=True) # Mặc định tích chọn
        self.profile_vars[profile_name] = var # Lưu vào dict để Main lấy
        
        chk = ttk.Checkbutton(card, variable=var)
        chk.pack(side="left", padx=5)
        # ------------------------------------------

        # Icon & Tên
        lbl_icon = ttk.Label(card, text="👤", font=("Segoe UI", 12))
        lbl_icon.pack(side="left", padx=5)

        lbl_name = ttk.Label(card, text=profile_name, font=("Segoe UI", 10, "bold"))
        lbl_name.pack(side="left", padx=5)

        # Các nút chức năng
        # Nút Xóa
        btn_del = ttk.Button(card, text="🗑️", width=3, command=lambda p=profile_name: self.delete_profile(p))
        btn_del.pack(side="right", padx=2)

        # Nút Setup
        btn_setup = ttk.Button(
            card, 
            text="⚙️ Setup", 
            style="Accent.TButton", 
            command=lambda p=profile_name: self.open_browser_setup(p)
        )
        btn_setup.pack(side="right", padx=2)
        
        # Hiển thị dung lượng
        path = os.path.join(self.profiles_dir, profile_name)
        size_mb = self.get_size(path)
        ttk.Label(card, text=f"{size_mb:.1f} MB", font=("Segoe UI", 8), foreground="#888").pack(side="right", padx=10)

    # --- HÀM HỖ TRỢ MAIN GỌI ---
    def get_selected_profiles(self):
        """Trả về danh sách tên các profile đang được tích chọn"""
        return [name for name, var in self.profile_vars.items() if var.get()]

    def select_all(self):
        """Chọn tất cả hoặc bỏ chọn tất cả"""
        any_unchecked = any(not var.get() for var in self.profile_vars.values())
        new_val = True if any_unchecked else False
        for var in self.profile_vars.values():
            var.set(new_val)

    # --- LOGIC CHỨC NĂNG (Thêm/Xóa/Import/Setup) ---
    def add_profile(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên Profile!")
            return

        invalid_chars = '<>:"/\\|?*'
        if any(char in invalid_chars for char in name):
            messagebox.showerror("Lỗi", "Tên không được chứa ký tự đặc biệt!")
            return

        new_path = os.path.join(self.profiles_dir, name)
        if os.path.exists(new_path):
            messagebox.showerror("Lỗi", "Tên này đã tồn tại!")
            return

        os.makedirs(new_path)
        self.entry_name.delete(0, tk.END)
        self.refresh_list()

    def import_profile(self):
        source_dir = filedialog.askdirectory(title="Chọn folder chứa dữ liệu Profile cũ")
        if not source_dir: return

        folder_name = os.path.basename(source_dir)
        if folder_name.lower() in ['user data', 'default', 'profile']:
            folder_name = f"Imported_{int(time.time())}"
        
        dest_path = os.path.join(self.profiles_dir, folder_name)

        if os.path.exists(dest_path):
            messagebox.showerror("Lỗi", f"Profile '{folder_name}' đã tồn tại! Vui lòng đổi tên folder gốc.")
            return

        try:
            def copy_task():
                shutil.copytree(source_dir, dest_path)
                self.after(0, lambda: [messagebox.showinfo("Xong", "Import thành công!"), self.refresh_list()])
            
            threading.Thread(target=copy_task, daemon=True).start()
            messagebox.showinfo("Thông báo", "Đang copy dữ liệu... Vui lòng đợi trong giây lát.")
        except Exception as e:
            messagebox.showerror("Lỗi Import", str(e))

    def delete_profile(self, profile_name):
        confirm = messagebox.askyesno("Xác nhận", f"Xóa vĩnh viễn profile '{profile_name}'?")
        if confirm:
            try:
                shutil.rmtree(os.path.join(self.profiles_dir, profile_name))
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa: {e}")

    def open_browser_setup(self, profile_name):
        profile_path = os.path.join(self.profiles_dir, profile_name)
        
        def run_browser():
            print(f"Opening Setup for {profile_name}...")
            # Gọi init_driver_from_profile, hàm này cần có trong browser_setup.py
            # Chú ý: Hàm này phải trả về driver selenium
            driver = init_driver_from_profile(profile_path, log_callback=print)
            
            if driver:
                try:
                    driver.get("https://gemini.google.com")
                    # Loop giữ trình duyệt mở
                    while True:
                        try:
                            _ = driver.title 
                            time.sleep(1)
                        except:
                            break
                    print(f"Setup {profile_name} closed.")
                except Exception as e:
                    print(f"Browser Error: {e}")
                finally:
                    try: driver.quit()
                    except: pass
            else:
                print("Failed to open driver")

        threading.Thread(target=run_browser, daemon=True).start()

    def get_size(self, start_path):
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(start_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except: pass
        return total_size / (1024 * 1024)