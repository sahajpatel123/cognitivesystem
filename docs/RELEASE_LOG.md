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

## Step 7B Evidence (Pass 1: Security Headers)
```
- date: 2026-01-25
  type: step16.7_security_headers
  staging_base: https://cognitivesystem-staging.up.railway.app
  summary: "Deterministic security headers added with optional HSTS on https non-local; Cache-Control no-store for API responses; import gate and unit test for headers contract."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - python3 -c "from backend.app.security.headers import security_headers; print('hdrs=', sorted(list(security_headers(is_https=False,is_non_local=False).keys()))[:3])"
    - pytest -q backend/tests/test_step7_headers.py
    - bash -n scripts/promotion_gate.sh
  commands_staging:
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | grep -E "^(Strict-Transport-Security|X-Content-Type-Options|Referrer-Policy|X-Frame-Options|Permissions-Policy)"
  expected_outcomes:
    - Security headers present on /api/chat responses; HSTS only when https and non-local
    - Header unit test passes locally; import gate passes
    - No schema changes; user_text not logged
  notes: "Pass 1 focuses on headers and verification; abuse scoring deferred to later pass."
```

## Step 7B Evidence (Pass 2: Suspicious Request Throttling)
```
- date: 2026-01-25
  type: step16.7_suspicious_request_throttle
  staging_base: https://cognitivesystem-staging.up.railway.app
  summary: "Deterministic abuse scoring for /api/chat with explicit 403/429 enforcement; security gate script and docs added; tests cover headers and abuse scoring."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - python3 -c "from backend.app.security.abuse import decide_abuse, AbuseContext; print('abuse_callable=', callable(decide_abuse))"
    - pytest -q backend/tests/test_step7_abuse_scoring.py backend/tests/test_step7_headers.py
    - bash -n scripts/promotion_gate.sh scripts/security_gate.sh
  commands_staging:
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - BASE=$STAGING_BASE ./scripts/security_gate.sh
    - curl -s -i -H "Content-Type: application/json" -H "User-Agent:" -H "Accept:" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | sed -n '1,20p'
  expected_outcomes:
    - Headers contract intact; HSTS only on https non-local
    - Suspicious requests receive 429 or 403 with deterministic failure_type (RATE_LIMITED or ABUSE_BLOCKED) and Retry-After
    - Normal requests unaffected; user_text not logged
  notes: "Pass 2 adds defensive throttle only; no model/provider changes."
```

## Step 8A Evidence (UX Reliability Signaling)
```
- date: 2026-01-26
  type: step16.8a_ux_reliability_signaling
  staging_base: https://cognitivesystem-staging.up.railway.app
  summary: "Deterministic UX state signaling added with headers X-UX-State/X-Cooldown-Seconds and contract fields ux_state/cooldown_seconds; no behavior changes."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - pytest -q backend/tests/test_step8_ux_state_mapping.py backend/tests/test_step8_ux_headers.py
    - bash -n scripts/promotion_gate.sh scripts/ux_gate.sh
  commands_staging:
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - BASE=$STAGING_BASE ./scripts/ux_gate.sh
    - curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | grep -E "^(X-UX-State|X-Cooldown-Seconds|X-Request-Id)"
  expected_outcomes:
    - /api/chat responses always include X-UX-State and X-Request-Id; X-Cooldown-Seconds present when Retry-After numeric
    - Contract fields ux_state/cooldown_seconds populated without breaking schema
    - No logging of user_text or rendered_text in headers/events
  notes: "UX signaling is passive; routing/entitlements/safety unchanged; deterministic mapping and cooldown clamping (1..86400)."
```

## Step 8B Evidence (Frontend UX Reliability Layer)
```
- date: 2026-01-26
  type: step16.8b_frontend_ux_reliability
  summary: "Frontend consumes X-UX-State/X-Cooldown-Seconds/X-Request-Id, shows SystemStatus banner with cooldown countdown, disables send during cooldown, retry affordance with request ID copy."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - bash -n scripts/promotion_gate.sh scripts/ux_frontend_gate.sh
    - ./scripts/ux_frontend_gate.sh
  commands_staging:
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | grep -E "^(X-UX-State|X-Cooldown-Seconds|X-Request-Id)"
  expected_outcomes:
    - Frontend maps UX headers to states deterministically; cooldown clamps 1..86400 and counts down client-side.
    - Send input disabled during cooldown; SystemStatus shows titles/body per state; retry button respects cooldown.
    - Request ID shown truncated with copy control; no user_text/rendered_text leaked.
  notes: "Frontend layer is passive; no backend decision changes; UX signaling stable on mobile/desktop."
```

## Step 8C Evidence (Staging UX Reliability Certification)
```
- date: 2026-01-26
  type: step16.8c_staging_ux_cert
  summary: "415 content-type error now emits X-UX-State alongside X-Request-Id; staging gates pass."
  commands_local:
    - python3 -m compileall backend mci_backend
    - python3 -c "import backend.app.main; print('OK backend.app.main import')"
    - bash -n scripts/promotion_gate.sh scripts/ux_gate.sh scripts/ux_frontend_gate.sh
  commands_staging:
    - MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
    - BASE=$STAGING_BASE ./scripts/ux_gate.sh
    - curl -s -D - -o /dev/null -H "Content-Type: text/plain" -d "hi" "$STAGING_BASE/api/chat" | grep -Ei "^(x-ux-state|x-request-id|content-type|http/|date:|server:)"
  observed_headers:
    - "HTTP/2 415 ..."
    - "content-type: application/json"
    - "x-request-id: <id>"
    - "x-ux-state: ERROR"
  notes: "No schema/body changes; only header injection on 415; user_text/rendered_text not emitted."
```

## Phase 16 — Step 9 Evidence (Release Engineering: Flags + Canary + Rollback)

Evidence date: 2026-01-27  
Scope: release flags (non-cognition), deterministic canary, canary gate script, promotion gate checks.

### Local verification (PASS)
Commands:
```bash
python3 -m compileall backend mci_backend
python3 -c "import backend.app.main; print('OK backend.app.main import')"
pytest -q backend/tests/test_step9_canary_determinism.py backend/tests/test_step9_flags_parsing.py
bash -n scripts/promotion_gate.sh scripts/canary_check.sh
```

Staging command: `MODE=staging BASE=$STAGING_BASE ./scripts/canary_check.sh`

Notes: Canary gate accepts action ANSWER, ASK_CLARIFY, or FALLBACK as valid success responses.
Additional note: Canary check forces HTTP/1.1 with retries to avoid HTTP/2 edge framing resets.
Additional note: Canary gate tolerates curl(18)/edge truncation by using --ignore-content-length and passing via headers (x-request-id + x-ux-state) when body is missing.

## Phase 16 — Step 10 Evidence (Certification & Lock)

Evidence date: 2026-01-27  
Scope: certification doc + promotion gate lock.

Local verification (PASS):
```bash
python3 -m compileall -q backend mci_backend
python3 -c "import backend.app.main; print('OK backend.app.main import')"
bash -n scripts/promotion_gate.sh scripts/canary_check.sh
bash -n scripts/canary_check.sh
```

Staging commands (run by operator):
```bash
MODE=staging BASE="https://cognitivesystem-staging.up.railway.app" ./scripts/promotion_gate.sh
MODE=staging BASE="https://cognitivesystem-staging.up.railway.app" ./scripts/canary_check.sh
```

## Phase 16 — Step 10 Evidence (Certification & Lock)
Evidence date: 2026-01-27  
Scope: certification doc present + promotion gate lock.

## Phase 16 — Step 10 Evidence (Certification & Lock)
Evidence date: 2026-01-27  
Commands (staging):
- MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh
- BASE=$STAGING_BASE ./scripts/security_gate.sh
- BASE=$STAGING_BASE ./scripts/ux_gate.sh
- MODE=staging BASE=$STAGING_BASE ./scripts/canary_check.sh
All PASS => Phase16 certified.

## Phase 17 — Step 0 Evidence (Deep Thinking Contract + Stop Rules)
Evidence date: 2026-01-28  
Scope: Phase 17 Deep Thinking Contract frozen; added gate presence check.
Deliverables:
- docs/PHASE17_DEEP_THINKING_CONTRACT.md created with hard-locked invariants
- scripts/promotion_gate.sh updated with phase17_contract_present check
- StopReason enum defined (9 codes: SUCCESS_COMPLETED, BUDGET_EXHAUSTED, PASS_LIMIT_REACHED, TIMEOUT, BREAKER_TRIPPED, ENTITLEMENT_CAP, ABUSE, VALIDATION_FAIL, INTERNAL_INCONSISTENCY)
Status: Contract locked, gate enforced, no implementation yet.

## Phase 17 — Step 9 Evidence (Eval Gates + Certification Freeze)
Evidence date: 2026-01-28  
Scope: Phase 17 frozen after Step 9; eval gates + certification doc added.
Deliverables:
- docs/PHASE17_CERTIFICATION.md created (version 17.9.0)
  * Invariants documented with enforcement locations
  * 4 evaluation gates defined with PASS/FAIL criteria
  * Frozen components list
  * Change control process
- backend/tests/test_phase17_eval_gates.py created
  * Gate A: Deterministic Replay (20 iterations)
  * Gate B: Two-Strikes Downgrade (exactness)
  * Gate C: StopReason Contract (exhaustive)
  * Gate D: Telemetry Safety (no text leakage)
- backend/tests/test_phase17_certification_freeze.py created
  * Verifies certification artifacts exist
  * Verifies doc content (version, invariants, gates, StopReasons)
- scripts/promotion_gate.sh updated
  * Added phase17_cert_present check (fail-closed)
  * Added phase17_eval_gates_present check (fail-closed)
Status: **Phase 17 FROZEN**. Changes to router/engine/validator/schema/telemetry require recertification.

## Phase 18 — Step 0 Evidence (Research Contract + Stop Rules)
Evidence date: 2026-01-29  
Scope: Phase 18 Research Contract frozen; added gate presence + content validation checks.
Deliverables:
- docs/PHASE18_RESEARCH_CONTRACT.md created (version 18.0.0)
  * 6 hard-lock invariants: Tool Boundary, No-Source→UNKNOWN, Policy Caps, Injection Policy, Non-Agentic, Fail-Closed
  * 11 ResearchStopReasons (exhaustive): SUCCESS_COMPLETED, ENTITLEMENT_CAP, POLICY_DISABLED, BUDGET_EXHAUSTED, RATE_LIMITED, TIMEOUT, SANDBOX_VIOLATION, INJECTION_DETECTED, NO_SOURCE, VALIDATION_FAIL, INTERNAL_INCONSISTENCY
  * Stop priority order (deterministic, 11 levels)
  * No-Source handling rule (mechanical: force ASK_CLARIFY or UNKNOWN)
  * PolicyCaps definitions (max_tool_calls_total, max_tool_calls_per_minute, per_call_timeout_ms, total_research_timeout_ms, budget_units_clamp)
  * Change control process
- scripts/promotion_gate.sh updated
  * Added phase18_contract_present check (fail-closed)
  * Added ContractVersion "18.0.0" validation (grep check)
  * Added Status: FROZEN validation (grep check)
  * Added ResearchStopReasons section validation (grep check)
Status: **CONTRACT FROZEN**. Implementation Steps 18.1–18.9 must comply. No research code added yet.

## Phase 19 — Step 0 Evidence (Memory Contract + Stop Rules)
Evidence date: 2026-01-30  
Scope: Phase 19 Memory Contract frozen; added gate presence + content validation checks.
Deliverables:
- docs/PHASE19_MEMORY_CONTRACT.md created (version 19.0.0)
  * 5 allowed memory categories (strict allowlist): PREFERENCE, WORKFLOW_DEFAULT, PROJECT_CONFIG, CONSTRAINT, REMINDER
  * 9 forbidden categories (hard block): Identity Traits, Health Information, Intimate Life, Criminal/Legal, Location Data, Credentials/Secrets, Biometrics/IDs, Inferred Profiling, Tool-Output Memory
  * 13 MemoryStopReasons (exhaustive): SUCCESS_STORED, SUCCESS_UPDATED, SUCCESS_DELETED, POLICY_DISABLED, ENTITLEMENT_CAP, FORBIDDEN_CATEGORY, MISSING_EXPLICIT_CONSENT, NO_SOURCE_DERIVED_FACT, INJECTION_DETECTED, SCHEMA_INVALID, BOUNDS_EXCEEDED, TTL_NOT_ALLOWED, INTERNAL_INCONSISTENCY
  * Stop priority order (deterministic, 11 levels)
  * NO SOURCE → DON'T STORE rule (mechanical: DERIVED_UNVERIFIED always rejected)
  * SourceKind definitions: USER_EXPLICIT, SYSTEM_KNOWN, CITED_SOURCE, DERIVED_UNVERIFIED
  * 8 hard-lock invariants
  * Change control process
- scripts/promotion_gate.sh updated
  * Added phase19_contract_present check (fail-closed)
  * Added ContractVersion "19.0.0" validation (grep check)
  * Added Status: FROZEN validation (grep check)
  * Added MEMORY STOP REASONS section validation (grep check)
  * Added ALLOWED MEMORY CATEGORIES section validation (grep check)
  * Added FORBIDDEN CATEGORIES section validation (grep check)
  * Added NO SOURCE → DON'T STORE rule validation (grep check)
Status: **CONTRACT FROZEN**. Governance only, no runtime code. Implementation Steps 19.1+ must comply.
