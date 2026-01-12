# Phase 8 — Step 1: Invocation Governance & Access Control (Deterministic, Fail-Closed)

## Scope
- Defines who may invoke the system, under which fixed invocation classes, and under what limits.
- Governance lives strictly outside cognition, accountability, and audit runtimes; it gates entry.
- No runtime behavior, cognition, audit semantics, or Phase 7 guarantees are modified.
- No UI, endpoints, infra, or deployment actions are introduced.

## Invocation Classes (Bounded, Non-Escalating)
- `INTERNAL_DECISION_INVOCATION`
  - May invoke: governed core decision pipeline entrypoint.
  - May not invoke: audit replay triggers, governance controls, kill switches.
  - Cannot escalate to any other class.
- `EXTERNAL_DECISION_INVOCATION`
  - May invoke: governed core decision pipeline entrypoint subject to strict boundary checks.
  - May not invoke: internal audits, governance controls, kill switches.
  - Cannot escalate to any other class.
- `AUDIT_INVOCATION`
  - May invoke: verdict-only external audit interface (read-only, no replay trigger).
  - May not invoke: cognition, decision pipeline, trace/evidence/attribution access, internal audit replay.
  - Cannot escalate to any other class.
- `GOVERNANCE_RESERVED`
  - Placeholder for future governance control plane operations.
  - May not invoke cognition, decision pipeline, or audit replay until explicitly defined in later steps.
- Classes are fixed; no dynamic creation, merging, or transformation. An invocation retains its class for its lifetime.

## Identity vs Trust (Separation)
- Caller identity (who) is distinct from authority/trust (what may be invoked).
- Identity alone never grants authority; ownership or operator status does not imply trust.
- Trust is explicitly granted per invocation class; operators/internal tools are not implicitly trusted.

## Request Gating (Deterministic, Fail-Closed, Pre-Cognition)
- Before any cognition executes:
  - Validate declared invocation class is one of the bounded set.
  - Validate caller authorization for that class.
  - Validate boundary compliance per Phase 8 Step 0 (scope, trust, data boundaries).
- On any failure: reject the request; cognition does not run; no partial execution; no best-effort access.

## Rate Limiting & Quotas (Deterministic, External to Cognition)
- Apply fixed limits per invocation class to prevent abuse/flooding/adversarial pressure.
- Exceeding a limit blocks invocation entirely; it does not alter cognition behavior or degrade quality.
- Limits are deterministic and enforced outside cognition; no adaptive or probabilistic adjustments.

## Abuse Containment (Non-Adaptive, Blunt)
- Abuse indicators: repeated limit violations, malformed invocation class claims, unauthorized class usage.
- Containment actions: block or throttle at the gateway; do not forward to cognition or audit runtimes.
- Escalation: escalate containment outside cognition; no learning, personalization, or heuristics in cognition.
- No model adaptation; no suspicion scoring inside the decision pipeline.

## Failure Behavior (Explicit, Fail-Closed)
- Access-control failures are explicit rejections.
- Access-control failures must not generate decision traces, evidence, attribution, or audits.
- No silent degradation, no partial execution, no governance bypass for convenience.

## Non-Goals
- No new UI, endpoints, or product flows.
- No kill switches (deferred to Phase 8 Step 3).
- No changes to cognition, accountability, audit semantics, or Phase 7 guarantees.
- No intelligence changes, heuristics, retries, fallbacks, or probabilistic policies.
- No performance optimization or infra decisions.

## Stability & Dependency
- These governance rules are STABLE once approved.
- Later Phase 8 steps depend on this definition; changing it requires reopening Phase 8.
- Phase 9+ may consume these rules but cannot alter them without reopening Phase 8.
