import pathlib
import sys

import pytest

# Ensure repository root on path for mci_backend imports when running directly.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.mci_backend.control_plan import (
    ClarificationReason,
    ClosureState,
    ControlAction,
    ControlPlanValidationError,
    ConfidenceSignalingLevel,
    FrictionPosture,
    InitiativeBudget,
    QuestionClass,
    RefusalCategory,
    RigorLevel,
    UnknownDisclosureLevel,
    build_control_plan,
)
from backend.mci_backend.decision_state import (
    ConfidenceLevel,
    ConsequenceHorizon,
    DecisionState,
    OutcomeClass,
    PhaseMarker as DecisionPhaseMarker,
    ProximityState,
    ReversibilityClass,
    ResponsibilityScope,
    RiskAssessment,
    RiskDomain,
    UnknownSource,
    PHASE_9_SCHEMA_VERSION,
)
from backend.mci_backend.output_plan import (
    ExpressionPosture,
    OutputAction,
    UnknownDisclosureMode,
    ConfidenceSignalingLevel as OutputConfidenceSignalingLevel,
    ClosureRenderingMode,
)
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason
from backend.mci_backend.expression_assembly import (
    OutputAssemblyError,
    OutputAssemblyInvariantViolation,
    assemble_output_plan,
)

# Phase 9 OutcomeClass lacks UNKNOWN alias; provide local alias for tests only.
if not hasattr(OutcomeClass, "UNKNOWN"):
    OutcomeClass.UNKNOWN = OutcomeClass.UNKNOWN_OUTCOME_CLASS  # type: ignore[attr-defined]


def _make_decision_state(
    *,
    proximity_state: ProximityState = ProximityState.MEDIUM,
    risk_domains: tuple[RiskAssessment, ...] | None = None,
    reversibility_class: ReversibilityClass = ReversibilityClass.COSTLY_REVERSIBLE,
    consequence_horizon: ConsequenceHorizon = ConsequenceHorizon.MEDIUM_HORIZON,
    responsibility_scope: ResponsibilityScope = ResponsibilityScope.SELF_ONLY,
    explicit_unknown_zone: tuple[UnknownSource, ...] = (),
    decision_id: str = "dec-1",
    trace_id: str = "trace-1",
) -> DecisionState:
    risks = risk_domains or (RiskAssessment(RiskDomain.FINANCIAL, ConfidenceLevel.LOW),)
    return DecisionState(
        decision_id=decision_id,
        trace_id=trace_id,
        phase_marker=DecisionPhaseMarker.PHASE_9,
        schema_version=PHASE_9_SCHEMA_VERSION,
        proximity_state=proximity_state,
        proximity_uncertainty=False,
        risk_domains=risks,
        reversibility_class=reversibility_class,
        consequence_horizon=consequence_horizon,
        responsibility_scope=responsibility_scope,
        outcome_classes=(OutcomeClass.FINANCIAL_OUTCOME,),
        explicit_unknown_zone=explicit_unknown_zone,
    )


def _make_control_plan(
    *,
    action: ControlAction = ControlAction.ANSWER_ALLOWED,
    rigor_level: RigorLevel = RigorLevel.MINIMAL,
    friction_posture: FrictionPosture = FrictionPosture.NONE,
    clarification_required: bool = False,
    clarification_reason: ClarificationReason = ClarificationReason.UNKNOWN,
    question_budget: int = 0,
    question_class: QuestionClass | None = None,
    confidence_signaling_level: ConfidenceSignalingLevel = ConfidenceSignalingLevel.MINIMAL,
    unknown_disclosure_level=UnknownDisclosureLevel.NONE,
    initiative_allowed: bool = False,
    initiative_budget: InitiativeBudget = InitiativeBudget.NONE,
    closure_state: ClosureState = ClosureState.OPEN,
    refusal_required: bool = False,
    refusal_category: RefusalCategory | None = RefusalCategory.NONE,
    decision_state_id: str = "dec-1",
    trace_id: str = "trace-1",
):
    return build_control_plan(
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
    )


# -------------------------------
# CATEGORY A: ACTION DOMINANCE
# -------------------------------


def test_action_dominance_closure_wins():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ANSWER_ALLOWED,
        closure_state=ClosureState.CLOSED,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.CLOSE
    assert plan.closure_spec is not None
    assert plan.question_spec is None
    assert plan.refusal_spec is None


def test_action_dominance_refusal_wins_over_answer():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.REFUSE,
        refusal_required=True,
        refusal_category=RefusalCategory.RISK_REFUSAL,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.REFUSE
    assert plan.refusal_spec is not None
    assert plan.question_spec is None
    assert plan.closure_spec is None


def test_action_dominance_ask_path():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ASK_ONE_QUESTION,
        clarification_required=True,
        question_budget=1,
        question_class=QuestionClass.INFORMATIONAL,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.ASK_ONE_QUESTION
    assert plan.question_spec is not None
    assert plan.refusal_spec is None
    assert plan.closure_spec is None


def test_action_dominance_answer_allowed():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ANSWER_ALLOWED,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.ANSWER
    assert plan.question_spec is None
    assert plan.refusal_spec is None
    assert plan.closure_spec is None


# -------------------------------
# CATEGORY B: FAIL-CLOSED CONTRADICTIONS
# -------------------------------


def test_fail_closed_stop_friction_blocks_answer():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ANSWER_ALLOWED,
        friction_posture=FrictionPosture.STOP,
        question_budget=0,
    )
    with pytest.raises(OutputAssemblyInvariantViolation):
        assemble_output_plan("user text", ds, cp)


def test_fail_closed_ask_with_zero_budget():
    with pytest.raises(ControlPlanValidationError):
        _make_control_plan(
            action=ControlAction.ASK_ONE_QUESTION,
            clarification_required=True,
            question_budget=0,
            question_class=QuestionClass.INFORMATIONAL,
        )


def test_fail_closed_refusal_without_category():
    with pytest.raises(ControlPlanValidationError):
        _make_control_plan(
            action=ControlAction.REFUSE,
            refusal_required=True,
            refusal_category=RefusalCategory.NONE,
            question_budget=0,
        )


def test_fail_closed_closure_with_question_budget():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ANSWER_ALLOWED,
        closure_state=ClosureState.CLOSED,
        clarification_required=True,
        question_budget=1,
    )
    with pytest.raises(OutputAssemblyError):
        assemble_output_plan("user text", ds, cp)


def test_fail_closed_missing_closure_rendering(monkeypatch):
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.CLOSE,
        closure_state=ClosureState.CLOSING,
        question_budget=0,
    )
    import backend.mci_backend.expression_assembly as assembly_mod

    def _bad_selector(*args, **kwargs):
        return None

    monkeypatch.setattr(assembly_mod, "select_closure_rendering_mode", _bad_selector)
    with pytest.raises(OutputAssemblyInvariantViolation):
        assemble_output_plan("user text", ds, cp)


# -------------------------------
# CATEGORY C: HONESTY / UNKNOWN DISCLOSURE
# -------------------------------


def test_unknown_zone_forbids_unknown_disclosure_none():
    ds = _make_decision_state(
        explicit_unknown_zone=(UnknownSource.PROXIMITY,),
    )
    cp = _make_control_plan(
        action=ControlAction.ANSWER_ALLOWED,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.unknown_disclosure != UnknownDisclosureMode.NONE


def test_high_stakes_with_unknowns_escalates_confidence():
    ds = _make_decision_state(
        risk_domains=(RiskAssessment(RiskDomain.MEDICAL_BIOLOGICAL, ConfidenceLevel.HIGH),),
        explicit_unknown_zone=(UnknownSource.RISK_DOMAINS,),
        responsibility_scope=ResponsibilityScope.THIRD_PARTY,
    )
    cp = _make_control_plan(
        action=ControlAction.ANSWER_ALLOWED,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.confidence_signaling != OutputConfidenceSignalingLevel.MINIMAL


# -------------------------------
# CATEGORY D: POSTURE SAFETY GUARANTEES
# -------------------------------


def test_refusal_requires_constrained_posture():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.REFUSE,
        refusal_required=True,
        refusal_category=RefusalCategory.RISK_REFUSAL,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.REFUSE
    assert plan.posture == ExpressionPosture.CONSTRAINED


def test_stop_friction_enforces_strong_posture_and_disclosures():
    ds = _make_decision_state(
        explicit_unknown_zone=(UnknownSource.PROXIMITY,),
    )
    cp = _make_control_plan(
        action=ControlAction.REFUSE,
        friction_posture=FrictionPosture.STOP,
        refusal_required=True,
        refusal_category=RefusalCategory.RISK_REFUSAL,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.posture == ExpressionPosture.CONSTRAINED
    assert plan.unknown_disclosure == UnknownDisclosureMode.EXPLICIT


# -------------------------------
# CATEGORY E: SINGLE-QUESTION INVARIANTS
# -------------------------------


def test_ask_one_has_single_question_spec():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ASK_ONE_QUESTION,
        clarification_required=True,
        question_budget=1,
        question_class=QuestionClass.INFORMATIONAL,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.ASK_ONE_QUESTION
    assert plan.question_spec is not None
    assert plan.question_spec.question_class == QuestionClass.INFORMATIONAL
    assert plan.question_spec.priority_reason == QuestionPriorityReason.UNKNOWN_CONTEXT


def test_ask_one_forbids_enforced_rigor():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.ASK_ONE_QUESTION,
        clarification_required=True,
        question_budget=1,
        question_class=QuestionClass.INFORMATIONAL,
        rigor_level=RigorLevel.ENFORCED,
    )
    with pytest.raises((OutputAssemblyInvariantViolation, OutputAssemblyError)):
        assemble_output_plan("user text", ds, cp)


# -------------------------------
# CATEGORY F: CLOSURE DISCIPLINE
# -------------------------------


def test_user_terminated_closure_silence():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.CLOSE,
        closure_state=ClosureState.USER_TERMINATED,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.CLOSE
    assert plan.closure_spec is not None
    assert plan.closure_spec.rendering_mode == ClosureRenderingMode.SILENCE
    assert plan.refusal_spec is None
    assert plan.question_spec is None


def test_closed_forbids_summary():
    ds = _make_decision_state()
    cp = _make_control_plan(
        action=ControlAction.CLOSE,
        closure_state=ClosureState.CLOSED,
        question_budget=0,
    )
    plan = assemble_output_plan("user text", ds, cp)
    assert plan.action == OutputAction.CLOSE
    assert plan.closure_spec is not None
    assert plan.closure_spec.rendering_mode in {
        ClosureRenderingMode.SILENCE,
        ClosureRenderingMode.CONFIRM_CLOSURE,
    }
