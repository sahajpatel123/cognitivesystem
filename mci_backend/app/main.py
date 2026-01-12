from __future__ import annotations

"""Request boundary and orchestration for MCI.

Implements the minimal pipeline:
- Enforce request boundary (session_id + text required).
- Load session-local hypotheses.
- Run single reasoning stage.
- Apply clamped, non-deleting hypothesis update.
- Run single expression stage.
- Return final user-visible text only.

No features, no optimizations, no retries, no caching.

STEP C: Passive observability hooks are added here. They record invariant
results and stage audit events without changing behavior or outputs.
"""

from typing import Dict, Any

from .models import UserMessage
from . import memory, reasoning, expression, invariants
from . import audit, observability
from .debug_events import StageAuditEvent
from ..accountability import (
    AccountabilityClass,
    DecisionCategory,
    PhaseStep,
    RuleEvidenceOutcome,
    RuleKey,
    trace_runtime,
    evidence_runtime,
    attribution_runtime,
)


def handle_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a single user request.

    Contract mapping:
    - Requires session_id and text.
    - Treats session_id as opaque; no identity inference.
    - Uses only session-local hypotheses.
    - Returns only final user-visible text.
    """
    session_id_raw = payload.get("session_id")
    text_raw = payload.get("text")

    if session_id_raw is None or str(session_id_raw).strip() == "":
        raise ValueError("session_id is required")
    if text_raw is None or str(text_raw).strip() == "":
        raise ValueError("text is required")

    user = UserMessage(session_id=str(session_id_raw), text=str(text_raw))

    # Decision trace: must exist for the decision to proceed.
    trace = trace_runtime.create_trace(
        decision_category=DecisionCategory.UNSPECIFIED,
        accountability_class=AccountabilityClass.WITHIN_GUARANTEES,
        initial_phase_steps=(PhaseStep.PHASE6_STEP1,),
    )
    # Prepare for evidence emission (Phase 6 Step 2 markers).
    trace = trace_runtime.append_phase_steps(trace, (PhaseStep.PHASE6_STEP2,))

    # Observability: create request record and log request invariants.
    request_id = observability.new_request_id()
    record = observability.start_request_record(request_id, user.session_id)
    observability.add_invariants(record, audit.check_request_invariants(user))
    trace = evidence_runtime.append_rule_evidence(
        trace,
        rule_key=RuleKey.REQUEST_BOUNDARY,
        outcome=RuleEvidenceOutcome.PASS,
        phase_step=PhaseStep.PHASE6_STEP2,
    )

    try:
        # Stage: request boundary (enter/exit considered a single successful step).
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="request_boundary",
                phase="enter",
                success=True,
                failure_reason=None,
            ),
        )

        # Load current session-local hypotheses (TTL-bound).
        current_h = memory.load_hypotheses(user.session_id)

        # Stage: reasoning.
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="reasoning",
                phase="enter",
                success=True,
                failure_reason=None,
            ),
        )
        try:
            reasoning_out = reasoning.run_reasoning(user, current_h)
        except Exception as e:  # noqa: BLE001
            observability.add_stage_event(
                record,
                StageAuditEvent(
                    request_id=request_id,
                    session_id=user.session_id,
                    stage="reasoning",
                    phase="exit",
                    success=False,
                    failure_reason=str(e),
                ),
            )
            observability.set_hard_failure(record, str(e))
            raise
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="reasoning",
                phase="exit",
                success=True,
                failure_reason=None,
            ),
        )

        # Invariants: ensure a valid plan exists (hard-fail on violation) and record results.
        invariants.assert_stage_isolation(reasoning_out)
        observability.add_invariants(record, audit.check_reasoning_invariants(reasoning_out))
        trace = evidence_runtime.append_rule_evidence(
            trace,
            rule_key=RuleKey.REASONING_ISOLATION,
            outcome=RuleEvidenceOutcome.PASS,
            phase_step=PhaseStep.PHASE6_STEP2,
        )

        # Stage: memory update.
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="memory_update",
                phase="enter",
                success=True,
                failure_reason=None,
            ),
        )
        try:
            updated_h = memory.apply_clamped_update(current_h, reasoning_out.proposed_hypotheses)
            memory.save_hypotheses(updated_h)
        except Exception as e:  # noqa: BLE001
            observability.add_stage_event(
                record,
                StageAuditEvent(
                    request_id=request_id,
                    session_id=user.session_id,
                    stage="memory_update",
                    phase="exit",
                    success=False,
                    failure_reason=str(e),
                ),
            )
            observability.set_hard_failure(record, str(e))
            raise
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="memory_update",
                phase="exit",
                success=True,
                failure_reason=None,
            ),
        )
        observability.add_invariants(record, audit.check_memory_invariants(current_h, updated_h))
        trace = evidence_runtime.append_rule_evidence(
            trace,
            rule_key=RuleKey.MEMORY_UPDATE,
            outcome=RuleEvidenceOutcome.PASS,
            phase_step=PhaseStep.PHASE6_STEP2,
        )

        # Stage: expression.
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="expression",
                phase="enter",
                success=True,
                failure_reason=None,
            ),
        )
        try:
            reply = expression.render_reply(reasoning_out.plan)
        except Exception as e:  # noqa: BLE001
            observability.add_stage_event(
                record,
                StageAuditEvent(
                    request_id=request_id,
                    session_id=user.session_id,
                    stage="expression",
                    phase="exit",
                    success=False,
                    failure_reason=str(e),
                ),
            )
            observability.set_hard_failure(record, str(e))
            raise
        observability.add_stage_event(
            record,
            StageAuditEvent(
                request_id=request_id,
                session_id=user.session_id,
                stage="expression",
                phase="exit",
                success=True,
                failure_reason=None,
            ),
        )

        # Invariants: non-empty expression output and record expression invariants.
        invariants.assert_expression_non_empty(reply)
        observability.add_invariants(record, audit.check_expression_invariants(reply))
        trace = evidence_runtime.append_rule_evidence(
            trace,
            rule_key=RuleKey.EXPRESSION_NON_EMPTY,
            outcome=RuleEvidenceOutcome.PASS,
            phase_step=PhaseStep.PHASE6_STEP2,
        )

        # Close trace on successful completion.
        trace = trace_runtime.close_trace_completed(
            trace,
            additional_steps=(
                PhaseStep.PHASE6_STEP1,
            ),
        )

        # Response boundary: only user-visible text.
        return {"reply": reply.text}
    except Exception:
        # Fail-closed: abort trace and re-raise.
        attribution = attribution_runtime.attribute_failure(trace)
        trace = trace_runtime.attach_failure_attribution(trace, attribution)
        trace = trace_runtime.close_trace_aborted(
            trace,
            additional_steps=(
                PhaseStep.PHASE6_STEP1,
            ),
        )
        raise

