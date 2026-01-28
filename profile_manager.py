import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import threading
import time

# Import hàm khởi tạo driver từ file setup
# Lưu ý: Đảm bảo file browser_setup.py nằm cùng thư mục
from browser_setup import init_driver_from_profile

class ProfileManagerTab(ttk.Frame):
    def __init__(self, parent, profiles_dir):
        super().__init__(parent)
        self.profiles_dir = profiles_dir
        
        # Đảm bảo thư mục profiles tồn tại
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # === 1. THANH CÔNG CỤ (TOP BAR) ===
        frame_top = ttk.Frame(self, padding=10)
        frame_top.pack(fill="x")

        # Nút Import (Giả lập kéo thả folder)
        btn_import = ttk.Button(frame_top, text="📂 Import Folder Profile có sẵn", command=self.import_profile)
        btn_import.pack(side="right")

        # Nút Refresh
        btn_refresh = ttk.Button(frame_top, text="🔄 Làm mới", command=self.refresh_list)
        btn_refresh.pack(side="right", padx=5)

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # === 2. VÙNG CHỨA DANH SÁCH (SCROLLABLE AREA) ===
        # Tạo Canvas và Scrollbar để cuộn danh sách
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Frame chứa các Card Profile
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Logic cuộn
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Layout Canvas
        self.canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.scrollbar.pack(side="right", fill="y")

        # Hỗ trợ cuộn chuột
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def refresh_list(self):
        """Vẽ lại toàn bộ danh sách profile"""
        # Xóa hết widget cũ trong khung cuộn
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if os.path.exists(self.profiles_dir):
            folders = sorted([f for f in os.listdir(self.profiles_dir) if os.path.isdir(os.path.join(self.profiles_dir, f))])
            
            if not folders:
                ttk.Label(self.scrollable_frame, text="Chưa có profile nào. Hãy tạo mới hoặc Import!", foreground="#888").pack(pady=20, padx=20)
                return

            for folder_name in folders:
                self.create_profile_card(folder_name)

    def create_profile_card(self, profile_name):
        """Tạo giao diện thẻ cho 1 profile"""
        # Khung bao ngoài (Card)
        card = ttk.LabelFrame(self.scrollable_frame, padding=(10, 5))
        card.pack(fill="x", expand=True, padx=10, pady=5, anchor="n")

        # Cột 1: Tên Profile (In đậm, to)
        lbl_icon = ttk.Label(card, text="👤", font=("Segoe UI", 14))
        lbl_icon.pack(side="left", padx=(0, 10))

        lbl_name = ttk.Label(card, text=profile_name, font=("Segoe UI", 11, "bold"))
        lbl_name.pack(side="left", padx=5)

        # Cột 2: Các nút chức năng (Bên phải)
        
        # Nút Xóa (Màu đỏ - style custom nếu cần, ở đây dùng text icon cho gọn)
        btn_del = ttk.Button(card, text="🗑️ Xóa", command=lambda p=profile_name: self.delete_profile(p))
        btn_del.pack(side="right", padx=5)

        # Nút Setup (Quan trọng nhất)
        btn_setup = ttk.Button(
            card, 
            text="⚙️ Đăng nhập / Setup", 
            style="Accent.TButton", # Màu xanh nổi bật
            command=lambda p=profile_name: self.open_browser_setup(p)
        )
        btn_setup.pack(side="right", padx=5)
        
        # Label trạng thái nhỏ
        path = os.path.join(self.profiles_dir, profile_name)
        size_mb = self.get_size(path)
        ttk.Label(card, text=f"Size: {size_mb:.1f} MB", font=("Segoe UI", 8), foreground="#888").pack(side="right", padx=20)

    # --- LOGIC CHỨC NĂNG ---

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
        """Thay cho việc kéo thả, dùng hộp thoại chọn folder"""
        source_dir = filedialog.askdirectory(title="Chọn folder chứa dữ liệu Profile cũ")
        if not source_dir: return

        folder_name = os.path.basename(source_dir)
        # Nếu folder gốc tên là 'User Data' hoặc 'Default', hỏi người dùng đặt tên mới
        if folder_name.lower() in ['user data', 'default', 'profile']:
            # Tạo popup hỏi tên (đơn giản hóa bằng cách dùng timestamp hoặc input dialog)
            folder_name = f"Imported_{int(time.time())}"
        
        dest_path = os.path.join(self.profiles_dir, folder_name)

        if os.path.exists(dest_path):
            messagebox.showerror("Lỗi", f"Profile '{folder_name}' đã tồn tại! Vui lòng đổi tên folder gốc.")
            return

        # Copy folder
        try:
            # Tạo luồng copy để không đơ giao diện
            def copy_task():
                shutil.copytree(source_dir, dest_path)
                # Refresh UI từ luồng chính
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
        """Mở trình duyệt để người dùng đăng nhập thủ công"""
        profile_path = os.path.join(self.profiles_dir, profile_name)
        
        def run_browser():
            print(f"Opening Setup for {profile_name}...")
            # Gọi hàm init driver (chế độ không log lỗi ra UI)
            driver = init_driver_from_profile(profile_path, log_callback=print)
            
            if driver:
                try:
                    # Mở trang Gemini
                    driver.get("https://gemini.google.com")
                    
                    # Giữ trình duyệt mở cho đến khi người dùng tắt thủ công
                    # Kiểm tra mỗi 1s xem cửa sổ còn mở không
                    while True:
                        try:
                            # Nếu lấy title bị lỗi nghĩa là trình duyệt đã tắt
                            _ = driver.title 
                            time.sleep(1)
                        except:
                            break
                    print(f"Setup {profile_name} closed.")
                except Exception as e:
                    print(f"Browser Closed or Error: {e}")
                finally:
                    try: driver.quit()
                    except: pass
            else:
                print("Failed to open driver")

        # Chạy ở luồng riêng để không treo tool
        threading.Thread(target=run_browser, daemon=True).start()

    def get_size(self, start_path):
        """Tính dung lượng folder (MB)"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(start_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except: pass
        return total_size / (1024 * 1024)