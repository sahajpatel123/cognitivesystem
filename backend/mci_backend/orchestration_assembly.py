"""Phase 10 — Step 8: ControlPlan assembly and cross-step validation.

Runs Steps 1–7 in canonical order, applies override rules, and builds a final
ControlPlan or fails closed with a typed error.
"""

from dataclasses import dataclass

from mci_backend.control_plan import (
    ClarificationReason,
    ClosureState,
    ConfidenceSignalingLevel,
    ControlAction,
    ControlPlan,
    ControlPlanValidationError,
    FrictionPosture,
    InitiativeBudget,
    QuestionClass,
    RefusalCategory,
    UnknownDisclosureLevel,
    build_control_plan,
    PhaseMarker,
    SCHEMA_VERSION,
)
from mci_backend.decision_state import DecisionState
from mci_backend.orchestration_clarification_trigger import ClarificationDecision, decide_clarification
from mci_backend.orchestration_closure import ClosureDecision, detect_closure
from mci_backend.orchestration_friction import select_friction
from mci_backend.orchestration_initiative import InitiativeDecision, select_initiative
from mci_backend.orchestration_question_compression import QuestionSelection, select_single_question
from mci_backend.orchestration_refusal import RefusalDecision, decide_refusal
from mci_backend.orchestration_rigor import select_rigor


class OrchestrationAssemblyError(ValueError):
    """Raised when assembly or cross-step validation fails."""


@dataclass(frozen=True)
class AssemblyResult:
    control_plan: ControlPlan


def _apply_overrides(
    closure_decision: ClosureDecision,
    clarification_decision: ClarificationDecision,
    question_selection: QuestionSelection | None,
    initiative_decision: InitiativeDecision,
    refusal_decision: RefusalDecision,
) -> tuple[
    ClosureDecision,
    ClarificationDecision,
    QuestionSelection | None,
    InitiativeDecision,
    RefusalDecision,
]:
    closure_state = closure_decision.closure_state
    clarification_required = clarification_decision.clarification_required
    question_budget = clarification_decision.question_budget
    initiative_budget = initiative_decision.initiative_budget
    warning_budget = initiative_decision.warning_budget

    # Rule 1 — Closure cancels further asks/interventions
    if closure_state in {ClosureState.CLOSED, ClosureState.USER_TERMINATED}:
        clarification_decision = ClarificationDecision(
            clarification_required=False,
            clarification_reason=ClarificationReason.UNKNOWN,
            question_budget=0,
        )
        question_selection = None
        initiative_decision = InitiativeDecision(
            initiative_budget=InitiativeBudget.NONE,
            warning_budget=0,
        )
        return (
            closure_decision,
            clarification_decision,
            question_selection,
            initiative_decision,
            refusal_decision,
        )

    # Rule 2 — Clarification consumes intervention slot
    if clarification_required:
        initiative_decision = InitiativeDecision(
            initiative_budget=initiative_budget if initiative_budget != InitiativeBudget.NONE else InitiativeBudget.ONCE,
            warning_budget=0,
        )

    # Rule 4 — Question selection consistency (handled again later)
    if question_budget == 0:
        question_selection = None

    return (
        closure_decision,
        clarification_decision,
        question_selection,
        initiative_decision,
        refusal_decision,
    )


def _enforce_cross_step_invariants(
    friction_posture: FrictionPosture,
    clarification_decision: ClarificationDecision,
    question_selection: QuestionSelection | None,
    initiative_decision: InitiativeDecision,
    closure_decision: ClosureDecision,
    refusal_decision: RefusalDecision,
) -> None:
    # Rule 3 — Refusal overrides answer permission (checked when choosing action)
    # Rule 4 — Question selection consistency
    if clarification_decision.question_budget == 1 and question_selection is None:
        raise OrchestrationAssemblyError(
            "question_budget==1 requires a question_selection."
        )
    if clarification_decision.question_budget == 0 and question_selection is not None:
        raise OrchestrationAssemblyError(
            "question_budget==0 requires question_selection to be None."
        )

    # Rule 5 — STOP friction consistency
    if friction_posture == FrictionPosture.STOP:
        if not (
            refusal_decision.refusal_required
            or closure_decision.closure_state != ClosureState.OPEN
            or clarification_decision.clarification_required
        ):
            raise OrchestrationAssemblyError(
                "STOP friction requires refusal, closure, or clarification to be active."
            )

    # Initiative invariant after clarification override
    if clarification_decision.clarification_required and initiative_decision.warning_budget != 0:
        raise OrchestrationAssemblyError(
            "Clarification consumes intervention slot; warning_budget must be 0."
        )

    # Refusal invariant
    if refusal_decision.refusal_required and refusal_decision.refusal_category == RefusalCategory.NONE:
        raise OrchestrationAssemblyError(
            "Refusal requires non-NONE refusal_category."
        )
    if not refusal_decision.refusal_required and refusal_decision.refusal_category != RefusalCategory.NONE:
        raise OrchestrationAssemblyError(
            "Non-refusal requires refusal_category to be NONE."
        )


def _choose_action(
    clarification_decision: ClarificationDecision,
    closure_decision: ClosureDecision,
    refusal_decision: RefusalDecision,
) -> ControlAction:
    if closure_decision.closure_state in {ClosureState.CLOSED, ClosureState.USER_TERMINATED}:
        return ControlAction.CLOSE
    if refusal_decision.refusal_required:
        return ControlAction.REFUSE
    if clarification_decision.clarification_required:
        return ControlAction.ASK_ONE_QUESTION
    return ControlAction.ANSWER_ALLOWED


def assemble_control_plan(user_text: str, decision_state: DecisionState) -> ControlPlan:
    """Run Steps 1–7 in canonical order, apply overrides, and build ControlPlan."""
    if decision_state is None:
        raise OrchestrationAssemblyError("DecisionState is required.")

    # 1) Rigor
    rigor_level = select_rigor(decision_state)
    # 2) Friction
    friction_posture = select_friction(decision_state, rigor_level)
    # 3) Clarification trigger
    clarification_decision = decide_clarification(decision_state, rigor_level, friction_posture)
    # 4) Question selection if needed
    question_selection = (
        select_single_question(
            decision_state,
            clarification_decision.clarification_reason,
            rigor_level,
            friction_posture,
            clarification_decision.clarification_required,
            clarification_decision.question_budget,
        )
        if clarification_decision.question_budget == 1
        else None
    )
    # 5) Initiative discipline
    initiative_decision = select_initiative(
        decision_state,
        rigor_level,
        friction_posture,
        clarification_decision.clarification_required,
        clarification_decision.question_budget,
    )
    # 6) Closure detection
    closure_decision = detect_closure(
        user_text,
        decision_state,
        rigor_level,
        friction_posture,
        clarification_decision.clarification_required,
        clarification_decision.question_budget,
    )
    # 7) Refusal triggers
    refusal_decision = decide_refusal(
        decision_state,
        rigor_level,
        friction_posture,
        clarification_decision.clarification_required,
        clarification_decision.question_budget,
        closure_decision.closure_state,
    )

    # Apply overrides
    (
        closure_decision,
        clarification_decision,
        question_selection,
        initiative_decision,
        refusal_decision,
    ) = _apply_overrides(
        closure_decision,
        clarification_decision,
        question_selection,
        initiative_decision,
        refusal_decision,
    )

    # Cross-step invariants
    _enforce_cross_step_invariants(
        friction_posture,
        clarification_decision,
        question_selection,
        initiative_decision,
        closure_decision,
        refusal_decision,
    )

    action = _choose_action(
        clarification_decision,
        closure_decision,
        refusal_decision,
    )

    initiative_allowed = initiative_decision.initiative_budget != InitiativeBudget.NONE

    try:
        plan = build_control_plan(
            trace_id=decision_state.trace_id,
            decision_state_id=decision_state.decision_id,
            action=action,
            rigor_level=rigor_level,
            friction_posture=friction_posture,
            clarification_required=clarification_decision.clarification_required,
            clarification_reason=clarification_decision.clarification_reason,
            question_budget=clarification_decision.question_budget,
            question_class=question_selection.question_class if question_selection else None,
            confidence_signaling_level=ConfidenceSignalingLevel.MINIMAL,
            unknown_disclosure_level=UnknownDisclosureLevel.NONE,
            initiative_allowed=initiative_allowed,
            initiative_budget=initiative_decision.initiative_budget,
            closure_state=closure_decision.closure_state,
            refusal_required=refusal_decision.refusal_required,
            refusal_category=refusal_decision.refusal_category,
        )
    except ControlPlanValidationError as exc:
        raise OrchestrationAssemblyError(f"ControlPlan validation failed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise OrchestrationAssemblyError(f"Failed to build ControlPlan: {exc}") from exc

    return plan
