"""Phase 11 — Step 2: Rigor disclosure planning.

Deterministically selects RigorDisclosureLevel using DecisionState, ControlPlan, and
ExpressionPosture. No text generation, no models, no side effects.
"""

from typing import Iterable

from mci_backend.control_plan import (
    ClosureState,
    ControlAction,
    ControlPlan,
    FrictionPosture,
    RigorLevel,
)
from mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)
from mci_backend.output_plan import ExpressionPosture, RigorDisclosureLevel


class RigorDisclosureSelectionError(Exception):
    """Raised when rigor disclosure selection cannot be determined."""


_ORDER = {
    RigorDisclosureLevel.MINIMAL: 0,
    RigorDisclosureLevel.GUARDED: 1,
    RigorDisclosureLevel.STRUCTURED: 2,
    RigorDisclosureLevel.ENFORCED: 3,
}

_CRITICAL_DOMAINS = {
    RiskDomain.LEGAL_REGULATORY,
    RiskDomain.MEDICAL_BIOLOGICAL,
    RiskDomain.PHYSICAL_SAFETY,
}

_CONFIDENCE_ORDER = {
    ConfidenceLevel.LOW: 0,
    ConfidenceLevel.MEDIUM: 1,
    ConfidenceLevel.HIGH: 2,
}


def _bump_min(current: RigorDisclosureLevel, target: RigorDisclosureLevel) -> RigorDisclosureLevel:
    return target if _ORDER[target] > _ORDER[current] else current


def _cap_max(current: RigorDisclosureLevel, cap: RigorDisclosureLevel) -> RigorDisclosureLevel:
    return current if _ORDER[current] <= _ORDER[cap] else cap


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_conf]
    except KeyError as exc:
        raise RigorDisclosureSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx
        ):
            return True
    return False


def _dominance_min(control_plan: ControlPlan) -> RigorDisclosureLevel:
    mapping = {
        RigorLevel.MINIMAL: RigorDisclosureLevel.MINIMAL,
        RigorLevel.GUARDED: RigorDisclosureLevel.GUARDED,
        RigorLevel.STRUCTURED: RigorDisclosureLevel.STRUCTURED,
        RigorLevel.ENFORCED: RigorDisclosureLevel.ENFORCED,
    }
    try:
        return mapping[control_plan.rigor_level]
    except KeyError as exc:
        raise RigorDisclosureSelectionError("Unknown control_plan.rigor_level.") from exc


def select_rigor_disclosure(
    decision_state: DecisionState,
    control_plan: ControlPlan,
    posture: ExpressionPosture,
) -> RigorDisclosureLevel:
    if decision_state is None or control_plan is None or posture is None:
        raise RigorDisclosureSelectionError("decision_state, control_plan, and posture are required.")

    min_required = _dominance_min(control_plan)
    max_allowed = RigorDisclosureLevel.ENFORCED

    # Action compatibility constraints
    if control_plan.action == ControlAction.ASK_ONE_QUESTION or control_plan.clarification_required:
        if min_required == RigorDisclosureLevel.ENFORCED:
            raise RigorDisclosureSelectionError("ENFORCED rigor incompatible with ASK_ONE_QUESTION/clarification.")
        max_allowed = _cap_max(max_allowed, RigorDisclosureLevel.STRUCTURED)

    if control_plan.action == ControlAction.CLOSE or control_plan.closure_state != ClosureState.OPEN:
        if min_required == RigorDisclosureLevel.ENFORCED:
            raise RigorDisclosureSelectionError("ENFORCED rigor incompatible with CLOSE/non-OPEN closure.")
        max_allowed = _cap_max(max_allowed, RigorDisclosureLevel.STRUCTURED)

    if control_plan.refusal_required:
        if min_required == RigorDisclosureLevel.ENFORCED:
            raise RigorDisclosureSelectionError("ENFORCED rigor incompatible with refusal flows.")
        min_required = _bump_min(min_required, RigorDisclosureLevel.GUARDED)
        max_allowed = _cap_max(max_allowed, RigorDisclosureLevel.STRUCTURED)

    # Posture coupling
    if posture == ExpressionPosture.BASELINE:
        if _ORDER[min_required] >= _ORDER[RigorDisclosureLevel.STRUCTURED]:
            raise RigorDisclosureSelectionError("Baseline posture incompatible with STRUCTURED/ENFORCED rigor.")
        max_allowed = _cap_max(max_allowed, RigorDisclosureLevel.GUARDED)
    elif posture == ExpressionPosture.GUARDED:
        # No additional cap beyond action/closure.
        pass
    elif posture == ExpressionPosture.CONSTRAINED:
        min_required = _bump_min(min_required, RigorDisclosureLevel.GUARDED)
    else:
        raise RigorDisclosureSelectionError("Unknown posture enum.")

    # Unknown-zone discipline
    unknowns_present = bool(decision_state.explicit_unknown_zone)
    proximity = decision_state.proximity_state
    if proximity in {ProximityState.MEDIUM, ProximityState.HIGH, ProximityState.IMMINENT} and unknowns_present:
        min_required = _bump_min(min_required, RigorDisclosureLevel.GUARDED)
    if proximity in {ProximityState.HIGH, ProximityState.IMMINENT} and unknowns_present:
        # Aim for STRUCTURED; may be capped by action/posture.
        min_required = _bump_min(min_required, RigorDisclosureLevel.STRUCTURED)

    # High-stakes alignment with proximity + critical domains.
    critical_mid = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    if critical_mid and proximity in {ProximityState.HIGH, ProximityState.IMMINENT}:
        min_required = _bump_min(min_required, RigorDisclosureLevel.STRUCTURED)
    if decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE and proximity in {
        ProximityState.HIGH,
        ProximityState.IMMINENT,
    }:
        min_required = _bump_min(min_required, RigorDisclosureLevel.STRUCTURED)

    # Final reconciliation: caps vs mins
    if _ORDER[min_required] > _ORDER[max_allowed]:
        raise RigorDisclosureSelectionError("Incompatible constraints between action/posture and required rigor.")

    return min_required
