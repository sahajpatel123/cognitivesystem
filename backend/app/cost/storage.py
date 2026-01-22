from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple


class RollingWindowCounter:
    """Token counter per key using fixed-size time buckets."""

    def __init__(self, window_seconds: int) -> None:
        self.window_seconds = max(1, int(window_seconds))
        self._buckets: Dict[str, Dict[int, int]] = defaultdict(dict)

    def _prune(self, key: str, now: float) -> None:
        cutoff = int(now) - self.window_seconds
        buckets = self._buckets.get(key, {})
        to_delete = [ts for ts in buckets if ts < cutoff]
        for ts in to_delete:
            buckets.pop(ts, None)

    def add(self, key: str, tokens: int, now: float | None = None) -> None:
        ts = int(now or time.time())
        buckets = self._buckets[key]
        buckets[ts] = buckets.get(ts, 0) + max(0, int(tokens))
        self._prune(key, ts)

    def total(self, key: str, now: float | None = None) -> int:
        ts = int(now or time.time())
        self._prune(key, ts)
        return sum(self._buckets.get(key, {}).values())


class DailyCounter:
    """Daily token counter per key, resets when the date changes."""

    def __init__(self) -> None:
        self._counts: Dict[str, Tuple[str, int]] = {}

    def add(self, key: str, tokens: int, now: float | None = None) -> None:
        ts = int(now or time.time())
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        existing_day, count = self._counts.get(key, (day, 0))
        if existing_day != day:
            self._counts[key] = (day, max(0, int(tokens)))
            return
        self._counts[key] = (existing_day, count + max(0, int(tokens)))

    def total(self, key: str, now: float | None = None) -> int:
        ts = int(now or time.time())
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        existing_day, count = self._counts.get(key, (day, 0))
        if existing_day != day:
            return 0
        return count


class RingBuffer:
    """Fixed-size ring buffer for recent accounting events."""

    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self._buf: Deque = deque(maxlen=self.capacity)

    def append(self, item) -> None:
        self._buf.append(item)

    def snapshot(self) -> List:
        return list(self._buf)
