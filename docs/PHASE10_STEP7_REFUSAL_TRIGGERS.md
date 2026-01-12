# Phase 10 — Step 7: Refusal Trigger Logic

## Purpose
Deterministically decide whether refusal is required and assign a bounded refusal category. No text generation, no explanations, no orchestration assembly.

## Allowed Inputs
- `DecisionState`: `proximity_state`, `risk_domains` (+ confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Phase 10 context: `rigor_level`, `friction_posture`, `clarification_required`, `question_budget`, `question_class` (optional), `initiative_budget`, `warning_budget`, `closure_state`.

Forbidden: history, profiles, external data/tools, model outputs, heuristics, weights, probabilities, free text.

## RefusalCategory Taxonomy (bounded)
- `NONE`
- `CAPABILITY_REFUSAL`
- `EPISTEMIC_REFUSAL`
- `RISK_REFUSAL`
- `IRREVERSIBILITY_REFUSAL`
- `THIRD_PARTY_REFUSAL`
- `GOVERNANCE_REFUSAL`

## Deterministic Trigger Ladder (first match wins)
1) `closure_state == USER_TERMINATED` → refusal_required=False (`NONE`) because interaction already ended.
2) Critical domain + high/imminent + significant unknowns + no clarification path (clarification_required=False or question_budget=0) → refusal_required=True (`RISK_REFUSAL`).
3) Imminent + IRREVERSIBLE + significant unknowns + no clarification → refusal_required=True (`IRREVERSIBILITY_REFUSAL`).
4) Third-party/systemic responsibility (≥ MEDIUM proximity) + significant unknowns + no clarification → refusal_required=True (`THIRD_PARTY_REFUSAL`).
5) Capability/structural constraint placeholder: friction==STOP with critical domain and unknowns → refusal_required=True (`CAPABILITY_REFUSAL`).
6) Default → refusal_required=False (`NONE`).

No escape-hatch categories such as `OTHER` are permitted; taxonomy is fixed and bounded.

Critical domains: `LEGAL_REGULATORY`, `MEDICAL_BIOLOGICAL`, `PHYSICAL_SAFETY`.  
Significant unknowns: any `explicit_unknown_zone` markers.

## Interaction with Clarification/Closure
- If `clarification_required=True` and `question_budget=1`, refusal is deferred unless extreme catastrophic combination (covered in Tier 2/3). Prefer asking the one question first.
- If `closure_state` is terminal, no refusal is necessary.

## Invariants
- If refusal_required=True → refusal_category must be non-`NONE`.
- If refusal_required=False → refusal_category must be `NONE`.
- Decision is categorical and deterministic; no probabilities or scores.

## Fail-Closed Behavior
- Invalid inputs → `RefusalDecisionError`.
- No partial outputs; returns one bounded `RefusalDecision`.

## Non-Goals
- No refusal wording, explanations, or UI.
- No policy language, moral reasoning, or debate.
- No model calls, heuristics, weights, probabilities.
- No modifications to Phase 9.

## Closure Marker
- Step 7 refusal trigger logic is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
