# Phase 12 — Step 4: Strict JSON Output Schemas (Edge Contract)

## Purpose
- Enforce machine-checkable, deterministic JSON outputs for all model actions.
- Eliminate prose/vibe responses; only structured payloads are permitted.
- Keep the model tool-only and subordinate to OutputPlan; fail-closed on any violation.

## Why Strict JSON
- Deterministic parsing and validation; no partial acceptance.
- Prevent authority leakage (model cannot invent actions/questions/rules).
- Block metadata smuggling (no markdown fences, prefixes, or extra keys).

## Schemas (bounded, no extra keys)
- **AnswerJSON**: `{ answer_text: str, assumptions?: list[str], unknowns?: list[str] }`
  - `answer_text` non-empty, length-bounded. Lists bounded in size and item length.
- **AskOneQuestionJSON**: `{ question: str, question_class: QuestionClass, priority_reason: QuestionPriorityReason }`
  - Exactly one question mark; no multi-question phrasing; length-bounded.
- **RefusalJSON**: `{ refusal_category: RefusalCategory, refusal_text: str, safe_next_step?: str }`
  - No policy/internal-rule language; bounded lengths.
- **CloseJSON**: `{ closure_state: ClosureState, closure_text: str }`
  - No questions; closure_text may be empty only for silence modes; length-bounded.

## Forbidden Patterns
- Markdown fences or prefixes/suffixes (e.g., ```json ... ```).
- Extra/unknown keys; arrays at top level; non-object JSON.
- Multiple questions or “? … ?” phrasing in ask payloads.
- Policy/internal-rule language in refusals; tool-claim language anywhere.
- Metadata leaks (system prompt, internal policies).

## Fail-Closed Semantics
- Parsing failures → ModelOutputParseError.
- Schema violations → ModelOutputSchemaViolation.
- No “best effort” parsing; invalid outputs are rejected entirely.

## Non-Goals
- No provider/model selection, no retries/fallbacks, no heuristics, no streaming/tools/function-calling.
- No UI, no personalization, no memory accumulation.

## Stability Marker
- Step 4 is locked once approved. Any change to schemas or validation reopens Phase 12 and requires recertification. OutputPlan dominance and tool-only constraints must be preserved.
