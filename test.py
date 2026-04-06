import subprocess
import os

def merge_video_audio(video_path, audio_path, output_path):
    """
    Ghép video MP4 và âm thanh MP3 thành một file MP4 mới.
    """
    
    # Kiểm tra xem file đầu vào có tồn tại không
    if not os.path.exists(video_path):
        print(f"Lỗi: Không tìm thấy file video '{video_path}'")
        return
    if not os.path.exists(audio_path):
        print(f"Lỗi: Không tìm thấy file audio '{audio_path}'")
        return

    # Xây dựng câu lệnh FFmpeg
    command = [
        'ffmpeg',
        '-i', video_path,       # File video đầu vào (Index 0)
        '-i', audio_path,       # File âm thanh đầu vào (Index 1)
        '-c:v', 'copy',         # Sao chép trực tiếp luồng video (không render lại, giúp chạy cực nhanh và giữ nguyên chất lượng)
        '-c:a', 'aac',          # Chuyển đổi định dạng âm thanh sang AAC (chuẩn tốt nhất cho file MP4)
        '-map', '0:v:0',        # Chỉ lấy hình ảnh từ file đầu vào thứ nhất (bỏ âm thanh cũ của video nếu có)
        '-map', '1:a:0',        # Chỉ lấy âm thanh từ file đầu vào thứ hai
        '-shortest',            # Độ dài video xuất ra sẽ bằng với độ dài của file ngắn hơn (video hoặc audio)
        '-y',                   # Tự động ghi đè nếu file đầu ra đã tồn tại
        output_path
    ]

    try:
        print("Đang tiến hành ghép video và audio...")
        # Thực thi lệnh FFmpeg
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"✅ Hoàn tất! File đầu ra được lưu tại: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi trong quá trình FFmpeg xử lý: {e}")
    except FileNotFoundError:
        print("❌ Lỗi: Không tìm thấy FFmpeg trên hệ thống. Bạn đã cài đặt và cấu hình biến môi trường cho FFmpeg chưa?")

# ==========================================
# CÁCH SỬ DỤNG
# ==========================================
if __name__ == "__main__":
    # Thay đổi đường dẫn tới file thực tế của bạn
    file_mp4_goc = r"\\Synology-new\data share\Dat\selfhelp\sf_1\Image_Final.mp4"
    file_mp3_goc = r"\\Synology-new\data share\Dat\selfhelp\test.mp3"
    file_dau_ra = r"\\Synology-new\data share\Dat\selfhelp\sf_1\video_da_ghep.mp4"
    merge_video_audio(file_mp4_goc, file_mp3_goc, file_dau_ra)