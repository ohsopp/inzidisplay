#!/usr/bin/env bash
# PLC_test 프론트엔드/백엔드 실행을 위한 환경 세팅 (실행은 하지 않음)
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== PLC_test 환경 세팅 ==="

# --- 백엔드 (Python venv + pip) ---
echo ""
echo "[1/2] 백엔드 환경 세팅..."
if ! command -v python3 &>/dev/null; then
  echo "오류: python3가 설치되어 있지 않습니다. Python 3.8+를 설치한 뒤 다시 실행하세요."
  exit 1
fi

# Debian/Ubuntu: venv 생성에 python3-venv 필요
if ! python3 -c "import venv" 2>/dev/null; then
  echo "오류: python3-venv가 없습니다. 다음으로 설치한 뒤 다시 실행하세요:"
  echo "  sudo apt install python3-venv   # 또는 sudo apt install python3.12-venv"
  exit 1
fi

BACKEND_DIR="$REPO_ROOT/backend"
VENV_DIR="$BACKEND_DIR/venv"

# 기존 venv가 다른 머신(예: macOS)에서 만들어진 경우 재생성
if [ -d "$VENV_DIR" ]; then
  PY_IN_VENV="$VENV_DIR/bin/python"
  if [ -x "$PY_IN_VENV" ] && "$PY_IN_VENV" -c "import sys; sys.exit(0)" 2>/dev/null; then
    echo "  기존 venv 사용: $VENV_DIR"
  else
    echo "  기존 venv가 현재 환경과 맞지 않아 재생성합니다."
    rm -rf "$VENV_DIR"
  fi
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "  venv 생성 중: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "  pip 의존성 설치 중..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"
echo "  백엔드 세팅 완료. 실행: cd backend && source venv/bin/activate && python app.py"

# --- 프론트엔드 (Node/npm) ---
echo ""
echo "[2/2] 프론트엔드 환경 세팅..."
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
  echo "  경고: node 또는 npm이 없어 프론트엔드 의존성을 설치하지 못했습니다."
  echo "  Node.js 18+ 및 npm을 설치한 뒤 아래를 실행하세요:"
  echo "    cd $REPO_ROOT/frontend && npm install"
  echo "  실행: cd frontend && npm run dev"
  exit 0
fi

FRONTEND_DIR="$REPO_ROOT/frontend"
echo "  npm 의존성 설치 중..."
(cd "$FRONTEND_DIR" && npm install --no-audit --no-fund)
echo "  프론트엔드 세팅 완료. 실행: cd frontend && npm run dev"

echo ""
echo "=== 환경 세팅이 완료되었습니다. ==="
echo "  백엔드: cd backend && source venv/bin/activate && python app.py"
echo "  프론트엔드: cd frontend && npm run dev"
