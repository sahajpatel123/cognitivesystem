"""Phase 10 — Step 5: Bounded initiative and intervention budget.

Deterministically sets initiative budgets to prevent nagging, loops, or repeated
warnings/clarifications. No text generation, no models, no orchestration.
"""

from dataclasses import dataclass
from typing import Iterable

from backend.mci_backend.control_plan import FrictionPosture, InitiativeBudget, RigorLevel
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class InitiativeSelectionError(ValueError):
    """Raised when initiative selection cannot be performed due to invalid input."""


@dataclass(frozen=True)
class InitiativeDecision:
    initiative_budget: InitiativeBudget
    warning_budget: int

    def __post_init__(self) -> None:
        if self.warning_budget not in (0, 1):
            raise InitiativeSelectionError("warning_budget must be 0 or 1.")


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
        raise InitiativeSelectionError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_idx
        ):
            return True
    return False


def select_initiative(
    decision_state: DecisionState,
    rigor_level: RigorLevel,
    friction_posture: FrictionPosture,
    clarification_required: bool,
    question_budget: int,
) -> InitiativeDecision:
    """
    Deterministically select bounded initiative and warning budgets.
    Preconditions: clarification/question budgets must be consistent with Phase 10 steps.
    """
    if decision_state is None:
        raise InitiativeSelectionError("DecisionState is required.")
    if rigor_level is None:
        raise InitiativeSelectionError("rigor_level is required.")
    if friction_posture is None:
        raise InitiativeSelectionError("friction_posture is required.")
    if clarification_required and question_budget != 1:
        raise InitiativeSelectionError(
            "clarification_required=True must align with question_budget=1."
        )
    if not clarification_required and question_budget not in (0, 1):
        raise InitiativeSelectionError("question_budget must be 0 or 1.")

    significant_unknowns = bool(decision_state.explicit_unknown_zone)
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)

    initiative = InitiativeBudget.NONE
    warning_budget = 0

    # Low proximity baseline
    if decision_state.proximity_state in {ProximityState.VERY_LOW, ProximityState.LOW}:
        if critical_low and significant_unknowns:
            initiative = InitiativeBudget.ONCE
            warning_budget = 1
        else:
            initiative = InitiativeBudget.NONE
            warning_budget = 0

    # Medium proximity
    elif decision_state.proximity_state == ProximityState.MEDIUM:
        if (
            significant_unknowns
            or decision_state.responsibility_scope
            in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
            or critical_low
        ):
            initiative = InitiativeBudget.ONCE
            warning_budget = 1 if not clarification_required else 0
        else:
            initiative = InitiativeBudget.NONE
            warning_budget = 0

    # High / Imminent proximity
    elif decision_state.proximity_state in {ProximityState.HIGH, ProximityState.IMMINENT}:
        high_stakes = (
            critical_low
            or decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
            or decision_state.responsibility_scope
            in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
            or friction_posture
            in {FrictionPosture.HARD_PAUSE, FrictionPosture.STOP}
        )
        if high_stakes or significant_unknowns:
            initiative = InitiativeBudget.STRICT_ONCE
            warning_budget = 1 if not clarification_required else 0
        else:
            initiative = InitiativeBudget.ONCE
            warning_budget = 1 if not clarification_required else 0
    else:
        raise InitiativeSelectionError("Unsupported proximity_state.")

    # Clarification consumes initiative slot; do not allow extra warnings.
    if clarification_required:
        initiative = InitiativeBudget.ONCE if initiative != InitiativeBudget.NONE else InitiativeBudget.ONCE
        warning_budget = 0

    return InitiativeDecision(
        initiative_budget=initiative,
        warning_budget=warning_budget,
    )
