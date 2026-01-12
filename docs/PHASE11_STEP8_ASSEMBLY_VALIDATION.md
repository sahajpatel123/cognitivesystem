# Phase 11 — Step 8: Output Assembly & Cross-Step Validation

## Purpose / Scope
Assemble a bounded `OutputPlan` from `DecisionState`, `ControlPlan`, and Phase 11 selectors (Steps 1–7). Deterministic, fail-closed; no rendering, no templates, no model calls.

## Inputs / Outputs
- Inputs: `user_text` (current request only), `DecisionState` (Phase 9), `ControlPlan` (Phase 10).
- Outputs: One validated `OutputPlan` object (no user-facing text).

## Canonical Assembly Order
Run selectors in strict order:
1. posture = select_expression_posture
2. rigor_disclosure = select_rigor_disclosure
3. confidence_signaling = select_confidence_signaling
4. unknown_disclosure = select_unknown_disclosure
5. assumption_surfacing = select_assumption_surfacing
6. refusal_explanation_mode (only if refusal_required; else safe baseline)
7. closure_rendering_mode (only if closure_state != OPEN; else safe baseline)

Then resolve action and build `OutputPlan`.

## Deterministic OutputAction Ladder (closure > refusal > ask > answer)
1. If `closure_state != OPEN` ⇒ `OutputAction.CLOSE`
2. Else if `refusal_required` ⇒ `OutputAction.REFUSE`
3. Else if `control_plan.action == ASK_ONE_QUESTION` ⇒ `OutputAction.ASK_ONE_QUESTION`
4. Else if `control_plan.action == ANSWER_ALLOWED` ⇒ `OutputAction.ANSWER`
5. Else ⇒ fail-closed.

## Spec Construction (bounded, no text)
- `QuestionSpec`: only for `ASK_ONE_QUESTION`; requires `question_budget == 1` and `question_class` present; uses bounded `QuestionPriorityReason`.
- `RefusalSpec`: only for `REFUSE`; requires `refusal_category != NONE`; include `refusal_explanation_mode`.
- `ClosureSpec`: only for `CLOSE`; requires `closure_state != OPEN`; include `closure_rendering_mode`.
- All other actions set unrelated specs to `None`.

## Cross-Step Invariants (fail-closed)
- Close: non-OPEN closure_state; question_budget == 0; clarification_required False; refusal_required False; closure_rendering_mode present; no question/refusal specs.
- Refuse: refusal_required True; refusal_category non-NONE; closure_state OPEN; question_budget == 0; refusal_explanation_mode present.
- Ask-one-question: closure_state OPEN; refusal_required False; question_budget == 1; question_spec present; no closure/refusal specs; ENFORCED rigor_disclosure forbidden.
- Answer: closure_state OPEN; refusal_required False; question_budget == 0; STOP friction disallowed.
- Global: any contradiction or missing required enum/spec ⇒ fail-closed; `validate_output_plan` must pass.

## Failure Semantics
Raise `OutputAssemblyError` (or `OutputAssemblyInvariantViolation`) on any selector failure, dominance conflict, spec inconsistency, or schema validation error. No partial output.

## Non-Goals
- No rendering, summaries, or suggestions.
- No model calls or prompts.
- No UI/UX or tests.

## Stability Marker
Assembly order and action dominance ladder are fixed. Changes require reopening Phase 11 and re-certification.
