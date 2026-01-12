# Phase 8 — Step 0: Deployment Scope & Trust Boundary Definition

## Scope (What is inside / outside)
- In scope (governed core):
  - Cognition runtime: MCI pipeline code in `mci_backend/app` (request boundary enforcement, reasoning, expression rendering) **excluding** any model weights or external services.
  - Accountability runtime: decision trace, rule/boundary evidence, failure attribution modules in `mci_backend/accountability`.
  - Audit runtime: internal audit replay engine in `mci_backend/accountability/audit_runtime.py`.
  - External audit interface (verdict-only) in `mci_backend/accountability/external_audit.py`.
  - Governance control plane concepts (kill switches, role checks) are scoped conceptually but not yet implemented; future steps must respect these boundaries.
- Out of scope (by default):
  - Any UI, client applications, or operator consoles.
  - External services, networks, data stores, caches, queues.
  - Model backends, LLMs, embeddings, or third-party APIs.
  - Infrastructure, deployment tooling, monitoring, logging systems.
  - Any component not explicitly listed as in-scope above.

## Trust Boundaries (Who/what is trusted)
- Trusted to uphold invariants: governed core runtimes listed above, running deterministically and fail-closed.
- Not trusted (even if internal): UIs, operators, external clients, networks, external services, model backends/LLMs, storage systems, and any telemetry or analytics surfaces.
- Trust is non-transitive: trusting the governed core does not extend trust to callers, hosts, or dependencies.

## Authority Boundaries (Who can do what)
- May initiate decisions: governed core entrypoints only (request handler), under existing boundary checks.
- May abort decisions: governed core fail-closed logic only (trace lifecycle).
- May mutate accountability state: none at runtime; traces/evidence/attribution are immutable after creation/closure.
- May trigger audits: internal audit replay is invoked only by governed core; external parties cannot trigger new audits (verdict-only interface).
- Kill-switch authority (conceptual placeholder): reserved for governance control plane; not implemented here and must not be delegated to UIs, operators, or external clients.
- Explicitly forbidden:
  - External or UI-driven control over cognition.
  - Operator patching or live mutation of cognition/accountability/audit logic.

## Data Boundaries (What can cross)
- External → Internal: request payloads limited to allowed fields (per Phase 4 framing); no elevation to internal artifacts.
- Internal → External: only user-visible reply text on success, and categorical verdicts from external audit interface when used; no traces, evidence, attribution, reasoning, or governance/audit internals may cross.
- Must never cross any boundary: reasoning traces, model prompts/outputs, accountability artifacts (trace/evidence/attribution), audit results beyond categorical verdict, governance logic/configuration.

## Failure Boundaries (Where failures stop)
- Request-level failures: violate invariants → abort the single request; no partial continuation.
- Component-level failures: invariant violations in accountability/audit → fail closed for the request and surface as hard failure; no silent degradation.
- Escalation candidates for later kill-switch attachment: repeated invariant violations, audit replay failures, attribution generation failures. No kill-switch is implemented here; later steps must attach explicitly.
- Forbidden: silent degradation, best-effort continuation, or partial masking of failed invariants.

## Non-Goals (Explicit exclusions)
- No deployment actions, infra provisioning, or environment selection.
- No access control, authentication, authorization, or rate limiting.
- No new runtime logic, cognition changes, or accountability/audit behavior changes.
- No UI, API surface, endpoint design, or product considerations.
- No intelligence changes, heuristics, retries, fallbacks, or probabilistic behaviors.

## Stability & Future Dependency
- This definition is STABLE once approved; later Phase 8 steps depend on it.
- Changing scope or boundaries requires reopening Phase 8 and explicit approval.
- Phase 9+ may consume outputs but may not alter these boundaries without reopening Phase 8.
