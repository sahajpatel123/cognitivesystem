from __future__ import annotations

from backend.app.chat_contract import ChatAction, FailureType as ContractFailureType


def map_action_to_contract(action: str) -> ChatAction:
    return ChatAction(action)


def map_failure_to_contract(failure: str | None) -> ContractFailureType | None:
    if failure is None:
        return None
    try:
        return ContractFailureType(failure)
    except Exception:
        return ContractFailureType.INTERNAL_ERROR_SANITIZED


__all__ = ["map_action_to_contract", "map_failure_to_contract"]
