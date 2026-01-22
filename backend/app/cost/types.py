from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class BudgetDecision:
    allowed: bool
    scope: Optional[str] = None
    reason: Optional[str] = None
    retry_after_s: Optional[int] = None


@dataclass
class UsageRecord:
    ts: float
    request_id: str
    route: str
    actor_key: str
    ip_hash: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_units: int
    outcome: str
    latency_ms: float
    budget_scope: Optional[str]
    breaker_state: Optional[str]
