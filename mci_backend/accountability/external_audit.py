from __future__ import annotations

"""
External audit interface (conceptual, verdict-only, read-only).

Constraints:
- No exposure of traces, evidence, attribution, reasoning, or model outputs.
- No re-execution or mutation.
- Deterministic categorical responses only.
"""

from .enums import AuditOutcome
from .types import AuditReplayBundle


class ExternalAuditQuestion:
    """Bounded external audit question classes."""

    PASS_STATUS = "pass_status"
    AUDITABLE = "auditable"
    INCONCLUSIVE_STATUS = "inconclusive_status"
    SCOPE_STATUS = "scope_status"

    ALLOWED = {
        PASS_STATUS,
        AUDITABLE,
        INCONCLUSIVE_STATUS,
        SCOPE_STATUS,
    }


class ExternalAuditVerdict:
    """Bounded external audit verdicts."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REFUSED = "REFUSED"

    ALLOWED = {PASS, FAIL, INCONCLUSIVE, NOT_APPLICABLE, REFUSED}


def _map_audit_outcome(outcome: AuditOutcome | None) -> str:
    if outcome is None:
        return ExternalAuditVerdict.INCONCLUSIVE
    if outcome is AuditOutcome.PASS:
        return ExternalAuditVerdict.PASS
    if outcome is AuditOutcome.INCONCLUSIVE:
        return ExternalAuditVerdict.INCONCLUSIVE
    # Any FAIL_* collapses to FAIL.
    return ExternalAuditVerdict.FAIL


def answer_external_audit(
    *,
    question: str,
    bundle: AuditReplayBundle | None,
    in_scope: bool = True,
    audit_outcome: AuditOutcome | None = None,
) -> str:
    """
    Provide a categorical external audit verdict without exposing artifacts.

    Deterministic mapping:
    - Unknown questions -> REFUSED
    - Out-of-scope -> NOT_APPLICABLE
    - Uses provided audit_outcome if given; otherwise uses bundle.audit_outcome.
    - Missing outcome -> INCONCLUSIVE (never PASS).
    """
    if question not in ExternalAuditQuestion.ALLOWED:
        return ExternalAuditVerdict.REFUSED

    if not in_scope:
        return ExternalAuditVerdict.NOT_APPLICABLE

    effective_outcome = audit_outcome
    if effective_outcome is None and bundle is not None:
        effective_outcome = bundle.audit_outcome

    if question == ExternalAuditQuestion.SCOPE_STATUS:
        # In-scope already validated; if outcome absent, still inconclusive.
        return _map_audit_outcome(effective_outcome)

    if question == ExternalAuditQuestion.AUDITABLE:
        # Auditability hinges on having an outcome at all.
        if effective_outcome is None:
            return ExternalAuditVerdict.INCONCLUSIVE
        return ExternalAuditVerdict.PASS

    if question == ExternalAuditQuestion.INCONCLUSIVE_STATUS:
        mapped = _map_audit_outcome(effective_outcome)
        return ExternalAuditVerdict.INCONCLUSIVE if mapped == ExternalAuditVerdict.INCONCLUSIVE else ExternalAuditVerdict.FAIL

    if question == ExternalAuditQuestion.PASS_STATUS:
        mapped = _map_audit_outcome(effective_outcome)
        if mapped == ExternalAuditVerdict.PASS:
            return ExternalAuditVerdict.PASS
        if mapped == ExternalAuditVerdict.INCONCLUSIVE:
            return ExternalAuditVerdict.INCONCLUSIVE
        return ExternalAuditVerdict.FAIL

    return ExternalAuditVerdict.REFUSED
