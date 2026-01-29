import os

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