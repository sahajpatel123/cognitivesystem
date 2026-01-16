"""Phase 10 — Step 2: Friction placement engine.

Deterministically maps a DecisionState (and optional rigor) to a bounded
FrictionPosture. No models, heuristics, or probabilities. No orchestration.
"""

from typing import Iterable, Optional

from mci_backend.control_plan import FrictionPosture, RigorLevel
from mci_backend.decision_state import (
    ConfidenceLevel,
    ConsequenceHorizon,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class FrictionSelectionError(ValueError):
    """Raised when friction selection cannot be performed due to invalid input."""


_ORDER = [
    FrictionPosture.NONE,
    FrictionPosture.SOFT_PAUSE,
    FrictionPosture.HARD_PAUSE,
    FrictionPosture.STOP,
]

_CONFIDENCE_ORDER = [
    ConfidenceLevel.LOW,
    ConfidenceLevel.MEDIUM,
    ConfidenceLevel.HIGH,
]


def _bump(current: FrictionPosture, target: FrictionPosture) -> FrictionPosture:
    if _ORDER.index(target) > _ORDER.index(current):
        return target
    return current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_confidence: ConfidenceLevel
) -> bool:
    critical = {RiskDomain.LEGAL_REGULATORY, RiskDomain.MEDICAL_BIOLOGICAL, RiskDomain.PHYSICAL_SAFETY}
    try:
        min_index = _CONFIDENCE_ORDER.index(min_confidence)
    except ValueError as exc:
        raise FrictionSelectionError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in critical
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_index
        ):
            return True
    return False


def select_friction(
    decision_state: DecisionState, rigor_level: Optional[RigorLevel] = None
) -> FrictionPosture:
    """Deterministically select a FrictionPosture based on DecisionState."""
    if decision_state is None:
        raise FrictionSelectionError("DecisionState is required.")

    friction = FrictionPosture.NONE
    significant_unknowns = bool(decision_state.explicit_unknown_zone)

    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)

    # Proximity primary driver
    if decision_state.proximity_state in {ProximityState.VERY_LOW, ProximityState.LOW}:
        friction = FrictionPosture.NONE
    elif decision_state.proximity_state == ProximityState.MEDIUM:
        if critical_low or decision_state.responsibility_scope != ResponsibilityScope.SELF_ONLY:
            friction = _bump(friction, FrictionPosture.SOFT_PAUSE)
        if decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE:
            friction = _bump(friction, FrictionPosture.SOFT_PAUSE)
        if significant_unknowns:
            friction = _bump(friction, FrictionPosture.SOFT_PAUSE)
    elif decision_state.proximity_state == ProximityState.HIGH:
        if (
            decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
            or decision_state.responsibility_scope
            in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
            or critical_low
        ):
            friction = _bump(friction, FrictionPosture.HARD_PAUSE)
        if significant_unknowns:
            friction = _bump(friction, FrictionPosture.HARD_PAUSE)
    elif decision_state.proximity_state == ProximityState.IMMINENT:
        if (
            decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
            or decision_state.responsibility_scope == ResponsibilityScope.SYSTEMIC_PUBLIC
            or critical_med
        ):
            friction = _bump(friction, FrictionPosture.HARD_PAUSE)
        if (
            decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
            and critical_low
            and significant_unknowns
        ):
            friction = _bump(friction, FrictionPosture.STOP)
        elif critical_low and significant_unknowns:
            friction = _bump(friction, FrictionPosture.HARD_PAUSE)
        elif significant_unknowns:
            friction = _bump(friction, FrictionPosture.HARD_PAUSE)

    # Horizon: long horizon can justify at least soft gating at medium proximity+
    if decision_state.consequence_horizon == ConsequenceHorizon.LONG_HORIZON:
        if decision_state.proximity_state in {
            ProximityState.MEDIUM,
            ProximityState.HIGH,
            ProximityState.IMMINENT,
        }:
            friction = _bump(friction, FrictionPosture.SOFT_PAUSE)

    # Rigor cross-check (optional input): higher rigor can support friction >= SOFT when already escalated.
    if rigor_level in {RigorLevel.STRUCTURED, RigorLevel.ENFORCED}:
        if friction == FrictionPosture.NONE and decision_state.proximity_state in {
            ProximityState.MEDIUM,
            ProximityState.HIGH,
            ProximityState.IMMINENT,
        }:
            friction = FrictionPosture.SOFT_PAUSE

    return friction
