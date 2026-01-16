"""Phase 11 — Step 4: Unknown disclosure planning.

Deterministically selects UnknownDisclosureMode using DecisionState, ControlPlan,
ExpressionPosture, rigor_disclosure, and confidence_signaling.
No text generation, no models, no side effects.
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
    ConsequenceHorizon,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)
from mci_backend.output_plan import (
    ConfidenceSignalingLevel,
    ExpressionPosture,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
)


class UnknownDisclosureSelectionError(Exception):
    """Raised when unknown disclosure selection cannot be determined."""


_ORDER = {
    UnknownDisclosureMode.NONE: 0,
    UnknownDisclosureMode.IMPLICIT: 1,
    UnknownDisclosureMode.EXPLICIT: 2,
}

_CONFIDENCE_ORDER = {
    ConfidenceLevel.LOW: 0,
    ConfidenceLevel.MEDIUM: 1,
    ConfidenceLevel.HIGH: 2,
}

_CRITICAL_DOMAINS = {
    RiskDomain.LEGAL_REGULATORY,
    RiskDomain.MEDICAL_BIOLOGICAL,
    RiskDomain.PHYSICAL_SAFETY,
}


def _bump(current: UnknownDisclosureMode, target: UnknownDisclosureMode) -> UnknownDisclosureMode:
    return target if _ORDER[target] > _ORDER[current] else current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_conf]
    except KeyError as exc:
        raise UnknownDisclosureSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx
        ):
            return True
    return False


def select_unknown_disclosure(
    decision_state: DecisionState,
    control_plan: ControlPlan,
    posture: ExpressionPosture,
    rigor_disclosure: RigorDisclosureLevel,
    confidence_signaling: ConfidenceSignalingLevel,
) -> UnknownDisclosureMode:
    if any(x is None for x in (decision_state, control_plan, posture, rigor_disclosure, confidence_signaling)):
        raise UnknownDisclosureSelectionError("All inputs are required.")

    mode = UnknownDisclosureMode.NONE
    unknowns_present = bool(decision_state.explicit_unknown_zone)
    proximity = decision_state.proximity_state
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)

    # HARD OVERRIDES
    if control_plan.friction_posture == FrictionPosture.STOP:
        mode = UnknownDisclosureMode.EXPLICIT
    if control_plan.refusal_required:
        mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)
        if unknowns_present:
            mode = _bump(mode, UnknownDisclosureMode.EXPLICIT)
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT:
        mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)
        if unknowns_present:
            mode = _bump(mode, UnknownDisclosureMode.EXPLICIT)
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED:
        mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)
        if unknowns_present:
            mode = _bump(mode, UnknownDisclosureMode.EXPLICIT)

    # UNKNOWN GATES
    if unknowns_present:
        mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)

    # PROXIMITY ESCALATION
    if proximity in {ProximityState.HIGH, ProximityState.IMMINENT} and unknowns_present:
        if control_plan.action == ControlAction.ASK_ONE_QUESTION or control_plan.closure_state != ClosureState.OPEN:
            mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)
        else:
            mode = _bump(mode, UnknownDisclosureMode.EXPLICIT)
    elif proximity == ProximityState.MEDIUM and unknowns_present:
        mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)

    # HIGH-STAKES ESCALATION
    high_stakes = any(
        [
            critical_med,
            decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE,
            decision_state.consequence_horizon == ConsequenceHorizon.LONG_HORIZON,
            decision_state.responsibility_scope
            in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC},
        ]
    )
    if high_stakes and unknowns_present and proximity in {
        ProximityState.MEDIUM,
        ProximityState.HIGH,
        ProximityState.IMMINENT,
    }:
        forced_explicit = (
            control_plan.action != ControlAction.ASK_ONE_QUESTION
            and control_plan.closure_state == ClosureState.OPEN
            and control_plan.action != ControlAction.CLOSE
        )
        if forced_explicit:
            mode = _bump(mode, UnknownDisclosureMode.EXPLICIT)
        else:
            mode = _bump(mode, UnknownDisclosureMode.IMPLICIT)

    # ACTION COMPATIBILITY
    if control_plan.action == ControlAction.ASK_ONE_QUESTION:
        if mode == UnknownDisclosureMode.EXPLICIT and not (
            control_plan.friction_posture == FrictionPosture.STOP
            or (high_stakes and proximity in {ProximityState.HIGH, ProximityState.IMMINENT})
        ):
            mode = UnknownDisclosureMode.IMPLICIT
    if control_plan.closure_state != ClosureState.OPEN:
        if mode == UnknownDisclosureMode.EXPLICIT and not (
            control_plan.friction_posture == FrictionPosture.STOP
            or (control_plan.refusal_required and unknowns_present)
        ):
            mode = UnknownDisclosureMode.IMPLICIT
    if control_plan.action == ControlAction.REFUSE:
        if mode == UnknownDisclosureMode.NONE:
            mode = UnknownDisclosureMode.IMPLICIT

    # BASELINE NONE ALLOW RULE
    baseline_none_ok = all(
        [
            not unknowns_present,
            proximity in {ProximityState.VERY_LOW, ProximityState.LOW},
            not critical_med,
            decision_state.reversibility_class != ReversibilityClass.IRREVERSIBLE,
            decision_state.consequence_horizon != ConsequenceHorizon.LONG_HORIZON,
            decision_state.responsibility_scope == ResponsibilityScope.SELF_ONLY,
            control_plan.closure_state == ClosureState.OPEN,
            not control_plan.refusal_required,
            control_plan.friction_posture in {FrictionPosture.NONE, FrictionPosture.SOFT_PAUSE},
            rigor_disclosure == RigorDisclosureLevel.MINIMAL,
            confidence_signaling == ConfidenceSignalingLevel.MINIMAL,
            posture == ExpressionPosture.BASELINE,
        ]
    )
    if mode == UnknownDisclosureMode.NONE and not baseline_none_ok:
        mode = UnknownDisclosureMode.IMPLICIT

    # Final hard constraints
    if control_plan.friction_posture == FrictionPosture.STOP and mode != UnknownDisclosureMode.EXPLICIT:
        raise UnknownDisclosureSelectionError("STOP friction requires EXPLICIT unknown disclosure.")
    if control_plan.refusal_required and mode == UnknownDisclosureMode.NONE:
        raise UnknownDisclosureSelectionError("Refusal requires at least IMPLICIT unknown disclosure.")
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT and mode == UnknownDisclosureMode.NONE:
        raise UnknownDisclosureSelectionError("EXPLICIT confidence signaling forbids unknown disclosure NONE.")
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED and mode == UnknownDisclosureMode.NONE:
        raise UnknownDisclosureSelectionError("ENFORCED rigor forbids unknown disclosure NONE.")
    if unknowns_present and mode == UnknownDisclosureMode.NONE:
        raise UnknownDisclosureSelectionError("Unknowns present forbid unknown disclosure NONE.")

    return mode
