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

    # DIAGNOSTIC: Log structured diagnostics for verification failure
    import json
    import logging
    from backend.mci_backend.diagnostic_utils import sanitize_preview
    
    logger = logging.getLogger(__name__)
    
    # Build comprehensive diagnostic payload
    diagnostic_payload = {
        "event": "model_output_verification_failed",
        "request_id": verified.request_id if verified else "unknown",
        "route": "/api/chat",  # This is called from chat endpoint
        "action": output_plan.action.value if output_plan else "unknown",
        "failure_type": verified.failure.failure_type.value if (verified and verified.failure) else None,
        "reason_code": verified.failure.reason_code if (verified and verified.failure) else None,
        "parse_error": verified.failure.message if (verified and verified.failure) else None,
        "has_output_json": bool(result.output_json),
        "has_output_text": bool(result.output_text),
        "output_shape": {
            "json_present": result.output_json is not None,
            "text_present": result.output_text is not None,
            "model_ok": result.ok,
        },
        "raw_preview": sanitize_preview(result.output_text) if result.output_text else sanitize_preview(str(result.output_json)) if result.output_json else "",
        "model": "expression_model",  # This is the expression model path
    }
    
    # Log as single-line JSON for grep-friendly Railway logs
    logger.warning("MODEL_VERIFY_FAIL %s", json.dumps(diagnostic_payload, ensure_ascii=False))
    
    # Also log human-readable version for backward compatibility
    logger.warning(
        "[FALLBACK] Model output verification failed, using fallback rendering",
        extra=diagnostic_payload,
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
