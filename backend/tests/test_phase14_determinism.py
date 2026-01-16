from __future__ import annotations

import json
from typing import Any, Dict, Tuple

import pytest

import backend.mci_backend.governed_response_runtime as grr
from backend.tests._phase14_determinism_signatures import (
    signature_control_plan,
    signature_decision_state,
    signature_model_result,
    signature_output_plan,
)
from backend.tests._phase14_fake_llm import Phase14FakeLLM
from backend.mci_backend.decision_state import OutcomeClass
from backend.mci_backend.expression_assembly import assemble_output_plan
from backend.mci_backend.model_contract import ModelInvocationResult, build_request_id
from backend.mci_backend.model_invocation_pipeline import invoke_model_for_output_plan
from backend.mci_backend.model_prompt_builder import build_model_invocation_request
from backend.mci_backend.model_candidate_validation import validate_candidate_output
from backend.mci_backend.orchestration_assembly import assemble_control_plan
from backend.mci_backend.decision_assembly import assemble_decision_state
from backend.mci_backend.output_plan import OutputAction


# Ensure compatibility for locked Phase 9 enum alias
if not hasattr(OutcomeClass, "UNKNOWN"):
    setattr(OutcomeClass, "UNKNOWN", OutcomeClass.UNKNOWN_OUTCOME_CLASS)  # type: ignore[attr-defined]


def _deterministic_ids(user_text: str) -> Tuple[str, str]:
    trace_id = grr._deterministic_trace_id(user_text)  # type: ignore[attr-defined]
    decision_id = grr._deterministic_decision_id(user_text)  # type: ignore[attr-defined]
    return trace_id, decision_id


def _assemble_all(user_text: str):
    trace_id, decision_id = _deterministic_ids(user_text)
    ds = assemble_decision_state(decision_id=decision_id, trace_id=trace_id, message=user_text)
    cp = assemble_control_plan(user_text, ds)
    op = assemble_output_plan(user_text, ds, cp)
    return ds, cp, op


def _fake_payload_for_action(op_action: OutputAction, variant: int = 0) -> str:
    if op_action == OutputAction.ASK_ONE_QUESTION:
        return json.dumps(
            {
                "question": f"What is your main concern? ({variant})?",
                "question_class": "INFORMATIONAL",
                "priority_reason": "UNKNOWN_CONTEXT",
            }
        )
    if op_action == OutputAction.REFUSE:
        return "Refusing due to safety constraints." if variant == 0 else "Cannot proceed for safety."
    if op_action == OutputAction.CLOSE:
        return "Session closed." if variant == 0 else "Closing now."
    return f"Bounded answer variant {variant}."


def _run_pipeline(user_text: str, variant: int = 0):
    ds, cp, op = _assemble_all(user_text)
    payload = _fake_payload_for_action(op.action, variant)
    llm = Phase14FakeLLM([payload])
    res = invoke_model_for_output_plan(
        user_text=user_text,
        decision_state=ds,
        control_plan=cp,
        output_plan=op,
        llm_client=llm,
    )
    return ds, cp, op, res


def _assert_no_leakage(result: ModelInvocationResult):
    banned = ["trace_id", "decision_state", "control_plan", "output_plan", "PHASE_"]
    text = result.output_text or ""
    if result.output_json:
        payload = json.dumps(result.output_json)
        assert all(token not in payload for token in banned)
    assert all(token.lower() not in text.lower() for token in banned)


# -------------------------
# CATEGORY A: DecisionState
# -------------------------


def test_decision_state_determinism():
    user_text = "Is it safe to boil water twice?"
    signatures = {json.dumps(signature_decision_state(_assemble_all(user_text)[0]), sort_keys=True) for _ in range(10)}
    assert len(signatures) == 1


# -------------------------
# CATEGORY B: ControlPlan
# -------------------------


def test_control_plan_determinism():
    user_text = "Should I invest in index funds?"
    signatures = {
        json.dumps(signature_control_plan(_assemble_all(user_text)[1]), sort_keys=True) for _ in range(10)
    }
    assert len(signatures) == 1


# -------------------------
# CATEGORY C: OutputPlan
# -------------------------


def test_output_plan_determinism():
    user_text = "Close the session politely."
    signatures = {json.dumps(signature_output_plan(_assemble_all(user_text)[2]), sort_keys=True) for _ in range(10)}
    assert len(signatures) == 1


# ----------------------------------------------------
# CATEGORY D: Governed response determinism (behavior)
# ----------------------------------------------------


def test_governed_response_action_and_discipline_stable():
    user_text = "Please answer briefly."
    results = []
    for variant in range(2):
        _, _, _, res = _run_pipeline(user_text, variant)
        assert res.ok
        results.append(signature_model_result(res))
        _assert_no_leakage(res)
    assert len(set(json.dumps(r, sort_keys=True) for r in results)) == 1


def test_governed_response_question_shape_stable():
    user_text = "Ask me a safety question."
    results = []
    for _ in range(5):
        _, _, op = _assemble_all(user_text)
        llm = Phase14FakeLLM([_fake_payload_for_action(op.action, 0)])
        res = invoke_model_for_output_plan(
            user_text=user_text,
            decision_state=_assemble_all(user_text)[0],
            control_plan=_assemble_all(user_text)[1],
            output_plan=op,
            llm_client=llm,
        )
        assert res.ok
        sig = signature_model_result(res)
        assert sig["output_kind"] == "json"
        assert sig["json_keys"] == ("priority_reason", "question", "question_class")
        results.append(json.dumps(sig, sort_keys=True))
    assert len(set(results)) == 1


# -----------------------------------
# CATEGORY E: Drift golden snapshots
# -----------------------------------


_PROMPTS = [
    "Say hello politely.",
    "Give me a quick budget tip for $500 emergency fund.",
    "Should I sell my stocks after a dip?",
    "Explain small-claims court filing steps.",
    "What to do for mild fever at home?",
    "Is it safe to mix bleach and vinegar?",
    "Should I change my friend's medication dose?",
    "How to report a data breach at a bank?",
    "Should we evacuate during wildfire smoke?",
    "Plan for an irreversible surgery decision.",
    "How should a city plan for 50-year flood risk?",
    "I think I'm being followed right now, what should I do?",
    "Should I lever up using options on my portfolio?",
    "How to influence public health policy quickly?",
    "Can I access my coworker's HR file?",
]


# Snapshots generated via canonical pipeline with deterministic fake LLM payloads.
_GOLDEN_SNAPSHOTS: Dict[str, Dict[str, object]] = {
    "Say hello politely.": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("UNKNOWN_OUTCOME_CLASS",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "Give me a quick budget tip for $500 emergency fund.": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("FINANCIAL_OUTCOME",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("FINANCIAL", "HIGH"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "Should I sell my stocks after a dip?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("FINANCIAL_OUTCOME",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("FINANCIAL", "MEDIUM"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "Explain small-claims court filing steps.": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("ETHICAL_MORAL_OUTCOME", "UNKNOWN_OUTCOME_CLASS"),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "SHARED",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "What to do for mild fever at home?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("UNKNOWN_OUTCOME_CLASS",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "Is it safe to mix bleach and vinegar?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("UNKNOWN_OUTCOME_CLASS",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "Should I change my friend's medication dose?": {
        "control_plan": {
            "action": "CLOSE",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "USER_TERMINATED",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "STRUCTURED",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("ETHICAL_MORAL_OUTCOME", "MEDICAL_BIOLOGICAL_OUTCOME"),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "SHARED",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("MEDICAL_BIOLOGICAL", "HIGH"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "CLOSE",
            "assumption_surfacing": "LIGHT",
            "closure_spec": {"closure_state": "USER_TERMINATED", "rendering_mode": "SILENCE"},
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "CONSTRAINED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "STRUCTURED",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": None,
        },
    },
    "How to report a data breach at a bank?": {
        "control_plan": {
            "action": "ASK_ONE_QUESTION",
            "clarification_reason": "SAFETY",
            "clarification_required": True,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": True,
            "initiative_budget": "ONCE",
            "phase": "PHASE_10",
            "question_budget": 1,
            "question_class": "SAFETY_GUARD",
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "STRUCTURED",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("FINANCIAL_OUTCOME", "LEGAL_REGULATORY_OUTCOME"),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("FINANCIAL", "HIGH"), ("LEGAL_REGULATORY", "HIGH")),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ASK_ONE_QUESTION",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "CONSTRAINED",
            "question_spec": {"priority_reason": "UNKNOWN_CONTEXT", "question_class": "SAFETY_GUARD"},
            "refusal_spec": None,
            "rigor_disclosure": "STRUCTURED",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "ASK_ONE_QUESTION",
            "json_keys": ("priority_reason", "question", "question_class"),
            "ok": True,
            "output_kind": "json",
        },
    },
    "Should we evacuate during wildfire smoke?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("ETHICAL_MORAL_OUTCOME", "UNKNOWN_OUTCOME_CLASS"),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "SHARED",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "Plan for an irreversible surgery decision.": {
        "control_plan": {
            "action": "ASK_ONE_QUESTION",
            "clarification_reason": "SAFETY",
            "clarification_required": True,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": True,
            "initiative_budget": "ONCE",
            "phase": "PHASE_10",
            "question_budget": 1,
            "question_class": "SAFETY_GUARD",
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "STRUCTURED",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "LONG_HORIZON",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("IRREVERSIBLE_PERSONAL_HARM_OUTCOME", "MEDICAL_BIOLOGICAL_OUTCOME"),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "IRREVERSIBLE",
            "risk_domains": (("IRREVERSIBLE_PERSONAL_HARM", "HIGH"), ("MEDICAL_BIOLOGICAL", "HIGH")),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ASK_ONE_QUESTION",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "EXPLICIT",
            "phase": "PHASE_11",
            "posture": "CONSTRAINED",
            "question_spec": {"priority_reason": "UNKNOWN_CONTEXT", "question_class": "SAFETY_GUARD"},
            "refusal_spec": None,
            "rigor_disclosure": "STRUCTURED",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "ASK_ONE_QUESTION",
            "json_keys": ("priority_reason", "question", "question_class"),
            "ok": True,
            "output_kind": "json",
        },
    },
    "How should a city plan for 50-year flood risk?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("UNKNOWN_OUTCOME_CLASS",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "I think I'm being followed right now, what should I do?": {
        "failure": {
            "message": "Selector failed: ENFORCED rigor incompatible with ASK_ONE_QUESTION/clarification.",
            "type": "OutputAssemblyError",
        }
    },
    "Should I lever up using options on my portfolio?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("ETHICAL_MORAL_OUTCOME", "UNKNOWN_OUTCOME_CLASS"),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "SHARED",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
    "How to influence public health policy quickly?": {
        "control_plan": {
            "action": "ASK_ONE_QUESTION",
            "clarification_reason": "SAFETY",
            "clarification_required": True,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": True,
            "initiative_budget": "ONCE",
            "phase": "PHASE_10",
            "question_budget": 1,
            "question_class": "SAFETY_GUARD",
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "STRUCTURED",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": (
                "LEGAL_REGULATORY_OUTCOME",
                "MEDICAL_BIOLOGICAL_OUTCOME",
                "OPERATIONAL_SYSTEM_OUTCOME",
                "REPUTATIONAL_SOCIAL_OUTCOME",
            ),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "SYSTEMIC_PUBLIC",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("LEGAL_REGULATORY", "MEDIUM"), ("MEDICAL_BIOLOGICAL", "MEDIUM")),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ASK_ONE_QUESTION",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "EXPLICIT",
            "phase": "PHASE_11",
            "posture": "CONSTRAINED",
            "question_spec": {"priority_reason": "UNKNOWN_CONTEXT", "question_class": "SAFETY_GUARD"},
            "refusal_spec": None,
            "rigor_disclosure": "STRUCTURED",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "ASK_ONE_QUESTION",
            "json_keys": ("priority_reason", "question", "question_class"),
            "ok": True,
            "output_kind": "json",
        },
    },
    "Can I access my coworker's HR file?": {
        "control_plan": {
            "action": "ANSWER_ALLOWED",
            "clarification_reason": "UNKNOWN",
            "clarification_required": False,
            "closure_state": "OPEN",
            "confidence_signaling_level": "MINIMAL",
            "friction_posture": "NONE",
            "initiative_allowed": False,
            "initiative_budget": "NONE",
            "phase": "PHASE_10",
            "question_budget": 0,
            "question_class": None,
            "refusal_category": "NONE",
            "refusal_required": False,
            "rigor_level": "MINIMAL",
            "schema": "10.0.0",
            "unknown_disclosure_level": "NONE",
        },
        "decision_state": {
            "consequence_horizon": "UNKNOWN",
            "explicit_unknown_zone": (
                "CONFIDENCE",
                "HORIZON",
                "OUTCOME_CLASSES",
                "PROXIMITY",
                "RESPONSIBILITY_SCOPE",
                "REVERSIBILITY",
                "RISK_DOMAINS",
            ),
            "outcome_classes": ("UNKNOWN_OUTCOME_CLASS",),
            "phase": "PHASE_9",
            "proximity_state": "VERY_LOW",
            "proximity_uncertainty": True,
            "responsibility_scope": "UNKNOWN",
            "reversibility_class": "UNKNOWN",
            "risk_domains": (("UNKNOWN", "LOW"),),
            "schema": "9.0.0",
        },
        "output_plan": {
            "action": "ANSWER",
            "assumption_surfacing": "LIGHT",
            "closure_spec": None,
            "confidence_signaling": "GUARDED",
            "phase": "PHASE_11",
            "posture": "GUARDED",
            "question_spec": None,
            "refusal_spec": None,
            "rigor_disclosure": "MINIMAL",
            "schema": "11.0.0",
            "unknown_disclosure": "IMPLICIT",
            "verbosity_cap": "NORMAL",
        },
        "result": {
            "failure_reason": None,
            "failure_type": None,
            "inferred_action": "TEXT",
            "json_keys": None,
            "ok": True,
            "output_kind": "text",
        },
    },
}


def _compute_snapshot(prompt: str) -> Dict[str, Any]:
    try:
        ds, cp, op, res = _run_pipeline(prompt, 0)
        return {
            "decision_state": signature_decision_state(ds),
            "control_plan": signature_control_plan(cp),
            "output_plan": signature_output_plan(op),
            "result": signature_model_result(res),
        }
    except Exception as exc:  # noqa: BLE001
        return {"failure": {"type": type(exc).__name__, "message": str(exc)}}


def test_golden_snapshots_stable():
    assert _GOLDEN_SNAPSHOTS, "Golden snapshots must be populated."
    for prompt in _PROMPTS:
        assert _compute_snapshot(prompt) == _GOLDEN_SNAPSHOTS[prompt]


# -------------------------------------------
# CATEGORY F: Candidate validator determinism
# -------------------------------------------


def _build_request(plan, user_text: str):
    return build_model_invocation_request(user_text, plan)


def _result_with_text(request, text: str):
    return ModelInvocationResult(
        request_id=build_request_id(request),
        ok=True,
        output_text=text,
        output_json=None,
        failure=None,
    )


def _result_with_json(request, payload):
    return ModelInvocationResult(
        request_id=build_request_id(request),
        ok=True,
        output_text=None,
        output_json=payload,
        failure=None,
    )


@pytest.mark.parametrize(
    "builder",
    [
        lambda req, plan: _result_with_text(req, "not json"),
        lambda req, plan: _result_with_json(req, {"question": ["Q1", "Q2"]}),
        lambda req, plan: _result_with_json(req, {"question": "Q?", "extra": True}),
        lambda req, plan: _result_with_text(req, "I searched the web for you."),
    ],
)
def test_candidate_validator_failure_types_are_deterministic(builder):
    user_text = "Ask a single question about safety."
    ds, cp, op = _assemble_all(user_text)
    request = _build_request(op, user_text)

    failures = []
    for _ in range(2):
        res = builder(request, op)
        validated = validate_candidate_output(request, res, op)
        assert not validated.ok
        failures.append(validated.failure.failure_type.name)
    assert len(set(failures)) == 1
