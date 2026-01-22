from __future__ import annotations

import functools
from typing import Optional

from backend.app.config import get_settings

from .accounting import Accounting
from .breaker import CircuitBreaker
from .budgets import (
    cost_actor_daily_tokens,
    cost_events_ring_size,
    cost_global_daily_tokens,
    cost_ip_window_seconds,
    cost_ip_window_tokens,
    cost_request_max_output_tokens,
    cost_request_max_tokens,
)
from .storage import DailyCounter, RollingWindowCounter
from .types import BreakerState, BudgetDecision


class CostPolicy:
    """Deterministic, in-memory cost control policy."""

    def __init__(self) -> None:
        self.global_daily = DailyCounter()
        self.actor_daily = DailyCounter()
        self.ip_window = RollingWindowCounter(cost_ip_window_seconds())
        self.breaker = CircuitBreaker()
        self.accounting = Accounting(cost_events_ring_size())
        self._settings = get_settings()

    def _actor_key(self, *, user_id: Optional[str], anon_id: Optional[str], subject_id: str) -> str:
        if user_id:
            return f"user:{user_id}"
        if anon_id:
            return f"anon:{anon_id}"
        return f"subject:{subject_id}"

    def _breaker_key(self) -> str:
        provider = self._settings.model_provider or "unknown"
        model = self._settings.model_name or "unknown"
        return f"{provider}:{model}"

    def precheck(
        self,
        *,
        request_id: str,
        actor_key: str,
        ip_hash: str,
        est_input_tokens: int,
        est_output_cap: int,
    ) -> BudgetDecision:
        total_est = max(0, est_input_tokens) + max(0, est_output_cap)
        if total_est > cost_request_max_tokens():
            return BudgetDecision(allowed=False, scope="request_cap", reason="request_tokens_exceeded")
        if est_output_cap > cost_request_max_output_tokens():
            return BudgetDecision(allowed=False, scope="request_cap", reason="request_output_tokens_exceeded")

        breaker_key = self._breaker_key()
        breaker_decision = self.breaker.precheck(breaker_key)
        if not breaker_decision.allowed:
            return breaker_decision

        # Global daily
        if self.global_daily.total("global") + total_est > cost_global_daily_tokens():
            return BudgetDecision(allowed=False, scope="global_daily", reason="budget_exceeded")

        # Per-IP rolling window
        if self.ip_window.total(ip_hash) + total_est > cost_ip_window_tokens():
            return BudgetDecision(allowed=False, scope="ip_window", reason="budget_exceeded")

        # Per-actor daily (optional)
        actor_cap = cost_actor_daily_tokens()
        if actor_cap > 0 and self.actor_daily.total(actor_key) + total_est > actor_cap:
            return BudgetDecision(allowed=False, scope="actor_daily", reason="budget_exceeded")

        return BudgetDecision(allowed=True, scope=None)

    def record_success(
        self,
        *,
        request_id: str,
        actor_key: str,
        ip_hash: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        outcome: str,
        budget_scope: Optional[str] = None,
    ) -> None:
        total_tokens = max(0, input_tokens) + max(0, output_tokens)
        self.global_daily.add("global", total_tokens)
        self.ip_window.add(ip_hash, total_tokens)
        self.actor_daily.add(actor_key, total_tokens)
        breaker_state = self.breaker._get(self._breaker_key()).state.value
        self.breaker.on_success(self._breaker_key())
        self.accounting.record_now(
            request_id=request_id,
            route="/api/chat",
            actor_key=actor_key,
            ip_hash=ip_hash,
            model=self._settings.model_name or "unknown",
            provider=self._settings.model_provider or "unknown",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_units=total_tokens,
            outcome=outcome,
            latency_ms=latency_ms,
            budget_scope=budget_scope,
            breaker_state=breaker_state,
        )

    def record_failure(
        self,
        *,
        request_id: str,
        actor_key: str,
        ip_hash: str,
        outcome: str,
        latency_ms: float,
        is_provider_failure: bool,
        budget_scope: Optional[str] = None,
    ) -> None:
        breaker_state = self.breaker._get(self._breaker_key()).state.value
        if is_provider_failure:
            self.breaker.on_failure(self._breaker_key())
            breaker_state = self.breaker._get(self._breaker_key()).state.value
        self.accounting.record_now(
            request_id=request_id,
            route="/api/chat",
            actor_key=actor_key,
            ip_hash=ip_hash,
            model=self._settings.model_name or "unknown",
            provider=self._settings.model_provider or "unknown",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_units=0,
            outcome=outcome,
            latency_ms=latency_ms,
            budget_scope=budget_scope,
            breaker_state=breaker_state,
        )


@functools.lru_cache(maxsize=1)
def get_cost_policy() -> CostPolicy:
    return CostPolicy()
