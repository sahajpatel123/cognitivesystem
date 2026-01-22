# Phase 16 Step 2 — Performance Budgets & Timeouts (LOCK)

## Purpose
Bound /api/chat latency and prevent hangs via explicit budgets, dependency timeouts, and shared clients—without changing cognition logic or contracts. Staging-first: enforce in staging before promoting to production.

## Budgets (Targets & Caps)
- Total /api/chat wall-clock cap: 20,000 ms (API_CHAT_TOTAL_TIMEOUT_MS, env override).
- Model call cap: 12,000 ms (MODEL_CALL_TIMEOUT_MS, env override).
- Outbound HTTP (shared client):
  - Total/read timeout: 8.0 s (OUTBOUND_HTTP_TIMEOUT_S)
  - Connect timeout: 3.0 s (OUTBOUND_HTTP_CONNECT_TIMEOUT_S)
  - Pool limits: max_connections=20, max_keepalive_connections=10, keepalive_expiry=30s
- Latency SLO placeholders (fill in ops process):
  - p50: <fill> ms, p95: <fill> ms, p99: <fill> ms
  - Hard cap: 20s total per /api/chat

## Scope
- Applies only to /api/chat. No cognition changes. Observability stays passive.
- No changes to /health or /db/health.
- Uses env guard rails from Phase 16 Step 2 (APP_ENV, DEBUG_ERRORS=0 in staging/prod, CORS/DB allowlists).

## Dependency Timeouts (HTTP/Model)
- Model call timeout: min(remaining budget, MODEL_CALL_TIMEOUT_MS) with 1s floor.
- Shared HTTP client (httpx) with bounded timeouts/limits above.
- JWKS fetch and outbound calls reuse shared client; no per-request clients.

## Cold-Start Notes
- Railway restarts may cause first request latency; budgets still enforced.
- If cold-start causes budget overrun, expect governed fallback with timeout reason.

## Evidence / Drills (Staging Gate)
- Run MODE=staging BASE=<staging> ./scripts/promotion_gate.sh
- Optional perf smoke (safe payload “hi”):
  - scripts/perf_gate_chat.sh (if available)
  - Verify: /health, /db/health, /auth/whoami, chat happy (“hi”), burst (15 requests) → expect 200 then 429, no 500.
- Observe logs: request_id, latency_ms, budget_ms_total, budget_ms_remaining_at_model_start, timeout_where, model_timeout_ms, http_timeout_ms. No user_text.

## Invalidation Triggers
- p95 exceeds target without an updated budget and re-lock.
- Frequent timeouts (> agreed threshold) or unbounded hangs.
- Provider/model changes that alter latency envelope without updated lock.
- Introducing unbounded clients or removing timeouts.
- Any cognition/personalization changes or raw prompt logging.

## Status
- Phase 16 Step 2 Status: COMPLETE ✅
- Locked on: 2026-01-22
