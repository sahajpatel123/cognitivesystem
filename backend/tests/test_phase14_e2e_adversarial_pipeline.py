from __future__ import annotations

import json
import re

import pytest

import backend.mci_backend.governed_response_runtime as grr
from backend.mci_backend.governed_response_runtime import render_governed_response
from backend.mci_backend.control_plan import (
    ClarificationReason,
    ClosureState,
    ControlAction,
    FrictionPosture,
    InitiativeBudget,
    QuestionClass,
    RefusalCategory,
    RigorLevel,
    ConfidenceSignalingLevel,
    UnknownDisclosureLevel,
    build_control_plan,
)
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
from backend.mci_backend.model_contract import ModelInvocationResult, ModelFailureType
from backend.mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ConfidenceSignalingLevel as OutputConfidenceLevel,
    ExpressionPosture,
    OutputAction,
    QuestionSpec,
    RefusalExplanationMode,
    RefusalSpec,
    ClosureSpec,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
    VerbosityCap,
    build_output_plan,
)
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason

from backend.tests._phase14_fake_llm import Phase14ErrorLLM, Phase14FakeLLM, Phase14TimeoutLLM


@pytest.fixture(autouse=True)
def patch_pipeline(monkeypatch):
    """Patch orchestrator assemblies to deterministic, invariant-respecting fixtures.

    We do NOT modify locked code; we only inject deterministic test doubles.
    """

    # Guard against legacy enum alias required by locked DecisionState checks.
    if not hasattr(OutcomeClass, "UNKNOWN"):
        setattr(OutcomeClass, "UNKNOWN", OutcomeClass.UNKNOWN_OUTCOME_CLASS)  # type: ignore[attr-defined]

    class PlanCtx:
        action: ControlAction = ControlAction.ANSWER_ALLOWED
        closure_state: ClosureState = ClosureState.OPEN

    ctx = PlanCtx()

    def _decision_state(decision_id: str, trace_id: str, message: str) -> DecisionState:
        return DecisionState(
            decision_id=decision_id,
            trace_id=trace_id,
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

    def _control_plan(user_text: str, decision_state: DecisionState):
        action = ctx.action
        if action == ControlAction.ANSWER_ALLOWED:
            return build_control_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                action=ControlAction.ANSWER_ALLOWED,
                rigor_level=RigorLevel.MINIMAL,
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
        if action == ControlAction.ASK_ONE_QUESTION:
            return build_control_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                action=ControlAction.ASK_ONE_QUESTION,
                rigor_level=RigorLevel.GUARDED,
                friction_posture=FrictionPosture.SOFT_PAUSE,
                clarification_required=True,
                clarification_reason=ClarificationReason.SAFETY,
                question_budget=1,
                question_class=QuestionClass.SAFETY_GUARD,
                confidence_signaling_level=ConfidenceSignalingLevel.GUARDED,
                unknown_disclosure_level=UnknownDisclosureLevel.FULL,
                initiative_allowed=False,
                initiative_budget=InitiativeBudget.NONE,
                closure_state=ClosureState.OPEN,
                refusal_required=False,
                refusal_category=None,
            )
        if action == ControlAction.REFUSE:
            return build_control_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                action=ControlAction.REFUSE,
                rigor_level=RigorLevel.STRUCTURED,
                friction_posture=FrictionPosture.HARD_PAUSE,
                clarification_required=False,
                clarification_reason=ClarificationReason.SAFETY,
                question_budget=0,
                question_class=None,
                confidence_signaling_level=ConfidenceSignalingLevel.GUARDED,
                unknown_disclosure_level=UnknownDisclosureLevel.PARTIAL,
                initiative_allowed=False,
                initiative_budget=InitiativeBudget.NONE,
                closure_state=ClosureState.CLOSING,
                refusal_required=True,
                refusal_category=RefusalCategory.RISK_REFUSAL,
            )
        if action == ControlAction.CLOSE:
            return build_control_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                action=ControlAction.CLOSE,
                rigor_level=RigorLevel.MINIMAL,
                friction_posture=FrictionPosture.STOP,
                clarification_required=False,
                clarification_reason=ClarificationReason.SCOPE_CONFIRMATION,
                question_budget=0,
                question_class=None,
                confidence_signaling_level=ConfidenceSignalingLevel.MINIMAL,
                unknown_disclosure_level=UnknownDisclosureLevel.NONE,
                initiative_allowed=False,
                initiative_budget=InitiativeBudget.NONE,
                closure_state=ctx.closure_state,
                refusal_required=False,
                refusal_category=None,
            )
        raise AssertionError("Unsupported action")

    def _output_plan(user_text: str, decision_state: DecisionState, control_plan):
        action_map = {
            ControlAction.ANSWER_ALLOWED: OutputAction.ANSWER,
            ControlAction.ASK_ONE_QUESTION: OutputAction.ASK_ONE_QUESTION,
            ControlAction.REFUSE: OutputAction.REFUSE,
            ControlAction.CLOSE: OutputAction.CLOSE,
        }
        action = action_map[control_plan.action]
        if action == OutputAction.ANSWER:
            return build_output_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                control_plan_id=control_plan.control_plan_id,
                action=OutputAction.ANSWER,
                posture=ExpressionPosture.BASELINE,
                rigor_disclosure=RigorDisclosureLevel.MINIMAL,
                confidence_signaling=OutputConfidenceLevel.MINIMAL,
                assumption_surfacing=AssumptionSurfacingMode.NONE,
                unknown_disclosure=UnknownDisclosureMode.NONE,
                verbosity_cap=VerbosityCap.NORMAL,
            )
        if action == OutputAction.ASK_ONE_QUESTION:
            return build_output_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                control_plan_id=control_plan.control_plan_id,
                action=OutputAction.ASK_ONE_QUESTION,
                posture=ExpressionPosture.GUARDED,
                rigor_disclosure=RigorDisclosureLevel.GUARDED,
                confidence_signaling=OutputConfidenceLevel.GUARDED,
                assumption_surfacing=AssumptionSurfacingMode.NONE,
                unknown_disclosure=UnknownDisclosureMode.EXPLICIT,
                verbosity_cap=VerbosityCap.NORMAL,
                question_spec=QuestionSpec(
                    question_class=QuestionClass.SAFETY_GUARD,
                    priority_reason=QuestionPriorityReason.SAFETY_CRITICAL,
                ),
            )
        if action == OutputAction.REFUSE:
            return build_output_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                control_plan_id=control_plan.control_plan_id,
                action=OutputAction.REFUSE,
                posture=ExpressionPosture.CONSTRAINED,
                rigor_disclosure=RigorDisclosureLevel.GUARDED,
                confidence_signaling=OutputConfidenceLevel.GUARDED,
                assumption_surfacing=AssumptionSurfacingMode.NONE,
                unknown_disclosure=UnknownDisclosureMode.IMPLICIT,
                verbosity_cap=VerbosityCap.NORMAL,
                refusal_spec=RefusalSpec(
                    refusal_category=RefusalCategory.RISK_REFUSAL,
                    explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
                ),
            )
        if action == OutputAction.CLOSE:
            return build_output_plan(
                trace_id=decision_state.trace_id,
                decision_state_id=decision_state.decision_id,
                control_plan_id=control_plan.control_plan_id,
                action=OutputAction.CLOSE,
                posture=ExpressionPosture.GUARDED,
                rigor_disclosure=RigorDisclosureLevel.MINIMAL,
                confidence_signaling=OutputConfidenceLevel.MINIMAL,
                assumption_surfacing=AssumptionSurfacingMode.NONE,
                unknown_disclosure=UnknownDisclosureMode.NONE,
                verbosity_cap=VerbosityCap.TERSE,
                closure_spec=ClosureSpec(
                    closure_state=ctx.closure_state,
                    rendering_mode=ClosureRenderingMode.CONFIRM_CLOSURE,
                ),
            )
        raise AssertionError("Unsupported action")

    monkeypatch.setattr(grr, "assemble_decision_state", _decision_state)
    monkeypatch.setattr(grr, "assemble_control_plan", _control_plan)
    monkeypatch.setattr(grr, "assemble_output_plan", _output_plan)

    return ctx


@pytest.fixture
def ctx(patch_pipeline):
    return patch_pipeline


def _assert_no_leakage(result: ModelInvocationResult):
    banned = ["trace_id", "DecisionState", "ControlPlan", "OutputPlan", "PHASE_"]
    text = result.output_text or ""
    if result.output_json:
        payload = json.dumps(result.output_json)
        assert all(token not in payload for token in banned)
    assert all(token.lower() not in text.lower() for token in banned)


def _run(user_text: str, ctx, llm, action: ControlAction = ControlAction.ANSWER_ALLOWED) -> ModelInvocationResult:
    ctx.action = action
    return grr.render_governed_response(user_text, llm_client=llm)


# CATEGORY A — DETERMINISM

def test_determinism_same_input_same_output(ctx):
    llm = Phase14FakeLLM(["bounded output", "bounded output"])
    res1 = _run("determinism check", ctx, llm, ControlAction.ANSWER_ALLOWED)
    res2 = _run("determinism check", ctx, llm, ControlAction.ANSWER_ALLOWED)
    assert res1.ok and res2.ok
    assert res1.output_text == res2.output_text


def test_determinism_fallback_is_stable(ctx):
    llm = Phase14FakeLLM(["I remember previous conversation", "I remember previous conversation"])
    res1 = _run("fallback determinism", ctx, llm, ControlAction.ANSWER_ALLOWED)
    res2 = _run("fallback determinism", ctx, llm, ControlAction.ANSWER_ALLOWED)
    assert res1.ok and res2.ok
    assert res1.output_text == res2.output_text


# CATEGORY B — STRUCTURED OUTPUT VIOLATIONS

def test_non_json_for_question_triggers_fallback(ctx):
    llm = Phase14FakeLLM(["not json"])
    res = _run("ask malformed", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    assert res.output_json is not None and "question" in res.output_json


def test_fenced_json_rejected(ctx):
    llm = Phase14FakeLLM(["```json {\"question\": \"hi\"}```"])
    res = _run("ask fenced", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    assert res.output_json is not None


def test_malformed_json_missing_question(ctx):
    llm = Phase14FakeLLM(["{\"wrong\": \"field\"}"])
    res = _run("ask missing", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    assert res.output_json is not None


def test_extra_keys_in_json_fail_closed(ctx):
    llm = Phase14FakeLLM(["{\"question\": \"hi\", \"extra\": true}"])
    res = _run("ask extra", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    assert res.output_json is not None


# CATEGORY C — MULTI-QUESTION INJECTION

def test_multi_question_phrase_rejected(ctx):
    llm = Phase14FakeLLM(['{"question": "Q1? Also Q2?"}'])
    res = _run("multi question", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    assert res.output_json is not None
    assert "also" not in res.output_json["question"].lower()


def test_multi_question_array_rejected(ctx):
    llm = Phase14FakeLLM(['["Q1","Q2"]'])
    res = _run("multi array", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    assert res.output_json is not None


# CATEGORY D — OUTPUTPLAN DOMINANCE ATTACKS

def test_model_attempts_to_answer_during_refusal(ctx):
    llm = Phase14FakeLLM(["I will answer anyway"])
    res = _run("refusal override", ctx, llm, ControlAction.REFUSE)
    assert res.ok
    assert res.output_text is not None
    assert "answer anyway" not in res.output_text.lower()


def test_model_asks_question_during_close(ctx):
    llm = Phase14FakeLLM(["Can I help more?"])
    res = _run("close override", ctx, llm, ControlAction.CLOSE)
    assert res.ok
    assert res.output_text is not None
    assert "?" not in res.output_text


# CATEGORY E — AUTHORITY / CAPABILITY HALLUCINATIONS

def test_authority_hallucination_fails_closed(ctx):
    llm = Phase14FakeLLM(["I accessed your data and updated rules."])
    res = _run("authority hallucination", ctx, llm, ControlAction.ANSWER_ALLOWED)
    assert res.ok
    assert res.output_text is not None
    assert "accessed your data" not in res.output_text.lower()
    _assert_no_leakage(res)


def test_memory_claims_fail_closed(ctx):
    llm = Phase14FakeLLM(["As you said earlier, I remember."])
    res = _run("recall scenario", ctx, llm, ControlAction.ANSWER_ALLOWED)
    assert res.ok
    assert res.output_text is not None
    assert "remember" not in res.output_text.lower()
    _assert_no_leakage(res)


# CATEGORY F — REFUSAL / CLOSURE DISCIPLINE

def test_refusal_remains_terminal(ctx):
    llm = Phase14FakeLLM(["Maybe you should try this advice."])
    res = _run("refusal discipline", ctx, llm, ControlAction.REFUSE)
    assert res.ok
    assert res.output_text is not None
    assert "should" not in res.output_text.lower()


def test_close_remains_terminal(ctx):
    llm = Phase14FakeLLM(["Closing? But here is another question?"])
    res = _run("closure discipline", ctx, llm, ControlAction.CLOSE)
    assert res.ok
    assert res.output_text is not None
    assert "?" not in res.output_text


def test_user_terminated_closure_is_bounded(ctx):
    ctx.closure_state = ClosureState.USER_TERMINATED
    llm = Phase14FakeLLM(["Continuing anyway"])
    res = _run("user terminated", ctx, llm, ControlAction.CLOSE)
    assert res.ok
    assert res.output_text is not None
    assert "continuing" not in res.output_text.lower()
    ctx.closure_state = ClosureState.OPEN


# CATEGORY G — FAIL-CLOSED PIPELINE ERRORS

def test_timeout_results_in_fallback(ctx):
    llm = Phase14TimeoutLLM()
    res = _run("timeout path", ctx, llm, ControlAction.ANSWER_ALLOWED)
    assert res.ok
    assert res.output_text is not None


def test_provider_error_results_in_fallback(ctx):
    llm = Phase14ErrorLLM("provider failure")
    res = _run("provider error", ctx, llm, ControlAction.ANSWER_ALLOWED)
    assert res.ok
    assert res.output_text is not None


# CATEGORY H — NO INTERNAL LEAKAGE

def test_no_internal_identifiers_leak(ctx):
    llm = Phase14FakeLLM(["trace_id=123 ControlPlan OutputPlan PHASE_12"])
    res = _run("leakage test", ctx, llm, ControlAction.ASK_ONE_QUESTION)
    assert res.ok
    _assert_no_leakage(res)
