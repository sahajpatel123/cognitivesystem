# Phase 14 — Step 6: Governance Failure Drills (Kill-Switch & Integrity Scenarios)

Status: Defined (doc-only, no runtime changes)

## (A) Purpose
- Define governance failure drills to validate deployment-level trust boundaries defined in Phase 8 (doc-only).
- Ensure fail-closed behavior when integrity is invalid or unverifiable, or when emergency states are invoked.
- Provide categorical, deterministic expectations for refusal/halt/audit-only states without changing runtime (Phases 1–13 remain locked).

## (B) Governance Failure Taxonomy
- Integrity states: `INTEGRITY_VALID`, `INTEGRITY_INVALID`, `INTEGRITY_UNVERIFIABLE`
- Emergency states: `NORMAL_OPERATION`, `INVOCATION_REFUSED`, `EXECUTION_HALTED`, `AUDIT_ONLY`
- Authority failures: `UNKNOWN_AUTHORITY`, `INVALID_AUTHORITY`, `MISSING_AUTHORITY_PROOF`, `AMBIGUOUS_STATE`

## (C) Drill Catalog (12 drills)
Each drill lists Preconditions / Stimulus / Expected System Action (categorical) / Expected Invariants / Failure Classification / Evidence.

### Category A — Integrity/Certification
1) **A1 Integrity Invalid**
   - Preconditions: Integrity state flagged `INTEGRITY_INVALID`.
   - Stimulus: Invocation request received.
   - Expected Action: `INVOCATION_REFUSED` (fail-closed, no cognition/model invocation).
   - Invariants: No model call; no control/output assembly; no user-facing reasoning; categorical refusal only.
   - Failure Classification: `INTEGRITY_INVALID_REFUSAL`.
   - Evidence: Single categorical refusal event; no payload beyond action/reason code.

2) **A2 Integrity Unverifiable**
   - Preconditions: Integrity check cannot be performed (`INTEGRITY_UNVERIFIABLE`).
   - Stimulus: Invocation request received.
   - Expected Action: `INVOCATION_REFUSED`.
   - Invariants: No best-effort answering; no partial pipelines; no leakage of integrity diagnostics.
   - Failure Classification: `INTEGRITY_UNVERIFIABLE_REFUSAL`.
   - Evidence: Refusal event with reason code only; no model I/O.

3) **A3 Integrity Valid → Normal**
   - Preconditions: `INTEGRITY_VALID`, emergency state `NORMAL_OPERATION`.
   - Stimulus: Invocation request.
   - Expected Action: Proceed per certified pipeline (reference phases 9–12) without alteration.
   - Invariants: Integrity metadata not exposed to UI; governance boundary unchanged.
   - Failure Classification: `UNEXPECTED_REFUSAL_WHEN_VALID` if blocked.
   - Evidence: Normal governed response; no extra integrity fields leaked.

### Category B — Emergency States
4) **B1 Emergency Refuse**
   - Preconditions: Emergency state set to `INVOCATION_REFUSED`.
   - Stimulus: Invocation request.
   - Expected Action: `INVOCATION_REFUSED` (categorical refusal).
   - Invariants: No cognition/model invocation; no control/output assembly.
   - Failure Classification: `EMERGENCY_REFUSE_BREACH` if any pipeline runs.
   - Evidence: Refusal event only.

5) **B2 Emergency Halt**
   - Preconditions: Emergency state set to `EXECUTION_HALTED`.
   - Stimulus: Invocation request.
   - Expected Action: `EXECUTION_HALTED` (hard stop, no further processing).
   - Invariants: No decision/control/output plans; no model calls; no retry suggestion.
   - Failure Classification: `EMERGENCY_HALT_BREACH`.
   - Evidence: Halt marker only.

6) **B3 Emergency Audit-Only**
   - Preconditions: Emergency state set to `AUDIT_ONLY`.
   - Stimulus: Invocation request.
   - Expected Action: `AUDIT_ONLY` path: record minimal categorical evidence; no cognition/model; no user answer.
   - Invariants: No rendered text; no JSON answers; audit record only.
   - Failure Classification: `AUDIT_ONLY_BREACH`.
   - Evidence: Audit event with reason code; no user-visible answer beyond categorical notice.

### Category C — Authority Boundary Failures
7) **C1 Unknown Authority**
   - Preconditions: Authority actor not recognized (`UNKNOWN_AUTHORITY`).
   - Stimulus: Authority command to change state/integrity.
   - Expected Action: Reject command; remain in prior safe state.
   - Invariants: No state change; log categorical rejection only.
   - Failure Classification: `AUTHORITY_UNKNOWN_REJECTED`.
   - Evidence: Rejection event; no mutation.

8) **C2 Invalid Authority Proof**
   - Preconditions: Proof provided but invalid (`INVALID_AUTHORITY`).
   - Stimulus: Authority command to change emergency state.
   - Expected Action: Reject; remain safe.
   - Invariants: No state change; no partial application; no hints on proof structure.
   - Failure Classification: `AUTHORITY_INVALID_PROOF_REJECTED`.
   - Evidence: Rejection event only.

9) **C3 Missing Authority Proof**
   - Preconditions: Command lacks proof (`MISSING_AUTHORITY_PROOF`).
   - Stimulus: Attempted state change.
   - Expected Action: Reject; remain safe; prompt for proper authority out-of-band.
   - Invariants: No state change; no pipeline execution.
   - Failure Classification: `AUTHORITY_MISSING_PROOF_REJECTED`.
   - Evidence: Rejection event only.

### Category D — Audit-Only Semantics
10) **D1 Audit-Only Invocation**
    - Preconditions: Emergency state `AUDIT_ONLY`, integrity valid.
    - Stimulus: Standard user invocation.
    - Expected Action: No cognition/model; record audit event; user-facing notice of audit-only mode.
    - Invariants: No model prompts; no decision/control/output plans; no text/JSON answers.
    - Failure Classification: `AUDIT_ONLY_OUTPUT_BREACH` if any output rendered.
    - Evidence: Audit event with categorical code.

### Category E — Recovery Discipline
11) **E1 Recovery to Normal Requires Authority**
    - Preconditions: Emergency state not NORMAL; valid authority proof available.
    - Stimulus: Authority command to return to `NORMAL_OPERATION`.
    - Expected Action: Transition to NORMAL only after categorical authority validation.
    - Invariants: No automatic recovery; no inferred authority; deterministic acceptance criteria.
    - Failure Classification: `UNAUTHORIZED_RECOVERY_BREACH`.
    - Evidence: Authority validation event; state transition event.

12) **E2 Ambiguous Governance State**
    - Preconditions: Conflicting signals (e.g., simultaneous HALT and AUDIT markers) → `AMBIGUOUS_STATE`.
    - Stimulus: Invocation request.
    - Expected Action: Treat as unsafe → `EXECUTION_HALTED`.
    - Invariants: No cognition/model; no partial responses; ambiguity resolves to halt.
    - Failure Classification: `AMBIGUOUS_STATE_HALTED`.
    - Evidence: Halt event noting ambiguity (categorical only).

## (D) Fail-Closed Invariants (Hard Requirements)
- Ambiguous or unknown governance state → HALT.
- Invalid or unverifiable integrity → refuse invocations (no cognition/model path).
- In AUDIT_ONLY → no cognition/model invocation; verdict-only external audit; no user answers.
- No traces/evidence/attribution leak to UI beyond categorical failure/notice codes.
- No "best effort" answering under any governance failure.

## (E) Drill Execution Protocol (Manual)
- Environment: staging with controlled feature flags; no production traffic.
- Simulation: manually set integrity/emergency/authority flags via staging control plane or mocks (Phase 14-only tooling; not production code).
- Procedure (per drill):
  1) Set preconditions (integrity/emergency/authority) using staging controls.
  2) Issue the stimulus (e.g., user invocation or authority command).
  3) Capture evidence: categorical event/log only (per failure classification). No user text, no model outputs.
  4) Verify invariants: no model invocation; no plan assembly; terminal/notice-only UI if applicable.
- Monitoring/Evidence: categorical events, minimal counters; no metrics-based auto-triggers; no user-text telemetry.
- Rollback: reset flags manually to `NORMAL_OPERATION` only with validated authority proof.

## (F) Not Covered Here
- Dashboarding or operator UX
- Metrics-based auto-triggers or automated kill switches
- Infra/ops integrations (e.g., load balancers, circuit breakers)
- Any runtime code changes to orchestrator/model/UI

## (G) Stability Marker
This document locks governance failure drill semantics for Phase 14 Step 6. Any change requires reopening Phase 14 Step 6 and may trigger Phase 8 (deployment governance) review.
