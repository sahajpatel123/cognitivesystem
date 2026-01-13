# Phase 13 — Step 7: Safe UX Constraints (Anti-Addiction & No Agent Creep)

## 1) Purpose
Prevent the chat UI from drifting into engagement optimization, persona/agent behavior, or authority over governed cognition. Enforce a renderer-only, neutral, fail-closed surface for `/product/chat`.

## 2) UX Threat Model
- Addiction/engagement drift: prompt suggestions, nudges, streaks, infinite loops.
- Agent creep: autonomy illusions, proactive actions, “continue?” prompts, auto-follow-ups.
- Persona framing: friendly/companion/anthropomorphic tone or emotions.
- Refusal/closure bypass: attempts to circumvent governance by UI wording.

## 3) Hard Banned UX Patterns
- Suggested prompts, “people also ask,” next-step recs, gamification, streaks, nudges.
- Auto-send, auto-retry, auto-follow-up, “want me to continue?”
- Persona/emotion (“I’m excited/proud/sorry”), emojis for humanization, agent claims.
- Any memory/personalization, history upload, metadata/telemetry for cognition.
- Rewriting/augmenting governed output; inferring action/rigor/friction/confidence.

## 4) Allowed UX Patterns (bounded)
- Single input box sending only `{ user_text }` (trimmed, bounded length).
- Verbatim rendering of `rendered_text` with action badges/strip for bounded actions.
- Manual retry of last user_text only; manual reset clears local state only.
- Neutral notices for failure/terminal states; no suggestions or follow-ups.
- Local-only copy controls (last response/transcript) with no backend calls.

## 5) Terminal Discipline
- Backend REFUSE or CLOSE → UI enters TERMINAL, input disabled, neutral notice; no bypass or “continue” affordance. Reset allowed (local only).

## 6) Prompting/Suggestion Policy
- No auto suggestions, no related prompts, no hint chips, no “people also ask.”
- Keyboard shortcuts only for submit (Enter) and newline (Shift+Enter) as implemented; no prompt scaffolding.

## 7) Copy/Retry/Reset Rules
- Retry is manual, resends only last user_text, no history/context added.
- Reset is local-only: clears transcript, input, state; no backend call.
- Copy actions are local-only; no telemetry or external storage.

## 8) UI Wording Constraints
- Neutral, tool-like language; no emotion or persona.
- Failures: bounded neutral text (e.g., “Request failed. Please retry.”).
- Terminal: “This session is closed by the system’s governance rules.”

## 9) Non-Goals
- No engagement UX, no personalization, no analytics, no design/theming changes, no streaming or auto-retries.

## 10) Stability Marker
Step 7 is locked. Any change to UX constraints, wording policies, or banned/allowed patterns requires reopening Phase 13 Step 7 under governance.
