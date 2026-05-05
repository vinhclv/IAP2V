import os
import re
import json

def get_image_prompt_status(img_dir, out_dir):
    """Quét trạng thái: Mỗi ảnh tương ứng với một file [tên_ảnh]_prompt.txt"""
    if not os.path.exists(img_dir): return [], []
    
    all_imgs = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    pending, completed = [], []
    
    for img in all_imgs:
        name_no_ext = os.path.splitext(img)[0]
        # CẬP NHẬT Ở ĐÂY: Đường dẫn file kiểu out_dir/tên_ảnh_prompt.txt
        prompt_file = os.path.join(out_dir, f"{name_no_ext}_prompt.txt")
        full_img_path = os.path.join(img_dir, img) 
        
        if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 0:
            completed.append(full_img_path)
        else:
            pending.append(full_img_path)
            
    return pending, completed

def get_prompt_video_status(json_path, out_dir):
    """
    Đọc file JSON đầu vào và kiểm tra trạng thái tiến độ tạo video.
    Quét trực tiếp trong thư mục out_dir để tìm file với định dạng: {Type}-{StartTime}.mp4
    Ví dụ: B-Roll-00-02-06-611.mp4
    """
    pending = []
    completed = []
    
    if not os.path.exists(json_path):
        print(f"⚠️ Không tìm thấy file JSON: {json_path}")
        return [], []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data:
            stt_str = str(item.get("STT", "")).strip()
            if not stt_str:
                continue
                
            task_item = item.copy()
            task_item["json_path"] = json_path
            # visual_details là tất cả các trường khác STT và Timecode
            task_item["visual_details"] = {k: v for k, v in item.items() if k not in ["STT", "Timecode"]}
            task_item["video_path"] = None
            task_item["Timecode"] = item.get("Timecode")

            # --- ĐOẠN XỬ LÝ TÊN FILE MỚI ---
            timecode = item.get("Timecode", "")
            v_type = item.get("Type", "Video") # Mặc định là 'Video' nếu không có trường Type
            
            # 1. Dọn dẹp trường Type (Xóa ngoặc vuông)
            # Ví dụ: "[B-Roll]" -> "B-Roll"
            clean_type = v_type.replace("[", "").replace("]", "").strip()
            if not clean_type:
                clean_type = "Video"
            
            # 2. Lấy thời gian bắt đầu và format lại
            # Ví dụ: "00:02:06,611 --> 00:02:11,739" -> "00:02:06,611" -> "00-02-06-611"
            start_time_str = "00-00-00-000" # Giá trị mặc định an toàn
            if timecode and "-->" in timecode:
                start_time_raw = timecode.split("-->")[0].strip()
                # Thay dấu hai chấm và dấu phẩy thành gạch ngang
                start_time_str = start_time_raw.replace(":", "-").replace(",", "-")
            elif timecode:
                # Fallback cho trường hợp timecode bị lỗi format thiếu '-->'
                start_time_str = timecode.replace(":", "-").replace(",", "-").strip()

            # 3. Ghép thành tên file đích
            expected_filename = f"{stt_str}_{clean_type}-{start_time_str}.mp4"
            expected_video_path = os.path.join(out_dir, expected_filename)
            task_item["video_path"] = expected_video_path

            is_done = False
            if os.path.exists(expected_video_path):
                is_done = True
            
            if is_done:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi xử lý JSON: {e}")
        
    return pending, completed

def get_srt_prompt_status(srt_path, output_dir):
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
                "STT": idx,           
                "text": text,
                "Timecode": time_range,
                "json_path": json_output_path, 
            }

            if idx in completed_ids:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi xử lý SRT: {e}")
        
    return pending, completed

def get_prompt_image_status(prompt_json_path, output_root_dir):
    """
    Đọc file input .json (chứa Prompt).
    Kiểm tra xem file ảnh tương ứng (STT.jpg) đã tồn tại trong thư mục output chưa.
    
    Ví dụ: 
    - Input: data/movie.json
    - Output folder: output_root_dir/movie/
    - Item STT=1 -> Check file: output_root_dir/movie/1.jpg
    """
    pending = []
    completed = []
    
    if not os.path.exists(prompt_json_path):
        return [], []

    try:
        # 1. Đọc nội dung JSON Input
        with open(prompt_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)


        # 3. Duyệt qua từng item
        for item in data:
            # Lấy STT và Prompt (ép kiểu str để an toàn)
            idx = str(item.get("STT", "")).strip()
            prompt_text = item.get("Prompt", "").strip() # Hoặc key là "text" tùy file json của bạn

            if not idx: continue # Bỏ qua nếu data lỗi không có STT

            # Đường dẫn file ảnh mong đợi
            # (Bạn có thể đổi thành .png nếu tool sinh ra png)
            image_filename = f"{idx}.jpg"
            image_path = os.path.join(output_root_dir, image_filename)

            # Tạo object task
            task_item = {
                "id": idx,
                "prompt": prompt_text,
                "save_path": image_path, # Đường dẫn lưu ảnh để Worker dùng
                "output_folder": output_root_dir,
                "type": "prompt_to_image"
            }

            # 4. Kiểm tra file ảnh có tồn tại và có dung lượng > 0
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi đọc JSON Prompt Image: {e}")
        
    return pending, completed

def get_2_image_prompt_status(img_dir, output_dir):
    """
    Quét folder ảnh, tạo cặp ảnh liên tiếp (1-2, 2-3...)
    Kiểm tra xem đã có file [id1]-[id2]_prompt.txt chưa (cấu trúc phẳng).
    """
    pending = []
    completed = []
    
    if not os.path.exists(img_dir):
        return [], []

    try:
        # 1. Lấy danh sách file ảnh và SẮP XẾP SỐ HỌC
        valid_exts = ['.jpg', '.jpeg', '.png', '.webp']
        files = [f for f in os.listdir(img_dir) if os.path.splitext(f)[1].lower() in valid_exts]
        
        # Sắp xếp để đảm bảo thứ tự 1, 2, 3... thay vì 1, 10, 2...
        try:
            files.sort(key=lambda f: int(os.path.splitext(f)[0]))
        except ValueError:
            files.sort()

        if len(files) < 2:
            return [], [] # Không đủ 2 ảnh để tạo cặp

        # 2. Duyệt qua danh sách để tạo cặp (Sliding Window)
        for i in range(len(files) - 1):
            img1_name = files[i]
            img2_name = files[i+1]
            
            id1 = os.path.splitext(img1_name)[0]
            id2 = os.path.splitext(img2_name)[0]
            
            pair_id = f"{id1}-{id2}" # Ví dụ: 1-2
            
            # ĐƯỜNG DẪN MỚI: out_dir / 1-2_prompt.txt
            prompt_file = os.path.join(output_dir, f"{pair_id}_prompt.txt")
            
            task_item = {
                "pair_id": pair_id,
                "img1_path": os.path.join(img_dir, img1_name),
                "img2_path": os.path.join(img_dir, img2_name),
                "output_dir": output_dir, # Thư mục gốc để lưu file phẳng
                "prompt_file": prompt_file,
            }

            # 3. Kiểm tra trạng thái file phẳng
            if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 10:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi quét cặp ảnh: {e}")

    return pending, completed

def get_srt_image_status(srt_path, output_dir):
    """
    Đọc file SRT và kiểm tra xem ảnh tương ứng đã được tạo chưa.
    Logic: Input (SRT) -> Output (Folder chứa ảnh 1.jpg, 2.jpg...)
    """
    pending = []
    completed = []

    if not os.path.exists(srt_path):
        return [], []

    try:
        # 1. Đọc nội dung SRT
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex tách các đoạn sub (Lấy ID và Text)
        # Group 1: ID
        # Group 2: Timestamp (bỏ qua)
        # Group 3: Text nội dung
        pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)', re.DOTALL)
        matches = pattern.findall(content)

        # 2. Xác định thư mục chứa ảnh đầu ra
        # Tên project lấy theo tên file SRT (ví dụ: movie.srt -> movie)

        # 3. Duyệt qua từng dòng sub để tạo Task
        for idx, _, text in matches:
            idx = str(idx).strip()
            
            # Làm sạch text để dùng làm Prompt
            # Xóa xuống dòng, xóa tag HTML nếu có
            clean_text = text.strip().replace('\n', ' ')
            clean_text = re.sub(r'<.*?>', '', clean_text) 

            # Đường dẫn file ảnh mong đợi (ví dụ: output/movie/1.jpg)
            image_filename = f"{idx}.jpg"
            image_path = os.path.join(output_dir, image_filename)

            # Tạo object task để Worker sử dụng ngay
            task_item = {
                "id": idx,
                "prompt": clean_text,         # Dùng trực tiếp text sub làm prompt
                "save_path": image_path,      # Đường dẫn file ảnh đích
                "output_folder": output_dir,  # Thư mục chứa ảnh (để Worker os.makedirs)
            }

            # 4. Kiểm tra trạng thái
            # File phải tồn tại và dung lượng > 0 mới tính là xong
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi xử lý file SRT: {e}")

    return pending, completed   

def get_srt_multilanguage_status(srt_path, output_dir, languages):
    pending, completed = [], []

    # Kiểm tra xem đây có phải là file hợp lệ không
    if not os.path.isfile(srt_path) or not srt_path.lower().endswith('.srt'):
        return [], []

    try:
        # Xử lý đường dẫn dài
        safe_srt_path = srt_path

        with open(safe_srt_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)', re.DOTALL)
        
        raw_blocks = [match.group(0) for match in pattern.finditer(original_content)]
        original_count = len(raw_blocks)

        if original_count == 0: return [], []

        base_name = os.path.splitext(os.path.basename(srt_path))[0]

        for lang in languages:
            out_filename = f"{base_name}_{lang}.srt"
            out_filepath = os.path.join(output_dir, out_filename)

            task_item = {
                "id": f"{base_name}_{lang}",
                "srt_path": srt_path,
                "lang": lang,
                "save_path": out_filepath,
                "original_count": original_count
            }

            is_done = False
            if os.path.exists(out_filepath) and os.path.getsize(out_filepath) > 0:
                with open(out_filepath, 'r', encoding='utf-8') as f_out:
                    out_content = f_out.read()
                out_count = len(pattern.findall(out_content))
                
                if out_count == original_count:
                    is_done = True

            if is_done: completed.append(task_item)
            else: pending.append(task_item)

    except Exception as e:
        print(f"Lỗi: {e}")

    return pending, completed

def get_srt_shuffle_status(srt_path, output_dir, shuffle_gems):
    """
    Kiểm tra trạng thái xáo trộn (Shuffle) cho từng dòng trong file SRT.
    Dựa trên file JSON tổng nằm trong output_dir.
    Ví dụ: input là 'movie.srt' -> output check 'output_dir/movie_shuffle.json'
    """
    pending = []
    completed = []

    if not os.path.exists(srt_path):
        return [], []

    try:
        # 1. Đọc nội dung SRT gốc
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex tách các đoạn sub
        pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)', re.DOTALL)
        matches = pattern.findall(content)

        # 2. Xác định file JSON Output
        srt_name = os.path.splitext(os.path.basename(srt_path))[0]
        json_output_path = os.path.join(output_dir, f"{srt_name}_shuffle.json")

        # 3. Lấy danh sách các STT đã làm xong từ file JSON tổng (nếu có)
        completed_ids = set()
        if os.path.exists(json_output_path):
            try:
                with open(json_output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Giả sử cấu trúc JSON lưu lại kết quả: 
                    # [{"STT": "1", "text": "...", "gem_used": "srt->prompt", "shuffled_result": "..."}, ...]
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
                "STT": idx,           
                "text": text,
                "time_range": time_range,
                "json_path": json_output_path,
                "shuffle_gems": shuffle_gems # Đưa danh sách gem vào để worker biết lấy ngẫu nhiên
            }

            if idx in completed_ids:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi xử lý SRT Shuffle: {e}")
        
    return pending, completed

def get_shuffle_image_status(json_path, output_dir):
    """
    Đọc file input .json (chứa Prompt).
    Kiểm tra xem file ảnh tương ứng (STT.jpg) đã tồn tại trong thư mục output chưa.
    """
    pending = []
    completed = []
    
    if not os.path.exists(json_path):
        return [], []

    try:
        # 1. Đọc nội dung JSON Input
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 2. Duyệt qua từng item
        for item in data:
            # Lấy STT và Prompt (ép kiểu str để an toàn)
            idx = str(item.get("STT", "")).strip()
            prompt_text = item.get("text", "").strip()

            if not idx: 
                continue # Bỏ qua nếu data lỗi không có STT

            # Đường dẫn file ảnh mong đợi (SỬA LỖI: dùng đúng output_dir)
            image_filename = f"{idx}.jpg"
            image_path = os.path.join(output_dir, image_filename)
            
            # --- SỬA LỖI LẤY THÔNG TIN GEM AN TOÀN ---
            gem_info = item.get("GEM", {}) # Lấy ra dict, nếu không có thì trả về dict rỗng {}
            gem_url = ""
            gem_name = ""
            
            # Đảm bảo gem_info thực sự là một dictionary trước khi gọi .get()
            if isinstance(gem_info, dict):
                gem_url = gem_info.get("url", "").strip()
                gem_name = gem_info.get("name", "").strip()

            # 3. Tạo object task
            task_item = {
                "id": idx,
                "prompt": prompt_text,
                "save_path": image_path, # Đường dẫn lưu ảnh để Worker dùng
                "output_folder": output_dir, # SỬA LỖI: dùng đúng output_dir
                "type": "shuffle_image", # SỬA LỖI: gõ đúng chính tả
                "gem_url": gem_url,
                "gem_name": gem_name
            }

            # 4. Kiểm tra file ảnh có tồn tại và có dung lượng > 0
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                completed.append(task_item)
            else:
                pending.append(task_item)

    except Exception as e:
        print(f"❌ Lỗi đọc JSON Prompt Image: {e}")
        
    return pending, completed

def get_2_image_prompt_video_status(prompt_dir, img_dir, out_dir):
    """
    Đọc folder prompt và folder ảnh, kiểm tra tiến độ tạo video.
    """
    pending = []
    completed = []
    
    if not os.path.exists(prompt_dir) or not os.path.exists(img_dir):
        return [], []
        
    try:
        prompt_files = [f for f in os.listdir(prompt_dir) if f.endswith("_prompt.txt")]
        
        for pf in prompt_files:
            stt = pf.replace("_prompt.txt", "") # e.g., "1-2"
            parts = stt.split("-")
            img1_id = parts[0]
            img2_id = parts[1] if len(parts) > 1 else None
            
            with open(os.path.join(prompt_dir, pf), 'r', encoding='utf-8') as f:
                prompt_text = f.read().strip()
                
            # Tìm ảnh tương ứng
            image_path = os.path.join(img_dir, f"{img1_id}.jpg")
            if not os.path.exists(image_path):
                image_path = os.path.join(img_dir, f"{img1_id}.png")
                
            image_end_path = ""
            if img2_id:
                image_end_path = os.path.join(img_dir, f"{img2_id}.jpg")
                if not os.path.exists(image_end_path):
                    image_end_path = os.path.join(img_dir, f"{img2_id}.png")
                
            expected_video_path = os.path.join(out_dir, f"{stt}.mp4")
            
            task_item = {
                "STT": stt,
                "visual_details": prompt_text,
                "image_path": image_path,
                "image_end_path": image_end_path,
                "video_path": expected_video_path
            }
            
            if os.path.exists(expected_video_path) and os.path.getsize(expected_video_path) > 0:
                completed.append(task_item)
            else:
                pending.append(task_item)
                
    except Exception as e:
        print(f"❌ Lỗi quét 2_image_prompt_video: {e}")
        
    return pending, completed