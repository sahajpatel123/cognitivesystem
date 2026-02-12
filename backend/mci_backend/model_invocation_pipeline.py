"""Phase 12 — Step 3: Canonical model invocation pipeline (prompt → invoke → validate)."""

from __future__ import annotations

from typing import Optional

from backend.app.llm_client import LLMClient
from backend.mci_backend.control_plan import ControlPlan
from backend.mci_backend.decision_state import DecisionState
from backend.mci_backend.model_candidate_validation import validate_candidate_output
from backend.mci_backend.model_contract import (
    ModelFailure,
    ModelFailureType,
    ModelInvocationRequest,
    ModelInvocationResult,
    build_request_id,
)
from backend.mci_backend.model_prompt_builder import ModelPromptBuilderError, build_model_invocation_request
from backend.mci_backend.model_runtime import invoke_model
from backend.mci_backend.model_output_verify import verify_and_sanitize_model_output
from backend.mci_backend.fallback_rendering import FallbackRenderingError, render_fallback_content
from backend.mci_backend.output_plan import OutputAction, OutputPlan, validate_output_plan


def _failure_result(
    request_id: str,
    failure_type: ModelFailureType,
    reason_code: str,
    message: str,
) -> ModelInvocationResult:
    return ModelInvocationResult(
        request_id=request_id,
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


def invoke_model_for_output_plan(
    *,
    user_text: str,
    decision_state: DecisionState,
    control_plan: ControlPlan,
    output_plan: OutputPlan,
    llm_client: Optional[LLMClient] = None,
) -> ModelInvocationResult:
    """Canonical pipeline: validate plan → build request → invoke model → validate candidate."""
    # 1) Validate OutputPlan (fail-closed)
    try:
        validate_output_plan(output_plan)
    except Exception as exc:  # noqa: BLE001
        rid = getattr(output_plan, "id", "invalid-output-plan")
        return _failure_result(rid, ModelFailureType.CONTRACT_VIOLATION, "OUTPUT_PLAN_INVALID", str(exc))

    # 2) Build request (Step 2)
    try:
        request = build_model_invocation_request(user_text, output_plan)
    except ModelPromptBuilderError as exc:
        rid = getattr(output_plan, "id", "invalid-output-plan")
        return _failure_result(rid, ModelFailureType.CONTRACT_VIOLATION, "REQUEST_BUILD_FAILED", str(exc))

    # 3) Invoke model (Step 1)
    result = invoke_model(request, llm_client=llm_client)

    # 4/5) Verify & sanitize candidate output against OutputPlan (fail-closed)
    verified = verify_and_sanitize_model_output(
        model_result=result,
        output_plan=output_plan,
        decision_state=decision_state,
        control_plan=control_plan,
        original_request_text=user_text,
    )
    if verified.ok:
        return verified

    # DIAGNOSTIC: Log why verification failed and fallback is being used
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "[FALLBACK] Model output verification failed, using fallback rendering",
        extra={
            "request_id": verified.request_id if verified else "unknown",
            "model_ok": result.ok,
            "model_has_text": bool(result.output_text),
            "model_has_json": bool(result.output_json),
            "verified_ok": verified.ok,
            "failure_type": verified.failure.failure_type.value if verified.failure else None,
            "failure_reason": verified.failure.reason_code if verified.failure else None,
            "output_action": output_plan.action.value,
        },
    )

    # 6) Deterministic fallback rendering (no model). Activates on model/verify failure.
    try:
        fallback = render_fallback_content(
            user_text=user_text,
            decision_state=decision_state,
            control_plan=control_plan,
            output_plan=output_plan,
        )
    except FallbackRenderingError as exc:
        rid = verified.request_id if verified and hasattr(verified, "request_id") else build_request_id(request)
        return _failure_result(rid, ModelFailureType.CONTRACT_VIOLATION, "FALLBACK_RENDER_FAILED", str(exc))

    # Build success result from fallback content.
    if output_plan.action == OutputAction.ASK_ONE_QUESTION:
        return ModelInvocationResult(
            request_id=verified.request_id if verified else build_request_id(request),
            ok=True,
            output_text=None,
            output_json=fallback.json,
            failure=None,
        )

    return ModelInvocationResult(
        request_id=verified.request_id if verified else build_request_id(request),
        ok=True,
        output_text=fallback.text,
        output_json=None,
        failure=None,
    )


__all__ = ["invoke_model_for_output_plan"]
