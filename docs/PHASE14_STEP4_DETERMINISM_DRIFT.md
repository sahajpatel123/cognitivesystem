# Phase 14 — Step 4: Determinism & Drift Tests

Status: Implemented (backend tests in `backend/tests/test_phase14_determinism.py`)

## Purpose
Lock in deterministic behavior across certified cores so identical governed inputs always produce identical governed outputs (at governance layer), and drift is caught via snapshots.

## Scope & Invariants
- Phase 9 DecisionState signatures deterministic (same input → same signature).
- Phase 10 ControlPlan signatures deterministic.
- Phase 11 OutputPlan signatures deterministic.
- Phase 12 governance outcomes stable: action class, validated constraints, fallback selection deterministic even if raw model text varies.
- Candidate validator outcomes deterministic for invalid candidates.
- Soft determinism: model free-form text may vary; tests assert governance-level invariants only.

## Test Assets
- Determinism suite: `backend/tests/test_phase14_determinism.py`
- Signature helpers: `backend/tests/_phase14_determinism_signatures.py`
- Deterministic LLM shim: `backend/tests/_phase14_fake_llm.py`

## Golden Snapshots (Drift Guard)
- Prompts corpus (15) in the test file.
- For each prompt, stored signatures of DecisionState, ControlPlan, OutputPlan, and governed result (action/json keys/failure type). One prompt (“I think I'm being followed right now…”) intentionally records the locked Phase 9/11 assembly error (documented xfail-equivalent finding; no runtime change allowed).
- Snapshots are bounded JSON-like dicts to keep diffs readable.

## Determinism Checks Covered
- Repeatability: 10x signature comparisons for DecisionState/ControlPlan/OutputPlan.
- Governed response stability: action class + JSON shape stable across payload variants; leakage checks to ensure no internals emitted.
- Candidate validator determinism: repeated invalid payloads yield identical failure types.
- Drift snapshots: current golden map compared against fresh pipeline runs using deterministic fake LLM payloads.

## Execution
- Command: `python -m pytest backend/tests/test_phase14_determinism.py`
- Last run: 10 passed.

## Constraints Observed
- No runtime changes to locked Phases 1–13.
- No randomness/time/order dependence; deterministic fake LLM used.
- Only governance-level assertions; raw model text not equality-checked.

## Next
- Keep snapshots updated only when governance semantics intentionally change (requires review/recertification of affected phase).
- Do not proceed to Step 5 until Step 4 certified.
