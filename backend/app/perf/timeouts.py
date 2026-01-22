from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class PerfTimeoutError(TimeoutError):
    """Raised when a performance timeout is exceeded."""


def remaining_budget_ms(start_ts: float, budget_ms_total: int) -> int:
    elapsed_ms = (time.monotonic() - start_ts) * 1000
    remaining = int(budget_ms_total - elapsed_ms)
    return remaining if remaining > 0 else 0


async def enforce_timeout(
    coro_fn: Callable[[], Awaitable[T]],
    timeout_ms: int,
) -> T:
    try:
        return await asyncio.wait_for(coro_fn(), timeout=timeout_ms / 1000.0)
    except asyncio.TimeoutError as exc:  # noqa: PERF203
        raise PerfTimeoutError(f"operation exceeded {timeout_ms} ms") from exc
