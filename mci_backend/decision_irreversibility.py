from __future__ import annotations

"""
Phase 9 — Step 3: Irreversibility & Consequence Horizon Engine (deterministic, bounded).

Populates only:
- reversibility_class
- consequence_horizon
- explicit_unknown_zone (for related unknowns)

Forbidden:
- No prediction, probability, or severity estimation.
- No advice, mitigation, refusals, or orchestration.
- No models, heuristics, personalization, or history.
"""

from dataclasses import replace
from typing import Iterable, Tuple

from .decision_state import (
    ConsequenceHorizon,
    DecisionState,
    ReversibilityClass,
    UnknownSource,
)


def _lower(text: str | None) -> str:
    return (text or "").lower()


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def classify_reversibility(message: str) -> Tuple[ReversibilityClass, bool]:
    text = _lower(message)

    irreversible_markers = [
        "cannot undo",
        "irreversible",
        "permanent",
        "one-way",
        "destructive",
        "non-recoverable",
        "delete permanently",
    ]
    if _contains_any(text, irreversible_markers):
        return ReversibilityClass.IRREVERSIBLE, False

    costly_markers = [
        "requires approval",
        "contract",
        "legal",
        "surgery",
        "compliance",
        "license",
        "migration",
        "downtime",
    ]
    if _contains_any(text, costly_markers):
        return ReversibilityClass.COSTLY_REVERSIBLE, False

    easy_markers = [
        "draft",
        "temporary",
        "test",
        "trial",
        "prototype",
        "undo",
        "rollback",
        "revert",
    ]
    if _contains_any(text, easy_markers):
        return ReversibilityClass.EASILY_REVERSIBLE, True

    return ReversibilityClass.UNKNOWN, True


def classify_horizon(message: str) -> Tuple[ConsequenceHorizon, bool]:
    text = _lower(message)

    long_markers = [
        "years",
        "decades",
        "lifetime",
        "forever",
        "permanent",
        "long term",
        "long-term",
        "irreversible",
    ]
    if _contains_any(text, long_markers):
        return ConsequenceHorizon.LONG_HORIZON, False

    medium_markers = [
        "months",
        "quarter",
        "this year",
        "over time",
        "medium term",
        "medium-term",
    ]
    if _contains_any(text, medium_markers):
        return ConsequenceHorizon.MEDIUM_HORIZON, False

    short_markers = [
        "today",
        "now",
        "tonight",
        "this week",
        "immediately",
        "soon",
        "short term",
        "short-term",
    ]
    if _contains_any(text, short_markers):
        return ConsequenceHorizon.SHORT_HORIZON, True

    return ConsequenceHorizon.UNKNOWN, True


def _enforce_invariants(
    decision_state: DecisionState,
    reversibility: ReversibilityClass,
    horizon: ConsequenceHorizon,
    uncertainty_flags: Tuple[UnknownSource, ...],
) -> Tuple[ReversibilityClass, ConsequenceHorizon, Tuple[UnknownSource, ...]]:
    unknowns = list(uncertainty_flags)

    if reversibility is ReversibilityClass.UNKNOWN and UnknownSource.REVERSIBILITY not in unknowns:
        unknowns.append(UnknownSource.REVERSIBILITY)
    if horizon is ConsequenceHorizon.UNKNOWN and UnknownSource.HORIZON not in unknowns:
        unknowns.append(UnknownSource.HORIZON)

    if reversibility is ReversibilityClass.IRREVERSIBLE and UnknownSource.REVERSIBILITY not in unknowns:
        unknowns.append(UnknownSource.REVERSIBILITY)
    if horizon is ConsequenceHorizon.LONG_HORIZON and UnknownSource.HORIZON not in unknowns:
        unknowns.append(UnknownSource.HORIZON)

    # Ensure at least one value is set; DecisionState __post_init__ enforces enum types.
    if reversibility not in ReversibilityClass:
        raise ValueError("Invalid reversibility_class.")
    if horizon not in ConsequenceHorizon:
        raise ValueError("Invalid consequence_horizon.")

    return reversibility, horizon, tuple(unknowns)


def apply_irreversibility(
    decision_state: DecisionState,
    message: str,
    intent_framing: str | None = None,
) -> DecisionState:
    """
    Populate reversibility_class and consequence_horizon deterministically.
    Uses only current message and optional Phase 4 framing.
    """
    reversibility, rev_uncertain = classify_reversibility(message)
    horizon, horizon_uncertain = classify_horizon(message)

    unknowns = list(decision_state.explicit_unknown_zone)
    if rev_uncertain:
        unknowns.append(UnknownSource.REVERSIBILITY)
    if horizon_uncertain:
        unknowns.append(UnknownSource.HORIZON)

    reversibility, horizon, unknowns_tuple = _enforce_invariants(
        decision_state=decision_state,
        reversibility=reversibility,
        horizon=horizon,
        uncertainty_flags=tuple(unknowns),
    )

    return replace(
        decision_state,
        reversibility_class=reversibility,
        consequence_horizon=horizon,
        explicit_unknown_zone=unknowns_tuple,
    )
