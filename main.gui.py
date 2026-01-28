import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import time
import shutil
import threading
import concurrent.futures
from datetime import datetime
import sv_ttk

# --- IMPORT LOGIC ---
from browser_setup import init_driver_from_profile
from image_to_prompt import process_image_to_prompt
from image_and_prompt_to_video import generate_video_for_file

# [MỚI] Import Tab quản lý profile
from profile_manager import ProfileManagerTab 

# --- CẤU HÌNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.join(BASE_DIR, "profiles")
DEFAULT_INPUT = os.path.join(BASE_DIR, "regen")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "assets")

class BatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Batch Auto Tool Pro")
        self.root.geometry("1100x800")
        
        # Kích hoạt theme
        try:
            sv_ttk.set_theme("dark")
        except: pass

        self.is_running = False
        self.stop_event = threading.Event()

        self._setup_ui()
        
        # Tự động load thống kê lần đầu
        self.root.after(1000, self.refresh_dashboard)

    def _setup_ui(self):
        # === TẠO HỆ THỐNG TAB (NOTEBOOK) ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # -- TAB 1: CHẠY AUTO (Giao diện cũ) --
        self.tab_run = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_run, text="🏃 Chạy Auto")

        # -- TAB 2: QUẢN LÝ PROFILES (Giao diện mới từ file khác) --
        self.tab_profiles = ProfileManagerTab(self.notebook, DEFAULT_PROFILES)
        self.notebook.add(self.tab_profiles, text="👥 Quản lý Profiles")

        # === SETUP GIAO DIỆN CHO TAB 1 (Copy logic cũ vào đây, đổi self.root -> self.tab_run) ===
        
        # 1. HEADER & CẤU HÌNH PATH
        frame_top = ttk.Frame(self.tab_run, padding=10)
        frame_top.pack(fill="x")

        frame_path = ttk.LabelFrame(frame_top, text="📂 Cấu hình Thư mục", padding=(15, 10))
        frame_path.pack(fill="x", expand=True)

        # Input
        ttk.Label(frame_path, text="Input Images (Ảnh gốc):").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_input = ttk.Entry(frame_path)
        self.entry_input.insert(0, DEFAULT_INPUT)
        self.entry_input.grid(row=0, column=1, sticky="ew", padx=10, ipady=3)

        # Output
        ttk.Label(frame_path, text="Output Assets (Kết quả):").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_output = ttk.Entry(frame_path)
        self.entry_output.insert(0, DEFAULT_OUTPUT)
        self.entry_output.grid(row=1, column=1, sticky="ew", padx=10, ipady=3)

        # Nút Refresh
        btn_refresh = ttk.Button(frame_path, text="🔄 Cập nhật Số liệu", command=self.refresh_dashboard)
        btn_refresh.grid(row=0, column=2, rowspan=2, padx=5, sticky="ns")

        frame_path.columnconfigure(1, weight=1)

        # 2. DASHBOARD
        frame_stats = ttk.LabelFrame(self.tab_run, text="📊 Thống kê Trạng thái", padding=15)
        frame_stats.pack(fill="x", padx=10, pady=5)

        frame_stats.columnconfigure(0, weight=1)
        frame_stats.columnconfigure(1, weight=2)
        frame_stats.columnconfigure(2, weight=2)

        # Profile Stats
        f1 = ttk.Frame(frame_stats)
        f1.grid(row=0, column=0, padx=10)
        ttk.Label(f1, text="Profiles", font=("Segoe UI", 11)).pack()
        self.lbl_profile = ttk.Label(f1, text="0", font=("Segoe UI", 28, "bold"), foreground="#4cc2ff")
        self.lbl_profile.pack()

        # Text Task Stats
        f2 = ttk.Frame(frame_stats)
        f2.grid(row=0, column=1, padx=10)
        ttk.Label(f2, text="Nhiệm vụ: Tạo Prompt", font=("Segoe UI", 11)).pack()
        f2_sub = ttk.Frame(f2)
        f2_sub.pack(pady=5)
        
        self.lbl_txt_pending = ttk.Label(f2_sub, text="0", font=("Segoe UI", 28, "bold"), foreground="#ffaa00")
        self.lbl_txt_pending.grid(row=0, column=1, padx=20)
        ttk.Label(f2_sub, text="Cần làm").grid(row=1, column=1)

        self.lbl_txt_total = ttk.Label(f2_sub, text="0", font=("Segoe UI", 14), foreground="#888")
        self.lbl_txt_total.grid(row=0, column=0, padx=10)
        ttk.Label(f2_sub, text="Tổng ảnh").grid(row=1, column=0)

        self.lbl_txt_done = ttk.Label(f2_sub, text="0", font=("Segoe UI", 14), foreground="#00cc6a")
        self.lbl_txt_done.grid(row=0, column=2, padx=10)
        ttk.Label(f2_sub, text="Đã xong").grid(row=1, column=2)

        # Video Task Stats
        f3 = ttk.Frame(frame_stats)
        f3.grid(row=0, column=2, padx=10)
        ttk.Label(f3, text="Nhiệm vụ: Tạo Video", font=("Segoe UI", 11)).pack()
        f3_sub = ttk.Frame(f3)
        f3_sub.pack(pady=5)

        self.lbl_vid_pending = ttk.Label(f3_sub, text="0", font=("Segoe UI", 28, "bold"), foreground="#ff5555")
        self.lbl_vid_pending.grid(row=0, column=1, padx=20)
        ttk.Label(f3_sub, text="Cần làm").grid(row=1, column=1)

        self.lbl_vid_total = ttk.Label(f3_sub, text="0", font=("Segoe UI", 14), foreground="#888")
        self.lbl_vid_total.grid(row=0, column=0, padx=10)
        ttk.Label(f3_sub, text="Tổng").grid(row=1, column=0)

        self.lbl_vid_done = ttk.Label(f3_sub, text="0", font=("Segoe UI", 14), foreground="#00cc6a")
        self.lbl_vid_done.grid(row=0, column=2, padx=10)
        ttk.Label(f3_sub, text="Đã xong").grid(row=1, column=2)

        # 3. ĐIỀU KHIỂN
        frame_ctrl = ttk.Frame(self.tab_run, padding=10)
        frame_ctrl.pack(fill="x")

        lbl_limit = ttk.Label(frame_ctrl, text="Số lượng xử lý / 1 Profile:")
        lbl_limit.pack(side="left")
        self.spin_limit = ttk.Spinbox(frame_ctrl, from_=1, to=50, width=5)
        self.spin_limit.set(5)
        self.spin_limit.pack(side="left", padx=5)

        self.btn_text = ttk.Button(frame_ctrl, text="🚀 CHẠY: Image ➡ Prompt", style="Accent.TButton", command=lambda: self.start_thread("text"))
        self.btn_text.pack(side="left", padx=20)

        self.btn_video = ttk.Button(frame_ctrl, text="🎥 CHẠY: Prompt ➡ Video", style="Accent.TButton", command=lambda: self.start_thread("video"))
        self.btn_video.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(frame_ctrl, text="🛑 DỪNG KHẨN CẤP", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="right")

        # 4. LOGS
        frame_log = ttk.LabelFrame(self.tab_run, text="📜 Nhật ký hoạt động", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_area = scrolledtext.ScrolledText(frame_log, height=10, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        self.log_area.tag_config("INFO", foreground="#cccccc")
        self.log_area.tag_config("SUCCESS", foreground="#6cc644")
        self.log_area.tag_config("ERROR", foreground="#ff5555")
        self.log_area.tag_config("WARNING", foreground="#ffb86c")

        # SỰ KIỆN CHUYỂN TAB: Khi quay lại tab 1 sẽ tự refresh số liệu
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        # Nếu người dùng chuyển sang Tab 0 (Chạy Auto), thì cập nhật lại số profile
        # vì có thể họ vừa thêm/xóa ở Tab 2
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0:
            self.refresh_dashboard()

    # ================= LOGIC DASHBOARD (GIỮ NGUYÊN) =================
    def refresh_dashboard(self):
        threading.Thread(target=self._calculate_stats, daemon=True).start()

    def _calculate_stats(self):
        try:
            inp = self.entry_input.get()
            out = self.entry_output.get()

            # Đếm Profiles
            if os.path.exists(DEFAULT_PROFILES):
                profiles = [f for f in os.listdir(DEFAULT_PROFILES) if os.path.isdir(os.path.join(DEFAULT_PROFILES, f))]
                n_prof = len(profiles)
            else:
                n_prof = 0

            pend_txt, comp_txt = self.get_image_status(inp, out)
            pend_vid, comp_vid = self.get_video_status(out)

            self.root.after(0, lambda: self._update_labels(
                n_prof, 
                len(pend_txt), len(comp_txt), 
                len(pend_vid), len(comp_vid)
            ))
        except Exception as e:
            pass

    def _update_labels(self, n_prof, n_pend_txt, n_comp_txt, n_pend_vid, n_comp_vid):
        self.lbl_profile.config(text=f"{n_prof}")
        self.lbl_txt_total.config(text=f"{n_pend_txt + n_comp_txt}")
        self.lbl_txt_pending.config(text=f"{n_pend_txt}")
        self.lbl_txt_done.config(text=f"{n_comp_txt}")
        self.lbl_vid_total.config(text=f"{n_pend_vid + n_comp_vid}")
        self.lbl_vid_pending.config(text=f"{n_pend_vid}")
        self.lbl_vid_done.config(text=f"{n_comp_vid}")

    # ================= LOGIC CHECK TRẠNG THÁI (GIỮ NGUYÊN) =================
    def get_image_status(self, img_dir, out_dir):
        if not os.path.exists(img_dir): return [], []
        all_imgs = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        pending, completed = [], []
        for img in all_imgs:
            name_no_ext = os.path.splitext(img)[0]
            prompt_file = os.path.join(out_dir, name_no_ext, "prompt.txt")
            full_img_path = os.path.join(img_dir, img) 
            if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 0:
                completed.append(full_img_path)
            else:
                pending.append(full_img_path)
        return pending, completed

    def get_video_status(self, out_dir):
        if not os.path.exists(out_dir): return [], []
        subfolders = [f for f in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, f))]
        pending, completed = [], []
        for sub in subfolders:
            sub_path = os.path.join(out_dir, sub)
            prompt_path = os.path.join(sub_path, "prompt.txt")
            if os.path.exists(prompt_path):
                imgs = [f for f in os.listdir(sub_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                if not imgs: continue
                img_full_path = os.path.join(sub_path, imgs[0])
                video_dir = os.path.join(sub_path, "video")
                is_done = False
                if os.path.exists(video_dir):
                    if any(f.endswith('_8s.mp4') for f in os.listdir(video_dir)): is_done = True
                if is_done: completed.append(img_full_path)
                else: pending.append(img_full_path)
        return pending, completed

    # ================= LOGGING & WORKER (GIỮ NGUYÊN) =================
    def log(self, message, tag="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}\n"
        def _update():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, full_msg, tag)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _update)

    def worker_task(self, profile_folder, file_batch, loop_type, assets_path):
        p_path = os.path.join(DEFAULT_PROFILES, profile_folder)
        def init_log(msg): pass 
        driver = init_driver_from_profile(p_path, log_callback=init_log)
        if not driver: return [f"ERROR: {profile_folder} Init Failed"]

        logs = []
        try:
            url = "https://gemini.google.com/gem/1bZsElT5GFF4JVXyoXoJ5qcHliqW2vUbR?usp=sharing/" if loop_type == "text" else "https://labs.google/fx/tools/video-fx"
            driver.get(url)
            time.sleep(5)

            for item_path in file_batch:
                if self.stop_event.is_set(): break
                file_name = os.path.basename(item_path)
                success = False
                try:
                    if loop_type == "text":
                        sub_name = os.path.splitext(file_name)[0]
                        dest_folder = os.path.join(assets_path, sub_name)
                        os.makedirs(dest_folder, exist_ok=True)
                        dest_img = os.path.join(dest_folder, file_name)
                        if not os.path.exists(dest_img): shutil.copy2(item_path, dest_img)
                        success = process_image_to_prompt(driver, dest_img, dest_folder)
                    else:
                        parent_folder = os.path.dirname(item_path)
                        prompt_path = os.path.join(parent_folder, "prompt.txt")
                        video_out_dir = os.path.join(parent_folder, "video")
                        if not os.path.exists(video_out_dir): os.makedirs(video_out_dir)
                        if os.path.exists(prompt_path):
                            with open(prompt_path, "r", encoding="utf-8") as f: txt = f.read().strip()
                            generate_video_for_file(driver, item_path, txt, video_out_dir)
                            success = True
                        else:
                            logs.append(f"WARNING: {profile_folder} | {file_name} thiếu prompt")
                            continue
                except Exception as e:
                    logs.append(f"ERROR: {profile_folder} | {file_name} Err: {e}")
                    continue

                status = "SUCCESS" if success else "ERROR"
                logs.append(f"{status}: {profile_folder} | {file_name}")

        except Exception as e:
            logs.append(f"ERROR: {profile_folder} Crash: {e}")
        finally:
            try: driver.quit()
            except: pass
        return logs

    def run_process(self, loop_type):
        input_dir = self.entry_input.get()
        output_dir = self.entry_output.get()
        limit = int(self.spin_limit.get())

        if not os.path.exists(DEFAULT_PROFILES):
            self.log("Thiếu folder profiles", "ERROR")
            self._reset_ui()
            return
        
        profile_folders = sorted([f for f in os.listdir(DEFAULT_PROFILES) if os.path.isdir(os.path.join(DEFAULT_PROFILES, f))])
        if not profile_folders:
            self.log("Không có profile nào!", "ERROR")
            self._reset_ui()
            return

        iteration = 1
        self.log(f"🚀 Bắt đầu chạy chế độ: {loop_type.upper()}", "INFO")

        while not self.stop_event.is_set():
            if loop_type == "text":
                pending, _ = self.get_image_status(input_dir, output_dir)
            else:
                pending, _ = self.get_video_status(output_dir)

            self.root.after(0, self.refresh_dashboard)

            if not pending:
                self.log("🎉 ĐÃ HOÀN THÀNH TẤT CẢ!", "SUCCESS")
                messagebox.showinfo("Thành công", "Đã xử lý hết tất cả các file!")
                break

            num_profiles = len(profile_folders)
            batches = [pending[i:i + limit] for i in range(0, len(pending), limit)]
            current_batches = batches[:num_profiles]
            active_count = len(current_batches)

            self.log(f"🔄 Vòng {iteration}: Còn {len(pending)} files. Chạy {active_count} profiles...", "INFO")

            with concurrent.futures.ThreadPoolExecutor(max_workers=active_count) as executor:
                futures = []
                for i in range(active_count):
                    if self.stop_event.is_set(): break
                    p_name = profile_folders[i]
                    batch = current_batches[i]
                    time.sleep(2)
                    self.log(f"▶️ Kích hoạt {p_name}...", "INFO")
                    future = executor.submit(self.worker_task, p_name, batch, loop_type, output_dir)
                    futures.append(future)

                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set(): break
                    try:
                        logs = future.result()
                        for line in logs:
                            tag = "INFO"
                            if "SUCCESS" in line: tag = "SUCCESS"
                            elif "ERROR" in line: tag = "ERROR"
                            elif "WARNING" in line: tag = "WARNING"
                            self.log(line, tag)
                    except Exception as e:
                        self.log(f"Thread Error: {e}", "ERROR")

            if self.stop_event.is_set():
                self.log("🛑 Đã dừng theo yêu cầu người dùng.", "WARNING")
                break

            self.log(f"⏳ Hết vòng {iteration}. Nghỉ 5s...", "WARNING")
            time.sleep(5)
            iteration += 1

        self._reset_ui()
        self.root.after(0, self.refresh_dashboard)

    def start_thread(self, loop_type):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.btn_text.config(state="disabled")
        self.btn_video.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.spin_limit.config(state="disabled")
        threading.Thread(target=self.run_process, args=(loop_type,), daemon=True).start()

    def stop_process(self):
        if self.is_running:
            self.log("🛑 Đang gửi lệnh dừng...", "WARNING")
            self.stop_event.set()

    def _reset_ui(self):
        self.is_running = False
        self.stop_event.clear()
        self.root.after(0, lambda: self.btn_text.config(state="normal"))
        self.root.after(0, lambda: self.btn_video.config(state="normal"))
        self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
        self.root.after(0, lambda: self.spin_limit.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchApp(root)
    root.mainloop()