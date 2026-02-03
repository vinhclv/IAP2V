import os
import shutil
import re

# --- 1. HÀM SẮP XẾP TỰ NHIÊN (Giữ nguyên từ bài trước) ---
def natural_sort_key(s):
    """Sắp xếp Screenshot_2 trước Screenshot_10"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

# --- 2. HÀM KIỂM TRA: ĐÂY CÓ PHẢI FOLDER CẦN XỬ LÝ KHÔNG? ---
def is_data_container(folder_path):
    """
    Kiểm tra xem folder này có chứa các sub-folder dữ liệu không.
    Ví dụ: 'Whistler' là True vì nó chứa 'Screenshot_1' (có ảnh).
    'Canada' là False vì nó chứa 'Whistler' (folder lồng folder).
    """
    try:
        # Lấy danh sách các folder con
        subdirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
        if not subdirs:
            return False

        # Kiểm tra thử folder con đầu tiên xem nó chứa gì
        first_subdir = os.path.join(folder_path, subdirs[0])
        files_inside = os.listdir(first_subdir)
        
        # Nếu bên trong folder con có ảnh hoặc file text -> Đây là nơi cần xử lý
        has_image_or_prompt = any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.txt')) for f in files_inside)
        return has_image_or_prompt
    except:
        return False

# --- 3. HÀM XỬ LÝ CORE (Tách 2 folder và gộp prompt) ---
def process_final_dataset(input_dataset_path, output_parent_path):
    folder_name = os.path.basename(input_dataset_path)
    
    # Tạo đường dẫn đích
    for_heli_dir = os.path.join(output_parent_path, f"{folder_name}_for_heli")
    proccessed_dir = os.path.join(output_parent_path, f"{folder_name}_proccessed")

    # 1. Tạo 2 folder đích
    if not os.path.exists(for_heli_dir): os.makedirs(for_heli_dir)
    if not os.path.exists(proccessed_dir): os.makedirs(proccessed_dir)

    print(f"   ⚙️ Đang xử lý: {folder_name} -> {for_heli_dir}")

    all_prompts = []
    output_prompt_file = os.path.join(for_heli_dir, 'prompt.txt')

    # Lấy danh sách folder con (Screenshot_1, Screenshot_2...) và sort
    raw_subdirs = [d for d in os.listdir(input_dataset_path) if os.path.isdir(os.path.join(input_dataset_path, d))]
    subdirs = sorted(raw_subdirs, key=natural_sort_key)

    for subdir in subdirs:
        subdir_path = os.path.join(input_dataset_path, subdir)
        
        # --- LẤY PROMPT ---
        current_prompt_content = "" 
        prompt_path = os.path.join(subdir_path, 'prompt.txt')
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    current_prompt_content = " ".join(content.splitlines())
            except: pass
        
        # --- COPY ẢNH ---
        files = sorted(os.listdir(subdir_path))
        images_in_folder = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

        for img_file in images_in_folder:
            # Copy
            src_img = os.path.join(subdir_path, img_file)
            new_image_name = f"{subdir}_{img_file}"
            dst_img = os.path.join(for_heli_dir, new_image_name)
            shutil.copy2(src_img, dst_img)
            
            # Ghi Prompt
            if current_prompt_content:
                all_prompts.append(current_prompt_content)
            else:
                all_prompts.append("<NO_PROMPT>")

    # Ghi file tổng
    if all_prompts:
        with open(output_prompt_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(all_prompts))

# --- 4. HÀM DUYỆT CÂY CHÍNH ---
def recursive_structure_mirror(input_root, output_base):
    print(f"🚀 Bắt đầu quét từ: {input_root}")
    
    # Duyệt cây thư mục (topdown=True để kiểm tra cha trước con)
    for root, dirs, files in os.walk(input_root, topdown=True):
        
        # Tính toán đường dẫn tương đối để tạo cấu trúc cây bên đích
        # Ví dụ: root = ...\Data_processed\Canada -> rel_path = Canada
        rel_path = os.path.relpath(root, input_root)
        
        # Nếu đang ở root chính (.) thì rel_path là ., ta bỏ qua tạo folder .
        if rel_path == ".":
            dest_folder_current = output_base
        else:
            dest_folder_current = os.path.join(output_base, rel_path)

        # KIỂM TRA: Folder hiện tại (root) có phải là Dataset cần tách không?
        if is_data_container(root):
            # === ĐÂY LÀ FOLDER ĐÍCH (Vd: Whistler) ===
            # Ta cần lấy folder cha của đích để tạo cặp folder con bên trong
            # Vd: output_base\Canada
            parent_dest = os.path.dirname(dest_folder_current)
            
            # Gọi hàm xử lý tạo _for_heli và _proccessed
            process_final_dataset(root, parent_dest)
            
            # [QUAN TRỌNG] Xóa danh sách dirs để không duyệt sâu vào trong (Screenshot_1...) nữa
            dirs[:] = [] 
            
        else:
            # === ĐÂY LÀ FOLDER CẤU TRÚC (Vd: Canada, Croatia) ===
            # Chỉ tạo folder tương ứng bên đích nếu chưa có
            if not os.path.exists(dest_folder_current):
                os.makedirs(dest_folder_current)
                # print(f"📁 Tạo cấu trúc: {rel_path}")

    print("\n✅ HOÀN TẤT TOÀN BỘ QUÁ TRÌNH!")

# --- CẤU HÌNH ---
# Folder gốc chứa toàn bộ dữ liệu (Data_processed)
input_dir_root = r'\\192.168.1.17\data share\Dat\Data_processed'

# Folder gốc đầu ra (Heli_proccessed)
output_dir_root = r'\\192.168.1.17\data share\Dat\Heli_proccessed_02'

# Chạy
recursive_structure_mirror(input_dir_root, output_dir_root)