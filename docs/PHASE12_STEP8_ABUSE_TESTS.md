# Phase 12 — Step 8: Model Governance Abuse Tests

## Purpose
- Prove the Phase 12 model layer is tool-only and subordinate to OutputPlan.
- Demonstrate fail-closed behavior under hostile/broken model outputs.
- Provide certification evidence that OutputPlan dominance and fallback remain intact.

## Threat Model
- Malicious or malformed model outputs (non-JSON, fenced JSON, wrong types, extra keys).
- Multi-question injections and action overrides.
- Authority/tool/policy hallucinations and refusal bypass attempts.
- Provider/timeouts and dependency failures.
- Leakage of internal artifacts (DecisionState/ControlPlan/OutputPlan ids, schema versions).

## Coverage Matrix (Categories A–H)
- A) Structured violations: non-JSON, fenced JSON, malformed, extra keys, missing keys, wrong types → rejected/fallback.
- B) Multi-question injections: multiple questions/arrays/“Also” → rejected/fallback to single bounded question.
- C) OutputPlan dominance: REFUSE/CLOSE/ASK actions enforced; model cannot override.
- D) Authority claims: memory/tool/policy/agent claims rejected; fallback removes them.
- E) Refusal bypass: “I can’t help but here’s how…” → remains refusal-shaped, bounded.
- F) Timeout/provider failure: deterministic fallback, no retries.
- G) Determinism: same inputs ⇒ same outputs after fallback/verification.
- H) No leakage: outputs do not expose internal plan/state IDs or schema versions.

## Non-Goals
- No output quality scoring, no UX validation, no personalization checks, no performance tests.

## Stability Marker
- These tests are mandatory. Weakening/removal requires reopening Phase 12 and recertification. Changes to Phase 12 behavior must be reflected with updated abuse coverage.
