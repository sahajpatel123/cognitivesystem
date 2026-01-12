"""Phase 10 — Step 6: Decision closure detection.

Determines bounded closure_state based on deterministic markers and context.
No text generation, no models, no orchestration.
"""

from dataclasses import dataclass
from typing import Iterable

from mci_backend.control_plan import ClosureState, FrictionPosture, RigorLevel
from mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)


class ClosureDetectionError(ValueError):
    """Raised when closure detection cannot be completed due to invalid inputs."""


@dataclass(frozen=True)
class ClosureDecision:
    closure_state: ClosureState


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

_STRONG_TERMINATION_MARKERS = {
    "i decided",
    "i've decided",
    "i will do it",
    "i’m going ahead",
    "i am going ahead",
    "done",
    "stop",
    "no more",
    "end",
    "i’m leaving",
    "i am leaving",
    "don't ask",
    "do not ask",
    "close this",
}

_REFUSAL_MARKERS = {
    "i won’t answer",
    "i will not answer",
    "doesn’t matter",
    "does not matter",
    "just answer",
}

_WEAK_MARKERS = {
    "ok",
    "okay",
    "cool",
    "thanks",
    "thank you",
    "got it",
}


def _has_critical_domain(
    risks: Iterable[RiskAssessment], min_confidence: ConfidenceLevel
) -> bool:
    try:
        min_idx = _CONFIDENCE_ORDER.index(min_confidence)
    except ValueError as exc:
        raise ClosureDetectionError("Invalid confidence level for comparison.") from exc
    for assessment in risks:
        if (
            assessment.domain in _CRITICAL_DOMAINS
            and _CONFIDENCE_ORDER.index(assessment.confidence) >= min_idx
        ):
            return True
    return False


def detect_closure(
    user_text: str,
    decision_state: DecisionState,
    rigor_level: RigorLevel,
    friction_posture: FrictionPosture,
    clarification_required: bool,
    question_budget: int,
) -> ClosureDecision:
    """
    Deterministically decide closure_state.
    """
    if decision_state is None:
        raise ClosureDetectionError("DecisionState is required.")
    if rigor_level is None:
        raise ClosureDetectionError("rigor_level is required.")
    if friction_posture is None:
        raise ClosureDetectionError("friction_posture is required.")
    if question_budget not in (0, 1):
        raise ClosureDetectionError("question_budget must be 0 or 1.")
    if clarification_required and question_budget != 1:
        raise ClosureDetectionError(
            "clarification_required=True requires question_budget=1."
        )

    normalized = (user_text or "").strip().lower()
    critical_low = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.LOW)
    critical_med = _has_critical_domain(decision_state.risk_domains, ConfidenceLevel.MEDIUM)
    significant_unknowns = bool(decision_state.explicit_unknown_zone)

    # Rule ladder: first match wins.

    # Strong termination markers -> USER_TERMINATED
    for marker in _STRONG_TERMINATION_MARKERS:
        if marker in normalized:
            return ClosureDecision(closure_state=ClosureState.USER_TERMINATED)

    # Refusal markers with high friction or high stakes -> USER_TERMINATED
    high_stakes = (
        critical_low
        or decision_state.reversibility_class == ReversibilityClass.IRREVERSIBLE
        or decision_state.responsibility_scope
        in {ResponsibilityScope.THIRD_PARTY, ResponsibilityScope.SYSTEMIC_PUBLIC}
        or friction_posture in {FrictionPosture.HARD_PAUSE, FrictionPosture.STOP}
    )
    for marker in _REFUSAL_MARKERS:
        if marker in normalized:
            if high_stakes:
                return ClosureDecision(closure_state=ClosureState.USER_TERMINATED)
            return ClosureDecision(closure_state=ClosureState.CLOSED)

    # Strong decision-finalization markers -> CLOSED
    decision_markers = {"i decided", "i've decided", "i will do it", "done", "i’m going ahead", "i am going ahead"}
    for marker in decision_markers:
        if marker in normalized:
            return ClosureDecision(closure_state=ClosureState.CLOSED)

    # Weak markers: only close when low stakes and no pending clarification.
    if normalized in _WEAK_MARKERS:
        low_stakes = (
            decision_state.proximity_state in {ProximityState.VERY_LOW, ProximityState.LOW}
            and decision_state.reversibility_class != ReversibilityClass.IRREVERSIBLE
            and not critical_med
            and decision_state.responsibility_scope == ResponsibilityScope.SELF_ONLY
        )
        if low_stakes and not clarification_required:
            return ClosureDecision(closure_state=ClosureState.CLOSING)

    # Default: remain open
    return ClosureDecision(closure_state=ClosureState.OPEN)
