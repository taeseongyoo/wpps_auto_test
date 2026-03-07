#!/bin/bash

# ============================================================
# 파일명: ubuntu_setup.sh
# 설명: AWS Ubuntu 서버용 WPPS 출하통보 봇 자동 세팅 스크립트
# 작성자: 안티그래비티 (LEO 비서 마리)
# ============================================================

# 에러 발생 시 즉시 중단
set -e

echo "🚀 [1/5] 시스템 패키지 업데이트 중..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "📦 [2/5] 서버 필수 패키지 설치 (Python 3 & venv)..."
sudo apt-get install -y python3 python3-venv python3-pip curl git

echo "🐍 [3/5] 파이썬 가상환경(venv) 생성 및 활성화..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "가상환경(venv)이 생성되었습니다."
fi
source venv/bin/activate

echo "📚 [4/5] 필수 파이썬 라이브러리 설치 (Playwright, python-dotenv, supabase)..."
pip install --upgrade pip
pip install playwright python-dotenv supabase

echo "🌐 [5/5] Playwright 크로미움 브라우저 및 OS 필수 종속성 설치..."
# 이 명령어가 우분투 환경에서 Headless 브라우저를 띄우기 위한 핵심입니다 (X11, libnss3 등 자동 설치)
playwright install chromium --with-deps

echo ""
echo "============================================================"
echo "✅ [완료] AWS Ubuntu 서버 세팅이 완벽하게 끝났습니다!"
echo "============================================================"
echo "이제 '.env' 파일을 서버에 복사(또는 생성)한 뒤 아래 명령어로 실행하세요:"
echo ""
echo "  source venv/bin/activate"
echo "  python3 wpps_auto_register.py"
echo "============================================================"
