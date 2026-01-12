# Phase 10 — Step 2: Friction Placement Engine

## Purpose
Deterministically select `FrictionPosture` for the ControlPlan from a given `DecisionState` (and optional `RigorLevel`), reflecting deliberate slowdown/gating to reduce irreversible cost. No text generation, no models, no orchestration.

## What Friction Is / Is Not
- **Is:** A categorical slowdown posture: `NONE`, `SOFT_PAUSE`, `HARD_PAUSE`, `STOP`.
- **Is NOT:** Refusal, rigor, clarification, closure, or content/tone. Does not ask questions or generate text.

## Allowed Inputs
- `DecisionState` fields only: `proximity_state`, `proximity_uncertainty`, `risk_domains` (+ confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Optional: previously selected `RigorLevel` (bounded enum only).

Forbidden: history, profiles, external data/tools, model outputs, heuristics, weights, probabilities.

## Deterministic Rule Ladder (Monotonic)
- Baseline: `NONE` when proximity is VERY_LOW/LOW and no escalators.
- Proximity MEDIUM:
  - Critical domain present OR responsibility != SELF_ONLY OR IRREVERSIBLE → ≥ `SOFT_PAUSE`.
  - Significant unknowns → ≥ `SOFT_PAUSE`.
- Proximity HIGH:
  - IRREVERSIBLE OR responsibility in {THIRD_PARTY, SYSTEMIC_PUBLIC} OR critical domain present → ≥ `HARD_PAUSE`.
  - Significant unknowns → ≥ `HARD_PAUSE`.
- Proximity IMMINENT:
  - IRREVERSIBLE OR SYSTEMIC_PUBLIC OR critical domain (confidence ≥ MEDIUM) → ≥ `HARD_PAUSE`.
  - IRREVERSIBLE + critical domain + significant unknowns → `STOP`.
  - Critical domain + significant unknowns → ≥ `HARD_PAUSE`.
  - Significant unknowns alone → ≥ `HARD_PAUSE`.
- Horizon: `LONG_HORIZON` with proximity ≥ MEDIUM → at least `SOFT_PAUSE`.
- Optional rigor cross-check: `STRUCTURED/ENFORCED` with proximity ≥ MEDIUM can lift `NONE` to `SOFT_PAUSE` (no downgrades).

Critical domains: `LEGAL_REGULATORY`, `MEDICAL_BIOLOGICAL`, `PHYSICAL_SAFETY`.
Significant unknowns: presence of any `explicit_unknown_zone` markers.

## Invariants / Forbidden States
- `NONE` forbidden when proximity ≥ MEDIUM with significant unknowns.
- `NONE` discouraged when critical domains are present at medium/high proximity.
- `STOP` reserved only for severe combinations (imminent + irreversible + critical + unknowns).

## Fail-Closed Behavior
- Invalid/missing `DecisionState` → `FrictionSelectionError`.
- No partial/approximate outputs; returns a single bounded `FrictionPosture`.

## Non-Goals
- No refusal, clarification, closure, initiative handling.
- No question wording, templates, or user-visible text.
- No model calls, weights, probabilities, or heuristics.
- No modifications to Phase 9 or ControlPlan schema.

## Closure Marker
- Step 2 friction placement is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
