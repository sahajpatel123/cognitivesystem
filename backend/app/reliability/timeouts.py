from __future__ import annotations

import time
from typing import Callable, Awaitable

from backend.app.perf import enforce_timeout, PerfTimeoutError


class Deadline:
    def __init__(self, start_ts: float, deadline_ms: int):
        self.start_ts = start_ts
        self.deadline_ms = max(0, int(deadline_ms))

    def remaining_ms(self) -> int:
        elapsed_ms = int((time.monotonic() - self.start_ts) * 1000)
        remaining = self.deadline_ms - elapsed_ms
        return remaining if remaining > 0 else 0

    def expired(self) -> bool:
        return self.remaining_ms() <= 0

    async def run_with(self, func: Callable[[], Awaitable], timeout_ms: int):
        timeout = clamp_attempt_timeout_ms(self, timeout_ms)
        return await enforce_timeout(func, timeout)


def clamp_attempt_timeout_ms(deadline: Deadline, requested_timeout_ms: int) -> int:
    remaining = deadline.remaining_ms()
    return max(100, min(requested_timeout_ms, remaining)) if remaining > 0 else 100


__all__ = ["Deadline", "clamp_attempt_timeout_ms", "PerfTimeoutError"]
