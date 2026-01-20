from __future__ import annotations

import time
from typing import Dict, List, Tuple

# key -> list of failure timestamps
_FAILURES: Dict[str, List[float]] = {}
# key -> open_until timestamp
_OPEN_UNTIL: Dict[str, float] = {}


def _now() -> float:
    return time.time()


def is_open(key: str, *, open_seconds: int) -> Tuple[bool, int | None]:
    now = _now()
    until = _OPEN_UNTIL.get(key, 0.0)
    if until > now:
        retry = int(max(1, until - now))
        return True, retry
    return False, None


def record_failure(key: str, *, window_seconds: int, failure_threshold: int, open_seconds: int) -> None:
    now = _now()
    window_start = now - window_seconds
    bucket = _FAILURES.get(key, [])
    bucket = [ts for ts in bucket if ts >= window_start]
    bucket.append(now)
    _FAILURES[key] = bucket
    if len(bucket) >= failure_threshold:
        _OPEN_UNTIL[key] = now + open_seconds


def record_success(key: str) -> None:
    _FAILURES.pop(key, None)
    _OPEN_UNTIL.pop(key, None)


__all__ = ["is_open", "record_failure", "record_success"]
