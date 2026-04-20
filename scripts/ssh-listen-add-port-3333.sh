#!/usr/bin/env bash
# Ubuntu/Debian: ssh.socket 이 포트 22만 열고 있으면 sshd_config 의 Port 만으로 3333 이 안 열림.
# 사용: sudo bash scripts/ssh-listen-add-port-3333.sh

set -euo pipefail

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "root 로 실행: sudo bash $0" >&2
  exit 1
fi

DROP_IN_DIR=/etc/systemd/system/ssh.socket.d
DROP_IN="${DROP_IN_DIR}/listen-3333.conf"

mkdir -p "$DROP_IN_DIR"
cat >"$DROP_IN" <<'EOF'
# 22 외 3333 수신 (ListenStream= 로 유닛 기본 리슨 초기화 후 재지정)
[Socket]
ListenStream=
ListenStream=0.0.0.0:22
ListenStream=[::]:22
ListenStream=0.0.0.0:3333
ListenStream=[::]:3333
EOF

PORTS_CONF=/etc/ssh/sshd_config.d/99-extra-ports.conf
cat >"$PORTS_CONF" <<'EOF'
# scripts/ssh-listen-add-port-3333.sh
Port 22
Port 3333
EOF

sshd -t
systemctl daemon-reload
systemctl restart ssh.socket
systemctl restart ssh

echo "적용 완료."
ss -tlnp | grep -E 'sshd|:22|:3333' || ss -tlnp | grep -E ':22|:3333'
echo "테스트: ssh -p 3333 $(hostname -I | awk '{print $1}')"
echo "UFW 사용 시: sudo ufw allow 3333/tcp && sudo ufw reload"
