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
    - /api/chat (json {"message":"hi"}) -> 200 with governed response
    - /api/chat (text/plain) -> 415
    - cost gate with lowered limits -> 429 FailureType.BUDGET_EXCEEDED
  env_toggles_for_cost_drill:
    - temporarily lower COST_GLOBAL_DAILY_TOKENS, COST_IP_WINDOW_TOKENS, COST_ACTOR_DAILY_TOKENS, COST_REQUEST_MAX_TOKENS, COST_REQUEST_MAX_OUTPUT_TOKENS
    - revert to defaults after drill
  notes: "No identity endpoint used in smoke; matches OpenAPI contract."
```
