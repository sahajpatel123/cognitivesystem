"""Phase 12 — Step 7: Canonical governed response orchestrator (deterministic, fail-closed)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from backend.app.llm_client import LLMClient
from mci_backend.decision_assembly import assemble_decision_state
from mci_backend.model_contract import ModelFailure, ModelFailureType, ModelInvocationResult
from mci_backend.model_invocation_pipeline import invoke_model_for_output_plan
from mci_backend.orchestration_assembly import assemble_control_plan
from mci_backend.expression_assembly import assemble_output_plan


class GovernedOrchestratorError(Exception):
    """Raised when orchestrator cannot complete deterministically."""


_TRACE_NAMESPACE = uuid.UUID("5b9fb9d8-4c5e-4568-8e5d-b1c0f6a99e7e")
_DECISION_NAMESPACE = uuid.UUID("b8e5b0b5-0c2b-4e91-9e2e-4f9c123b9f66")


def _failure_result(request_id: str, failure_type: ModelFailureType, reason_code: str, message: str) -> ModelInvocationResult:
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


def _deterministic_trace_id(user_text: str) -> str:
    return str(uuid.uuid5(_TRACE_NAMESPACE, user_text.strip()))


def _deterministic_decision_id(user_text: str) -> str:
    return str(uuid.uuid5(_DECISION_NAMESPACE, user_text.strip()))


def render_governed_response(user_text: str, *, llm_client: Optional[LLMClient] = None) -> ModelInvocationResult:
    """
    Canonical orchestrator entrypoint (Phase 12 Step 7).

    Pipeline:
    - Assemble DecisionState (Phase 9)
    - Assemble ControlPlan (Phase 10)
    - Assemble OutputPlan (Phase 11)
    - Invoke Phase 12 model pipeline (prompt → runtime → verify → fallback)

    Returns ModelInvocationResult with governed text/JSON or fail-closed failure.
    """
    if not isinstance(user_text, str) or not user_text.strip():
        raise GovernedOrchestratorError("user_text must be non-empty")

    trace_id = _deterministic_trace_id(user_text)
    decision_id = _deterministic_decision_id(user_text)

    try:
        decision_state = assemble_decision_state(decision_id=decision_id, trace_id=trace_id, message=user_text)
    except Exception as exc:  # noqa: BLE001
        return _failure_result(trace_id, ModelFailureType.CONTRACT_VIOLATION, "DECISION_ASSEMBLY_FAILED", str(exc))

    try:
        control_plan = assemble_control_plan(user_text, decision_state)
    except Exception as exc:  # noqa: BLE001
        return _failure_result(trace_id, ModelFailureType.CONTRACT_VIOLATION, "CONTROL_PLAN_ASSEMBLY_FAILED", str(exc))

    try:
        output_plan = assemble_output_plan(user_text, decision_state, control_plan)
    except Exception as exc:  # noqa: BLE001
        return _failure_result(trace_id, ModelFailureType.CONTRACT_VIOLATION, "OUTPUT_PLAN_ASSEMBLY_FAILED", str(exc))

    # Phase 12 pipeline (includes verification + fallback)
    return invoke_model_for_output_plan(
        user_text=user_text,
        decision_state=decision_state,
        control_plan=control_plan,
        output_plan=output_plan,
        llm_client=llm_client,
    )


__all__ = ["render_governed_response", "GovernedOrchestratorError"]
