# utils/instructions.py

# ==========================================
# 📘 BẢNG HƯỚNG DẪN ĐẦU VÀO & ĐẦU RA CHO TỪNG TÍNH NĂNG
# ==========================================
MODE_HELP_DATA = {
    "Image ➡ Prompt": (
        "🌟 CHẾ ĐỘ: IMAGE ➡ PROMPT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Tải ảnh phân cảnh lên Gemini cùng sub để AI tự động phân tích và viết prompt chi tiết cho hình ảnh.\n\n"
        "📥 Đầu vào:\n"
        "• File SRT phụ đề kịch bản gốc.\n"
        "• Thư mục chứa các tệp ảnh kịch bản [STT].jpg hoặc [STT].png.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa tệp JSON kết quả ([Tên folder ảnh].json) chứa prompt chi tiết."
    ),
    "Prompt ➡ Video": (
        "🌟 CHẾ ĐỘ: PROMPT ➡ VIDEO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Sinh video tự động từ mô tả prompt dạng văn bản bằng công nghệ Google Labs VideoFX (Veo model).\n\n"
        "📥 Đầu vào:\n"
        "• File JSON chứa prompt kịch bản đã chuẩn bị.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa các video MP4 kết quả ({STT}_{Type}-{StartTime}.mp4)."
    ),
    "SRT ➡ Prompt": (
        "🌟 CHẾ ĐỘ: SRT ➡ PROMPT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Dựa trên file kịch bản phụ đề SRT, gửi từng câu sub lên Gemini nhờ AI viết ý tưởng/prompt mô tả hình ảnh cho cảnh đó.\n\n"
        "📥 Đầu vào:\n"
        "• File SRT phụ đề kịch bản gốc.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa file JSON kết quả ([Tên file SRT].json) chứa prompt gợi ý phân cảnh."
    ),
    "Prompt ➡ Image": (
        "🌟 CHẾ ĐỘ: PROMPT ➡ IMAGE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Gửi prompt mô tả từ file JSON lên Gemini để sinh ảnh AI chất lượng cao.\n\n"
        "📥 Đầu vào:\n"
        "• File JSON chứa danh sách các prompt hình ảnh.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa các ảnh .jpg được sinh ra đặt tên [STT].jpg."
    ),
    "2_Image ➡ Prompt": (
        "🌟 CHẾ ĐỘ: 2_IMAGE ➡ PROMPT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Phân tích cặp ảnh liên tiếp (e.g. 1 & 2) để viết prompt mô tả sự dịch chuyển/chuyển cảnh giữa hai khung hình.\n\n"
        "📥 Đầu vào:\n"
        "• Thư mục chứa các file ảnh gốc.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa các file phẳng [STT1-STT2]_prompt.txt tả chuyển động."
    ),
    "SRT ➡ Image": (
        "🌟 CHẾ ĐỘ: SRT ➡ IMAGE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Sinh ảnh trực tiếp từ nội dung văn bản phụ đề của kịch bản SRT bằng Gemini Image Generator.\n\n"
        "📥 Đầu vào:\n"
        "• File SRT kịch bản phụ đề gốc.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa các tệp ảnh .jpg tương ứng với từng câu phụ đề."
    ),
    "SRT ➡ Multilanguage": (
        "🌟 CHẾ ĐỘ: SRT ➡ MULTILANGUAGE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Dịch phụ đề SRT sang nhiều ngôn ngữ được chọn bằng Gemini, giữ nguyên cấu trúc timecode.\n\n"
        "📥 Đầu vào:\n"
        "• File SRT gốc.\n"
        "• Tích chọn các ngôn ngữ muốn dịch trên bảng điều khiển.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa các file SRT đã dịch: [Tên file gốc]_[Mã ngôn ngữ].srt."
    ),
    "SRT ➡ Shuffle": (
        "🌟 CHẾ ĐỘ: SRT ➡ SHUFFLE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Trộn kịch bản phụ đề SRT và gửi ngẫu nhiên qua các GEM khác nhau được chọn để đa dạng hóa ý tưởng.\n\n"
        "📥 Đầu vào:\n"
        "• File SRT kịch bản.\n"
        "• Tích chọn danh sách các GEM muốn trộn ở bảng điều khiển.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa tệp JSON tổng hợp kết quả shuffle."
    ),
    "Shuffle ➡ Image": (
        "🌟 CHẾ ĐỘ: SHUFFLE ➡ IMAGE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Tạo ảnh AI từ kịch bản JSON đã xáo trộn ở bước trước bằng các GEM tương ứng theo đúng cấu hình.\n\n"
        "📥 Đầu vào:\n"
        "• File JSON shuffle kịch bản ([Tên file SRT]_shuffle.json).\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa các ảnh .jpg sinh ra từ các GEM tương ứng."
    ),
    "2_Image + Prompt ➡ Video": (
        "🌟 CHẾ ĐỘ: 2_IMAGE + PROMPT ➡ VIDEO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Sinh video chuyển cảnh chất lượng cao (Image-to-Video) từ ảnh đầu (startImage), ảnh cuối (endImage) kết hợp prompt chuyển động qua Google Veo.\n\n"
        "📥 Đầu vào:\n"
        "• Thư mục chứa prompt chuyển cảnh ([STT1-STT2]_prompt.txt).\n"
        "• Thư mục chứa các ảnh gốc.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa video MP4 kết quả [STT1-STT2].mp4."
    ),
    "Image + Prompt ➡ Video": (
        "🌟 CHẾ ĐỘ: IMAGE + PROMPT ➡ VIDEO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 Mô tả: Sinh video chuyển động (Image-to-Video) từ một ảnh gốc (startImage) kết hợp prompt mô tả hành động qua Google Veo.\n\n"
        "📥 Đầu vào:\n"
        "• File JSON chứa prompt kịch bản sinh video.\n"
        "• Thư mục chứa các tệp ảnh gốc.\n\n"
        "📤 Đầu ra:\n"
        "• Thư mục chứa video MP4 [STT].mp4 sinh ra tương ứng."
    ),
}
