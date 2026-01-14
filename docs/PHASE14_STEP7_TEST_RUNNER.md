# Phase 14 — Step 7: Regression CI Harness & Test Runner Discipline

Status: Implemented (doc + runners). No runtime changes to locked phases.

## Purpose
Make Phase 14 adversarial validation reproducible and deterministic with canonical commands for backend and frontend, clear fast/full groupings, and snapshot discipline.

## Backend Runners (deterministic)
Make targets (repo root):
- `make test:phase14:backend:fast`
  - backend/tests/test_phase14_e2e_adversarial_pipeline.py
  - backend/tests/test_phase14_unit_adversarial_phase9.py (contains documented xfail)
  - backend/tests/test_phase14_unit_adversarial_phase10.py
  - backend/tests/test_phase14_unit_adversarial_phase11.py
  - backend/tests/test_phase14_unit_adversarial_phase12_schema_verify.py
  - backend/tests/test_phase14_integration_adversarial_pipeline.py
  - backend/tests/test_phase14_determinism.py
- `make test:phase14:backend:full`
  - All FAST files plus:
  - backend/tests/test_phase11_expression_abuse.py
  - backend/tests/test_phase12_model_governance_abuse.py
  - backend/tests/test_phase12_model_output_schema.py
  - backend/tests/test_phase12_model_output_verify.py
  - backend/tests/test_phase12_fallback_rendering.py
  - backend/tests/test_phase12_invocation_pipeline.py
  - backend/tests/test_phase12_orchestrator.py
  - backend/tests/test_phase12_prompt_builder.py
  - backend/tests/test_phase12_model_runtime.py
  - backend/tests/test_phase13_chat_api_contract.py

Rules:
- No retries, seeds, or parallel assumptions beyond pytest defaults.
- The known xfail in Phase 9 determinism test remains allowed; any new xfail is a failure (investigate before certifying).

## Frontend Runners (Playwright)
Scripts added in frontend/package.json:
- `npm run test:ui:phase13` — frontend/tests/phase13_ui_abuse.spec.ts (baseline UI abuse)
- `npm run test:ui:phase14` — frontend/tests/phase14_ui_attack.spec.ts (Step 5)
- `npm run test:ui:full` — full Playwright suite
Make targets (repo root):
- `make test:phase14:ui:phase13`
- `make test:phase14:ui:phase14`
- `make test:phase14:ui:full`
- `make test:phase14:all` (backend fast + UI phase14)

Playwright note: ensure browsers installed once via `npx playwright install` in frontend/.

## Snapshot Discipline (Step 4 golden snapshots)
- Default mode: verify snapshots only; any mismatch fails.
- Snapshot file: backend/tests/test_phase14_determinism.py (_GOLDEN_SNAPSHOTS).
- Regeneration is **not automated**. If governance-approved changes are needed, explicitly edit snapshots and commit with review; no casual regen.
- NEVER regen without explicit Phase 14 approval; treat snapshot drift as potential regression.

## Execution Evidence (for Phase 14 certification / Step 8 readiness)
- Backend FAST: `make test:phase14:backend:fast`
- Backend FULL (optional gate): `make test:phase14:backend:full`
- Frontend phase14 UI: `make test:phase14:ui:phase14`
- Frontend full UI (optional gate): `make test:phase14:ui:full`
- Record pass/fail with timestamps; any xfail outside the documented one is a blocker.

## Stability Marker
This doc locks Step 7 runner discipline. Any weakening, re-grouping, or auto-regeneration of snapshots requires reopening Phase 14 Step 7 (and may require broader governance review).
