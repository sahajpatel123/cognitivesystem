# Phase 13 — Step 8: Session Handling (TTL + Local Thread)

## 1) Purpose
Provide bounded, local-only session continuity (session_id + transcript) with TTL expiry, without adding memory, personalization, or backend history. Preserve renderer-only, fail-closed UI.

## 2) Definitions
- Session: UI-local continuity token (session_id, timestamps, local transcript). Not cognitive memory, not user identity, not authoritative.

## 3) Trust Boundary
- UI is untrusted; session data is untrusted and validated before use.
- Backend remains authoritative; no history or session metadata is sent for cognition.
- Request payload stays `{ user_text }` only.

## 4) TTL Semantics
- Default TTL: 60 minutes from session creation.
- On load: if expired → clear storage, start new session, show neutral expiry notice.
- Session restart regenerates session_id and resets transcript and UI state.

## 5) Local Transcript Rules
- Stored shape (versioned): `{ storage_version: 1, session_id, created_at, expires_at, messages[] }`.
- Max messages stored: 200; max per message length: 4000 chars; bounded trimming on persist.
- Stored transcript is local-only; never sent to backend.
- If malformed/invalid → discard and start new session (fail-closed).

## 6) Failure Handling Matrix
- Expired TTL: discard, start new session, neutral notice.
- Corrupted storage: discard, start new session.
- Oversized transcript/message: bounded trim; if invalid → discard and reset.
- Network/invalid response: UI FAILED state; manual retry allowed; reset/new session allowed.
- Terminal backend actions (REFUSE/CLOSE): UI TERMINAL; new session clears terminal.

## 7) Non-Goals
- No user identity, no personalization, no cross-session memory, no analytics/telemetry, no backend history, no auto-retries.

## 8) Stability Marker
Step 8 is locked. Any change to TTL duration, storage shape, or session rules requires reopening Phase 13 Step 8 under governance.
