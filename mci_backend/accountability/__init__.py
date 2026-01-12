"""
Phase 7 scaffolding package for accountability types and invariants.

This module exposes only structural contracts (enums, dataclasses, errors)
and contains no runtime behavior, logging, or model interaction.
"""

from .enums import (
    AccountabilityClass,
    AuditOutcome,
    BoundaryActivationType,
    DecisionCategory,
    BoundaryKey,
    RuleKey,
    FailureOrigin,
    FailureType,
    OutcomeDomain,
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
from .types import (
    BoundaryEvidenceRecord,
    DecisionTrace,
    FailureAttributionRecord,
    RuleEvidenceRecord,
    AuditReplayBundle,
)
from . import trace_runtime, evidence_runtime, attribution_runtime
from . import audit_runtime, external_audit

__all__ = [
    "AccountabilityClass",
    "AuditOutcome",
    "BoundaryActivationType",
    "DecisionCategory",
    "BoundaryKey",
    "RuleKey",
    "FailureOrigin",
    "FailureType",
    "OutcomeDomain",
    "PhaseStep",
    "RuleEvidenceOutcome",
    "TraceLifecycleStatus",
    "AuditNotReadyError",
    "EvidenceMissingError",
    "InvalidTraceError",
    "AttributionMissingError",
    "BoundaryEvidenceRecord",
    "DecisionTrace",
    "FailureAttributionRecord",
    "RuleEvidenceRecord",
    "AuditReplayBundle",
    "trace_runtime",
    "evidence_runtime",
    "attribution_runtime",
    "audit_runtime",
    "external_audit",
]
