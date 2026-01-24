# Phase 16 Step 5 — Reliability, Quality, Safety Discipline (Deterministic & Observable)

## Purpose
Add a bounded, deterministic wrapper around `/api/chat` model invocation that:
- Enforces circuit/budget short-circuits
- Imposes total and per-attempt deadlines
- Applies safety envelope and quality gate deterministically
- Supports chaos flags for drills
- Preserves existing Step 4 routing and the public contract

## Determinism Guarantees
- Fixed attempt order per Step 4 route plan
- Max attempts bounded (default 2)
- No randomness; chaos flags are explicit env toggles
- Deadlines derived from request budget/per-attempt caps
- No logging of `user_text`

## Failure Taxonomy (Step 5)
- `PROVIDER_UNAVAILABLE`: breaker_open short-circuit
- `BUDGET_EXCEEDED`: budget_blocked short-circuit
- `TIMEOUT`: per-attempt or total deadline exceeded
- `PROVIDER_BAD_RESPONSE`/`PROVIDER_TIMEOUT`: provider invocation failures
- `SAFETY_BLOCKED`: safety envelope refusal
- Quality gate: action `ASK_CLARIFY`, no failure_type

## Chaos Flags (per-request process env)
- `FORCE_BREAKER_OPEN=1` → breaker_open short-circuit (FALLBACK, PROVIDER_UNAVAILABLE)
- `FORCE_BUDGET_BLOCK=1` → budget_blocked short-circuit (FALLBACK, BUDGET_EXCEEDED)
- `FORCE_PROVIDER_TIMEOUT=1` → simulate provider timeout (FALLBACK, TIMEOUT, timeout_where=provider)
- `FORCE_QUALITY_FAIL=1` → quality gate -> ASK_CLARIFY with clarifying prompt
- `FORCE_SAFETY_BLOCK=1` → safety envelope -> FALLBACK, SAFETY_BLOCKED

## Observability
Structured log `[API] step5.summary` fields:
- request_id, status_code, action, failure_type, failure_reason (truncated)
- plan_value, mode_requested, mode_effective, model_class_effective
- attempts, breaker_open, budget_blocked, timeout_where, latency_ms

## Verification Checklist (local)
```
python3 -m compileall backend mci_backend
python3 -c "import backend.app.main; print('OK backend.app.main import')"
pytest -q backend/tests/test_step5_determinism.py backend/tests/test_step5_quality_gate.py backend/tests/test_step5_safety_envelope.py backend/tests/test_step5_timeouts.py
bash -n scripts/smoke_api_chat.sh scripts/promotion_gate.sh scripts/cost_gate_chat.sh scripts/chaos_gate.sh
```

## Verification Checklist (staging)
```
STAGING_BASE=https://cognitivesystem-staging.up.railway.app
MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
BASE=$STAGING_BASE ./scripts/chaos_gate.sh
```
