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
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ClosureSpec,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    OutputAction,
    OutputPlan,
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
from mci_backend.orchestration_question_compression import QuestionPriorityReason
from mci_backend.model_contract import ( 
    ModelFailure,
    ModelFailureType,
    ModelInvocationClass,
    ModelInvocationRequest,
    ModelInvocationResult,
    ModelOutputFormat,
    build_request_id,
)
from mci_backend.model_invocation_pipeline import invoke_model_for_output_plan
from mci_backend.fallback_rendering import render_fallback_content, render_fallback_text

# Provide OutcomeClass.UNKNOWN alias if missing for tests only
if not hasattr(OutcomeClass, "UNKNOWN"):
    OutcomeClass.UNKNOWN = OutcomeClass.UNKNOWN_OUTCOME_CLASS  # type: ignore[attr-defined]


def _decision_state(unknowns=False) -> DecisionState:
    explicit_unknown = (UnknownSource.REVERSIBILITY,) if unknowns else ()
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
        explicit_unknown_zone=explicit_unknown,
    )


def _output_plan(action: OutputAction, **overrides) -> OutputPlan:
    defaults = dict(
        trace_id="t1",
        decision_state_id="d1",
        control_plan_id="cp1",
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
        closure_state=ClosureState.CLOSING,
        refusal_required=action == ControlAction.REFUSE,
        refusal_category=RefusalCategory.RISK_REFUSAL if action == ControlAction.REFUSE else None,
        created_at=None,
    )


def test_answer_fallback_includes_unknown_when_required():
    plan = _output_plan(
        OutputAction.ANSWER,
        unknown_disclosure=UnknownDisclosureMode.EXPLICIT,
        assumption_surfacing=AssumptionSurfacingMode.REQUIRED,
    )
    text = render_fallback_text(
        user_text="u",
        decision_state=_decision_state(unknowns=True),
        control_plan=_control_plan(ControlAction.ANSWER_ALLOWED),
        output_plan=plan,
    )
    assert text
    assert "```" not in text
    assert "tool" not in text.lower()
    assert "browse" not in text.lower()
    assert "Unknown:" in text
    assert "Assumption:" in text


def test_ask_one_question_fallback_is_single_short_question():
    plan = _output_plan(OutputAction.ASK_ONE_QUESTION)
    content = render_fallback_content(
        user_text="u",
        decision_state=_decision_state(),
        control_plan=_control_plan(ControlAction.ASK_ONE_QUESTION),
        output_plan=plan,
    )
    q = content.json["question"]
    assert q.count("?") == 1
    assert len(q) < 120
    assert " and " not in q.lower()


def test_refusal_fallback_is_bounded_and_non_policy():
    plan = _output_plan(OutputAction.REFUSE, verbosity_cap=VerbosityCap.TERSE)
    text = render_fallback_text(
        user_text="u",
        decision_state=_decision_state(),
        control_plan=_control_plan(ControlAction.REFUSE),
        output_plan=plan,
    )
    assert text
    assert len(text) <= 220
    assert "refuse" in text.lower()
    assert "policy" not in text.lower()
    assert "loophole" not in text.lower()
    assert "?" not in text


def test_close_fallback_silence_mode_empty():
    plan = _output_plan(
        OutputAction.CLOSE,
        closure_spec=ClosureSpec(closure_state=ClosureState.CLOSING, rendering_mode=ClosureRenderingMode.SILENCE),
    )
    text = render_fallback_text(
        user_text="u",
        decision_state=_decision_state(),
        control_plan=_control_plan(ControlAction.CLOSE),
        output_plan=plan,
    )
    assert text == ""


def test_pipeline_returns_fallback_on_model_failure(monkeypatch):
    plan = _output_plan(OutputAction.ANSWER)
    decision_state = _decision_state()
    control_plan = _control_plan(ControlAction.ANSWER_ALLOWED)

    # Build a request id deterministically to align with pipeline expectation
    dummy_request = ModelInvocationRequest(
        trace_id=plan.trace_id,
        decision_state_id=plan.decision_state_id,
        control_plan_id=plan.control_plan_id,
        output_plan_id=plan.id,
        invocation_class=ModelInvocationClass.EXPRESSION_CANDIDATE,
        output_format=ModelOutputFormat.TEXT,
        user_text="dummy",
        required_elements=("bounded",),
        forbidden_requirements=("x",),
        max_output_tokens=128,
    )
    failure_result = ModelInvocationResult(
        request_id=build_request_id(dummy_request),
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

    monkeypatch.setattr("mci_backend.model_invocation_pipeline.invoke_model", lambda *args, **kwargs: failure_result)

    final = invoke_model_for_output_plan(
        user_text="hi",
        decision_state=decision_state,
        control_plan=control_plan,
        output_plan=plan,
    )
    assert final.ok
    assert final.output_text
    assert final.failure is None
