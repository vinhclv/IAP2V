import os
import time
import random
import json
import re
# SỬA LẠI: Import bản async
from playwright.async_api import Page, Locator 
import config 

# ==========================================
# 🤖 HỆ THỐNG MÔ PHỎNG HÀNH VI NGƯỜI THẬT
# ==========================================

async def human_click(locator: Locator, page: Page, force: bool = False):
    """
    Mô phỏng click chuột của người thật bằng Virtual Mouse.
    Không chiếm chuột vật lý của máy tính.
    """
    try:
        # 1. Cuộn trang mượt mà tới phần tử (nếu nó đang bị khuất)
        await locator.scroll_into_view_if_needed(timeout=5000)
        
        # 2. Rê chuột (hover) vào phần tử, tạo ra các sự kiện mousemove, mouseenter
        await locator.hover(timeout=5000)
        
        # 3. Mắt người nhìn xác nhận trước khi bấm
        await page.wait_for_timeout(random.uniform(100, 300))
        
        # 4. Nhấn chuột xuống và nhả ra với độ trễ của cơ tay (50ms - 150ms)
        await locator.click(delay=random.randint(50, 150), force=force)
    except Exception as e:
        # Backup: Nếu phần tử bị thẻ div khác đè lên, ép click cơ bản nhưng vẫn có trễ
        print(f"⚠️ Chuyển sang click dự phòng: {e}")
        await locator.click(delay=random.randint(50, 150), force=True)

async def human_type(locator: Locator, text: str, page: Page):
    """
    Mô phỏng gõ phím theo cụm (chunk) với tốc độ và nhịp thở của người thật.
    """
    # Thay vì click cứng, gọi hàm human_click
    await human_click(locator, page)
    await page.wait_for_timeout(random.uniform(200, 400))

    idx = 0
    while idx < len(text):
        chunk_size = random.randint(15, 30)
        chunk = text[idx:idx+chunk_size]
        
        # Ép tốc độ gõ phím siêu tốc: 5-10ms cho mỗi ký tự
        await locator.press_sequentially(chunk, delay=random.randint(5, 10))
        idx += chunk_size
        
        # Thời gian nghỉ giữa các cụm cực ngắn (20-50ms)
        await page.wait_for_timeout(random.uniform(20, 50))
        
        # Giảm tỷ lệ "suy nghĩ" xuống còn 5% và thời gian khựng cũng ngắn lại
        if random.random() < 0.05:
            await page.wait_for_timeout(random.uniform(100, 200))

    # Thời gian chờ chốt hạ
    await page.wait_for_timeout(random.uniform(200, 400))

# ==========================================
# ⚙️ LOGIC CHÍNH CỦA BẠN (Đã bọc Human Click)
# ==========================================

async def setup_video_creation_mode(page: Page):
    print("⚙️ Đang cấu hình giao diện (Mode -> Landscape -> Qty=1 -> Quality Model)...")

    try:
        # 1. Tạo dự án
        create_btn = page.locator("i:has-text('add_2')").first
        if await create_btn.is_visible(timeout=45000):
            await human_click(create_btn, page)
            await page.wait_for_timeout(1000)
        
        print("Đang chọn chế độ video...")
        dropdown_btn = page.locator("button[type='button'][aria-haspopup='menu']", has_text=re.compile(r"Banana|Video", re.IGNORECASE)).first
        await dropdown_btn.wait_for(state="visible", timeout=45000)
        # Dùng human_click thay vì click thông thường, bật force=True như logic gốc của bạn
        await human_click(dropdown_btn, page, force=True)
        await page.wait_for_timeout(1000) 

        await human_click(page.locator("i:has-text('videocam')").last, page)
        await page.wait_for_timeout(500)
        
        print("Đang chọn chế độ thành phần...")
        await human_click(page.locator("i:has-text('chrome_extension')").first, page)
        await page.wait_for_timeout(500)
        
        print("Đang chọn khung hình...")
        await human_click(page.locator("i:has-text('crop_16_9')").last, page)
        await page.wait_for_timeout(500)
        
        print("Đang chọn model...")
        await human_click(page.locator("i:has-text('arrow_drop_down')").first, page)
        await page.wait_for_timeout(500)
        await human_click(page.locator("i:has-text('volume_up')").nth(1), page)
        await page.wait_for_timeout(500)
        
        print("Đang chọn số lượng = 1...")
        await human_click(page.locator("button.flow_tab_slider_trigger", has_text="x1").first, page)
        await page.wait_for_timeout(500)
        
        print("Đang đóng bảng...")
        await human_click(page.locator("i:has-text('crop_16_9')").first, page)
        await page.wait_for_timeout(500)
        print("✅ Đã cấu hình xong!")

    except Exception as e:
        print(f"⚠️ Dừng ngay tại lỗi setup: {e}")

async def inject_radar_js(page: Page):
    js_interceptor = r"""
    (function() {
        window._python_results = window._python_results || {};
        window._mediaIdToSTT = window._mediaIdToSTT || {};
        window._completedSTTs = window._completedSTTs || new Set(); 
        window._isInterceptorInjected = window._isInterceptorInjected || false;

        if (window._isInterceptorInjected) return;
        window._isInterceptorInjected = true;
        console.log("%c[HỆ THỐNG] 🚀 ĐÃ BƠM RADAR BẮT SỐNG (ZERO LATENCY)...", "color: #ff00ff; font-size: 16px; font-weight: bold;");

        // 1. CƯỚP CÒ XHR
        const origOpen = XMLHttpRequest.prototype.open;
        const origSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._intercept_url = typeof url === 'string' ? url : url.toString();
            
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

        // 2. CƯỚP CÒ FETCH
        const origFetch = window.fetch;
        window.fetch = async function(...args) {
            const url = args[0]?.url || args[0] || "";
            
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

        // 3. QUÉT DOM SIÊU TỐC
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
        }, 500); 

    })();
    """
    await page.evaluate(js_interceptor)


def parse_duration_to_seconds(timecode_str: str) -> float:
    try:
        # Tách start và end
        parts = timecode_str.split(" --> ")
        def to_sec(t):
            # Format: HH:MM:SS,mmm
            h, m, s_ms = t.split(":")
            s, ms = s_ms.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        duration = to_sec(parts[1]) - to_sec(parts[0])
        return duration
    except:
        return 8.0 # Mặc định nếu lỗi
        
async def setup_video_duration(page: Page, timecode: str):
    """
    Cấu hình thời lượng video dựa trên timecode từ SRT.
    Các tùy chọn: 4s, 6s, 8s.
    """
    print(f"⏳ Đang tính toán thời lượng cho: {timecode}")
    
    try:
        # 1. Tính toán số giây thực tế
        actual_seconds = parse_duration_to_seconds(timecode)
        
        # 2. Định danh mục tiêu (target)
        if actual_seconds <= 4:
            target_label = "4s"
        elif actual_seconds <= 6:
            target_label = "6s"
        else:
            target_label = "8s"
            
        print(f"-> Thời gian thực: {actual_seconds:.2f}s | Ép cấu hình: {target_label}")

        # 3. Thực hiện tương tác UI
        dropdown_btn = page.locator("button[type='button'][aria-haspopup='menu']", has_text=re.compile(r"Banana|Video", re.IGNORECASE)).first
        await dropdown_btn.wait_for(state="visible", timeout=45000)
        await human_click(dropdown_btn, page, force=True)
        await page.wait_for_timeout(1000) 


        # Tìm nút có text tương ứng (ví dụ: "4s", "6s", "8s")
        duration_btn = page.locator("button, .flow_tab_slider_trigger", has_text=target_label).first
        
        if await duration_btn.is_visible(timeout=5000):
            await human_click(duration_btn, page)
            await human_click(page.locator("i:has-text('crop_16_9')").first, page)
            await page.wait_for_timeout(500)
            print(f"✅ Đã chọn thời lượng {target_label}")
        else:
            print(f"⚠️ Không tìm thấy nút {target_label} trong menu hiện tại.")

    except Exception as e:
        print(f"⚠️ Lỗi khi cấu hình duration: {e}")

async def process_video_batch(page: Page, file_batch: list, output_folder: str, log_callback=print):
    tasks = {} 
    downloaded_urls = set() 

    # --- GIAI ĐOẠN 1: SUBMIT ---
    for item in file_batch:
        stt = str(item.get("STT", "")).strip()
        if not stt: continue

        await setup_video_duration(page, item.get("Timecode"))
        
        video_path = item.get("video_path")
        prompt_text = item.get("visual_details", "Cinematic masterpiece, hyper detailed")
        
        if os.path.exists(video_path):
            log_callback(f"⏭️ Bỏ qua STT {stt} (Đã có video)")
            continue

        id_tag = f"||{stt}||"
        tasks[stt] = {
            "video_path": video_path,
            "id_tag": id_tag,
            "done": False,
            "original_item": item
        }
        
        try:
            textbox = page.locator("[role='textbox']")
            await textbox.wait_for(state="visible", timeout=15000) 
            
            # Thay vì gọi click trực tiếp, human_type sẽ lo việc focus và gõ phím
            await human_type(textbox, f"{id_tag} {prompt_text}", page)
            await page.wait_for_timeout(random.uniform(1000, 2000))
            
            btn_gen = page.locator("i:has-text('arrow_forward')").first
            await btn_gen.wait_for(state="visible", timeout=15000) 
            
            # Thay thế click thường bằng human_click cho nút submit
            await human_click(btn_gen, page)
            await page.wait_for_timeout(random.uniform(5000, 6000))
            
        except Exception as e:
            log_callback(f"❌ Lỗi gửi STT {stt}: {e}")
            tasks.pop(stt, None) 

    if not tasks: 
        return False, file_batch 

    # --- GIAI ĐOẠN 2: COLLECT ---
    log_callback(f"⏳ Chờ render {len(tasks)} video qua Radar JS...")
    start_time = time.time()
    wait_time_limit = config.global_settings["system"]["wait_time"]
    
    while time.time() - start_time < wait_time_limit:
        active_tasks = [uid for uid, info in tasks.items() if not info["done"]]
        if not active_tasks: 
            log_callback("✅ Tất cả video trong đợt này đã tải xong!")
            break

        js_results_str = await page.evaluate("JSON.stringify(window._python_results || {})")
        js_results = json.loads(js_results_str)

        for uid in active_tasks:
            info = tasks[uid]
            
            if uid in js_results:
                video_url = js_results[uid]
                
                if video_url in downloaded_urls:
                    continue
                
                os.makedirs(os.path.dirname(info["video_path"]), exist_ok=True)
                log_callback(f"💾 Bắt đầu tải Video xịn: STT {uid}")
                
                try:
                    response = await page.request.get(video_url)
                    with open(info["video_path"], "wb") as f:
                        f.write(await response.body())
                        
                    if os.path.exists(info["video_path"]) and os.path.getsize(info["video_path"]) > 0:
                        log_callback(f"✅ Thành công: STT {uid}")
                        info["done"] = True
                        downloaded_urls.add(video_url)
                    else:
                        log_callback(f"⚠️ Lỗi tải file bị 0KB: STT {uid}")
                except Exception as e:
                    log_callback(f"❌ Lỗi download MP4 STT {uid}: {e}")

        await page.wait_for_timeout(3000)

    # --- TỔNG KẾT BATCH ---
    failed_objects = [v["original_item"] for k, v in tasks.items() if not v["done"]]
    return len(failed_objects) == 0, failed_objects