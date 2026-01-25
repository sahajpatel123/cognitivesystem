# Release Log (Append-Only)

Use this file to record promotions and rollbacks. Do not overwrite existing entries; append new entries in chronological order. Evidence must reference staging gates and post-promotion checks. Do not paste secrets.

## Promotion Entry Template
```
- release_id: <YYYYMMDD-HHMM-rc1>
  type: promotion
  commit_sha: <sha>
  environment: production
  from_branch: main
  to_branch: release
  staging_base: <https://staging...>
  staging_gate_command: MODE=staging BASE=<staging> ./scripts/promotion_gate.sh
  staging_gate_result: pass|fail
  gates_run:
    - health
    - db_health
    - chat_happy
    - chat_415
    - burst_429
    - release_drills_subset (if run)
    - certify_phase15_subset (if run)
  change_class: A|B|C (C forbidden)
  prod_verification:
    - health
    - db_health
    - chat_happy
    - chat_415
  result: pass|fail
  rollback_plan: <pointer/notes>
  notes: <short notes>
  operator: <name/handle>
  evidence_refs: <links or file refs if any>
  cost_control_evidence:
    - cost_gate_chat: MODE=staging BASE=<...> ./scripts/cost_gate_chat.sh
    - breaker_drill: ./scripts/cost_drill_breaker.sh (if run)
```

## Rollback Entry Template
```
- release_id: <YYYYMMDD-HHMM-rb1>
  type: rollback
  trigger: <e.g., 5xx spike, auth failure>
  from_sha: <sha before rollback>
  to_sha: <sha rolled back to>
  environment: production
  actions:
    - redeploy last known good
    - rerun smoke (health/db/chat/415)
  post_rollback_verification:
    - health
    - db_health
    - chat_happy
    - chat_415
  result: completed|partial
  notes: <short notes>
  operator: <name/handle>
  evidence_refs: <links or file refs if any>
```

## Step 3 Evidence (Cost Control + Contract Alignment)
```
- date: 2026-01-22
  type: step16.3_cert_alignment
  staging_base: <https://staging...>
  summary: "Aligned smoke/promotion gates to OpenAPI: chat payload uses {\"message\"}, removed invalid /auth/whoami check."
  local_gates:
    - python3 -m compileall backend mci_backend (pass)
    - python3 -c "import backend.app.main; print('OK backend.app.main import')" (pass)
    - python3 -c "import mci_backend.main; print('OK mci_backend.main import')" (pass)
    - bash -n scripts/smoke_api_chat.sh scripts/promotion_gate.sh scripts/cost_gate_chat.sh (pass)
  staging_commands:
    - MODE=staging BASE=<staging> ./scripts/promotion_gate.sh
    - BASE=<staging> EXPECT_BUDGET_BLOCK=1 ./scripts/cost_gate_chat.sh
  expected_outcomes:
    - /health -> 200
    - /db/health -> 200
    - /api/chat (json {"user_text":"hi"}) -> 200 with governed response
    - /auth/whoami -> 200 JSON (no 422; accepts Request/Response injection)
    - /api/chat (text/plain) -> 415
    - cost gate with lowered limits -> 429 FailureType.BUDGET_EXCEEDED
  env_toggles_for_cost_drill:
    - temporarily lower COST_GLOBAL_DAILY_TOKENS, COST_IP_WINDOW_TOKENS, COST_ACTOR_DAILY_TOKENS, COST_REQUEST_MAX_TOKENS, COST_REQUEST_MAX_OUTPUT_TOKENS
    - revert to defaults after drill
  notes: "No identity endpoint used in smoke; matches OpenAPI contract."
```

## Step 4 Evidence (Model Routing Policy + request_id/whoami hotfix)
```
- date: 2026-01-23
  type: step16.4_routing_policy
  staging_base: https://cognitivesystem-staging.up.railway.app
  prod_base: https://cognitivesystem-production.up.railway.app
  summary: "Fixed module-call crash on /api/chat by importing callable get_request_id; whoami returns 200; deterministic routing policy enforced; patched datetime NameError in chat logging."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - python3 -c "from backend.app.observability.request_id import get_request_id; print('callable=', callable(get_request_id), 'type=', type(get_request_id))"
    - bash -n scripts/smoke_api_chat.sh scripts/promotion_gate.sh scripts/cost_gate_chat.sh
  commands_staging:
    - curl -s -i -H "Content-Type: application/json" -d '{"user_text":"hi"}' $STAGING_BASE/api/chat  # expect 200 governed JSON
    - curl -s -i $STAGING_BASE/auth/whoami  # expect 200 JSON
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - curl -s -i -H "Content-Type: application/json" -H "X-Mode: THINKING" -d '{"user_text":"hi","mode":"thinking"}' $STAGING_BASE/api/chat  # expect 200, deterministic downgrade if tier disallows
  commands_prod:
    - curl -s -i -H "Content-Type: application/json" -d '{"user_text":"hi"}' $PROD_BASE/api/chat  # expect 200 governed JSON
    - curl -s -i $PROD_BASE/auth/whoami  # expect 200 JSON
  expected_outcomes:
    - /api/chat with {"user_text":"hi"} -> 200
    - /auth/whoami -> 200
    - routing logs include "routing decision" with tier/requested_mode/effective_mode/primary_model_class
    - no "'module' object is not callable" errors
  notes: "Policy module remains pure; no provider imports; deterministic downgrades; no user_text logging."
```

## Step 5 Evidence (Reliability + Quality + Safety)
```
- date: 2026-01-24
  type: step16.5_reliability_quality_safety
  staging_base: https://cognitivesystem-staging.up.railway.app
  summary: "Deterministic Step 5 wrapper added: breaker/budget short-circuit, deadlines, quality gate, safety envelope, chaos flags, observability."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - pytest -q backend/tests/test_step5_determinism.py backend/tests/test_step5_quality_gate.py backend/tests/test_step5_safety_envelope.py backend/tests/test_step5_timeouts.py
    - bash -n scripts/smoke_api_chat.sh scripts/promotion_gate.sh scripts/cost_gate_chat.sh scripts/chaos_gate.sh
  commands_staging:
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - BASE=$STAGING_BASE ./scripts/chaos_gate.sh
  expected_outcomes:
    - breaker/budget chaos flags return FALLBACK with corresponding failure_type
    - provider timeout chaos flag returns TIMEOUT with timeout_where=provider
    - quality fail chaos flag returns ASK_CLARIFY with clarifying prompt
    - safety block chaos flag returns SAFETY_BLOCKED refusal
    - /api/chat contract preserved; no user_text logging; routing decision logs intact
  notes: "Step 5 deterministic, bounded, chaos-ready; integrates with Step 4 policy without schema changes."
```

## Step 6 Evidence (Pass 1: Passive Observability)
```
- date: 2026-01-25
  type: step16.6_passive_observability
  staging_base: https://cognitivesystem-staging.up.railway.app
  summary: "Added X-Request-Id header propagation and passive chat.summary sampling (2%) without behavior changes."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - bash -n scripts/promotion_gate.sh
  commands_staging:
    - curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | sed -n '1,20p'
  expected_outcomes:
    - /api/chat responses include X-Request-Id header on success and error
    - chat.summary structured event fields contain only safe metadata; sampling deterministic; no user_text
  notes: "Pass 1 only; no behavior changes to routing/quality/safety."
```

## Step 6 Evidence (Pass 2: Observability + Offline Eval Gates)
```
- date: 2026-01-25
  type: step16.6_observability_eval_gate
  staging_base: https://cognitivesystem-staging.up.railway.app
  summary: "chat.summary contract finalized with deterministic sampling; X-Request-Id on all /api/chat responses; offline eval gate and dashboard spec documented."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - pytest -q backend/tests/test_step6_observability_contract.py backend/tests/test_step6_eval_gate_scenarios.py
    - bash -n scripts/promotion_gate.sh scripts/eval_gate.sh
  commands_staging:
    - curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | sed -n '1,20p'
    - MODE=staging BASE="$STAGING_BASE" ./scripts/promotion_gate.sh
    - ./scripts/eval_gate.sh
  expected_outcomes:
    - /api/chat headers include X-Request-Id on success and error
    - chat.summary contains only safe metadata; sampling deterministic (2% success, always on errors)
    - eval_gate.sh passes offline without network
    - dashboard spec available in docs/DASHBOARD_SPEC.md
  notes: "Passive only; no changes to routing/quality/safety; logs remain content-free (no user_text/rendered_text)."
```
