from __future__ import annotations

"""
Deterministic audit replay engine.

Constraints:
- Uses only pre-recorded artifacts (trace, evidence, attribution).
- Never re-executes cognition or models.
- No mutation, no logging, no persistence.
- Outcomes are categorical and bounded.
"""

from .enums import AuditOutcome, TraceLifecycleStatus
from .types import AuditReplayBundle, DecisionTrace


def _trace_closed_once(trace: DecisionTrace) -> bool:
    return trace.lifecycle_status in (TraceLifecycleStatus.COMPLETED, TraceLifecycleStatus.ABORTED)


def replay_audit(bundle: AuditReplayBundle) -> AuditOutcome:
    """Verify artifact consistency and return categorical audit outcome."""
    trace = bundle.trace

    # Lifecycle must be closed and valid.
    if not _trace_closed_once(trace):
        return AuditOutcome.FAIL_INCONSISTENCY

    # Evidence completeness: rule or boundary evidence must exist and align.
    if not trace.rule_evidence and not trace.boundary_evidence:
        return AuditOutcome.FAIL_MISSING_EVIDENCE

    # Bundle alignment: evidence must exactly match trace (checked in __post_init__).
    # Attribution consistency.
    if trace.lifecycle_status is TraceLifecycleStatus.ABORTED:
        if bundle.attribution is None or trace.failure_attribution is None:
            return AuditOutcome.FAIL_MISSING_EVIDENCE
        if bundle.attribution != trace.failure_attribution:
            return AuditOutcome.FAIL_INCONSISTENCY
    else:
        # COMPLETED: attribution optional but if present must align.
        if bundle.attribution is not None and bundle.attribution != trace.failure_attribution:
            return AuditOutcome.FAIL_INCONSISTENCY

    # If we reach here, artifacts are present and internally consistent.
    return AuditOutcome.PASS
