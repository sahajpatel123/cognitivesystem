from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable

from backend.app.config import get_settings


class Plan(str, Enum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"


@dataclass(frozen=True)
class PlanLimits:
    requests_per_day: int
    token_budget_per_day: int
    max_input_tokens: int
    max_output_tokens: int


_DEFAULT_LIMITS: Dict[Plan, PlanLimits] = {
    Plan.FREE: PlanLimits(
        requests_per_day=50,
        token_budget_per_day=25_000,
        max_input_tokens=8_000,
        max_output_tokens=800,
    ),
    Plan.PRO: PlanLimits(
        requests_per_day=300,
        token_budget_per_day=250_000,
        max_input_tokens=32_000,
        max_output_tokens=2_500,
    ),
    Plan.MAX: PlanLimits(
        requests_per_day=1_500,
        token_budget_per_day=1_500_000,
        max_input_tokens=128_000,
        max_output_tokens=6_000,
    ),
}


def _parse_subject_list(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


_settings = get_settings()


def _first_non_empty(items: Iterable[str | None], default: str) -> str:
    for item in items:
        if item and item.strip():
            return item.strip()
    return default


def resolve_plan(subject_id: str | None) -> Plan:
    """Resolve plan from env overrides, defaulting to FREE."""
    plan_default = _first_non_empty([_settings.plan_default], Plan.FREE.value).lower()
    default_plan = Plan(plan_default) if plan_default in Plan._value2member_map_ else Plan.FREE

    if subject_id:
        max_subjects = _parse_subject_list(_settings.max_subjects)
        pro_subjects = _parse_subject_list(_settings.pro_subjects)
        if subject_id in max_subjects:
            return Plan.MAX
        if subject_id in pro_subjects:
            return Plan.PRO
    return default_plan


def get_plan_limits(plan: Plan) -> PlanLimits:
    return _DEFAULT_LIMITS.get(plan, _DEFAULT_LIMITS[Plan.FREE])


__all__ = ["Plan", "PlanLimits", "resolve_plan", "get_plan_limits"]
