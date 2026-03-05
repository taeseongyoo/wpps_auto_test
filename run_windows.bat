@echo off
chcp 65001 >nul
:: ============================================================
:: 파일명: run_windows.bat
:: 설명: 윈도우(Windows) 직원용 원클릭 자동 실행 버튼
:: ============================================================
echo [로지스올 출하통보 자동화 봇 - 윈도우용 시작]
echo.

:: 1. 파이썬 설치 여부 확인
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [경고] 파이썬이 설치되어 있지 않습니다!
    echo 파이썬을 먼저 설치해주세요 (https://www.python.org/downloads/)
    echo 설치 시 반드시 "Add Python to PATH"에 체크하셔야 합니다.
    pause
    exit /b
)

:: 2. 가상환경 세팅 및 패키지 설치
if not exist ".venv_win" (
    echo 1/3: 봇 실행을 위한 독립 환경(가상환경)을 건설 중입니다...
    python -m venv .venv_win
)

echo 2/3: 필요한 부품(라이브러리)을 장착 중입니다... 
call .venv_win\Scripts\activate
pip install -q playwright python-dotenv

echo 3/3: Playwright 자동화 브라우저 엔진을 설치 중입니다...
playwright install chromium

:: 3. 자동화 스크립트 실행
echo.
echo ==============================================
echo 🚀 WPPS 자동 등록 봇을 가동합니다!
echo ==============================================
python wpps_auto_register.py

echo.
echo 작업을 성공적으로 마쳤습니다.
pause
