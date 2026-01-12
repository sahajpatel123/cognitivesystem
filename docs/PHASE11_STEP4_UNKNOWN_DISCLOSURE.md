# Phase 11 — Step 4: Unknown Disclosure Planning

## Purpose / Scope
Deterministically select `UnknownDisclosureMode` (NONE / IMPLICIT / EXPLICIT) for governed outputs using `DecisionState`, `ControlPlan`, and prior posture/rigor/confidence selections. No text generation, no rendering, no models, no assembly.

## What Unknown Disclosure IS / IS NOT
- **Is:** A bounded choice about whether and how to surface known unknowns.
- **Is NOT:** Verbosity, probability, confidence statements, assumption surfacing, or formatting of unknown lists.

## Allowed Inputs
- `DecisionState`: proximity_state, risk_domains (+ confidence), reversibility_class, consequence_horizon, responsibility_scope, outcome_classes, explicit_unknown_zone.
- `ControlPlan`: action, friction_posture, closure_state, refusal_required.
- Prior selections: `ExpressionPosture`, `RigorDisclosureLevel`, `ConfidenceSignalingLevel`.

Forbidden: history, profiles, external tools/data, model outputs, heuristics, probabilities, free text, templates.

## Taxonomy (ordered)
- `UnknownDisclosureMode`: NONE < IMPLICIT < EXPLICIT.

## Deterministic Ladder (priority bumps)
- Hard overrides:
  - friction STOP → EXPLICIT.
  - refusal_required → ≥ IMPLICIT; if unknowns present → EXPLICIT.
  - confidence_signaling EXPLICIT → ≥ IMPLICIT; EXPLICIT if unknowns present.
  - rigor_disclosure ENFORCED → ≥ IMPLICIT; EXPLICIT if unknowns present.
- Unknown gates:
  - unknowns present → ≥ IMPLICIT.
- Proximity escalation:
  - proximity ≥ HIGH with unknowns → EXPLICIT, except ASK_ONE_QUESTION or non-OPEN closure may cap to IMPLICIT (never NONE).
  - proximity == MEDIUM with unknowns → ≥ IMPLICIT.
- High-stakes escalation (critical domain ≥ MEDIUM, IRREVERSIBLE, LONG_HORIZON, or third-party/systemic responsibility):
  - If high-stakes AND unknowns AND proximity ≥ MEDIUM → EXPLICIT unless constrained by question/closure/close; if constrained, IMPLICIT (never NONE).
- Action compatibility:
  - ASK_ONE_QUESTION: prefer IMPLICIT; EXPLICIT only if STOP or high-stakes + high proximity forces it.
  - closure_state != OPEN: avoid EXPLICIT unless STOP or refusal+unknowns; never NONE when unknowns present.
  - REFUSE: allow IMPLICIT or EXPLICIT only (never NONE).
- Baseline NONE allow (all must hold): no unknowns; proximity VERY_LOW/LOW; no critical ≥ MEDIUM; not IRREVERSIBLE; horizon not LONG; responsibility SELF_ONLY; closure OPEN; no refusal; friction NONE/SOFT; rigor_disclosure MINIMAL; confidence_signaling MINIMAL; posture BASELINE. Otherwise NONE is disallowed.

## Invariants
- Unknowns present forbid NONE.
- STOP friction ⇒ EXPLICIT.
- Confidence EXPLICIT or rigor ENFORCED ⇒ not NONE.
- Refusal requires ≥ IMPLICIT.
- Outputs constrained to {NONE, IMPLICIT, EXPLICIT}; no probabilities/weights.

## Fail-Closed Semantics
- Violations raise `UnknownDisclosureSelectionError`; no partial/approximate outputs.

## Non-Goals
- No assumption surfacing policy, no formatting, no templates, no rendering, no model calls, no UI, no OutputPlan assembly.

## Stability
- Step 4 is locked upon acceptance. Any change to taxonomy or rules requires reopening Phase 11 and re-certification.
