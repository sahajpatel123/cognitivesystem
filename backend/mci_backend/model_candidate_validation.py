"""Phase 12 — Step 3: Candidate output validation (fail-closed, bounded)."""

from __future__ import annotations

from typing import Any, Dict

from backend.mci_backend.model_contract import (
    ModelFailure,
    ModelFailureType,
    ModelInvocationRequest,
    ModelInvocationResult,
    ModelOutputFormat,
)
from backend.mci_backend.output_plan import (
    ConfidenceSignalingLevel,
    OutputAction,
    OutputPlan,
    UnknownDisclosureMode,
)


class ModelCandidateValidationError(Exception):
    """Raised when candidate output fails validation."""


_MAX_TEXT_CHARS = 6000
_MAX_JSON_CHARS = 4000

_REFUSAL_PHRASES = (
    "i cannot comply",
    "i can't help with that",
    "as an ai model",
    "as an ai language model",
    "i must refuse",
    "i will not",
)

_TOOL_CLAIMS = (
    "i searched the web",
    "i accessed your account",
    "i executed code",
    "i ran a tool",
    "i called an api",
    "i browsed the internet",
    "<analysis>",
    "<system>",
    "system prompt",
    "internal policy",
)


def _failure(result: ModelInvocationResult, failure_type: ModelFailureType, reason_code: str, message: str) -> ModelInvocationResult:
    return ModelInvocationResult(
        request_id=result.request_id,
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


def _validate_common_text(text: str, result: ModelInvocationResult) -> ModelInvocationResult | None:
    if not text or not text.strip():
        return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "EMPTY_TEXT", "Output text missing")
    if len(text) > _MAX_TEXT_CHARS:
        return _failure(result, ModelFailureType.SCHEMA_MISMATCH, "TEXT_TOO_LONG", "Output text exceeds limit")
    lowered = text.lower()
    for phrase in _TOOL_CLAIMS:
        if phrase in lowered:
            return _failure(result, ModelFailureType.FORBIDDEN_CONTENT, "TOOL_CLAIM", "Tool-claim detected")
    return None


def _validate_answer(text: str, plan: OutputPlan, result: ModelInvocationResult) -> ModelInvocationResult | None:
    lowered = text.lower()
    if "?" in text:
        return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "QUESTION_IN_ANSWER", "Answer must not ask questions")
    for phrase in _REFUSAL_PHRASES:
        if phrase in lowered:
            return _failure(result, ModelFailureType.FORBIDDEN_CONTENT, "REFUSAL_IN_ANSWER", "Refusal phrasing in answer")
    if plan.unknown_disclosure != UnknownDisclosureMode.NONE:
        if all(token not in lowered for token in ["unknown", "uncertain", "not sure", "uncertainty"]):
            return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "MISSING_UNKNOWN_DISCLOSURE", "Unknown disclosure required")
    if plan.confidence_signaling != ConfidenceSignalingLevel.EXPLICIT:
        if any(token in lowered for token in ["100%", "certain", "definitely", "absolutely"]):
            return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "OVERCONFIDENT", "Overconfident language not allowed")
    return None


def _validate_question_output(payload: Dict[str, Any], result: ModelInvocationResult) -> ModelInvocationResult | None:
    if set(payload.keys()) != {"question"}:
        return _failure(result, ModelFailureType.SCHEMA_MISMATCH, "EXTRA_KEYS", "Question JSON must only contain 'question'")
    question = payload["question"]
    if not isinstance(question, str) or not question.strip():
        return _failure(result, ModelFailureType.SCHEMA_MISMATCH, "QUESTION_MISSING", "Question must be non-empty string")
    if len(question) > _MAX_JSON_CHARS:
        return _failure(result, ModelFailureType.SCHEMA_MISMATCH, "QUESTION_TOO_LONG", "Question exceeds limit")
    q_lower = question.lower()
    if "?" in question and question.count("?") > 1:
        return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "MULTI_QUESTION", "Multiple questions detected")
    if any(token in q_lower for token in ["and also", "also", "plus", "another question"]):
        return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "MULTI_QUESTION_HINT", "Multi-question phrasing detected")
    return None


def _validate_refusal(text: str, result: ModelInvocationResult) -> ModelInvocationResult | None:
    lowered = text.lower()
    if any(token in lowered for token in ["policy", "as per policy", "as an ai model"]):
        return _failure(result, ModelFailureType.FORBIDDEN_CONTENT, "POLICY_LANGUAGE", "Policy language not allowed")
    return None


def _validate_close(text: str, result: ModelInvocationResult) -> ModelInvocationResult | None:
    if "?" in text:
        return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "QUESTION_IN_CLOSE", "Closure must not ask questions")
    if len(text) > 500:
        return _failure(result, ModelFailureType.SCHEMA_MISMATCH, "CLOSE_TOO_LONG", "Closure too long")
    return None


def validate_candidate_output(request: ModelInvocationRequest, result: ModelInvocationResult, plan: OutputPlan) -> ModelInvocationResult:
    if not result.ok:
        return result

    if request.output_format == ModelOutputFormat.JSON:
        if result.output_json is None or not isinstance(result.output_json, dict):
            return _failure(result, ModelFailureType.SCHEMA_MISMATCH, "JSON_REQUIRED", "JSON output required")
        failure = _validate_question_output(result.output_json, result)
        return failure or result

    # TEXT path
    if result.output_text is None:
        return _failure(result, ModelFailureType.CONTRACT_VIOLATION, "TEXT_REQUIRED", "Text output required")
    failure = _validate_common_text(result.output_text, result)
    if failure:
        return failure

    if plan.action == OutputAction.ANSWER:
        failure = _validate_answer(result.output_text, plan, result)
    elif plan.action == OutputAction.REFUSE:
        failure = _validate_refusal(result.output_text, result)
    elif plan.action == OutputAction.CLOSE:
        failure = _validate_close(result.output_text, result)
    elif plan.action == OutputAction.ASK_ONE_QUESTION:
        # Should have been JSON; treat text as violation.
        failure = _failure(result, ModelFailureType.SCHEMA_MISMATCH, "QUESTION_JSON_REQUIRED", "ASK_ONE_QUESTION requires JSON output")
    else:
        failure = _failure(result, ModelFailureType.CONTRACT_VIOLATION, "UNKNOWN_ACTION", "Unsupported action")

    return failure or result


__all__ = ["ModelCandidateValidationError", "validate_candidate_output"]
