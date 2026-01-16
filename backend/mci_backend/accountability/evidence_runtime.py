from __future__ import annotations

"""
Runtime utilities for rule and boundary evidence emission.

Constraints:
- No persistence, logging, or external I/O.
- Evidence is categorical, bounded, and immutable after emission.
- Evidence never inspects reasoning, prompts, or user text.
- Fail-closed: invalid evidence aborts the decision.
"""

from dataclasses import replace
from typing import Iterable

from .enums import (
    BoundaryActivationType,
    BoundaryKey,
    PhaseStep,
    RuleEvidenceOutcome,
    RuleKey,
)
from .errors import InvalidTraceError
from .types import (
    BoundaryEvidenceRecord,
    DecisionTrace,
    RuleEvidenceRecord,
    RuleId,
    BoundaryId,
)


def _ensure_started(trace: DecisionTrace) -> None:
    from .enums import TraceLifecycleStatus  # local import to avoid cycles

    if trace.lifecycle_status is not TraceLifecycleStatus.STARTED:
        raise InvalidTraceError("Evidence cannot be emitted after trace closure.")


def append_rule_evidence(
    trace: DecisionTrace,
    *,
    rule_key: RuleKey,
    outcome: RuleEvidenceOutcome,
    phase_step: PhaseStep,
    rule_id: RuleId | None = None,
) -> DecisionTrace:
    """Emit categorical rule evidence bound to a trace."""
    _ensure_started(trace)
    if phase_step not in trace.phase_steps:
        raise InvalidTraceError("Rule evidence phase_step not recorded in trace.")
    rid = rule_id or RuleId(rule_key.name)
    new_record = RuleEvidenceRecord(
        trace_id=trace.trace_id,
        rule_key=rule_key,
        rule_id=rid,
        outcome=outcome,
        phase_step=phase_step,
    )
    for existing in trace.rule_evidence:
        if (
            existing.rule_key == new_record.rule_key
            and existing.rule_id == new_record.rule_id
            and existing.phase_step == new_record.phase_step
        ):
            raise InvalidTraceError("Duplicate rule evidence emission.")
    return replace(trace, rule_evidence=trace.rule_evidence + (new_record,))


def append_boundary_evidence(
    trace: DecisionTrace,
    *,
    boundary_key: BoundaryKey,
    boundary_type: BoundaryActivationType,
    phase_step: PhaseStep,
    boundary_id: BoundaryId | None = None,
) -> DecisionTrace:
    """Emit categorical boundary evidence bound to a trace."""
    _ensure_started(trace)
    if phase_step not in trace.phase_steps:
        raise InvalidTraceError("Boundary evidence phase_step not recorded in trace.")
    bid = boundary_id or BoundaryId(boundary_key.name)
    new_record = BoundaryEvidenceRecord(
        trace_id=trace.trace_id,
        boundary_key=boundary_key,
        boundary_id=bid,
        boundary_type=boundary_type,
        phase_step=phase_step,
    )
    for existing in trace.boundary_evidence:
        if (
            existing.boundary_key == new_record.boundary_key
            and existing.boundary_id == new_record.boundary_id
            and existing.phase_step == new_record.phase_step
        ):
            raise InvalidTraceError("Duplicate boundary evidence emission.")
    return replace(trace, boundary_evidence=trace.boundary_evidence + (new_record,))


def assert_evidence_non_empty(trace: DecisionTrace) -> None:
    """Fail-closed if trace lacks evidence."""
    if not trace.rule_evidence and not trace.boundary_evidence:
        raise InvalidTraceError("Trace lacks required rule or boundary evidence.")
