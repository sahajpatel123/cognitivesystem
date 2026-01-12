"""Phase 10 — Step 0: ControlPlan schema and invariants.

This module defines the bounded, deterministic, immutable ControlPlan output
contract for Phase 10. No behavior or orchestration is implemented here.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import uuid


SCHEMA_VERSION = "10.0.0"


class PhaseMarker(Enum):
    PHASE_10 = "PHASE_10"


class ControlAction(Enum):
    ANSWER_ALLOWED = "ANSWER_ALLOWED"
    ASK_ONE_QUESTION = "ASK_ONE_QUESTION"
    REFUSE = "REFUSE"
    CLOSE = "CLOSE"
    ABORT_FAIL_CLOSED = "ABORT_FAIL_CLOSED"


class RigorLevel(Enum):
    MINIMAL = "MINIMAL"
    GUARDED = "GUARDED"
    STRUCTURED = "STRUCTURED"
    ENFORCED = "ENFORCED"
    UNKNOWN = "UNKNOWN"


class FrictionPosture(Enum):
    NONE = "NONE"
    SOFT_PAUSE = "SOFT_PAUSE"
    HARD_PAUSE = "HARD_PAUSE"
    STOP = "STOP"


class ClarificationReason(Enum):
    DISAMBIGUATION = "DISAMBIGUATION"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    SAFETY = "SAFETY"
    SCOPE_CONFIRMATION = "SCOPE_CONFIRMATION"
    UNKNOWN = "UNKNOWN"


class QuestionClass(Enum):
    INFORMATIONAL = "INFORMATIONAL"
    SAFETY_GUARD = "SAFETY_GUARD"
    CONSENT = "CONSENT"
    OTHER_BOUNDARY = "OTHER_BOUNDARY"


class ConfidenceSignalingLevel(Enum):
    MINIMAL = "MINIMAL"
    GUARDED = "GUARDED"
    EXPLICIT = "EXPLICIT"


class UnknownDisclosureLevel(Enum):
    NONE = "NONE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class InitiativeBudget(Enum):
    NONE = "NONE"
    ONCE = "ONCE"
    STRICT_ONCE = "STRICT_ONCE"


class ClosureState(Enum):
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    USER_TERMINATED = "USER_TERMINATED"


class RefusalCategory(Enum):
    NONE = "NONE"
    CAPABILITY_REFUSAL = "CAPABILITY_REFUSAL"
    EPISTEMIC_REFUSAL = "EPISTEMIC_REFUSAL"
    RISK_REFUSAL = "RISK_REFUSAL"
    IRREVERSIBILITY_REFUSAL = "IRREVERSIBILITY_REFUSAL"
    THIRD_PARTY_REFUSAL = "THIRD_PARTY_REFUSAL"
    GOVERNANCE_REFUSAL = "GOVERNANCE_REFUSAL"


class ControlPlanValidationError(ValueError):
    """Raised when a ControlPlan violates schema or invariants."""


def _deterministic_plan_id(
    trace_id: str, decision_state_id: str, action: ControlAction
) -> str:
    material = f"{trace_id}:{decision_state_id}:{action.value}:{SCHEMA_VERSION}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, material))


@dataclass(frozen=True)
class ControlPlan:
    schema_version: str
    phase_marker: PhaseMarker
    control_plan_id: str
    trace_id: str
    decision_state_id: str
    action: ControlAction
    rigor_level: RigorLevel
    friction_posture: FrictionPosture
    clarification_required: bool
    clarification_reason: ClarificationReason
    question_budget: int
    question_class: Optional[QuestionClass]
    confidence_signaling_level: ConfidenceSignalingLevel
    unknown_disclosure_level: UnknownDisclosureLevel
    initiative_allowed: bool
    initiative_budget: InitiativeBudget
    closure_state: ClosureState
    refusal_required: bool
    refusal_category: Optional[RefusalCategory]
    created_at: Optional[int] = field(default=None)

    def __post_init__(self) -> None:
        computed_id = _deterministic_plan_id(
            self.trace_id, self.decision_state_id, self.action
        )
        if self.control_plan_id != computed_id:
            raise ControlPlanValidationError("control_plan_id is not deterministic.")
        if self.schema_version != SCHEMA_VERSION:
            raise ControlPlanValidationError("schema_version must match Phase 10.")
        if self.phase_marker != PhaseMarker.PHASE_10:
            raise ControlPlanValidationError("phase_marker must be PHASE_10.")
        if self.question_budget not in (0, 1):
            raise ControlPlanValidationError("question_budget must be 0 or 1.")
        if self.action == ControlAction.ASK_ONE_QUESTION and self.question_budget != 1:
            raise ControlPlanValidationError(
                "ASK_ONE_QUESTION action requires question_budget == 1."
            )
        if (
            self.action != ControlAction.ASK_ONE_QUESTION
            and self.question_budget == 1
            and self.clarification_required is False
        ):
            raise ControlPlanValidationError(
                "question_budget of 1 implies clarification_required."
            )
        if self.action == ControlAction.ANSWER_ALLOWED and self.refusal_required:
            raise ControlPlanValidationError(
                "ANSWER_ALLOWED cannot coexist with refusal_required."
            )
        if (
            self.action == ControlAction.REFUSE
            and not self.refusal_required
            and self.action != ControlAction.ABORT_FAIL_CLOSED
        ):
            raise ControlPlanValidationError(
                "REFUSE action requires refusal_required unless aborting fail-closed."
            )
        if self.action == ControlAction.CLOSE and self.clarification_required:
            raise ControlPlanValidationError(
                "CLOSE action cannot require clarification."
            )
        if (
            self.closure_state == ClosureState.CLOSED
            and self.action == ControlAction.ASK_ONE_QUESTION
        ):
            raise ControlPlanValidationError(
                "closure_state CLOSED is incompatible with ASK_ONE_QUESTION."
            )
        if self.question_budget == 0 and self.question_class is not None:
            raise ControlPlanValidationError(
                "question_class must be None when question_budget is 0."
            )
        if self.refusal_required is False and self.refusal_category not in (
            None,
            RefusalCategory.NONE,
        ):
            raise ControlPlanValidationError(
                "refusal_category must be NONE when refusal is not required."
            )
        if self.refusal_required and (
            self.refusal_category is None or self.refusal_category == RefusalCategory.NONE
        ):
            raise ControlPlanValidationError(
                "refusal_required=True requires a non-NONE refusal_category."
            )


def build_control_plan(
    trace_id: str,
    decision_state_id: str,
    action: ControlAction,
    rigor_level: RigorLevel,
    friction_posture: FrictionPosture,
    clarification_required: bool,
    clarification_reason: ClarificationReason,
    question_budget: int,
    question_class: Optional[QuestionClass],
    confidence_signaling_level: ConfidenceSignalingLevel,
    unknown_disclosure_level: UnknownDisclosureLevel,
    initiative_allowed: bool,
    initiative_budget: InitiativeBudget,
    closure_state: ClosureState,
    refusal_required: bool,
    refusal_category: Optional[RefusalCategory],
    created_at: Optional[int] = None,
) -> ControlPlan:
    plan_id = _deterministic_plan_id(trace_id, decision_state_id, action)
    return ControlPlan(
        schema_version=SCHEMA_VERSION,
        phase_marker=PhaseMarker.PHASE_10,
        control_plan_id=plan_id,
        trace_id=trace_id,
        decision_state_id=decision_state_id,
        action=action,
        rigor_level=rigor_level,
        friction_posture=friction_posture,
        clarification_required=clarification_required,
        clarification_reason=clarification_reason,
        question_budget=question_budget,
        question_class=question_class,
        confidence_signaling_level=confidence_signaling_level,
        unknown_disclosure_level=unknown_disclosure_level,
        initiative_allowed=initiative_allowed,
        initiative_budget=initiative_budget,
        closure_state=closure_state,
        refusal_required=refusal_required,
        refusal_category=refusal_category,
        created_at=created_at,
    )
