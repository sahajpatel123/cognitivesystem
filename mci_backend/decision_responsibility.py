from __future__ import annotations

"""
Phase 9 — Step 4: Responsibility Scope Detection (deterministic, bounded).

Populates only:
- responsibility_scope
- explicit_unknown_zone (for responsibility uncertainty)

Forbidden:
- No advice, mitigation, escalation, refusal, or orchestration.
- No models, heuristics, probabilities, personalization, or history.
- No modification of other DecisionState fields.
"""

from dataclasses import replace
from typing import Iterable, Tuple

from .decision_state import (
    DecisionState,
    ResponsibilityScope,
    UnknownSource,
    ConsequenceHorizon,
)


def _lower(text: str | None) -> str:
    return (text or "").lower()


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def classify_responsibility_scope(message: str, intent_framing: str | None = None) -> Tuple[ResponsibilityScope, bool]:
    text = _lower(message)
    framing = _lower(intent_framing)

    systemic_markers = [
        "publicly",
        "publish",
        "broadcast",
        "release",
        "release publicly",
        "policy",
        "users",
        "customers",
        "vulnerability",
        "exploit",
        "mass",
        "system-wide",
        "company-wide",
    ]
    if _contains_any(text, systemic_markers) or _contains_any(framing, systemic_markers):
        return ResponsibilityScope.SYSTEMIC_PUBLIC, False

    third_party_markers = [
        "client",
        "customer",
        "employee",
        "employer",
        "manager",
        "contractor",
        "for them",
        "for her",
        "for him",
        "for them",
        "allow",
        "approve",
        "deny",
        "permission",
        "they depend on me",
    ]
    if _contains_any(text, third_party_markers) or _contains_any(framing, third_party_markers):
        return ResponsibilityScope.THIRD_PARTY, False

    shared_markers = [
        "family",
        "parents",
        "child",
        "friend",
        "partner",
        "team",
        "group",
        "we",
        "us",
        "together",
        "shared",
        "our",
    ]
    if _contains_any(text, shared_markers) or _contains_any(framing, shared_markers):
        return ResponsibilityScope.SHARED, False

    self_markers = [
        "i will",
        "i'm going to",
        "for myself",
        "my decision",
        "personal",
    ]
    if _contains_any(text, self_markers) or _contains_any(framing, self_markers):
        return ResponsibilityScope.SELF_ONLY, True

    return ResponsibilityScope.UNKNOWN, True


def _enforce_invariants(
    scope: ResponsibilityScope,
    consequence_horizon: ConsequenceHorizon,
    explicit_unknown_zone: Tuple[UnknownSource, ...],
) -> Tuple[ResponsibilityScope, Tuple[UnknownSource, ...]]:
    unknowns = list(explicit_unknown_zone)

    if scope is ResponsibilityScope.UNKNOWN and UnknownSource.RESPONSIBILITY_SCOPE not in unknowns:
        unknowns.append(UnknownSource.RESPONSIBILITY_SCOPE)

    if scope not in ResponsibilityScope:
        raise ValueError("responsibility_scope must be a bounded ResponsibilityScope enum.")

    # SYSTEMIC_PUBLIC with SHORT_HORIZON requires acknowledging uncertainty in horizon.
    if (
        scope is ResponsibilityScope.SYSTEMIC_PUBLIC
        and consequence_horizon is ConsequenceHorizon.SHORT_HORIZON
        and UnknownSource.HORIZON not in unknowns
    ):
        unknowns.append(UnknownSource.HORIZON)

    return scope, tuple(unknowns)


def apply_responsibility_scope(
    decision_state: DecisionState,
    message: str,
    intent_framing: str | None = None,
) -> DecisionState:
    """Populate responsibility_scope deterministically; leaves other fields unchanged."""
    scope, uncertain = classify_responsibility_scope(message, intent_framing)

    unknowns = list(decision_state.explicit_unknown_zone)
    if uncertain and UnknownSource.RESPONSIBILITY_SCOPE not in unknowns:
        unknowns.append(UnknownSource.RESPONSIBILITY_SCOPE)

    scope, unknowns_tuple = _enforce_invariants(scope, decision_state.consequence_horizon, tuple(unknowns))

    return replace(
        decision_state,
        responsibility_scope=scope,
        explicit_unknown_zone=unknowns_tuple,
    )
