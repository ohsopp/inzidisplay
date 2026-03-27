"""
Gunicorn 설정 — 실제 서버 배포용.
- bind: 127.0.0.1:8000 (Nginx가 이 주소로 프록시. 8000 사용 중이면 8001 등으로 변경)
- workers: 1 (앱이 프로세스 전역 상태/SSE 큐를 사용하므로 멀티워커 비권장)
- timeout: 120 (SSE 장기 연결 허용)
- chdir: backend 디렉터리
- wsgi_app: app:app
"""
import multiprocessing
import os

# 프로젝트 백엔드 루트 (이 설정 파일이 있는 디렉터리)
_chdir = os.path.dirname(os.path.abspath(__file__))

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
chdir = _chdir
wsgi_app = "app:app"

# app.py는 프로세스 전역 메모리(mc_thread/client_queues)를 사용하므로 기본은 1워커 고정.
# 필요 시 Redis/pubsub 등 외부 상태 저장소로 전환 후 멀티워커 확장 권장.
workers = int(os.environ.get("GUNICORN_WORKERS", 1))
# SSE 연결(/api/events)은 연결당 스레드 1개를 장시간 점유하므로 여유 스레드가 필수.
# 기본 64로 상향해 스레드 고갈(health/API 타임아웃) 가능성을 줄인다.
threads = int(os.environ.get("GUNICORN_THREADS", 64))
worker_class = "gthread"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5

# 로그: 프로젝트 내 logs 또는 /var/log
_log_dir = os.environ.get("GUNICORN_LOG_DIR", os.path.join(_chdir, "logs"))
os.makedirs(_log_dir, exist_ok=True)
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", os.path.join(_log_dir, "gunicorn_access.log"))
errorlog = os.environ.get("GUNICORN_ERROR_LOG", os.path.join(_log_dir, "gunicorn_error.log"))
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True

# 프로세스 이름
proc_name = "plc-backend"
