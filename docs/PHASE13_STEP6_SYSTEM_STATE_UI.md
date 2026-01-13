# Phase 13 — Step 6: System State UI Representation

## Purpose & Scope
Expose governed system state cues in the chat UI without granting authority or cognition. The UI renders bounded, contract-compliant labels for system actions and closures while remaining fail-closed and non-adaptive.

## Allowed Rendering
- Render backend-provided action (ANSWER, ASK_ONE_QUESTION, REFUSE, CLOSE, FALLBACK) as badges/state strip labels.
- Render rendered_text verbatim with whitespace preserved.
- Show terminal notices when backend signals REFUSE/CLOSE.
- Display failure labels only as sanitized strings already provided by backend.

## Forbidden Behaviors
- No inference of risk/rigor/friction/confidence from text.
- No heuristics, scoring, personalization, or memory.
- No history uploads or extra metadata in requests.
- No retries/auto-resends; only manual retry with same user_text.
- No rewriting or summarizing backend outputs.

## State Indicators & Visual Mapping
- Action: last system action badge and state strip label.
- Status: UI state machine label (IDLE/SENDING/FAILED/TERMINAL).
- Failure: shows last sanitized failure_type or NONE.
- Terminal notice: neutral message when REFUSE/CLOSE.
- Friction/rigor/confidence/unknowns: only if backend provides bounded fields (currently absent); never inferred.

## UI State Machine (Step 6)
- IDLE → on send → SENDING.
- SENDING → on valid response: TERMINAL if REFUSE/CLOSE; FAILED if FALLBACK; else IDLE. On error → FAILED.
- FAILED → user may manually retry (same user_text) → SENDING; reset allowed.
- TERMINAL → input disabled; reset allowed; no sends.
- Stale responses (non-current request_id) are ignored.

## Contract Enforcement
- Requests: `{ user_text }` only, trimmed, bounded length; no extras/history/metadata.
- Responses: validated bounded enums/strings; invalid responses yield neutral failure and FAILED state.
- No reliance on unrecognized fields; fail-closed on schema mismatch.

## Failure Matrix
- Network/HTTP/error: neutral failure message; state → FAILED; manual retry or reset.
- Invalid response shape: neutral failure; state → FAILED.
- Backend fail-closed (FALLBACK): render, state → FAILED.
- Terminal actions (REFUSE/CLOSE): render, state → TERMINAL; input disabled.

## Stability Marker
Step 6 is locked. Any change to UI state representation, mappings, or contract handling requires reopening Phase 13 Step 6 under governance.
