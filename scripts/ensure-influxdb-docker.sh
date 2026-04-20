#!/usr/bin/env bash
# InfluxDB Docker 컨테이너 기동. 헬스 체크 실패 시 한 번 재시작 후 다시 대기.
# PLC_INFLUX_SKIP=1 이면 건너뜀. 컨테이너 이름은 PLC_INFLUX_DOCKER_NAME (기본 plc_influxdb).

PLC_INFLUX_DOCKER_NAME="${PLC_INFLUX_DOCKER_NAME:-plc_influxdb}"
PLC_INFLUX_HEALTH_URL="${PLC_INFLUX_HEALTH_URL:-http://127.0.0.1:8090/health}"

if [ "${PLC_INFLUX_SKIP:-}" = "1" ]; then
  echo "[InfluxDB Docker] 건너뜀 (PLC_INFLUX_SKIP=1)"
  exit 0
fi

if ! command -v docker &>/dev/null; then
  echo "[InfluxDB Docker] docker 없음 — 건너뜁니다."
  exit 0
fi

if ! docker info &>/dev/null; then
  echo "[InfluxDB Docker] Docker 데몬에 연결할 수 없음 — 건너뜁니다. (sudo usermod -aG docker \$USER 후 재로그인 등)"
  exit 0
fi

if ! docker inspect "$PLC_INFLUX_DOCKER_NAME" &>/dev/null; then
  echo "[InfluxDB Docker] 컨테이너 '$PLC_INFLUX_DOCKER_NAME' 없음 — 건너뜁니다."
  exit 0
fi

_influx_health_ok() {
  curl -sf --max-time 3 "$PLC_INFLUX_HEALTH_URL" >/dev/null 2>&1
}

echo "[InfluxDB Docker] $PLC_INFLUX_DOCKER_NAME 시작…"
docker start "$PLC_INFLUX_DOCKER_NAME" 2>/dev/null || true

for _ in $(seq 1 30); do
  if _influx_health_ok; then
    echo "[InfluxDB Docker] 준비됨 ($PLC_INFLUX_HEALTH_URL)"
    exit 0
  fi
  sleep 1
done

echo "[InfluxDB Docker] 헬스 실패 — 재시작 후 다시 확인합니다…"
docker restart "$PLC_INFLUX_DOCKER_NAME" 2>/dev/null || true
sleep 2

for _ in $(seq 1 25); do
  if _influx_health_ok; then
    echo "[InfluxDB Docker] 재시작 후 준비됨"
    exit 0
  fi
  sleep 1
done

echo "[InfluxDB Docker] 경고: $PLC_INFLUX_HEALTH_URL 응답 없음. 로그: docker logs $PLC_INFLUX_DOCKER_NAME"
exit 0
