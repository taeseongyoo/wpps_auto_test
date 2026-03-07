import os
import time
import uuid
import datetime
from threading import Lock
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()
WPPS_USER_ID = os.getenv("WPPS_ID", "YOUR_ID")
WPPS_PASSWORD = os.getenv("WPPS_PW")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LOGIN_URL = "https://wpps.logisall.net/login"

app = FastAPI(title="WPPS Automation SaaS API")

# Initialize Scheduler
scheduler = BackgroundScheduler()
scheduler.start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase 초기화 실패: {e}")

# Models
class ShipmentItem(BaseModel):
    dest_name: Optional[str] = None # For UI convenience, not used in playwright
    dest_code: str
    type_code: str
    quantity: str

class JobRequest(BaseModel):
    items: List[ShipmentItem]
    user_id: Optional[str] = WPPS_USER_ID

# To prevent multiple browsers opening at once, we use a global lock
job_lock = Lock()

def close_popups(page):
    for sel in [".noticeRenewWpps__closeBtn", ".popup-close", "button.close"]:
        try:
            if page.locator(sel).first.is_visible(timeout=500):
                page.locator(sel).first.click()
                time.sleep(0.3)
        except Exception:
            pass
    for frame in page.frames:
        try:
            if frame.locator("#popupBtnClose").first.is_visible(timeout=500):
                frame.locator("#popupBtnClose").first.click()
                time.sleep(0.3)
        except Exception:
            pass

def find_content_frame(page):
    for frame in page.frames:
        try:
            if frame.evaluate("document.body ? document.body.innerHTML.includes('새로고침') : false"):
                return frame
        except Exception:
            pass
    return page

def run_automation_task(job_req: JobRequest):
    # This prevents multiple jobs from running simultaneously
    with job_lock:
        try:
            # Login and setup
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=False, # Show browser for local debugging
                    args=["--start-maximized", "--disable-save-password-bubble",
                          "--disable-notifications", "--disable-infobars"]
                )
                context = browser.new_context(no_viewport=True)
                page = context.new_page()
                page.on("dialog", lambda d: d.accept())

                print("🌐 로그인 중...")
                page.goto(LOGIN_URL, wait_until="networkidle")
                close_popups(page)
                time.sleep(1)
                
                page.locator("input#loginId").fill(WPPS_USER_ID)
                page.locator("input#password").fill(WPPS_PASSWORD)
                page.locator("button.btn_login").click()
                
                try:
                    page.wait_for_url("**/ps/**", timeout=15000)
                except:
                    pass
                page.wait_for_load_state("networkidle")
                close_popups(page)
                
                # Navigate to the registration page
                print("📂 출하통보등록 이동...")
                try: 
                    page.locator("text=입출고관리").first.click()
                    time.sleep(1)
                except: pass
                
                page.locator("text=출하통보등록").first.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(5)
                close_popups(page)
                time.sleep(2)
                
                # Fetch target frame once
                cf = find_content_frame(page)
                
                cf.locator("text=새로고침").first.click()
                time.sleep(3)
                page.wait_for_load_state("networkidle", timeout=10000)
                cf = find_content_frame(page)

                cf.locator("text=신규").first.click()
                time.sleep(2)
                page.keyboard.press("Escape")
                time.sleep(1)

                # Frame offset logic
                frame_offset_x, frame_offset_y = 0, 0
                for frame_el in page.locator("iframe").all():
                    try:
                        if "PBM140MW" in (frame_el.get_attribute("src") or ""):
                            f_box = frame_el.bounding_box()
                            if f_box:
                                frame_offset_x, frame_offset_y = f_box['x'], f_box['y']
                                break
                    except: pass

                # Main item loop
                loc = cf.get_by_text("하차지", exact=True)
                target_box = None
                for i in range(loc.count()):
                    box = loc.nth(i).bounding_box()
                    if box and box['y'] > 50:
                        if not target_box or box['y'] > target_box['y']:
                            target_box = box

                for item in job_req.items:
                    # Mark in DB as processing
                    print(f"🔄 처리 중: {item.dest_code} / {item.quantity}개")

                    # 3. 1번행 하단 여백 1번 클릭
                    cx = target_box['x'] + frame_offset_x + 10 
                    cy = target_box['y'] + frame_offset_y + 90 
                    page.mouse.click(cx, cy)
                    time.sleep(1) 

                    # 4. 하차지 입력
                    page.keyboard.type(item.dest_code)
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(0.5)
                    
                    for _ in range(5):
                        page.keyboard.press("ArrowRight")
                        time.sleep(0.2)
                        
                    page.keyboard.press("Enter")
                    time.sleep(0.5)

                    page.keyboard.type(item.type_code)
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(0.5)
                    
                    for _ in range(3):
                        page.keyboard.press("ArrowRight")
                        time.sleep(0.2)
                        
                    page.keyboard.press("Enter")
                    time.sleep(0.5)

                    page.keyboard.press("Control+a")
                    page.keyboard.type(str(item.quantity))
                    time.sleep(0.5)
                    
                    page.keyboard.press("Enter")
                    time.sleep(1)

                    # Update Supabase Success
                    if supabase:
                        supabase.table("automation_logs").insert({
                            "user_id": str(job_req.user_id),
                            "dest_code": item.dest_code,
                            "type_code": item.type_code,
                            "quantity": item.quantity,
                            "status": "SUCCESS"
                        }).execute()

                # Final Save
                print("🔟 저장 버튼 클릭!")
                cf = find_content_frame(page)
                cf.locator("text=저장").first.click()
                time.sleep(3)
                print("✅ 전체 배치 작업 완료!")

                browser.close()

        except Exception as e:
            print(f"⚠️ 백그라운드 태스크 오류: {e}")
            import traceback
            traceback.print_exc()
            if supabase:
                try:
                    supabase.table("automation_logs").insert({
                        "user_id": str(job_req.user_id),
                        "status": "ERROR",
                        "dest_code": "SYSTEM",
                        "type_code": "ERR",
                        "quantity": 0,
                    }).execute()
                except Exception as db_err:
                    print(f"DB Error Log Fail: {db_err}")


@app.post("/api/register")
async def trigger_registration(req: JobRequest, background_tasks: BackgroundTasks):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured.")
        
    if not req.items or len(req.items) == 0:
        raise HTTPException(status_code=400, detail="No items provided in array.")

    # 1. Background 작업 실행 (큐에 넣기)
    background_tasks.add_task(run_automation_task, req)

    # 2. 클라이언트에는 접수 완료 즉시 응답 반환
    return {
        "status": "queued",
        "message": f"{len(req.items)}건의 출하통보 요청이 백그라운드 큐에 배정되었습니다.",
        "user_id": req.user_id
    }

class ScheduleRequest(BaseModel):
    time: str # "HH:MM" format
    recurrence: str = "daily" # daily, weekly, monthly
    recurrence_val: Optional[str] = None # e.g., "0" for Monday, "1" for 1st of month
    items: List[ShipmentItem]
    user_id: Optional[str] = WPPS_USER_ID

@app.post("/api/schedule")
async def setup_daily_schedule(req: ScheduleRequest):
    try:
        hour, minute = req.time.split(":")
        
        # User defined payload
        job_req = JobRequest(
            items=req.items,
            user_id=req.user_id
        )
        
        job_id = f"routine_job_{req.user_id}"
        
        # Remove existing job if exists
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
            
        # Determine Cron Trigger
        if req.recurrence == "weekly" and req.recurrence_val:
            trigger = CronTrigger(day_of_week=int(req.recurrence_val), hour=int(hour), minute=int(minute))
            freq_str = f"매주 요일({req.recurrence_val})"
        elif req.recurrence == "monthly" and req.recurrence_val:
            trigger = CronTrigger(day=int(req.recurrence_val), hour=int(hour), minute=int(minute))
            freq_str = f"매월 {req.recurrence_val}일"
        else:
            trigger = CronTrigger(hour=int(hour), minute=int(minute))
            freq_str = "매일"
            
        # Add new job
        scheduler.add_job(
            run_automation_task,
            trigger,
            args=[job_req],
            id=job_id
        )
        print(f"⏰ 스케줄 등록 완료: {freq_str} {req.time}")
        return {"status": "success", "message": f"{freq_str} {req.time} 자동 실행이 설정되었습니다."}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "WPPS SaaS Backend Running"}

if __name__ == "__main__":
    import uvicorn
    # Test via `python app.py` locally
    uvicorn.run(app, host="0.0.0.0", port=8000)
