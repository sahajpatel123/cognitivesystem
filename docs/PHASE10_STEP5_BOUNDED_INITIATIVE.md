# Phase 10 — Step 5: Bounded Initiative & Intervention Budget

## Purpose
Deterministically set bounded initiative/intervention budgets to prevent nagging, loops, repeated warnings, or repeated clarifications. No text generation, no models, no orchestration.

## Initiative vs Rigor vs Friction
- **Initiative:** Whether the system intervenes unprompted (warnings/clarifications), bounded to at most once.
- **Rigor:** Constraint density/strictness (Step 1).
- **Friction:** Deliberate slowdown/gating posture (Step 2).

## Allowed Inputs
- `DecisionState`: `proximity_state`, `risk_domains` (+ confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Phase 10 context: `rigor_level`, `friction_posture`, `clarification_required`, `question_budget`, `question_class`.

Forbidden: history, personalization, external data/tools, model outputs, heuristics, weights, probabilities, free text.

## Budget Taxonomy (bounded)
- `InitiativeBudget`: `NONE`, `ONCE`, `STRICT_ONCE`.
- `warning_budget`: `0` or `1` only.

## Deterministic Rule Ladder (first match wins)
- Proximity VERY_LOW/LOW:
  - If critical domain (legal/medical/physical safety) with unknowns → `initiative_budget=ONCE`, `warning_budget=1`.
  - Else `initiative_budget=NONE`, `warning_budget=0`.
- Proximity MEDIUM:
  - If significant unknowns OR responsibility affects others OR critical domain → `initiative_budget=ONCE`; `warning_budget=1` unless clarification already required.
  - Else `initiative_budget=NONE`, `warning_budget=0`.
- Proximity HIGH/IMMINENT:
  - If high-stakes (critical domain, IRREVERSIBLE, THIRD_PARTY/SYSTEMIC_PUBLIC, or friction ≥ HARD_PAUSE) OR significant unknowns → `initiative_budget=STRICT_ONCE`; `warning_budget=1` unless clarification already required.
  - Else `initiative_budget=ONCE`; `warning_budget=1` unless clarification already required.
- Clarification constraint: if `clarification_required=True`, `question_budget` must be 1, and `warning_budget=0` (the question consumes the single initiative slot).

Critical domains: `LEGAL_REGULATORY`, `MEDICAL_BIOLOGICAL`, `PHYSICAL_SAFETY`.  
Significant unknowns: any `explicit_unknown_zone` markers.

## Invariants
- `warning_budget` ∈ {0,1}.
- `initiative_budget` bounded enum only.
- `clarification_required=True` ⇒ `question_budget=1` and `warning_budget=0`; initiative cannot exceed one intervention.
- No loops; no stateful accumulation.

## Fail-Closed Behavior
- Invalid inputs or inconsistent budgets → `InitiativeSelectionError`.
- No partial outputs; returns one bounded `InitiativeDecision`.

## Non-Goals
- No closure detection, refusal logic, or final orchestration.
- No question wording/templates.
- No model calls, heuristics, weights, probabilities.
- No modifications to Phase 9 or ControlPlan schema beyond bounded fields.

## Closure Marker
- Step 5 bounded initiative is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
