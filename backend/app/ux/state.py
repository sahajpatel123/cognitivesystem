from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional


class UXState(str, Enum):
    OK = "OK"
    NEEDS_INPUT = "NEEDS_INPUT"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class UXDecision:
    ux_state: UXState
    cooldown_seconds: Optional[int] = None


def decide_ux_state(
    *,
    status_code: int,
    action: Optional[str],
    failure_type: Optional[str],
    failure_reason: Optional[str] = None,
) -> UXState:
    reason_lower = (failure_reason or "").lower()

    if status_code == 200:
        if action == "ASK_CLARIFY":
            return UXState.NEEDS_INPUT
        return UXState.OK

    if status_code in {415, 422}:
        return UXState.NEEDS_INPUT

    if failure_type == "BUDGET_EXCEEDED" or "budget" in reason_lower or "quota" in reason_lower:
        return UXState.QUOTA_EXCEEDED

    if failure_type == "ABUSE_BLOCKED":
        return UXState.BLOCKED

    if status_code in {401, 403}:
        return UXState.BLOCKED

    if status_code == 429:
        return UXState.RATE_LIMITED

    if status_code == 503:
        if "temporarily unavailable" in reason_lower:
            return UXState.DEGRADED
        return UXState.DEGRADED

    if failure_type == "PROVIDER_UNAVAILABLE":
        return UXState.DEGRADED

    if status_code >= 500:
        return UXState.ERROR

    return UXState.ERROR


def extract_retry_after(headers: Mapping[str, str] | None) -> Optional[int]:
    if not headers:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except Exception:
        return None


def extract_cooldown_seconds(headers: Mapping[str, str] | None) -> Optional[int]:
    retry_after = extract_retry_after(headers)
    if retry_after is None:
        return None
    clamped = max(1, min(86_400, retry_after))
    return clamped


def build_ux_headers(ux_state: UXState, cooldown_seconds: Optional[int]) -> dict[str, str]:
    hdrs = {"X-UX-State": ux_state.value}
    if cooldown_seconds is not None:
        hdrs["X-Cooldown-Seconds"] = str(cooldown_seconds)
    return hdrs


__all__ = [
    "UXState",
    "UXDecision",
    "decide_ux_state",
    "extract_retry_after",
    "extract_cooldown_seconds",
    "build_ux_headers",
]
