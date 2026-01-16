# Phase 15 — Step 0: Production Scope Lock
Status: **LOCKED**
Date: 2026-01-15

This document is normative; violating it voids production trust.

## 1) Purpose
Phase 15 Step 0 exists to prevent:
- trust drift away from governed guarantees
- memory creep that introduces persistence beyond explicit design
- UI authority creep (renderer-only invariant must hold)
- model authority creep (tool-only, governed pipeline must hold)
- production logging leaks of sensitive or governed internals

## 2) Production Definition (What “Production” Means)
Production is the governed runtime exposed to real users with:
- strict contracts and deterministic orchestration
- auditable release discipline (evidence before deploy)
- privacy/data minimization as default posture
- no behavior drift from certified phases
- fail-closed handling of all failure or uncertainty

## 3) Scope: Governed Core vs Non-governed Surface
**Governed core (immutable semantics):**
- Phase 9 DecisionState
- Phase 10 ControlPlan
- Phase 11 OutputPlan
- Phase 12 model tool-only pipeline (contract, prompt builder, verifier, fallback, orchestrator)
- Phase 13 chat API contract and UI renderer-only rules

**Non-governed surface (may change cosmetically/operationally, but cannot influence cognition):**
- frontend styling and layout
- infrastructure/hosting platform
- database choice/configuration
- monitoring/observability tooling
- authentication/authorization plans
These surfaces must still obey boundaries and must not alter governed decisions or semantics.

## 4) Authority & Trust Boundaries (Non-transitive)
- UI is untrusted and has zero decision authority.
- Operators and support staff are untrusted with respect to cognition outcomes.
- Networks and transport layers are untrusted; inputs must be validated.
- Model output is untrusted until schema/governance verification passes.
- Trust is non-transitive: no component inherits trust from another.
- Only the governed core may decide action/refusal/closure.

## 5) Data Policy (Storage Boundaries)
**Allowed persistent storage (examples):**
- user_id (opaque)
- session_id (opaque)
- plan tier metadata (FREE/MEDIUM/MAX) — metadata only; must not affect cognition semantics
- timestamps
- quota usage counters
- request size and token usage counts (aggregated)
- action outcome enum (ANSWER/REFUSE/CLOSE/ASK_ONE)
- failure_type enum (sanitized)
- anonymized request hash (optional)

**Forbidden persistent storage (examples):**
- raw user text by default
- model raw output by default
- DecisionState internals
- ControlPlan internals
- OutputPlan internals
- audit traces/evidence internals
- personal profile data
- embeddings for personalization
- “tone signature”
- hidden memory to simulate user personality

If raw prompts are stored, it requires explicit user consent plus a new phase with a revised threat model.

## 6) Database Design Constraints (Non-Functional)
- Postgres allowed; Supabase allowed.
- Minimal schema philosophy; collect only what is required for quotas/audit summaries.
- Must be multi-tenant safe with strict access controls and least privilege.
- Retention TTL policy for logs is mandatory; no indefinite retention by default.
- Database must not become a memory engine for cognition or personalization.

## 7) Monitoring & Telemetry Constraints
Allowed:
- categorical signals only (aligned to Phase 8 monitoring semantics)
- request accepted/refused/aborted events
- action type counts
- error category counts

Forbidden:
- logging reasoning content
- logging model prompts or responses
- monitoring that feeds back into behavior or decision thresholds
- adaptive thresholds that alter cognition semantics

## 8) Release Discipline & Evidence Checklist
A release to production requires evidence of:
- Phase 14 backend fast suite passing (xfail only as documented)
- Phase 14 UI phase14 suite passing
- Phase 13 UI abuse suite passing
- Phase 12 abuse suite passing
- determinism snapshots unchanged
- no secrets detected in the workspace
- semver release tagging applied
- rollback plan prepared and documented

## 9) Invalidation Triggers
“Production Certified Trust” is void if any occur:
- any change to governed core logic
- any bypass of verification or fallback
- any UI sending history/metadata beyond contract
- any model output accepted without schema verification
- any relaxation of fail-closed behavior
- any logging of raw content without explicit consent and new phase approval
- any “hotfix patching” of governed artifacts outside formal reopening

## 10) Dependency Rules for Future Phases
- Phase 15+ may add DB/auth/paid plans, but must not alter governed core semantics without reopening Phase 9–12 as required.
- Paid tiers may adjust quotas/TTL and operational limits, not cognition authority or safety posture.

## 11) Stability Marker (Closure)
Phase 15 Step 0 is LOCKED. Any change requires reopening Phase 15 and updating certification evidence.
