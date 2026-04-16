"""
PostgreSQL 기반 설정 저장소.
- poll_rate_settings 테이블에 스레드별 폴링 주기(sec) 저장
- 앱 재시작 시 DB 값을 읽어 폴링 주기에 반영
"""
from __future__ import annotations

import os
from contextlib import contextmanager

try:
    import psycopg
except Exception:  # pragma: no cover - 의존성 누락 시 런타임 처리
    psycopg = None


POLL_RATE_KEYS = ("50ms", "1s")


def _build_connect_kwargs() -> dict:
    # POSTGRES_DSN 우선 사용. 없으면 표준 libpq 환경변수 사용.
    dsn = (os.environ.get("POSTGRES_DSN") or "").strip()
    if dsn:
        return {"conninfo": dsn}

    host = os.environ.get("PGHOST")
    port = os.environ.get("PGPORT")
    dbname = os.environ.get("PGDATABASE")
    user = os.environ.get("PGUSER")
    password = os.environ.get("PGPASSWORD")
    kwargs = {}
    if host:
        kwargs["host"] = host
    if port:
        kwargs["port"] = port
    if dbname:
        kwargs["dbname"] = dbname
    if user:
        kwargs["user"] = user
    if password:
        kwargs["password"] = password
    return kwargs


def postgres_enabled() -> bool:
    if psycopg is None:
        return False
    return bool(_build_connect_kwargs())


@contextmanager
def _connect():
    if psycopg is None:
        raise RuntimeError("psycopg가 설치되어 있지 않습니다.")
    kwargs = _build_connect_kwargs()
    if not kwargs:
        raise RuntimeError("PostgreSQL 접속 정보가 없습니다. POSTGRES_DSN 또는 PG* 환경변수를 설정하세요.")
    conn = psycopg.connect(**kwargs)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_postgres():
    """
    poll_rate_settings 테이블 생성.
    반환: (ok: bool, message: str)
    """
    if not postgres_enabled():
        return (False, "PostgreSQL 미설정(POSTGRES_DSN 또는 PG* 환경변수 필요)")
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS poll_rate_settings (
                        thread_key TEXT PRIMARY KEY,
                        interval_sec DOUBLE PRECISION NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
        return (True, "PostgreSQL 준비 완료")
    except Exception as e:
        return (False, str(e))


def load_poll_intervals() -> dict[str, float]:
    """
    DB에서 스레드별 폴링 주기(sec) 읽기.
    """
    if not postgres_enabled():
        return {}
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT thread_key, interval_sec FROM poll_rate_settings WHERE thread_key = ANY(%s)",
                (list(POLL_RATE_KEYS),),
            )
            rows = cur.fetchall() or []
    out = {}
    for key, sec in rows:
        try:
            out[str(key)] = float(sec)
        except Exception:
            continue
    return out


def save_poll_intervals(interval_map_sec: dict[str, float]):
    """
    DB에 스레드별 폴링 주기(sec) upsert.
    """
    if not postgres_enabled():
        raise RuntimeError("PostgreSQL 미설정 상태입니다.")
    if not interval_map_sec:
        return
    with _connect() as conn:
        with conn.cursor() as cur:
            for key, sec in interval_map_sec.items():
                if key not in POLL_RATE_KEYS:
                    continue
                cur.execute(
                    """
                    INSERT INTO poll_rate_settings (thread_key, interval_sec, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (thread_key)
                    DO UPDATE SET interval_sec = EXCLUDED.interval_sec, updated_at = NOW()
                    """,
                    (key, float(sec)),
                )
