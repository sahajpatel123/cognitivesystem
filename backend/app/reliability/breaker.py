from __future__ import annotations

import os


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip() == "1"


def evaluate_breaker(existing_open: bool = False) -> bool:
    """
    Deterministic breaker evaluation; honors forced chaos flag.
    """
    forced = _flag("FORCE_BREAKER_OPEN")
    return existing_open or forced


def force_budget_blocked() -> bool:
    # support both names to avoid breaking earlier envs
    return _flag("FORCE_BUDGET_BLOCK") or _flag("FORCE_BUDGET_EXCEEDED")


def force_provider_timeout() -> bool:
    return _flag("FORCE_PROVIDER_TIMEOUT")


def force_quality_fail() -> bool:
    return _flag("FORCE_QUALITY_FAIL")


def force_safety_block() -> bool:
    return _flag("FORCE_SAFETY_BLOCK")


__all__ = [
    "evaluate_breaker",
    "force_budget_blocked",
    "force_provider_timeout",
    "force_quality_fail",
    "force_safety_block",
]
