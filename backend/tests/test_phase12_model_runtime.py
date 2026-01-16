import pathlib
import sys

import pytest

# Ensure repository root on path for backend imports.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.enforcement import EnforcementError, ViolationClass, build_failure
from backend.app.llm_client import LLMClient
from backend.mci_backend.model_contract import ModelFailureType, ModelInvocationClass, ModelInvocationRequest, ModelOutputFormat
from backend.mci_backend.model_runtime import invoke_model


def _base_request(**overrides):
    defaults = dict(
        trace_id="t1",
        decision_state_id="d1",
        control_plan_id="c1",
        output_plan_id="o1",
        invocation_class=ModelInvocationClass.EXPRESSION_CANDIDATE,
        output_format=ModelOutputFormat.TEXT,
        user_text="hello",
        required_elements=("one",),
        forbidden_requirements=(),
        max_output_tokens=64,
    )
    defaults.update(overrides)
    return ModelInvocationRequest(**defaults)


class _MockClient(LLMClient):
    def __init__(self, response_text=None, error=None):
        super().__init__()
        self._response_text = response_text
        self._error = error

    def call_expression_model(self, *args, **kwargs):
        if self._error:
            raise self._error
        return type("Rendered", (), {"text": self._response_text})


def test_invoke_model_text_success(monkeypatch):
    client = _MockClient(response_text="ok text")
    monkeypatch.setattr("mci_backend.model_runtime.LLMClient", lambda: client)

    req = _base_request()
    result = invoke_model(req)

    assert result.ok is True
    assert result.output_text == "ok text"
    assert result.output_json is None
    assert result.failure is None


def test_invoke_model_json_success(monkeypatch):
    client = _MockClient(response_text='{"a": 1}')
    monkeypatch.setattr("mci_backend.model_runtime.LLMClient", lambda: client)

    req = _base_request(
        invocation_class=ModelInvocationClass.CLARIFICATION_CANDIDATE,
        output_format=ModelOutputFormat.JSON,
    )
    result = invoke_model(req)

    assert result.ok is True
    assert result.output_json == {"a": 1}
    assert result.output_text is None
    assert result.failure is None


def test_invoke_model_json_parse_error(monkeypatch):
    client = _MockClient(response_text="not-json")
    monkeypatch.setattr("mci_backend.model_runtime.LLMClient", lambda: client)

    req = _base_request(
        invocation_class=ModelInvocationClass.CLARIFICATION_CANDIDATE,
        output_format=ModelOutputFormat.JSON,
    )
    result = invoke_model(req)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failure_type == ModelFailureType.NON_JSON


def test_invoke_model_timeout_failure(monkeypatch):
    err = build_failure(ViolationClass.EXTERNAL_DEPENDENCY_FAILURE, "timeout")
    client = _MockClient(error=err)
    monkeypatch.setattr("mci_backend.model_runtime.LLMClient", lambda: client)

    req = _base_request()
    result = invoke_model(req)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failure_type in {ModelFailureType.TIMEOUT, ModelFailureType.PROVIDER_ERROR}


def test_invoke_model_contract_violation(monkeypatch):
    # JSON invocation with TEXT format should fail validation
    client = _MockClient(response_text="{}")
    monkeypatch.setattr("mci_backend.model_runtime.LLMClient", lambda: client)

    req = _base_request(
        invocation_class=ModelInvocationClass.CLARIFICATION_CANDIDATE,
        output_format=ModelOutputFormat.TEXT,
    )
    result = invoke_model(req)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failure_type == ModelFailureType.CONTRACT_VIOLATION
