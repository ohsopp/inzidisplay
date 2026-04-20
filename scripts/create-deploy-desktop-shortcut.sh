#!/usr/bin/env bash
# 바탕화면에 PLC모니터(배포).desktop 생성 (백엔드만 + Vercel 브라우저)
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

EXEC="$REPO_ROOT/PLC모니터-배포.sh"

DESKTOP=""
for candidate in "$XDG_DESKTOP_DIR" "$HOME/Desktop" "$HOME/바탕화면" "$HOME/desktop"; do
  [ -z "$candidate" ] && continue
  if [ -d "$candidate" ]; then
    DESKTOP="$candidate"
    break
  fi
done
[ -z "$DESKTOP" ] && DESKTOP="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
mkdir -p "$DESKTOP"

cat > "$DESKTOP/PLC모니터(배포).desktop" << EOF
[Desktop Entry]
Type=Application
Name=PLC 모니터 (배포)
Comment=InfluxDB Docker 자동 기동, 백엔드만 (http://localhost:6005). Vercel 브라우저 열기
Exec=$EXEC
Path=$REPO_ROOT
Terminal=true
Categories=Utility;
EOF
chmod +x "$DESKTOP/PLC모니터(배포).desktop"
gio set "$DESKTOP/PLC모니터(배포).desktop" metadata::trusted true 2>/dev/null || true

echo "바탕화면에 PLC모니터(배포).desktop 갱신"
