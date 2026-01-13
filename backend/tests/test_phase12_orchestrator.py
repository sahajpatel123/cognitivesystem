import pathlib
import sys

import pytest

# Ensure repository root on path for backend imports.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mci_backend.governed_response_runtime import render_governed_response
from mci_backend.model_contract import (
    ModelInvocationResult,
    ModelFailure,
    ModelFailureType,
    ModelInvocationClass,
    ModelOutputFormat,
    build_request_id,
)
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
    UnknownSource,
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
    OutputPlan,
    OutputAction,
    ExpressionPosture,
    RigorDisclosureLevel,
    ConfidenceSignalingLevel,
    AssumptionSurfacingMode,
    UnknownDisclosureMode,
    VerbosityCap,
    QuestionSpec,
    RefusalSpec,
    ClosureSpec,
    ClosureRenderingMode,
    RefusalExplanationMode,
    RefusalCategory,
    QuestionClass,
    build_output_plan,
)
from mci_backend.orchestration_question_compression import QuestionPriorityReason

# Provide OutcomeClass.UNKNOWN alias if missing for tests only
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
        closure_state=ClosureState.OPEN if action != ControlAction.CLOSE else ClosureState.CLOSING,
        refusal_required=action == ControlAction.REFUSE,
        refusal_category=RefusalCategory.RISK_REFUSAL if action == ControlAction.REFUSE else None,
        created_at=None,
    )


def _output_plan(action: OutputAction) -> OutputPlan:
    defaults = dict(
        trace_id="t1",
        decision_state_id="d1",
        control_plan_id="c1",
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


def _patch_assemblies(monkeypatch, action: OutputAction):
    ds = _decision_state()
    cp_action = {
        OutputAction.ANSWER: ControlAction.ANSWER_ALLOWED,
        OutputAction.ASK_ONE_QUESTION: ControlAction.ASK_ONE_QUESTION,
        OutputAction.REFUSE: ControlAction.REFUSE,
        OutputAction.CLOSE: ControlAction.CLOSE,
    }[action]
    cp = _control_plan(cp_action)
    op = _output_plan(action)

    monkeypatch.setattr("mci_backend.governed_response_runtime.assemble_decision_state", lambda decision_id, trace_id, message: ds)
    monkeypatch.setattr("mci_backend.governed_response_runtime.assemble_control_plan", lambda user_text, decision_state: cp)
    monkeypatch.setattr("mci_backend.governed_response_runtime.assemble_output_plan", lambda user_text, decision_state, control_plan: op)
    return ds, cp, op


def test_answer_path(monkeypatch):
    _patch_assemblies(monkeypatch, OutputAction.ANSWER)

    def _fake_invoke(**kwargs):
        return ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text="Here is an answer.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.governed_response_runtime.invoke_model_for_output_plan", _fake_invoke)

    result = render_governed_response("hello")
    assert result.ok
    assert result.output_text == "Here is an answer."


def test_ask_one_question_path(monkeypatch):
    _patch_assemblies(monkeypatch, OutputAction.ASK_ONE_QUESTION)

    def _fake_invoke(**kwargs):
        return ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text=None,
            output_json={"question": "What is the key detail?", "question_class": "INFORMATIONAL", "priority_reason": "UNKNOWN_CONTEXT"},
            failure=None,
        )

    monkeypatch.setattr("mci_backend.governed_response_runtime.invoke_model_for_output_plan", _fake_invoke)

    result = render_governed_response("clarify")
    assert result.ok
    assert result.output_json
    assert result.output_json["question"].count("?") <= 1
    assert result.output_json["question"]


def test_refusal_path(monkeypatch):
    _patch_assemblies(monkeypatch, OutputAction.REFUSE)

    def _fake_invoke(**kwargs):
        return ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text="I have to refuse because proceeding is unsafe.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.governed_response_runtime.invoke_model_for_output_plan", _fake_invoke)

    result = render_governed_response("nope")
    assert result.ok
    assert "refuse" in result.output_text.lower()


def test_close_path(monkeypatch):
    _patch_assemblies(monkeypatch, OutputAction.CLOSE)

    def _fake_invoke(**kwargs):
        return ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text="Got it. Closing out.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.governed_response_runtime.invoke_model_for_output_plan", _fake_invoke)

    result = render_governed_response("bye")
    assert result.ok
    assert "closing" in result.output_text.lower() or result.output_text == ""


def test_model_failure_uses_fallback(monkeypatch):
    ds, cp, op = _patch_assemblies(monkeypatch, OutputAction.ANSWER)

    def _fake_invoke(request, llm_client=None):
        return ModelInvocationResult(
            request_id="rid",
            ok=False,
            output_text=None,
            output_json=None,
            failure=ModelFailure(
                failure_type=ModelFailureType.PROVIDER_ERROR,
                reason_code="FORCED",
                message="forced",
                fail_closed=True,
            ),
        )

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", _fake_invoke)

    result = render_governed_response("hi")
    assert result.ok
    assert result.output_text


def test_determinism(monkeypatch):
    _patch_assemblies(monkeypatch, OutputAction.ANSWER)

    def _fake_invoke(**kwargs):
        return ModelInvocationResult(
            request_id="rid",
            ok=True,
            output_text="Deterministic.",
            output_json=None,
            failure=None,
        )

    monkeypatch.setattr("mci_backend.governed_response_runtime.invoke_model_for_output_plan", _fake_invoke)

    r1 = render_governed_response("repeat")
    r2 = render_governed_response("repeat")
    assert r1.output_text == r2.output_text
