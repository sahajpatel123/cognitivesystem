import os
from contextlib import suppress
from typing import Tuple

from .config import settings


def _database_url() -> str | None:
    return os.getenv("DATABASE_URL") or settings.database_url


def check_db_connection() -> Tuple[bool, str | None]:
    """
    Deterministic, fail-closed database connectivity check.
    Does not leak connection details; returns (ok, sanitized_reason_or_None).
    """
    url = _database_url()
    if not url:
        return False, "database_url_missing"

    try:
        import psycopg

        with suppress(Exception):
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    _ = cur.fetchone()
        return True, None
    except ModuleNotFoundError:
        return False, "psycopg_not_installed"
    except Exception:
        return False, "db_unreachable"
