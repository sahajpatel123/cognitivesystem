from __future__ import annotations

import logging
import time
from typing import Optional

from .storage import RingBuffer
from .types import UsageRecord

logger = logging.getLogger(__name__)


class Accounting:
    """In-memory accounting ring buffer for recent cost events."""

    def __init__(self, capacity: int) -> None:
        self._events = RingBuffer(capacity)

    def record(self, record: UsageRecord) -> None:
        self._events.append(record)
        try:
            logger.info(
                "[Cost] usage recorded",
                extra={
                    "request_id": record.request_id,
                    "route": record.route,
                    "actor_key": record.actor_key,
                    "ip_hash": record.ip_hash,
                    "model": record.model,
                    "provider": record.provider,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                    "cost_units": record.cost_units,
                    "outcome": record.outcome,
                    "latency_ms": int(record.latency_ms),
                    "budget_scope": record.budget_scope,
                    "breaker_state": record.breaker_state,
                    "ts": int(record.ts),
                },
            )
        except Exception:
            # best-effort logging; never raise
            return

    def snapshot(self) -> list[UsageRecord]:
        return self._events.snapshot()

    def record_now(
        self,
        *,
        request_id: str,
        route: str,
        actor_key: str,
        ip_hash: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost_units: int,
        outcome: str,
        latency_ms: float,
        budget_scope: Optional[str],
        breaker_state: Optional[str],
    ) -> None:
        self.record(
            UsageRecord(
                ts=time.time(),
                request_id=request_id,
                route=route,
                actor_key=actor_key,
                ip_hash=ip_hash,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_units=cost_units,
                outcome=outcome,
                latency_ms=latency_ms,
                budget_scope=budget_scope,
                breaker_state=breaker_state,
            )
        )
