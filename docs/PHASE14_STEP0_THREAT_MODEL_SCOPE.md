# Phase 14 — Step 0: Threat Model & Test Scope (Lock)

## 1) Purpose
- Establish the adversarial validation and long-horizon correctness scope for Phase 14.
- Define what will be tested, how, and under which trust boundaries without altering any locked phases.
- Phase 14 is validation-only; no feature development or runtime changes are authorized.

## 2) Governing Principle
- Fail-closed > helpfulness at every boundary.
- LLM is a tool, never authority; governed outputs dominate any model suggestions.
- UI is renderer-only; no decision or authority resides in the client.
- Locked phases cannot be touched; any change requires formal reopen and recertification.
- Determinism is required: same governed inputs produce the same governed outputs within defined bounds.

## 3) Certified System Under Test (SUT) — Boundaries
- In scope: DecisionState pipeline (Phase 9), ControlPlan pipeline (Phase 10), OutputPlan pipeline (Phase 11), model integration tool-only pipeline (Phase 12), backend `/api/chat` contract and enforcement (Phase 13), UI chat page renderer-only behavior and contract validator (Phase 13).
- Out of scope: styling/aesthetics, infrastructure scaling/caching/latency, model quality improvements, personalization, long-term memory, any new features or endpoints.

## 4) Trust Boundaries (Restate the architecture truthfully)
- Model output is untrusted and must pass schema validation and verifier/fallback before rendering.
- UI is untrusted; backend contract is authoritative and enforces request/response bounds.
- Monitoring is passive only; no in-band control loops.
- No cross-request memory beyond bounded, local-only session TTL behavior; no history is sent to backend.

## 5) Threat Model
- A) User attacker: prompt injection, jailbreak, multi-question or coercive prompts aiming to bypass refusals/closures or inject multiple intents; system must enforce contract, single-question discipline, refusal/closure dominance.
- B) Model attacker: emits non-JSON/malformed JSON, unknown actions, inflated content, or claims of authority; system must validate, fail-closed, and prefer fallback over unsafe renderings.
- C) UI attacker: mutates payload, injects history/metadata, or bypasses terminal/TTL guards; system must reject non-contract payloads, maintain terminal discipline, and never send history.
- D) API attacker: invalid bodies, oversize payloads, replay attempts, schema abuse; system must enforce strict schemas, size limits, and determinism of handling.
- E) System failure: timeouts, provider outage, corrupted outputs; system must fail-closed, surface neutral notices, and avoid retries/loops.

## 6) Attack Surfaces
- `/api/chat` boundary (request/response schema enforcement).
- `governed_response_runtime` orchestrator path.
- Model prompt builder and invocation pipeline.
- Output schemas and verifier.
- Fallback rendering engine.
- UI terminal discipline, TTL/session handling, and contract validator.

## 7) Non-Negotiable Governance Invariants (Pass Conditions)
- OutputPlan dominance MUST hold; model cannot override selected action.
- Single-question invariant MUST hold; ask-one cannot become multi-question.
- Refusal dominance MUST hold; refusal cannot become an answer.
- Closure dominance MUST hold; close cannot reopen or ask follow-ups.
- Unknown honesty MUST hold when required by plan; no suppression of required unknowns.
- No leakage MUST hold; no trace ids, schema versions, enums, or internal artifacts exposed.
- Determinism MUST hold; same governed inputs yield same governed outputs within defined bounds.
- No retries or adaptive loops MUST hold; manual-only controls remain.
- No model authority claims MUST hold; LLM outputs are bounded and verified/fallback.

## 8) Failure Taxonomy (Fail Conditions)
- Authority drift (UI or model claiming or gaining authority).
- Invariant violation (OutputPlan dominance, refusal/closure, single-question, unknown honesty).
- Non-determinism beyond defined bounds.
- Leakage of internal artifacts (trace ids, schema versions, enums, internals).
- Silent degradation (accepting malformed outputs or skipping checks).
- Retry loops / agent creep / auto-follow-ups.
- UI bypass of contract or terminal discipline.
- Model output acceptance without schema validity.

## 9) Evidence Requirements (What Phase 14 must produce)
- Adversarial corpora (prompt suites) covering attack classes A–E.
- Regression test suites proving invariants under adversarial and long-horizon conditions.
- Logs limited to categorical outcomes (no user content) demonstrating enforcement.
- Certification evidence summary for Phase 14 lock.

## 10) Explicit Prohibitions (To prevent scope creep)
- No new features or endpoints.
- No “fixing” logic in locked phases without reopen/recertify.
- No UI engagement additions (suggestions, persona, auto follow-ups).
- No model tuning, RAG, memory persistence, or personalization.
- No expansion of contract schemas or loosening of validators.

## 11) Stability Marker
- Phase 14 Step 0 is LOCKED upon creation. Any modification requires reopening Phase 14 and invalidates subsequent Phase 14 steps.
