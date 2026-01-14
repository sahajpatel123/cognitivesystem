# Phase 14 — Step 3: Component-Level Adversarial Tests (Lock)

## Purpose
Harden the governed system against adversarial inputs at the component level (Phases 9–12) by directly attacking schemas, invariants, dominance rules, and verification layers. No runtime logic is modified; only deterministic tests and fakes are added to prove fail-closed behavior.

## Scope
- In scope: DecisionState (Phase 9), ControlPlan/orchestration (Phase 10), OutputPlan assembly (Phase 11), model output schema + verification (Phase 12), and orchestrator/pipeline integration (no UI).
- Out of scope: Frontend/UI, network calls, performance/load, new features.

## Attack Taxonomy (A–E)
A. DecisionState integrity attacks (empty/duplicate/misaligned unknowns)
B. ControlPlan invariant attacks (budget/closure/refusal consistency, STOP friction gates)
C. OutputPlan dominance and selector safety (refusal/closure dominance, single-question discipline)
D. Schema + verify abuse (fenced JSON, malformed/extra/missing/wrong types, authority/tool/memory claims, leakage)
E. Integration adversarial pipeline (orchestrator with malicious model output -> fail-closed/fallback, no leakage)

## Coverage Matrix
- A: backend/tests/test_phase14_unit_adversarial_phase9.py
- B: backend/tests/test_phase14_unit_adversarial_phase10.py
- C: backend/tests/test_phase14_unit_adversarial_phase11.py
- D: backend/tests/test_phase14_unit_adversarial_phase12_schema_verify.py
- E: backend/tests/test_phase14_integration_adversarial_pipeline.py

## Failure Taxonomy
- Schema violation (parse/schema/type/bounds)
- Dominance violation (action/closure/refusal vs questions)
- Honesty leak (authority/capability/memory/tool claims)
- Internal artifact leakage (trace/control/output ids, phase markers)
- Contract mismatch (refusal category/action alignment)

## Findings
- XFAIL: DecisionState currently allows empty outcome_classes when unknown markers are present (test marked xfail in test_phase14_unit_adversarial_phase9.py). Certification-relevant; requires phase reopen to change.
- All other adversarial behaviors currently fail-closed via verification or OutputPlan dominance/fallback.

## Stability Marker
Phase 14 Step 3 is LOCKED. Weakening/removal of tests or coverage requires reopening Phase 14 and re-certifying.
