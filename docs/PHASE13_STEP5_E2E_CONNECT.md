# Phase 13 — Step 5: E2E Chat Connection

## Purpose & Scope
Connect the Product → Chat UI to the governed backend so user input flows through the certified pipeline and renders governed responses, without granting UI authority or adding cognition.

## Trust Boundary
- UI is untrusted, renderer-only; sends bounded `{ user_text }`.
- Backend governed core is authoritative; OutputPlan/ControlPlan dominance preserved.
- No internal artifacts, prompts, traces, or histories cross to the UI.

## Request Schema
- POST `/api/chat`
- Body: `{ "user_text": string }` (trimmed, non-empty, length ≤ 2000)
- No history, no metadata, no IDs, no extra fields.

## Response Expectations
- `action`: enum {ANSWER, ASK_ONE_QUESTION, REFUSE, CLOSE, FALLBACK}
- `rendered_text`: required string (verbatim rendering)
- Optional: `failure_type`, `failure_reason` (sanitized strings)
- Any extra/unrecognized fields are ignored; invalid shapes fail-closed in UI.

## Fail-Closed Handling
- Invalid response shape or network/HTTP error → UI shows neutral failure and enters FAILED; no auto-retry.
- Terminal actions REFUSE/CLOSE → UI disables input, keeps transcript, shows neutral terminal notice.

## Non-Goals
- No retries/auto-resends beyond manual retry of the same user_text.
- No memory/persistence, no personalization, no analytics, no UI redesign.
- No history uploads or parallel channel data.

## Stability Marker
Step 5 behavior is locked. Any change to request/response handling or trust boundaries requires reopening Phase 13 Step 5 under governance.
