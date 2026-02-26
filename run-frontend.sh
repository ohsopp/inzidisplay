#!/usr/bin/env bash
# 프론트엔드만 실행 (포트 6173)
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

if ! command -v npm &>/dev/null; then
  echo "오류: npm이 없습니다. Node.js를 설치한 뒤 다시 실행하세요."
  exit 1
fi
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "오류: frontend/node_modules가 없습니다. 먼저: cd frontend && npm install"
  exit 1
fi

cd "$FRONTEND_DIR"
# npm run dev 시 .bin 래퍼가 ESM으로 로드되지 않는 환경 대비, Vite bin 직접 실행
exec node node_modules/vite/bin/vite.js
