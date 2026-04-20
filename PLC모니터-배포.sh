#!/usr/bin/env bash
# 배포 프론트(Vercel)용: 백엔드(6005)만 기동. (원격 서버면 PLC모니터_배포.env 로 SSH 설정)
cd "$(dirname "$0")"
REPO_ROOT="$(pwd)"

./scripts/create-deploy-desktop-shortcut.sh 2>/dev/null || true

if [ -f "$REPO_ROOT/PLC모니터_배포.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$REPO_ROOT/PLC모니터_배포.env"
  set +a
fi

if [ -n "${PLC_DEPLOY_SSH_HOST:-}" ]; then
  CMD="${PLC_DEPLOY_REMOTE_CMD:-}"
  if [ -z "$CMD" ]; then
    echo "PLC_DEPLOY_SSH_HOST 가 설정됐는데 PLC_DEPLOY_REMOTE_CMD 가 없습니다."
    echo "PLC모니터_배포.env.example 을 참고해 원격에서 실행할 한 줄을 넣으세요."
    exit 1
  fi
  exec ssh ${PLC_DEPLOY_SSH_OPTS:-} "$PLC_DEPLOY_SSH_HOST" "bash -lc $(printf '%q' "$CMD")"
fi

exec "$REPO_ROOT/scripts/start-backend-only.sh"
