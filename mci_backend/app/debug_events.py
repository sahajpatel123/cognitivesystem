from __future__ import annotations

"""Debug event and invariant result schemas for MCI.

No logic is defined here. These dataclasses are used by observability and audit
modules to record what happened during a request.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any, List


@dataclass
class InvariantResult:
    """Result of checking a single invariant.

    - invariant_id: stable identifier.
    - description: human-readable summary.
    - passed: True if invariant holds.
    - failure_reason: explanation only when passed is False.
    """

    invariant_id: str
    description: str
    passed: bool
    failure_reason: Optional[str] = None


@dataclass
class StageAuditEvent:
    """Audit of entering and exiting a stage for a request.

    Stages are: request_boundary, reasoning, memory_update, expression.
    """

    request_id: str
    session_id: str
    stage: Literal["request_boundary", "reasoning", "memory_update", "expression"]
    phase: Literal["enter", "exit"]
    success: bool
    failure_reason: Optional[str] = None


@dataclass
class RequestObservabilityRecord:
    """Top-level observability record for a single request.

    Contains:
    - request_id
    - session_id
    - timestamp (float seconds since epoch)
    - invariants: list of invariant results
    - stages: list of stage audit events
    - hard_failure_reason: set only when a hard error occurs
    """

    request_id: str
    session_id: str
    timestamp: float
    invariants: List[InvariantResult]
    stages: List[StageAuditEvent]
    hard_failure_reason: Optional[str] = None
