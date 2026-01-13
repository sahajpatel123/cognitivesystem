# Phase 12 — Step 5: Model Output Verifier & Sanitizer (Fail-Closed)

## A) Purpose
- Verify and sanitize model outputs against strict schemas and OutputPlan dominance.
- Enforce tool-only, non-authoritative model behavior; reject violations fail-closed.
- Deliver machine-checkable outputs or typed failures with no partial acceptance.

## B) Trust Boundary
- Model output is untrusted candidate text/JSON.
- All calls already pass through Phase 3 enforcement; Step 5 is post-call verification.
- OutputPlan and ControlPlan remain authoritative; model cannot change actions or disclosures.

## C) Inputs / Outputs
- Inputs: OutputPlan (Phase 11), DecisionState (Phase 9), ControlPlan (Phase 10), ModelInvocationResult (Phase 12 Step 1), optional original user_text for strict validation only.
- Output: Verified/sanitized ModelInvocationResult or typed failure (fail_closed=True).

## D) Verification Checks
- Structural: strict JSON parse (no fences/prefix/suffix), schema validation via Step 4 schemas (Answer/AskOne/Refusal/Close), forbid extra keys.
- Action alignment: OutputAction → matching schema only; mismatches reject.
- Semantic:
  - Single-question rule; no multi-question hints or advice inside questions.
  - Refusal: no policy/internal-rule language; no tool/authority claims; category must match OutputPlan.
  - Close: no questions; no expansion beyond closure intent.
  - Answer: no tool/policy/memory/system-prompt claims; honor unknown disclosure requirements; reject overconfident claims when unknowns required.
  - Forbidden phrases: memory/policy/tool/authority leaks rejected.

## E) Sanitization Rules (minimal, deterministic)
- Trim whitespace; normalize line endings; remove zero-width/control characters.
- No paraphrasing, no content repair, no retries/fallbacks.

## F) Fail-Closed Taxonomy
- NON_JSON / SCHEMA_MISMATCH for parse/structure errors.
- CONTRACT_VIOLATION for action mismatch, semantic violations, missing disclosures, multi-question.
- FORBIDDEN_CONTENT for policy/tool/memory/authority claims.
- All failures include fail_closed=True; no partial outputs.

## G) Non-Goals
- No provider/model selection, no retries, no heuristics/probabilities.
- No UI, no personalization/memory, no streaming/tools/function-calling.
- No content rewriting beyond minimal sanitization.

## H) Stability Marker
- Step 5 is locked upon approval. Changes to verification/sanitization rules or schemas require reopening Phase 12 and recertification. OutputPlan dominance and tool-only constraints must remain intact.
