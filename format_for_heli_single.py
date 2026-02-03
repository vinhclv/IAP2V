import os
import shutil
import re # <--- [QUAN TRỌNG 1] Thêm thư viện xử lý biểu thức chính quy

def natural_sort_key(s):
    """
    Hàm hỗ trợ sắp xếp tự nhiên:
    Screenshot_2 sẽ đứng trước Screenshot_10
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def standardize_dataset_fixed(input_root, output_base_path):
    folder_name = os.path.basename(input_root)
    
    for_heli_dir = os.path.join(output_base_path, f"{folder_name}_for_heli")
    proccessed_dir = os.path.join(output_base_path, f"{folder_name}_proccessed")

    if not os.path.exists(for_heli_dir): os.makedirs(for_heli_dir)
    if not os.path.exists(proccessed_dir): os.makedirs(proccessed_dir)

    all_prompts = []
    output_prompt_file = os.path.join(for_heli_dir, 'prompt.txt')

    # Lấy danh sách folder thô
    raw_subdirs = [d for d in os.listdir(input_root) if os.path.isdir(os.path.join(input_root, d))]
    
    # [QUAN TRỌNG 2] Sắp xếp lại theo kiểu Natural Sort (giống Windows)
    subdirs = sorted(raw_subdirs, key=natural_sort_key)

    print(f"🔄 Đang xử lý {len(subdirs)} thư mục (Đã sort đúng thứ tự 1->2->10)...")

    for subdir in subdirs:
        subdir_path = os.path.join(input_root, subdir)
        
        # --- BƯỚC 1: LẤY NỘI DUNG PROMPT ---
        current_prompt_content = "" 
        prompt_path = os.path.join(subdir_path, 'prompt.txt')
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Chỉ lấy dòng đầu tiên hoặc join lại để tránh lỗi xuống dòng
                    current_prompt_content = " ".join(content.splitlines())
            except Exception as e:
                print(f"⚠️ Lỗi đọc prompt {subdir}: {e}")
        
        # --- BƯỚC 2: DUYỆT ẢNH ---
        files = sorted(os.listdir(subdir_path))
        images_in_folder = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

        for img_file in images_in_folder:
            # Copy ảnh
            src_img = os.path.join(subdir_path, img_file)
            new_image_name = f"{subdir}_{img_file}"
            dst_img = os.path.join(for_heli_dir, new_image_name)
            shutil.copy2(src_img, dst_img)
            
            # Ghi prompt tương ứng
            if current_prompt_content:
                all_prompts.append(current_prompt_content)
            else:
                all_prompts.append("<NO_PROMPT>")
                print(f"⚠️ Đã thêm <NO_PROMPT> cho folder: {subdir}")

    # Ghi file tổng
    with open(output_prompt_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(all_prompts))

    print(f"\n🚀 Hoàn thành!")
    print(f"- Output: {for_heli_dir}")

# --- Thực thi ---
input_dir = r'\\192.168.1.17\data share\Dat\Data_processed\Croatia\Rovinj'
output_base = r'\\192.168.1.17\data share\Dat\Heli_proccessed\Croatia'

standardize_dataset_fixed(input_dir, output_base)
