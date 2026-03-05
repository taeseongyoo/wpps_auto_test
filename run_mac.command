#!/bin/bash
# ============================================================
# 파일명: run_mac.command
# 설명: 맥(Mac) 직원용 원클릭 자동 실행 버튼 (더블클릭 실행)
# ============================================================

# 스크립트가 위치한 폴더로 이동 (더블클릭 실행 시 위치 문제 해결)
cd "$(dirname "$0")"

echo "[로지스올 출하통보 자동화 봇 - Mac용 시작]"
echo ""

# 1. 파이썬 확인
if ! command -v python3 &> /dev/null; then
    echo "[경고] 파이썬이 설치되어 있지 않습니다!"
    echo "파이썬을 먼저 설치해주세요."
    exit 1
fi

# 2. 가상환경 세팅 및 설치
if [ ! -d ".venv_mac" ]; then
    echo "1/3: 봇 실행을 위한 독립 환경(가상환경)을 건설 중입니다..."
    python3 -m venv .venv_mac
fi

echo "2/3: 필요한 부품(라이브러리)을 장착 중입니다..."
source .venv_mac/bin/activate
pip install -q playwright python-dotenv

echo "3/3: Playwright 자동화 브라우저 엔진을 설치 중입니다..."
PLAYWRIGHT_BROWSERS_PATH=0 playwright install chromium

# 3. 봇 실행
echo ""
echo "=============================================="
echo "🚀 WPPS 자동 등록 봇을 가동합니다!"
echo "=============================================="
python3 wpps_auto_register.py

echo ""
echo "작업을 성공적으로 마쳤습니다."
