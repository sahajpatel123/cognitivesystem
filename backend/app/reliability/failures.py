from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.app.chat_contract import ChatAction, FailureType as ContractFailureType


class Action(str, Enum):
    ANSWER = "ANSWER"
    ANSWER_DEGRADED = "ANSWER_DEGRADED"
    ASK_CLARIFY = "ASK_CLARIFY"
    FAIL_GRACEFULLY = "FAIL_GRACEFULLY"
    BLOCK = "BLOCK"


class FailureType(str, Enum):
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    TIMEOUT = "TIMEOUT"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_AUTH_ERROR = "PROVIDER_AUTH_ERROR"
    PROVIDER_BAD_RESPONSE = "PROVIDER_BAD_RESPONSE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"


@dataclass
class FailureInfo:
    failure_type: FailureType
    reason: str
    action: Action
    status_code: int = 200


@dataclass
class OutcomeMeta:
    attempt_index: int
    route_class: str
    effective_mode: str
    action: Action
    failure_type: Optional[FailureType] = None
    failure_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    breaker_open: bool = False
    budget_blocked: bool = False


def _map_failure(ft: Optional[FailureType]) -> Optional[ContractFailureType]:
    if ft is None:
        return None
    mapping = {
        FailureType.INTERNAL_ERROR: ContractFailureType.INTERNAL_ERROR_SANITIZED,
        FailureType.VALIDATION_ERROR: ContractFailureType.REQUEST_SCHEMA_INVALID,
        FailureType.PROVIDER_TIMEOUT: ContractFailureType.PROVIDER_TIMEOUT,
        FailureType.TIMEOUT: ContractFailureType.TIMEOUT,
        FailureType.PROVIDER_RATE_LIMIT: ContractFailureType.PROVIDER_RATE_LIMIT,
        FailureType.PROVIDER_AUTH_ERROR: ContractFailureType.PROVIDER_AUTH_ERROR,
        FailureType.PROVIDER_BAD_RESPONSE: ContractFailureType.PROVIDER_BAD_RESPONSE,
        FailureType.BUDGET_EXCEEDED: ContractFailureType.BUDGET_EXCEEDED,
        FailureType.CIRCUIT_OPEN: ContractFailureType.CIRCUIT_OPEN,
        FailureType.SAFETY_BLOCKED: ContractFailureType.SAFETY_BLOCKED,
    }
    return mapping.get(ft)


def _map_action(action: Action) -> ChatAction:
    mapping = {
        Action.ANSWER: ChatAction.ANSWER,
        Action.ANSWER_DEGRADED: ChatAction.ANSWER_DEGRADED,
        Action.ASK_CLARIFY: ChatAction.ASK_CLARIFY,
        Action.FAIL_GRACEFULLY: ChatAction.FAIL_GRACEFULLY,
        Action.BLOCK: ChatAction.BLOCK,
    }
    return mapping[action]


def to_public_error(info: FailureInfo) -> tuple[ChatAction, Optional[ContractFailureType], str]:
    action = _map_action(info.action)
    failure = _map_failure(info.failure_type)
    reason = info.reason[:200]
    return action, failure, reason


__all__ = ["Action", "FailureType", "FailureInfo", "OutcomeMeta", "to_public_error"]
