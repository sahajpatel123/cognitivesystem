# Phase 16 — Step 6: Passive Observability Upgrade

## Purpose
Provide passive, privacy-safe observability for `/api/chat` without influencing routing, cognition, Step 4 policy, or Step 5 reliability/quality/safety. All signals are exportable via structured logs only; no runtime feedback loops.

## Definitions
- **request_id**: Stable per-request identifier; propagated via `X-Request-Id` header on all `/api/chat` responses.
- **chat.summary**: Structured log event capturing safe metadata about `/api/chat` outcomes.
- **Sampling**: Deterministic decision derived from `request_id`. Errors are always emitted; successes are emitted at a fixed 2% rate.

## chat.summary Contract (fields and safety)
- `event`: "chat.summary"
- `request_id`: string
- `timestamp_utc`: ISO8601 UTC string
- `sampled`: bool (deterministic from `request_id` unless forced by error)
- `endpoint`: string ("/api/chat")
- `status_code`: int
- `latency_ms`: int
- `plan`: string (FREE/PRO/MAX or equivalent)
- `requested_mode`: string or null
- `granted_mode`: string or null
- `model_class`: string or null
- `action`: string (answer/fallback/ask_clarify/refuse/unknown)
- `failure_type`: string or null
- `failure_reason`: string or null, capped at 200 chars
- `input_tokens_est`: int or null
- `output_tokens_cap`: int or null
- `breaker_open`: bool
- `budget_block`: bool
- `budget_scope`: string or null
- `timeout_where`: string or null
- `http_timeout_ms`: int or null
- `waf_limiter`: string or null
- `subject_type`: string (e.g., anon/user)
- `subject_id_hash`: salted hash (never raw id)
- `ip_hash`: hash (never raw IP)
- `version`: service version string

Forbidden content: user_text, rendered_text, prompts, provider keys/secrets, cookies, Authorization headers, raw IPs/emails/phones. Failure reasons are capped to 200 chars.

## Sampling Rules
- Emit always when `status_code >= 400` OR `failure_type` present OR breaker/budget/timeout paths fire.
- For successes, emit if `_should_sample(request_id, rate=0.02)` returns true (deterministic SHA-256 of request_id mapped to [0,1)).

## Request ID Propagation
- All `/api/chat` responses (success and errors) include `X-Request-Id` header derived from the request context.

## Verification Checklist
- Local/CI:
  - `python3 -m compileall backend mci_backend`
  - `python3 -c "import backend.app.main; print('OK backend.app.main import')"`
  - `pytest -q backend/tests/test_step6_observability_contract.py backend/tests/test_step6_eval_gate_scenarios.py`
  - `bash -n scripts/promotion_gate.sh scripts/eval_gate.sh`
- Staging spot check (manual):
  - `STAGING_BASE=https://cognitivesystem-staging.up.railway.app`
  - `curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$STAGING_BASE/api/chat" | sed -n '1,20p'` (expect `X-Request-Id` header)

## Non-goals
- No OpenTelemetry/Datadog/Prometheus client agents.
- No runtime feedback or auto-tuning based on metrics.
- No logging of request bodies, prompts, or provider secrets.

## Retention & Privacy Guidance
- Keep structured logs minimal and time-bound; apply access controls and redaction policies externally.
- Do not persist raw user inputs or model outputs in observability streams.

## How to interpret
- Use `chat.summary` to correlate latency, failure modes, breaker/budget activity, and mode/tier decisions without exposing user content.
- Sampling ensures scalable volume while guaranteeing coverage for errors and critical paths.
