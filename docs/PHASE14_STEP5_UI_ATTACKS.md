# Phase 14 — Step 5: UI Attack & Bypass Suite

Status: Implemented (Playwright adversarial suite)

## Purpose
Prove UI remains renderer-only, enforces contract payload `{ user_text }`, maintains terminal discipline, ignores stale responses, blocks spam/in-flight sends, respects TTL/local session boundaries, and renders backend output verbatim without agent/suggestions.

## Threat Model (A–G)
- **A. Payload / Contract attacks**: No extra keys, no history/metadata sent; UI never forwards local/session data.
- **B. Terminal discipline**: REFUSE/CLOSE → terminal state; send/retry disabled; terminal notice present.
- **C. Race / stale responses**: Out-of-order responses ignored via request-id guard; stale payloads not rendered.
- **D. In-flight blocking / spam**: While a request is pending, additional sends are blocked; exactly one call in-flight.
- **E. TTL / session attacks**: Expired TTL resets locally without backend call; history not replayed to backend after reload.
- **F. Render-only**: Backend text (markdown/unicode) rendered verbatim; no trimming/rephrasing.
- **G. No-agent / no-suggestion**: No suggestion chips, no agent prompts/typing indicators beyond allowed status.

## Coverage Matrix (tests in `frontend/tests/phase14_ui_attack.spec.ts`)
- A1/A2: Payload integrity and no metadata leakage.
- B1/B2: Terminal discipline after REFUSE/CLOSE; retry disabled.
- C1: Out-of-order responses; stale ignored.
- D1: In-flight blocking; single call enforced.
- E1/E2: TTL expiry local reset; no history replay to backend.
- F1: Verbatim render of unicode/markdown.
- G1: No suggestion/agent UI elements.

## Failure Taxonomy
- Contract violation: extra keys or history leaked to `/api/chat`.
- Terminal breach: sends allowed after REFUSE/CLOSE; retry enabled when terminal.
- Race/stale breach: stale response renders after newer request.
- In-flight breach: multiple concurrent backend calls for single input.
- TTL breach: expired session triggers backend call or replays history.
- Render breach: text rewritten, trimmed, or augmented.
- Agent breach: suggestion chips/agent prompts appear.

## Execution
- Run from frontend workspace:
  - `npm run test:ui`
- Playwright browsers already installed in repo; no extra flags needed.

## Stability Marker
This suite is part of Phase 14 certification. Any weakening of assertions or coverage requires reopening Phase 14 governance. Snapshots/expectations must only change with explicit, reviewed UI contract updates.
