#!/usr/bin/env bash
# 배포/운영용: Flask 백엔드(6005)만 기동. Vite·로컬 프론트는 사용하지 않음.
# 프론트는 Vercel 등에서 열면 됨. API URL이 이 머신의 6005를 가리키도록 설정되어 있어야 함.
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- InfluxDB (Docker): 기동 후 문제 시 한 번 재시작 ---
"$REPO_ROOT/scripts/ensure-influxdb-docker.sh"

BACKEND_DIR="$REPO_ROOT/backend"
VENV_DIR="$BACKEND_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-plc_test}"
export PGUSER="${PGUSER:-plc_app}"
export PGPASSWORD="${PGPASSWORD:-simpac}"

pkill -f "$BACKEND_DIR/launcher.py" 2>/dev/null || true
sleep 0.4

if ! command -v python3 &>/dev/null; then
  echo "오류: python3가 없습니다."
  exit 1
fi
if ! python3 -c "import venv" 2>/dev/null; then
  echo "오류: python3-venv가 필요합니다 (sudo apt install python3-venv)"
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "백엔드 환경을 처음 설정합니다..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip
  "$VENV_DIR/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"
else
  if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c "import sys" 2>/dev/null; then
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"
  elif ! "$VENV_PYTHON" -c "import pymcprotocol, psycopg, pyarrow" 2>/dev/null; then
    "$VENV_PYTHON" -m pip install --quiet -r "$BACKEND_DIR/requirements.txt"
  fi
fi

# launcher.py 가 6005 브라우저 자동 오픈하지 않게 (아래에서 Vercel 등만 연다)
export OPEN_BROWSER_FROM_SHELL=1

echo "백엔드만 시작: http://0.0.0.0:6005 (로컬: http://localhost:6005)"
"$VENV_PYTHON" "$BACKEND_DIR/launcher.py" &
SERVER_PID=$!
sleep 1.2

VERCEL_URL="${PLC_DEPLOY_OPEN_BROWSER:-https://inzidisplay-dashboard.vercel.app/}"
export DISPLAY="${DISPLAY:-:0}"
if [ -n "$VERCEL_URL" ] && [ "$VERCEL_URL" != "0" ]; then
  echo "브라우저: $VERCEL_URL"
  xdg-open "$VERCEL_URL" 2>/dev/null || gio open "$VERCEL_URL" 2>/dev/null || true
fi

wait $SERVER_PID
