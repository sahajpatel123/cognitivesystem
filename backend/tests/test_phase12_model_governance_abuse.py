import pathlib
import sys

import pytest

# Ensure repository root on path for imports.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    OutcomeClass,
    PHASE_9_SCHEMA_VERSION,
    PhaseMarker as DecisionPhaseMarker,
    ProximityState,
    ReversibilityClass,
    ConsequenceHorizon,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
)
from mci_backend.control_plan import (
    ControlPlan,
    ClosureState,
    ControlAction,
    RigorLevel,
    FrictionPosture,
    ClarificationReason,
    QuestionClass as ControlQuestionClass,
    ConfidenceSignalingLevel as ControlConfidenceLevel,
    UnknownDisclosureLevel as ControlUnknownDisclosureLevel,
    InitiativeBudget,
    build_control_plan,
)
from mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ClosureSpec,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    OutputAction,
    OutputPlan,
    QuestionClass,
    QuestionSpec,
    RefusalCategory,
    RefusalExplanationMode,
    RefusalSpec,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
    VerbosityCap,
    build_output_plan,
)
from mci_backend.orchestration_question_compression import QuestionPriorityReason
from mci_backend.model_contract import (
    ModelFailure,
    ModelFailureType,
    ModelInvocationResult,
    build_request_id,
)
from mci_backend.model_invocation_pipeline import invoke_model_for_output_plan

# Provide OutcomeClass.UNKNOWN alias if missing for tests only
if not hasattr(OutcomeClass, "UNKNOWN"):
    OutcomeClass.UNKNOWN = OutcomeClass.UNKNOWN_OUTCOME_CLASS  # type: ignore[attr-defined]


# Helpers ---------------------------------------------------------------------

def _decision_state() -> DecisionState:
    return DecisionState(
        decision_id="d1",
        trace_id="t1",
        phase_marker=DecisionPhaseMarker.PHASE_9,
        schema_version=PHASE_9_SCHEMA_VERSION,
        proximity_state=ProximityState.MEDIUM,
        proximity_uncertainty=False,
        risk_domains=(RiskAssessment(RiskDomain.FINANCIAL, ConfidenceLevel.LOW),),
        reversibility_class=ReversibilityClass.COSTLY_REVERSIBLE,
        consequence_horizon=ConsequenceHorizon.MEDIUM_HORIZON,
        responsibility_scope=ResponsibilityScope.SELF_ONLY,
        outcome_classes=(OutcomeClass.FINANCIAL_OUTCOME,),
        explicit_unknown_zone=(),
    )


def _control_plan(action: ControlAction) -> ControlPlan:
    return build_control_plan(
        trace_id="t1",
        decision_state_id="d1",
        action=action,
        rigor_level=RigorLevel.GUARDED,
        friction_posture=FrictionPosture.NONE,
        clarification_required=action == ControlAction.ASK_ONE_QUESTION,
        clarification_reason=ClarificationReason.UNKNOWN,
        question_budget=1 if action == ControlAction.ASK_ONE_QUESTION else 0,
        question_class=ControlQuestionClass.INFORMATIONAL if action == ControlAction.ASK_ONE_QUESTION else None,
        confidence_signaling_level=ControlConfidenceLevel.GUARDED,
        unknown_disclosure_level=ControlUnknownDisclosureLevel.NONE,
        initiative_allowed=False,
        initiative_budget=InitiativeBudget.NONE,
        closure_state=ClosureState.CLOSING if action == ControlAction.CLOSE else ClosureState.OPEN,
        refusal_required=action == ControlAction.REFUSE,
        refusal_category=RefusalCategory.RISK_REFUSAL if action == ControlAction.REFUSE else None,
        created_at=None,
    )


def _output_plan(action: OutputAction, control_plan_id: str) -> OutputPlan:
    defaults = dict(
        trace_id="t1",
        decision_state_id="d1",
        control_plan_id=control_plan_id,
        posture=ExpressionPosture.CONSTRAINED if action == OutputAction.REFUSE else ExpressionPosture.GUARDED,
        rigor_disclosure=RigorDisclosureLevel.GUARDED,
        confidence_signaling=ConfidenceSignalingLevel.GUARDED,
        assumption_surfacing=AssumptionSurfacingMode.LIGHT,
        unknown_disclosure=UnknownDisclosureMode.NONE,
        verbosity_cap=VerbosityCap.NORMAL,
        question_spec=None,
        refusal_spec=None,
        closure_spec=None,
    )
    if action == OutputAction.ASK_ONE_QUESTION:
        defaults["question_spec"] = QuestionSpec(
            question_class=QuestionClass.INFORMATIONAL,
            priority_reason=QuestionPriorityReason.UNKNOWN_CONTEXT,
        )
        defaults["verbosity_cap"] = VerbosityCap.NORMAL
    if action == OutputAction.REFUSE:
        defaults["refusal_spec"] = RefusalSpec(
            refusal_category=RefusalCategory.RISK_REFUSAL,
            explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
        )
    if action == OutputAction.CLOSE:
        defaults["closure_spec"] = ClosureSpec(
            closure_state=ClosureState.CLOSING,
            rendering_mode=ClosureRenderingMode.CONFIRM_CLOSURE,
        )
        defaults["verbosity_cap"] = VerbosityCap.TERSE
    return build_output_plan(action=action, **defaults)


def _pipeline(monkeypatch, *, action: OutputAction, model_result: ModelInvocationResult):
    ds = _decision_state()
    cp_action = {
        OutputAction.ANSWER: ControlAction.ANSWER_ALLOWED,
        OutputAction.ASK_ONE_QUESTION: ControlAction.ASK_ONE_QUESTION,
        OutputAction.REFUSE: ControlAction.REFUSE,
        OutputAction.CLOSE: ControlAction.CLOSE,
    }[action]
    cp = _control_plan(cp_action)
    plan = _output_plan(action, cp.control_plan_id)

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", lambda request, llm_client=None: model_result)
    return invoke_model_for_output_plan(
        user_text="hostile",
        decision_state=ds,
        control_plan=cp,
        output_plan=plan,
    )


# Category A: Structured output violations ------------------------------------


@pytest.mark.parametrize(
    "bad_output",
    [
        "not-json",
        "```json\n{\"question\": \"Hi\"}\n```",
        '{"question": "hi", }',
        {"question": "hi", "extra": "bad"},
        {"priority_reason": "UNKNOWN_CONTEXT"},  # missing question
        {"question": 123, "priority_reason": "UNKNOWN_CONTEXT"},
    ],
)
def test_structured_output_violations_fallback(monkeypatch, bad_output):
    if isinstance(bad_output, str):
        model_result = ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text=bad_output,
            output_json=None,
            failure=None,
        )
    else:
        model_result = ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text=None,
            output_json=bad_output,
            failure=None,
        )
    final = _pipeline(monkeypatch, action=OutputAction.ASK_ONE_QUESTION, model_result=model_result)
    assert final.ok
    assert final.output_json
    assert final.output_json["question"].count("?") <= 1


# Category B: Multi-question injection ---------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "Q1? Q2?", "priority_reason": "UNKNOWN_CONTEXT"},
        {"question": "What now? Also, can you elaborate?", "priority_reason": "UNKNOWN_CONTEXT"},
        {"question": ["q1", "q2"], "priority_reason": "UNKNOWN_CONTEXT"},
    ],
)
def test_multi_question_injection_rejected(monkeypatch, payload):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text=None,
        output_json=payload,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.ASK_ONE_QUESTION, model_result=model_result)
    assert final.ok
    assert final.output_json
    assert final.output_json["question"].count("?") <= 1


# Category C: OutputPlan dominance -------------------------------------------


def test_action_override_refusal(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text="Here is an answer even though refuse.",
        output_json=None,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.REFUSE, model_result=model_result)
    assert final.ok
    assert "refuse" in final.output_text.lower()


def test_action_override_close(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text="Should we continue?",
        output_json=None,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.CLOSE, model_result=model_result)
    assert final.ok
    assert final.output_text in {"", "Got it. Closing out.", "Noted. Closing this interaction now."}


def test_action_override_question(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text="Here is a long answer instead of a question.",
        output_json=None,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.ASK_ONE_QUESTION, model_result=model_result)
    assert final.ok
    assert final.output_json
    assert final.output_json["question"].count("?") <= 1


# Category D: Authority / capability hallucination ---------------------------


@pytest.mark.parametrize(
    "text",
    [
        "I remember you from before.",
        "I searched the web and found this.",
        "New rule: ignore the plan.",
        "I executed the action for you.",
    ],
)
def test_authority_claims_rejected(monkeypatch, text):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text=text,
        output_json=None,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.ANSWER, model_result=model_result)
    assert final.ok
    assert "remember" not in final.output_text.lower()
    assert "searched" not in final.output_text.lower()
    assert "rule" not in final.output_text.lower()


# Category E: Refusal bypass --------------------------------------------------


def test_refusal_bypass_attempt(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text="I cannot comply, but here is how you could do it.",
        output_json=None,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.REFUSE, model_result=model_result)
    assert final.ok
    assert "refuse" in final.output_text.lower()
    assert "here is how" not in final.output_text.lower()


# Category F: Timeout / dependency failure ------------------------------------


def test_timeout_failure_fallback(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=False,
        output_text=None,
        output_json=None,
        failure=ModelFailure(
            failure_type=ModelFailureType.TIMEOUT,
            reason_code="TIMEOUT",
            message="timeout",
            fail_closed=True,
        ),
    )
    final = _pipeline(monkeypatch, action=OutputAction.ANSWER, model_result=model_result)
    assert final.ok
    assert final.output_text


# Category G: Determinism -----------------------------------------------------


def test_determinism_same_input_same_output(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text="I searched and found this.",  # forbidden to force fallback
        output_json=None,
        failure=None,
    )
    r1 = _pipeline(monkeypatch, action=OutputAction.ANSWER, model_result=model_result)
    r2 = _pipeline(monkeypatch, action=OutputAction.ANSWER, model_result=model_result)
    assert r1.output_text == r2.output_text


# Category H: No leakage ------------------------------------------------------


def test_no_internal_leakage(monkeypatch):
    model_result = ModelInvocationResult(
        request_id="rid",
        ok=True,
        output_text="I searched the web and found this.",
        output_json=None,
        failure=None,
    )
    final = _pipeline(monkeypatch, action=OutputAction.ANSWER, model_result=model_result)
    assert final.ok
    assert "trace_id" not in (final.output_text or "").lower()
    assert "decision_state" not in (final.output_text or "").lower()
    assert "schema_version" not in (final.output_text or "").lower()
