from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

try:
    from backend.app.db.database import get_db_connection
except Exception:  # pragma: no cover
    get_db_connection = None  # type: ignore


@dataclass
class QuotaState:
    requests_count: int
    tokens_count: int
    reset_at: datetime

    def as_tuple(self) -> Tuple[int, int, datetime]:
        return self.requests_count, self.tokens_count, self.reset_at


def _today_window() -> tuple[date, datetime]:
    today = datetime.now(timezone.utc).date()
    reset_at = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return today, reset_at


def _connect():
    if get_db_connection is None:
        return None
    try:
        return get_db_connection()
    except Exception:
        return None


def _ensure_row(conn, subject_type: str, subject_id: str, window_date: date, reset_at: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO quotas (id, subject_type, subject_id, date, requests_count, tokens_count, reset_at)
            VALUES (%s, %s, %s, %s, 0, 0, %s)
            ON CONFLICT (subject_type, subject_id, date) DO NOTHING;
            """,
            (uuid.uuid4(), subject_type, subject_id, window_date, reset_at),
        )
    conn.commit()


def _fetch_state(conn, subject_type: str, subject_id: str, window_date: date) -> Optional[QuotaState]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT requests_count, tokens_count, reset_at
            FROM quotas
            WHERE subject_type = %s AND subject_id = %s AND date = %s;
            """,
            (subject_type, subject_id, window_date),
        )
        row = cur.fetchone()
        if row:
            return QuotaState(requests_count=row[0], tokens_count=row[1], reset_at=row[2])
    return None


def get_or_create_quota(subject_type: str, subject_id: str) -> Optional[QuotaState]:
    conn = _connect()
    if conn is None:
        return None
    window_date, reset_at = _today_window()
    try:
        _ensure_row(conn, subject_type, subject_id, window_date, reset_at)
        state = _fetch_state(conn, subject_type, subject_id, window_date)
        return state
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def increment_usage(subject_type: str, subject_id: str, requests_inc: int, tokens_inc: int) -> Optional[QuotaState]:
    conn = _connect()
    if conn is None:
        return None
    window_date, reset_at = _today_window()
    try:
        _ensure_row(conn, subject_type, subject_id, window_date, reset_at)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE quotas
                SET requests_count = requests_count + %s,
                    tokens_count = tokens_count + %s
                WHERE subject_type = %s AND subject_id = %s AND date = %s
                RETURNING requests_count, tokens_count, reset_at;
                """,
                (requests_inc, tokens_inc, subject_type, subject_id, window_date),
            )
            row = cur.fetchone()
        conn.commit()
        if row:
            return QuotaState(requests_count=row[0], tokens_count=row[1], reset_at=row[2])
        return None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def check_request_limit(subject_type: str, subject_id: str, limit: int) -> tuple[bool, Optional[QuotaState]]:
    state = get_or_create_quota(subject_type, subject_id)
    if state is None:
        return True, None
    if state.requests_count >= limit:
        return False, state
    return True, state


def check_token_budget(subject_type: str, subject_id: str, limit: int, incoming_tokens: int) -> tuple[bool, Optional[QuotaState]]:
    state = get_or_create_quota(subject_type, subject_id)
    if state is None:
        return True, None
    if state.tokens_count + incoming_tokens > limit:
        return False, state
    return True, state


__all__ = [
    "QuotaState",
    "get_or_create_quota",
    "increment_usage",
    "check_request_limit",
    "check_token_budget",
]
