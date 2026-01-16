import pathlib
import sys
from dataclasses import replace

import pytest

# Ensure repository root on path for backend imports.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.mci_backend.control_plan import ClosureState
from backend.mci_backend.model_contract import (
    ModelContractInvariantViolation,
    ModelInvocationClass,
    ModelOutputFormat,
    build_request_id,
)
from backend.mci_backend.model_prompt_builder import ModelPromptBuilderError, build_model_invocation_request
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


def _plan(action: OutputAction, **overrides):
    defaults = dict(
        trace_id="t1",
        decision_state_id="d1",
        control_plan_id="c1",
        posture=ExpressionPosture.GUARDED,
        rigor_disclosure=RigorDisclosureLevel.GUARDED,
        confidence_signaling=ConfidenceSignalingLevel.GUARDED,
        assumption_surfacing=AssumptionSurfacingMode.LIGHT,
        unknown_disclosure=UnknownDisclosureMode.EXPLICIT,
        verbosity_cap=VerbosityCap.NORMAL,
        question_spec=None,
        refusal_spec=None,
        closure_spec=None,
    )
    defaults.update(overrides)
    # Provide minimal required specs per action
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


def test_answer_invocation_class_and_envelope():
    plan = _plan(OutputAction.ANSWER, verbosity_cap=VerbosityCap.NORMAL)
    req = build_model_invocation_request("Hello", plan)
    assert req.invocation_class == ModelInvocationClass.EXPRESSION_CANDIDATE
    assert req.output_format == ModelOutputFormat.TEXT
    assert "SYSTEM:" in req.user_text
    assert "CONSTRAINT_TAGS" in req.user_text
    for term in ("DecisionState", "ControlPlan", "trace_id", "audit", "governance"):
        assert term not in req.user_text


def test_ask_one_question_json_schema_and_determinism():
    q_plan = _plan(OutputAction.ASK_ONE_QUESTION)
    req1 = build_model_invocation_request("Need clarity", q_plan)
    req2 = build_model_invocation_request("Need clarity", q_plan)

    assert req1.invocation_class == ModelInvocationClass.CLARIFICATION_CANDIDATE
    assert req1.output_format == ModelOutputFormat.JSON
    assert '"question": "string"' in req1.user_text
    assert req1.user_text == req2.user_text
    assert build_request_id(req1) == build_request_id(req2)


def test_refuse_invocation_enforces_no_policy_language():
    r_plan = _plan(OutputAction.REFUSE, posture=ExpressionPosture.CONSTRAINED, verbosity_cap=VerbosityCap.NORMAL)
    req = build_model_invocation_request("No", r_plan)
    assert req.invocation_class == ModelInvocationClass.REFUSAL_EXPLANATION_CANDIDATE
    assert req.output_format == ModelOutputFormat.TEXT
    assert "policy" not in req.user_text.lower()


def test_close_invocation_is_terse():
    c_plan = _plan(OutputAction.CLOSE, posture=ExpressionPosture.GUARDED, verbosity_cap=VerbosityCap.TERSE)
    req = build_model_invocation_request("Done", c_plan)
    assert req.invocation_class == ModelInvocationClass.CLOSURE_MESSAGE_CANDIDATE
    assert req.output_format == ModelOutputFormat.TEXT
    assert "closure" in req.user_text.lower()


def test_forbidden_terms_absent():
    plan = _plan(OutputAction.ANSWER)
    req = build_model_invocation_request("Hello", plan)
    forbidden = ["DecisionState", "ControlPlan", "trace_id", "audit", "governance"]
    assert all(term not in req.user_text for term in forbidden)


def test_fail_closed_on_invalid_plan():
    valid_plan = _plan(OutputAction.ASK_ONE_QUESTION)
    invalid_plan = replace(valid_plan, verbosity_cap=VerbosityCap.DETAILED)
    with pytest.raises(ModelPromptBuilderError):
        build_model_invocation_request("x", invalid_plan)
