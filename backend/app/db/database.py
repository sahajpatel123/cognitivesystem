from __future__ import annotations

import os
import time
from contextlib import suppress
from typing import Any, Iterable, Optional

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore


DB_CONNECT_TIMEOUT = 3  # seconds


def _database_url(env: Optional[dict[str, str]] = None) -> str | None:
    env_map = env or os.environ
    return env_map.get("DATABASE_URL")


def get_db_connection():
    """
    Return a psycopg connection using DATABASE_URL.
    Raises ModuleNotFoundError if psycopg is missing.
    Raises Exception on connection errors.
    """
    url = _database_url()
    if not url:
        raise RuntimeError("DATABASE_URL not configured")
    if psycopg is None:
        raise ModuleNotFoundError("psycopg not installed")
    return psycopg.connect(url, connect_timeout=DB_CONNECT_TIMEOUT)


def check_db_connection() -> tuple[bool, str | None]:
    """
    Deterministic, fail-closed database connectivity check.
    Does not leak connection details; returns (ok, sanitized_reason_or_None).
    """
    url = _database_url()
    if not url:
        return False, "database_url_missing"
    if psycopg is None:
        return False, "psycopg_not_installed"
    try:
        with psycopg.connect(url, connect_timeout=DB_CONNECT_TIMEOUT) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                _ = cur.fetchone()
        return True, None
    except Exception:
        return False, "db_unreachable"


def cleanup_expired_records(now_ts: Optional[float] = None) -> dict[str, int]:
    """
    Best-effort cleanup for TTL tables. Returns counts of deleted rows per table.
    If DB is not configured or psycopg missing, returns empty dict.
    """
    url = _database_url()
    if not url or psycopg is None:
        return {}
    ts = int(now_ts or time.time())
    deleted: dict[str, int] = {}
    statements: dict[str, tuple[str, Iterable[Any]]] = {
        "sessions": ("DELETE FROM sessions WHERE expires_at <= to_timestamp(%s);", (ts,)),
        "invocation_logs": (
            "DELETE FROM invocation_logs WHERE ts <= (NOW() - INTERVAL '14 days');",
            (),
        ),
        "rate_limits": (
            "DELETE FROM rate_limits WHERE blocked_until IS NOT NULL AND blocked_until <= NOW();",
            (),
        ),
        "quotas": (
            "DELETE FROM quotas WHERE reset_at IS NOT NULL AND reset_at <= NOW();",
            (),
        ),
    }
    with suppress(Exception):
        with psycopg.connect(url, connect_timeout=DB_CONNECT_TIMEOUT) as conn:
            with conn.cursor() as cur:
                for table, (sql, params) in statements.items():
                    cur.execute(sql, params)
                    deleted[table] = cur.rowcount or 0
            conn.commit()
    return deleted
