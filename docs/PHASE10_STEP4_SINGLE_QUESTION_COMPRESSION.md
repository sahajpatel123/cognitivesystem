# Phase 10 — Step 4: Single-Question Compression

## Purpose
Deterministically select exactly one bounded `question_class` when clarification is required. No wording, no multi-question behavior, no templates, no models.

## What Step 4 Is / Is Not
- **Is:** Categorical choice of one question class (and priority reason). Optional bounded targets are not added here.
- **Is NOT:** Clarification trigger (Step 3), refusal, closure, answer generation, UI, or text production. No multi-part or multiple questions.

## Allowed Inputs
- `DecisionState` fields: `proximity_state`, `proximity_uncertainty`, `risk_domains` (+ confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Phase 10 context: `clarification_reason`, `rigor_level`, `friction_posture`, with precondition `clarification_required=True` and `question_budget=1`.

Forbidden: history, profiles, external data/tools, model outputs, heuristics, weights, probabilities, free-text.

## Question Taxonomy (bounded)
- `QuestionClass`: `INFORMATIONAL`, `SAFETY_GUARD`, `CONSENT`, `OTHER_BOUNDARY`.
- `QuestionPriorityReason`: `SAFETY_CRITICAL`, `LEGAL_CONTEXT`, `SCOPE_CLARIFICATION`, `IRREVERSIBILITY`, `CONSTRAINT_GAP`, `INTENT_AMBIGUITY`, `UNKNOWN_CONTEXT`.

## Deterministic Priority Ordering (first match wins)
1) **Safety/Legal gating:** Critical domain (LEGAL/MEDICAL/PHYSICAL_SAFETY) at ≥ MEDIUM with unknowns → `SAFETY_GUARD` (SAFETY_CRITICAL/LEGAL_CONTEXT).
2) **Irreversibility + high/imminent + unknowns:** IRREVERSIBLE and proximity HIGH/IMMINENT with unknowns → `SAFETY_GUARD` (IRREVERSIBILITY).
3) **Responsibility (third-party/systemic) + unknowns:** → `CONSENT` (SCOPE_CLARIFICATION).
4) **Constraint gaps (non-safety unknowns / high friction / high rigor):** → `OTHER_BOUNDARY` (CONSTRAINT_GAP).
5) **Intent ambiguity:** `INFORMATIONAL` (INTENT_AMBIGUITY).
6) **Fallback:** If critical domain present → `SAFETY_GUARD` (UNKNOWN_CONTEXT); else if third-party/systemic → `CONSENT`; else `INFORMATIONAL` (UNKNOWN_CONTEXT).

Critical domains: `LEGAL_REGULATORY`, `MEDICAL_BIOLOGICAL`, `PHYSICAL_SAFETY`.  
Significant unknowns: any `explicit_unknown_zone` markers.

## Invariants
- Precondition: `clarification_required=True` and `question_budget=1`; otherwise error.
- Exactly one `question_class` selected; never multiple or multi-part questions.
- Outputs remain bounded enums; no text.

## Fail-Closed Behavior
- Invalid inputs or unmet preconditions → `QuestionCompressionError`.
- If no rule matches, fallback still produces a single bounded selection (no silence).

## Non-Goals
- No question wording or templates.
- No refusal, closure, or initiative handling.
- No model calls, weights, probabilities, or heuristics.
- No modifications to Phase 9 or ControlPlan schema.

## Closure Marker
- Step 4 single-question compression is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
