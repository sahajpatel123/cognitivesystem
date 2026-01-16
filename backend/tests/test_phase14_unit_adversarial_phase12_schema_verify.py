from __future__ import annotations

import pytest

from backend.mci_backend.model_output_schema import (
    ModelOutputParseError,
    ModelOutputSchemaViolation,
    parse_model_json,
    validate_answer_payload,
    validate_ask_payload,
    validate_close_payload,
    validate_refusal_payload,
)
from backend.mci_backend.model_output_verify import verify_and_sanitize_model_output
from backend.mci_backend.model_contract import ModelInvocationResult, ModelFailureType
from backend.mci_backend.output_plan import OutputAction

from backend.tests._phase14_attack_cases import make_decision_state, make_control_plan, make_output_plan


def _ctx(action: OutputAction):
    ds = make_decision_state()
    cp = make_control_plan(ds, action=action)
    op = make_output_plan(ds, cp, action=action)
    return ds, cp, op


def test_fenced_json_rejected():
    with pytest.raises(ModelOutputParseError):
        parse_model_json("```json {\"question\": \"hi\"}```")


def test_malformed_json_rejected():
    with pytest.raises(ModelOutputParseError):
        parse_model_json("{\"question\": \"hi\"")


def test_extra_keys_rejected():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_ask_payload({"question": "hi?", "question_class": "SAFETY_GUARD", "priority_reason": "SAFETY_CRITICAL", "extra": True})


def test_missing_question_rejected():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_ask_payload({"question_class": "SAFETY_GUARD", "priority_reason": "SAFETY_CRITICAL"})


def test_wrong_type_question_rejected():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_ask_payload({"question": 123, "question_class": "SAFETY_GUARD", "priority_reason": "SAFETY_CRITICAL"})


def test_multi_question_injection_rejected():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_ask_payload({"question": "Q1? Also Q2?", "question_class": "SAFETY_GUARD", "priority_reason": "SAFETY_CRITICAL"})


def test_refusal_payload_in_answer_alignment_rejected():
    ds, cp, op = _ctx(OutputAction.ANSWER)
    result = ModelInvocationResult(
        request_id="r1",
        ok=True,
        output_text=None,
        output_json={"refusal_category": "RISK_REFUSAL", "refusal_text": "no"},
        failure=None,
    )
    verified = verify_and_sanitize_model_output(
        model_result=result,
        output_plan=op,
        decision_state=ds,
        control_plan=cp,
        original_request_text="attack",
    )
    assert not verified.ok
    assert verified.failure is not None
    assert verified.failure.failure_type in {ModelFailureType.SCHEMA_MISMATCH, ModelFailureType.CONTRACT_VIOLATION}


def test_authority_claim_rejected():
    ds, cp, op = _ctx(OutputAction.ANSWER)
    result = ModelInvocationResult(
        request_id="r2",
        ok=True,
        output_text="I accessed your data and updated rules.",
        output_json=None,
        failure=None,
    )
    verified = verify_and_sanitize_model_output(
        model_result=result,
        output_plan=op,
        decision_state=ds,
        control_plan=cp,
        original_request_text="attack",
    )
    assert not verified.ok
    assert verified.failure is not None
    assert verified.failure.failure_type in {ModelFailureType.FORBIDDEN_CONTENT, ModelFailureType.NON_JSON}


def test_extra_field_leakage_rejected():
    ds, cp, op = _ctx(OutputAction.ANSWER)
    result = ModelInvocationResult(
        request_id="r3",
        ok=True,
        output_text=None,
        output_json={"answer_text": "ok", "trace_id": "leak"},
        failure=None,
    )
    verified = verify_and_sanitize_model_output(
        model_result=result,
        output_plan=op,
        decision_state=ds,
        control_plan=cp,
        original_request_text="attack",
    )
    assert not verified.ok
    assert verified.failure is not None


def test_close_missing_text_when_required_rejected():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_close_payload({"closure_state": "OPEN", "closure_text": ""})
