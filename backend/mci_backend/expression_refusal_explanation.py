"""Phase 11 — Step 6: Refusal explanation planning.

Deterministically selects RefusalExplanationMode using DecisionState, ControlPlan,
and prior Phase 11 selections. No text generation, no templates, no models, and
no side effects.
"""

from typing import Iterable

from mci_backend.control_plan import (
    ClosureState,
    ControlAction,
    ControlPlan,
    FrictionPosture,
    RefusalCategory,
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
    AssumptionSurfacingMode,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    RefusalExplanationMode,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
)


class RefusalExplanationSelectionError(Exception):
    """Raised when refusal explanation selection cannot be determined."""


_ORDER = {
    RefusalExplanationMode.BRIEF_BOUNDARY: 0,
    RefusalExplanationMode.BOUNDED_EXPLANATION: 1,
    RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME: 2,
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
    current: RefusalExplanationMode, target: RefusalExplanationMode
) -> RefusalExplanationMode:
    return target if _ORDER[target] > _ORDER[current] else current


def _raise_one(current: RefusalExplanationMode) -> RefusalExplanationMode:
    for mode, idx in _ORDER.items():
        if idx == min(_ORDER[current] + 1, max(_ORDER.values())):
            return mode
    return current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_conf]
    except KeyError as exc:
        raise RefusalExplanationSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx
        ):
            return True
    return False


def _category_baseline(category: RefusalCategory) -> RefusalExplanationMode:
    mapping = {
        RefusalCategory.CAPABILITY_REFUSAL: RefusalExplanationMode.BRIEF_BOUNDARY,
        RefusalCategory.EPISTEMIC_REFUSAL: RefusalExplanationMode.BOUNDED_EXPLANATION,
        RefusalCategory.RISK_REFUSAL: RefusalExplanationMode.BOUNDED_EXPLANATION,
        RefusalCategory.IRREVERSIBILITY_REFUSAL: RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME,
        RefusalCategory.THIRD_PARTY_REFUSAL: RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME,
        RefusalCategory.GOVERNANCE_REFUSAL: RefusalExplanationMode.BOUNDED_EXPLANATION,
    }
    try:
        return mapping[category]
    except KeyError as exc:
        raise RefusalExplanationSelectionError("Unsupported refusal category.") from exc


def select_refusal_explanation_mode(
    decision_state: DecisionState,
    control_plan: ControlPlan,
    posture: ExpressionPosture,
    rigor_disclosure: RigorDisclosureLevel,
    confidence_signaling: ConfidenceSignalingLevel,
    unknown_disclosure: UnknownDisclosureMode,
    assumption_surfacing: AssumptionSurfacingMode,
) -> RefusalExplanationMode:
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
        )
    ):
        raise RefusalExplanationSelectionError("All inputs are required.")

    if not control_plan.refusal_required:
        raise RefusalExplanationSelectionError("Refusal explanation selection requires refusal_required=True.")

    if control_plan.refusal_category is None:
        raise RefusalExplanationSelectionError("Refusal category must be present when refusal is required.")

    mode = _category_baseline(control_plan.refusal_category)

    unknowns_present = bool(decision_state.explicit_unknown_zone)
    proximity = decision_state.proximity_state
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
        mode = RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME
    if posture == ExpressionPosture.CONSTRAINED:
        mode = _bump(mode, RefusalExplanationMode.BRIEF_BOUNDARY)
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT:
        mode = _bump(mode, RefusalExplanationMode.BRIEF_BOUNDARY)
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED:
        mode = _bump(mode, RefusalExplanationMode.BRIEF_BOUNDARY)

    # UNKNOWN COUPLING
    if unknowns_present and unknown_disclosure != UnknownDisclosureMode.NONE:
        mode = _bump(mode, RefusalExplanationMode.BOUNDED_EXPLANATION)
    if unknowns_present and unknown_disclosure == UnknownDisclosureMode.EXPLICIT:
        mode = _bump(mode, RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME)

    # HIGH-STAKES SUPPORT
    if high_stakes:
        mode = _bump(mode, RefusalExplanationMode.BRIEF_BOUNDARY)
        if proximity in {
            ProximityState.MEDIUM,
            ProximityState.HIGH,
            ProximityState.IMMINENT,
        }:
            mode = _bump(mode, RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME)

    # PROXIMITY ESCALATION
    if proximity in {ProximityState.HIGH, ProximityState.IMMINENT}:
        mode = _bump(mode, _raise_one(mode))

    # ACTION COMPATIBILITY / closure cap
    if closure != ClosureState.OPEN and friction != FrictionPosture.STOP:
        mode = RefusalExplanationMode.BRIEF_BOUNDARY

    # FINAL HARD CONSTRAINTS (fail-closed)
    strongest = RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME
    if friction == FrictionPosture.STOP and mode != strongest:
        raise RefusalExplanationSelectionError("STOP friction requires strongest refusal explanation mode.")
    if control_plan.refusal_required and mode is None:
        raise RefusalExplanationSelectionError("Refusal requires a non-NONE explanation mode.")
    if confidence_signaling == ConfidenceSignalingLevel.EXPLICIT and mode is None:
        raise RefusalExplanationSelectionError("EXPLICIT confidence forbids missing explanation mode.")
    if posture == ExpressionPosture.CONSTRAINED and mode is None:
        raise RefusalExplanationSelectionError("CONSTRAINED posture forbids missing explanation mode.")
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED and mode is None:
        raise RefusalExplanationSelectionError("ENFORCED rigor forbids missing explanation mode.")
    if unknowns_present and unknown_disclosure == UnknownDisclosureMode.EXPLICIT and mode is None:
        raise RefusalExplanationSelectionError("Unknown disclosure EXPLICIT forbids missing explanation mode.")

    return mode
