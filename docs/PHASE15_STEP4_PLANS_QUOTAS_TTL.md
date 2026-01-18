# Phase 15 — Step 4: Plans, Quotas, TTL (Above-the-Line Only)

## Scope (implemented now)
- Plan tiers: **FREE / PRO / MAX** with deterministic limits
- Enforced per request (pre-check):
  - Daily requests cap
  - Daily token budget cap (input + max allowed output)
  - Max input tokens (payload cap)
- Enforced at/after model:
  - Max output tokens per response (best-effort: provider cap if supported + deterministic clamp)
- Post-call accounting (best-effort): requests + tokens written to `quotas` table
- Enforcement applies **only** to the governed chat endpoint `/api/chat`

## Coming soon (not implemented in this step)
- Concurrency limits
- Priority / queueing
- Thinking mode / research mode
- Web queries budget
- File upload limits
- Server-stored chat history / transcripts

## Plan limits (single source of truth)
| Plan | Requests/day | Token budget/day | Max input tokens | Max output tokens |
| --- | --- | --- | --- | --- |
| FREE | 50 | 25,000 | 8,000 | 800 |
| PRO | 300 | 250,000 | 32,000 | 2,500 |
| MAX | 1,500 | 1,500,000 | 128,000 | 6,000 |

Notes:
- Token estimation uses a deterministic approximation (chars/4) and does **not** log content.
- Budget pre-check uses: `input_tokens + max_output_tokens` (worst case).
- Actual tokens recorded post-call use estimated input + rendered output (clamped).

## Plan resolution
- Default plan: FREE (override with `PLAN_DEFAULT` if desired).
- Overrides via env allowlists:
  - `PRO_SUBJECTS="uuid1,uuid2"`
  - `MAX_SUBJECTS="uuid3,uuid4"`
- Subject id comes from identity context (user id, anon id, or hashed IP fallback).

## Enforcement flow (only `/api/chat`)
1) Payload size guard (existing `MAX_PAYLOAD_BYTES` + JSON validation).
2) Plan + limits resolution from identity.
3) Max input tokens check → `413 input_too_large`.
4) Daily requests cap → `429 requests_limit_exceeded`.
5) Daily token budget cap → `429 token_budget_exceeded`.
6) Governed pipeline executes; output is deterministically clamped to plan `max_output_tokens`.
7) Post-accounting best-effort: increments requests + token usage in `quotas` (fail-open on DB issues).

### Error response shape
```json
{
  "status": "error",
  "error_code": "input_too_large | requests_limit_exceeded | token_budget_exceeded",
  "message": "...",
  "plan": "free|pro|max",
  "limit": <number>,
  "used": <number>,
  "reset_at": "<iso timestamp>" // when available
}
```

## TTL interpretation (this step)
- Session validity remains bounded by `sessions.expires_at` (see Step 2).
- Quota window resets daily (`date`, `reset_at` fields).
- No server-stored chat history or transcript TTL is introduced in this step.

## Database touchpoints
- Uses existing `quotas` table (schema from Phase 15 Step 2).
- Operations are best-effort; DB failures do **not** block chat (fail-open with warning).

## Environment variables
- `PLAN_DEFAULT` (optional, default `free`)
- `PRO_SUBJECTS` (csv of subject_ids)
- `MAX_SUBJECTS` (csv of subject_ids)
- Existing identity/env variables from prior steps still apply.

## Endpoint reference
- **POST** `/api/chat` — governed chat (limits enforced)
- No changes to:
  - `/health`
  - `/db/health`
  - `/auth/*`
