# Phase 11 — Step 7: Closure Rendering Planning

## Purpose / Scope
Deterministically select `ClosureRenderingMode` for the `OutputPlan` when closure is active. No text generation, no summaries, no suggestions—only a bounded mode choice for how to terminate interaction.

## What Closure Rendering IS / IS NOT
- **IS:** A categorical choice of how to render closure (silence, brief acknowledge, brief summary then stop) under strict silence discipline.
- **IS NOT:** Generating closure text, offering next steps, reopening questions, or running models.

## Allowed Inputs
- `DecisionState`: proximity, risk domains + confidence, reversibility, consequence horizon, responsibility scope, explicit unknown zone.
- `ControlPlan`: closure_state (must be non-OPEN), friction_posture, question_budget, clarification_required, action, rigor_level, confidence_signaling_level, unknown_disclosure_level.
- Prior Phase 11 selections: `ExpressionPosture`, `RigorDisclosureLevel`, `ConfidenceSignalingLevel`, `UnknownDisclosureMode`, `AssumptionSurfacingMode`, `RefusalExplanationMode`.

Forbidden inputs: user history, UI context, model outputs, free text, randomness, heuristics.

## Taxonomy
- `SILENCE`
- `CONFIRM_CLOSURE`
- `BRIEF_SUMMARY_AND_STOP`

## Deterministic Ladder
### Preconditions
- If `closure_state == OPEN` ⇒ error.
- If `closure_state != OPEN` and `question_budget == 1` ⇒ error (closure cancels questions).
- If `closure_state != OPEN` and `clarification_required` ⇒ error (closure forbids clarification).

### Hard Overrides
- `closure_state == USER_TERMINATED` ⇒ strictest termination (silence/minimal), no summary.
- `friction_posture == STOP` ⇒ strict/brief only (silence).
- `posture == CONSTRAINED` ⇒ no verbose summary.
- `confidence_signaling == EXPLICIT` or `unknown_disclosure == EXPLICIT` ⇒ only brief acknowledge or bounded summary (summary only if `closure_state == CLOSING`).

### Closure State Mapping
- `CLOSED` ⇒ strict mode (silence or confirm closure), no summary.
- `CLOSING` ⇒ allow brief acknowledge; bounded brief summary only if not USER_TERMINATED/STOP and not posture-constrained.

### High-Stakes Support (bounded)
- High-stakes factors: critical domain (LEGAL_REGULATORY, MEDICAL_BIOLOGICAL, PHYSICAL_SAFETY) with confidence ≥ MEDIUM, or IRREVERSIBLE, or LONG_HORIZON, or responsibility_scope ∈ {THIRD_PARTY, SYSTEMIC_PUBLIC}.
- If `closure_state == CLOSING` and high-stakes and not STOP/USER_TERMINATED ⇒ prefer `BRIEF_SUMMARY_AND_STOP` (bounded).

### Proximity Support
- If `proximity_state == IMMINENT` and `closure_state == CLOSING` and not STOP/USER_TERMINATED ⇒ prefer `BRIEF_SUMMARY_AND_STOP` (bounded).

### Default
- If no rule forces summary, choose minimal acknowledge (`CONFIRM_CLOSURE`), never reopen interaction.

## Invariants (fail-closed)
- `closure_state != OPEN` ⇒ no questions, no clarification.
- `USER_TERMINATED` ⇒ no summary mode.
- `STOP` friction ⇒ strict termination (silence).
- `posture == CONSTRAINED` ⇒ no verbose summary.
- `closure_state == CLOSED` ⇒ no summary.

## Failure Semantics
Raise `ClosureRenderingSelectionError` for any invariant violation, incompatible closure state, contradictory question/clarification during closure, or attempts at verbose/continuing modes under constrained/strict states.

## Non-Goals
- No rendering of text, no suggestions, no continuation, no model calls.

## Stability Marker
Step 7 is lockable once accepted; changes require reopening Phase 11 and re-certification.
