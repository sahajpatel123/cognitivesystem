# Phase 12 — Step 1: Model Invocation Runtime Adapter

## Purpose
- Provide the deterministic runtime bridge from the Phase 12 contract to the Phase 3 enforcement/adapter.
- Keep the model strictly tool-only and non-authoritative; OutputPlan dominance is preserved.
- Enforce fail-closed handling of all model responses before they can be used.

## Trust Boundary (Phase 3 Choke Point)
- All invocations pass through the existing Phase 3 enforcement + LLM client path (`backend.app.enforcement`, `backend.app.llm_client`).
- No direct provider access; no bypass of the adapter.
- Model output is never authoritative; it is only a candidate payload and must not change ControlPlan/OutputPlan.

## Contract Mapping (Phase 12 → Phase 3 → Phase 12)
- Input: `ModelInvocationRequest` validated (schema_version=12.0.0, PhaseMarker=PHASE_12, bounded tokens, bounded required/forbidden elements).
- Mapping to Phase 3 expression adapter: default bounded `CognitiveStyle`, `ExpressionPlan`, and `IntermediateAnswer` constructed from `required_elements`; user_text becomes `UserMessage`.
- Output: Phase 3 rendered text parsed per `output_format` into `ModelInvocationResult` (text or JSON).
- Data minimization: only bounded fields required for rendering are passed; no ids or artifacts beyond what Phase 3 needs.

## Failure Mapping (Fail-Closed)
- Enforcement/HTTP/timeout ⇒ `EXTERNAL_DEPENDENCY_FAILURE` → `TIMEOUT` or `PROVIDER_ERROR`.
- Non-JSON when JSON expected ⇒ `NON_JSON`.
- JSON shape issues ⇒ `SCHEMA_MISMATCH`.
- Contract validation/forbidden combinations ⇒ `CONTRACT_VIOLATION`.
- Unexpected errors ⇒ `PROVIDER_ERROR` (fail-closed).
- All failures return `ModelInvocationResult` with `fail_closed=True`; no raw exceptions escape.

## Non-Goals
- No provider/model choice, no prompt tuning, no retries/fallbacks, no streaming, no tools/function calls.
- No UI wiring, no caching/memory, no personalization, no plan mutation, no logging of user text beyond adapter need.

## Stability / Closure Marker
- This adapter interface is part of Phase 12 Step 1 and is stable. Any changes require reopening Phase 12 and re-certifying the contract and adapter together. No further steps may weaken OutputPlan dominance or bypass the Phase 3 choke point.
