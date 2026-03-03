#!/usr/bin/env bash
# Linux 단일 실행파일 빌드 (PyInstaller). 결과물: dist/PLC모니터
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== PLC 모니터 Linux 빌드 ==="

# 1) 프론트 빌드
echo ""
echo "[1/3] 프론트엔드 빌드..."
cd "$REPO_ROOT/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi
node node_modules/vite/bin/vite.js build
cd "$REPO_ROOT"

# 2) frontend_dist 복사
echo ""
echo "[2/3] backend/frontend_dist 복사..."
rm -rf "$REPO_ROOT/backend/frontend_dist"
cp -r "$REPO_ROOT/frontend/dist" "$REPO_ROOT/backend/frontend_dist"

# 3) PyInstaller (Linux 실행파일)
echo ""
echo "[3/3] PyInstaller 실행..."
pip install pyinstaller --quiet
pyinstaller --noconfirm backend/plc_app.spec

echo ""
echo "=== 완료 ==="
echo "실행 파일: $REPO_ROOT/dist/PLC모니터"
echo "더블클릭으로 실행하려면 scripts/create-desktop-shortcut.sh 로 바탕화면 바로가기를 만드세요."
