from __future__ import annotations

"""
Runtime utilities for decision trace lifecycle.

Constraints:
- No persistence, logging, or external I/O.
- No reasoning, prompts, or user text captured.
- Fail-closed: inability to create or close a trace must abort the decision.
"""

import time
import uuid
from dataclasses import replace
from typing import Iterable, Tuple

from .enums import (
    AccountabilityClass,
    DecisionCategory,
    PhaseStep,
    TraceLifecycleStatus,
)
from .errors import InvalidTraceError
from .types import DecisionTrace, TraceId, FailureAttributionRecord
from . import evidence_runtime


def _generate_trace_id() -> TraceId:
    try:
        return TraceId(str(uuid.uuid4()))
    except Exception as exc:  # noqa: BLE001
        raise InvalidTraceError("Failed to generate trace ID.") from exc


def _now_pair() -> Tuple[float, float]:
    try:
        return time.time(), time.monotonic()
    except Exception as exc:  # noqa: BLE001
        raise InvalidTraceError("Failed to read time sources.") from exc


def create_trace(
    *,
    decision_category: DecisionCategory = DecisionCategory.UNSPECIFIED,
    accountability_class: AccountabilityClass = AccountabilityClass.WITHIN_GUARANTEES,
    initial_phase_steps: Iterable[PhaseStep] | None = None,
) -> DecisionTrace:
    """Create a new trace at decision start. Fail-closed on error."""
    started_at, monotonic_started_at = _now_pair()
    phase_steps = tuple(initial_phase_steps) if initial_phase_steps else (PhaseStep.PHASE6_STEP1,)
    trace_id = _generate_trace_id()
    trace = DecisionTrace(
        trace_id=trace_id,
        lifecycle_status=TraceLifecycleStatus.STARTED,
        decision_category=decision_category,
        accountability_class=accountability_class,
        started_at=started_at,
        monotonic_started_at=monotonic_started_at,
        ended_at=None,
        monotonic_ended_at=None,
        phase_steps=phase_steps,
        rule_evidence=(),
        boundary_evidence=(),
        outcome_domains=(),
    )
    return trace


def append_phase_steps(trace: DecisionTrace, steps: Iterable[PhaseStep]) -> DecisionTrace:
    """Append phase steps during construction; forbidden after closure."""
    if trace.lifecycle_status is not TraceLifecycleStatus.STARTED:
        raise InvalidTraceError("Cannot append phase steps after trace closure.")
    new_steps = trace.phase_steps + tuple(step for step in steps if step not in trace.phase_steps)
    return replace(trace, phase_steps=new_steps)


def attach_failure_attribution(trace: DecisionTrace, attribution: FailureAttributionRecord) -> DecisionTrace:
    """Bind a failure attribution to a trace before closure."""
    if trace.lifecycle_status is not TraceLifecycleStatus.STARTED:
        raise InvalidTraceError("Cannot attach attribution after trace closure.")
    if attribution.trace_id != trace.trace_id:
        raise InvalidTraceError("Attribution trace_id mismatch.")
    if trace.failure_attribution is not None:
        raise InvalidTraceError("Failure attribution already attached.")
    return replace(trace, failure_attribution=attribution)


def close_trace_completed(trace: DecisionTrace, *, additional_steps: Iterable[PhaseStep] | None = None) -> DecisionTrace:
    """Close a trace as completed; immutable close."""
    if trace.lifecycle_status is not TraceLifecycleStatus.STARTED:
        raise InvalidTraceError("Trace already closed.")
    evidence_runtime.assert_evidence_non_empty(trace)
    ended_at, monotonic_ended_at = _now_pair()
    phase_steps = trace.phase_steps
    if additional_steps:
        phase_steps = trace.phase_steps + tuple(step for step in additional_steps if step not in trace.phase_steps)
    return replace(
        trace,
        lifecycle_status=TraceLifecycleStatus.COMPLETED,
        ended_at=ended_at,
        monotonic_ended_at=monotonic_ended_at,
        phase_steps=phase_steps,
    )


def close_trace_aborted(trace: DecisionTrace, *, additional_steps: Iterable[PhaseStep] | None = None) -> DecisionTrace:
    """Close a trace as aborted; immutable close."""
    if trace.lifecycle_status is not TraceLifecycleStatus.STARTED:
        raise InvalidTraceError("Trace already closed.")
    evidence_runtime.assert_evidence_non_empty(trace)
    if trace.failure_attribution is None:
        raise InvalidTraceError("Aborted trace requires failure attribution.")
    ended_at, monotonic_ended_at = _now_pair()
    phase_steps = trace.phase_steps
    if additional_steps:
        phase_steps = trace.phase_steps + tuple(step for step in additional_steps if step not in trace.phase_steps)
    return replace(
        trace,
        lifecycle_status=TraceLifecycleStatus.ABORTED,
        ended_at=ended_at,
        monotonic_ended_at=monotonic_ended_at,
        phase_steps=phase_steps,
    )
