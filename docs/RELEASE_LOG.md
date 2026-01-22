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
    - whoami
    - chat_happy
    - chat_415
    - burst_429
    - release_drills_subset (if run)
    - certify_phase15_subset (if run)
  change_class: A|B|C (C forbidden)
  prod_verification:
    - health
    - db_health
    - whoami
    - chat_happy
    - chat_415
  result: pass|fail
  rollback_plan: <pointer/notes>
  notes: <short notes>
  operator: <name/handle>
  evidence_refs: <links or file refs if any>
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
    - rerun smoke (health/db/whoami/chat/415)
  post_rollback_verification:
    - health
    - db_health
    - whoami
    - chat_happy
    - chat_415
  result: completed|partial
  notes: <short notes>
  operator: <name/handle>
  evidence_refs: <links or file refs if any>
```
