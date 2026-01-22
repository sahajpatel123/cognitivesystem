# Phase 16 — Step 3: Cost Control Engine (LOCK)

Status: LOCKED ✅ (2026-01-22)

## Purpose
Make cost a first-class, deterministic safety rail for `/api/chat` by enforcing explicit token budgets, circuit breakers, and user-visible cost failure responses without altering cognition truth rules.

## Definitions
- **Budget scope**: where limits apply (global/day, per-IP rolling window, per-actor/day, per-request).
- **Actor key**: preferred `user_id`, else anon cookie ID, else hashed IP.
- **Cost units**: token counts (input/output/total) used for budgeting.
- **Breaker**: per provider+model guard that opens after repeated dependency failures.
- **Outcome codes**: success, timeout, provider_down, budget_blocked, breaker_open, other_error.

## Env Vars (defaults)
- COST_GLOBAL_DAILY_TOKENS=500000
- COST_IP_WINDOW_SECONDS=3600
- COST_IP_WINDOW_TOKENS=20000
- COST_ACTOR_DAILY_TOKENS=50000
- COST_REQUEST_MAX_TOKENS=6000
- COST_REQUEST_MAX_OUTPUT_TOKENS=1200
- COST_BREAKER_FAIL_THRESHOLD=5
- COST_BREAKER_WINDOW_SECONDS=60
- COST_BREAKER_COOLDOWN_SECONDS=120
- COST_EVENTS_RING_SIZE=500
- COST_LOG_LEVEL=INFO

## Budget Rules
- Global daily total tokens cap.
- Per-IP rolling window cap (window seconds + token limit).
- Per-actor daily cap when actor_key available; no-op if missing.
- Per-request caps for total and output tokens; reject early if estimated tokens exceed cap.
- No cross-replica sync; per-instance only (documented limitation).

## Circuit Breaker
- Key: provider+model (or route label).
- Threshold: COST_BREAKER_FAIL_THRESHOLD failures within COST_BREAKER_WINDOW_SECONDS.
- Cooldown: COST_BREAKER_COOLDOWN_SECONDS after opening; half-open allows one probe then re-closes or re-opens.
- Failures counted for timeouts or explicit provider errors; user errors do not trip breaker.

## Deterministic Fallback Matrix
- Budget exceeded → HTTP 429, failure_type=BUDGET_EXCEEDED, action=FALLBACK, retry_after hint if available.
- Breaker open → HTTP 503, failure_type=PROVIDER_UNAVAILABLE, action=FALLBACK, includes `retry_after_s`.
- No hidden provider swapping; if a deterministic single fallback is used, must be declared with `fallback_used=true` and capped to one hop. (Current step returns failure; no new routing.)

## User-Visible Response Rules
- Preserve existing chat contract keys; add failure_type/failure_reason as needed.
- Rendered text is concise, sanitized; no secrets or user text echoed.
- No silent degradation: cost blocks are explicit with HTTP status 429/503.

## Logging & Privacy
- Never log user_text or prompts.
- Log metadata only: request_id, route, actor_key hash, ip_hash, model/provider, tokens, cost_units, outcome, latency_ms, budget_scope hit, breaker state.
- In-memory ring buffer of recent events (size COST_EVENTS_RING_SIZE) for debugging; not exposed.

## Evidence Checklist
- Import gates: `python3 -c "import backend.app.cost.policy"` and `python3 -c "import backend.app.main"`.
- `python3 -m compileall backend mci_backend`
- `BASE=... ./scripts/smoke_api_chat.sh`
- `BASE=... MODE=staging ./scripts/cost_gate_chat.sh` (burst + observe cost responses when limits configured)
- Optional breaker drill: `./scripts/cost_drill_breaker.sh` (if run)

## Invalidation Triggers
- Any cognition/truth-rule change (Phase 15 lock).
- Any logging of user_text/prompts.
- Silent degradation of cost enforcement.
- Missing staging import gates or Railway boot errors.

## Notes / Limitations
- In-memory budgets are per-instance; multi-replica fairness requires later infra work.
- Token estimates fallback to simple heuristics when provider usage not returned.
