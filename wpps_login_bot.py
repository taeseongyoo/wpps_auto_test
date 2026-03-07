# ============================================================
# 파일명: wpps_login_bot.py
# 설명: Playwright 브라우저 자동화 - WPPS 로그인 + 출하통보등록 접근
# Why type()?: fill()은 JS 이벤트를 발생시키지 않아 로그인 실패.
#   type()은 실제 키보드 입력처럼 동작하여 사이트의 JS가 정상 인식합니다.
# ============================================================
import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# 금고(.env)에서 인증 정보 로드
load_dotenv()
WPPS_USER_ID = os.getenv("WPPS_ID", "YOUR_ID")
WPPS_PASSWORD = os.getenv("WPPS_PW")
LOGIN_URL = "https://wpps.logisall.net/login"
SCREENSHOT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_browser():
    """비밀번호 저장 팝업 차단된 크롬 브라우저 생성"""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=["--disable-save-password-bubble", "--disable-notifications", "--disable-infobars"]
    )
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    return pw, browser, page


def close_popup(page, desc="팝업"):
    """페이지에 뜬 팝업을 찾아 닫기"""
    selectors = [
        ".noticeRenewWpps__closeBtn",
        ".popup-close", ".modal .close", "button.close",
        ".layerpopup .btn_close", ".pop_wrap .btn_close",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click()
                print(f"   📢 {desc} 닫기 완료! ({sel})")
                time.sleep(0.5)
                return True
        except Exception:
            continue
    try:
        x_btn = page.locator("button:has-text('×'), button:has-text('닫기'), a:has-text('[Close]'), :has-text('[Close]') >> visible=true").first
        if x_btn.is_visible(timeout=1500):
            x_btn.click()
            print(f"   📢 {desc} 닫기 완료! (텍스트)")
            time.sleep(0.5)
            return True
    except Exception:
        pass
    # X 아이콘 (✖) 닫기 버튼
    try:
        x_icon = page.locator(".popup_close, .pop_close, [class*='popup'] [class*='close'], .layerPopup .close").first
        if x_icon.is_visible(timeout=1500):
            x_icon.click()
            print(f"   📢 {desc} 닫기 완료! (아이콘)")
            time.sleep(0.5)
            return True
    except Exception:
        pass
    return False


def login_to_wpps():
    """WPPS 로그인 후 page 객체 반환"""
    pw, browser, page = create_browser()
    try:
        print(f"🌐 로그인 페이지 이동...")
        page.goto(LOGIN_URL, wait_until="networkidle")

        # 팝업 닫기
        close_popup(page, "로그인 팝업")
        time.sleep(1)

        # 아이디 입력 (type: 한 글자씩 = JS 이벤트 발생 = 사이트 인식 OK)
        id_field = page.locator("input#loginId")
        id_field.click()
        id_field.fill("")
        id_field.type(WPPS_USER_ID)
        print(f"⌨️  아이디 입력: [{WPPS_USER_ID}]")

        # 비밀번호 입력
        pw_field = page.locator("input#password")
        pw_field.click()
        pw_field.fill("")
        pw_field.type(WPPS_PASSWORD)
        print(f"🔑 비밀번호 입력 완료 ({len(WPPS_PASSWORD)}글자)")

        # 로그인 버튼 클릭
        print("🖱️  로그인 버튼 클릭!")
        page.locator("button.btn_login").click()

        # URL이 /ps/로 변경될 때까지 명시적 대기 (최대 15초)
        # Why wait_for_url?: sleep+networkidle보다 정확. URL이 바뀌어야 성공
        page.wait_for_url("**/ps/**", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)

        if "/ps/" not in page.url:
            print(f"❌ 로그인 실패! URL: {page.url}")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "login_failed.png"))
            browser.close(); pw.stop()
            return None, None, None

        print(f"✅ 로그인 성공! → {page.url}")

        # 메인 페이지 팝업 닫기
        close_popup(page, "공지사항 팝업")
        close_popup(page, "추가 팝업")

        return pw, browser, page

    except Exception as e:
        print(f"⚠️ 오류: {e}")
        browser.close(); pw.stop()
        return None, None, None


def go_to_shipment_registration(page):
    """출하통보등록 메뉴로 이동"""
    print("\n📂 입출고관리 → 출하통보등록 이동...")

    # 입출고관리 메뉴 펼치기
    try:
        page.locator("text=입출고관리").first.click()
        time.sleep(1)
    except Exception:
        pass

    # 출하통보등록 클릭
    page.locator("text=출하통보등록").first.click()
    page.wait_for_load_state("networkidle", timeout=10000)
    time.sleep(1)
    print("   ✅ 출하통보등록 페이지 도착!")

    # 팝업 닫기 (3단계 시도)
    print("🔄 팝업 처리 중...")

    # 방법 1: 일반 셀렉터 시도
    close_popup(page, "출하통보등록 팝업")

    # 방법 2: iframe 내부의 #popupBtnClose 클릭 시도
    try:
        for frame in page.frames:
            try:
                btn = frame.locator("#popupBtnClose")
                if btn.is_visible(timeout=2000):
                    btn.click()
                    print("   📢 iframe 내 #popupBtnClose 클릭 성공!")
                    time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass

    # 방법 3: JavaScript로 팝업/오버레이 강제 제거
    try:
        page.evaluate("""
            // 모든 팝업 관련 요소 숨기기
            document.querySelectorAll('[class*="popup"], [class*="modal"], [class*="layer"]').forEach(el => {
                if (el.style) el.style.display = 'none';
            });
            // 오버레이/딤 배경 제거
            document.querySelectorAll('[class*="dim"], [class*="overlay"], [class*="mask"]').forEach(el => {
                if (el.style) el.style.display = 'none';
            });
        """)
        print("   📢 JS로 팝업/오버레이 강제 제거 완료!")
    except Exception:
        pass

    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "shipment_registration.png"))
    print(f"📸 스크린샷 저장 완료")
    return page


if __name__ == "__main__":
    if not WPPS_PASSWORD:
        print("🚨 .env에 WPPS_PW 없음!")
    else:
        print("🚀 WPPS 자동화 봇 시작!")
        print("=" * 50)

        pw, browser, page = login_to_wpps()
        if page:
            page = go_to_shipment_registration(page)
            print("\n🏁 출하통보등록 페이지 도착! 화면을 확인해주세요.")
            input("⏸️  Enter → 브라우저 닫기...")
            browser.close(); pw.stop()
        else:
            print("❌ 로그인 실패")
