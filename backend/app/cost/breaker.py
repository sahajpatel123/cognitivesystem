from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Tuple

from .budgets import (
    cost_breaker_cooldown_seconds,
    cost_breaker_fail_threshold,
    cost_breaker_window_seconds,
)
from .types import BreakerState, BudgetDecision


@dataclass
class _BreakerState:
    state: BreakerState = BreakerState.CLOSED
    opened_at: float = 0.0
    failures: Dict[int, int] = field(default_factory=dict)


class CircuitBreaker:
    """In-memory circuit breaker keyed by provider+model."""

    def __init__(self) -> None:
        self._states: Dict[str, _BreakerState] = {}

    def _get(self, key: str) -> _BreakerState:
        if key not in self._states:
            self._states[key] = _BreakerState()
        return self._states[key]

    def _prune(self, st: _BreakerState, now: float) -> None:
        cutoff = int(now) - cost_breaker_window_seconds()
        to_drop = [ts for ts in st.failures if ts < cutoff]
        for ts in to_drop:
            st.failures.pop(ts, None)

    def precheck(self, key: str, now: float | None = None) -> BudgetDecision:
        ts = now or time.time()
        st = self._get(key)
        self._prune(st, ts)
        cooldown = cost_breaker_cooldown_seconds()

        if st.state == BreakerState.OPEN:
            if ts - st.opened_at >= cooldown:
                st.state = BreakerState.HALF_OPEN
                return BudgetDecision(allowed=True, scope="breaker", reason="half_open_probe")
            return BudgetDecision(allowed=False, scope="breaker", reason="open", retry_after_s=int(cooldown - (ts - st.opened_at)))

        if st.state == BreakerState.HALF_OPEN:
            # allow one probe; caller must call on_success/on_failure
            return BudgetDecision(allowed=True, scope="breaker", reason="half_open_probe")

        # CLOSED
        recent_failures = sum(st.failures.values())
        if recent_failures >= cost_breaker_fail_threshold():
            st.state = BreakerState.OPEN
            st.opened_at = ts
            return BudgetDecision(allowed=False, scope="breaker", reason="open", retry_after_s=cooldown)
        return BudgetDecision(allowed=True, scope=None)

    def on_failure(self, key: str, now: float | None = None) -> None:
        ts = int(now or time.time())
        st = self._get(key)
        st.failures[ts] = st.failures.get(ts, 0) + 1
        self._prune(st, ts)
        if sum(st.failures.values()) >= cost_breaker_fail_threshold():
            st.state = BreakerState.OPEN
            st.opened_at = ts

    def on_success(self, key: str) -> None:
        st = self._get(key)
        st.state = BreakerState.CLOSED
        st.failures.clear()
        st.opened_at = 0.0
