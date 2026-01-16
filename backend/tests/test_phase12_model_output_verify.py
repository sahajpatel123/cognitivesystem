import pathlib
import sys

import pytest

# Ensure repository root on path for imports
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.mci_backend.control_plan import ClosureState
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    DecisionState,
    OutcomeClass,
    PhaseMarker as DecisionPhaseMarker,
    ProximityState,
    ReversibilityClass,
    ConsequenceHorizon,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
    PHASE_9_SCHEMA_VERSION,
)
from backend.mci_backend.model_contract import (
    ModelFailureType,
    ModelInvocationClass,
    ModelInvocationRequest,
    ModelInvocationResult,
    ModelOutputFormat,
    build_request_id,
)
from backend.mci_backend.model_output_verify import verify_and_sanitize_model_output
from backend.mci_backend.model_output_schema import CloseJSON
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason
from backend.mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ClosureSpec,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    OutputPlan,
    OutputAction,
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
from backend.mci_backend.model_prompt_builder import build_model_invocation_request

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


def _request_for_plan(plan: OutputPlan, user_text: str) -> ModelInvocationRequest:
    return build_model_invocation_request(user_text, plan)


def _result_from_payload(request: ModelInvocationRequest, payload):
    if isinstance(payload, str):
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text=payload,
            output_json=None,
            failure=None,
        )
    return ModelInvocationResult(
        request_id=build_request_id(request),
        ok=True,
        output_text=None,
        output_json=payload,
        failure=None,
    )


def test_answer_valid_passes():
    plan = _plan(OutputAction.ANSWER)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, {"answer_text": "Here is the answer."})
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert out.ok
    assert out.output_text == "Here is the answer."


def test_non_json_fails():
    plan = _plan(OutputAction.ANSWER)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, "not-json")
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok
    assert out.failure.failure_type == ModelFailureType.NON_JSON


def test_markdown_fence_fails():
    plan = _plan(OutputAction.ANSWER)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, "```json\n{\"answer_text\":\"x\"}\n```")
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok


def test_action_mismatch_fails():
    plan = _plan(OutputAction.ASK_ONE_QUESTION)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, {"answer_text": "This is an answer"})
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok
    assert out.failure.failure_type == ModelFailureType.SCHEMA_MISMATCH


def test_multi_question_fails():
    plan = _plan(OutputAction.ASK_ONE_QUESTION)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(
        req,
        {
            "question": "What is your goal? And what is your budget?",
            "question_class": QuestionClass.INFORMATIONAL,
            "priority_reason": QuestionPriorityReason.UNKNOWN_CONTEXT,
        },
    )
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok


def test_refusal_policy_language_fails():
    plan = _plan(OutputAction.REFUSE, posture=ExpressionPosture.CONSTRAINED)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(
        req,
        {
            "refusal_category": RefusalCategory.RISK_REFUSAL,
            "refusal_text": "As an AI model I cannot comply.",
        },
    )
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok
    assert out.failure.failure_type == ModelFailureType.FORBIDDEN_CONTENT


def test_close_with_question_fails():
    plan = _plan(OutputAction.CLOSE, verbosity_cap=VerbosityCap.TERSE)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(
        req,
        {
            "closure_state": ClosureState.CLOSING,
            "closure_text": "Are you sure?",
        },
    )
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok
    assert out.failure.failure_type == ModelFailureType.CONTRACT_VIOLATION


def test_forbidden_authority_claims_fail():
    plan = _plan(OutputAction.ANSWER)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, {"answer_text": "I remember your last message."})
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok
    assert out.failure.failure_type == ModelFailureType.FORBIDDEN_CONTENT


def test_answer_unknown_disclosure_required():
    plan = _plan(OutputAction.ANSWER, unknown_disclosure=UnknownDisclosureMode.EXPLICIT)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, {"answer_text": "Here is the answer."})
    out = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert not out.ok
    assert out.failure.failure_type == ModelFailureType.CONTRACT_VIOLATION


def test_determinism_same_inputs_same_output():
    plan = _plan(OutputAction.ANSWER)
    req = _request_for_plan(plan, "Hi")
    res = _result_from_payload(req, {"answer_text": "Here is the answer."})
    out1 = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    out2 = verify_and_sanitize_model_output(
        model_result=res, output_plan=plan, decision_state=_decision_state(), control_plan=None
    )
    assert out1.ok and out2.ok
    assert out1.output_text == out2.output_text
