# Phase16 Step 7B: Security Upgrade & Abuse Evolution

## Threat Model (scope)
- Automated/bot traffic probing `/api/chat` and auth endpoints.
- Anonymous abuse without authentication.
- Misconfigured clients lacking basic headers.
- Replay of scripted requests over non-HTTPS in non-local environments.

## Scoring Rubric (deterministic)
- Start score=0; cap at 100.
- +30 missing/blank User-Agent.
- +15 missing/blank Accept.
- +15 missing/blank Content-Type on POST /api/chat.
- +10 method unexpected for endpoint (e.g., GET on /api/chat).
- +15 sensitive path and no auth.
- +10 waf_limiter contains any of: limited, blocked, rate, waf (case-insensitive).
- +10 request_scheme != "https" when is_non_local=True.

## Thresholds & Enforcement
- score >= 90: action BLOCK, HTTP 403, Retry-After 600s.
- 70 <= score < 90: action RATE_LIMIT, HTTP 429, Retry-After 60s.
- score < 70: action ALLOW.
- Response body: ContractChatResponse with FALLBACK action; failure_type ABUSE_BLOCKED (403) or RATE_LIMITED (429); deterministic rendered_text.
- Structured chat.summary fields include abuse_score, abuse_action, abuse_allowed, abuse_reason (no user_text).

## Security Headers Contract
- Always set: X-Content-Type-Options=nosniff, Referrer-Policy=no-referrer, X-Frame-Options=DENY, Permissions-Policy="geolocation=(), microphone=(), camera=()", Cache-Control=no-store.
- HSTS: Strict-Transport-Security="max-age=15552000; includeSubDomains" only when https AND non-local env/host.

## Cookie Hardening
- anon_session cookie: HttpOnly, SameSite=Lax preserved; Secure set only when https AND non-local.

## Privacy Constraints
- Never log user_text or rendered_text.
- Reasons are short, deterministic, and contain no PII.

## Operational Notes
- Deterministic scoring; no learning/ML/state.
- Only /api/chat enforcement path changes; other endpoints unaffected.
- Tuning knobs: environment classification (is_non_local), waf_limiter strings, header presence.

## Non-Goals
- No CAPTCHA or interactive challenges.
- No provider/model changes.
- No database/schema changes.
- No new cookies or auth flows.
