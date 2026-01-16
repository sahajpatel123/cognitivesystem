"""Phase 12 — Step 0: Model invocation contract and trust boundary lock.

Defines bounded enums and immutable dataclasses for model invocation requests/results.
No provider selection, no runtime calls, no retries. OutputPlan remains authoritative.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


SCHEMA_VERSION = "12.0.0"


class PhaseMarker(str, Enum):
    PHASE_12 = "PHASE_12"


class ModelInvocationClass(str, Enum):
    EXPRESSION_CANDIDATE = "EXPRESSION_CANDIDATE"
    CLARIFICATION_CANDIDATE = "CLARIFICATION_CANDIDATE"
    REFUSAL_EXPLANATION_CANDIDATE = "REFUSAL_EXPLANATION_CANDIDATE"
    CLOSURE_MESSAGE_CANDIDATE = "CLOSURE_MESSAGE_CANDIDATE"


class ModelOutputFormat(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"


class ModelFailureType(str, Enum):
    TIMEOUT = "TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    NON_JSON = "NON_JSON"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    FORBIDDEN_CONTENT = "FORBIDDEN_CONTENT"


class ModelContractError(Exception):
    """Base contract error."""


class ModelContractInvariantViolation(ModelContractError):
    """Raised when contract invariants are violated."""


@dataclass(frozen=True)
class ModelInvocationRequest:
    trace_id: str
    decision_state_id: str
    control_plan_id: str
    output_plan_id: str
    invocation_class: ModelInvocationClass
    output_format: ModelOutputFormat
    user_text: str
    required_elements: Tuple[str, ...]
    forbidden_requirements: Tuple[str, ...]
    max_output_tokens: int
    schema_version: str = SCHEMA_VERSION
    phase_marker: PhaseMarker = PhaseMarker.PHASE_12


@dataclass(frozen=True)
class ModelFailure:
    failure_type: ModelFailureType
    reason_code: str
    message: str
    fail_closed: bool = True


@dataclass(frozen=True)
class ModelInvocationResult:
    request_id: str
    ok: bool
    output_text: Optional[str]
    output_json: Optional[Dict[str, object]]
    failure: Optional[ModelFailure]
    schema_version: str = SCHEMA_VERSION
    phase_marker: PhaseMarker = PhaseMarker.PHASE_12


def _is_non_empty(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def validate_model_request(request: ModelInvocationRequest) -> None:
    if request is None:
        raise ModelContractError("request is required")

    required_ids = [
        request.trace_id,
        request.decision_state_id,
        request.control_plan_id,
        request.output_plan_id,
    ]
    if not all(_is_non_empty(v) for v in required_ids):
        raise ModelContractInvariantViolation("all ids must be non-empty")

    if request.schema_version != SCHEMA_VERSION:
        raise ModelContractInvariantViolation("schema_version mismatch")
    if request.phase_marker != PhaseMarker.PHASE_12:
        raise ModelContractInvariantViolation("phase_marker mismatch")

    if request.max_output_tokens <= 0 or request.max_output_tokens > 8192:
        raise ModelContractInvariantViolation("max_output_tokens must be within 1..8192")

    if not _is_non_empty(request.user_text):
        raise ModelContractInvariantViolation("user_text must be non-empty")

    if any(not _is_non_empty(e) for e in request.required_elements):
        raise ModelContractInvariantViolation("required_elements must be non-empty strings")
    if any(not _is_non_empty(e) for e in request.forbidden_requirements):
        raise ModelContractInvariantViolation("forbidden_requirements must be non-empty strings")

    if request.invocation_class == ModelInvocationClass.CLARIFICATION_CANDIDATE:
        if request.output_format != ModelOutputFormat.JSON:
            raise ModelContractInvariantViolation("CLARIFICATION_CANDIDATE requires JSON output_format")
    else:
        if request.output_format != ModelOutputFormat.TEXT:
            raise ModelContractInvariantViolation("Only TEXT output_format allowed for this invocation_class")


def validate_model_result(result: ModelInvocationResult, request: ModelInvocationRequest) -> None:
    if result is None or request is None:
        raise ModelContractError("result and request are required")

    if result.schema_version != SCHEMA_VERSION:
        raise ModelContractInvariantViolation("schema_version mismatch")
    if result.phase_marker != PhaseMarker.PHASE_12:
        raise ModelContractInvariantViolation("phase_marker mismatch")

    if not _is_non_empty(result.request_id):
        raise ModelContractInvariantViolation("request_id must be non-empty")

    if result.ok:
        if result.failure is not None:
            raise ModelContractInvariantViolation("ok result cannot include failure")
        if request.output_format == ModelOutputFormat.JSON:
            if result.output_json is None:
                raise ModelContractInvariantViolation("JSON output required")
            if not isinstance(result.output_json, dict):
                raise ModelContractInvariantViolation("output_json must be a dict")
            if result.output_text not in (None, ""):
                raise ModelContractInvariantViolation("output_text must be empty when JSON requested")
        else:
            if not _is_non_empty(result.output_text or ""):
                raise ModelContractInvariantViolation("text output required")
            if result.output_json not in (None, {}):
                raise ModelContractInvariantViolation("output_json must be empty when text requested")
    else:
        if result.failure is None:
            raise ModelContractInvariantViolation("non-ok result must include failure")
        if result.output_text not in (None, "") or result.output_json not in (None, {}):
            raise ModelContractInvariantViolation("failure result must not include outputs")
        if result.failure.fail_closed is not True:
            raise ModelContractInvariantViolation("failure must be fail-closed")


def build_request_id(request: ModelInvocationRequest) -> str:
    """Deterministic request id derived from trace + output_plan + invocation class."""
    seed = f"{request.trace_id}:{request.output_plan_id}:{request.invocation_class.value}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


__all__ = [
    "SCHEMA_VERSION",
    "PhaseMarker",
    "ModelInvocationClass",
    "ModelOutputFormat",
    "ModelFailureType",
    "ModelContractError",
    "ModelContractInvariantViolation",
    "ModelInvocationRequest",
    "ModelInvocationResult",
    "ModelFailure",
    "validate_model_request",
    "validate_model_result",
    "build_request_id",
]
