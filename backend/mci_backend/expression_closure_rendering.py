"""Phase 11 — Step 7: Closure rendering planning.

Deterministically selects ClosureRenderingMode using DecisionState, ControlPlan,
and prior Phase 11 selections. No text generation, no templates, no models, and
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
    ClosureRenderingMode,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    RefusalExplanationMode,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
)


class ClosureRenderingSelectionError(Exception):
    """Raised when closure rendering selection cannot be determined."""


_ORDER = {
    ClosureRenderingMode.SILENCE: 0,
    ClosureRenderingMode.CONFIRM_CLOSURE: 1,
    ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP: 2,
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
    current: ClosureRenderingMode, target: ClosureRenderingMode
) -> ClosureRenderingMode:
    return target if _ORDER[target] > _ORDER[current] else current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_conf]
    except KeyError as exc:
        raise ClosureRenderingSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx
        ):
            return True
    return False


def select_closure_rendering_mode(
    decision_state: DecisionState,
    control_plan: ControlPlan,
    posture: ExpressionPosture,
    rigor_disclosure: RigorDisclosureLevel,
    confidence_signaling: ConfidenceSignalingLevel,
    unknown_disclosure: UnknownDisclosureMode,
    assumption_surfacing: AssumptionSurfacingMode,
    refusal_explanation_mode: RefusalExplanationMode,
) -> ClosureRenderingMode:
    if any(
        x is None
        for x in (
            decision_state,
            control_plan,
            posture,
            rigor_disclosure,
            confidence_signaling,
            unknown_disclosure,
            assumption_surfacing,
            refusal_explanation_mode,
        )
    ):
        raise ClosureRenderingSelectionError("All inputs are required.")

    closure = control_plan.closure_state
    if closure == ClosureState.OPEN:
        raise ClosureRenderingSelectionError("Closure rendering runs only when closure_state != OPEN.")
    if control_plan.question_budget == 1:
        raise ClosureRenderingSelectionError("Closure with question budget is contradictory.")
    if control_plan.clarification_required:
        raise ClosureRenderingSelectionError("Closure cannot require clarification.")

    proximity = decision_state.proximity_state
    friction = control_plan.friction_posture
    unknowns_present = bool(decision_state.explicit_unknown_zone)

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

    # Baseline by closure state
    if closure == ClosureState.CLOSED:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE
    elif closure == ClosureState.CLOSING:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE
    else:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE

    # HARD OVERRIDES
    if closure == ClosureState.USER_TERMINATED:
        mode = ClosureRenderingMode.SILENCE
    if friction == FrictionPosture.STOP:
        mode = ClosureRenderingMode.SILENCE
    if posture == ExpressionPosture.CONSTRAINED and mode == ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT or unknown_disclosure == UnknownDisclosureMode.EXPLICIT:
        if closure == ClosureState.CLOSING and mode != ClosureRenderingMode.SILENCE:
            mode = _bump(mode, ClosureRenderingMode.CONFIRM_CLOSURE)
        if closure == ClosureState.CLOSED:
            mode = ClosureRenderingMode.CONFIRM_CLOSURE

    # CLOSURE STATE MAPPING
    if closure == ClosureState.CLOSED:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE
    elif closure == ClosureState.CLOSING:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE

    # HIGH-STAKES SUPPORT
    if (
        closure == ClosureState.CLOSING
        and high_stakes
        and friction != FrictionPosture.STOP
        and closure != ClosureState.USER_TERMINATED
        and posture != ExpressionPosture.CONSTRAINED
    ):
        mode = _bump(mode, ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP)

    # PROXIMITY SUPPORT
    if (
        closure == ClosureState.CLOSING
        and proximity == ProximityState.IMMINENT
        and friction != FrictionPosture.STOP
        and closure != ClosureState.USER_TERMINATED
        and posture != ExpressionPosture.CONSTRAINED
    ):
        mode = _bump(mode, ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP)

    # Default minimal acknowledge already set; ensure CLOSED never summarizes
    if closure == ClosureState.CLOSED and mode == ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP:
        mode = ClosureRenderingMode.CONFIRM_CLOSURE

    # FINAL HARD CONSTRAINTS (fail-closed)
    if closure == ClosureState.USER_TERMINATED and mode != ClosureRenderingMode.SILENCE:
        raise ClosureRenderingSelectionError("USER_TERMINATED requires strict silence/minimal termination.")
    if friction == FrictionPosture.STOP and mode != ClosureRenderingMode.SILENCE:
        raise ClosureRenderingSelectionError("STOP friction requires strict closure rendering.")
    if posture == ExpressionPosture.CONSTRAINED and mode == ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP:
        raise ClosureRenderingSelectionError("CONSTRAINED posture forbids verbose closure.")
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT and closure == ClosureState.CLOSED and mode == ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP:
        raise ClosureRenderingSelectionError("Explicit confidence with CLOSED closure forbids summary.")
    if unknown_disclosure == UnknownDisclosureMode.EXPLICIT and closure == ClosureState.CLOSED and mode == ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP:
        raise ClosureRenderingSelectionError("Explicit unknown disclosure with CLOSED closure forbids summary.")

    return mode
