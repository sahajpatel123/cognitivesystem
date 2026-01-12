# Phase 11 — Step 6: Refusal Explanation Planning

## Purpose / Scope
Deterministically select `RefusalExplanationMode` for the `OutputPlan` when refusal is required. No text generation, no templates, no negotiation, no clarification asking.

## What Refusal Explanation IS / IS NOT
- **IS:** A bounded choice of explanation strength for refusal (categorical only).
- **IS NOT:** Rendering refusal text, policy language, advice, or model calls. Not assumption surfacing, not unknown disclosure, not question asking.

## Allowed Inputs
- `DecisionState`: proximity, risk domains + confidence, reversibility, consequence horizon, responsibility scope, explicit unknown zone.
- `ControlPlan`: refusal_required, refusal_category, action, friction_posture, closure_state, rigor_level, confidence_signaling_level, unknown_disclosure_level (for compatibility).
- Prior Phase 11 selections: `ExpressionPosture`, `RigorDisclosureLevel`, `ConfidenceSignalingLevel`, `UnknownDisclosureMode`, `AssumptionSurfacingMode`.

Forbidden inputs: user history, UI context, model outputs, free text, randomness, heuristics.

## Taxonomy (ordered)
- `BRIEF_BOUNDARY`
- `BOUNDED_EXPLANATION`
- `REDIRECT_TO_SAFE_FRAME`

## Deterministic Ladder
### Precondition
- If `refusal_required` is False ⇒ raise `RefusalExplanationSelectionError`.

### Hard Overrides
- `friction_posture == STOP` ⇒ strongest (`REDIRECT_TO_SAFE_FRAME`).
- `posture == CONSTRAINED` ⇒ not `NONE` (at least `BRIEF_BOUNDARY`).
- `confidence_signaling == EXPLICIT` ⇒ not `NONE` (at least `BRIEF_BOUNDARY`).
- `rigor_disclosure == ENFORCED` ⇒ not `NONE` (at least `BRIEF_BOUNDARY`).

### Category Mapping (baseline per refusal_category)
- `CAPABILITY_REFUSAL` ⇒ `BRIEF_BOUNDARY`
- `EPISTEMIC_REFUSAL` ⇒ `BOUNDED_EXPLANATION`
- `RISK_REFUSAL` ⇒ `BOUNDED_EXPLANATION`
- `IRREVERSIBILITY_REFUSAL` ⇒ `REDIRECT_TO_SAFE_FRAME`
- `THIRD_PARTY_REFUSAL` ⇒ `REDIRECT_TO_SAFE_FRAME`
- `GOVERNANCE_REFUSAL` ⇒ `BOUNDED_EXPLANATION`

### Unknown Coupling
- Unknowns present + unknown_disclosure != NONE ⇒ at least `BOUNDED_EXPLANATION`.
- Unknowns present + unknown_disclosure == EXPLICIT ⇒ prefer strongest (unless closure caps).

### Proximity Escalation
- If proximity >= HIGH ⇒ escalate one level (unless closure caps).

### High-Stakes Support
High-stakes factors: critical domain (LEGAL_REGULATORY, MEDICAL_BIOLOGICAL, PHYSICAL_SAFETY) with confidence >= MEDIUM, or reversibility == IRREVERSIBLE, or consequence_horizon == LONG_HORIZON, or responsibility_scope in {THIRD_PARTY, SYSTEMIC_PUBLIC}.
- If high-stakes ⇒ not `NONE`.
- If high-stakes and proximity >= MEDIUM ⇒ prefer strongest (unless closure caps).

### Closure Compatibility
- If `closure_state != OPEN` ⇒ cap to brief modes (no long structured explanation), unless `friction_posture == STOP` forces strongest.

## Invariants (fail-closed)
- `refusal_required` ⇒ explanation mode present (not `NONE`).
- `friction_posture == STOP` ⇒ strongest mode.
- `confidence_signaling == EXPLICIT` ⇒ not `NONE`.
- `posture == CONSTRAINED` ⇒ not `NONE`.
- `rigor_disclosure == ENFORCED` ⇒ not `NONE`.
- Closure cap respected unless STOP.

## Failure Semantics
Raise `RefusalExplanationSelectionError` on any invariant violation, missing or invalid category, running when `refusal_required` is False, or attempting a capped-forbidden mode.

## Non-Goals
- No rendering or template selection.
- No policy or advisory language.
- No OutputPlan assembly or answer generation.
- No model calls, heuristics, or probabilistic scoring.

## Stability Marker
Step 6 is lockable once accepted. Changes require reopening Phase 11 and re-certification.
