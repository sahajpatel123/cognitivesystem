from __future__ import annotations

"""
Phase 9 — Step 8: Decision State Assembly Pipeline (deterministic, bounded, fail-closed).

Responsibilities:
- Run Steps 1–5 and 7 in canonical order.
- Enforce cross-field invariants without changing engine semantics.
- Return a final immutable DecisionState or raise a bounded validation error.

Forbidden:
- No advice, answers, orchestration, or model calls.
- No modification of Step 1–7 engine behavior.
- No heuristics, probabilities, or history.
"""

from dataclasses import dataclass

from .decision_irreversibility import apply_irreversibility
from .decision_outcomes import apply_outcome_classes
from .decision_proximity import apply_proximity
from .decision_responsibility import apply_responsibility_scope
from .decision_risk import apply_risk_classification
from .decision_unknowns import consolidate_unknowns
from .decision_state import (
    ConfidenceLevel,
    ConsequenceHorizon,
    DecisionState,
    OutcomeClass,
    PhaseMarker,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
    UnknownSource,
    PHASE_9_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class AssemblyValidationError(ValueError):
    message: str


def _validate_cross_fields(state: DecisionState) -> DecisionState:
    """Enforce Step 8 cross-field invariants; fail-closed on violations."""
    if not state.risk_domains:
        raise AssemblyValidationError("risk_domains must be non-empty after assembly.")
    if not state.outcome_classes:
        raise AssemblyValidationError("outcome_classes must be non-empty after assembly.")

    # Unknown taxonomy bounded.
    for entry in state.explicit_unknown_zone:
        if entry not in UnknownSource:
            raise AssemblyValidationError("explicit_unknown_zone contains non-UnknownSource entries.")

    # Required unknown markers.
    if (
        state.reversibility_class is ReversibilityClass.IRREVERSIBLE
        and UnknownSource.REVERSIBILITY not in state.explicit_unknown_zone
    ):
        raise AssemblyValidationError("IRREVERSIBLE requires UnknownSource.REVERSIBILITY.")
    if (
        state.consequence_horizon is ConsequenceHorizon.LONG_HORIZON
        and UnknownSource.HORIZON not in state.explicit_unknown_zone
    ):
        raise AssemblyValidationError("LONG_HORIZON requires UnknownSource.HORIZON.")
    if (
        state.responsibility_scope is ResponsibilityScope.SYSTEMIC_PUBLIC
        and state.consequence_horizon is ConsequenceHorizon.SHORT_HORIZON
        and UnknownSource.HORIZON not in state.explicit_unknown_zone
    ):
        raise AssemblyValidationError("SYSTEMIC_PUBLIC with SHORT_HORIZON requires UnknownSource.HORIZON.")
    if (
        state.outcome_classes
        and OutcomeClass.UNKNOWN_OUTCOME_CLASS in state.outcome_classes
        and UnknownSource.OUTCOME_CLASSES not in state.explicit_unknown_zone
    ):
        raise AssemblyValidationError("UNKNOWN_OUTCOME_CLASS requires UnknownSource.OUTCOME_CLASSES.")

    # Risk/outcome coherence: legal/regulatory.
    legal_present = any(
        rd.domain in (RiskDomain.LEGAL_REGULATORY, RiskDomain.LEGAL_ADJACENT_GRAY_ZONE) for rd in state.risk_domains
    )
    if legal_present and OutcomeClass.LEGAL_REGULATORY_OUTCOME not in state.outcome_classes:
        if UnknownSource.OUTCOME_CLASSES not in state.explicit_unknown_zone:
            raise AssemblyValidationError("Legal/regulatory risk requires legal/regulatory outcome or explicit unknown.")

    # Medical coherence.
    medical_present = any(rd.domain is RiskDomain.MEDICAL_BIOLOGICAL for rd in state.risk_domains)
    if medical_present and OutcomeClass.MEDICAL_BIOLOGICAL_OUTCOME not in state.outcome_classes:
        if UnknownSource.OUTCOME_CLASSES not in state.explicit_unknown_zone:
            raise AssemblyValidationError("Medical risk requires medical outcome or explicit unknown.")

    return state


def assemble_decision_state(
    decision_id: str,
    trace_id: str,
    message: str,
    intent_framing: str | None = None,
) -> DecisionState:
    """Canonical Step 8 assembly pipeline. Returns final DecisionState or raises AssemblyValidationError."""
    # Baseline state that satisfies schema; engines will replace fields deterministically.
    baseline = DecisionState(
        decision_id=decision_id,
        trace_id=trace_id,
        phase_marker=PhaseMarker.PHASE_9,
        schema_version=PHASE_9_SCHEMA_VERSION,
        proximity_state=ProximityState.UNKNOWN,
        proximity_uncertainty=True,
        risk_domains=(RiskAssessment(domain=RiskDomain.UNKNOWN, confidence=ConfidenceLevel.LOW),),
        reversibility_class=ReversibilityClass.UNKNOWN,
        consequence_horizon=ConsequenceHorizon.UNKNOWN,
        responsibility_scope=ResponsibilityScope.UNKNOWN,
        outcome_classes=(OutcomeClass.UNKNOWN_OUTCOME_CLASS,),
        explicit_unknown_zone=(
            UnknownSource.PROXIMITY,
            UnknownSource.RISK_DOMAINS,
            UnknownSource.REVERSIBILITY,
            UnknownSource.HORIZON,
            UnknownSource.RESPONSIBILITY_SCOPE,
            UnknownSource.OUTCOME_CLASSES,
            UnknownSource.CONFIDENCE,
        ),
    )

    state = apply_proximity(baseline, message, intent_framing)
    state = apply_risk_classification(state, message, intent_framing)
    state = apply_irreversibility(state, message, intent_framing)
    state = apply_responsibility_scope(state, message, intent_framing)
    state = apply_outcome_classes(state, message, intent_framing)
    state = consolidate_unknowns(state)

    return _validate_cross_fields(state)
