from __future__ import annotations

from typing import Any, Dict, Optional

from backend.mci_backend.control_plan import ControlPlan
from backend.mci_backend.decision_state import DecisionState, RiskAssessment
from backend.mci_backend.model_contract import ModelInvocationResult
from backend.mci_backend.output_plan import OutputPlan


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.name if hasattr(value, "name") else str(value)


def _normalize_risk_assessments(risks: tuple[RiskAssessment, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((ra.domain.name, ra.confidence.name) for ra in risks))


def signature_decision_state(state: DecisionState) -> Dict[str, Any]:
    return {
        "phase": _enum_value(state.phase_marker),
        "schema": getattr(state, "schema_version", None),
        "proximity_state": _enum_value(state.proximity_state),
        "proximity_uncertainty": bool(state.proximity_uncertainty),
        "reversibility_class": _enum_value(state.reversibility_class),
        "consequence_horizon": _enum_value(state.consequence_horizon),
        "responsibility_scope": _enum_value(state.responsibility_scope),
        "risk_domains": _normalize_risk_assessments(tuple(state.risk_domains)),
        "outcome_classes": tuple(sorted(_enum_value(o) for o in state.outcome_classes)),
        "explicit_unknown_zone": tuple(sorted(_enum_value(u) for u in getattr(state, "explicit_unknown_zone", ()))),
    }


def signature_control_plan(plan: ControlPlan) -> Dict[str, Any]:
    return {
        "phase": _enum_value(getattr(plan, "phase_marker", None)),
        "schema": getattr(plan, "schema_version", None),
        "action": _enum_value(plan.action),
        "rigor_level": _enum_value(getattr(plan, "rigor_level", None)),
        "friction_posture": _enum_value(getattr(plan, "friction_posture", None)),
        "clarification_required": bool(getattr(plan, "clarification_required", False)),
        "clarification_reason": _enum_value(getattr(plan, "clarification_reason", None)),
        "question_budget": getattr(plan, "question_budget", None),
        "question_class": _enum_value(getattr(plan, "question_class", None)),
        "initiative_allowed": bool(getattr(plan, "initiative_allowed", False)),
        "initiative_budget": _enum_value(getattr(plan, "initiative_budget", None)),
        "closure_state": _enum_value(getattr(plan, "closure_state", None)),
        "refusal_required": bool(getattr(plan, "refusal_required", False)),
        "refusal_category": _enum_value(getattr(plan, "refusal_category", None)),
        "confidence_signaling_level": _enum_value(getattr(plan, "confidence_signaling_level", None)),
        "unknown_disclosure_level": _enum_value(getattr(plan, "unknown_disclosure_level", None)),
    }


def _signature_question_spec(spec: Any) -> Optional[Dict[str, Any]]:
    if spec is None:
        return None
    return {
        "question_class": _enum_value(getattr(spec, "question_class", None)),
        "priority_reason": _enum_value(getattr(spec, "priority_reason", None)),
    }


def _signature_refusal_spec(spec: Any) -> Optional[Dict[str, Any]]:
    if spec is None:
        return None
    return {
        "refusal_category": _enum_value(getattr(spec, "refusal_category", None)),
        "explanation_mode": _enum_value(getattr(spec, "explanation_mode", None)),
    }


def _signature_closure_spec(spec: Any) -> Optional[Dict[str, Any]]:
    if spec is None:
        return None
    return {
        "closure_state": _enum_value(getattr(spec, "closure_state", None)),
        "rendering_mode": _enum_value(getattr(spec, "rendering_mode", None)),
    }


def signature_output_plan(plan: OutputPlan) -> Dict[str, Any]:
    return {
        "phase": _enum_value(getattr(plan, "phase_marker", None)),
        "schema": getattr(plan, "schema_version", None),
        "action": _enum_value(plan.action),
        "posture": _enum_value(getattr(plan, "posture", None)),
        "rigor_disclosure": _enum_value(getattr(plan, "rigor_disclosure", None)),
        "confidence_signaling": _enum_value(getattr(plan, "confidence_signaling", None)),
        "assumption_surfacing": _enum_value(getattr(plan, "assumption_surfacing", None)),
        "unknown_disclosure": _enum_value(getattr(plan, "unknown_disclosure", None)),
        "verbosity_cap": _enum_value(getattr(plan, "verbosity_cap", None)),
        "question_spec": _signature_question_spec(getattr(plan, "question_spec", None)),
        "refusal_spec": _signature_refusal_spec(getattr(plan, "refusal_spec", None)),
        "closure_spec": _signature_closure_spec(getattr(plan, "closure_spec", None)),
    }


def signature_model_result(result: ModelInvocationResult) -> Dict[str, Any]:
    failure_type = None
    failure_reason = None
    if result.failure:
        failure_type = _enum_value(result.failure.failure_type)
        failure_reason = getattr(result.failure, "reason_code", None)
    has_json = result.output_json is not None
    has_text = result.output_text is not None and result.output_text != ""
    inferred_action = None
    if has_json and "question" in result.output_json:
        inferred_action = "ASK_ONE_QUESTION"
    elif has_json:
        inferred_action = "JSON"
    elif result.failure:
        inferred_action = "FAILURE"
    else:
        inferred_action = "TEXT"

    json_keys = tuple(sorted(result.output_json.keys())) if has_json else None

    return {
        "ok": bool(result.ok),
        "failure_type": failure_type,
        "failure_reason": failure_reason,
        "output_kind": "json" if has_json else ("text" if has_text else None),
        "json_keys": json_keys,
        "inferred_action": inferred_action,
    }
