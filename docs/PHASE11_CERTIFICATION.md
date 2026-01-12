# Phase 11 — Certification: Expression & Output Governance
**Status:** COMPLETE · CERTIFIED · LOCKED  
**Date:** 2026-01-12

## 1) Scope (What is governed)
- Governed artifacts: Phase 11 Expression & Output Governance planning and assembly only.
- Modules: output_plan schema, selectors (Steps 1–7), assembly (Step 8), abuse tests (Step 9).
- Schema boundary: Phase 11 `schema_version=11.0.0`; `PhaseMarker.PHASE_11`.
- Not covered: UI, rendering templates, model calls, deployment, storage.

## 2) Threat model / trust boundary
- Inputs: untrusted user text.
- Trusted upstream: `DecisionState` (Phase 9) and `ControlPlan` (Phase 10) as previously certified.
- No external models invoked in Phase 11.

## 3) Positive Guarantees
- Deterministic plan selection; no models, no stochasticity.
- OutputAction dominance ladder: closure > refusal > ask > answer.
- Single-question guarantee on ASK_ONE_QUESTION path (exactly one bounded QuestionSpec).
- Unknown honesty: explicit unknown zone forbids `UnknownDisclosureMode.NONE`.
- Refusal posture constraint: refusal requires `ExpressionPosture.CONSTRAINED`.
- Closure discipline: `USER_TERMINATED` ⇒ `ClosureRenderingMode.SILENCE`; `CLOSED` forbids summary modes.
- Fail-closed on contradictions and invalid inputs.

## 4) Explicit Non-Guarantees
- No correctness guarantee of answers or advice.
- No legal/medical correctness guarantee.
- No fairness/ethics correctness guarantee.
- No UX satisfaction or helpfulness guarantee.
- No best-question guarantee.
- No natural-language rendering quality guarantee (templates are outside this phase).

## 5) Certification Invalidation Triggers
- Changing OutputPlan schema/enums/invariants/schema_version.
- Bypassing or altering the Step 8 assembly pipeline.
- Weakening the dominance ladder (closure/refusal/ask/answer).
- Allowing multi-question clarification.
- Allowing `UnknownDisclosureMode.NONE` when unknowns exist.
- Allowing minimal confidence signaling in high-stakes+unknown scenarios.
- Relaxing refusal explanation or refusal posture constraints.
- Adding heuristics/probabilities/scoring/adaptive behavior or model calls inside Phase 11.
- Logging/storing user text or reasoning inside governance artifacts.
- Weakening or removing Step 9 abuse/honesty tests.
- Allowing raw model output or UI layers to bypass or rewrite OutputPlan.

## 6) Dependency Rules (for later phases)
- Phase 12 (model usage) may generate text but must not decide OutputAction or disclosure/posture/closure/refusal modes; it must consume OutputPlan as-is.
- UI or later phases may not rewrite ControlPlan/OutputPlan; any change requires reopening Phase 11.
- Any phase that bypasses OutputPlan or ControlPlan invalidates certification.

## 7) Evidence / Conformance Proof
- Abuse/honesty suite: `backend/tests/test_phase11_expression_abuse.py`.
- pytest result: 17 passed (action dominance, fail-closed contradictions, unknown honesty, posture/refusal coupling, single-question invariants, closure discipline).

## 8) Closure Marker
- Phase 11 is frozen (COMPLETE / CERTIFIED / LOCKED).
- Any modification to governed artifacts requires reopening Phase 11 and recertification.
