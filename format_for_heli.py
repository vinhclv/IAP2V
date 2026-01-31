import os
import shutil

def standardize_dataset(input_root, output_folder):
    # Tạo thư mục đầu ra nếu chưa có
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    all_prompts = []
    output_prompt_file = os.path.join(output_folder, 'prompt.txt')

    # Duyệt qua các thư mục con (1, 2, 3...)
    # sorted để đảm bảo thứ tự từ 1-10
    subdirs = sorted([d for d in os.listdir(input_root) if os.path.isdir(os.path.join(input_root, d))])

    for subdir in subdirs:
        subdir_path = os.path.join(input_root, subdir)
        
        for file in os.listdir(subdir_path):
            file_path = os.path.join(subdir_path, file)
            
            # Xử lý file ảnh (hỗ trợ jpg, png, jpeg...)
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                # Copy ảnh sang thư mục mới
                # Nếu muốn đổi tên ảnh theo folder (ví dụ: 1.jpg, 2.jpg) để tránh trùng:
                new_image_name = f"{subdir}_{file}" 
                shutil.copy2(file_path, os.path.join(output_folder, new_image_name))
            
            # Xử lý file prompt.txt
            elif file == 'prompt.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Loại bỏ xuống dòng trong nội dung prompt cũ để đưa về 1 dòng
                    standardized_prompt = " ".join(content.splitlines())
                    if standardized_prompt:
                        all_prompts.append(standardized_prompt)

    # Ghi tất cả prompt vào file duy nhất
    with open(output_prompt_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(all_prompts))

    print(f"Hoàn thành! Kết quả tại: {output_folder}")

# --- Cấu hình đường dẫn của bạn ---
input_dir = r'\\192.168.1.17\data share\Dat\Data_processed\Positano, Capri - Italy\Capri'
output_dir = r'\\192.168.1.17\data share\Dat\Data_processed\Positano, Capri - Italy\Capri_for_heli'

standardize_dataset(input_dir, output_dir)