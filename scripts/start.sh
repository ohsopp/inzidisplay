#!/usr/bin/env bash
# 한 번에 실행: 필요하면 venv·npm·프론트 빌드까지 자동으로 한 뒤 서버 + 브라우저
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
VENV_DIR="$BACKEND_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
FRONTEND_DIST="$BACKEND_DIR/frontend_dist"

# --- 1) Python/venv 필수 (없으면 안내만) ---
if ! command -v python3 &>/dev/null; then
  echo "오류: python3가 없습니다. Python 3.8+ 를 설치한 뒤 다시 실행하세요."
  exit 1
fi
if ! python3 -c "import venv" 2>/dev/null; then
  echo "오류: python3-venv가 없습니다. 터미널에서 다음을 실행한 뒤 다시 시도하세요:"
  echo "  sudo apt install python3-venv"
  exit 1
fi

# --- 2) 백엔드 venv 없으면 만들고 pip 설치 ---
if [ ! -d "$VENV_DIR" ]; then
  echo "백엔드 환경을 처음 설정합니다 (한 번만)..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip
  "$VENV_DIR/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"
  echo "백엔드 설정 완료."
else
  # venv 있지만 실행이 안 되면(다른 머신에서 만든 경우 등) 재생성
  if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c "import sys" 2>/dev/null; then
    echo "백엔드 환경을 다시 설정합니다..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"
    echo "백엔드 설정 완료."
  fi
fi

# --- 3) frontend_dist 없으면 npm 설치 + 빌드 ---
if [ ! -d "$FRONTEND_DIST" ] || [ ! -f "$FRONTEND_DIST/index.html" ]; then
  if ! command -v npm &>/dev/null; then
    echo "오류: npm이 없습니다. Node.js 를 설치한 뒤 다시 실행하세요."
    exit 1
  fi
  echo "프론트엔드 준비 중 (한 번만)..."
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    (cd "$FRONTEND_DIR" && npm install --no-audit --no-fund)
  fi
  (cd "$FRONTEND_DIR" && node node_modules/vite/bin/vite.js build)
  rm -rf "$FRONTEND_DIST"
  cp -r "$FRONTEND_DIR/dist" "$FRONTEND_DIST"
  echo "프론트엔드 준비 완료."
fi

# --- 4) 서버 실행 + 브라우저 열기 ---
echo "PLC 모니터 시작 (http://localhost:6005)..."
export OPEN_BROWSER_FROM_SHELL=1
"$VENV_PYTHON" "$BACKEND_DIR/launcher.py" &
SERVER_PID=$!
sleep 2.5
# .desktop으로 실행 시 DISPLAY가 비어 있을 수 있음
export DISPLAY="${DISPLAY:-:0}"
echo "브라우저 열기 시도 중..."
if ! xdg-open "http://localhost:6005" 2>/dev/null; then
  gio open "http://localhost:6005" 2>/dev/null || true
fi
echo "안 열리면 브라우저에 직접 입력: http://localhost:6005"
wait $SERVER_PID
