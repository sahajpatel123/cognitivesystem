# Phase 11 — Step 5: Assumption Surfacing Planning

## Purpose / Scope
Deterministically select `AssumptionSurfacingMode` for the `OutputPlan` based on `DecisionState`, `ControlPlan`, and previously selected Phase 11 parameters (posture, rigor disclosure, confidence signaling, unknown disclosure). No text generation, no assumption phrasing, no list construction—only a bounded mode selection.

## What Assumption Surfacing IS / IS NOT
- **IS:** A deterministic decision of whether assumptions must be surfaced and how strongly (none, light, required).
- **IS NOT:** Unknown disclosure (Step 4), clarification asking (Phase 10), assumption list selection, assumption wording, templates, or any model/LLM behavior.

## Allowed Inputs (only)
- `DecisionState`: proximity, risk domains + confidence, reversibility, consequence horizon, responsibility scope, explicit unknown zone.
- `ControlPlan`: action, friction_posture, closure_state, refusal_required, rigor_level, confidence_signaling_level, unknown_disclosure_level (for compatibility), initiative and other Step 10 outputs as context only.
- Prior Phase 11 selections: `ExpressionPosture`, `RigorDisclosureLevel`, `ConfidenceSignalingLevel`, `UnknownDisclosureMode`.

Forbidden: any text inputs, user messages, model calls, randomness, heuristics, free-form scoring.

## Taxonomy (ordered)
- `NONE`
- `LIGHT`
- `REQUIRED`

## Deterministic Ladder (priority order)
### Hard Overrides
- `friction_posture == STOP` ⇒ `REQUIRED`.
- `refusal_required` ⇒ at least `LIGHT`; `REQUIRED` if unknowns present.
- `confidence_signaling == EXPLICIT` ⇒ not `NONE`; escalate to `REQUIRED` if unknowns present or high-stakes factors.
- `rigor_disclosure == ENFORCED` ⇒ not `NONE`; escalate to `REQUIRED` if unknowns present or high-stakes factors.

### Unknown Coupling
- If explicit unknowns present ⇒ at least `LIGHT`.
- If `unknown_disclosure == EXPLICIT` ⇒ not `NONE`; becomes `REQUIRED` when unknowns present and proximity ≥ MEDIUM.

### Proximity Escalation
- If proximity ≥ HIGH and unknowns present ⇒ `REQUIRED`, except capped to `LIGHT` when `action == ASK_ONE_QUESTION` or `closure_state != OPEN` (unless STOP/refusal forces `REQUIRED`).
- If proximity == MEDIUM and unknowns present ⇒ at least `LIGHT`.

### High-Stakes Escalation
- High-stakes factors (critical domain with ≥ MEDIUM confidence, IRREVERSIBLE, LONG_HORIZON, THIRD_PARTY or SYSTEMIC_PUBLIC responsibility) + unknowns ⇒ at least `LIGHT`.
- If also proximity ≥ MEDIUM ⇒ `REQUIRED` (subject to action/closure caps).
- Responsibility_scope ∈ {THIRD_PARTY, SYSTEMIC_PUBLIC} and proximity ≥ HIGH ⇒ `REQUIRED` (capped to `LIGHT` only when closure/ASK_ONE_QUESTION and no STOP/refusal).

### Action Compatibility
- `ASK_ONE_QUESTION`: prefer `LIGHT`; allow `REQUIRED` only for STOP, refusal_required, or high-stakes with HIGH/IMMINENT proximity.
- `closure_state != OPEN`: prefer `LIGHT`; forbid `REQUIRED` unless STOP or refusal_required.
- `action == REFUSE`: forbid `NONE`; allow `LIGHT` or `REQUIRED`.

### Baseline NONE Allow Rule
`NONE` allowed only when **all** hold: no unknowns; proximity ∈ {VERY_LOW, LOW}; no critical domain with ≥ MEDIUM confidence; reversibility not IRREVERSIBLE; horizon not LONG_HORIZON; responsibility_scope == SELF_ONLY; closure_state == OPEN; refusal_required == False; friction_posture ∈ {NONE, SOFT_PAUSE}; rigor_disclosure == MINIMAL; confidence_signaling == MINIMAL; unknown_disclosure ∈ {NONE, IMPLICIT}; posture == BASELINE.

## Invariants (fail-closed)
- STOP ⇒ `REQUIRED`.
- refusal_required ⇒ not `NONE`.
- confidence_signaling == EXPLICIT ⇒ not `NONE`.
- rigor_disclosure == ENFORCED ⇒ not `NONE`.
- unknowns present ⇒ not `NONE`.
- unknown_disclosure == EXPLICIT ⇒ not `NONE`.

## Failure Semantics
Raise `AssumptionSurfacingSelectionError` on any invariant violation, invalid enum, or contradictory state (e.g., STOP with non-REQUIRED, EXPLICIT confidence with NONE).

## Non-Goals
- No assumption list generation, phrasing, or templates.
- No OutputPlan assembly or rendering.
- No model calls, heuristics, or probabilistic scoring.

## Stability Marker
Step 5 is lockable once accepted. Any change requires reopening Phase 11 and re-certification.
