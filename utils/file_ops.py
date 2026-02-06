import os
import re
import json

def get_image_status(img_dir, out_dir):
    """Quét trạng thái ảnh và prompt"""
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

def get_video_status(out_dir):
    """Quét trạng thái video"""
    if not os.path.exists(out_dir): return [], []
    
    subfolders = [f for f in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, f))]
    pending, completed = [], []
    
    for sub in subfolders:
        sub_path = os.path.join(out_dir, sub)
        prompt_path = os.path.join(sub_path, "prompt.txt")
        
        # Chỉ tính những folder ĐÃ CÓ prompt.txt
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

    
def get_srt_status(srt_path, output_dir):
    """
    Đọc file .srt và kiểm tra trạng thái dựa trên file JSON tổng nằm trong output_dir.
    File JSON tổng có tên giống file SRT.
    Ví dụ: input là 'movie.srt' -> output check 'output_dir/movie.json'
    """
    pending = []
    completed = []
    
    if not os.path.exists(srt_path):
        return [], []

    try:
        # 1. Đọc nội dung SRT
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex tách các đoạn sub
        pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)', re.DOTALL)
        matches = pattern.findall(content)

        # 2. Xác định file JSON Output
        srt_name = os.path.splitext(os.path.basename(srt_path))[0]
        json_output_path = os.path.join(output_dir, f"{srt_name}.json")

        # 3. Lấy danh sách các STT đã làm xong từ file JSON tổng (nếu có)
        completed_ids = set()
        if os.path.exists(json_output_path):
            try:
                with open(json_output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Giả sử cấu trúc: [{"STT": "1", "Prompt": "..."}, ...]
                    if isinstance(data, list):
                        for item in data:
                            if "STT" in item:
                                completed_ids.add(str(item["STT"]))
            except Exception as e:
                print(f"⚠️ Lỗi đọc file JSON output hiện tại: {e}")

        # 4. Phân loại Task
        for idx, time_range, text in matches:
            idx = str(idx).strip()
            text = text.strip().replace('\n', ' ')
            
            task_item = {
                "id": idx,           
                "text": text,
                "json_path": json_output_path, 
            }

            if idx in completed_ids:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi xử lý SRT: {e}")
        
    return pending, completed