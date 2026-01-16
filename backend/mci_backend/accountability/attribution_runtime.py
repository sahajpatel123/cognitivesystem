from __future__ import annotations

"""
Deterministic, categorical failure attribution runtime.

Constraints:
- No reasoning, prompts, user text, or logs are inspected.
- No probabilities, heuristics, narratives, or causal inference.
- Attribution is categorical, bounded, and deterministic for identical inputs.
"""

import uuid
from typing import Tuple

from .enums import (
    AccountabilityClass,
    FailureOrigin,
    FailureType,
    RuleEvidenceOutcome,
    TraceLifecycleStatus,
)
from .types import DecisionTrace, FailureAttributionRecord, AttributionId
from .errors import InvalidTraceError


def _has_rule_fail(trace: DecisionTrace) -> bool:
    return any(ev.outcome is RuleEvidenceOutcome.FAIL for ev in trace.rule_evidence)


def _has_rule_evidence(trace: DecisionTrace) -> bool:
    return bool(trace.rule_evidence)


def _has_boundary_evidence(trace: DecisionTrace) -> bool:
    return bool(trace.boundary_evidence)


def _attribution_id(trace: DecisionTrace, payload: Tuple[str, ...]) -> AttributionId:
    # Deterministic ID derived from trace_id and categorical payload.
    seed = "|".join((trace.trace_id, *payload))
    return AttributionId(str(uuid.uuid5(uuid.NAMESPACE_URL, seed)))


def attribute_failure(trace: DecisionTrace) -> FailureAttributionRecord:
    """Produce a deterministic, bounded attribution record for an aborted decision."""
    if trace.lifecycle_status not in (TraceLifecycleStatus.STARTED, TraceLifecycleStatus.ABORTED):
        raise InvalidTraceError("Attribution can only be generated for active or aborted traces.")

    # Priority 1: missing evidence
    if not _has_rule_evidence(trace) and not _has_boundary_evidence(trace):
        payload = ("rule_enforcement", "omission", "within")
        return FailureAttributionRecord(
            attribution_id=_attribution_id(trace, payload),
            origin=FailureOrigin.RULE_ENFORCEMENT,
            failure_type=FailureType.OMISSION,
            accountability_class=AccountabilityClass.WITHIN_GUARANTEES,
            related_rules=(),
            related_boundaries=(),
            trace_id=trace.trace_id,
        )

    # Priority 2: explicit rule failure
    if _has_rule_fail(trace):
        failed_rules = tuple(ev.rule_id for ev in trace.rule_evidence if ev.outcome is RuleEvidenceOutcome.FAIL)
        payload = ("rule_enforcement", "inconsistency", "within", *failed_rules)
        return FailureAttributionRecord(
            attribution_id=_attribution_id(trace, payload),
            origin=FailureOrigin.RULE_ENFORCEMENT,
            failure_type=FailureType.INCONSISTENCY,
            accountability_class=AccountabilityClass.WITHIN_GUARANTEES,
            related_rules=failed_rules,
            related_boundaries=(),
            trace_id=trace.trace_id,
        )

    # Priority 3: boundary context present without explicit failure markers
    if _has_boundary_evidence(trace):
        related = tuple(ev.boundary_id for ev in trace.boundary_evidence)
        payload = ("boundary_activation", "ambiguity_exposure", "within", *related)
        return FailureAttributionRecord(
            attribution_id=_attribution_id(trace, payload),
            origin=FailureOrigin.BOUNDARY_ACTIVATION,
            failure_type=FailureType.AMBIGUITY_EXPOSURE,
            accountability_class=AccountabilityClass.WITHIN_GUARANTEES,
            related_rules=(),
            related_boundaries=related,
            trace_id=trace.trace_id,
        )

    # Fallback: unattributable/unknown within guarantees.
    payload = ("system_logic", "ambiguity_exposure", "within")
    return FailureAttributionRecord(
        attribution_id=_attribution_id(trace, payload),
        origin=FailureOrigin.SYSTEM_LOGIC,
        failure_type=FailureType.AMBIGUITY_EXPOSURE,
        accountability_class=AccountabilityClass.WITHIN_GUARANTEES,
        related_rules=(),
        related_boundaries=(),
        trace_id=trace.trace_id,
    )
