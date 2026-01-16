"""Phase 10 — Step 4: Single-question compression.

Select exactly one bounded question_class when clarification is required.
No wording, no multi-question behavior, no models, no orchestration.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from backend.mci_backend.control_plan import ClarificationReason, FrictionPosture, QuestionClass, RigorLevel
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class QuestionCompressionError(ValueError):
    """Raised when a single-question selection cannot be made deterministically."""


class QuestionPriorityReason(Enum):
    SAFETY_CRITICAL = "SAFETY_CRITICAL"
    LEGAL_CONTEXT = "LEGAL_CONTEXT"
    SCOPE_CLARIFICATION = "SCOPE_CLARIFICATION"
    IRREVERSIBILITY = "IRREVERSIBILITY"
    CONSTRAINT_GAP = "CONSTRAINT_GAP"
    INTENT_AMBIGUITY = "INTENT_AMBIGUITY"
    UNKNOWN_CONTEXT = "UNKNOWN_CONTEXT"


@dataclass(frozen=True)
class QuestionSelection:
    question_class: QuestionClass
    priority_reason: QuestionPriorityReason


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
        raise QuestionCompressionError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_idx
        ):
            return True
    return False


def select_single_question(
    decision_state: DecisionState,
    clarification_reason: ClarificationReason,
    rigor_level: RigorLevel,
    friction_posture: FrictionPosture,
    clarification_required: bool,
    question_budget: int,
) -> QuestionSelection:
    """
    Deterministically choose exactly one question_class.
    Preconditions: clarification_required=True and question_budget==1.
    """
    if decision_state is None:
        raise QuestionCompressionError("DecisionState is required.")
    if clarification_reason is None:
        raise QuestionCompressionError("clarification_reason is required.")
    if rigor_level is None:
        raise QuestionCompressionError("rigor_level is required.")
    if friction_posture is None:
        raise QuestionCompressionError("friction_posture is required.")
    if not clarification_required or question_budget != 1:
        raise QuestionCompressionError("Single-question selection requires clarification_required=True and question_budget==1.")

    significant_unknowns = bool(decision_state.explicit_unknown_zone)
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)

    # Priority-ordered rule ladder (first match wins)

    # Tier 1: Safety/Legal gating
    if critical_med and significant_unknowns:
        return QuestionSelection(
            question_class=QuestionClass.SAFETY_GUARD,
            priority_reason=QuestionPriorityReason.SAFETY_CRITICAL,
        )
    if critical_med and clarification_reason in {
        ClarificationReason.SAFETY,
        ClarificationReason.SCOPE_CONFIRMATION,
    }:
        return QuestionSelection(
            question_class=QuestionClass.SAFETY_GUARD,
            priority_reason=QuestionPriorityReason.SAFETY_CRITICAL,
        )
    if critical_med and decision_state.responsibility_scope in {
        ResponsibilityScope.THIRD_PARTY,
        ResponsibilityScope.SYSTEMIC_PUBLIC,
    }:
        return QuestionSelection(
            question_class=QuestionClass.SAFETY_GUARD,
            priority_reason=QuestionPriorityReason.LEGAL_CONTEXT,
        )

    # Tier 2: Irreversibility + imminent/high proximity with unknowns
    if (
        decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
        and decision_state.proximity_state in {ProximityState.HIGH, ProximityState.IMMINENT}
        and significant_unknowns
    ):
        return QuestionSelection(
            question_class=QuestionClass.SAFETY_GUARD,
            priority_reason=QuestionPriorityReason.IRREVERSIBILITY,
        )

    # Tier 3: Responsibility (third-party/systemic) with unknowns
    if decision_state.responsibility_scope in {
        ResponsibilityScope.THIRD_PARTY,
        ResponsibilityScope.SYSTEMIC_PUBLIC,
    } and significant_unknowns:
        return QuestionSelection(
            question_class=QuestionClass.CONSENT,
            priority_reason=QuestionPriorityReason.SCOPE_CLARIFICATION,
        )

    # Tier 4: Constraints / narrowing for non-safety critical gaps
    if clarification_reason in {
        ClarificationReason.MISSING_CONTEXT,
    } and significant_unknowns:
        return QuestionSelection(
            question_class=QuestionClass.OTHER_BOUNDARY,
            priority_reason=QuestionPriorityReason.CONSTRAINT_GAP,
        )
    if friction_posture in {FrictionPosture.HARD_PAUSE, FrictionPosture.STOP} and significant_unknowns:
        return QuestionSelection(
            question_class=QuestionClass.OTHER_BOUNDARY,
            priority_reason=QuestionPriorityReason.CONSTRAINT_GAP,
        )
    if rigor_level in {RigorLevel.STRUCTURED, RigorLevel.ENFORCED} and significant_unknowns:
        return QuestionSelection(
            question_class=QuestionClass.OTHER_BOUNDARY,
            priority_reason=QuestionPriorityReason.CONSTRAINT_GAP,
        )

    # Tier 5: Intent ambiguity
    if clarification_reason == ClarificationReason.DISAMBIGUATION:
        return QuestionSelection(
            question_class=QuestionClass.INFORMATIONAL,
            priority_reason=QuestionPriorityReason.INTENT_AMBIGUITY,
        )

    # Fallback: unknown context but clarification required — pick informational/consent depending on responsibility
    if critical_low:
        return QuestionSelection(
            question_class=QuestionClass.SAFETY_GUARD,
            priority_reason=QuestionPriorityReason.UNKNOWN_CONTEXT,
        )
    if decision_state.responsibility_scope in {
        ResponsibilityScope.THIRD_PARTY,
        ResponsibilityScope.SYSTEMIC_PUBLIC,
    }:
        return QuestionSelection(
            question_class=QuestionClass.CONSENT,
            priority_reason=QuestionPriorityReason.SCOPE_CLARIFICATION,
        )
    return QuestionSelection(
        question_class=QuestionClass.INFORMATIONAL,
        priority_reason=QuestionPriorityReason.UNKNOWN_CONTEXT,
    )
