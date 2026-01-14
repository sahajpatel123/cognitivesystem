# Phase 14 — Step 2: E2E Adversarial Harness (Lock)

## Purpose
Establish an end-to-end adversarial test harness that exercises the governed pipeline via `render_governed_response`, validating fail-closed behavior, determinism, and OutputPlan dominance under hostile outputs. No runtime logic is changed; only tests and fakes are added.

## Trust Boundary Attacked
- Model output boundary (tool-only; untrusted).
- Orchestrator path: DecisionState → ControlPlan → OutputPlan → model invocation pipeline → verifier/fallback.
- UI is out of scope here; API/backend boundary is exercised through the orchestrator entrypoint.

## Invariants Validated
- Determinism: identical inputs yield identical governed outputs (including fallback).
- OutputPlan dominance: model cannot override action or introduce multi-question/authority drift.
- Single-question guarantee: ASK_ONE_QUESTION cannot become multi-question.
- Refusal/closure discipline: REFUSE and CLOSE remain terminal; no follow-ups.
- Fail-closed: malformed/non-JSON/extra-key outputs trigger verify/fallback, not acceptance.
- No authority or capability claims allowed; no memory/tool hallucinations.
- No internal leakage: trace/control/output identifiers and phase markers are not emitted.

## Coverage Categories (from Step 1)
- Determinism & stability
- Schema/JSON attacks
- Multi-question injection
- OutputPlan dominance attacks
- Authority/capability hallucinations
- Refusal/closure discipline
- Fail-closed pipeline errors (timeouts/provider errors)
- No internal leakage

## Not Tested Here
- Frontend/UI rendering paths (reserved for later E2E UI steps).
- Performance, load, or latency characteristics.
- Any new feature behavior; no schema or contract changes.

## Implementation Notes
- Tests invoke `render_governed_response` with deterministic DecisionState/ControlPlan/OutputPlan patches to avoid modifying locked code.
- Deterministic fake LLM client (`backend/tests/_phase14_fake_llm.py`) supplies controlled outputs, malformed JSON, authority claims, or exceptions (timeout/provider error) without network access.
- Assertions focus on governed outcomes, fallback activation, terminal discipline, and absence of internal identifiers.

## Stability Marker
Phase 14 Step 2 is LOCKED. Any changes require reopening Phase 14 Step 2 and re-running certification for later steps.
