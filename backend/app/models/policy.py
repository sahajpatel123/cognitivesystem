from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from backend.app.config import get_settings


class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"


class RequestedMode(str, Enum):
    DEFAULT = "default"
    THINKING = "thinking"
    RESEARCH = "research"


class EffectiveMode(str, Enum):
    DEFAULT = "default"
    THINKING = "thinking"
    RESEARCH = "research"


class ModelClass(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    STRONG = "strong"


class Capability(str, Enum):
    CHAT = "chat"
    RESEARCH = "research"


class DecisionReason(str, Enum):
    REQUESTED_DEFAULT = "requested_default"
    REQUESTED_THINKING = "requested_thinking"
    REQUESTED_RESEARCH = "requested_research"
    DOWNGRADED_TIER_LIMIT = "downgraded_tier_limit"
    DOWNGRADED_BREAKER = "downgraded_breaker"
    DOWNGRADED_BUDGET = "downgraded_budget"
    DEFAULT_POLICY = "default_policy"


@dataclass
class RouteConstraints:
    max_output_tokens: int
    max_input_tokens: int


@dataclass
class ModelRoute:
    capability: Capability
    model_class: ModelClass
    effective_mode: EffectiveMode
    constraints: RouteConstraints
    reasons: List[DecisionReason] = field(default_factory=list)


@dataclass
class RoutingContext:
    tier: Tier = Tier.FREE
    requested_mode: RequestedMode = RequestedMode.DEFAULT
    breaker_open: bool = False
    budget_tight: bool = False
    est_input_tokens: Optional[int] = None


@dataclass
class ModelRoutePlan:
    tier: Tier
    requested_mode: RequestedMode
    effective_mode: EffectiveMode
    primary: ModelRoute
    fallbacks: List[ModelRoute]
    decision_trace: List[DecisionReason]

    @property
    def routes(self) -> List[ModelRoute]:
        return [self.primary, *self.fallbacks]


def _allowed_modes(tier: Tier) -> List[RequestedMode]:
    if tier == Tier.FREE:
        return [RequestedMode.DEFAULT]
    if tier == Tier.PRO:
        return [RequestedMode.DEFAULT, RequestedMode.THINKING]
    return [RequestedMode.DEFAULT, RequestedMode.THINKING, RequestedMode.RESEARCH]


def _downgrade_mode(mode: RequestedMode) -> EffectiveMode:
    if mode == RequestedMode.RESEARCH:
        return EffectiveMode.THINKING
    if mode == RequestedMode.THINKING:
        return EffectiveMode.DEFAULT
    return EffectiveMode.DEFAULT


def _model_class_for_mode(mode: EffectiveMode) -> ModelClass:
    if mode == EffectiveMode.RESEARCH:
        return ModelClass.STRONG
    if mode == EffectiveMode.THINKING:
        return ModelClass.BALANCED
    return ModelClass.BALANCED


def _downgrade_model_class(model_class: ModelClass) -> ModelClass:
    if model_class == ModelClass.STRONG:
        return ModelClass.BALANCED
    if model_class == ModelClass.BALANCED:
        return ModelClass.FAST
    return ModelClass.FAST


def _route_constraints(mode: EffectiveMode) -> RouteConstraints:
    s = get_settings()
    caps = s.validated_caps()
    # Keep conservative caps; never exceed global settings.
    # Thinking/Research are clamped to the same safe outputs to avoid escalation.
    base_output = caps["model_max_output_tokens"]
    base_input = caps["model_max_input_tokens"]
    return RouteConstraints(max_output_tokens=base_output, max_input_tokens=base_input)


def decide_route(ctx: RoutingContext) -> ModelRoutePlan:
    decisions: List[DecisionReason] = []

    requested = ctx.requested_mode
    decisions.append(
        DecisionReason.REQUESTED_RESEARCH
        if requested == RequestedMode.RESEARCH
        else DecisionReason.REQUESTED_THINKING
        if requested == RequestedMode.THINKING
        else DecisionReason.REQUESTED_DEFAULT
    )

    allowed = _allowed_modes(ctx.tier)
    effective_mode: EffectiveMode
    if requested in allowed:
        effective_mode = EffectiveMode(requested.value)
    else:
        # deterministic downgrade ladder
        step = requested
        while step not in allowed:
            step = RequestedMode(_downgrade_mode(step).value)
        effective_mode = EffectiveMode(step.value)
        decisions.append(DecisionReason.DOWNGRADED_TIER_LIMIT)

    model_class = _model_class_for_mode(effective_mode)

    if ctx.breaker_open:
        model_class = _downgrade_model_class(model_class)
        if effective_mode == EffectiveMode.RESEARCH:
            effective_mode = EffectiveMode.THINKING
        decisions.append(DecisionReason.DOWNGRADED_BREAKER)

    if ctx.budget_tight:
        model_class = _downgrade_model_class(model_class)
        if effective_mode == EffectiveMode.RESEARCH:
            effective_mode = EffectiveMode.THINKING
        elif effective_mode == EffectiveMode.THINKING:
            effective_mode = EffectiveMode.DEFAULT
        decisions.append(DecisionReason.DOWNGRADED_BUDGET)

    constraints = _route_constraints(effective_mode)
    primary = ModelRoute(
        capability=Capability.CHAT,
        model_class=model_class,
        effective_mode=effective_mode,
        constraints=constraints,
        reasons=decisions.copy(),
    )

    # deterministic fallback chain: lower model class, then lower mode
    fallbacks: List[ModelRoute] = []
    next_model = _downgrade_model_class(model_class)
    if next_model != model_class:
        fallbacks.append(
            ModelRoute(
                capability=Capability.CHAT,
                model_class=next_model,
                effective_mode=effective_mode,
                constraints=constraints,
                reasons=decisions + [DecisionReason.DEFAULT_POLICY],
            )
        )
    lower_mode = EffectiveMode(_downgrade_mode(RequestedMode(effective_mode.value)).value)
    if lower_mode != effective_mode:
        fallbacks.append(
            ModelRoute(
                capability=Capability.CHAT,
                model_class=_downgrade_model_class(next_model),
                effective_mode=lower_mode,
                constraints=_route_constraints(lower_mode),
                reasons=decisions + [DecisionReason.DEFAULT_POLICY],
            )
        )

    plan = ModelRoutePlan(
        tier=ctx.tier,
        requested_mode=ctx.requested_mode,
        effective_mode=effective_mode,
        primary=primary,
        fallbacks=fallbacks,
        decision_trace=decisions.copy(),
    )
    return plan


__all__ = [
    "Tier",
    "RequestedMode",
    "EffectiveMode",
    "ModelClass",
    "Capability",
    "DecisionReason",
    "RouteConstraints",
    "ModelRoute",
    "RoutingContext",
    "ModelRoutePlan",
    "decide_route",
]
