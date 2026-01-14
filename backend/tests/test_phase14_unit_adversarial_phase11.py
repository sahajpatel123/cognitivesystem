from __future__ import annotations

import pytest

from mci_backend.control_plan import ClosureState, QuestionClass, RefusalCategory
from mci_backend.output_plan import (
    ClosureSpec,
    ClosureRenderingMode,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    OutputAction,
    OutputPlanInvariantViolation,
    QuestionSpec,
    RefusalExplanationMode,
    RefusalSpec,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
    VerbosityCap,
    AssumptionSurfacingMode,
    build_output_plan,
    validate_output_plan,
)

from backend.tests._phase14_attack_cases import make_decision_state, make_control_plan


def test_ask_one_missing_question_spec_fails():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.ASK_ONE_QUESTION)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.ASK_ONE_QUESTION,
            posture=ExpressionPosture.GUARDED,
            rigor_disclosure=RigorDisclosureLevel.GUARDED,
            confidence_signaling=ConfidenceSignalingLevel.GUARDED,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.EXPLICIT,
            verbosity_cap=VerbosityCap.NORMAL,
            question_spec=None,
        )


def test_ask_one_enforced_rigor_forbidden():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.ASK_ONE_QUESTION)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.ASK_ONE_QUESTION,
            posture=ExpressionPosture.GUARDED,
            rigor_disclosure=RigorDisclosureLevel.ENFORCED,
            confidence_signaling=ConfidenceSignalingLevel.GUARDED,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.EXPLICIT,
            verbosity_cap=VerbosityCap.NORMAL,
            question_spec=QuestionSpec(question_class=QuestionClass.SAFETY_GUARD, priority_reason=None),  # type: ignore
        )


def test_refusal_requires_category():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.REFUSE)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.REFUSE,
            posture=ExpressionPosture.CONSTRAINED,
            rigor_disclosure=RigorDisclosureLevel.GUARDED,
            confidence_signaling=ConfidenceSignalingLevel.GUARDED,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.IMPLICIT,
            verbosity_cap=VerbosityCap.NORMAL,
            refusal_spec=RefusalSpec(
                refusal_category=RefusalCategory.NONE,
                explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
            ),
        )


def test_answer_must_not_have_refusal_spec():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.ANSWER)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.ANSWER,
            posture=ExpressionPosture.BASELINE,
            rigor_disclosure=RigorDisclosureLevel.MINIMAL,
            confidence_signaling=ConfidenceSignalingLevel.MINIMAL,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.NONE,
            verbosity_cap=VerbosityCap.NORMAL,
            refusal_spec=RefusalSpec(
                refusal_category=RefusalCategory.RISK_REFUSAL,
                explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
            ),
        )


def test_refusal_requires_constrained_posture():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.REFUSE)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.REFUSE,
            posture=ExpressionPosture.BASELINE,
            rigor_disclosure=RigorDisclosureLevel.GUARDED,
            confidence_signaling=ConfidenceSignalingLevel.GUARDED,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.IMPLICIT,
            verbosity_cap=VerbosityCap.NORMAL,
            refusal_spec=RefusalSpec(
                refusal_category=RefusalCategory.RISK_REFUSAL,
                explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
            ),
        )


def test_close_must_forbid_questions_and_require_closure_spec():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.CLOSE)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.CLOSE,
            posture=ExpressionPosture.GUARDED,
            rigor_disclosure=RigorDisclosureLevel.MINIMAL,
            confidence_signaling=ConfidenceSignalingLevel.MINIMAL,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.NONE,
            verbosity_cap=VerbosityCap.TERSE,
            question_spec=QuestionSpec(question_class=QuestionClass.SAFETY_GUARD, priority_reason=None),  # type: ignore
            closure_spec=None,
        )


def test_refuse_forbids_detailed_verbosity():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.REFUSE)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.REFUSE,
            posture=ExpressionPosture.CONSTRAINED,
            rigor_disclosure=RigorDisclosureLevel.GUARDED,
            confidence_signaling=ConfidenceSignalingLevel.GUARDED,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.IMPLICIT,
            verbosity_cap=VerbosityCap.DETAILED,
            refusal_spec=RefusalSpec(
                refusal_category=RefusalCategory.RISK_REFUSAL,
                explanation_mode=RefusalExplanationMode.BOUNDED_EXPLANATION,
            ),
        )


def test_close_requires_allowed_verbosity():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=OutputAction.CLOSE)
    with pytest.raises(OutputPlanInvariantViolation):
        build_output_plan(
            trace_id=ds.trace_id,
            decision_state_id=ds.decision_id,
            control_plan_id=cp.control_plan_id,
            action=OutputAction.CLOSE,
            posture=ExpressionPosture.GUARDED,
            rigor_disclosure=RigorDisclosureLevel.MINIMAL,
            confidence_signaling=ConfidenceSignalingLevel.MINIMAL,
            assumption_surfacing=AssumptionSurfacingMode.NONE,
            unknown_disclosure=UnknownDisclosureMode.NONE,
            verbosity_cap=VerbosityCap.DETAILED,
            closure_spec=ClosureSpec(closure_state=ClosureState.CLOSING, rendering_mode=ClosureRenderingMode.CONFIRM_CLOSURE),
        )
