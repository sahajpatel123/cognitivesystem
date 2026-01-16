from __future__ import annotations

"""Passive observability for MCI.

This module records invariant results and stage audit events without
influencing behavior or responses.
"""

import time
import uuid
from typing import List

from .debug_events import RequestObservabilityRecord, InvariantResult, StageAuditEvent


# In-memory list of records for MCI. This is internal-only.
_RECORDS: List[RequestObservabilityRecord] = []


def new_request_id() -> str:
    return uuid.uuid4().hex


def start_request_record(request_id: str, session_id: str) -> RequestObservabilityRecord:
    record = RequestObservabilityRecord(
        request_id=request_id,
        session_id=session_id,
        timestamp=time.time(),
        invariants=[],
        stages=[],
        hard_failure_reason=None,
    )
    _RECORDS.append(record)
    return record


def add_invariants(record: RequestObservabilityRecord, results: List[InvariantResult]) -> None:
    record.invariants.extend(results)


def add_stage_event(record: RequestObservabilityRecord, event: StageAuditEvent) -> None:
    record.stages.append(event)


def set_hard_failure(record: RequestObservabilityRecord, reason: str) -> None:
    record.hard_failure_reason = reason


def get_records() -> List[RequestObservabilityRecord]:
    """Return all observability records.

    This is intended for internal debugging and audits.
    """
    return list(_RECORDS)
