from __future__ import annotations

"""
Phase 9 — Step 5: Outcome-Class Awareness (deterministic, bounded).

Populates only:
- outcome_classes (deduplicated bounded enums)
- explicit_unknown_zone (for outcome unknowns)

Forbidden:
- No prediction, probability, severity, or advice.
- No models, heuristics, personalization, or history.
- No modification of other DecisionState fields.
"""

from dataclasses import replace
from typing import Iterable, List, Set, Tuple

from .decision_state import (
    ConsequenceHorizon,
    DecisionState,
    OutcomeClass,
    ReversibilityClass,
    RiskDomain,
    UnknownSource,
    ResponsibilityScope,
)


def _lower(text: str | None) -> str:
    return (text or "").lower()


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def _text_markers() -> dict[OutcomeClass, dict[str, List[str]]]:
    return {
        OutcomeClass.FINANCIAL_OUTCOME: {
            "markers": ["payment", "wire", "bank", "invoice", "price", "budget", "cost", "buy", "sell"],
        },
        OutcomeClass.LEGAL_REGULATORY_OUTCOME: {
            "markers": ["illegal", "lawsuit", "regulation", "compliance", "violate", "breach", "contract", "policy"],
        },
        OutcomeClass.MEDICAL_BIOLOGICAL_OUTCOME: {
            "markers": ["surgery", "prescription", "dose", "diagnosis", "clinical", "health", "treatment"],
        },
        OutcomeClass.PHYSICAL_SAFETY_OUTCOME: {
            "markers": ["weapon", "attack", "hazard", "injury", "crash", "dangerous", "safety"],
        },
        OutcomeClass.PSYCHOLOGICAL_EMOTIONAL_OUTCOME: {
            "markers": ["stress", "anxiety", "depressed", "panic", "trauma", "self-harm", "bullying"],
        },
        OutcomeClass.ETHICAL_MORAL_OUTCOME: {
            "markers": ["ethical", "moral", "plagiarize", "cheat", "fraud", "bribe", "integrity"],
        },
        OutcomeClass.REPUTATIONAL_SOCIAL_OUTCOME: {
            "markers": ["publicly", "publish", "broadcast", "reputation", "defamation", "slander", "libel", "backlash"],
        },
        OutcomeClass.OPERATIONAL_SYSTEM_OUTCOME: {
            "markers": ["outage", "downtime", "deployment", "rollback", "system failure", "maintenance"],
        },
        OutcomeClass.IRREVERSIBLE_PERSONAL_HARM_OUTCOME: {
            "markers": ["irreversible", "permanent damage", "cannot undo", "lifelong"],
        },
    }


def _classify_from_text(message: str, framing: str) -> Set[OutcomeClass]:
    outcomes: Set[OutcomeClass] = set()
    markers = _text_markers()
    for outcome, data in markers.items():
        if _contains_any(message, data["markers"]) or _contains_any(framing, data["markers"]):
            outcomes.add(outcome)
    return outcomes


def _classify_from_state(decision_state: DecisionState) -> Set[OutcomeClass]:
    outcomes: Set[OutcomeClass] = set()
    domain_map = {
        RiskDomain.FINANCIAL: OutcomeClass.FINANCIAL_OUTCOME,
        RiskDomain.LEGAL_REGULATORY: OutcomeClass.LEGAL_REGULATORY_OUTCOME,
        RiskDomain.MEDICAL_BIOLOGICAL: OutcomeClass.MEDICAL_BIOLOGICAL_OUTCOME,
        RiskDomain.PHYSICAL_SAFETY: OutcomeClass.PHYSICAL_SAFETY_OUTCOME,
        RiskDomain.PSYCHOLOGICAL_EMOTIONAL: OutcomeClass.PSYCHOLOGICAL_EMOTIONAL_OUTCOME,
        RiskDomain.ETHICAL_MORAL: OutcomeClass.ETHICAL_MORAL_OUTCOME,
        RiskDomain.REPUTATIONAL_SOCIAL: OutcomeClass.REPUTATIONAL_SOCIAL_OUTCOME,
        RiskDomain.OPERATIONAL_SYSTEMIC: OutcomeClass.OPERATIONAL_SYSTEM_OUTCOME,
        RiskDomain.IRREVERSIBLE_PERSONAL_HARM: OutcomeClass.IRREVERSIBLE_PERSONAL_HARM_OUTCOME,
        RiskDomain.LEGAL_ADJACENT_GRAY_ZONE: OutcomeClass.LEGAL_REGULATORY_OUTCOME,
        RiskDomain.UNKNOWN: OutcomeClass.UNKNOWN_OUTCOME_CLASS,
    }
    for assessment in decision_state.risk_domains:
        mapped = domain_map.get(assessment.domain)
        if mapped:
            outcomes.add(mapped)

    # Responsibility-driven signals
    if decision_state.responsibility_scope is ResponsibilityScope.SYSTEMIC_PUBLIC:
        outcomes.add(OutcomeClass.REPUTATIONAL_SOCIAL_OUTCOME)
        outcomes.add(OutcomeClass.OPERATIONAL_SYSTEM_OUTCOME)
    if decision_state.responsibility_scope is ResponsibilityScope.THIRD_PARTY:
        outcomes.add(OutcomeClass.ETHICAL_MORAL_OUTCOME)
    if decision_state.responsibility_scope is ResponsibilityScope.SHARED:
        outcomes.add(OutcomeClass.ETHICAL_MORAL_OUTCOME)

    # Horizon + irreversibility hints
    if (
        decision_state.consequence_horizon is ConsequenceHorizon.LONG_HORIZON
        or decision_state.reversibility_class is ReversibilityClass.IRREVERSIBLE
    ):
        outcomes.add(OutcomeClass.IRREVERSIBLE_PERSONAL_HARM_OUTCOME)

    return outcomes


def _enforce_invariants(
    outcomes: Set[OutcomeClass],
    explicit_unknown_zone: Tuple[UnknownSource, ...],
) -> Tuple[Tuple[OutcomeClass, ...], Tuple[UnknownSource, ...]]:
    unknowns = list(explicit_unknown_zone)

    if not outcomes:
        outcomes.add(OutcomeClass.UNKNOWN_OUTCOME_CLASS)
    if OutcomeClass.UNKNOWN_OUTCOME_CLASS in outcomes and UnknownSource.OUTCOME_CLASSES not in unknowns:
        unknowns.append(UnknownSource.OUTCOME_CLASSES)

    # Deduplicate (set already) and ensure bounded enums.
    for oc in outcomes:
        if oc not in OutcomeClass:
            raise ValueError("All outcome_classes must be bounded OutcomeClass enums.")

    return tuple(outcomes), tuple(unknowns)


def apply_outcome_classes(
    decision_state: DecisionState,
    message: str,
    intent_framing: str | None = None,
) -> DecisionState:
    """
    Populate outcome_classes deterministically.

    Inputs:
    - message: current user message only.
    - intent_framing: optional Phase 4 framing.
    """
    text = _lower(message)
    framing = _lower(intent_framing)

    outcomes: Set[OutcomeClass] = set()
    outcomes.update(_classify_from_text(text, framing))
    outcomes.update(_classify_from_state(decision_state))

    outcomes_tuple, unknowns_tuple = _enforce_invariants(outcomes, decision_state.explicit_unknown_zone)

    return replace(
        decision_state,
        outcome_classes=outcomes_tuple,
        explicit_unknown_zone=unknowns_tuple,
    )
