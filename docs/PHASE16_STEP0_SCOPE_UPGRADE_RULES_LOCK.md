# Phase 16 Step 0 — Scope & Upgrade Rules (LOCK)

## Purpose
Phase 16 Step 0 exists to prevent scaling and reliability efforts from mutating cognition or product semantics. It establishes enforceable guardrails so upgrades stay operational, cost-aware, and reversible without altering governed behavior.

## Phase 16 Definition
- Objective: scaling, reliability, cost control, upgrade safety, and governance continuity for the certified system.
- Includes: infra hardening, performance tuning, predictable costs, safer rollouts, guardrail reinforcement, and observability hygiene.
- Not included: improving reasoning quality, personalization learning, long-term memory, or cognition feature changes.

## Non-Negotiable Locks (Phases 1–14 + Phase 15)
- Phases 1–14 remain locked; Phase 15 certification (docs/PHASE15_CERTIFICATION.md) is the baseline and stays in force.
- No changes to cognition logic, truth rules, adaptive behavior, or personalization learning.
- Output contract, failure taxonomy, and governed pipeline order remain unchanged.

## Change Classification Protocol
- Every change/PR must declare: Class, impacted surfaces (API/UI/infra/logs), and rollback plan.
- Class A — No behavior change: infra, refactor, performance, deploy tooling; output contract and semantics must remain identical.
- Class B — Policy/limits: quotas, TTLs, rate limits, model selection within declared policy envelopes; must document policy diffs and ensure contracts unchanged.
- Class C — Behavior/cognition: any change to reasoning, prompts, routing, schemas, or adaptive behavior; **forbidden in Phase 16**.

## Allowed Changes (Examples)
- Infra and reliability hardening, dependency bumps with no contract change.
- Performance tuning (timeouts, pooling, cache lifetimes) without altering outputs.
- Cost controls: token ceilings, call budgets, circuit breaker thresholds, model selection within declared policy.
- Security and observability hygiene (passive only), WAF/rate/quota tuning within policy.
- Deployment/rollout tooling (canary, feature flags for policy switches) that do not change response semantics.

## Forbidden Changes (Examples)
- Storing user prompts/content; adding memory/personalization/embeddings from chats.
- “Auto improving prompts” or adaptive prompt rewrites based on user content.
- Changing response schema, fields, or cognition routing logic.
- Silent model switching based on difficulty without declared policy and user-visible signaling.
- Introducing new tables or services that retain chat content or identity-linked history.

## No Silent Degradation Policy
- Silent degradation = any reduction in quality/coverage not surfaced to users or operators.
- Requirements: degradations must be detectable, logged in sanitized form, and user-visible via governed failure codes or explicit degraded-mode flag.
- Allowed: explicit fallback with clear failure_type/reason and logs; controlled feature flag disabling with operator notice.
- Forbidden: hidden fallbacks that change outputs or skip controls without signaling; dropping guardrails to “keep responses flowing.”

## Cost & Risk Boundaries
- Enforce budget caps, token ceilings, timeouts, and circuit breakers for all model calls.
- WAF, quotas, and auth remain mandatory gates; cannot be bypassed.
- Any cost-affecting change must specify limits, monitoring, and rollback trigger.

## Environment & Rollout Rules
- Environments: local/dev → staging → production. Production-only changes require staging promotion first.
- Risky changes (even Class A/B) use canary or feature flags; document blast radius and rollback.
- Rollback must be fast, documented, and rehearsed; prior stable build must remain deployable.

## Evidence Required for Any Change
- Minimum checklist per change:
  - Smoke: health, db health, auth/whoami, /api/chat happy path, 415 rejection, 429 rate/burst.
  - Release drill subset: reference docs/PHASE15_STEP8_RELEASE_DRILLS.md (select applicable drills).
  - Confirmation that no sensitive logging was introduced; observability remains passive.
  - For Class A: contract-consistency check (schema and failure taxonomy unchanged).
  - For Class B: policy diff documented; limits validated in staging; flag/canary plan stated.

## Observability Constraint (Passive Only)
- Observability must not feed back into cognition or routing.
- No raw user_text/prompt logs; only hashed/derived IDs and aggregate metrics are permitted.
- Logging failures must not affect responses; redaction stays enforced.

## Data & Storage Constraints
- Allowed stores (unchanged from Phase 15): sessions, quotas, rate_limits, invocation_logs (sanitized metadata only).
- Forbidden: memory/personalization tables, embeddings or vector stores populated from user chats, transcript storage.
- Retention remains bounded per Phase 15; no expansion without new certification.

## Invalidation Triggers
- Storing user content or adding personalization/memory.
- Removing or bypassing WAF/quota/auth gates.
- Changing output contract/schema or cognition routing without a new certification phase.
- Expanding logs to include sensitive content or raw prompts/user_text.
- Any Class C change attempted or merged.

## Acceptance Checklist
- Classification framework (A/B/C) present.
- Allowed vs forbidden lists present.
- No silent degradation policy stated.
- Rollout and evidence rules documented.
- Invalidation triggers listed.

## Status
- Phase 16 Step 0 Status: LOCKED ✅
- Locked on: <fill>
