from __future__ import annotations

"""
Phase 9 — Step 2: Risk Domain Classification Engine (deterministic, bounded).

Responsibilities:
- Populate DecisionState.risk_domains with bounded RiskDomain enums.
- Assign per-domain ConfidenceLevel (LOW, MEDIUM, HIGH); no UNKNOWN confidence.
- Bias toward inclusion; ambiguity → include with LOW confidence and mark unknowns.

Forbidden:
- No probability/severity estimates, no outcome prediction, no advice/mitigation.
- No models, heuristics, personalization, or external data.
- No modification of other DecisionState fields beyond risk domains and unknown markers.
"""

from dataclasses import replace
from typing import Iterable, List, Tuple

from .decision_state import (
    ConfidenceLevel,
    DecisionState,
    RiskAssessment,
    RiskDomain,
    UnknownSource,
    ProximityState,
)


def _lower(text: str | None) -> str:
    return (text or "").lower()


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def _domain_markers() -> dict[RiskDomain, dict[str, List[str]]]:
    return {
        RiskDomain.FINANCIAL: {
            "high": ["payment", "wire", "transfer", "bank", "invoice", "price", "budget"],
            "medium": ["cost", "spend", "buy", "sell", "refund"],
        },
        RiskDomain.LEGAL_REGULATORY: {
            "high": ["illegal", "lawsuit", "regulation", "compliance", "violate", "breach"],
            "medium": ["contract", "terms", "policy", "license"],
        },
        RiskDomain.MEDICAL_BIOLOGICAL: {
            "high": ["surgery", "prescription", "dose", "diagnosis", "clinical", "biological"],
            "medium": ["health", "symptom", "treatment", "therapy"],
        },
        RiskDomain.PHYSICAL_SAFETY: {
            "high": ["weapon", "attack", "crash", "hazard", "injury", "kill"],
            "medium": ["dangerous", "safety", "accident", "exposure"],
        },
        RiskDomain.PSYCHOLOGICAL_EMOTIONAL: {
            "high": ["self-harm", "suicide", "panic", "trauma"],
            "medium": ["stress", "anxiety", "depressed", "bullying"],
        },
        RiskDomain.ETHICAL_MORAL: {
            "high": ["plagiarize", "cheat", "fraud", "bribe"],
            "medium": ["fair", "ethical", "moral", "integrity"],
        },
        RiskDomain.REPUTATIONAL_SOCIAL: {
            "high": ["defamation", "slander", "libel", "cancel"],
            "medium": ["public image", "reputation", "social backlash"],
        },
        RiskDomain.OPERATIONAL_SYSTEMIC: {
            "high": ["outage", "downtime", "system failure"],
            "medium": ["deployment", "rollback", "maintenance"],
        },
        RiskDomain.IRREVERSIBLE_PERSONAL_HARM: {
            "high": ["irreversible", "permanent damage"],
            "medium": ["lifelong", "cannot undo"],
        },
        RiskDomain.LEGAL_ADJACENT_GRAY_ZONE: {
            "high": ["loophole", "gray area", "grey area"],
            "medium": ["borderline", "edge case"],
        },
    }


def _classify_domains(text: str, framing: str) -> List[RiskAssessment]:
    assessments: List[RiskAssessment] = []
    markers = _domain_markers()
    for domain, levels in markers.items():
        confidence: ConfidenceLevel | None = None
        if _contains_any(text, levels["high"]) or _contains_any(framing, levels["high"]):
            confidence = ConfidenceLevel.HIGH
        elif _contains_any(text, levels["medium"]) or _contains_any(framing, levels["medium"]):
            confidence = ConfidenceLevel.MEDIUM
        if confidence:
            assessments.append(RiskAssessment(domain=domain, confidence=confidence))
    return assessments


def _ensure_presence(
    assessments: List[RiskAssessment],
    unknowns: List[UnknownSource],
) -> Tuple[List[RiskAssessment], List[UnknownSource]]:
    seen = {ra.domain for ra in assessments}
    if not assessments:
        # Bias to inclusion: add UNKNOWN domain with LOW confidence.
        assessments.append(RiskAssessment(domain=RiskDomain.UNKNOWN, confidence=ConfidenceLevel.LOW))
        unknowns.extend([UnknownSource.RISK_DOMAINS, UnknownSource.CONFIDENCE])
    # Deduplicate while preserving first confidence.
    unique: List[RiskAssessment] = []
    seen_domains = set()
    for ra in assessments:
        if ra.domain in seen_domains:
            continue
        unique.append(ra)
        seen_domains.add(ra.domain)
    return unique, unknowns


def _enforce_invariants(
    assessments: List[RiskAssessment],
    proximity_state: ProximityState,
    explicit_unknown_zone: Tuple[UnknownSource, ...],
) -> Tuple[Tuple[RiskAssessment, ...], Tuple[UnknownSource, ...]]:
    if not assessments:
        raise ValueError("risk_domains must not be empty.")
    if any(ra.confidence is ConfidenceLevel.UNKNOWN for ra in assessments):
        raise ValueError("risk_domains confidence must be LOW, MEDIUM, or HIGH.")
    domains = [ra.domain for ra in assessments]
    if len(domains) != len(set(domains)):
        raise ValueError("risk_domains must be deduplicated.")

    updated_unknowns = list(explicit_unknown_zone)
    if any(ra.domain is RiskDomain.UNKNOWN for ra in assessments) and UnknownSource.RISK_DOMAINS not in updated_unknowns:
        updated_unknowns.append(UnknownSource.RISK_DOMAINS)
    # Add confidence unknown marker when we used fallback UNKNOWN domain.
    if RiskDomain.UNKNOWN in domains and UnknownSource.CONFIDENCE not in updated_unknowns:
        updated_unknowns.append(UnknownSource.CONFIDENCE)

    # Ensure IMMINENT proximity is not contradicted by empty unknowns (delegated to DecisionState invariant).
    if proximity_state is ProximityState.IMMINENT and not updated_unknowns:
        updated_unknowns.append(UnknownSource.RISK_DOMAINS)

    return tuple(assessments), tuple(updated_unknowns)


def apply_risk_classification(
    decision_state: DecisionState,
    message: str,
    intent_framing: str | None = None,
) -> DecisionState:
    """
    Populate risk_domains with deterministic, bounded classifications.

    Inputs:
    - message: current user message only.
    - intent_framing: optional Phase 4 framing.
    """
    text = _lower(message)
    framing = _lower(intent_framing)

    unknowns: List[UnknownSource] = list(decision_state.explicit_unknown_zone)
    assessments = _classify_domains(text, framing)

    assessments, unknowns = _ensure_presence(assessments, unknowns)
    assessments_tuple, unknowns_tuple = _enforce_invariants(
        assessments=assessments,
        proximity_state=decision_state.proximity_state,
        explicit_unknown_zone=tuple(unknowns),
    )

    return replace(
        decision_state,
        risk_domains=assessments_tuple,
        explicit_unknown_zone=unknowns_tuple,
    )
