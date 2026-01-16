"""Phase 11 — Step 8: Output assembly and cross-step validation.

Runs Phase 11 selectors in canonical order, resolves OutputAction, builds a
validated OutputPlan, and fails closed on any contradiction. No text rendering,
no templates, no models.
"""

from typing import Optional

from backend.mci_backend.control_plan import (
    ClosureState,
    ControlAction,
    ControlPlan,
    FrictionPosture,
    RefusalCategory,
)
from backend.mci_backend.decision_state import DecisionState
from backend.mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ConfidenceSignalingLevel,
    ExpressionPosture,
    OutputAction,
    OutputPlan,
    RefusalExplanationMode,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
    VerbosityCap,
    build_output_plan,
    validate_output_plan,
    QuestionSpec,
    RefusalSpec,
    ClosureSpec,
)
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason
from backend.mci_backend.expression_assumption_surfacing import select_assumption_surfacing
from backend.mci_backend.expression_closure_rendering import select_closure_rendering_mode
from backend.mci_backend.expression_confidence_signaling import select_confidence_signaling
from backend.mci_backend.expression_posture import select_expression_posture
from backend.mci_backend.expression_refusal_explanation import select_refusal_explanation_mode
from backend.mci_backend.expression_rigor_disclosure import select_rigor_disclosure
from backend.mci_backend.expression_unknown_disclosure import select_unknown_disclosure


class OutputAssemblyError(Exception):
    """Raised when OutputPlan assembly fails."""


class OutputAssemblyInvariantViolation(OutputAssemblyError):
    """Raised for specific invariant violations during assembly."""


def _resolve_action(control_plan: ControlPlan) -> OutputAction:
    if control_plan.closure_state != ClosureState.OPEN:
        return OutputAction.CLOSE
    if control_plan.refusal_required:
        return OutputAction.REFUSE
    if control_plan.action == ControlAction.ASK_ONE_QUESTION:
        return OutputAction.ASK_ONE_QUESTION
    if control_plan.action == ControlAction.ANSWER_ALLOWED:
        return OutputAction.ANSWER
    raise OutputAssemblyInvariantViolation("Unsupported control action for OutputPlan assembly.")


def assemble_output_plan(
    user_text: str,
    decision_state: DecisionState,
    control_plan: ControlPlan,
) -> OutputPlan:
    """Canonical Phase 11 assembly. No rendering, deterministic, fail-closed."""
    if decision_state is None or control_plan is None:
        raise OutputAssemblyError("decision_state and control_plan are required.")

    try:
        posture = select_expression_posture(decision_state, control_plan)
        rigor_disclosure = select_rigor_disclosure(decision_state, control_plan, posture)
        confidence_signaling = select_confidence_signaling(
            decision_state, control_plan, posture, rigor_disclosure
        )
        unknown_disclosure = select_unknown_disclosure(
            decision_state, control_plan, posture, rigor_disclosure, confidence_signaling
        )
        assumption_surfacing = select_assumption_surfacing(
            decision_state,
            control_plan,
            posture,
            rigor_disclosure,
            confidence_signaling,
            unknown_disclosure,
        )
    except Exception as exc:  # noqa: BLE001
        raise OutputAssemblyError(f"Selector failed: {exc}") from exc

    refusal_explanation_mode: Optional[RefusalExplanationMode] = None
    if control_plan.refusal_required:
        try:
            refusal_explanation_mode = select_refusal_explanation_mode(
                decision_state,
                control_plan,
                posture,
                rigor_disclosure,
                confidence_signaling,
                unknown_disclosure,
                assumption_surfacing,
            )
        except Exception as exc:  # noqa: BLE001
            raise OutputAssemblyError(f"Refusal explanation selection failed: {exc}") from exc
    else:
        refusal_explanation_mode = RefusalExplanationMode.BRIEF_BOUNDARY

    closure_rendering_mode: Optional[ClosureRenderingMode] = None
    if control_plan.closure_state != ClosureState.OPEN:
        try:
            closure_rendering_mode = select_closure_rendering_mode(
                decision_state,
                control_plan,
                posture,
                rigor_disclosure,
                confidence_signaling,
                unknown_disclosure,
                assumption_surfacing,
                refusal_explanation_mode,
            )
        except Exception as exc:  # noqa: BLE001
            raise OutputAssemblyError(f"Closure rendering selection failed: {exc}") from exc
    else:
        closure_rendering_mode = ClosureRenderingMode.CONFIRM_CLOSURE

    action = _resolve_action(control_plan)

    question_spec: Optional[QuestionSpec] = None
    refusal_spec: Optional[RefusalSpec] = None
    closure_spec: Optional[ClosureSpec] = None
    verbosity_cap = VerbosityCap.NORMAL

    # Action-specific assembly and cross-step invariants
    if action == OutputAction.CLOSE:
        if control_plan.closure_state == ClosureState.OPEN:
            raise OutputAssemblyInvariantViolation("CLOSE action requires non-OPEN closure_state.")
        if control_plan.question_budget != 0:
            raise OutputAssemblyInvariantViolation("CLOSE action forbids questions.")
        if control_plan.clarification_required:
            raise OutputAssemblyInvariantViolation("CLOSE action forbids clarification.")
        if control_plan.refusal_required:
            raise OutputAssemblyInvariantViolation("CLOSE action cannot coexist with refusal_required.")
        if closure_rendering_mode is None:
            raise OutputAssemblyInvariantViolation("Closure rendering mode is required for CLOSE action.")
        closure_spec = ClosureSpec(
            closure_state=control_plan.closure_state, rendering_mode=closure_rendering_mode
        )
        refusal_spec = None
        question_spec = None
        if verbosity_cap not in {VerbosityCap.TERSE, VerbosityCap.NORMAL}:
            verbosity_cap = VerbosityCap.NORMAL

    elif action == OutputAction.REFUSE:
        if not control_plan.refusal_required:
            raise OutputAssemblyInvariantViolation("REFUSE action requires refusal_required=True.")
        if control_plan.refusal_category is None or control_plan.refusal_category == RefusalCategory.NONE:
            raise OutputAssemblyInvariantViolation("REFUSE action requires non-NONE refusal_category.")
        if control_plan.closure_state != ClosureState.OPEN:
            raise OutputAssemblyInvariantViolation("REFUSE action requires closure_state OPEN.")
        if control_plan.question_budget != 0:
            raise OutputAssemblyInvariantViolation("REFUSE action forbids question budget.")
        if refusal_explanation_mode is None:
            raise OutputAssemblyInvariantViolation("Refusal explanation mode is required for REFUSE action.")
        refusal_spec = RefusalSpec(
            refusal_category=control_plan.refusal_category,
            explanation_mode=refusal_explanation_mode,
        )
        question_spec = None
        closure_spec = None
        if verbosity_cap == VerbosityCap.DETAILED:
            verbosity_cap = VerbosityCap.NORMAL

    elif action == OutputAction.ASK_ONE_QUESTION:
        if control_plan.closure_state != ClosureState.OPEN:
            raise OutputAssemblyInvariantViolation("ASK_ONE_QUESTION requires closure_state OPEN.")
        if control_plan.refusal_required:
            raise OutputAssemblyInvariantViolation("ASK_ONE_QUESTION incompatible with refusal_required.")
        if control_plan.question_budget != 1:
            raise OutputAssemblyInvariantViolation("ASK_ONE_QUESTION requires question_budget==1.")
        if control_plan.question_class is None:
            raise OutputAssemblyInvariantViolation("ASK_ONE_QUESTION requires question_class.")
        priority_reason = QuestionPriorityReason.UNKNOWN_CONTEXT
        question_spec = QuestionSpec(
            question_class=control_plan.question_class, priority_reason=priority_reason
        )
        refusal_spec = None
        closure_spec = None
        if verbosity_cap == VerbosityCap.DETAILED:
            verbosity_cap = VerbosityCap.NORMAL
        if rigor_disclosure == RigorDisclosureLevel.ENFORCED:
            raise OutputAssemblyInvariantViolation("ASK_ONE_QUESTION forbids ENFORCED rigor_disclosure.")

    elif action == OutputAction.ANSWER:
        if control_plan.closure_state != ClosureState.OPEN:
            raise OutputAssemblyInvariantViolation("ANSWER requires closure_state OPEN.")
        if control_plan.refusal_required:
            raise OutputAssemblyInvariantViolation("ANSWER incompatible with refusal_required.")
        if control_plan.question_budget != 0:
            raise OutputAssemblyInvariantViolation("ANSWER forbids question budget.")
        if control_plan.friction_posture == FrictionPosture.STOP:
            raise OutputAssemblyInvariantViolation("ANSWER cannot proceed under STOP friction.")
        question_spec = None
        refusal_spec = None
        closure_spec = None
    else:
        raise OutputAssemblyInvariantViolation("Unsupported OutputAction.")

    try:
        plan = build_output_plan(
            trace_id=decision_state.trace_id,
            decision_state_id=decision_state.decision_id,
            control_plan_id=control_plan.control_plan_id,
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
    except Exception as exc:  # noqa: BLE001
        raise OutputAssemblyError(f"Failed to build or validate OutputPlan: {exc}") from exc
