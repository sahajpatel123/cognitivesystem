from dataclasses import dataclass, field
from typing import NewType, Tuple, Optional

from .enums import (
    AccountabilityClass,
    AuditOutcome,
    BoundaryActivationType,
    BoundaryKey,
    DecisionCategory,
    FailureOrigin,
    FailureType,
    OutcomeDomain,
    RuleKey,
    PhaseStep,
    RuleEvidenceOutcome,
    TraceLifecycleStatus,
)
from .errors import (
    AuditNotReadyError,
    EvidenceMissingError,
    InvalidTraceError,
    AttributionMissingError,
)

RuleId = NewType("RuleId", str)
BoundaryId = NewType("BoundaryId", str)
TraceId = NewType("TraceId", str)
AttributionId = NewType("AttributionId", str)


@dataclass(frozen=True)
class RuleEvidenceRecord:
    trace_id: TraceId
    rule_key: RuleKey
    rule_id: RuleId
    outcome: RuleEvidenceOutcome
    phase_step: PhaseStep


@dataclass(frozen=True)
class BoundaryEvidenceRecord:
    trace_id: TraceId
    boundary_key: BoundaryKey
    boundary_id: BoundaryId
    boundary_type: BoundaryActivationType
    phase_step: PhaseStep


@dataclass(frozen=True)
class DecisionTrace:
    trace_id: TraceId
    lifecycle_status: TraceLifecycleStatus
    decision_category: DecisionCategory
    accountability_class: AccountabilityClass
    started_at: float
    monotonic_started_at: float
    ended_at: Optional[float]
    monotonic_ended_at: Optional[float]
    phase_steps: Tuple[PhaseStep, ...]
    rule_evidence: Tuple[RuleEvidenceRecord, ...] = field(default_factory=tuple)
    boundary_evidence: Tuple[BoundaryEvidenceRecord, ...] = field(default_factory=tuple)
    outcome_domains: Tuple[OutcomeDomain, ...] = field(default_factory=tuple)
    failure_attribution: Optional["FailureAttributionRecord"] = None

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise InvalidTraceError("Trace ID is required.")
        if not self.phase_steps:
            raise InvalidTraceError("At least one phase step marker is required.")
        if self.started_at <= 0 or self.monotonic_started_at <= 0:
            raise InvalidTraceError("Valid start timestamps are required.")
        if self.lifecycle_status not in TraceLifecycleStatus:
            raise InvalidTraceError("Lifecycle status is required.")
        if self.lifecycle_status in (TraceLifecycleStatus.COMPLETED, TraceLifecycleStatus.ABORTED):
            if self.ended_at is None or self.monotonic_ended_at is None:
                raise InvalidTraceError("Completed/aborted traces require end timestamps.")
            if self.ended_at <= self.started_at:
                raise InvalidTraceError("End time must be after start time.")
            if self.monotonic_ended_at <= self.monotonic_started_at:
                raise InvalidTraceError("Monotonic end time must be after start time.")
        # Ensure referenced steps are within the trace markers.
        for ev in self.rule_evidence:
            if ev.trace_id != self.trace_id:
                raise InvalidTraceError("Rule evidence trace_id mismatch.")
            if ev.phase_step not in self.phase_steps:
                raise InvalidTraceError("Rule evidence references missing phase step.")
        for ev in self.boundary_evidence:
            if ev.trace_id != self.trace_id:
                raise InvalidTraceError("Boundary evidence trace_id mismatch.")
            if ev.phase_step not in self.phase_steps:
                raise InvalidTraceError("Boundary evidence references missing phase step.")
        if self.failure_attribution:
            if self.failure_attribution.trace_id != self.trace_id:
                raise InvalidTraceError("Attribution trace_id mismatch.")
            if self.failure_attribution.accountability_class not in AccountabilityClass:
                raise InvalidTraceError("Invalid accountability class in attribution.")
            if self.failure_attribution.origin not in FailureOrigin:
                raise InvalidTraceError("Invalid origin in attribution.")
            if self.failure_attribution.failure_type not in FailureType:
                raise InvalidTraceError("Invalid failure_type in attribution.")


@dataclass(frozen=True)
class FailureAttributionRecord:
    attribution_id: AttributionId
    origin: FailureOrigin
    failure_type: FailureType
    accountability_class: AccountabilityClass
    trace_id: TraceId
    related_rules: Tuple[RuleId, ...] = field(default_factory=tuple)
    related_boundaries: Tuple[BoundaryId, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AuditReplayBundle:
    trace: DecisionTrace
    rule_evidence: Tuple[RuleEvidenceRecord, ...]
    boundary_evidence: Tuple[BoundaryEvidenceRecord, ...]
    attribution: Optional[FailureAttributionRecord]
    audit_outcome: Optional[AuditOutcome] = None

    def __post_init__(self) -> None:
        # Enforce alignment: evidence in bundle must match trace references.
        if self.rule_evidence != self.trace.rule_evidence or self.boundary_evidence != self.trace.boundary_evidence:
            raise AuditNotReadyError("Evidence in bundle must match trace references exactly.")
        if self.attribution and not (self.rule_evidence or self.boundary_evidence):
            raise AttributionMissingError("Attribution requires evidence.")
        if self.audit_outcome and self.audit_outcome not in AuditOutcome:
            raise AuditNotReadyError("Invalid audit outcome.")
