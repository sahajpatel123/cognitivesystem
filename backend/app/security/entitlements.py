from __future__ import annotations

from dataclasses import dataclass


@dataclass(init=False)
class EntitlementsContext:
    plan_value: str
    subject_type: str
    requested_mode_value: str
    requested_model_class_value: str
    breaker_open: bool
    budget_flag: bool

    def __init__(
        self,
        plan_value: str | None = None,
        subject_type: str | None = None,
        requested_mode_value: str | None = None,
        requested_model_class_value: str | None = None,
        breaker_open: bool = False,
        budget_flag: bool = False,
        **aliases: object,
    ) -> None:
        # Accept legacy alias keys without failing callers
        if plan_value is None:
            plan_value = aliases.get("plan")  # type: ignore[assignment]
        if requested_mode_value is None:
            requested_mode_value = aliases.get("requested_mode")  # type: ignore[assignment]
        if requested_model_class_value is None:
            requested_model_class_value = aliases.get("requested_model_class")  # type: ignore[assignment]

        self.plan_value = plan_value or ""
        self.subject_type = subject_type or ""
        self.requested_mode_value = requested_mode_value or ""
        self.requested_model_class_value = requested_model_class_value or ""
        self.breaker_open = bool(breaker_open)
        self.budget_flag = bool(budget_flag)


@dataclass
class EntitlementsDecision:
    effective_mode_value: str
    model_class_cap_value: str
    reason: str

    # Compatibility helpers for existing call sites
    @property
    def effective_mode(self) -> str:
        return self.effective_mode_value

    @property
    def model_class_cap(self) -> str:
        return self.model_class_cap_value

    @property
    def effective_model_class(self) -> str:
        return self.model_class_cap_value


_MODE_LADDER = ["default", "thinking", "research"]
_MODEL_CLASSES = ["fast", "balanced", "strong"]


def _normalize_mode(mode_value: str) -> str:
    mode = (mode_value or "").strip().lower()
    return mode if mode in _MODE_LADDER else "default"


def _normalize_model_class(model_value: str) -> str:
    model = (model_value or "").strip().lower()
    return model if model in _MODEL_CLASSES else "fast"


def _allowed_for_plan(plan_value: str) -> tuple[set[str], str]:
    plan = (plan_value or "").strip().lower()
    if plan == "max":
        return {"default", "thinking", "research"}, "strong"
    if plan == "pro":
        return {"default", "thinking"}, "balanced"
    return {"default"}, "fast"


def _downgrade_mode_once(mode_value: str) -> str:
    if mode_value == "research":
        return "thinking"
    if mode_value == "thinking":
        return "default"
    return "default"


def decide_entitlements(ctx: EntitlementsContext) -> EntitlementsDecision:
    requested_mode = _normalize_mode(ctx.requested_mode_value)
    requested_model_class = _normalize_model_class(ctx.requested_model_class_value)

    allowed_modes, plan_cap = _allowed_for_plan(ctx.plan_value)
    effective_mode = requested_mode
    reason_parts: list[str] = []

    while effective_mode not in allowed_modes:
        effective_mode = _downgrade_mode_once(effective_mode)
        if "MODE_DOWNGRADED_BY_ENTITLEMENTS" not in reason_parts:
            reason_parts.append("MODE_DOWNGRADED_BY_ENTITLEMENTS")

    model_class_cap = plan_cap

    if ctx.breaker_open or ctx.budget_flag:
        effective_mode = "default"
        model_class_cap = "fast"
        reason_parts.append("COST_OR_BREAKER_CLAMP")

    if not reason_parts:
        reason_parts.append("OK")

    reason = "+".join(reason_parts)

    return EntitlementsDecision(
        effective_mode_value=effective_mode,
        model_class_cap_value=model_class_cap,
        reason=reason,
    )


__all__ = ["EntitlementsContext", "EntitlementsDecision", "decide_entitlements"]
