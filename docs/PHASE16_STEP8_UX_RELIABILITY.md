# Phase 16 Step 8A — UX Reliability Signaling

## UX States
- OK
- NEEDS_INPUT
- RATE_LIMITED
- QUOTA_EXCEEDED
- DEGRADED
- BLOCKED
- ERROR

## Mapping (deterministic, bounded)
- 200 + action ASK_CLARIFY → NEEDS_INPUT
- 200 otherwise → OK
- 415 or 422 → NEEDS_INPUT
- 429 → RATE_LIMITED (unless QUOTA_EXCEEDED rule below applies)
- 503 → DEGRADED (provider unavailable / temporarily unavailable → DEGRADED)
- failure_type BUDGET_EXCEEDED or failure_reason mentions budget/quota → QUOTA_EXCEEDED (preferred over RATE_LIMITED)
- failure_type ABUSE_BLOCKED → BLOCKED
- status 401 or 403 → BLOCKED
- 5xx otherwise → ERROR
- default fallback → ERROR

## Headers Contract
- `X-UX-State` is always included on `/api/chat` responses (success and errors) with one of the states above.
- `X-Cooldown-Seconds` is included only when a meaningful retry hint exists (derived from Retry-After) and the state/status is rate-limited/degraded/quota.
- Existing headers (security, X-Request-Id) remain unchanged.

## Cooldown Derivation
- Parse `Retry-After` header when it is an integer number of seconds.
- Clamp to the range 1..86400 seconds.
- Only emit `X-Cooldown-Seconds` (and payload `cooldown_seconds`) when status is 429/503 or ux_state is RATE_LIMITED/DEGRADED/QUOTA_EXCEEDED.

## Contract Fields (additive)
- `ux_state: str` (default "ERROR" when not set)
- `cooldown_seconds: Optional[int]` (default null)
- No breaking changes to existing ContractChatResponse schema.

## Non-goals / Safety
- Does **not** change routing, model selection, entitlements, or Step 5/6/7 decision logic.
- Does **not** log `user_text` or `rendered_text` in headers or structured events.
- Deterministic only; no randomness or automatic upgrades.

## Client Expectations
- Clients can render stable states (needs input, blocked, rate-limited, quota exceeded, degraded, error) without inspecting failure_reason.
- Cooldown hints enable UX retry timers aligned with Retry-After.

## Step 8B (Frontend UX Reliability Layer)
- Consumes headers: X-UX-State, X-Cooldown-Seconds (optional), X-Request-Id from /api/chat responses.
- UI SystemStatus strip renders title/body per UX state and shows cooldown countdown; aria-live="polite" for announcements.
- Cooldown behavior: send input disabled while countdown > 0; countdown derived from clamped Retry-After (0..86400) using client clock.
- Retry affordance: retry button available for ERROR/RATE_LIMITED/DEGRADED when provided; disabled during cooldown.
- Request ID: displayed truncated (last 8 chars) with copy control for full value; no user_text/rendered_text shown.
- Accessibility: buttons use disabled + aria-disabled; status region aria-live polite; mobile-responsive layout.

## Non-goals (Step 8B)
- No changes to routing, cognition, entitlements, safety, or backend decision logic.
- Does not alter /api/chat schema (still {"user_text": "..."}).
- Does not log or display user_text/rendered_text in status surfaces.

## Verification Checklist (Step 8B)
- Headers are read from /api/chat and mapped via normalizeUxState/clampCooldownSeconds.
- Cooldown disables send and counts down to zero, then re-enables input.
- SystemStatus renders correct copy per state and supports retry (when provided) respecting cooldown.
- Request ID copy button copies full ID while showing truncated form.
- Gate: scripts/ux_frontend_gate.sh present/executable; promotion_gate.sh reports Step 8B files.
