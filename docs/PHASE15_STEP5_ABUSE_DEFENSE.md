# Phase 15 — Step 5: Abuse Defense (WAF Layer)

## Scope (Implemented Now — “Above the Line”)
- Request shaping for `/api/chat`:
  - Enforce `Content-Type: application/json`
  - Max body bytes: `WAF_MAX_BODY_BYTES`
  - `user_text` required, string, max length: `WAF_MAX_USER_TEXT_CHARS`
- Rate limiting and lockouts (deterministic):
  - Per-IP burst + sustained windows
  - Per-subject (user/anon) burst + sustained windows
  - Escalating lockout schedule with cooldown reset
  - Best-effort DB-backed limiter using existing `rate_limits` table; per-process in-memory fallback with `X-WAF-Limiter: memory-fallback`
- Clear error contract (no cognition changes):
  - HTTP 415: `content_type_invalid`
  - HTTP 413: `payload_too_large`, `user_text_too_long`
  - HTTP 400: `invalid_json`, `invalid_payload`, `invalid_content_length`
  - HTTP 429: `rate_limited` with `retry_after_seconds` and `limit_scope` (`ip`/`subject`)
  - JSON shape: `{ "ok": false, "error_code": "...", "message": "...", "retry_after_seconds": <int?>, "limit_scope": "ip|subject" }`

## Not Implemented (Coming Soon / Doc-Only)
- CAPTCHA / Turnstile / hCaptcha
- Redis / Cloudflare WAF integration
- Device fingerprinting beyond existing identity hashing
- Content inspection / prompt analysis (forbidden)

## Limits (defaults; override via env)
- Body bytes: `WAF_MAX_BODY_BYTES=200000`
- user_text chars: `WAF_MAX_USER_TEXT_CHARS=8000`
- IP burst: `WAF_IP_BURST_LIMIT=5` per `WAF_IP_BURST_WINDOW_SECONDS=10`
- IP sustained: `WAF_IP_SUSTAIN_LIMIT=60` per `WAF_IP_SUSTAIN_WINDOW_SECONDS=60`
- Subject burst: `WAF_SUBJECT_BURST_LIMIT=8` per `WAF_SUBJECT_BURST_WINDOW_SECONDS=10`
- Subject sustained: `WAF_SUBJECT_SUSTAIN_LIMIT=120` per `WAF_SUBJECT_SUSTAIN_WINDOW_SECONDS=60`
- Lockout schedule: `WAF_LOCKOUT_SCHEDULE_SECONDS=30,120,600,3600` (escalating)
- Lockout cooldown reset: `WAF_LOCKOUT_COOLDOWN_SECONDS=21600`
- Enforced routes: `WAF_ENFORCE_ROUTES=/api/chat`

## Architecture Notes
- Implemented as a FastAPI dependency `waf_dependency` running before the plan guard on `/api/chat`.
- DB-first limiter using `rate_limits` table (no schema change); in-memory fallback if DB unavailable; headers include `X-WAF-Limiter: memory-fallback` when fallback used.
- IP extraction: first `X-Forwarded-For` entry, else `request.client.host`.
- IPs hashed with `IDENTITY_HASH_SALT` before storage; subjects unchanged (user/anon IDs).
- No raw prompts stored or logged.
- Observability remains passive; no cognition logic touched.
- Railway runs behind a proxy; uvicorn must be started with `--proxy-headers --forwarded-allow-ips "100.64.0.0/10"` so IP rate limiting sees the real client IP without trusting arbitrary headers.

## Error Examples
- Invalid content type:
  - 415 `{ "ok": false, "error_code": "content_type_invalid", "message": "Content-Type must be application/json" }`
- Payload too large:
  - 413 `{ "ok": false, "error_code": "payload_too_large", "message": "Payload exceeds maximum size." }`
- Rate limited (IP):
  - 429 `{ "ok": false, "error_code": "rate_limited", "message": "Too many requests from IP.", "retry_after_seconds": 30, "limit_scope": "ip" }`

## Smoke Tests (replace BASE with your Railway URL)
1) Normal request:
```bash
curl -i -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"user_text":"hi"}'
```
2) Content-Type rejected:
```bash
curl -i -X POST "$BASE/api/chat" -H "Content-Type: text/plain" -d 'hi'
```
3) Payload too large:
```bash
python - <<'PY' | curl -i -X POST "$BASE/api/chat" -H "Content-Type: application/json" --data-binary @-
import json; print(json.dumps({"user_text":"x"*9000}))
PY
```
4) Rate limit burst (expect 429):
```bash
for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"user_text":"hi"}'; done
```
5) Lockout retry-after honored:
```bash
curl -i -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"user_text":"hi"}'
# If 429, note Retry-After and wait before retrying
```

## Boundaries
- Cognition logic, prompts, and governed behavior remain unchanged.
- No prompt storage, no content logging.
- Enforcement only on `/api/chat`; health/auth endpoints untouched.
