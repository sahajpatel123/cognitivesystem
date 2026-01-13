# Phase 12 — Certification & Lock (Model Tool Integration)

## Purpose / Role
- Phase 12 governs model invocation as a tool-only renderer under OutputPlan dominance.
- It binds prompt building, runtime invocation through Phase 3 enforcement, strict schemas, verification, fallback, and orchestrator wiring.
- It is not decision-making, not intent shaping, not UI/UX, and not product behavior; it only renders within governance constraints.

## Governing Trust Boundary
- Model output is untrusted; Phase 3 adapter/enforcement is the choke point for all calls.
- OutputPlan (Phase 11) dominates: action, disclosures, verbosity, and specs cannot be overridden by the model.
- No cross-request memory or personalization is permitted; each call is bounded to current user_text and deterministic plans.

## Scope (Governed and Locked)
- Code modules:
  - mci_backend/model_contract.py
  - mci_backend/model_runtime.py
  - mci_backend/model_prompt_builder.py
  - mci_backend/model_invocation_pipeline.py
  - mci_backend/model_candidate_validation.py
  - mci_backend/model_output_schema.py
  - mci_backend/model_verified_output.py
  - mci_backend/model_output_verify.py
  - mci_backend/fallback_rendering.py
  - mci_backend/governed_response_runtime.py
- Documentation (Phase 12 steps 0–8): docs/PHASE12_STEP*.md
- Tests: backend/tests/test_phase12_*.py (including abuse suite)

## Positive Guarantees
- Model remains non-authoritative; OutputPlan dominates every rendering request.
- Every invocation routes through Phase 3 enforcement and strict contracts.
- JSON-only governed outputs with forbid-extra; fenced JSON is rejected.
- Fail-closed verification: invalid/ambiguous outputs are rejected; deterministic fallback is used.
- No retries, no best-effort salvage, no prompt evolution.
- Deterministic behavior for identical inputs under fixed plans.
- Internal artifacts (ids, schemas, state) are not emitted to users.

## Explicit Non-Guarantees
- No guarantee of truth, correctness, fairness, ethics, legal/medical validity.
- No guarantees on performance, uptime, latency, or cost.
- No promise of user satisfaction, persuasion, or completeness.
- No prevention of downstream misuse beyond fail-closed governance.

## Certification Evidence
- Phase 12 includes unit tests for runtime adapter, prompt builder, output schema, verifier, fallback, orchestrator, and the abuse suite.
- Step 8 abuse tests are in place and passing, demonstrating tool-only, fail-closed behavior under adversarial outputs.

## Invalidation Triggers
- Allowing non-JSON or fenced JSON; relaxing forbid-extra schemas.
- Permitting multi-question outputs or changing action dominance (OutputPlan override).
- Adding retries, partial-output salvage, or reusing violating fragments.
- Bypassing Phase 3 enforcement or calling models outside the pipeline.
- Storing or using cross-request state in prompts or outputs.
- Exposing internal ids, schema versions, DecisionState/ControlPlan/OutputPlan internals to users.
- Weakening candidate validation, verification, or deterministic fallback templates.
- Changing invocation class mappings or OutputPlan binding requirements.

## Dependency Rules
- Later phases (e.g., Phase 13 UI) must call the governed_response_runtime/pipeline and cannot bypass Phase 12.
- No direct model access from downstream phases; any provider must honor the existing contract and enforcement.
- Phase 14+ tests may probe but cannot alter semantics or bypass governance.

## Closure Marker
- PHASE 12 COMPLETE, CERTIFIED, LOCKED — Dated: 2026-01-13.
- Any governed change requires reopening Phase 12 and full recertification.
