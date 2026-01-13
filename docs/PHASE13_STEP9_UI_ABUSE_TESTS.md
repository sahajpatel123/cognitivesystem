# Phase 13 — Step 9: UI Abuse Tests (Governance UI Attack Suite)

## Purpose
Prove via automated UI tests that the chat surface cannot bypass governance, gain authority, or leak context. Validate strict contract use, terminal discipline, fail-closed behavior, stale-response protection, and local-only session TTL handling.

## Threat Model
- Contract abuse: extra fields, history, metadata, oversized/empty inputs.
- Terminal bypass: continuing after REFUSE/CLOSE.
- Malformed backend responses: invalid JSON, unknown actions, missing fields.
- Agent/engagement creep: suggestions, auto-follow-ups, multi-question injection by UI.
- Stale/out-of-order responses overriding newer ones.
- Session TTL misuse or transcript leakage to backend.

## Coverage Matrix (Categories A–H)
- A: Request bounds (only user_text, empty/oversized blocked).
- B: Terminal discipline (REFUSE/CLOSE disable input, no further calls).
- C: Fail-closed on malformed responses (invalid JSON/action/missing rendered_text).
- D: Multi-question injection defense (render verbatim, no suggestions).
- E: Stale response ignored; ordering preserved.
- F: Session TTL safety (no history sent; expiry resets locally only).
- G: Manual retry/reset discipline (single retry call; reset local only).
- H: No authority drift (rendered_text verbatim; labels do not alter content).

## Failure Taxonomy
- Contract violation (extra fields, empty/oversized, malformed response).
- Terminal violation (action REFUSE/CLOSE not enforcing closure).
- Stale-response corruption (old response overwrites new).
- Drift/agent creep (suggestions, rewritten outputs, unauthorized actions).
- Session leakage (history/metadata sent; TTL not enforced).

## Non-Goals
- No performance/latency tests.
- No visual regression tests.
- No backend load/stress.

## Stability Marker
Step 9 is locked. Weakening/removing tests or altering abuse coverage requires reopening Phase 13 Step 9 under governance.
