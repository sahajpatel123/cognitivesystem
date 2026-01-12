# Phase 10 — Step 3: Clarification Trigger Decision

## Purpose
Deterministically decide whether a single clarification is required before proceeding. This step only sets `clarification_required`, `clarification_reason`, and `question_budget` (0 or 1). No question wording, no selection of question class, no text generation, no models.

## Allowed Inputs
- `DecisionState` fields: `proximity_state`, `proximity_uncertainty`, `risk_domains` (+ confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Phase 10 inputs: `rigor_level` (Step 1), `friction_posture` (Step 2).

Forbidden: history, personalization, external data/tools, model outputs, heuristics, weights, probabilities, free-text prompts.

## ClarificationReason Taxonomy (bounded)
- `DISAMBIGUATION`
- `MISSING_CONTEXT`
- `SAFETY`
- `SCOPE_CONFIRMATION`
- `UNKNOWN` (only when clarification is not required)

## Deterministic Rule Ladder
- Proximity VERY_LOW/LOW: proceed (no clarification) unless critical domain at ≥ MEDIUM confidence with significant unknowns, or IRREVERSIBLE + unknowns → require clarification (reason: SAFETY).
- Proximity MEDIUM:
  - Critical domain (MEDICAL/LEGAL/PHYSICAL_SAFETY) at ≥ MEDIUM → require clarification (SAFETY).
  - IRREVERSIBLE → require clarification (SAFETY).
  - Responsibility THIRD_PARTY/SYSTEMIC_PUBLIC → require clarification (SCOPE_CONFIRMATION).
  - Friction ≥ SOFT_PAUSE with significant unknowns → require clarification (MISSING_CONTEXT).
  - Significant unknowns with rigor STRUCTURED/ENFORCED → require clarification (MISSING_CONTEXT).
  - Else proceed.
- Proximity HIGH/IMMINENT:
  - If significant unknowns OR IRREVERSIBLE OR responsibility affects others OR critical domain present OR friction in {HARD_PAUSE, STOP} → require clarification.
    - Reason: MISSING_CONTEXT if unknowns; SAFETY if irreversibility/critical; SCOPE_CONFIRMATION if responsibility scope; SAFETY otherwise.
  - Else proceed.

Significant unknowns: any `explicit_unknown_zone` markers.
Critical domains: `LEGAL_REGULATORY`, `MEDICAL_BIOLOGICAL`, `PHYSICAL_SAFETY`.

## Invariants
- `clarification_required=True` ⇒ `question_budget=1`.
- `clarification_required=False` ⇒ `question_budget=0`.
- `question_budget` ∈ {0, 1} only.
- `clarification_reason` must be bounded; use `UNKNOWN` only when not asking.

## Fail-Closed Behavior
- Invalid inputs → `ClarificationTriggerError`.
- No partial outputs; returns one bounded `ClarificationDecision`.

## Non-Goals
- No question selection or wording (Step 4).
- No refusal, closure, or initiative logic.
- No UI, templates, model calls, heuristics, weights, probabilities.
- No modifications to Phase 9 or ControlPlan schema.

## Closure Marker
- Step 3 clarification trigger is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
