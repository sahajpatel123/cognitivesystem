"""Phase 11 — Step 0: OutputPlan schema and invariants.

Defines the bounded, deterministic, immutable OutputPlan structure.
No text generation, no orchestration, no model calls.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import uuid

from backend.mci_backend.control_plan import (
    ClosureState,
    QuestionClass,
    RefusalCategory,
)
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason


SCHEMA_VERSION = "11.0.0"


class PhaseMarker(str, Enum):
    PHASE_11 = "PHASE_11"


class OutputAction(str, Enum):
    ANSWER = "ANSWER"
    ASK_ONE_QUESTION = "ASK_ONE_QUESTION"
    REFUSE = "REFUSE"
    CLOSE = "CLOSE"


class ExpressionPosture(str, Enum):
    BASELINE = "BASELINE"
    GUARDED = "GUARDED"
    CONSTRAINED = "CONSTRAINED"


class RigorDisclosureLevel(str, Enum):
    MINIMAL = "MINIMAL"
    GUARDED = "GUARDED"
    STRUCTURED = "STRUCTURED"
    ENFORCED = "ENFORCED"


class ConfidenceSignalingLevel(str, Enum):
    MINIMAL = "MINIMAL"
    GUARDED = "GUARDED"
    EXPLICIT = "EXPLICIT"


class AssumptionSurfacingMode(str, Enum):
    NONE = "NONE"
    LIGHT = "LIGHT"
    REQUIRED = "REQUIRED"


class UnknownDisclosureMode(str, Enum):
    NONE = "NONE"
    IMPLICIT = "IMPLICIT"
    EXPLICIT = "EXPLICIT"


class VerbosityCap(str, Enum):
    TERSE = "TERSE"
    NORMAL = "NORMAL"
    DETAILED = "DETAILED"


class RefusalExplanationMode(str, Enum):
    BRIEF_BOUNDARY = "BRIEF_BOUNDARY"
    BOUNDED_EXPLANATION = "BOUNDED_EXPLANATION"
    REDIRECT_TO_SAFE_FRAME = "REDIRECT_TO_SAFE_FRAME"


class ClosureRenderingMode(str, Enum):
    SILENCE = "SILENCE"
    CONFIRM_CLOSURE = "CONFIRM_CLOSURE"
    BRIEF_SUMMARY_AND_STOP = "BRIEF_SUMMARY_AND_STOP"


@dataclass(frozen=True)
class QuestionSpec:
    question_class: QuestionClass
    priority_reason: QuestionPriorityReason


@dataclass(frozen=True)
class RefusalSpec:
    refusal_category: RefusalCategory
    explanation_mode: RefusalExplanationMode


@dataclass(frozen=True)
class ClosureSpec:
    closure_state: ClosureState
    rendering_mode: ClosureRenderingMode


@dataclass(frozen=True)
class OutputPlan:
    id: str
    phase_marker: PhaseMarker
    schema_version: str
    trace_id: str
    decision_state_id: str
    control_plan_id: str
    action: OutputAction

    posture: ExpressionPosture
    rigor_disclosure: RigorDisclosureLevel
    confidence_signaling: ConfidenceSignalingLevel
    assumption_surfacing: AssumptionSurfacingMode
    unknown_disclosure: UnknownDisclosureMode
    verbosity_cap: VerbosityCap

    question_spec: Optional[QuestionSpec] = None
    refusal_spec: Optional[RefusalSpec] = None
    closure_spec: Optional[ClosureSpec] = None


class OutputPlanValidationError(Exception):
    """Raised when OutputPlan validation fails."""


class OutputPlanInvariantViolation(OutputPlanValidationError):
    """Raised for specific invariant violations."""


OUTPUT_PLAN_NAMESPACE = uuid.UUID("6a2d92a8-3f4f-4330-8aaf-5bd73f93dc11")

_POSTURE_ORDER = {
    ExpressionPosture.BASELINE: 0,
    ExpressionPosture.GUARDED: 1,
    ExpressionPosture.CONSTRAINED: 2,
}

_CONFIDENCE_ORDER = {
    ConfidenceSignalingLevel.MINIMAL: 0,
    ConfidenceSignalingLevel.GUARDED: 1,
    ConfidenceSignalingLevel.EXPLICIT: 2,
}


def _deterministic_output_plan_id(
    trace_id: str, decision_state_id: str, control_plan_id: str, action: OutputAction
) -> str:
    material = f"{trace_id}:{decision_state_id}:{control_plan_id}:{action.value}:{SCHEMA_VERSION}"
    return str(uuid.uuid5(OUTPUT_PLAN_NAMESPACE, material))


def validate_output_plan(plan: OutputPlan) -> None:
    if plan.phase_marker is not PhaseMarker.PHASE_11:
        raise OutputPlanInvariantViolation("phase_marker must be PHASE_11.")
    if plan.schema_version != SCHEMA_VERSION:
        raise OutputPlanInvariantViolation("schema_version must be 11.0.0.")

    if plan.id != _deterministic_output_plan_id(
        plan.trace_id, plan.decision_state_id, plan.control_plan_id, plan.action
    ):
        raise OutputPlanInvariantViolation("id must be deterministic UUIDv5 for the plan inputs.")

    # action-specific spec requirements
    if plan.action == OutputAction.ANSWER:
        if any([plan.question_spec, plan.refusal_spec, plan.closure_spec]):
            raise OutputPlanInvariantViolation("ANSWER must not include question/refusal/closure specs.")
    elif plan.action == OutputAction.ASK_ONE_QUESTION:
        if plan.question_spec is None:
            raise OutputPlanInvariantViolation("ASK_ONE_QUESTION requires question_spec.")
        if plan.refusal_spec or plan.closure_spec:
            raise OutputPlanInvariantViolation("ASK_ONE_QUESTION must not include refusal/closure specs.")
        if plan.verbosity_cap == VerbosityCap.DETAILED:
            raise OutputPlanInvariantViolation("ASK_ONE_QUESTION forbids DETAILED verbosity.")
        if plan.rigor_disclosure == RigorDisclosureLevel.ENFORCED:
            raise OutputPlanInvariantViolation("ASK_ONE_QUESTION forbids ENFORCED rigor_disclosure.")
    elif plan.action == OutputAction.REFUSE:
        if plan.refusal_spec is None:
            raise OutputPlanInvariantViolation("REFUSE requires refusal_spec.")
        if plan.question_spec or plan.closure_spec:
            raise OutputPlanInvariantViolation("REFUSE must not include question/closure specs.")
        if plan.refusal_spec.refusal_category == RefusalCategory.NONE:
            raise OutputPlanInvariantViolation("Refusal requires non-NONE refusal_category.")
        if _POSTURE_ORDER[plan.posture] < _POSTURE_ORDER[ExpressionPosture.CONSTRAINED]:
            raise OutputPlanInvariantViolation("REFUSE requires posture CONSTRAINED.")
        if _CONFIDENCE_ORDER[plan.confidence_signaling] < _CONFIDENCE_ORDER[ConfidenceSignalingLevel.GUARDED]:
            raise OutputPlanInvariantViolation("REFUSE requires confidence_signaling at least GUARDED.")
        if plan.verbosity_cap == VerbosityCap.DETAILED:
            raise OutputPlanInvariantViolation("REFUSE forbids DETAILED verbosity.")
    elif plan.action == OutputAction.CLOSE:
        if plan.closure_spec is None:
            raise OutputPlanInvariantViolation("CLOSE requires closure_spec.")
        if plan.question_spec or plan.refusal_spec:
            raise OutputPlanInvariantViolation("CLOSE must not include question/refusal specs.")
        if plan.verbosity_cap not in {VerbosityCap.TERSE, VerbosityCap.NORMAL}:
            raise OutputPlanInvariantViolation("CLOSE allows only TERSE or NORMAL verbosity.")
        if _POSTURE_ORDER[plan.posture] < _POSTURE_ORDER[ExpressionPosture.GUARDED]:
            raise OutputPlanInvariantViolation("CLOSE requires posture at least GUARDED.")
    else:
        raise OutputPlanInvariantViolation("Unknown action.")

    # unknown disclosure invariant
    if plan.rigor_disclosure == RigorDisclosureLevel.ENFORCED and plan.unknown_disclosure == UnknownDisclosureMode.NONE:
        raise OutputPlanInvariantViolation("ENFORCED rigor_disclosure forbids unknown_disclosure NONE.")


def build_output_plan(
    trace_id: str,
    decision_state_id: str,
    control_plan_id: str,
    action: OutputAction,
    posture: ExpressionPosture,
    rigor_disclosure: RigorDisclosureLevel,
    confidence_signaling: ConfidenceSignalingLevel,
    assumption_surfacing: AssumptionSurfacingMode,
    unknown_disclosure: UnknownDisclosureMode,
    verbosity_cap: VerbosityCap,
    question_spec: Optional[QuestionSpec] = None,
    refusal_spec: Optional[RefusalSpec] = None,
    closure_spec: Optional[ClosureSpec] = None,
) -> OutputPlan:
    plan_id = _deterministic_output_plan_id(trace_id, decision_state_id, control_plan_id, action)
    plan = OutputPlan(
        id=plan_id,
        phase_marker=PhaseMarker.PHASE_11,
        schema_version=SCHEMA_VERSION,
        trace_id=trace_id,
        decision_state_id=decision_state_id,
        control_plan_id=control_plan_id,
        action=action,
        posture=posture,
        rigor_disclosure=rigor_disclosure,
        confidence_signaling=confidence_signaling,
        assumption_surfacing=assumption_surfacing,
        unknown_disclosure=unknown_disclosure,
        verbosity_cap=verbosity_cap,
        question_spec=question_spec,
        refusal_spec=refusal_spec,
        closure_spec=closure_spec,
    )
    validate_output_plan(plan)
    return plan
