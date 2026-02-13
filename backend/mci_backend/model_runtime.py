"""Phase 12 — Step 1: Model invocation runtime adapter (tool-only, fail-closed).

Bridges the Phase 12 contract to the Phase 3 enforced model adapter.
No provider selection, no retries, no prompt tuning, no authority.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from backend.app.enforcement import EnforcementError, ViolationClass
from backend.app.llm_client import LLMClient
from backend.app.schemas import CognitiveStyle, ExpressionPlan, IntermediateAnswer, UserMessage

from backend.mci_backend.model_contract import (
    ModelContractError,
    ModelFailure,
    ModelFailureType,
    ModelInvocationClass,
    ModelInvocationRequest,
    ModelInvocationResult,
    ModelOutputFormat,
    build_request_id,
    validate_model_request,
)

logger = logging.getLogger(__name__)


def _default_style() -> CognitiveStyle:
    return CognitiveStyle(
        abstraction_level="medium",
        formality="neutral",
        preferred_analogies="mixed",
        overrides=None,
    )


def _default_expression_plan(required: tuple[str, ...]) -> ExpressionPlan:
    return ExpressionPlan(
        target_tone="neutral",
        structure=["ack"],
        analogy_style="mixed",
        constraints={"required_elements": list(required)},
        emphasis=list(required),
    )


def _default_intermediate(required: tuple[str, ...]) -> IntermediateAnswer:
    return IntermediateAnswer(
        goals=list(required) or ["bounded rendering"],
        key_points=list(required) or ["bounded response"],
        assumptions_and_uncertainties=[],
        checks_for_understanding=[],
    )


def _map_violation_to_failure_type(violation: ViolationClass, reason: str) -> ModelFailureType:
    if violation == ViolationClass.EXTERNAL_DEPENDENCY_FAILURE:
        if "timeout" in reason.lower():
            return ModelFailureType.TIMEOUT
        return ModelFailureType.PROVIDER_ERROR
    if violation in {ViolationClass.STRUCTURAL_VIOLATION, ViolationClass.SCHEMA_MISMATCH}:
        return ModelFailureType.SCHEMA_MISMATCH
    if violation in {
        ViolationClass.SEMANTIC_CONTRACT_VIOLATION,
        ViolationClass.BOUNDARY_VIOLATION,
        ViolationClass.EXECUTION_CONSTRAINT_VIOLATION,
    }:
        return ModelFailureType.CONTRACT_VIOLATION
    return ModelFailureType.CONTRACT_VIOLATION


def _failure_result(
    request: ModelInvocationRequest,
    failure_type: ModelFailureType,
    reason_code: str,
    message: str,
) -> ModelInvocationResult:
    return ModelInvocationResult(
        request_id=build_request_id(request),
        ok=False,
        output_text=None,
        output_json=None,
        failure=ModelFailure(
            failure_type=failure_type,
            reason_code=reason_code,
            message=message,
            fail_closed=True,
        ),
    )


def _call_expression_model(client: LLMClient, request: ModelInvocationRequest) -> str:
    user_message = UserMessage(id=request.trace_id, text=request.user_text, timestamp=0)
    style = _default_style()
    plan = _default_expression_plan(request.required_elements)
    intermediate = _default_intermediate(request.required_elements)
    rendered = client.call_expression_model(
        user_message=user_message,
        style=style,
        plan=plan,
        intermediate=intermediate,
    )
    return rendered.text


def invoke_model(request: ModelInvocationRequest, llm_client: LLMClient | None = None) -> ModelInvocationResult:
    try:
        validate_model_request(request)
    except ModelContractError as exc:
        return _failure_result(
            request,
            ModelFailureType.CONTRACT_VIOLATION,
            reason_code="INVALID_REQUEST",
            message=str(exc),
        )

    client = llm_client or LLMClient()

    try:
        raw_output = _call_expression_model(client, request)
        if request.output_format == ModelOutputFormat.JSON:
            try:
                parsed: Dict[str, Any] = json.loads(raw_output)
            except json.JSONDecodeError:
                return _failure_result(
                    request,
                    ModelFailureType.NON_JSON,
                    reason_code="NON_JSON_RESPONSE",
                    message="Model output was not valid JSON",
                )
            if not isinstance(parsed, dict):
                return _failure_result(
                    request,
                    ModelFailureType.SCHEMA_MISMATCH,
                    reason_code="NON_OBJECT_JSON",
                    message="Model JSON output must be an object",
                )
            return ModelInvocationResult(
                request_id=build_request_id(request),
                ok=True,
                output_text=None,
                output_json=parsed,
                failure=None,
            )
        # TEXT path
        if not isinstance(raw_output, str) or not raw_output.strip():
            return _failure_result(
                request,
                ModelFailureType.SCHEMA_MISMATCH,
                reason_code="EMPTY_TEXT",
                message="Model text output missing",
            )
        return ModelInvocationResult(
            request_id=build_request_id(request),
            ok=True,
            output_text=raw_output,
            output_json=None,
            failure=None,
        )
    except EnforcementError as exc:
        failure_type = _map_violation_to_failure_type(exc.failure.violation_class, exc.failure.reason)
        return _failure_result(
            request,
            failure_type,
            reason_code=exc.failure.violation_class.value,
            message=exc.failure.reason,
        )
    except ModelContractError as exc:
        return _failure_result(
            request,
            ModelFailureType.CONTRACT_VIOLATION,
            reason_code="CONTRACT_ERROR",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        # Log full traceback for debugging provider errors
        logger.exception(
            "PROVIDER_ERROR",
            extra={
                "model": "expression_model",
                "request_id": build_request_id(request),
                "route": "/api/chat",
            }
        )
        return _failure_result(
            request,
            ModelFailureType.PROVIDER_ERROR,
            reason_code="UNEXPECTED_ERROR",
            message=str(exc),
        )


__all__ = [
    "invoke_model",
]
