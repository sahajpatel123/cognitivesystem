# Phase 11 — Step 1: Expression Posture Selection

## Purpose / Scope
Deterministically select `ExpressionPosture` for governed outputs using only `DecisionState` (Phase 9) and `ControlPlan` (Phase 10). No text generation, no rendering, no models, no orchestration beyond posture selection.

## What Posture IS / IS NOT
- **Is:** Output restraint/discipline level (BASELINE → GUARDED → CONSTRAINED).
- **Is NOT:** Tone, personality, verbosity styling, or content generation.
- **Is NOT:** Rigor disclosure, confidence signaling, or refusal wording (later steps).

## Allowed Inputs (bounded)
- `DecisionState`: proximity_state, risk_domains (+ confidence), reversibility_class, consequence_horizon, responsibility_scope, outcome_classes, explicit_unknown_zone.
- `ControlPlan`: action, friction_posture, closure_state, clarification_required, refusal_required.

Forbidden: history, profiles, external tools/data, model outputs, heuristics, probabilities, free-form text.

## Taxonomy (ordered)
- `ExpressionPosture`: BASELINE < GUARDED < CONSTRAINED.

## Deterministic Escalation Ladder (first match wins by monotonic bump)
- Hard overrides:
  - refusal_required True or action REFUSE → CONSTRAINED.
  - friction STOP → CONSTRAINED.
  - closure_state != OPEN → at least GUARDED.
- High-stakes triggers:
  - Critical domain (LEGAL/MEDICAL/PHYSICAL) at ≥ MEDIUM confidence → CONSTRAINED.
  - IRREVERSIBLE → ≥ GUARDED; if proximity HIGH/IMMINENT → CONSTRAINED.
  - LONG_HORIZON → ≥ GUARDED.
  - Responsibility THIRD_PARTY/SYSTEMIC_PUBLIC → ≥ GUARDED; if proximity HIGH/IMMINENT → CONSTRAINED.
- Unknown/uncertainty:
  - Proximity ≥ MEDIUM with unknowns → ≥ GUARDED.
  - Proximity ≥ HIGH with unknowns → CONSTRAINED.
- Clarification path:
  - action ASK_ONE_QUESTION or clarification_required → ≥ GUARDED; if critical domain or third-party/systemic → CONSTRAINED.
- Baseline allow (only if all true):
  - Proximity VERY_LOW/LOW; no critical domain ≥ MEDIUM; not IRREVERSIBLE; horizon not LONG; responsibility SELF_ONLY; no unknowns; no clarification/refusal/closure; friction in {NONE, SOFT_PAUSE}; closure_state OPEN; no refusal_required.
  - Otherwise escalate to at least GUARDED.

## Invariants
- High-stakes conditions cannot map to BASELINE.
- Refusal or STOP friction ⇒ CONSTRAINED.
- Clarification cannot be BASELINE.
- Posture must be one of {BASELINE, GUARDED, CONSTRAINED} with monotonic escalation.

## Fail-Closed Semantics
- Invalid/missing enums raise `ExpressionPostureSelectionError`.
- No partial/approximate outputs; returns a single bounded posture.

## Non-Goals
- No rendering, templates, or text generation.
- No model/LLM usage.
- No UI or orchestration integration beyond posture selection.

## Stability / Closure
- Step 1 is locked upon acceptance. Any change to taxonomy or rules requires reopening Phase 11 and re-certification.
