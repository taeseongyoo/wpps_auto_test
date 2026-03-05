#!/bin/bash
# ============================================================
# 파일명: build_app.sh
# 설명: WPPS 출하통보 자동화 봇 배포용 Mac App / Windows Exe 제작 스크립트
# ============================================================

echo "📦 배포용 프로그램 제작을 시작합니다..."

# Playwright 브라우저 바이너리 포함 빌드를 위한 설정
echo "1️⃣ Playwright 브라우저 바이너리 다운로드 확인..."
PLAYWRIGHT_BROWSERS_PATH=0 .venv/bin/playwright install chromium

echo "2️⃣ 기존 빌드 파일 정리..."
rm -rf build dist *.spec

echo "3️⃣ PyInstaller 패키징 시작..."
# --windowed: 콘솔 창 숨기기 (Mac에서는 .app 생성)
# --onefile: 하나의 파일로 만들기
# --add-data: .env 템플릿 파일 포함 (선택)
.venv/bin/pyinstaller --noconfirm --windowed --onefile \
    --name "WPPS_AutoBot" \
    --add-data ".env:." \
    wpps_auto_register.py

echo "✅ 빌드 완료! 'dist' 폴더를 확인하세요."
