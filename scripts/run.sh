#!/usr/bin/env bash
# 프론트엔드·백엔드 동시 실행 (백그라운드)
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"

# 백엔드
if [ ! -x "$VENV_PYTHON" ]; then
  echo "백엔드 venv가 없습니다. 먼저 ./scripts/setup.sh 를 실행하세요."
  exit 1
fi
echo "백엔드 시작 (포트 6005)..."
"$VENV_PYTHON" "$BACKEND_DIR/app.py" &
BACKEND_PID=$!

# 프론트엔드
if ! command -v npm &>/dev/null; then
  echo "npm이 없습니다. Node.js 설치 후 다시 실행하세요. 백엔드만 PID $BACKEND_PID 로 실행 중."
  exit 1
fi
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "프론트엔드 node_modules가 없습니다. 먼저 ./scripts/setup.sh 를 실행하세요."
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi
echo "프론트엔드 시작 (포트 6173)..."
(cd "$FRONTEND_DIR" && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "실행 중입니다."
echo "  백엔드:  http://localhost:6005  (PID $BACKEND_PID)"
echo "  프론트:  http://localhost:6173  (PID $FRONTEND_PID)"
echo "종료: kill $BACKEND_PID $FRONTEND_PID"
