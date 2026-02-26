#!/usr/bin/env bash
# 백엔드만 실행 (포트 6005)
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

BACKEND_DIR="$REPO_ROOT/backend"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"

# 포트 6005 사용 중이면 종료
if command -v lsof &>/dev/null; then
  pids=$(lsof -ti ":6005" 2>/dev/null) || true
  if [ -n "$pids" ]; then
    echo "기존 프로세스 종료 중 (포트 6005)..."
    echo "$pids" | xargs -r kill 2>/dev/null || true
    sleep 1
  fi
fi

# venv가 다른 OS/아키텍처에서 만들어진 경우 실행 불가이므로 python3 사용
if [ -x "$VENV_PYTHON" ] && "$VENV_PYTHON" -c "import sys" 2>/dev/null; then
  exec "$VENV_PYTHON" "$BACKEND_DIR/app.py"
else
  exec python3 "$BACKEND_DIR/app.py"
fi
