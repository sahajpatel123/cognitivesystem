"""Phase 10 — Step 3: Clarification trigger decision.

Determines if a single clarification is required (yes/no) before proceeding.
No question selection, no text generation, no models, no orchestration.
"""

from dataclasses import dataclass
from typing import Optional, Sequence

from backend.mci_backend.control_plan import ClarificationReason, FrictionPosture, RigorLevel
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class ClarificationTriggerError(ValueError):
    """Raised when clarification decision cannot be determined due to invalid input."""


@dataclass(frozen=True)
class ClarificationDecision:
    clarification_required: bool
    clarification_reason: ClarificationReason
    question_budget: int

    def __post_init__(self) -> None:
        if self.question_budget not in (0, 1):
            raise ClarificationTriggerError("question_budget must be 0 or 1.")
        if self.clarification_required and self.question_budget != 1:
            raise ClarificationTriggerError(
                "clarification_required=True requires question_budget=1."
            )
        if not self.clarification_required and self.question_budget != 0:
            raise ClarificationTriggerError(
                "clarification_required=False requires question_budget=0."
            )


_CONFIDENCE_ORDER: Sequence[ConfidenceLevel] = [
    ConfidenceLevel.LOW,
    ConfidenceLevel.MEDIUM,
    ConfidenceLevel.HIGH,
]

_CRITICAL_DOMAINS = {
    RiskDomain.LEGAL_REGULATORY,
    RiskDomain.MEDICAL_BIOLOGICAL,
    RiskDomain.PHYSICAL_SAFETY,
}


def _has_critical_domain(
    risks: Sequence[RiskAssessment], min_conf: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER.index(min_conf)
    except ValueError as exc:
        raise ClarificationTriggerError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_idx
        ):
            return True
    return False


def decide_clarification(
    decision_state: DecisionState,
    rigor_level: RigorLevel,
    friction_posture: FrictionPosture,
) -> ClarificationDecision:
    """
    Deterministically decide if clarification is required.
    Returns ClarificationDecision with bounded fields only.
    """
    if decision_state is None:
        raise ClarificationTriggerError("DecisionState is required.")
    if rigor_level is None:
        raise ClarificationTriggerError("rigor_level is required.")
    if friction_posture is None:
        raise ClarificationTriggerError("friction_posture is required.")

    significant_unknowns = bool(decision_state.explicit_unknown_zone)
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)

    required = False
    reason = ClarificationReason.UNKNOWN

    # VERY_LOW / LOW proximity: default proceed
    if decision_state.proximity_state in {ProximityState.VERY_LOW, ProximityState.LOW}:
        if critical_med and significant_unknowns:
            required = True
            reason = ClarificationReason.SAFETY
        elif (
            decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
            and significant_unknowns
        ):
            required = True
            reason = ClarificationReason.SAFETY
        else:
            required = False
            reason = ClarificationReason.UNKNOWN

    # MEDIUM proximity
    elif decision_state.proximity_state == ProximityState.MEDIUM:
        if critical_med:
            required = True
            reason = ClarificationReason.SAFETY
        elif decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE:
            required = True
            reason = ClarificationReason.SAFETY
        elif decision_state.responsibility_scope in {
            ResponsibilityScope.THIRD_PARTY,
            ResponsibilityScope.SYSTEMIC_PUBLIC,
        }:
            required = True
            reason = ClarificationReason.SCOPE_CONFIRMATION
        elif friction_posture in {
            FrictionPosture.SOFT_PAUSE,
            FrictionPosture.HARD_PAUSE,
            FrictionPosture.STOP,
        } and significant_unknowns:
            required = True
            reason = ClarificationReason.MISSING_CONTEXT
        elif significant_unknowns and rigor_level in {
            RigorLevel.STRUCTURED,
            RigorLevel.ENFORCED,
        }:
            required = True
            reason = ClarificationReason.MISSING_CONTEXT
        else:
            required = False
            reason = ClarificationReason.UNKNOWN

    # HIGH / IMMINENT proximity
    elif decision_state.proximity_state in {ProximityState.HIGH, ProximityState.IMMINENT}:
        if (
            significant_unknowns
            or decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
            or decision_state.responsibility_scope
            in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
            or critical_low
            or friction_posture
            in {FrictionPosture.HARD_PAUSE, FrictionPosture.STOP}
        ):
            required = True
            if significant_unknowns:
                reason = ClarificationReason.MISSING_CONTEXT
            elif decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE:
                reason = ClarificationReason.SAFETY
            elif decision_state.responsibility_scope in {
                ResponsibilityScope.THIRD_PARTY,
                ResponsibilityScope.SYSTEMIC_PUBLIC,
            }:
                reason = ClarificationReason.SCOPE_CONFIRMATION
            else:
                reason = ClarificationReason.SAFETY
        else:
            required = False
            reason = ClarificationReason.UNKNOWN

    else:
        raise ClarificationTriggerError("Unsupported proximity_state.")

    question_budget = 1 if required else 0
    return ClarificationDecision(
        clarification_required=required,
        clarification_reason=reason,
        question_budget=question_budget,
    )
