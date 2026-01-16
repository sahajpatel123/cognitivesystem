"""Phase 11 — Step 1: Expression posture selection.

Deterministically selects ExpressionPosture using DecisionState + ControlPlan.
No text generation, no models, no side effects.
"""

from enum import Enum
from typing import Iterable

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
from backend.mci_backend.control_plan import (
    ClarificationReason,
    ClosureState,
    ControlAction,
    ControlPlan,
    FrictionPosture,
)
from backend.mci_backend.output_plan import ExpressionPosture


class ExpressionPostureSelectionError(Exception):
    """Raised when posture selection cannot be determined due to invalid inputs."""


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

_POSTURE_ORDER = {
    ExpressionPosture.BASELINE: 0,
    ExpressionPosture.GUARDED: 1,
    ExpressionPosture.CONSTRAINED: 2,
}


def _bump(current: ExpressionPosture, target: ExpressionPosture) -> ExpressionPosture:
    if _POSTURE_ORDER[target] > _POSTURE_ORDER[current]:
        return target
    return current


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_confidence: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER[min_confidence]
    except KeyError as exc:
        raise ExpressionPostureSelectionError("Invalid confidence level.") from exc
    for assessment in risks:
        if assessment.domain in _CRITICAL_DOMAINS:
            if _CONFIDENCE_ORDER.get(assessment.confidence, -1) >= min_idx:
                return True
    return False


def select_expression_posture(
    decision_state: DecisionState, control_plan: ControlPlan
) -> ExpressionPosture:
    if decision_state is None or control_plan is None:
        raise ExpressionPostureSelectionError("decision_state and control_plan are required.")

    posture = ExpressionPosture.BASELINE

    critical_mid = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)
    unknowns_present = bool(decision_state.explicit_unknown_zone)

    proximity = decision_state.proximity_state

    # HARD OVERRIDES
    if control_plan.refusal_required or control_plan.action == ControlAction.REFUSE:
        return ExpressionPosture.CONSTRAINED
    if control_plan.friction_posture == FrictionPosture.STOP:
        return ExpressionPosture.CONSTRAINED
    if control_plan.closure_state != ClosureState.OPEN:
        posture = _bump(posture, ExpressionPosture.GUARDED)

    # HIGH-STAKES TRIGGERS
    if critical_mid:
        posture = _bump(posture, ExpressionPosture.CONSTRAINED)
    if decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE:
        posture = _bump(posture, ExpressionPosture.GUARDED)
        if proximity in {ProximityState.HIGH, ProximityState.IMMINENT}:
            posture = _bump(posture, ExpressionPosture.CONSTRAINED)
    if decision_state.consequence_horizon == ConsequenceHorizon.LONG_HORIZON:
        posture = _bump(posture, ExpressionPosture.GUARDED)
    if decision_state.responsibility_scope in {
        ResponsibilityScope.THIRD_PARTY,
        ResponsibilityScope.SYSTEMIC_PUBLIC,
    }:
        posture = _bump(posture, ExpressionPosture.GUARDED)
        if proximity in {ProximityState.HIGH, ProximityState.IMMINENT}:
            posture = _bump(posture, ExpressionPosture.CONSTRAINED)

    # UNKNOWN / UNCERTAINTY ESCALATION
    if proximity in {ProximityState.MEDIUM, ProximityState.HIGH, ProximityState.IMMINENT} and unknowns_present:
        posture = _bump(posture, ExpressionPosture.GUARDED)
    if proximity in {ProximityState.HIGH, ProximityState.IMMINENT} and unknowns_present:
        posture = _bump(posture, ExpressionPosture.CONSTRAINED)

    # CLARIFICATION PATH
    if control_plan.action == ControlAction.ASK_ONE_QUESTION or control_plan.clarification_required:
        posture = _bump(posture, ExpressionPosture.GUARDED)
        if critical_mid or decision_state.responsibility_scope in {
            ResponsibilityScope.THIRD_PARTY,
            ResponsibilityScope.SYSTEMIC_PUBLIC,
        }:
            posture = _bump(posture, ExpressionPosture.CONSTRAINED)

    # BASELINE ALLOW RULE
    if posture == ExpressionPosture.BASELINE:
        baseline_ok = all(
            [
                proximity in {ProximityState.VERY_LOW, ProximityState.LOW},
                not critical_mid,
                decision_state.reversibility_class != ReversibilityClass.IRREVERSIBLE,
                decision_state.consequence_horizon != ConsequenceHorizon.LONG_HORIZON,
                decision_state.responsibility_scope == ResponsibilityScope.SELF_ONLY,
                not unknowns_present,
                control_plan.action not in {ControlAction.ASK_ONE_QUESTION, ControlAction.REFUSE, ControlAction.CLOSE},
                not control_plan.clarification_required,
                control_plan.friction_posture in {FrictionPosture.NONE, FrictionPosture.SOFT_PAUSE},
                control_plan.closure_state == ClosureState.OPEN,
                not control_plan.refusal_required,
            ]
        )
        if not baseline_ok:
            posture = ExpressionPosture.GUARDED

    return posture
