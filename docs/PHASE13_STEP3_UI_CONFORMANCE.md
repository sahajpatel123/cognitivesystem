# Phase 13 — Step 3: UI Conformance & Discipline Lock

## 1) Purpose of Step 3
Lock the chat UI into a renderer-only, fail-closed client of the governed backend. Prevent authority drift, memory, retries, or contract violations.

## 2) Trust Boundary
- UI is untrusted and attacker-controllable; it only renders governed outputs and sends `user_text`.
- Backend governed pipeline is authoritative; ControlPlan/OutputPlan dominance cannot be overridden by UI.
- No internal artifacts (DecisionState/ControlPlan/OutputPlan/trace/evidence/audit/prompts) cross the boundary.

## 3) Positive Guarantees
- UI sends only `{ user_text }`, trimmed and bounded.
- UI validates responses against the bounded contract (actions, rendered_text, optional failure fields) before rendering.
- UI state machine blocks parallel sends, enforces terminal closure, and guards against stale responses.
- UI renders governed text verbatim with action badges; no rewriting or augmentation.

## 4) Forbidden Behaviors
- No decision-making, retries, auto follow-ups, streaming, or memory/personalization.
- No history uploads; no additional metadata/IDs; no prompt injection/rewrites.
- No analytics or telemetry of user text; no exposure of internal artifacts.
- UI never sets actions; only honors backend actions.

## 5) UI State Machine (states → transitions)
- IDLE: ready to send; on valid submit → SENDING.
- SENDING: request in flight; on valid response → TERMINAL if action ∈ {REFUSE, CLOSE}, FAILED if FALLBACK, else IDLE; on error → FAILED.
- FAILED: user may retry manually; no auto-retry; send moves to SENDING.
- TERMINAL: input disabled; no further sends allowed.
- Stale response guard: responses with non-current request_id are ignored.

## 6) Contract Enforcement Rules
- Request: `{ user_text }`, trimmed, non-empty, length ≤ 2000; extra fields rejected client-side; no history or context.
- Response: action ∈ {ANSWER, ASK_ONE_QUESTION, REFUSE, CLOSE, FALLBACK}; rendered_text required and length-bounded; optional failure_type/failure_reason strings; unknown shapes fail-closed with neutral message.
- No reliance on any other fields; no inference from extras.

## 7) Terminal Session Discipline
- REFUSE or CLOSE → transition to TERMINAL; input disabled; neutral notice shown; no continuation controls.

## 8) Failure Matrix
- Network/HTTP error → neutral message: "Request could not be processed."; state → FAILED.
- Invalid schema/validator failure → neutral fail-closed message; state → FAILED.
- Backend fail-closed (FALLBACK) → render as FALLBACK, state → FAILED.
- Stale responses → ignored (no state change).

## 9) Stability Marker
Step 3 is locked. Any change to UI conformance, state machine, or contract handling requires reopening Phase 13 Step 3 under governance.
