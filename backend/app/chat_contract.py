from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator


MAX_USER_TEXT_CHARS = 2000
MAX_PAYLOAD_BYTES = 16_384  # 16KB
MAX_FAILURE_REASON_CHARS = 200


class ChatAction(str, Enum):
    ANSWER = "ANSWER"
    ASK_ONE_QUESTION = "ASK_ONE_QUESTION"
    REFUSE = "REFUSE"
    CLOSE = "CLOSE"
    FALLBACK = "FALLBACK"


class FailureType(str, Enum):
    REQUEST_SCHEMA_INVALID = "REQUEST_SCHEMA_INVALID"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    EMPTY_INPUT = "EMPTY_INPUT"
    MODEL_FAILED_FALLBACK_USED = "MODEL_FAILED_FALLBACK_USED"
    GOVERNED_PIPELINE_ABORTED = "GOVERNED_PIPELINE_ABORTED"
    INTERNAL_ERROR_SANITIZED = "INTERNAL_ERROR_SANITIZED"
    TIMEOUT = "TIMEOUT"


class ChatRequest(BaseModel):
    user_text: StrictStr = Field(..., min_length=1, max_length=MAX_USER_TEXT_CHARS)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _strip_and_require(cls, values: dict) -> dict:
        if isinstance(values, dict) and "user_text" in values and isinstance(values["user_text"], str):
            values = {**values, "user_text": values["user_text"].strip()}
        return values


class ChatResponse(BaseModel):
    action: ChatAction
    rendered_text: StrictStr
    failure_type: Optional[FailureType] = None
    failure_reason: Optional[StrictStr] = Field(default=None, max_length=MAX_FAILURE_REASON_CHARS)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _ensure_rendered_text(self) -> "ChatResponse":
        if self.failure_type is None and (not isinstance(self.rendered_text, str) or not self.rendered_text.strip()):
            raise ValueError("rendered_text required for successful responses")
        return self


class ExpressionPlan(BaseModel):
    steps: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
