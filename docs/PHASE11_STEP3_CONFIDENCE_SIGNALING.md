# Phase 11 — Step 3: Confidence Signaling Planning

## Purpose / Scope
Deterministically select `ConfidenceSignalingLevel` for governed outputs using `DecisionState`, `ControlPlan`, and previously selected posture + rigor_disclosure. No text generation, no models, no rendering, no assembly.

## What Confidence Signaling IS / IS NOT
- **Is:** Bounded epistemic disclosure level (MINIMAL, GUARDED, EXPLICIT).
- **Is NOT:** Probability, likelihood, numeric confidence, or templates; not unknown disclosure or assumption surfacing.

## Allowed Inputs
- `DecisionState`: proximity_state, risk_domains (+ confidence), reversibility_class, consequence_horizon, responsibility_scope, outcome_classes, explicit_unknown_zone.
- `ControlPlan`: action, friction_posture, closure_state, refusal_required, rigor_level, clarification_required.
- `posture` (ExpressionPosture) and `rigor_disclosure` (RigorDisclosureLevel) from prior steps.

Forbidden: history, profiles, external data/tools, model outputs, heuristics, probabilities, free text.

## Taxonomy (ordered)
- `ConfidenceSignalingLevel`: MINIMAL < GUARDED < EXPLICIT.

## Deterministic Escalation Ladder
- Hard overrides:
  - refusal_required → EXPLICIT (GUARDED only if closure != OPEN; never MINIMAL).
  - friction STOP → EXPLICIT.
  - closure_state != OPEN → ≥ GUARDED.
  - proximity IMMINENT → ≥ GUARDED; if unknowns or high-stakes → EXPLICIT.
- Unknown gates:
  - unknown_zone non-empty → ≥ GUARDED.
  - unknown_zone non-empty AND proximity ≥ HIGH → EXPLICIT.
  - UNKNOWN_OUTCOME_CLASS present → ≥ GUARDED; if proximity ≥ MEDIUM → EXPLICIT.
- High-stakes:
  - Critical domain (LEGAL/MEDICAL/PHYSICAL) ≥ MEDIUM: if proximity ≥ MEDIUM → EXPLICIT, else ≥ GUARDED.
  - IRREVERSIBLE → ≥ GUARDED; if proximity ≥ HIGH → EXPLICIT.
  - LONG_HORIZON → ≥ GUARDED; + unknowns → EXPLICIT.
  - Responsibility THIRD_PARTY/SYSTEMIC_PUBLIC → ≥ GUARDED; if proximity ≥ HIGH or unknowns → EXPLICIT.
- Coupling:
  - posture CONSTRAINED → ≥ GUARDED.
  - posture BASELINE adds no bump.
  - rigor_disclosure STRUCTURED → ≥ GUARDED; ENFORCED → EXPLICIT.
- Baseline allow (MINIMAL only if ALL): no unknowns; proximity VERY_LOW/LOW; no critical ≥ MEDIUM; not IRREVERSIBLE; responsibility SELF_ONLY; closure OPEN; no refusal; friction NONE/SOFT; rigor_disclosure MINIMAL; posture BASELINE; no UNKNOWN_OUTCOME_CLASS. Otherwise elevate to ≥ GUARDED.
- Dominance rule: cannot be below mapping of control_plan.rigor_level (MINIMAL→MINIMAL, GUARDED→GUARDED, STRUCTURED→GUARDED, ENFORCED→EXPLICIT).

## Invariants
- Unknowns forbid MINIMAL; ENFORCED rigor requires EXPLICIT.
- Refusal/STOP require EXPLICIT (refusal may allow GUARDED only if closure != OPEN).
- Closure != OPEN forbids MINIMAL.
- Result must be within {MINIMAL, GUARDED, EXPLICIT} and obey dominance mapping.

## Fail-Closed Semantics
- Violations raise `ConfidenceSignalingSelectionError`; no partial outputs, no fallback to MINIMAL.

## Non-Goals
- No text phrasing, no numeric confidence, no unknown disclosure policy, no assumption surfacing, no rendering, no model calls, no UI.

## Stability
- Step 3 is locked upon acceptance. Any change to rules or taxonomy requires reopening Phase 11 and re-certification.
