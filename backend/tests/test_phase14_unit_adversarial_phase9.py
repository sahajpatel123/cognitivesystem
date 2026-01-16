from __future__ import annotations

import pytest

from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    ConsequenceHorizon,
    DecisionState,
    OutcomeClass,
    PhaseMarker as DecisionPhaseMarker,
    ProximityState,
    ResponsibilityScope,
    ReversibilityClass,
    RiskAssessment,
    RiskDomain,
    UnknownSource,
)


def _build_state(**overrides):
    base = dict(
        decision_id="d",
        trace_id="t",
        phase_marker=DecisionPhaseMarker.PHASE_9,
        schema_version="9.0.0",
        proximity_state=ProximityState.LOW,
        proximity_uncertainty=False,
        risk_domains=(RiskAssessment(domain=RiskDomain.FINANCIAL, confidence=ConfidenceLevel.LOW),),
        reversibility_class=ReversibilityClass.COSTLY_REVERSIBLE,
        consequence_horizon=ConsequenceHorizon.MEDIUM_HORIZON,
        responsibility_scope=ResponsibilityScope.SELF_ONLY,
        outcome_classes=(OutcomeClass.FINANCIAL_OUTCOME,),
        explicit_unknown_zone=(UnknownSource.RISK_DOMAINS,),
    )
    base.update(overrides)
    return DecisionState(**base)


def test_empty_risk_domains_fails():
    with pytest.raises(ValueError):
        _build_state(risk_domains=tuple(), explicit_unknown_zone=(UnknownSource.RISK_DOMAINS,))


@pytest.mark.xfail(strict=True, reason="DecisionState allows empty outcome_classes when unknown marker provided (certification flaw)")
def test_empty_outcome_classes_fails():
    _build_state(outcome_classes=tuple(), explicit_unknown_zone=())


def test_duplicate_risk_domains_fails():
    with pytest.raises(ValueError):
        _build_state(
            risk_domains=(
                RiskAssessment(domain=RiskDomain.FINANCIAL, confidence=ConfidenceLevel.LOW),
                RiskAssessment(domain=RiskDomain.FINANCIAL, confidence=ConfidenceLevel.MEDIUM),
            )
        )


def test_invalid_unknown_source_rejected():
    with pytest.raises(ValueError):
        _build_state(explicit_unknown_zone=("NOT_ALLOWED",))  # type: ignore[arg-type]


def test_irreversible_requires_unknown_marker():
    with pytest.raises(ValueError):
        _build_state(
            reversibility_class=ReversibilityClass.IRREVERSIBLE,
            explicit_unknown_zone=(),
        )


def test_long_horizon_requires_unknown_marker():
    with pytest.raises(ValueError):
        _build_state(
            consequence_horizon=ConsequenceHorizon.LONG_HORIZON,
            explicit_unknown_zone=(),
        )


def test_systemic_public_short_horizon_requires_unknown_marker():
    with pytest.raises(ValueError):
        _build_state(
            responsibility_scope=ResponsibilityScope.SYSTEMIC_PUBLIC,
            consequence_horizon=ConsequenceHorizon.SHORT_HORIZON,
            explicit_unknown_zone=(),
        )


def test_unknown_zone_must_cover_all_sources():
    with pytest.raises(ValueError):
        _build_state(
            proximity_state=ProximityState.UNKNOWN,
            risk_domains=(RiskAssessment(domain=RiskDomain.UNKNOWN, confidence=ConfidenceLevel.LOW),),
            outcome_classes=(OutcomeClass.UNKNOWN_OUTCOME_CLASS,),
            explicit_unknown_zone=(UnknownSource.PROXIMITY,),  # missing others
        )
