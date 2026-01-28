"""
Phase 17 Step 2: DecisionDelta Schema

Defines the patch-only DSL for deep-thinking pass outputs.
Only allowed fields may be patched; all others are forbidden.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional
from enum import Enum


# Action enum for decision patches (aligned with ChatAction)
class DecisionAction(str, Enum):
    """Allowed actions for decision patches."""
    ANSWER = "ANSWER"
    ASK_CLARIFY = "ASK_CLARIFY"
    REFUSE = "REFUSE"
    FALLBACK = "FALLBACK"


# Bounds for text fields (conservative)
MAX_ANSWER_CHARS = 1200
MAX_RATIONALE_CHARS = 600
MAX_CLARIFY_QUESTION_CHARS = 300
MAX_ALTERNATIVE_CHARS = 200
MAX_ALTERNATIVES_COUNT = 3


# Allowed patch paths (single source of truth)
ALLOWED_PATCH_PATHS = frozenset([
    "decision.action",
    "decision.answer",
    "decision.rationale",
    "decision.clarify_question",
    "decision.alternatives",
])


# Path specifications (type, bounds, constraints)
PATH_SPECS: Dict[str, Dict[str, Any]] = {
    "decision.action": {
        "type": "enum",
        "enum_values": frozenset([a.value for a in DecisionAction]),
    },
    "decision.answer": {
        "type": "string",
        "max_length": MAX_ANSWER_CHARS,
        "optional": True,
    },
    "decision.rationale": {
        "type": "string",
        "max_length": MAX_RATIONALE_CHARS,
        "optional": True,
    },
    "decision.clarify_question": {
        "type": "string",
        "max_length": MAX_CLARIFY_QUESTION_CHARS,
        "optional": True,
    },
    "decision.alternatives": {
        "type": "list",
        "item_type": "string",
        "max_items": MAX_ALTERNATIVES_COUNT,
        "max_item_length": MAX_ALTERNATIVE_CHARS,
        "optional": True,
    },
}


@dataclass(frozen=True)
class PatchOp:
    """
    A single patch operation.
    Only 'set' operation is supported.
    """
    op: Literal["set"]
    path: str
    value: Any

    def __post_init__(self) -> None:
        if self.op != "set":
            raise ValueError(f"Only 'set' operation is supported, got: {self.op}")
        if not isinstance(self.path, str):
            raise ValueError("path must be a string")


# DecisionDelta is a list of PatchOp
DecisionDelta = List[PatchOp]


def is_allowed_path(path: str) -> bool:
    """Check if a patch path is in the allowlist."""
    return path in ALLOWED_PATCH_PATHS


def get_path_spec(path: str) -> Optional[Dict[str, Any]]:
    """Get the specification for a patch path."""
    return PATH_SPECS.get(path)


# Forbidden path patterns (defensive check)
FORBIDDEN_PATH_PATTERNS = [
    "entitlement",
    "tier",
    "cap",
    "routing",
    "pass_count",
    "breaker",
    "budget",
    "clamp",
    "safety",
    "security",
    "header",
    "cookie",
    "auth",
    "token",
    "policy",
]


def is_forbidden_path(path: str) -> bool:
    """
    Check if a path matches forbidden patterns.
    This is a defensive check in addition to the allowlist.
    """
    path_lower = path.lower()
    return any(pattern in path_lower for pattern in FORBIDDEN_PATH_PATTERNS)
