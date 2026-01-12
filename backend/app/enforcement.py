from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from .schemas import (
    CognitiveStyle,
    ExpressionPlan,
    Hypothesis,
    IntermediateAnswer,
    Intent,
    ReasoningOutput,
    RenderedMessage,
    UserMessage,
)


class ViolationClass(str, Enum):
    STRUCTURAL_VIOLATION = "STRUCTURAL_VIOLATION"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    SEMANTIC_CONTRACT_VIOLATION = "SEMANTIC_CONTRACT_VIOLATION"
    BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
    EXECUTION_CONSTRAINT_VIOLATION = "EXECUTION_CONSTRAINT_VIOLATION"
    EXTERNAL_DEPENDENCY_FAILURE = "EXTERNAL_DEPENDENCY_FAILURE"


class ViolationSeverity(str, Enum):
    FATAL = "FATAL"
    NON_FATAL = "NON_FATAL"


class EnforcementFailure(BaseModel):
    violation_class: ViolationClass
    severity: ViolationSeverity
    reason: str
    detail: Optional[Dict[str, Any]] = None


class EnforcementError(RuntimeError):
    def __init__(self, failure: EnforcementFailure) -> None:
        self.failure = failure
        super().__init__(failure.reason)


class ReasoningAdapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_message: UserMessage
    intent: Intent
    cognitive_style: CognitiveStyle
    session_summary: Dict[str, Any]
    current_hypotheses: list[Hypothesis]


class ExpressionAdapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_message: UserMessage
    cognitive_style: CognitiveStyle
    expression_plan: ExpressionPlan
    intermediate_answer: IntermediateAnswer


MAX_REASONING_TEXT_CHARS = 6000
MAX_EXPRESSION_TEXT_CHARS = 6000
MAX_REASONING_OUTPUT_CHARS = 12000
MAX_EXPRESSION_OUTPUT_CHARS = 6000
MAX_MESSAGE_LATENCY_MS = 30_000  # conceptual bound mirrors HTTP timeout

SEMANTIC_GUARD_PATTERNS = [
    r"\bI (?:remember|recall|will remember)\b",
    r"\bI (?:learned|learn)\b",
    r"\bI have (?:a )?memory\b",
    r"\bI am (?:an )?agent\b",
    r"\bI can change (?:the )?rules\b",
    r"\bI (?:store|kept) your data\b",
    r"\bI (?:updated|redefined) my constraints\b",
    r"\bautonomous\b",
]


def build_failure(
    violation_class: ViolationClass,
    reason: str,
    *,
    severity: ViolationSeverity = ViolationSeverity.FATAL,
    detail: Optional[Dict[str, Any]] = None,
) -> EnforcementError:
    failure = EnforcementFailure(
        violation_class=violation_class,
        severity=severity,
        reason=reason,
        detail=detail,
    )
    return EnforcementError(failure)


def _estimate_char_footprint(payload: Dict[str, Any]) -> int:
    def _flatten(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return " ".join(_flatten(v) for v in value.values())
        if isinstance(value, list):
            return " ".join(_flatten(v) for v in value)
        return ""

    return len(_flatten(payload))


def enforce_pre_call(
    call_type: Literal["reasoning", "expression"],
    adapter_input: BaseModel,
    *,
    now_ms: Optional[int] = None,
    call_budget_remaining: Optional[int] = None,
) -> None:
    if call_type not in {"reasoning", "expression"}:
        raise build_failure(
            ViolationClass.BOUNDARY_VIOLATION,
            f"Unknown call type: {call_type}",
        )

    payload = adapter_input.model_dump()

    char_limit = MAX_REASONING_TEXT_CHARS if call_type == "reasoning" else MAX_EXPRESSION_TEXT_CHARS
    char_footprint = _estimate_char_footprint(payload)
    if char_footprint > char_limit:
        raise build_failure(
            ViolationClass.EXECUTION_CONSTRAINT_VIOLATION,
            f"{call_type} adapter payload exceeds character budget",
            detail={"char_footprint": char_footprint, "limit": char_limit},
        )

    if call_budget_remaining is not None and call_budget_remaining <= 0:
        raise build_failure(
            ViolationClass.EXECUTION_CONSTRAINT_VIOLATION,
            f"{call_type} call budget exhausted",
        )

    if now_ms is not None and now_ms > MAX_MESSAGE_LATENCY_MS:
        raise build_failure(
            ViolationClass.EXECUTION_CONSTRAINT_VIOLATION,
            f"{call_type} runtime exceeded latency budget",
            detail={"latency_ms": now_ms, "limit_ms": MAX_MESSAGE_LATENCY_MS},
        )


def parse_reasoning_output(raw_content: str) -> ReasoningOutput:
    if len(raw_content) > MAX_REASONING_OUTPUT_CHARS:
        raise build_failure(
            ViolationClass.STRUCTURAL_VIOLATION,
            "Reasoning output exceeds maximum length",
            detail={"length": len(raw_content), "limit": MAX_REASONING_OUTPUT_CHARS},
        )

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise build_failure(
            ViolationClass.STRUCTURAL_VIOLATION,
            "Reasoning output is not valid JSON",
            detail={"content_snippet": raw_content[:200]},
        ) from exc

    try:
        return ReasoningOutput(**parsed)
    except ValidationError as exc:
        raise build_failure(
            ViolationClass.SCHEMA_MISMATCH,
            "Reasoning output failed schema validation",
            detail={"errors": exc.errors()},
        ) from exc


def validate_expression_output(
    raw_text: str,
    *,
    intermediate: IntermediateAnswer,
) -> RenderedMessage:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise build_failure(
            ViolationClass.STRUCTURAL_VIOLATION,
            "Expression output missing natural-language text",
        )

    if len(raw_text) > MAX_EXPRESSION_OUTPUT_CHARS:
        raise build_failure(
            ViolationClass.STRUCTURAL_VIOLATION,
            "Expression output exceeds maximum length",
            detail={"length": len(raw_text), "limit": MAX_EXPRESSION_OUTPUT_CHARS},
        )

    lowered = raw_text.lower()
    for pattern in SEMANTIC_GUARD_PATTERNS:
        if re.search(pattern, raw_text, flags=re.IGNORECASE):
            raise build_failure(
                ViolationClass.SEMANTIC_CONTRACT_VIOLATION,
                "Expression output made disallowed claims about capability or memory",
                detail={"pattern": pattern, "text_snippet": raw_text[:200]},
            )

    # Keep intermediate scope enforcement: ensure no unsupported strong-modality statements.
    keypoints_joined = " ".join(intermediate.key_points).lower()
    forbidden_terms = ["always", "never", "must", "best practice"]
    for term in forbidden_terms:
        if term in lowered and term not in keypoints_joined:
            raise build_failure(
                ViolationClass.SEMANTIC_CONTRACT_VIOLATION,
                "Expression output introduced unsupported strong-modality claims",
                detail={"term": term, "text_snippet": raw_text[:200]},
            )

    return RenderedMessage(text=raw_text.strip())
