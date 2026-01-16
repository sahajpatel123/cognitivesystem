"""Phase 11 — Step 3: Confidence signaling planning.

Deterministically selects ConfidenceSignalingLevel using DecisionState, ControlPlan,
ExpressionPosture, and rigor_disclosure. No text generation, no models, no side effects.
"""

from typing import Iterable

from backend.mci_backend.control_plan import (
    ClosureState,
    ControlAction,
    ControlPlan,
    FrictionPosture,
    RefusalCategory,
    RigorLevel,
)
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    OutcomeClass,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)
from backend.mci_backend.output_plan import (
    ConfidenceSignalingLevel,
    ExpressionPosture,
    RigorDisclosureLevel,
)


class ConfidenceSignalingSelectionError(Exception):
    """Raised when confidence signaling selection cannot be determined."""


_ORDER = {
    ConfidenceSignalingLevel.MINIMAL: 0,
    ConfidenceSignalingLevel.GUARDED: 1,
    ConfidenceSignalingLevel.EXPLICIT: 2,
}

_RIGOR_ORDER = {
    RigorLevel.MINIMAL: 0,
    RigorLevel.GUARDED: 1,
    RigorLevel.STRUCTURED: 2,
    RigorLevel.ENFORCED: 3,
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


def _bump(current: ConfidenceSignalingLevel, target: ConfidenceSignalingLevel) -> ConfidenceSignalingLevel:
    return target if _ORDER[target] > _ORDER[current] else current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_conf]
    except KeyError as exc:
        raise ConfidenceSignalingSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx
        ):
            return True
    return False


def _dominance_min(control_plan: ControlPlan) -> ConfidenceSignalingLevel:
    mapping = {
        RigorLevel.MINIMAL: ConfidenceSignalingLevel.MINIMAL,
        RigorLevel.GUARDED: ConfidenceSignalingLevel.GUARDED,
        RigorLevel.STRUCTURED: ConfidenceSignalingLevel.GUARDED,
        RigorLevel.ENFORCED: ConfidenceSignalingLevel.EXPLICIT,
    }
    try:
        return mapping[control_plan.rigor_level]
    except KeyError as exc:
        raise ConfidenceSignalingSelectionError("Unknown control_plan.rigor_level.") from exc


def select_confidence_signaling(
    decision_state: DecisionState,
    control_plan: ControlPlan,
    posture: ExpressionPosture,
    rigor_disclosure: RigorDisclosureLevel,
) -> ConfidenceSignalingLevel:
    if decision_state is None or control_plan is None or posture is None or rigor_disclosure is None:
        raise ConfidenceSignalingSelectionError("decision_state, control_plan, posture, and rigor_disclosure are required.")

    signaling = ConfidenceSignalingLevel.MINIMAL

    unknowns_present = bool(decision_state.explicit_unknown_zone)
    proximity = decision_state.proximity_state
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)

    # HARD OVERRIDES
    if control_plan.refusal_required:
        if control_plan.closure_state != ClosureState.OPEN:
            signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
        signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)
    if control_plan.friction_posture == FrictionPosture.STOP:
        signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)
    if control_plan.closure_state != ClosureState.OPEN:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
    if proximity == ProximityState.IMMINENT:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
        if unknowns_present or critical_med or critical_low:
            signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)

    # UNKNOWN ZONE GATES
    if unknowns_present:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
        if proximity in {ProximityState.HIGH, ProximityState.IMMINENT}:
            signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)
    if OutcomeClass.UNKNOWN_OUTCOME_CLASS in decision_state.outcome_classes:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
        if proximity in {ProximityState.MEDIUM, ProximityState.HIGH, ProximityState.IMMINENT}:
            signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)

    # HIGH-STAKES ESCALATION
    if critical_med:
        if proximity in {ProximityState.MEDIUM, ProximityState.HIGH, ProximityState.IMMINENT}:
            signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)
        else:
            signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
    if decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
        if proximity in {ProximityState.HIGH, ProximityState.IMMINENT}:
            signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)
    if getattr(decision_state, "consequence_horizon", None) is not None:
        # Use string-safe check to avoid modifying locked enums beyond import.
        if str(decision_state.consequence_horizon).endswith("LONG_HORIZON"):
            signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
            if unknowns_present:
                signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)

    # RESPONSIBILITY ESCALATION
    if decision_state.responsibility_scope in {
        ResponsibilityScope.THIRD_PARTY,
        ResponsibilityScope.SYSTEMIC_PUBLIC,
    }:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
        if proximity in {ProximityState.HIGH, ProximityState.IMMINENT} or unknowns_present:
            signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)

    # COUPLING WITH POSTURE AND RIGOR DISCLOSURE
    if posture == ExpressionPosture.CONSTRAINED:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)
    elif posture == ExpressionPosture.BASELINE:
        pass  # no bump from posture alone
    elif posture == ExpressionPosture.GUARDED:
        pass
    else:
        raise ConfidenceSignalingSelectionError("Unknown posture enum.")

    if rigor_disclosure == RigorDisclosureLevel.ENFORCED:
        signaling = _bump(signaling, ConfidenceSignalingLevel.EXPLICIT)
    elif rigor_disclosure == RigorDisclosureLevel.STRUCTURED:
        signaling = _bump(signaling, ConfidenceSignalingLevel.GUARDED)

    # BASELINE ALLOW RULE
    baseline_ok = all(
        [
            not unknowns_present,
            proximity in {ProximityState.VERY_LOW, ProximityState.LOW},
            not critical_med,
            decision_state.reversibility_class != ReversibilityClass.IRREVERSIBLE,
            decision_state.responsibility_scope == ResponsibilityScope.SELF_ONLY,
            control_plan.closure_state == ClosureState.OPEN,
            not control_plan.refusal_required,
            control_plan.friction_posture in {FrictionPosture.NONE, FrictionPosture.SOFT_PAUSE},
            rigor_disclosure == RigorDisclosureLevel.MINIMAL,
            posture == ExpressionPosture.BASELINE,
            OutcomeClass.UNKNOWN_OUTCOME_CLASS not in decision_state.outcome_classes,
        ]
    )
    if baseline_ok:
        signaling = ConfidenceSignalingLevel.MINIMAL
    elif signaling == ConfidenceSignalingLevel.MINIMAL:
        signaling = ConfidenceSignalingLevel.GUARDED

    # Dominance rule: ensure not below control_plan.rigor_level mapping
    dominance_min = _dominance_min(control_plan)
    signaling = _bump(signaling, dominance_min)

    # Final hard constraints
    if rigor_disclosure == RigorDisclosureLevel.ENFORCED and signaling != ConfidenceSignalingLevel.EXPLICIT:
        raise ConfidenceSignalingSelectionError("ENFORCED rigor requires EXPLICIT confidence signaling.")
    if control_plan.refusal_required and signaling == ConfidenceSignalingLevel.MINIMAL:
        raise ConfidenceSignalingSelectionError("Refusal flows cannot use MINIMAL confidence signaling.")
    if control_plan.friction_posture == FrictionPosture.STOP and signaling != ConfidenceSignalingLevel.EXPLICIT:
        raise ConfidenceSignalingSelectionError("STOP friction requires EXPLICIT confidence signaling.")
    if control_plan.closure_state != ClosureState.OPEN and signaling == ConfidenceSignalingLevel.MINIMAL:
        raise ConfidenceSignalingSelectionError("Non-OPEN closure forbids MINIMAL confidence signaling.")

    return signaling
