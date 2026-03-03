#!/usr/bin/env bash
cd "$(dirname "$0")"
# 매번 바탕화면 .desktop 갱신 (절대경로라 더블클릭하면 웹 열림)
./scripts/create-desktop-shortcut.sh 2>/dev/null || true
exec ./scripts/start.sh
