#!/usr/bin/env bash
# Inzi Nginx용 Let's Encrypt 발급 (HTTP-01 webroot)
#
# 사전 조건:
#   - sudo bash deploy/server-apply-inzidisplay-nginx.sh 를 한 번 실행해 nginx·80 ACME·snippet 이 있을 것
#   - 공유기: 외부 80/TCP → 이 PC (Let's Encrypt 가 http://도메인/.well-known/ 로 검증)
#
# 사용 (택 1 — sudo는 기본적으로 사용자 export 를 넘기지 않음):
#   A) 환경 유지:  export CERTBOT_EMAIL='you@example.com' INZI_LE_DOMAINS='inzi.duckdns.org'
#                 sudo -E bash deploy/issue-inzi-letsencrypt.sh
#   B) 한 줄:     sudo CERTBOT_EMAIL='you@example.com' INZI_LE_DOMAINS='inzi.duckdns.org' bash deploy/issue-inzi-letsencrypt.sh
#   C) 설정 파일:  echo "CERTBOT_EMAIL=you@example.com" | sudo tee /etc/inzi-certbot.env
#                 echo "INZI_LE_DOMAINS=inzi.duckdns.org" | sudo tee -a /etc/inzi-certbot.env
#                 sudo bash deploy/issue-inzi-letsencrypt.sh
#
# SAN에 여러 도메인을 넣으면 하나라도 실패하면 전체 발급이 실패합니다.
# iptime 무료 호스트는 상위 도메인 CAA로 Let's Encrypt가 막히는 경우가 많습니다.
#
# 이메일 없이(비권장): sudo bash deploy/issue-inzi-letsencrypt.sh
#
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "root 로 실행: sudo bash deploy/issue-inzi-letsencrypt.sh" >&2
  exit 1
fi

# sudo bash 만 쓰는 경우: export 가 root 로 안 넘어오면 /etc/inzi-certbot.env 로 보완
# (sudo -E 로 이미 설정된 키는 덮어쓰지 않음)
if [ -r /etc/inzi-certbot.env ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"; key="${key#"${key%%[![:space:]]*}"}"
    val="${val%"${val##*[![:space:]]}"}"; val="${val#"${val%%[![:space:]]*}"}"
    case "$key" in
      CERTBOT_EMAIL)    [ -z "${CERTBOT_EMAIL+x}" ]    && export CERTBOT_EMAIL="$val" ;;
      INZI_LE_DOMAINS)  [ -z "${INZI_LE_DOMAINS+x}" ]  && export INZI_LE_DOMAINS="$val" ;;
    esac
  done < /etc/inzi-certbot.env
fi

WEBROOT=/var/www/certbot
mkdir -p "$WEBROOT" /etc/nginx/snippets

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot 설치: apt-get update && apt-get install -y certbot" >&2
  exit 1
fi

EMAIL_ARGS=()
if [ -n "${CERTBOT_EMAIL:-}" ]; then
  EMAIL_ARGS=(--email "$CERTBOT_EMAIL")
else
  echo "경고: CERTBOT_EMAIL 없음 — --register-unsafely-without-email 사용" >&2
  if [ -n "${SUDO_USER:-}" ]; then
    echo "  (sudo 는 export 변수를 넘기지 않습니다. sudo -E … 또는 sudo CERTBOT_EMAIL=… … 또는 /etc/inzi-certbot.env 참고)" >&2
  fi
  EMAIL_ARGS=(--register-unsafely-without-email)
fi

nginx -t
systemctl reload nginx 2>/dev/null || true

# 공백 구분 FQDN 목록. 첫 번째 이름이 certbot live 디렉터리 이름이 됩니다.
INZI_LE_DOMAINS="${INZI_LE_DOMAINS:-inzi.duckdns.org uitsolutions.iptime.org}"
CERT_PRIMARY=""
DOMAIN_ARGS=()
for d in $INZI_LE_DOMAINS; do
  [ -z "$d" ] && continue
  DOMAIN_ARGS+=(-d "$d")
  [ -z "$CERT_PRIMARY" ] && CERT_PRIMARY="$d"
done
if [ "${#DOMAIN_ARGS[@]}" -eq 0 ]; then
  echo "INZI_LE_DOMAINS 가 비어 있습니다." >&2
  exit 1
fi

echo "Certbot 요청 도메인: $INZI_LE_DOMAINS" >&2

certbot certonly \
  --webroot -w "$WEBROOT" \
  "${DOMAIN_ARGS[@]}" \
  --non-interactive \
  --agree-tos \
  "${EMAIL_ARGS[@]}" \
  --keep-until-expiring

cat >/etc/nginx/snippets/inzi-display-ssl.conf <<EOF
ssl_certificate     /etc/letsencrypt/live/${CERT_PRIMARY}/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/${CERT_PRIMARY}/privkey.pem;
EOF

nginx -t
systemctl reload nginx

echo ""
echo "Let's Encrypt 적용 완료."
echo "  curl -sS https://${CERT_PRIMARY}:6006/api/health"
echo "  갱신: certbot renew --webroot -w $WEBROOT --deploy-hook 'systemctl reload nginx'"
