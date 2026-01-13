# Phase 13 — Step 2: Chat UI Wiring & Contract Enforcement

## Purpose & Scope
- Bind the chat UI to the governed backend contract as a rendering-only surface.
- Prevent authority inversion: UI cannot influence ControlPlan/OutputPlan or cognition; it only submits `user_text` and renders governed outputs.
- Enforce client-side guards to fail-closed before requests and after responses.

## Trust Boundary
- UI is untrusted and attacker-controllable; backend governed core is authoritative.
- Network is untrusted; validation occurs both client-side (pre-flight) and server-side (already in Step 1).
- No internal artifacts (DecisionState/ControlPlan/OutputPlan/trace/evidence/audit) may cross the boundary.

## Contract Enforcement Rules
- Requests: JSON `{ user_text: string }`, trimmed, non-empty, max 2000 chars, no extra fields, no history, no metadata.
- Responses: must validate `action ∈ {ANSWER, ASK_ONE_QUESTION, REFUSE, CLOSE, FALLBACK}`, `rendered_text` string, optional `failure_type`/`failure_reason` strings; unknown shapes fail-closed with generic UI error.
- UI renders `rendered_text` verbatim; no rewriting, summarization, or augmentation.

## Forbidden Behaviors
- No decision-making, no retries, no auto-follow-ups, no memory/personalization/history uploads, no prompt injection/rewrites, no analytics, no multi-question injection, no exposure of internals.
- UI must not attempt to set refusal/closure; honors backend action only.

## Action Dominance Handling in UI
- UI displays action badge for each system message (ANSWER/ASK_ONE_QUESTION/REFUSE/CLOSE/FALLBACK).
- On closure (CLOSE or REFUSE treated as terminal), UI disables input and shows neutral “Conversation closed.”
- UI never overrides or infers alternate actions.

## Failure Handling
- Network or invalid response → generic bounded message: “I couldn’t complete that request right now.” / “Unexpected response from governed service.”
- Backend `failure_type`/`failure_reason` rendered only as minimal note; no internals shown.
- No retries or auto-resends; fail-closed is preferred to partial help.

## Stability Marker
- Phase 13 Step 2 is defined and locked. Any change to UI wiring, guards, or contract handling requires reopening Phase 13.
