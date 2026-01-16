from __future__ import annotations

import pytest

from backend.mci_backend.control_plan import (
    ClarificationReason,
    ClosureState,
    ControlAction,
    ControlPlanValidationError,
    FrictionPosture,
    InitiativeBudget,
    QuestionClass,
    RefusalCategory,
    RigorLevel,
    ConfidenceSignalingLevel,
    UnknownDisclosureLevel,
    build_control_plan,
)
from backend.mci_backend.orchestration_assembly import assemble_control_plan, OrchestrationAssemblyError
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
import backend.mci_backend.orchestration_clarification_trigger as clar
import backend.mci_backend.orchestration_closure as closure
import backend.mci_backend.orchestration_friction as friction
import backend.mci_backend.orchestration_rigor as rigor
import backend.mci_backend.orchestration_initiative as initiative
import backend.mci_backend.orchestration_question_compression as compression
from backend.mci_backend.orchestration_question_compression import QuestionSelection, select_single_question
from backend.mci_backend.orchestration_refusal import RefusalDecision, decide_refusal
import backend.mci_backend.orchestration_refusal as refusal_module
from backend.mci_backend.orchestration_rigor import select_rigor
from backend.mci_backend.expression_assembly import (
    assemble_output_plan,
    OutputAssemblyInvariantViolation,
    OutputAssemblyError,
)
import backend.mci_backend.orchestration_assembly as assembly


def _base_kwargs():
    return dict(
        trace_id="t",
        decision_state_id="d",
        rigor_level=RigorLevel.GUARDED,
        friction_posture=FrictionPosture.NONE,
        clarification_required=False,
        clarification_reason=ClarificationReason.DISAMBIGUATION,
        question_budget=0,
        question_class=None,
        confidence_signaling_level=ConfidenceSignalingLevel.MINIMAL,
        unknown_disclosure_level=UnknownDisclosureLevel.NONE,
        initiative_allowed=False,
        initiative_budget=InitiativeBudget.NONE,
        closure_state=ClosureState.OPEN,
        refusal_required=False,
        refusal_category=None,
    )


def test_ask_one_with_wrong_budget_fails():
    with pytest.raises(ControlPlanValidationError):
        kwargs = _base_kwargs()
        kwargs.update(
            {
                "action": ControlAction.ASK_ONE_QUESTION,
                "question_budget": 0,
                "question_class": QuestionClass.SAFETY_GUARD,
            }
        )
        build_control_plan(**kwargs)


def test_clarification_required_with_zero_budget_fails():
    with pytest.raises(ControlPlanValidationError):
        kwargs = _base_kwargs()
        kwargs.update(
            {
                "action": ControlAction.ASK_ONE_QUESTION,
                "clarification_required": True,
                "question_budget": 0,
                "question_class": QuestionClass.SAFETY_GUARD,
            }
        )
        build_control_plan(**kwargs)


def test_closure_closed_with_question_budget_fails():
    # ControlPlan permits this shape, but downstream OutputPlan assembly must reject questions when closure is active.
    kwargs = _base_kwargs()
    kwargs.update(
        {
            "action": ControlAction.ANSWER_ALLOWED,
            "closure_state": ClosureState.CLOSED,
            "question_budget": 1,
            "question_class": QuestionClass.SAFETY_GUARD,
            "clarification_required": True,
        }
    )
    cp = build_control_plan(**kwargs)
    ds = DecisionState(
        decision_id="d",
        trace_id="t",
        phase_marker=DecisionPhaseMarker.PHASE_9,
        schema_version="9.0.0",
        proximity_state=ProximityState.LOW,
        proximity_uncertainty=False,
        risk_domains=(RiskAssessment(domain=RiskDomain.FINANCIAL, confidence=ConfidenceLevel.LOW),),
        reversibility_class=ReversibilityClass.COSTLY_REVERSIBLE,
        consequence_horizon=ConsequenceHorizon.SHORT_HORIZON,
        responsibility_scope=ResponsibilityScope.SELF_ONLY,
        outcome_classes=(OutcomeClass.FINANCIAL_OUTCOME,),
        explicit_unknown_zone=(UnknownSource.RISK_DOMAINS,),
    )
    with pytest.raises(OutputAssemblyError):
        assemble_output_plan("closure with questions", ds, cp)


def test_refusal_required_none_category_fails():
    with pytest.raises(ControlPlanValidationError):
        kwargs = _base_kwargs()
        kwargs.update(
            {
                "action": ControlAction.REFUSE,
                "refusal_required": True,
                "refusal_category": RefusalCategory.NONE,
            }
        )
        build_control_plan(**kwargs)


def test_non_refusal_with_category_not_none_fails():
    with pytest.raises(ControlPlanValidationError):
        kwargs = _base_kwargs()
        kwargs.update(
            {
                "action": ControlAction.ANSWER_ALLOWED,
                "refusal_required": False,
                "refusal_category": RefusalCategory.RISK_REFUSAL,
            }
        )
        build_control_plan(**kwargs)


def test_stop_friction_requires_gate(monkeypatch):
    # Force assembly path to produce STOP friction with no gates to trigger invariant.
    ds = DecisionState(
        decision_id="d",
        trace_id="t",
        phase_marker=DecisionPhaseMarker.PHASE_9,
        schema_version="9.0.0",
        proximity_state=ProximityState.LOW,
        proximity_uncertainty=False,
        risk_domains=(RiskAssessment(domain=RiskDomain.FINANCIAL, confidence=ConfidenceLevel.LOW),),
        reversibility_class=ReversibilityClass.COSTLY_REVERSIBLE,
        consequence_horizon=ConsequenceHorizon.SHORT_HORIZON,
        responsibility_scope=ResponsibilityScope.SELF_ONLY,
        outcome_classes=(OutcomeClass.FINANCIAL_OUTCOME,),
        explicit_unknown_zone=(UnknownSource.RISK_DOMAINS,),
    )

    monkeypatch.setattr(assembly, "select_rigor", lambda *_: RigorLevel.MINIMAL)
    monkeypatch.setattr(assembly, "select_friction", lambda *_: FrictionPosture.STOP)
    monkeypatch.setattr(
        assembly,
        "decide_clarification",
        lambda *_: clar.ClarificationDecision(clarification_required=False, clarification_reason=ClarificationReason.UNKNOWN, question_budget=0),
    )
    monkeypatch.setattr(assembly, "detect_closure", lambda *args, **kwargs: closure.ClosureDecision(closure_state=ClosureState.OPEN))
    monkeypatch.setattr(
        assembly,
        "select_initiative",
        lambda *_: initiative.InitiativeDecision(initiative_budget=InitiativeBudget.NONE, warning_budget=0),
    )
    monkeypatch.setattr(
        assembly,
        "select_single_question",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        assembly,
        "decide_refusal",
        lambda *_: refusal_module.RefusalDecision(refusal_required=False, refusal_category=RefusalCategory.NONE),
    )

    with pytest.raises(OrchestrationAssemblyError):
        assemble_control_plan("stop friction", ds)
