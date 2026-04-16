import os
import time
import random
import json
from playwright.sync_api import Page, Locator
import config # Giả sử bạn vẫn dùng file config.py để lưu setting
import re
async def human_type(locator: Locator, text: str, page: Page):
    
    await locator.click()
    await page.wait_for_timeout(random.uniform(200, 400))

    idx = 0
    while idx < len(text):
        chunk_size = random.randint(15, 30)
        chunk = text[idx:idx+chunk_size]
        
        # 3. Ép tốc độ gõ phím siêu tốc: 5-10ms cho mỗi ký tự
        await locator.press_sequentially(chunk, delay=random.randint(5, 10))
        idx += chunk_size
        
        # 4. Thời gian nghỉ giữa các cụm cực ngắn (20-50ms)
        await page.wait_for_timeout(random.uniform(20, 50))
        
        # 5. Giảm tỷ lệ "suy nghĩ" xuống còn 5% và thời gian khựng cũng ngắn lại
        if random.random() < 0.05:
            await page.wait_for_timeout(random.uniform(100, 200))

    # 6. Giảm thời gian chờ chốt hạ
    await page.wait_for_timeout(random.uniform(200, 400))

async def setup_video_creation_mode(page: Page):
    print("⚙️ Đang cấu hình giao diện (Mode -> Landscape -> Qty=1 -> Quality Model)...")

    try:
        # 1. Tạo dự án
        create_btn = page.locator("i:has-text('add_2')").first
        if await create_btn.is_visible(timeout=45000):
            await create_btn.click(timeout=5000)
            await page.wait_for_timeout(1000)
        
        print("Đang chọn chế độ video...")
        dropdown_btn = page.locator("button[type='button'][aria-haspopup='menu']", has_text=re.compile(r"Banana|Video", re.IGNORECASE)).first
        
        # Chờ nút xuất hiện và sẵn sàng click
        await dropdown_btn.wait_for(state="visible", timeout=45000)
        
        # Dùng click của Playwright (isTrusted = true). 
        # Thêm delay để giả lập người bấm. Thêm force=True để ép click nếu web có thẻ div ẩn đè lên.
        await dropdown_btn.click(delay=random.randint(50, 150), force=True)
        await page.wait_for_timeout(1000) # Nghỉ 1s chờ menu xổ ra mượt mà

        await page.locator("i:has-text('videocam')").last.click(timeout=5000)
        await page.wait_for_timeout(500)
        print("Đang chọn chế độ thành phần...")

        # 3. Chế độ Thành phần
        await page.locator("i:has-text('chrome_extension')").first.click(timeout=5000)
        await page.wait_for_timeout(500)
        print("Đang chọn khung hình...")

        # 4. Khung hình
        await page.locator("i:has-text('crop_16_9')").last.click(timeout=5000)
        await page.wait_for_timeout(500)
        print("Đang chọn model...")

        # 5. Chọn Model
        await page.locator("i:has-text('arrow_drop_down')").first.click(timeout=5000)
        await page.wait_for_timeout(500)
        await page.locator("i:has-text('volume_up')").nth(1).click(timeout=5000)
        await page.wait_for_timeout(500)
        print("Đang chọn số lượng = 1...")

        # 6. Số lượng = 1
        await page.locator("button.flow_tab_slider_trigger", has_text="x1").first.click(timeout=5000)
        await page.wait_for_timeout(500)
        print("Đang đóng bảng...")

        # 7. Đóng bảng
        await page.locator("i:has-text('crop_16_9')").first.click(timeout=5000)
        await page.wait_for_timeout(500)
        print("✅ Đã cấu hình xong!")

    except Exception as e:
        print(f"⚠️ Dừng ngay tại lỗi: {e}")

# --- HÀM MỚI: TIÊM JS RADAR VÀO TRANG WEB ---
async def inject_radar_js(page: Page):
    """Tiêm đoạn JS săn lùng vào thẳng trình duyệt để nó chạy ngầm"""
    
    # THÊM CHỮ 'r' VÀO TRƯỚC DẤU NGOẶC KÉP
    js_interceptor = r"""
    (function() {
        window._python_results = window._python_results || {};
        window._mediaIdToSTT = window._mediaIdToSTT || {};
        window._completedSTTs = window._completedSTTs || new Set(); 
        window._isInterceptorInjected = window._isInterceptorInjected || false;

        if (window._isInterceptorInjected) return;
        window._isInterceptorInjected = true;
        console.log("%c[HỆ THỐNG] 🚀 ĐÃ BƠM RADAR BẮT SỐNG (ZERO LATENCY)...", "color: #ff00ff; font-size: 16px; font-weight: bold;");

        // 1. CƯỚP CÒ XHR: Bắt link ngay lúc trình duyệt vừa tạo request
        const origOpen = XMLHttpRequest.prototype.open;
        const origSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._intercept_url = typeof url === 'string' ? url : url.toString();
            
            // Soi ngay xem có phải link tải video không
            let checkUrl = this._intercept_url;
            if (!checkUrl.toLowerCase().includes("thumbnail") && 
                (checkUrl.includes("GoogleAccessId") || checkUrl.includes("media.getMediaUrlRedirect") || checkUrl.includes("storage.googleapis.com"))) {
                for (let [mediaId, stt] of Object.entries(window._mediaIdToSTT)) {
                    if (checkUrl.includes(mediaId) && !window._completedSTTs.has(stt)) {
                        window._completedSTTs.add(stt);
                        window._python_results[stt] = checkUrl;
                    }
                }
            }
            origOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function() {
            this.addEventListener('load', function() {
                if (this._intercept_url.includes("batchCheckAsyncVideoGenerationStatus") || 
                    this._intercept_url.includes("batchAsyncGenerateVideoText")) {
                    try {
                        let text = this.responseText.replace(/^\)\]\}'\n/, '');
                        let data = JSON.parse(text);
                        let mediaArr = data.media || (data.result && data.result.media) || [];
                        
                        mediaArr.forEach(item => {
                            let mediaId = item?.name;
                            let rawPrompt = item?.mediaMetadata?.requestData?.promptInputs?.[0]?.structuredPrompt?.parts?.[0]?.text || "";
                            let genPrompt = item?.video?.generatedVideo?.prompt || "";
                            let titlePrompt = item?.mediaMetadata?.mediaTitle || "";
                            let match = (`${rawPrompt} | ${genPrompt} | ${titlePrompt}`).match(/\|\|(.*?)\|\|/);

                            if (match && mediaId && !window._mediaIdToSTT[mediaId]) {
                                window._mediaIdToSTT[mediaId] = match[1].trim();
                            }
                        });
                    } catch(e) {}
                }
            });
            origSend.apply(this, arguments);
        };

        // 2. CƯỚP CÒ FETCH: Bắt link ở cửa Fetch
        const origFetch = window.fetch;
        window.fetch = async function(...args) {
            const url = args[0]?.url || args[0] || "";
            
            // Soi link Fetch trước khi nó bay đi
            if (typeof url === 'string' && !url.toLowerCase().includes("thumbnail") && 
               (url.includes("GoogleAccessId") || url.includes("media.getMediaUrlRedirect") || url.includes("storage.googleapis.com"))) {
                for (let [mediaId, stt] of Object.entries(window._mediaIdToSTT)) {
                    if (url.includes(mediaId) && !window._completedSTTs.has(stt)) {
                        window._completedSTTs.add(stt);
                        window._python_results[stt] = url;
                    }
                }
            }

            const response = await origFetch.apply(this, args);
            // Soi JSON trạng thái
            if (typeof url === 'string' && url.includes("batchCheckAsyncVideoGenerationStatus")) {
                const clone = response.clone();
                clone.text().then(text => {
                    try {
                        let cleaned = text.replace(/^\)\]\}'\n/, '');
                        let data = JSON.parse(cleaned);
                        let mediaArr = data.media || [];
                        mediaArr.forEach(item => {
                            let mediaId = item?.name;
                            let raw = item?.mediaMetadata?.requestData?.promptInputs?.[0]?.structuredPrompt?.parts?.[0]?.text || "";
                            let gen = item?.video?.generatedVideo?.prompt || "";
                            let title = item?.mediaMetadata?.mediaTitle || "";
                            let match = (`${raw} | ${gen} | ${title}`).match(/\|\|(.*?)\|\|/);
                            if (match && mediaId && !window._mediaIdToSTT[mediaId]) {
                                window._mediaIdToSTT[mediaId] = match[1].trim();
                            }
                        });
                    } catch(e) {}
                }).catch(e=>{});
            }
            return response;
        };

        // 3. QUÉT DOM SIÊU TỐC (Backup)
        // Lỡ trình duyệt giấu link tải đi đâu đó mà gắn thẳng lên giao diện, ta mò trên UI
        setInterval(() => {
            const mediaElements = document.querySelectorAll('video, source');
            mediaElements.forEach(el => {
                let url = el.src || el.currentSrc || "";
                if (!url || typeof url !== 'string' || url.toLowerCase().includes("thumbnail")) return;

                if (url.includes("GoogleAccessId") || url.includes("media.getMediaUrlRedirect") || url.includes("storage.googleapis.com")) {
                    for (let [mediaId, stt] of Object.entries(window._mediaIdToSTT)) {
                        if (url.includes(mediaId) && !window._completedSTTs.has(stt)) {
                            window._completedSTTs.add(stt); 
                            window._python_results[stt] = url;
                        }
                    }
                }
            });
        }, 500); // Quét 2 lần mỗi giây

    })();
    """
    await page.evaluate(js_interceptor)

# --- HÀM 4: CỐT LÕI - XỬ LÝ BATCH ---
async def process_video_batch(page: Page, file_batch: list, output_folder: str, log_callback=print):
    """
    Tham số `file_batch` nhận đầu vào là mảng list chứa các object.
    """

    
    tasks = {} 
    downloaded_urls = set() 

    # --- GIAI ĐOẠN 1: SUBMIT (Lấy Data từ Object Dictionary) ---
    for item in file_batch:
        stt = str(item.get("STT", "")).strip()
        if not stt: continue
        
        save_path = item.get("video_path")
        
        prompt_text = item.get("visual_details", "Cinematic masterpiece, hyper detailed")
        
        if os.path.exists(save_path):
            log_callback(f"⏭️ Bỏ qua STT {stt} (Đã có video)")
            continue

        id_tag = f"||{stt}||"
        tasks[stt] = {
            "save_path": save_path,
            "id_tag": id_tag,
            "done": False,
            "original_item": item
        }
        
        try:
            textbox = page.locator("[role='textbox']")
            await textbox.wait_for(state="visible", timeout=15000) 
            
            # GỌI HÀM VÀ THÊM AWAIT Ở ĐÂY
            await human_type(textbox, f"{id_tag} {prompt_text}", page)
            
            await page.wait_for_timeout(random.uniform(1000, 2000))
            
            btn_gen = page.locator("i:has-text('arrow_forward')").first
            await btn_gen.wait_for(state="visible", timeout=15000) 
            await btn_gen.click()
            await page.wait_for_timeout(random.uniform(5000, 6000))
            
        except Exception as e:
            log_callback(f"❌ Lỗi gửi STT {stt}: {e}")
            tasks.pop(stt, None) 

    if not tasks: 
        return False, file_batch 

    # --- GIAI ĐOẠN 2: COLLECT (Bằng cách đọc kết quả từ JS Radar) ---
    log_callback(f"⏳ Chờ render {len(tasks)} video qua Radar JS...")
    start_time = time.time()
    
    # Ở đây mình tạm hardcode timeout. Nên thay bằng config.global_settings["system"]["wait_time"]
    wait_time_limit =  config.global_settings["system"]["wait_time"]
    
    while time.time() - start_time < wait_time_limit:
        active_tasks = [uid for uid, info in tasks.items() if not info["done"]]
        if not active_tasks: 
            log_callback("✅ Tất cả video trong đợt này đã tải xong!")
            break

        # Đọc biến window._python_results từ trình duyệt
        js_results_str = await page.evaluate("JSON.stringify(window._python_results || {})")
        js_results = json.loads(js_results_str)

        for uid in active_tasks:
            info = tasks[uid]
            
            # Nếu JS Radar đã bắt được link của STT này
            if uid in js_results:
                video_url = js_results[uid]
                
                # Tránh tải lại link đã tải
                if video_url in downloaded_urls:
                    continue
                
                os.makedirs(os.path.dirname(info["save_path"]), exist_ok=True)
                log_callback(f"💾 Bắt đầu tải Video xịn: STT {uid}")
                
                try:
                    # Dùng API của Playwright để tải thẳng file MP4
                    response = await page.request.get(video_url)
                    with open(info["save_path"], "wb") as f:
                        f.write(await response.body())
                        
                    if os.path.exists(info["save_path"]) and os.path.getsize(info["save_path"]) > 0:
                        log_callback(f"✅ Thành công: STT {uid}")
                        info["done"] = True
                        downloaded_urls.add(video_url)
                    else:
                        log_callback(f"⚠️ Lỗi tải file bị 0KB: STT {uid}")
                except Exception as e:
                    log_callback(f"❌ Lỗi download MP4 STT {uid}: {e}")

        await page.wait_for_timeout(3000) # Quét lại sau mỗi 3 giây

    # --- TỔNG KẾT BATCH ---
    # Những object nào chưa "done" thì trả nguyên gốc lại để cho vào hàng đợi retry
    failed_objects = [v["original_item"] for k, v in tasks.items() if not v["done"]]
    
    return len(failed_objects) == 0, failed_objects