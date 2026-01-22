# Release Log (Append-Only)

Use this file to record promotions and rollbacks. Do not overwrite existing entries; append new entries in chronological order. Evidence must reference staging gates and post-promotion checks. Do not paste secrets.

## Promotion Entry Template
```
- release_id: <YYYYMMDD-HHMM-rc1>
  type: promotion
  commit_sha: <sha>
  environment: production
  gates_run:
    - health
    - db_health
    - whoami
    - chat_happy
    - chat_415
    - burst_429
    - release_drills_subset (if run)
    - certify_phase15_subset (if run)
  result: pass|fail
  notes: <short notes>
  operator: <name/handle>
  evidence_refs: <links or file refs if any>
```

## Rollback Entry Template
```
- release_id: <YYYYMMDD-HHMM-rb1>
  type: rollback
  commit_sha: <sha rolled back to>
  environment: production
  reason: <trigger e.g., 5xx spike, auth failure>
  actions:
    - redeploy last known good
    - rerun smoke (health/db/whoami/chat/415)
  result: completed|partial
  notes: <short notes>
  operator: <name/handle>
  evidence_refs: <links or file refs if any>
```
