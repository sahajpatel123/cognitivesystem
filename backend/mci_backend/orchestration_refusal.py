"""Phase 10 — Step 7: Refusal trigger logic.

Deterministically decides if refusal is required and assigns a bounded category.
No text generation, no models, no orchestration assembly.
"""

from dataclasses import dataclass
from typing import Iterable

from backend.mci_backend.control_plan import (
    ClosureState,
    FrictionPosture,
    RefusalCategory,
    RigorLevel,
)
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class RefusalDecisionError(ValueError):
    """Raised when refusal decision cannot be determined due to invalid inputs."""


@dataclass(frozen=True)
class RefusalDecision:
    refusal_required: bool
    refusal_category: RefusalCategory


_CONFIDENCE_ORDER = [
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
    risks: Iterable[RiskAssessment], min_confidence: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER.index(min_confidence)
    except ValueError as exc:
        raise RefusalDecisionError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_idx
        ):
            return True
    return False


def decide_refusal(
    decision_state: DecisionState,
    rigor_level: RigorLevel,
    friction_posture: FrictionPosture,
    clarification_required: bool,
    question_budget: int,
    closure_state: ClosureState,
) -> RefusalDecision:
    """
    Deterministically decide refusal requirement.
    """
    if decision_state is None:
        raise RefusalDecisionError("DecisionState is required.")
    if rigor_level is None:
        raise RefusalDecisionError("rigor_level is required.")
    if friction_posture is None:
        raise RefusalDecisionError("friction_posture is required.")
    if closure_state is None:
        raise RefusalDecisionError("closure_state is required.")
    if question_budget not in (0, 1):
        raise RefusalDecisionError("question_budget must be 0 or 1.")
    if clarification_required and question_budget != 1:
        raise RefusalDecisionError(
            "clarification_required=True requires question_budget=1."
        )

    significant_unknowns = bool(decision_state.explicit_unknown_zone)
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)

    # Tier 1: Closure already ended interaction.
    if closure_state == ClosureState.USER_TERMINATED:
        return RefusalDecision(refusal_required=False, refusal_category=RefusalCategory.NONE)

    # Future governance/kill-switch placeholder (not active now).
    # if governance_triggered:
    #     return RefusalDecision(True, RefusalCategory.GOVERNANCE_REFUSAL)

    # Tier 2: Critical domain + high/imminent + unknowns + no clarification path.
    if (
        decision_state.proximity_state in {ProximityState.HIGH, ProximityState.IMMINENT}
        and critical_med
        and significant_unknowns
        and (not clarification_required or question_budget == 0)
    ):
        return RefusalDecision(
            refusal_required=True, refusal_category=RefusalCategory.RISK_REFUSAL
        )

    # Tier 3: Irreversibility refusal.
    if (
        decision_state.proximity_state == ProximityState.IMMINENT
        and decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
        and significant_unknowns
        and not clarification_required
    ):
        return RefusalDecision(
            refusal_required=True,
            refusal_category=RefusalCategory.IRREVERSIBILITY_REFUSAL,
        )

    # Tier 4: Third-party/systemic refusal.
    if (
        decision_state.responsibility_scope
        in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
        and decision_state.proximity_state
        in {ProximityState.MEDIUM, ProximityState.HIGH, ProximityState.IMMINENT}
        and significant_unknowns
        and not clarification_required
    ):
        return RefusalDecision(
            refusal_required=True,
            refusal_category=RefusalCategory.THIRD_PARTY_REFUSAL,
        )

    # Tier 5: Capability refusal placeholder (rare): previously mapped to TECHNICAL_LIMIT.
    if friction_posture == FrictionPosture.STOP and critical_low and significant_unknowns:
        return RefusalDecision(
            refusal_required=True,
            refusal_category=RefusalCategory.CAPABILITY_REFUSAL,
        )

    # Default: proceed (no refusal).
    return RefusalDecision(refusal_required=False, refusal_category=RefusalCategory.NONE)
