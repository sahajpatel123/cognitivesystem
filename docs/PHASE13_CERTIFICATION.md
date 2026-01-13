# Phase 13 COMPLETE, CERTIFIED, LOCKED (2026-01-13)

## Phase Lock Declaration
Phase 13 (UI renderer-only governance layer) is complete, certified, and locked. Any modification requires formally reopening Phase 13 and re-certification. Phases 1–12 remain immutable.

## Scope
- **In scope:** Frontend chat surface at `/product/chat`, its strict client request/response handling, session TTL/persistence behavior, UI state machine (IDLE/SENDING/FAILED/TERMINAL), and adherence to the Phase 13 chat API contract (`POST /api/chat` with `{ user_text }` only; responses with bounded `action` + `rendered_text` + optional sanitized failure info).
- **Included for compliance:** Backend chat contract only as the external dependency that the UI must respect; its semantics are frozen for UI purposes.
- **Out of scope:** Any cognition, model, or governance logic in Phases 1–12; non-chat product surfaces; performance, analytics, personalization, or engagement layers.

## Trust Boundary & Authority Boundary
- UI is an **untrusted renderer** with **zero authority**.
- UI cannot initiate cognition, alter refusals/closures, or change rigor/friction decisions.
- UI must not fabricate, reshape, or reinterpret governed outputs; renders verbatim bounded text only.
- UI cannot emit new actions, tools, or side-effects; it is text-in/text-out.

## Positive Guarantees (Must)
- Renderer-only behavior; no decision-making or agent behaviors.
- Contract-only payloads: sends exactly `{ user_text }`; no history, metadata, or session leakage.
- Fail-closed handling for invalid inputs/responses; neutral error rendering only.
- Terminal discipline: REFUSE and CLOSE place UI in terminal state; input/send disabled.
- No suggestion chips, no persona, no engagement or auto-follow-ups.
- Local-only session runtime (UUID, ~60m TTL, bounded transcript) never sent to backend.
- Stale-response guard via request ordering; late responses ignored.
- Verbatim rendering of governed text; no rewrites or multi-question injection.
- Manual-only retry; no auto-retry; reset/new session is local-only.

## Explicit Non-Guarantees
- No correctness of answers or model safety guarantees.
- No UX quality, latency, uptime, or performance guarantees.
- No personalization, adaptation, or learning from user inputs.
- No memory assistant behavior; no conversational continuity beyond local TTL transcript.
- No guarantees beyond the bounded contract fields and renderer-only discipline.

## Evidence / Conformance Proof
- Phase 13 Step 9 Playwright UI abuse suite is passing (16/16) after browser binaries installation; covers contract bounds, terminal discipline, fail-closed behavior, stale-response guard, TTL handling, retry/reset discipline, and authority drift prevention.

## Invalidation Triggers (Certification Void If Any Occur)
- UI sends any history, metadata, session IDs, or transcripts to backend beyond `{ user_text }`.
- UI adds suggestion chips, proactive follow-ups, persona/engagement hooks, or agent-like behaviors.
- UI rewrites or augments governed outputs; allows multi-question or unbounded responses.
- UI bypasses or weakens contract validation; accepts/produces extra fields or unknown actions.
- UI stores or transmits transcript/session data to backend or external services.
- UI makes autonomous calls outside `/api/chat` for chat flow.
- UI adds memory/personalization, trend adaptation, or learning behaviors.
- UI allows continuation after REFUSE/CLOSE or removes terminal disablement.
- UI introduces hidden endpoints or bypasses `/api/chat` trust boundary.

## Dependency Rules
- Later phases may measure or consume the existing UI but may **not** alter its authority model, contract semantics, fail-closed behaviors, or renderer-only scope without reopening Phase 13.
- Any change to UI scope, payload/response handling, session semantics, or terminal discipline requires Phase 13 re-open and new certification.

## Closure Marker
Phase 13 is locked. Any modification requires formal Phase 13 re-open plus a new certification cycle.
