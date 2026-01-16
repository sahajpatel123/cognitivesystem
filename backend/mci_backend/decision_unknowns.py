from __future__ import annotations

"""
Phase 9 — Step 7: Unknown-Zone Consolidation (deterministic, bounded).

Responsibilities:
- Consolidate and deduplicate explicit_unknown_zone.
- Enforce bounded unknown taxonomy based on DecisionState fields.
- Fail-closed on invalid or missing required markers.

No other DecisionState fields are modified.
No prediction, probability, advice, or orchestration is introduced.
"""

from dataclasses import replace
from typing import Tuple

from .decision_state import (
    ConsequenceHorizon,
    DecisionState,
    OutcomeClass,
    ProximityState,
    ReversibilityClass,
    RiskAssessment,
    RiskDomain,
    UnknownSource,
    ResponsibilityScope,
)


def consolidate_unknowns(decision_state: DecisionState) -> DecisionState:
    """Deterministically consolidate explicit unknown markers; leaves other fields unchanged."""
    required = set()

    # Proximity
    if decision_state.proximity_state is ProximityState.UNKNOWN or decision_state.proximity_uncertainty:
        required.add(UnknownSource.PROXIMITY)

    # Risk domains
    if not decision_state.risk_domains:
        raise ValueError("risk_domains must not be empty during unknown consolidation.")
    for rd in decision_state.risk_domains:
        if not isinstance(rd, RiskAssessment):
            raise ValueError("risk_domains entries must be RiskAssessment during unknown consolidation.")
        if rd.domain is RiskDomain.UNKNOWN:
            required.add(UnknownSource.RISK_DOMAINS)
        if rd.confidence.name == "UNKNOWN":
            required.add(UnknownSource.CONFIDENCE)

    # Reversibility / horizon
    if decision_state.reversibility_class is ReversibilityClass.UNKNOWN:
        required.add(UnknownSource.REVERSIBILITY)
    if decision_state.reversibility_class is ReversibilityClass.IRREVERSIBLE:
        required.add(UnknownSource.REVERSIBILITY)

    if decision_state.consequence_horizon is ConsequenceHorizon.UNKNOWN:
        required.add(UnknownSource.HORIZON)
    if decision_state.consequence_horizon is ConsequenceHorizon.LONG_HORIZON:
        required.add(UnknownSource.HORIZON)

    # Responsibility
    if decision_state.responsibility_scope is ResponsibilityScope.UNKNOWN:
        required.add(UnknownSource.RESPONSIBILITY_SCOPE)
    if (
        decision_state.responsibility_scope is ResponsibilityScope.SYSTEMIC_PUBLIC
        and decision_state.consequence_horizon is ConsequenceHorizon.SHORT_HORIZON
    ):
        required.add(UnknownSource.HORIZON)

    # Outcomes
    if not decision_state.outcome_classes:
        raise ValueError("outcome_classes must not be empty during unknown consolidation.")
    if any(oc is OutcomeClass.UNKNOWN_OUTCOME_CLASS for oc in decision_state.outcome_classes):
        required.add(UnknownSource.OUTCOME_CLASSES)

    # Merge with existing, enforce bounded taxonomy.
    merged = set(decision_state.explicit_unknown_zone) | required
    for entry in merged:
        if not isinstance(entry, UnknownSource):
            raise ValueError("explicit_unknown_zone contains non-UnknownSource entries.")

    # Deterministic ordering.
    merged_sorted = tuple(sorted(merged, key=lambda u: u.value))

    return replace(decision_state, explicit_unknown_zone=merged_sorted)
