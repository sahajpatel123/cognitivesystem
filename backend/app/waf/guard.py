from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import Depends, Request

from backend.app.auth.identity import IdentityContext
from backend.app.deps.identity import identity_dependency

try:
    from backend.app.db.database import get_db_connection
except Exception:  # pragma: no cover
    get_db_connection = None  # type: ignore


# Environment-driven WAF settings
WAF_MAX_BODY_BYTES = int(os.getenv("WAF_MAX_BODY_BYTES", "200000"))
WAF_MAX_USER_TEXT_CHARS = int(os.getenv("WAF_MAX_USER_TEXT_CHARS", "8000"))

WAF_IP_BURST_LIMIT = int(os.getenv("WAF_IP_BURST_LIMIT", "5"))
WAF_IP_BURST_WINDOW_SECONDS = int(os.getenv("WAF_IP_BURST_WINDOW_SECONDS", "10"))
WAF_IP_SUSTAIN_LIMIT = int(os.getenv("WAF_IP_SUSTAIN_LIMIT", "60"))
WAF_IP_SUSTAIN_WINDOW_SECONDS = int(os.getenv("WAF_IP_SUSTAIN_WINDOW_SECONDS", "60"))

WAF_SUBJECT_BURST_LIMIT = int(os.getenv("WAF_SUBJECT_BURST_LIMIT", "8"))
WAF_SUBJECT_BURST_WINDOW_SECONDS = int(os.getenv("WAF_SUBJECT_BURST_WINDOW_SECONDS", "10"))
WAF_SUBJECT_SUSTAIN_LIMIT = int(os.getenv("WAF_SUBJECT_SUSTAIN_LIMIT", "120"))
WAF_SUBJECT_SUSTAIN_WINDOW_SECONDS = int(os.getenv("WAF_SUBJECT_SUSTAIN_WINDOW_SECONDS", "60"))

_lockout_schedule_raw = os.getenv("WAF_LOCKOUT_SCHEDULE_SECONDS", "30,120,600,3600")
WAF_LOCKOUT_SCHEDULE_SECONDS = tuple(
    s for s in (int(x) for x in _lockout_schedule_raw.split(",") if x.strip()) if s > 0
) or (30, 120, 600, 3600)
WAF_LOCKOUT_COOLDOWN_SECONDS = int(os.getenv("WAF_LOCKOUT_COOLDOWN_SECONDS", "21600"))

WAF_ENFORCE_ROUTES = {p.strip() for p in os.getenv("WAF_ENFORCE_ROUTES", "/api/chat").split(",") if p.strip()}

_HASH_SALT = os.getenv("IDENTITY_HASH_SALT", "dev-salt").encode("utf-8")


class WAFError(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        retry_after_seconds: Optional[int] = None,
        limit_scope: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.retry_after_seconds = retry_after_seconds
        self.limit_scope = limit_scope
        super().__init__(message)

    def to_body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "ok": False,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.retry_after_seconds is not None:
            body["retry_after_seconds"] = self.retry_after_seconds
        if self.limit_scope:
            body["limit_scope"] = self.limit_scope
        return body

    def to_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.retry_after_seconds is not None:
            headers["Retry-After"] = str(self.retry_after_seconds)
        return headers


def _hash_value(value: str) -> str:
    h = hashlib.sha256()
    h.update(_HASH_SALT)
    h.update(value.encode("utf-8"))
    return h.hexdigest()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@dataclass
class RateKey:
    scope: str  # "ip" or "subject"
    value: str

    def hashed(self) -> "RateKey":
        if self.scope == "ip":
            return RateKey(scope=self.scope, value=_hash_value(self.value))
        return self


@dataclass
class LimitWindow:
    limit: int
    window_seconds: int


# In-memory fallback limiter (per-process)
_mem_windows: Dict[Tuple[str, str, int, int], int] = {}
_mem_locks: Dict[Tuple[str, str], Tuple[int, float]] = {}


def _now() -> float:
    return time.time()


def _db_conn():
    if get_db_connection is None:
        return None
    try:
        return get_db_connection()
    except Exception:
        return None


def _floor_window(ts: float, window: int) -> float:
    return ts - (ts % window)


def _get_lockout_db(conn, key: RateKey, now_ts: float) -> Optional[float]:
    window_start = datetime.fromtimestamp(_floor_window(now_ts, 86400), tz=timezone.utc)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT blocked_until, hits FROM rate_limits
                WHERE subject_type = %s AND subject_id = %s AND window_start = %s AND window_seconds = 0;
                """,
                (key.scope, key.hashed().value, window_start),
            )
            row = cur.fetchone()
            if not row:
                return None
            blocked_until, strikes = row
            if blocked_until and blocked_until > datetime.now(timezone.utc):
                return blocked_until.timestamp()
            if blocked_until and (datetime.now(timezone.utc) - blocked_until).total_seconds() > WAF_LOCKOUT_COOLDOWN_SECONDS:
                with conn.cursor() as cur2:
                    cur2.execute(
                        """
                        UPDATE rate_limits
                        SET hits = 0, blocked_until = NULL
                        WHERE subject_type = %s AND subject_id = %s AND window_start = %s AND window_seconds = 0;
                        """,
                        (key.scope, key.hashed().value, window_start),
                    )
                conn.commit()
            return None
    except Exception:
        return None


def _set_lockout_db(conn, key: RateKey, now_ts: float) -> Optional[Tuple[int, float]]:
    window_start = datetime.fromtimestamp(_floor_window(now_ts, 86400), tz=timezone.utc)
    strikes = 1
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rate_limits (id, subject_type, subject_id, window_start, window_seconds, hits, blocked_until)
                VALUES (%s, %s, %s, %s, 0, 1, %s)
                ON CONFLICT (subject_type, subject_id, window_start, window_seconds)
                DO UPDATE SET
                    hits = CASE
                        WHEN EXTRACT(EPOCH FROM (NOW() - COALESCE(rate_limits.blocked_until, NOW()))) > %s THEN 1
                        ELSE rate_limits.hits + 1
                    END,
                    blocked_until = NOW()
                RETURNING hits;
                """,
                (
                    uuid.uuid4(),
                    key.scope,
                    key.hashed().value,
                    window_start,
                    datetime.fromtimestamp(now_ts, tz=timezone.utc),
                    WAF_LOCKOUT_COOLDOWN_SECONDS,
                ),
            )
            row = cur.fetchone()
            strikes = int(row[0]) if row else 1
        conn.commit()
        idx = min(strikes - 1, len(WAF_LOCKOUT_SCHEDULE_SECONDS) - 1)
        duration = WAF_LOCKOUT_SCHEDULE_SECONDS[idx]
        blocked_until_ts = now_ts + duration
        blocked_until_dt = datetime.fromtimestamp(blocked_until_ts, tz=timezone.utc)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rate_limits
                SET blocked_until = %s
                WHERE subject_type = %s AND subject_id = %s AND window_start = %s AND window_seconds = 0;
                """,
                (blocked_until_dt, key.scope, key.hashed().value, window_start),
            )
        conn.commit()
        return strikes, blocked_until_ts
    except Exception:
        return None


def _increment_window_db(conn, key: RateKey, window: LimitWindow, now_ts: float) -> int:
    window_start = datetime.fromtimestamp(_floor_window(now_ts, window.window_seconds), tz=timezone.utc)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rate_limits (id, subject_type, subject_id, window_start, window_seconds, hits)
                VALUES (%s, %s, %s, %s, %s, 1)
                ON CONFLICT (subject_type, subject_id, window_start, window_seconds)
                DO UPDATE SET hits = rate_limits.hits + 1
                RETURNING hits;
                """,
                (uuid.uuid4(), key.scope, key.hashed().value, window_start, window.window_seconds),
            )
            row = cur.fetchone()
            hits = int(row[0]) if row else 1
        conn.commit()
        return hits
    except Exception:
        return 0


def _increment_window_mem(key: RateKey, window: LimitWindow, now_ts: float) -> int:
    hashed = key.hashed().value
    bucket = int(_floor_window(now_ts, window.window_seconds))
    k = (key.scope, hashed, window.window_seconds, bucket)
    hits = _mem_windows.get(k, 0) + 1
    _mem_windows[k] = hits
    return hits


def _apply_lockout_mem(key: RateKey, now_ts: float) -> int:
    hashed = key.hashed().value
    strikes, last_blocked = _mem_locks.get((key.scope, hashed), (0, now_ts))
    if now_ts - last_blocked > WAF_LOCKOUT_COOLDOWN_SECONDS:
        strikes = 0
    strikes += 1
    idx = min(strikes - 1, len(WAF_LOCKOUT_SCHEDULE_SECONDS) - 1)
    duration = WAF_LOCKOUT_SCHEDULE_SECONDS[idx]
    blocked_until = now_ts + duration
    _mem_locks[(key.scope, hashed)] = (strikes, blocked_until)
    return strikes


def _check_lockout_mem(key: RateKey, now_ts: float) -> Optional[float]:
    hashed = key.hashed().value
    strikes, blocked_until = _mem_locks.get((key.scope, hashed), (0, 0.0))
    if blocked_until > now_ts:
        return blocked_until
    if blocked_until and (now_ts - blocked_until) > WAF_LOCKOUT_COOLDOWN_SECONDS:
        _mem_locks.pop((key.scope, hashed), None)
    return None


def _rate_check(key: RateKey, windows: tuple[LimitWindow, LimitWindow], now_ts: float) -> Tuple[bool, Optional[int], bool]:
    conn = _db_conn()
    used_memory = conn is None

    locked = _get_lockout_db(conn, key, now_ts) if conn else _check_lockout_mem(key, now_ts)
    if locked and locked > now_ts:
        return False, int(max(1, locked - now_ts)), used_memory

    for window in windows:
        if window.limit <= 0 or window.window_seconds <= 0:
            continue
        hits = _increment_window_db(conn, key, window, now_ts) if conn else _increment_window_mem(key, window, now_ts)
        if hits > window.limit:
            if conn:
                result = _set_lockout_db(conn, key, now_ts)
                if result is None:
                    strikes = 1
                    blocked_until_ts = now_ts + WAF_LOCKOUT_SCHEDULE_SECONDS[-1]
                else:
                    strikes, blocked_until_ts = result
            else:
                strikes = _apply_lockout_mem(key, now_ts)
                blocked_until_ts = now_ts + WAF_LOCKOUT_SCHEDULE_SECONDS[min(strikes - 1, len(WAF_LOCKOUT_SCHEDULE_SECONDS) - 1)]
            idx = min(strikes - 1, len(WAF_LOCKOUT_SCHEDULE_SECONDS) - 1)
            retry_after = int(max(1, blocked_until_ts - now_ts)) if blocked_until_ts else WAF_LOCKOUT_SCHEDULE_SECONDS[idx]
            return False, retry_after, used_memory
    return True, None, used_memory


async def waf_dependency(request: Request, identity: IdentityContext = Depends(identity_dependency)) -> IdentityContext:
    # Path scoping
    if request.url.path not in WAF_ENFORCE_ROUTES:
        return identity

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise WAFError(415, "content_type_invalid", "Content-Type must be application/json")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > WAF_MAX_BODY_BYTES:
                raise WAFError(413, "payload_too_large", "Payload exceeds maximum size.")
        except ValueError:
            raise WAFError(400, "invalid_content_length", "Invalid Content-Length header.")

    body = await request.body()
    if len(body) > WAF_MAX_BODY_BYTES:
        raise WAFError(413, "payload_too_large", "Payload exceeds maximum size.")

    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError:
        raise WAFError(400, "invalid_json", "Request body must be valid JSON.")

    if not isinstance(payload, dict) or "user_text" not in payload:
        raise WAFError(400, "invalid_payload", "user_text is required.")

    user_text = payload.get("user_text")
    if not isinstance(user_text, str):
        raise WAFError(400, "invalid_payload", "user_text must be a string.")
    if len(user_text) > WAF_MAX_USER_TEXT_CHARS:
        raise WAFError(413, "user_text_too_long", "user_text exceeds maximum length.")

    now_ts = _now()

    # Rate limiting by IP
    ip_key = RateKey(scope="ip", value=_client_ip(request))
    ip_windows = (
        LimitWindow(WAF_IP_BURST_LIMIT, WAF_IP_BURST_WINDOW_SECONDS),
        LimitWindow(WAF_IP_SUSTAIN_LIMIT, WAF_IP_SUSTAIN_WINDOW_SECONDS),
    )
    ip_allowed, ip_retry, ip_used_mem = _rate_check(ip_key, ip_windows, now_ts)
    if ip_used_mem:
        request.state.waf_used_memory = True
    if not ip_allowed:
        raise WAFError(429, "rate_limited", "Too many requests from IP.", retry_after_seconds=ip_retry, limit_scope="ip")

    # Rate limiting by subject (if present)
    if identity and identity.subject_id:
        subject_key = RateKey(scope=identity.subject_type, value=identity.subject_id)
        subject_windows = (
            LimitWindow(WAF_SUBJECT_BURST_LIMIT, WAF_SUBJECT_BURST_WINDOW_SECONDS),
            LimitWindow(WAF_SUBJECT_SUSTAIN_LIMIT, WAF_SUBJECT_SUSTAIN_WINDOW_SECONDS),
        )
        sub_allowed, sub_retry, sub_used_mem = _rate_check(subject_key, subject_windows, now_ts)
        if sub_used_mem:
            request.state.waf_used_memory = True
        if not sub_allowed:
            raise WAFError(
                429,
                "rate_limited",
                "Too many requests for this subject.",
                retry_after_seconds=sub_retry,
                limit_scope="subject",
            )

    return identity


__all__ = ["waf_dependency", "WAFError"]
