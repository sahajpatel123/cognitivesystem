from __future__ import annotations

from typing import Dict

from backend.app.config import get_settings
from backend.app.llm_client import LLMClient
from backend.app.providers.circuit import is_open, record_failure, record_success
from backend.app.providers.errors import (
    ProviderCircuitOpenError,
    ProviderDisabledError,
    ProviderMisconfiguredError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)
from backend.mci_backend.governed_response_runtime import render_governed_response
from backend.mci_backend.model_contract import ModelFailureType, ModelInvocationResult


def _circuit_key(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def call_model(user_text: str, *, request_id: str, token_estimate_in: int, max_output_tokens: int) -> ModelInvocationResult:
    s = get_settings()
    caps = s.validated_caps()
    key = _circuit_key(s.model_provider, s.model_name)

    if s.model_calls_enabled == 0:
        raise ProviderDisabledError("model calls disabled")

    if s.model_provider == "none":
        raise ProviderMisconfiguredError("model provider not configured")

    if s.model_provider not in ("custom", "local") and not (s.model_api_key or s.llm_api_key):
        raise ProviderMisconfiguredError("model api key missing")

    open_now, retry_after = is_open(key, open_seconds=s.model_circuit_breaker_open_seconds)
    if open_now:
        raise ProviderCircuitOpenError(retry_after)

    client = LLMClient(
        api_base=s.model_base_url or s.model_provider_base_url or s.llm_api_base,
        api_key=s.model_api_key or s.llm_api_key,
        timeout_seconds=float(s.model_timeout_seconds),
        connect_timeout_seconds=float(s.model_connect_timeout_seconds),
        request_id_header=s.request_id_header,
        request_id_value=request_id,
    )

    try:
        result = render_governed_response(user_text, llm_client=client)
    except ProviderCircuitOpenError:
        raise
    except Exception as exc:  # noqa: BLE001
        record_failure(
            key,
            window_seconds=s.model_circuit_breaker_window_seconds,
            failure_threshold=s.model_circuit_breaker_failures,
            open_seconds=s.model_circuit_breaker_open_seconds,
        )
        raise ProviderUpstreamError(str(exc)) from exc

    if result.ok:
        record_success(key)
        return result

    failure = result.failure
    if failure:
        if failure.failure_type == ModelFailureType.TIMEOUT:
            record_failure(
                key,
                window_seconds=s.model_circuit_breaker_window_seconds,
                failure_threshold=s.model_circuit_breaker_failures,
                open_seconds=s.model_circuit_breaker_open_seconds,
            )
            raise ProviderTimeoutError(failure.message)
        if failure.failure_type == ModelFailureType.PROVIDER_ERROR:
            record_failure(
                key,
                window_seconds=s.model_circuit_breaker_window_seconds,
                failure_threshold=s.model_circuit_breaker_failures,
                open_seconds=s.model_circuit_breaker_open_seconds,
            )
            raise ProviderUpstreamError(failure.message)

    # Non-provider failures do not trip the circuit
    record_success(key)
    return result


__all__ = ["call_model"]
