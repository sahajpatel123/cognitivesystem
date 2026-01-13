# Phase 12 — Step 6: Deterministic Fallback Rendering (Fail-Closed)

## Purpose
- Provide a deterministic, model-free safety net that renders governed output when model invocation or output verification fails.
- Preserve OutputPlan dominance: action, posture, disclosures, and verbosity caps remain authoritative.
- Ensure the system remains correct and bounded even if the model is unavailable or returns invalid output.

## Trust Boundary
- Inputs: OutputPlan (Phase 11), DecisionState (Phase 9), ControlPlan (Phase 10), user_text (for traceability only).
- Model outputs are untrusted; fallback produces governed text/JSON without any model call.
- No retries, no alternate providers, no prompt tweaks.

## Inputs / Outputs
- Inputs: user_text, DecisionState, ControlPlan, OutputPlan.
- Outputs: deterministic fallback content (text or JSON) or typed failure if rendering cannot comply with constraints.

## Action-Specific Behaviors
- ANSWER: Short bounded answer; includes explicit unknown line if required; includes assumption line when surfacing is LIGHT/REQUIRED; confidence line when signaling is GUARDED/EXPLICIT; honors verbosity cap; no tool/memory claims.
- ASK_ONE_QUESTION: Exactly one short question; template keyed by QuestionClass; ends with “?”; no multi-question phrasing; JSON object with question, question_class, priority_reason.
- REFUSE: Template chosen by RefusalCategory; bounded phrasing; no policy/loophole language; explanation_mode adds minimal safe tail; posture assumed CONSTRAINED; respects verbosity cap.
- CLOSE: RenderingMode mapping — SILENCE → empty string; CONFIRM_CLOSURE → “Got it. Closing out.”; BRIEF_SUMMARY_AND_STOP → “Noted. Closing this interaction now.”; never asks questions.

## Fail-Closed Rules
- If OutputPlan invariant or required spec missing → typed failure.
- If fallback would exceed verbosity cap → deterministic truncation.
- No markdown fences, no links, no system/policy/tool/memory claims.
- No retries; if fallback cannot render safely → contract violation with fail_closed=True.

## Non-Goals
- No provider/model selection, no streaming, no personalization/memory, no tool calls.
- No paraphrasing of user input beyond minimal deterministic templates.
- No changes to locked Phases 1–11.

## Stability Marker
- Step 6 semantics are locked. Any change to templates, truncation, or action mappings requires reopening Phase 12 and recertification. OutputPlan dominance and fail-closed behavior must remain intact.
