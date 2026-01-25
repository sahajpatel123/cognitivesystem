from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Optional

_MAX_KEYS = 10_000

_PLAN_LIMITS = {
    "free": {"rpm": 20, "concurrency": 2, "max_output_cap": 256},
    "pro": {"rpm": 60, "concurrency": 4, "max_output_cap": 512},
    "max": {"rpm": 120, "concurrency": 8, "max_output_cap": 1024},
}

_buckets: dict[str, dict] = {}
_in_flight: dict[str, dict] = {}


@dataclass
class QuotaDecision:
    allowed: bool
    status_code: int
    retry_after_s: Optional[int]
    reason_code: str
    effective_output_cap: Optional[int]


@dataclass
class QuotaContext:
    plan: str
    actor_key: str
    ip_hash: str
    est_input_tokens: int
    est_output_cap: int
    now_monotonic: float


def _evict_if_needed(store: dict) -> None:
    if len(store) <= _MAX_KEYS:
        return
    oldest_key = None
    oldest_ts = None
    for key, meta in store.items():
        ts = meta.get("last_seen", 0)
        if oldest_ts is None or ts < oldest_ts:
            oldest_key = key
            oldest_ts = ts
    if oldest_key is not None:
        store.pop(oldest_key, None)


def _refill(tokens: float, limit_per_minute: int, now: float, last_updated: float) -> tuple[float, float]:
    rate_per_sec = float(limit_per_minute) / 60.0
    if now > last_updated:
        tokens = min(float(limit_per_minute), tokens + (now - last_updated) * rate_per_sec)
    return tokens, rate_per_sec


def _plan_config(plan: str) -> dict:
    return _PLAN_LIMITS.get((plan or "free").lower().strip(), _PLAN_LIMITS["free"])


def _force_block_enabled() -> bool:
    val = os.getenv("QUOTA_FORCE_BLOCK", "").lower().strip()
    return val in {"1", "true", "yes"}


def _retry_after_seconds(needed_tokens: float, rate_per_sec: float) -> int:
    if rate_per_sec <= 0:
        return 60
    return max(1, int(math.ceil(needed_tokens / rate_per_sec)))


def _touch_in_flight(actor_key: str, now: float, delta: int) -> None:
    meta = _in_flight.get(actor_key, {"count": 0, "last_seen": now})
    meta["count"] = max(0, meta.get("count", 0) + delta)
    meta["last_seen"] = now
    if meta["count"] <= 0:
        _in_flight.pop(actor_key, None)
    else:
        _in_flight[actor_key] = meta
        _evict_if_needed(_in_flight)


def quota_begin(actor_key: str) -> None:
    now = time.monotonic()
    _touch_in_flight(actor_key, now, 1)


def quota_end(actor_key: str) -> None:
    now = time.monotonic()
    _touch_in_flight(actor_key, now, -1)


def quota_precheck(ctx: QuotaContext) -> QuotaDecision:
    if _force_block_enabled():
        return QuotaDecision(False, 429, None, "RATE_LIMIT", None)

    cfg = _plan_config(ctx.plan)
    max_output_cap = cfg["max_output_cap"]
    concurrency_limit = cfg["concurrency"]
    rpm_limit = cfg["rpm"]

    if ctx.est_output_cap is not None and ctx.est_output_cap > max_output_cap:
        return QuotaDecision(False, 429, None, "REQUEST_CAP", None)

    current_inflight = _in_flight.get(ctx.actor_key, {}).get("count", 0)
    if current_inflight >= concurrency_limit:
        return QuotaDecision(False, 429, 5, "CONCURRENCY_LIMIT", None)

    keys = [ctx.actor_key]
    if ctx.ip_hash:
        keys.append(f"{ctx.actor_key}|{ctx.ip_hash}")

    pending_updates = []
    retry_after_candidates: list[int] = []
    now = ctx.now_monotonic

    for key in keys:
        bucket = _buckets.get(key, {"tokens": float(rpm_limit), "updated_at": now, "last_seen": now})
        tokens_refilled, rate_per_sec = _refill(bucket.get("tokens", 0.0), rpm_limit, now, bucket.get("updated_at", now))
        if tokens_refilled < 1.0:
            retry_after_candidates.append(_retry_after_seconds(1.0 - tokens_refilled, rate_per_sec))
        pending_updates.append((key, max(0.0, tokens_refilled - 1.0)))

    if retry_after_candidates:
        return QuotaDecision(False, 429, max(retry_after_candidates), "RATE_LIMIT", None)

    for key, new_tokens in pending_updates:
        _buckets[key] = {"tokens": new_tokens, "updated_at": now, "last_seen": now}
    _evict_if_needed(_buckets)

    effective_output_cap = max_output_cap
    if ctx.est_output_cap is not None:
        effective_output_cap = min(ctx.est_output_cap, max_output_cap)

    return QuotaDecision(True, 200, None, "OK", effective_output_cap)


def _reset_state() -> None:
    _buckets.clear()
    _in_flight.clear()


__all__ = [
    "QuotaDecision",
    "QuotaContext",
    "quota_precheck",
    "quota_begin",
    "quota_end",
    "_reset_state",
]
