# Phase 10 — Step 8: ControlPlan Assembly & Cross-Step Validation

## Purpose
Execute Steps 1–7 in canonical order, apply override rules, enforce cross-step invariants, and emit a fully validated `ControlPlan` or fail closed with a typed error. No text generation or model calls occur here.

## Canonical Order
1) Rigor: `select_rigor`
2) Friction: `select_friction`
3) Clarification trigger: `decide_clarification`
4) Single-question compression (if `question_budget==1`): `select_single_question`
5) Initiative discipline: `select_initiative`
6) Closure detection: `detect_closure` (uses bounded user_text markers)
7) Refusal trigger: `decide_refusal`
8) Apply override rules
9) Build final `ControlPlan` (fail-closed on validation)

## Override Rules (mandatory)
- Closure cancels asks/interventions: if `closure_state` in `{CLOSED, USER_TERMINATED}` → `clarification_required=False`, `question_budget=0`, `question_class=None`, `initiative_budget=NONE`, `warning_budget=0`.
- Clarification consumes intervention slot: if `clarification_required=True` → `warning_budget=0`.
- Refusal overrides answer permission: refusal-required plans must not yield “answer allowed”.
- Question selection consistency: `question_budget==1` ⇒ `question_class` present; `question_budget==0` ⇒ `question_class=None`.
- STOP friction consistency: if `friction_posture==STOP`, then at least one of {refusal, closure != OPEN, clarification} must hold; else fail.

## Cross-Step Invariants
- Refusal required ⇒ refusal_category ≠ `NONE`; else refusal_category must be `NONE`.
- Clarification budget consistency (`question_budget` ∈ {0,1}) and matching selection.
- Initiative after clarification: `warning_budget` must be 0 when clarification is active.
- Final `ControlPlan` must satisfy schema invariants (fail-closed on violation).

## Failure Semantics
- Any contradiction or invariant violation raises `OrchestrationAssemblyError`.
- `ControlPlan` construction errors (schema validation) are wrapped as assembly failures.

## Non-Goals
- No refusal wording or explanations.
- No question wording or templates.
- No expression governance (Phase 11).
- No model/tool calls, heuristics, weights, or probabilities.
- No Phase 10 Step 9 lock in this step.

## Closure Marker
- Step 8 assembly and validation is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
