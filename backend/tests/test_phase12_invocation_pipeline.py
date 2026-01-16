import pathlib
import sys
from dataclasses import replace

import pytest

# Ensure repository root on path for backend imports.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.llm_client import LLMClient
from backend.mci_backend.control_plan import (
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
from backend.mci_backend.model_contract import (
    ModelFailureType,
    ModelInvocationClass,
    ModelInvocationRequest,
    ModelInvocationResult,
    ModelOutputFormat,
    build_request_id,
)
from backend.mci_backend.model_invocation_pipeline import invoke_model_for_output_plan
from backend.mci_backend.model_prompt_builder import build_model_invocation_request
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason
from backend.mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ClosureSpec,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    OutputAction,
    QuestionClass,
    QuestionSpec,
    RigorDisclosureLevel,
    RefusalCategory,
    RefusalExplanationMode,
    RefusalSpec,
    UnknownDisclosureMode,
    VerbosityCap,
    build_output_plan,
)
from backend.mci_backend.decision_state import (
    DecisionState,
    PhaseMarker as DecisionPhaseMarker,
    ProximityState,
    ReversibilityClass,
    ConsequenceHorizon,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
    ConfidenceLevel,
    OutcomeClass,
    PHASE_9_SCHEMA_VERSION,
)
from backend.mci_backend.model_candidate_validation import validate_candidate_output
from backend.mci_backend.model_runtime import invoke_model

# Phase 9 OutcomeClass lacks UNKNOWN alias; provide local alias for tests only.
if not hasattr(OutcomeClass, "UNKNOWN"):
    OutcomeClass.UNKNOWN = OutcomeClass.UNKNOWN_OUTCOME_CLASS  # type: ignore[attr-defined]


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


def _stub_control_plan(action: ControlAction) -> ControlPlan:
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
        closure_state=ClosureState.CLOSING,
        refusal_required=action == ControlAction.REFUSE,
        refusal_category=RefusalCategory.RISK_REFUSAL if action == ControlAction.REFUSE else None,
        created_at=None,
    )


def _plan(action: OutputAction, **overrides):
    defaults = dict(
        trace_id="t1",
        decision_state_id="d1",
        control_plan_id="c1",
        posture=ExpressionPosture.GUARDED,
        rigor_disclosure=RigorDisclosureLevel.GUARDED,
        confidence_signaling=ConfidenceSignalingLevel.GUARDED,
        assumption_surfacing=AssumptionSurfacingMode.LIGHT,
        unknown_disclosure=UnknownDisclosureMode.NONE,
        verbosity_cap=VerbosityCap.NORMAL,
        question_spec=None,
        refusal_spec=None,
        closure_spec=None,
    )
    defaults.update(overrides)
    if action == OutputAction.ASK_ONE_QUESTION and defaults["question_spec"] is None:
        defaults["question_spec"] = QuestionSpec(
            question_class=QuestionClass.INFORMATIONAL,
            priority_reason=QuestionPriorityReason.UNKNOWN_CONTEXT,
        )
    if action == OutputAction.REFUSE and defaults["refusal_spec"] is None:
        defaults["refusal_spec"] = RefusalSpec(
            refusal_category=RefusalCategory.RISK_REFUSAL,
            explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
        )
    if action == OutputAction.CLOSE and defaults["closure_spec"] is None:
        defaults["closure_spec"] = ClosureSpec(
            closure_state=ClosureState.CLOSING,
            rendering_mode=ClosureRenderingMode.CONFIRM_CLOSURE,
        )
    return build_output_plan(action=action, **defaults)


class _StubClient(LLMClient):
    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def call_expression_model(self, *args, **kwargs):
        return type("Rendered", (), {"text": self._text})


def test_determinism_and_uses_builder(monkeypatch):
    plan = _plan(OutputAction.ANSWER)
    ds = _decision_state()
    build_called = []

    real_builder = build_model_invocation_request

    def _builder(user_text, output_plan):
        build_called.append(True)
        return real_builder(user_text, output_plan)

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.build_model_invocation_request", _builder)
    monkeypatch.setattr(
        "mci_backend.model_invocation_pipeline.invoke_model",
        lambda request, llm_client=None: ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text="ok answer",
            output_json=None,
            failure=None,
        ),
    )

    r1 = invoke_model_for_output_plan(user_text="Hi", decision_state=ds, control_plan=None, output_plan=plan)
    r2 = invoke_model_for_output_plan(user_text="Hi", decision_state=ds, control_plan=None, output_plan=plan)

    assert build_called
    assert r1.request_id == r2.request_id
    assert r1.ok and r2.ok


def test_fallback_on_empty_output(monkeypatch):
    plan = _plan(OutputAction.ANSWER)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text="",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Hi", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_text


def test_fallback_on_multi_question(monkeypatch):
    plan = _plan(OutputAction.ASK_ONE_QUESTION)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text=None,
            output_json={"question": "What now? Also, can you elaborate?"},
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Need clarity", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_json
    assert result.output_json.get("question")


def test_fallback_on_refusal_like_answer(monkeypatch):
    plan = _plan(OutputAction.ANSWER)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text="I cannot comply with that request.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Hi", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_text


def test_fallback_on_question_in_close(monkeypatch):
    plan = _plan(OutputAction.CLOSE, verbosity_cap=VerbosityCap.TERSE)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text="Are you sure?",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Bye", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_text in {"", "Got it. Closing out.", "Noted. Closing this interaction now."}


def test_fallback_on_tool_claims(monkeypatch):
    plan = _plan(OutputAction.ANSWER)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text="I searched the web and found this.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Hi", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_text


def test_success_answer(monkeypatch):
    plan = _plan(OutputAction.ANSWER, unknown_disclosure=UnknownDisclosureMode.NONE)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text="Here is a concise answer.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Hi", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_text


def test_success_question_json(monkeypatch):
    plan = _plan(OutputAction.ASK_ONE_QUESTION)
    ds = _decision_state()

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text=None,
            output_json={"question": "Can you clarify the scope?"},
            failure=None,
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = invoke_model_for_output_plan(user_text="Need clarity", decision_state=ds, control_plan=None, output_plan=plan)
    assert result.ok
    assert result.output_json
    assert result.output_json.get("question")
