# Phase 8 — Step 3: Kill Switches & Emergency Controls (Deterministic, Fail-Closed)

## Purpose (Why)
- Provide a governed, lawful mechanism to halt or refuse operation under extraordinary conditions.
- Address systemic risk, governance intervention, legal/regulatory suspension, security compromise, or invalidated assumptions.
- Distinct from crashes/errors: emergency control is intentional, explicit, and accountable.

## Emergency States (Categorical, Bounded)
- `NORMAL_OPERATION`
  - Allowed: standard invocation per Phase 8 Steps 0–2; cognition may execute.
  - Forbidden: bypassing accountability/audit; emergency controls inactive.
  - In-flight: proceed normally.
- `INVOCATION_REFUSED`
  - Allowed: refuse new invocations deterministically; no cognition execution starts.
  - Forbidden: running cognition, triggering audits via new requests.
  - In-flight: none (new invocations blocked).
- `EXECUTION_HALTED`
  - Allowed: maintain integrity of existing artifacts; accountability/audit remain readable.
  - Forbidden: starting or continuing cognition; new invocations rejected; in-flight executions are aborted fail-closed.
  - Outputs: suppressed; aborts produce no user-visible output.
- `AUDIT_ONLY` (optional, conceptual)
  - Allowed: verdict-only external audit queries; no cognition or new decisions.
  - Forbidden: new decision invocations, internal audit replays triggered by externals, any artifact mutation.
- States are fixed, non-gradient, and non-heuristic; no soft transitions.

## Authority Model (Categorical, Non-Transitive)
- Authority classes (illustrative):
  - `GOVERNANCE_AUTHORITY`: may set emergency state.
  - `NONE`: default for all callers, users, operators, models, and UIs.
- Identity ≠ authority; ownership/operator status does not confer authority.
- Models, users, and operators have NO authority to trigger or disable emergency states.
- Authority is external, explicit, and non-delegable; no transitive escalation.

## Emergency Action Semantics (Deterministic, Fail-Closed)
- Activation:
  - If authority validation fails → REFUSE change, remain in current state.
  - On ambiguity or unknown state → HALT (treat as EXECUTION_HALTED).
- Effects:
  - New invocations: REFUSED in `INVOCATION_REFUSED`, `EXECUTION_HALTED`, and `AUDIT_ONLY` (except verdict-only queries in `AUDIT_ONLY`).
  - In-flight executions: aborted fail-closed in `EXECUTION_HALTED`; none start in `INVOCATION_REFUSED`.
  - Outputs: suppressed during halted/abort; no user-visible output on emergency abort.
  - Accountability: preserved; traces/evidence/attribution remain intact; no mutation.
- Transitions are explicit, categorical, and logged via existing accountability surfaces only if within allowed scope; no new artifact types are introduced.

## Accountability & Audit Relationship
- Emergency controls do NOT modify past decisions or artifacts.
- Aborts follow existing fail-closed paths, producing required attribution where applicable.
- Emergency state is auditable as a categorical system state; no explanations or reasoning are emitted.
- No hiding or erasure of traces, evidence, attribution, or audits.

## Failure & Ambiguity Handling
- Unknown state → treat as `EXECUTION_HALTED` (refuse/abort).
- Ambiguous transition request → REFUSE change and HALT if uncertainty remains.
- Authority validation failure → REFUSE; no state change.
- All failures fail-closed; no partial or best-effort transitions.

## Non-Goals
- No UI, dashboards, admin tools, or operator consoles.
- No automatic/metric-driven shutdown, heuristics, thresholds, or adaptive triggers.
- No retries, fallbacks, degradation modes, or selective user access.
- No changes to cognition, accountability, audit semantics, or Phase 7 guarantees.
- No performance or infra automation.

## Stability & Dependency
- Emergency semantics are STABLE once approved.
- Later Phase 8 steps depend on these definitions; changes require reopening Phase 8.
- Phase 9+ may consume these semantics but cannot alter them without reopening Phase 8.
