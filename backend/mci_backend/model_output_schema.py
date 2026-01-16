"""Phase 12 — Step 4: Strict JSON output schemas (edge contract)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.mci_backend.control_plan import ClosureState, QuestionClass, RefusalCategory
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason


class ModelOutputSchemaError(Exception):
    """Base schema error."""


class ModelOutputParseError(ModelOutputSchemaError):
    """Raised when raw text is not valid JSON object."""


class ModelOutputSchemaViolation(ModelOutputSchemaError):
    """Raised when payload violates structured schema."""


MAX_TEXT_LEN = 6000
MAX_LIST_LEN = 10
MAX_LIST_ITEM_LEN = 400
MAX_QUESTION_LEN = 500
_MULTI_Q_PATTERN = re.compile(r"\?.*[\n\r].*\?|\\?\\s+and\\s+\\?", re.IGNORECASE)


def parse_model_json(raw_text: str) -> Dict[str, Any]:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ModelOutputParseError("Output must be non-empty string containing JSON")
    if raw_text.strip().startswith("```"):
        raise ModelOutputParseError("Markdown fenced code blocks are forbidden")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ModelOutputParseError(f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ModelOutputParseError("Top-level JSON must be an object")
    return parsed


class AnswerJSON(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    answer_text: str = Field(min_length=1, max_length=MAX_TEXT_LEN)
    assumptions: Optional[List[str]] = None
    unknowns: Optional[List[str]] = None

    @model_validator(mode="after")
    def _bounds(self) -> "AnswerJSON":
        for field_name in ("assumptions", "unknowns"):
            items = getattr(self, field_name)
            if items is None:
                continue
            if len(items) > MAX_LIST_LEN:
                raise ValueError(f"{field_name} length exceeds {MAX_LIST_LEN}")
            for item in items:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(f"{field_name} items must be non-empty strings")
                if len(item) > MAX_LIST_ITEM_LEN:
                    raise ValueError(f"{field_name} item exceeds {MAX_LIST_ITEM_LEN}")
        return self


class AskOneQuestionJSON(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=MAX_QUESTION_LEN)
    question_class: QuestionClass
    priority_reason: QuestionPriorityReason

    @model_validator(mode="after")
    def _single_question(self) -> "AskOneQuestionJSON":
        q = self.question.strip()
        # must include a single question mark
        if q.count("?") != 1:
            raise ValueError("Question must contain exactly one question mark")
        if _MULTI_Q_PATTERN.search(q):
            raise ValueError("Multi-question phrasing detected")
        return self


class RefusalJSON(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    refusal_category: RefusalCategory
    refusal_text: str = Field(min_length=1, max_length=MAX_TEXT_LEN)
    safe_next_step: Optional[str] = Field(default=None, max_length=MAX_TEXT_LEN)

    @model_validator(mode="after")
    def _check_policy_language(self) -> "RefusalJSON":
        lowered = self.refusal_text.lower()
        for banned in ("as an ai model", "policy"):
            if banned in lowered:
                raise ValueError("Policy or loophole language forbidden in refusal_text")
        if self.safe_next_step:
            if not self.safe_next_step.strip():
                raise ValueError("safe_next_step, if provided, must be non-empty")
        return self


class CloseJSON(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    closure_state: ClosureState
    closure_text: str = Field(default="", max_length=MAX_TEXT_LEN)

    @model_validator(mode="after")
    def _closure_rules(self) -> "CloseJSON":
        if self.closure_state != ClosureState.CLOSING and not self.closure_text:
            raise ValueError("Non-silence closure requires text")
        if "?" in self.closure_text:
            raise ValueError("Closure must not ask questions")
        return self


def validate_answer_payload(payload: Dict[str, Any]) -> AnswerJSON:
    try:
        return AnswerJSON(**payload)
    except ValidationError as exc:
        raise ModelOutputSchemaViolation(str(exc)) from exc


def validate_ask_payload(payload: Dict[str, Any]) -> AskOneQuestionJSON:
    try:
        return AskOneQuestionJSON(**payload)
    except ValidationError as exc:
        raise ModelOutputSchemaViolation(str(exc)) from exc


def validate_refusal_payload(payload: Dict[str, Any]) -> RefusalJSON:
    try:
        return RefusalJSON(**payload)
    except ValidationError as exc:
        raise ModelOutputSchemaViolation(str(exc)) from exc


def validate_close_payload(payload: Dict[str, Any]) -> CloseJSON:
    try:
        return CloseJSON(**payload)
    except ValidationError as exc:
        raise ModelOutputSchemaViolation(str(exc)) from exc


__all__ = [
    "ModelOutputSchemaError",
    "ModelOutputParseError",
    "ModelOutputSchemaViolation",
    "parse_model_json",
    "validate_answer_payload",
    "validate_ask_payload",
    "validate_refusal_payload",
    "validate_close_payload",
    "AnswerJSON",
    "AskOneQuestionJSON",
    "RefusalJSON",
    "CloseJSON",
]
