# ============================================================
# 파일명: wpps_auto_register.py  
# 설명: WPPS 출하통보등록 자동화 - 방향키 5번 이동 (하차지 -> 유형)
# ============================================================
import os
import time
import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from supabase import create_client, Client

load_dotenv()
WPPS_USER_ID = os.getenv("WPPS_ID", "YOUR_ID")
WPPS_PASSWORD = os.getenv("WPPS_PW")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LOGIN_URL = "https://wpps.logisall.net/login"
SCREENSHOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase 초기화 실패: {e}")
WPPS_USER_ID = os.getenv("WPPS_ID", "YOUR_ID")
WPPS_PASSWORD = os.getenv("WPPS_PW")
LOGIN_URL = "https://wpps.logisall.net/login"
SCREENSHOT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 전역 변수 설정 (사용자 입력으로 덮어씌워짐) ---
DEST_CODE = ""
TYPE_CODE = ""
QUANTITY = ""

# --- 그리드 네비게이션 설정 ---
STEPS_TO_TYPE = 5
STEPS_TO_QUANTITY = 3

import sys

def get_user_input():
    global DEST_CODE, TYPE_CODE, QUANTITY
    
    # 스케줄러 등을 위해 커맨드라인 인자로 자동 실행 지원
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        print("\n⚙️ [자동 실행 모드] 백그라운드 고정값으로 1건 자동 생성 진행")
        DEST_CODE = "000000"
        TYPE_CODE = "N11"
        QUANTITY = "4"
        return "2", 1

    print("\n📦 === 출하통보등록 자동화 === 📦")
    print("1: [단건 수기 모드] 매번 하차지, 유형, 수량을 직접 입력")
    print("2: [고정 자동 모드] 하차지(000000), 유형(N11), 수량(4) 매일 1건 자동 생성")
    mode = input(">> 모드를 선택하세요 (1 또는 2): ").strip()

    loop_count = 1
    if mode == "1":
        DEST_CODE = input(">> 하차지 코드를 입력하세요 (예: 000000): ").strip()
        TYPE_CODE = input(">> 유형 코드를 입력하세요 (예: N11): ").strip()
        QUANTITY = input(">> 수량을 입력하세요: ").strip()
    elif mode == "2":
        print("\n⚙️ [고정 자동 모드] 하차지: 000000, 유형: N11, 수량: 4 (1건 생성)")
        DEST_CODE = "000000"
        TYPE_CODE = "N11"
        QUANTITY = "4"
    else:
        print("❌ 잘못된 입력입니다. 종료합니다.")
        exit(1)
        
    return mode, loop_count

def create_browser():
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=["--start-maximized", "--disable-save-password-bubble",
              "--disable-notifications", "--disable-infobars"]
    )
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    page.on("dialog", lambda d: d.accept())
    return pw, browser, page

def close_popups(page):
    for sel in [".noticeRenewWpps__closeBtn", ".popup-close", "button.close"]:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                page.locator(sel).first.click()
                time.sleep(0.3)
        except Exception:
            pass
    for frame in page.frames:
        try:
            if frame.locator("#popupBtnClose").first.is_visible(timeout=1000):
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


    return page

if __name__ == "__main__":
    mode, loop_count = get_user_input()
    
    pw, browser, page = create_browser()
    try:
        # 로그인 단계
        print("\n🌐 로그인...")
        page.goto(LOGIN_URL, wait_until="networkidle")
        close_popups(page)
        time.sleep(1)
        
        page.locator("input#loginId").click()
        page.locator("input#loginId").fill("")
        page.locator("input#loginId").type(WPPS_USER_ID)
        page.locator("input#password").click()
        page.locator("input#password").fill("")
        page.locator("input#password").type(WPPS_PASSWORD)
        page.locator("button.btn_login").click()
        
        page.wait_for_url("**/ps/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        print("✅ 로그인 성공!")
        close_popups(page)
        time.sleep(1)

        # 출하통보등록 이동
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
        
        print("✅ 준비 완료!")

        for cycle in range(1, loop_count + 1):
            if loop_count > 1:
                print(f"\n🚀 ═══ 등록 시작 ({cycle}/{loop_count}번째) ═══")
            else:
                print("\n🚀 ═══ 등록 시작 ═══")
                
            cf = find_content_frame(page)

            # 1. 새로고침
            print("1️⃣ 새로고침")
            cf.locator("text=새로고침").first.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            cf = find_content_frame(page)

            # 2. 신규버튼 클릭
            print("2️⃣ 신규 (1번행 생성)")
            cf.locator("text=신규").first.click()
            time.sleep(2)
            
            # 팝업 달력 회피용 ESC
            page.keyboard.press("Escape")
            time.sleep(1)

            # ==========================================================
            # ★ '신규' 클릭 직후 표 계산 및 여백 마우스 클릭
            # ==========================================================
            
            # 프레임 오프셋 계산
            frame_offset_x, frame_offset_y = 0, 0
            for frame_el in page.locator("iframe").all():
                try:
                    if "PBM140MW" in (frame_el.get_attribute("src") or ""):
                        f_box = frame_el.bounding_box()
                        if f_box:
                            frame_offset_x, frame_offset_y = f_box['x'], f_box['y']
                            break
                except: pass

            # 하차지 헤더를 기준점으로 잡아 여백 계산
            loc = cf.get_by_text("하차지", exact=True)
            target_box = None
            for i in range(loc.count()):
                box = loc.nth(i).bounding_box()
                if box and box['y'] > 50:
                    if not target_box or box['y'] > target_box['y']:
                        target_box = box

            if not target_box:
                raise Exception("❌ 기준점 '하차지' 헤더를 찾을 수 없습니다!")

            # 3. 1번행 하단 여백 1번 클릭
            cx = target_box['x'] + frame_offset_x + 10 
            cy = target_box['y'] + frame_offset_y + 90 
            
            print(f"3️⃣ 마우스로 1번행 하단 여백 클릭 ({cx:.0f}, {cy:.0f})")
            page.mouse.click(cx, cy)
            time.sleep(1) 

            # 4. 하차지 입력
            print(f"4️⃣ [하차지] 입력: {DEST_CODE}")
            page.keyboard.type(DEST_CODE)
            time.sleep(0.5)

            # 5. 방향키(ArrowRight) 5번으로 우측 이동 (유형)
            print(f"5️⃣ [유형] 으로 이동 (방향키 {STEPS_TO_TYPE}번)")
            page.keyboard.press("Enter")  # 하차지 입력 확정
            time.sleep(0.5)
            
            for _ in range(STEPS_TO_TYPE):
                page.keyboard.press("ArrowRight")
                time.sleep(0.2)
                
            page.keyboard.press("Enter")  # 유형 칸 열기
            time.sleep(0.5)

            # 6. 유형 입력
            print(f"6️⃣ [유형] 입력: {TYPE_CODE}")
            page.keyboard.type(TYPE_CODE)
            time.sleep(0.5)

            # 7. 방향키(ArrowRight) 1번으로 우측 이동 (수량)
            print(f"7️⃣ [수량] 으로 이동 (방향키 {STEPS_TO_QUANTITY}번)")
            page.keyboard.press("Enter")  # 유형 입력 확정
            time.sleep(0.5)
            
            for _ in range(STEPS_TO_QUANTITY):
                page.keyboard.press("ArrowRight")
                time.sleep(0.2)
                
            page.keyboard.press("Enter")  # 수량 칸 열기
            time.sleep(0.5)

            # 8. 수량 입력
            print(f"8️⃣ [수량] 입력: {QUANTITY}")
            # 기존 0이 있을 수 있으니 컨트롤A
            page.keyboard.press("Control+a")
            page.keyboard.type(QUANTITY)
            time.sleep(0.5)
            
            # 입력 최종 확정
            page.keyboard.press("Enter")
            time.sleep(1)
            
            print("   ✅ 연속 데이터 입력 사이클 완료!")

            # 상황 검증용 스크린샷
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "before_save.png"))

            # 10. 최종 저장 버튼 누르기 (대기 없이 즉각)
            print("🔟 저장 버튼 클릭!")
            cf = find_content_frame(page)
            cf.locator("text=저장").first.click()
            time.sleep(3)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"complete_cycle_{cycle}.png"))
            print(f"   ✅ {cycle}번째 생성 완료")

            # 11. 로그 발송 (DB 저장)
            if supabase:
                try:
                    log_data = {
                        "user_id": WPPS_USER_ID,
                        "dest_code": DEST_CODE,
                        "type_code": TYPE_CODE,
                        "quantity": QUANTITY,
                        "status": "SUCCESS",
                        "error_message": None
                    }
                    supabase.table("automation_logs").insert(log_data).execute()
                    print("📡 DB 기록 완료: SUCCESS")
                except Exception as db_e:
                    print(f"⚠️ DB 기록 실패: {db_e}")
            
            # 다음 사이클을 위해 잠깐 대기
            time.sleep(2)

        print("\n🎉 ═══ 모든 스크립트 실행 종료 ═══")
        # 수동 대기 없이 바로 종료. 브라우저 창은 여기서 닫힘.

    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "error.png"))
        
        # 오류 발생 시 실패 로그 발송
        if 'supabase' in globals() and supabase:
            try:
                log_data = {
                    "user_id": WPPS_USER_ID,
                    "dest_code": DEST_CODE,
                    "type_code": TYPE_CODE,
                    "quantity": QUANTITY,
                    "status": "ERROR",
                    "error_message": str(e)
                }
                supabase.table("automation_logs").insert(log_data).execute()
                print("📡 DB 기록 완료: ERROR")
            except Exception as db_e:
                pass
    finally:
        browser.close()
        pw.stop()
