# ============================================================
# 파일명: wpps_inbound_register.py
# 설명: WPPS 납품/반납요청(입고) 자동화 스크립트
# 규칙: 요청구분(입고), 하차일(D+2), 유형(N11), 수량(50)
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

# Supabase 초기화
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase 초기화 실패: {e}")

# --- 입고 입력 고정 데이터 ---
REQ_TYPE = "입고"         # 요청구분 (드롭다운/직접입력)
req_date_obj = datetime.datetime.now() + datetime.timedelta(days=2)
REQ_DATE = req_date_obj.strftime("%Y%m%d") # 하차요청일자 (안전재고 이하시 2일후, 형식: 20260313)
PALLET_TYPE = "N11"       # 유형: KPP파렛트
QUANTITY = "50"           # 요청수량

# 보안을 위해 실제 상호 및 상차지 주소는 더미 처리. 
# 실무 적용 시 .env로 빼내거나 사용자 입력(DB)에서 가져오도록 권장합니다.
REQ_COMPANY_CODE = "000000"  # 실제 요청업체 코드로 변경 필요 (더미 처리)
REQ_DEST = "DUMMY_ADDRESS"   # 실제 도착지 주소로 변경 필요 (더미 처리)

# --- 그리드 네비게이션 설정 ---
# 납품/반납요청 그리드 순서:
# 선택 | 요청구분 | 하차요청일자 | 유형 | 행 복사 | 차량구분 | 요청수량 | 요청업체 | (빈칸) | 실도착지
# 클릭(기준) 한 뒤 요청구분에서 시작한다고 가정
STEPS_TO_DATE = 1
STEPS_TO_TYPE = 1
STEPS_TO_QTY = 3    # 유형 -> 행 복사 -> 차량구분 -> 요청수량
STEPS_TO_COMP = 1   # 요청수량 -> 요청업체
STEPS_TO_DEST = 2   # 요청업체 -> (빈칸) -> 실도착지

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
    # '신규' 버튼을 포함하는 프레임을 찾음
    for frame in page.frames:
        try:
            if frame.locator("text=신규").first.is_visible(timeout=500):
                return frame
        except Exception:
            pass
    return page

if __name__ == "__main__":
    pw, browser, page = create_browser()
    try:
        # 1. 로그인
        print("🌐 로그인...")
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

        # 2. 납품/반납요청 메뉴 이동
        print("📂 요청 및 조회관리 → 납품/반납요청 이동...")
        try:
            page.locator("text=요청 및 조회관리").first.click()
            time.sleep(1)
        except Exception:
            pass
            
        page.locator("text=납품/반납요청").first.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(5)
        close_popups(page)
        time.sleep(2)
        
        print("✅ 준비 완료!")
        cf = find_content_frame(page)

        print("\n🚀 ═══ [입고] 납품/반납요청 등록 시작 ═══")

        # 1. 새로고침
        print("1️⃣ 새로고침")
        try:
            cf.locator("text=새로고침").first.click()
            time.sleep(3)
        except:
            print("   (새로고침 버튼이 없거나 실패. 계속 진행)")
            pass
        
        page.wait_for_load_state("networkidle", timeout=10000)
        cf = find_content_frame(page)

        # 2. 신규버튼 클릭
        print("2️⃣ 신규 (1번행 생성)")
        cf.locator("text=신규").first.click()
        time.sleep(2)
        
        page.keyboard.press("Escape")
        time.sleep(1)

        # 3. 1번행 하단 여백 클릭 방식
        frame_offset_x, frame_offset_y = 0, 0
        for frame_el in page.locator("iframe").all():
            try:
                if frame_el.get_attribute("src") and "ps/" in frame_el.get_attribute("src"):
                    f_box = frame_el.bounding_box()
                    if f_box:
                        frame_offset_x, frame_offset_y = f_box['x'], f_box['y']
                        break
            except: pass

        # '요청구분' 헤더를 기준점으로 잡아 여백 계산
        loc = cf.get_by_text("요청구분", exact=True)
        target_box = None
        for i in range(loc.count()):
            box = loc.nth(i).bounding_box()
            if box and box['y'] > 50:
                if not target_box or box['y'] > target_box['y']:
                    target_box = box

        if not target_box:
            raise Exception("❌ 기준점 '요청구분' 헤더를 찾을 수 없습니다!")

        # 하단 여백 클릭 (표의 첫번째 셀 부근)
        cx = target_box['x'] + frame_offset_x + 10 
        cy = target_box['y'] + frame_offset_y + 90 
        
        print(f"3️⃣ 마우스로 1번행 하단 여백 클릭 ({cx:.0f}, {cy:.0f})")
        page.mouse.click(cx, cy)
        time.sleep(1) 

        # 4. 키보드 입력 사이클 (요청구분 -> 날짜 -> 유형 -> 수량)
        print("4️⃣ 키보드 입력 시작")
        
        # [요청구분]
        print(f"   ▷ [요청구분] 입력: {REQ_TYPE}")
        page.keyboard.type(REQ_TYPE)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        # [하차요청일자]로 이동
        for _ in range(STEPS_TO_DATE):
            page.keyboard.press("ArrowRight")
            time.sleep(0.2)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        print(f"   ▷ [하차요청일자] 입력: {REQ_DATE}")
        page.keyboard.type(REQ_DATE)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        # [유형]으로 이동
        for _ in range(STEPS_TO_TYPE):
            page.keyboard.press("ArrowRight")
            time.sleep(0.2)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        print(f"   ▷ [유형] 입력: {PALLET_TYPE}")
        page.keyboard.type(PALLET_TYPE)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        # [수량]으로 이동
        for _ in range(STEPS_TO_QTY):
            page.keyboard.press("ArrowRight")
            time.sleep(0.2)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        print(f"   ▷ [요청수량] 입력: {QUANTITY}")
        page.keyboard.type(QUANTITY)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(0.5)

        # [요청업체]로 이동
        for _ in range(STEPS_TO_COMP):
            page.keyboard.press("ArrowRight")
            time.sleep(0.2)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        print(f"   ▷ [요청업체] 입력: {REQ_COMPANY_CODE}")
        page.keyboard.type(REQ_COMPANY_CODE)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(1) # 업체 검색 등 팝업/자동완성 대기 가능성 높음

        # [실도착지]로 이동
        for _ in range(STEPS_TO_DEST):
            page.keyboard.press("ArrowRight")
            time.sleep(0.2)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        
        print(f"   ▷ [실도착지] 입력: {REQ_DEST}")
        page.keyboard.type(REQ_DEST)
        time.sleep(0.5)
        
        # 최종 행 완료
        page.keyboard.press("Enter")
        time.sleep(1)

        print("   ✅ 연속 데이터 입력 사이클 완료!")

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "inbound_before_save.png"))

        # 최종 저장 버튼 (수동대기 없이 즉각 저장)
        print("🔟 저장 버튼 클릭!")
        cf = find_content_frame(page)
        cf.locator("text=저장").first.click()
        time.sleep(3)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "inbound_complete.png"))
        print("\n✅ ═══ 스크립트 실행 종료 ═══")

        # Supabase 로깅
        if supabase:
            try:
                log_data = {
                    "user_id": WPPS_USER_ID,
                    "dest_code": "납품/반납요청",
                    "type_code": PALLET_TYPE,
                    "quantity": QUANTITY,
                    "status": "SUCCESS",
                    "error_message": f"Date: {REQ_DATE}"
                }
                supabase.table("automation_logs").insert(log_data).execute()
                print("📡 DB 기록 완료: SUCCESS")
            except: pass

        time.sleep(3)

    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "inbound_error.png"))
    finally:
        browser.close()
        pw.stop()
