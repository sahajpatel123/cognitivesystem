# Phase 15 — Step 6: Observability & Monitoring (Passive Only)

## Principles (Passive, No Feedback into Cognition)
- Observability is passive; telemetry never affects cognition, model prompts, or behavior.
- Never log or store `user_text`, model outputs, JWTs, cookies, API keys, or DATABASE_URL.
- Stable error contracts remain: WAF/plan guards return structured 4xx/5xx JSON; no HTML errors.
- Fail-open for telemetry: logging/DB write failures must not break requests.

## What We Log for `/api/chat` (single end-of-request event)
- `type`: `"api_chat"`
- `request_id`: `x-railway-request-id` if present, else generated UUID
- `route`, `method`, `status_code`, `latency_ms`
- `plan` (resolved plan tier)
- `subject_type` and `hashed_subject` (hash with IDENTITY_HASH_SALT; never raw IDs or IPs)
- WAF decision: `waf_decision`, `waf_error`, `waf_limiter` (`db` or `memory-fallback`)
- Plan/quota decision: `plan_decision`, `plan_error`
- Token estimates: `token_estimate_in`, `token_estimate_out_cap` (numeric only)
- `error_code` (if any), `invocation_log_written` (true/false)
- **Not logged:** `user_text`, payload, headers, cookies, JWT, model outputs.

## Metrics (log-based, optional)
- Request counts by status_code
- Latency distribution (ms)
- WAF blocks by error_code
- Quota blocks by error_code
- If Prometheus is enabled later: keep labels minimal (route, status_code); never include subject IDs/IPs.

## Invocation Logs (best-effort)
- Table: `invocation_logs` (ts, route, status_code, latency_ms, error_code, hashed_subject, session_id, model_used?)
- Write is best-effort; failures are swallowed and reflected as `invocation_log_written=false`.
- No prompts, payloads, or model outputs stored.

## Retention Policy (recommendation)
- Keep `invocation_logs` for 14–30 days max; purge/TTL via DB job.
- No sensitive content retained; only redacted metadata.

## Smoke Tests (passive only)
1) Normal:
```bash
curl -i -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"user_text":"hi"}'
```
Expect 200; log contains `type=api_chat`, hashed_subject, status_code=200.
2) Wrong content-type:
```bash
curl -i -X POST "$BASE/api/chat" -H "Content-Type: text/plain" -d 'hi'
```
Expect 415 `content_type_invalid`; log status_code=415, waf_error=content_type_invalid.
3) Burst (may trigger 429):
```bash
for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"user_text":"hi"}'; done
```
Expect some 429; logs show waf_decision=blocked or plan_decision=blocked with error_code.

## Monitoring Checklist
- Verify `/api/chat` logs include request_id, hashed_subject, status_code, latency_ms.
- Confirm no `user_text` or payload appears in logs or DB.
- Confirm invocation_log writes do not fail the request (invocation_log_written=false when DB unavailable).
- Ensure WAF/plan guard decisions are present and sanitized.
- Keep `METRICS_ENABLED` default off; enable only if Prometheus endpoint is intentionally deployed.
