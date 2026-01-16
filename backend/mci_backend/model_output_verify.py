"""Phase 12 — Step 5: Model output verifier & sanitizer (fail-closed)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from backend.mci_backend.control_plan import ControlPlan
from backend.mci_backend.decision_state import DecisionState
from backend.mci_backend.model_contract import ModelFailure, ModelFailureType, ModelInvocationResult
from backend.mci_backend.model_output_schema import (
    AnswerJSON,
    AskOneQuestionJSON,
    CloseJSON,
    ModelOutputParseError,
    ModelOutputSchemaViolation,
    RefusalJSON,
    parse_model_json,
    validate_answer_payload,
    validate_ask_payload,
    validate_close_payload,
    validate_refusal_payload,
)
from backend.mci_backend.model_verified_output import (
    VerifiedAnswer,
    VerifiedAsk,
    VerifiedClose,
    VerifiedRefusal,
)
from backend.mci_backend.output_plan import OutputAction, OutputPlan, UnknownDisclosureMode


class ModelOutputVerifyError(Exception):
    """Base verification error."""


class ModelOutputRejected(ModelOutputVerifyError):
    """Semantic violation."""


class ModelOutputSchemaError(ModelOutputVerifyError):
    """Schema or parsing mismatch."""


_FORBIDDEN_PHRASES = [
    "i remember",
    "as you said earlier",
    "previous conversation",
    "system prompt",
    "developer message",
    "i will change the rules",
    "override",
    "i will now do",
    "i'll keep checking",
    "i accessed",
    "i searched",
    "i called api",
    "i browsed",
    "i learned",
    "i updated my rules",
    "based on previous chats",
]

_ADVICE_PHRASES = ["you should", "you must", "you need to"]
_MULTI_QUESTION_HINTS = ["and also", "also", "plus", "another question", "as well"]


def _failure(request_id: str, failure_type: ModelFailureType, reason_code: str, message: str) -> ModelInvocationResult:
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


_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\u2060]")


def _sanitize_text(text: str) -> str:
    sanitized = _ZERO_WIDTH.sub("", text or "")
    sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")
    return sanitized.strip()


def _check_forbidden_phrases(text: str, request_id: str) -> Optional[ModelInvocationResult]:
    lowered = text.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in lowered:
            return _failure(request_id, ModelFailureType.FORBIDDEN_CONTENT, "FORBIDDEN_PHRASE", f"Forbidden phrase: {phrase}")
    return None


def _verify_action_alignment(action: OutputAction, payload: Dict[str, Any], request_id: str) -> Tuple[Any, Optional[ModelInvocationResult]]:
    try:
        if action == OutputAction.ANSWER:
            return validate_answer_payload(payload), None
        if action == OutputAction.ASK_ONE_QUESTION:
            return validate_ask_payload(payload), None
        if action == OutputAction.REFUSE:
            return validate_refusal_payload(payload), None
        if action == OutputAction.CLOSE:
            return validate_close_payload(payload), None
    except (ModelOutputSchemaViolation,) as exc:
        message = str(exc)
        if "Policy or loophole language forbidden" in message:
            return None, _failure(
                request_id,
                ModelFailureType.FORBIDDEN_CONTENT,
                "FORBIDDEN_CONTENT",
                message,
            )
        if "must not ask questions" in message:
            return None, _failure(
                request_id,
                ModelFailureType.CONTRACT_VIOLATION,
                "QUESTION_IN_CLOSE",
                message,
            )
        return None, _failure(request_id, ModelFailureType.SCHEMA_MISMATCH, "SCHEMA_MISMATCH", message)
    return None, _failure(request_id, ModelFailureType.CONTRACT_VIOLATION, "ACTION_MISMATCH", "Unsupported action")


def _verify_answer(
    answer: AnswerJSON,
    plan: OutputPlan,
    decision_state: DecisionState,
    request_id: str,
) -> Optional[ModelInvocationResult]:
    failure = _check_forbidden_phrases(answer.answer_text, request_id)
    if failure:
        return failure
    if plan.unknown_disclosure != UnknownDisclosureMode.NONE:
        lowered = answer.answer_text.lower()
        if all(token not in lowered for token in ["unknown", "uncertain", "not sure", "unclear", "cannot confirm"]):
            return _failure(
                request_id,
                ModelFailureType.CONTRACT_VIOLATION,
                "MISSING_UNKNOWN_DISCLOSURE",
                "Explicit unknown disclosure required",
            )
    if plan.unknown_disclosure == UnknownDisclosureMode.NONE and getattr(decision_state, "explicit_unknown_zone", ()):
        return _failure(
            request_id,
            ModelFailureType.CONTRACT_VIOLATION,
            "UNKNOWN_SUPPRESSED",
            "Unknowns present but disclosure set to NONE",
        )
    return None


def _verify_ask_one(ask: AskOneQuestionJSON, request_id: str) -> Optional[ModelInvocationResult]:
    q = ask.question.strip()
    lower_q = q.lower()
    for hint in _MULTI_QUESTION_HINTS:
        if hint in lower_q:
            return _failure(request_id, ModelFailureType.CONTRACT_VIOLATION, "MULTI_QUESTION", "Multi-question phrasing detected")
    for adv in _ADVICE_PHRASES:
        if adv in lower_q:
            return _failure(request_id, ModelFailureType.CONTRACT_VIOLATION, "QUESTION_CONTAINS_ADVICE", "Question must not include advice")
    return _check_forbidden_phrases(q, request_id)


def _verify_refusal(refusal: RefusalJSON, plan: OutputPlan, request_id: str) -> Optional[ModelInvocationResult]:
    failure = _check_forbidden_phrases(refusal.refusal_text, request_id)
    if failure:
        return failure
    if plan.refusal_spec and refusal.refusal_category != plan.refusal_spec.refusal_category:
        return _failure(request_id, ModelFailureType.CONTRACT_VIOLATION, "REFUSAL_CATEGORY_MISMATCH", "Refusal category mismatch")
    return None


def _verify_close(close: CloseJSON, request_id: str) -> Optional[ModelInvocationResult]:
    failure = _check_forbidden_phrases(close.closure_text, request_id)
    if failure:
        return failure
    if "?" in close.closure_text:
        return _failure(request_id, ModelFailureType.CONTRACT_VIOLATION, "QUESTION_IN_CLOSE", "Closure must not ask questions")
    return None


def verify_and_sanitize_model_output(
    *,
    model_result: ModelInvocationResult,
    output_plan: OutputPlan,
    decision_state: DecisionState,
    control_plan: ControlPlan,
    original_request_text: Optional[str] = None,
) -> ModelInvocationResult:
    request_id = model_result.request_id

    if not model_result.ok:
        return model_result

    try:
        payload = model_result.output_json if model_result.output_json is not None else parse_model_json(model_result.output_text or "")
    except ModelOutputParseError as exc:
        return _failure(request_id, ModelFailureType.NON_JSON, "NON_JSON", str(exc))

    validated, failure = _verify_action_alignment(output_plan.action, payload, request_id)
    if failure:
        return failure

    # semantic checks per action
    if isinstance(validated, AnswerJSON):
        failure = _verify_answer(validated, output_plan, decision_state, request_id)
        if failure:
            return failure
        sanitized_text = _sanitize_text(validated.answer_text)
        return ModelInvocationResult(
            request_id=request_id,
            ok=True,
            output_text=sanitized_text,
            output_json=None,
            failure=None,
        )

    if isinstance(validated, AskOneQuestionJSON):
        failure = _verify_ask_one(validated, request_id)
        if failure:
            return failure
        sanitized_question = _sanitize_text(validated.question)
        return ModelInvocationResult(
            request_id=request_id,
            ok=True,
            output_text=None,
            output_json={
                "question": sanitized_question,
                "question_class": validated.question_class.value,
                "priority_reason": validated.priority_reason.value,
            },
            failure=None,
        )

    if isinstance(validated, RefusalJSON):
        failure = _verify_refusal(validated, output_plan, request_id)
        if failure:
            return failure
        sanitized_text = _sanitize_text(validated.refusal_text)
        return ModelInvocationResult(
            request_id=request_id,
            ok=True,
            output_text=sanitized_text,
            output_json=None,
            failure=None,
        )

    if isinstance(validated, CloseJSON):
        failure = _verify_close(validated, request_id)
        if failure:
            return failure
        sanitized_text = _sanitize_text(validated.closure_text)
        return ModelInvocationResult(
            request_id=request_id,
            ok=True,
            output_text=sanitized_text,
            output_json=None,
            failure=None,
        )

    return _failure(request_id, ModelFailureType.CONTRACT_VIOLATION, "UNHANDLED_ACTION", "Unhandled action")


__all__ = [
    "ModelOutputVerifyError",
    "ModelOutputRejected",
    "ModelOutputSchemaError",
    "verify_and_sanitize_model_output",
]
