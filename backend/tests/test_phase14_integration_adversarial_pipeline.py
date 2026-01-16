from __future__ import annotations

import pytest

import backend.mci_backend.governed_response_runtime as grr
from backend.tests._phase14_fake_llm import Phase14FakeLLM, Phase14TimeoutLLM, Phase14ErrorLLM
from backend.tests._phase14_attack_cases import make_decision_state, make_control_plan, make_output_plan
from backend.mci_backend.control_plan import (
    ControlAction,
    ClarificationReason,
    RefusalCategory,
    FrictionPosture,
    InitiativeBudget,
    RigorLevel,
    QuestionClass,
    ConfidenceSignalingLevel,
    UnknownDisclosureLevel,
)
from backend.mci_backend.output_plan import OutputAction
from backend.mci_backend.model_contract import ModelFailureType


@pytest.fixture(autouse=True)
def patch_orchestrator(monkeypatch):
    # minimal deterministic assemblies to avoid touching locked code paths beyond orchestrator wiring
    def _decision_state(decision_id: str, trace_id: str, message: str):
        return make_decision_state()

    def _control_plan(user_text, decision_state):
        return make_control_plan(decision_state, action=ControlAction.ANSWER_ALLOWED)

    def _output_plan(user_text, decision_state, control_plan):
        return make_output_plan(decision_state, control_plan, action=OutputAction.ANSWER)

    monkeypatch.setattr(grr, "assemble_decision_state", _decision_state)
    monkeypatch.setattr(grr, "assemble_control_plan", _control_plan)
    monkeypatch.setattr(grr, "assemble_output_plan", _output_plan)


def test_fenced_json_via_pipeline_falls_back():
    llm = Phase14FakeLLM(["```json {\"question\":\"hi\"}```"])
    res = grr.render_governed_response("attack fenced", llm_client=llm)
    assert res.ok
    assert res.output_text is not None


def test_extra_keys_in_json_via_pipeline_rejected_then_fallback():
    llm = Phase14FakeLLM(['{"question": "hi?", "question_class": "SAFETY_GUARD", "priority_reason": "SAFETY_CRITICAL", "extra": true}'])
    res = grr.render_governed_response("attack extra keys", llm_client=llm)
    assert res.ok
    assert res.output_text is not None


def test_authority_claims_do_not_leak():
    llm = Phase14FakeLLM(["I accessed your data and updated rules"])
    res = grr.render_governed_response("authority claim", llm_client=llm)
    assert res.ok
    assert res.output_text is not None
    assert "accessed your data" not in res.output_text.lower()


def test_timeout_path_uses_fallback():
    llm = Phase14TimeoutLLM()
    res = grr.render_governed_response("timeout path", llm_client=llm)
    assert res.ok
    assert res.failure is None
    assert res.output_text is not None


def test_provider_error_uses_fallback():
    llm = Phase14ErrorLLM("provider error")
    res = grr.render_governed_response("provider path", llm_client=llm)
    assert res.ok
    assert res.output_text is not None


def test_refusal_category_mismatch_rejected():
    # The pipeline should fail-closed internally and surface safe refusal text.
    ds = make_decision_state()
    cp = make_control_plan(ds, action=ControlAction.REFUSE)
    op = make_output_plan(ds, cp, action=OutputAction.REFUSE)
    llm = Phase14FakeLLM(['{"refusal_category": "CAPABILITY_REFUSAL", "refusal_text": "no"}'])
    res = grr.invoke_model_for_output_plan(
        user_text="refusal mismatch",
        decision_state=ds,
        control_plan=cp,
        output_plan=op,
        llm_client=llm,
    )
    assert res.ok
    assert res.failure is None
    assert res.output_text is not None
    assert "capability" not in res.output_text.lower()


def test_close_cannot_accept_questions():
    ds = make_decision_state()
    cp = make_control_plan(ds, action=ControlAction.CLOSE)
    op = make_output_plan(ds, cp, action=OutputAction.CLOSE)
    llm = Phase14FakeLLM(['{"closure_state": "CLOSING", "closure_text": "Shutting down?"}'])
    res = grr.invoke_model_for_output_plan(
        user_text="close question",
        decision_state=ds,
        control_plan=cp,
        output_plan=op,
        llm_client=llm,
    )
    assert res.ok
    assert res.failure is None
    assert res.output_text is not None
    assert "?" not in res.output_text
