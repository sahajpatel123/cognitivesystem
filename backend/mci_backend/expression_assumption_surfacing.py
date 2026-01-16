"""Phase 11 — Step 5: Assumption surfacing planning.

Deterministically selects AssumptionSurfacingMode using DecisionState,
ControlPlan, and prior Phase 11 selections. No text generation, no models,
no side effects.
"""

from typing import Iterable

from backend.mci_backend.control_plan import (
    ClosureState,
    ControlAction,
    ControlPlan,
    FrictionPosture,
    RigorLevel,
)
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
from backend.mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
)


class AssumptionSurfacingSelectionError(Exception):
    """Raised when assumption surfacing selection cannot be determined."""


_ORDER = {
    AssumptionSurfacingMode.NONE: 0,
    AssumptionSurfacingMode.LIGHT: 1,
    AssumptionSurfacingMode.REQUIRED: 2,
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


def _bump(
    current: AssumptionSurfacingMode, target: AssumptionSurfacingMode
) -> AssumptionSurfacingMode:
    return target if _ORDER[target] > _ORDER[current] else current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_conf]
    except KeyError as exc:
        raise AssumptionSurfacingSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx
        ):
            return True
    return False


def select_assumption_surfacing(
    decision_state: DecisionState,
    control_plan: ControlPlan,
    posture: ExpressionPosture,
    rigor_disclosure: RigorDisclosureLevel,
    confidence_signaling: ConfidenceSignalingLevel,
    unknown_disclosure: UnknownDisclosureMode,
) -> AssumptionSurfacingMode:
    if any(
        x is None
        for x in (
            decision_state,
            control_plan,
            posture,
            rigor_disclosure,
            confidence_signaling,
            unknown_disclosure,
        )
    ):
        raise AssumptionSurfacingSelectionError("All inputs are required.")

    mode = AssumptionSurfacingMode.NONE
    unknowns_present = bool(decision_state.explicit_unknown_zone)
    proximity = decision_state.proximity_state
    action = control_plan.action
    closure = control_plan.closure_state
    friction = control_plan.friction_posture

    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    high_stakes = any(
        [
            critical_med,
            decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE,
            decision_state.consequence_horizon == ConsequenceHorizon.LONG_HORIZON,
            decision_state.responsibility_scope
            in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC},
        ]
    )

    # HARD OVERRIDES
    if friction == FrictionPosture.STOP:
        mode = AssumptionSurfacingMode.REQUIRED
    if control_plan.refusal_required:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)
        if unknowns_present:
            mode = _bump(mode, AssumptionSurfacingMode.REQUIRED)
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)
        if unknowns_present or high_stakes:
            mode = _bump(mode, AssumptionSurfacingMode.REQUIRED)
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)
        if unknowns_present or high_stakes:
            mode = _bump(mode, AssumptionSurfacingMode.REQUIRED)

    # UNKNOWN COUPLING GATES
    if unknowns_present:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)
    if unknown_disclosure == UnknownDisclosureMode.EXPLICIT:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)
        if unknowns_present and proximity in {
            ProximityState.MEDIUM,
            ProximityState.HIGH,
            ProximityState.IMMINENT,
        }:
            mode = _bump(mode, AssumptionSurfacingMode.REQUIRED)

    # PROXIMITY ESCALATION
    if proximity in {ProximityState.HIGH, ProximityState.IMMINENT} and unknowns_present:
        target = AssumptionSurfacingMode.REQUIRED
        if action == ControlAction.ASK_ONE_QUESTION or closure != ClosureState.OPEN:
            target = AssumptionSurfacingMode.LIGHT
            if friction == FrictionPosture.STOP or (
                control_plan.refusal_required and unknowns_present
            ):
                target = AssumptionSurfacingMode.REQUIRED
        mode = _bump(mode, target)
    elif proximity == ProximityState.MEDIUM and unknowns_present:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)

    # HIGH-STAKES ESCALATION
    if high_stakes and unknowns_present:
        mode = _bump(mode, AssumptionSurfacingMode.LIGHT)
        if proximity in {
            ProximityState.MEDIUM,
            ProximityState.HIGH,
            ProximityState.IMMINENT,
        }:
            mode = _bump(mode, AssumptionSurfacingMode.REQUIRED)
    if (
        decision_state.responsibility_scope
        in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
        and proximity in {ProximityState.HIGH, ProximityState.IMMINENT}
    ):
        target = AssumptionSurfacingMode.REQUIRED
        if (action == ControlAction.ASK_ONE_QUESTION or closure != ClosureState.OPEN) and friction != FrictionPosture.STOP and not control_plan.refusal_required:
            target = AssumptionSurfacingMode.LIGHT
        mode = _bump(mode, target)

    # ACTION COMPATIBILITY
    if action == ControlAction.ASK_ONE_QUESTION:
        if mode == AssumptionSurfacingMode.REQUIRED and not (
            friction == FrictionPosture.STOP
            or control_plan.refusal_required
            or (high_stakes and proximity in {ProximityState.HIGH, ProximityState.IMMINENT})
        ):
            mode = AssumptionSurfacingMode.LIGHT
    if closure != ClosureState.OPEN:
        if mode == AssumptionSurfacingMode.REQUIRED and not (
            friction == FrictionPosture.STOP or control_plan.refusal_required
        ):
            mode = AssumptionSurfacingMode.LIGHT
    if action == ControlAction.REFUSE and mode == AssumptionSurfacingMode.NONE:
        mode = AssumptionSurfacingMode.LIGHT

    # BASELINE NONE ALLOW RULE
    baseline_none_ok = all(
        [
            not unknowns_present,
            proximity in {ProximityState.VERY_LOW, ProximityState.LOW},
            not critical_med,
            decision_state.reversibility_class != ReversibilityClass.IRREVERSIBLE,
            decision_state.consequence_horizon != ConsequenceHorizon.LONG_HORIZON,
            decision_state.responsibility_scope == ResponsibilityScope.SELF_ONLY,
            closure == ClosureState.OPEN,
            not control_plan.refusal_required,
            friction in {FrictionPosture.NONE, FrictionPosture.SOFT_PAUSE},
            rigor_disclosure == RigorDisclosureLevel.MINIMAL,
            confidence_signaling == ConfidenceSignalingLevel.MINIMAL,
            unknown_disclosure in {UnknownDisclosureMode.NONE, UnknownDisclosureMode.IMPLICIT},
            posture == ExpressionPosture.BASELINE,
        ]
    )
    if mode == AssumptionSurfacingMode.NONE and not baseline_none_ok:
        mode = AssumptionSurfacingMode.LIGHT

    # Final hard constraints (fail-closed)
    if friction == FrictionPosture.STOP and mode != AssumptionSurfacingMode.REQUIRED:
        raise AssumptionSurfacingSelectionError("STOP friction requires REQUIRED assumption surfacing.")
    if control_plan.refusal_required and mode == AssumptionSurfacingMode.NONE:
        raise AssumptionSurfacingSelectionError("Refusal requires at least LIGHT assumption surfacing.")
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT and mode == AssumptionSurfacingMode.NONE:
        raise AssumptionSurfacingSelectionError("EXPLICIT confidence signaling forbids assumption surfacing NONE.")
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED and mode == AssumptionSurfacingMode.NONE:
        raise AssumptionSurfacingSelectionError("ENFORCED rigor forbids assumption surfacing NONE.")
    if unknowns_present and mode == AssumptionSurfacingMode.NONE:
        raise AssumptionSurfacingSelectionError("Unknowns present forbid assumption surfacing NONE.")
    if unknown_disclosure == UnknownDisclosureMode.EXPLICIT and mode == AssumptionSurfacingMode.NONE:
        raise AssumptionSurfacingSelectionError("EXPLICIT unknown disclosure forbids assumption surfacing NONE.")

    return mode
