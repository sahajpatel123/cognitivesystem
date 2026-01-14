from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Tuple

from mci_backend.control_plan import (
    ClarificationReason,
    ClosureState,
    ControlAction,
    ControlPlan,
    ConfidenceSignalingLevel,
    FrictionPosture,
    InitiativeBudget,
    QuestionClass,
    RefusalCategory,
    RigorLevel,
    UnknownDisclosureLevel,
    build_control_plan,
)
from mci_backend.decision_state import (
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
from mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ConfidenceSignalingLevel as OutputConfidenceLevel,
    ExpressionPosture,
    OutputAction,
    QuestionSpec,
    RefusalExplanationMode,
    RefusalSpec,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
    VerbosityCap,
    build_output_plan,
    ClosureSpec,
)
from mci_backend.orchestration_question_compression import QuestionPriorityReason


@dataclass
class FixtureBundle:
    decision_state: DecisionState
    control_plan: ControlPlan
    output_plan: object


# Ensure compatibility if OutcomeClass.UNKNOWN is absent
if not hasattr(OutcomeClass, "UNKNOWN"):
    setattr(OutcomeClass, "UNKNOWN", OutcomeClass.UNKNOWN_OUTCOME_CLASS)  # type: ignore[attr-defined]


def make_decision_state(
    *,
    outcome_classes: Tuple[OutcomeClass, ...] = (OutcomeClass.FINANCIAL_OUTCOME,),
    unknown_zone: Tuple[UnknownSource, ...] = (),
    proximity_state: ProximityState = ProximityState.LOW,
) -> DecisionState:
    trace_id = str(uuid.uuid4())
    return DecisionState(
        decision_id=str(uuid.uuid4()),
        trace_id=trace_id,
        phase_marker=DecisionPhaseMarker.PHASE_9,
        schema_version="9.0.0",
        proximity_state=proximity_state,
        proximity_uncertainty=False,
        risk_domains=(RiskAssessment(domain=RiskDomain.FINANCIAL, confidence=ConfidenceLevel.LOW),),
        reversibility_class=ReversibilityClass.COSTLY_REVERSIBLE,
        consequence_horizon=ConsequenceHorizon.MEDIUM_HORIZON,
        responsibility_scope=ResponsibilityScope.SELF_ONLY,
        outcome_classes=outcome_classes,
        explicit_unknown_zone=unknown_zone,
    )


def make_control_plan(decision_state: DecisionState, action: ControlAction) -> ControlPlan:
    trace_id = decision_state.trace_id
    if action == ControlAction.ASK_ONE_QUESTION:
        return build_control_plan(
            trace_id=trace_id,
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
            trace_id=trace_id,
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
            closure_state=ClosureState.OPEN,
            refusal_required=True,
            refusal_category=RefusalCategory.RISK_REFUSAL,
        )
    if action == ControlAction.CLOSE:
        return build_control_plan(
            trace_id=trace_id,
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
            closure_state=ClosureState.CLOSING,
            refusal_required=False,
            refusal_category=None,
        )
    # default answer
    return build_control_plan(
        trace_id=trace_id,
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


def make_output_plan(decision_state: DecisionState, control_plan: ControlPlan, action: OutputAction):
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
                closure_state=control_plan.closure_state,
                rendering_mode=ClosureRenderingMode.CONFIRM_CLOSURE,
            ),
        )
    raise ValueError("Unsupported action")
