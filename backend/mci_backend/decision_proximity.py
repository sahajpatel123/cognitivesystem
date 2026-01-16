from __future__ import annotations

"""
Phase 9 — Step 1: Decision-Proximity Engine (deterministic, bounded, non-adaptive).

Responsibilities:
- Classify proximity_state (VERY_LOW, LOW, MEDIUM, HIGH, IMMINENT, UNKNOWN) using bounded structural signals.
- Set proximity_uncertainty explicitly.
- Enforce invariants (single state, explicit uncertainty, no regression, IMMINENT requires non-empty unknown_zone).

Forbidden:
- No intent inference, risk assessment, emotion/sentiment, heuristics, probabilities, models, or user profiling.
- No modification of other DecisionState fields beyond proximity_state/uncertainty and unknown_zone additions for proximity.
"""

from dataclasses import replace
from typing import Iterable, Tuple

from .decision_state import (
    DecisionState,
    ProximityState,
    UnknownSource,
)

PROXIMITY_ORDER = [
    ProximityState.VERY_LOW,
    ProximityState.LOW,
    ProximityState.MEDIUM,
    ProximityState.HIGH,
    ProximityState.IMMINENT,
]


def _lower(s: str | None) -> str:
    return (s or "").lower()


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def classify_proximity(message: str, intent_framing: str | None = None) -> Tuple[ProximityState, bool]:
    """
    Deterministic rule-based classification of proximity.

    Inputs:
    - message: current user message only.
    - intent_framing: optional Phase 4 Step 0 framing (bounded).
    """
    text = _lower(message)
    framing = _lower(intent_framing)

    # Strongest signals: imminent execution framing and immediate temporal markers.
    imminent_markers = [
        "about to",
        "ready to",
        "before i do",
        "before we do",
        "going to",
        "on my way",
        "right now",
        "doing this now",
        "today",
        "tonight",
        "this minute",
        "immediately",
    ]
    if _contains_any(text, imminent_markers) or _contains_any(framing, imminent_markers):
        return ProximityState.IMMINENT, False

    # High: clear commitment / execution language without immediate timing.
    high_markers = [
        "will do",
        "plan to",
        "planning to",
        "intend to",
        "going ahead",
        "scheduled",
        "set to",
        "decided to",
    ]
    if _contains_any(text, high_markers) or _contains_any(framing, high_markers):
        return ProximityState.HIGH, False

    # Medium: narrowing options, validation-seeking prior to action.
    medium_markers = [
        "between",
        "should i pick",
        "choose between",
        "which option",
        "confirm",
        "is this okay",
        "is this ok",
        "before choosing",
        "before choosing",
    ]
    if _contains_any(text, medium_markers) or _contains_any(framing, medium_markers):
        return ProximityState.MEDIUM, False

    # Low: early-stage, exploratory references to action.
    low_markers = [
        "thinking about",
        "considering",
        "might",
        "maybe do",
        "could",
        "potentially",
    ]
    if _contains_any(text, low_markers) or _contains_any(framing, low_markers):
        return ProximityState.LOW, True

    # Default: insufficient signals → very low with uncertainty.
    return ProximityState.VERY_LOW, True


def _enforce_invariants(
    prior_state: ProximityState,
    new_state: ProximityState,
    proximity_uncertainty: bool,
    explicit_unknown_zone: Tuple[UnknownSource, ...],
) -> Tuple[UnknownSource, ...]:
    if new_state not in PROXIMITY_ORDER and new_state is not ProximityState.UNKNOWN:
        raise ValueError("proximity_state must be a bounded ProximityState enum.")

    # No regression within a single turn if prior known (excluding UNKNOWN).
    if prior_state is not ProximityState.UNKNOWN:
        prior_index = PROXIMITY_ORDER.index(prior_state)
        new_index = PROXIMITY_ORDER.index(new_state)
        if new_index < prior_index:
            raise ValueError("proximity_state regression within a turn is forbidden.")

    # Uncertainty must be explicit.
    if proximity_uncertainty not in (True, False):
        raise ValueError("proximity_uncertainty must be explicitly set.")

    # IMMINENT cannot coexist with empty unknown_zone (explicit rule).
    updated_unknowns = list(explicit_unknown_zone)
    if proximity_uncertainty and UnknownSource.PROXIMITY not in updated_unknowns:
        updated_unknowns.append(UnknownSource.PROXIMITY)
    if new_state is ProximityState.IMMINENT and not updated_unknowns:
        raise ValueError("IMMINENT proximity requires non-empty explicit_unknown_zone.")

    return tuple(updated_unknowns)


def apply_proximity(
    decision_state: DecisionState,
    message: str,
    intent_framing: str | None = None,
) -> DecisionState:
    """Populate proximity_state and proximity_uncertainty on a DecisionState (immutable replace)."""
    new_state, uncertainty = classify_proximity(message, intent_framing)
    updated_unknowns = _enforce_invariants(
        prior_state=decision_state.proximity_state,
        new_state=new_state,
        proximity_uncertainty=uncertainty,
        explicit_unknown_zone=decision_state.explicit_unknown_zone,
    )
    return replace(
        decision_state,
        proximity_state=new_state,
        proximity_uncertainty=uncertainty,
        explicit_unknown_zone=updated_unknowns,
    )
