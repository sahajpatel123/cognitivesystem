"""Phase 10 — Step 1: Rigor selection engine.

Deterministically maps a DecisionState to a bounded RigorLevel.
No orchestration, no models, no heuristics, no probabilities.
"""

from typing import Iterable

from backend.mci_backend.control_plan import RigorLevel
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    ConsequenceHorizon,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class RigorSelectionError(ValueError):
    """Raised when rigor selection cannot be performed due to invalid input."""


_ORDER = [
    RigorLevel.MINIMAL,
    RigorLevel.GUARDED,
    RigorLevel.STRUCTURED,
    RigorLevel.ENFORCED,
]

_CONFIDENCE_ORDER = [
    ConfidenceLevel.LOW,
    ConfidenceLevel.MEDIUM,
    ConfidenceLevel.HIGH,
]


def _bump(current: RigorLevel, target: RigorLevel) -> RigorLevel:
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
        raise RigorSelectionError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in critical
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_index
        ):
            return True
    return False


def select_rigor(decision_state: DecisionState) -> RigorLevel:
    """
    Deterministically select a RigorLevel based on DecisionState.
    """
    if decision_state is None:
        raise RigorSelectionError("DecisionState is required.")

    rigor = RigorLevel.MINIMAL

    # Proximity escalation
    if decision_state.proximity_state in {ProximityState.MEDIUM}:
        rigor = _bump(rigor, RigorLevel.GUARDED)
    elif decision_state.proximity_state in {ProximityState.HIGH, ProximityState.IMMINENT}:
        rigor = _bump(rigor, RigorLevel.STRUCTURED)

    # Unknown-zone honesty with elevated proximity prevents MINIMAL
    if decision_state.explicit_unknown_zone and decision_state.proximity_state in {
        ProximityState.MEDIUM,
        ProximityState.HIGH,
        ProximityState.IMMINENT,
    }:
        rigor = _bump(rigor, RigorLevel.GUARDED)

    # Domain escalation
    has_critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)
    has_critical_mid = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    if has_critical_low:
        rigor = _bump(rigor, RigorLevel.GUARDED)
    if has_critical_mid:
        rigor = _bump(rigor, RigorLevel.STRUCTURED)

    # Irreversibility escalation
    if decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE:
        rigor = _bump(rigor, RigorLevel.STRUCTURED)

    # Consequence horizon escalation
    # LONG_HORIZON should raise rigor at least to GUARDED.
    # Unknown honesty is enforced in DecisionState; rigor still escalates.
    if decision_state.consequence_horizon == ConsequenceHorizon.LONG_HORIZON:
        rigor = _bump(rigor, RigorLevel.GUARDED)

    # Responsibility escalation
    if decision_state.responsibility_scope == ResponsibilityScope.THIRD_PARTY:
        rigor = _bump(rigor, RigorLevel.GUARDED)
    elif decision_state.responsibility_scope == ResponsibilityScope.SYSTEMIC_PUBLIC:
        rigor = _bump(rigor, RigorLevel.STRUCTURED)

    # Reserved ENFORCED conditions
    imminent = decision_state.proximity_state == ProximityState.IMMINENT
    high = decision_state.proximity_state == ProximityState.HIGH
    critical_high = _has_critical_domain(
        decision_state.risk_domains, ConfidenceLevel.MEDIUM
    )
    irreversible = decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
    systemic_public = decision_state.responsibility_scope == ResponsibilityScope.SYSTEMIC_PUBLIC
    high_unknown = bool(decision_state.explicit_unknown_zone) and (
        high or imminent
    )
    if imminent and (irreversible or systemic_public or critical_high):
        rigor = _bump(rigor, RigorLevel.ENFORCED)
    elif high_unknown and critical_high:
        rigor = _bump(rigor, RigorLevel.ENFORCED)
    elif imminent and high_unknown:
        rigor = _bump(rigor, RigorLevel.ENFORCED)

    return rigor
