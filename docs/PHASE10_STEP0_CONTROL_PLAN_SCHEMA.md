# Phase 10 — Step 0: ControlPlan Schema & Invariants

## Purpose
Define and lock the bounded, deterministic, immutable `ControlPlan` schema that Phase 10 produces. This is the sole output contract for Phase 10. No orchestration or mapping from `DecisionState` occurs here; only structure, enums, and invariants are defined.

## What this is
- Canonical schema for Phase 10 outputs.
- Bounded categorical enums; no free-form text (except bounded IDs).
- Deterministic identity binding to `trace_id` and `decision_state_id`.
- Fail-closed validation via typed error on invariant violations.

## What this is NOT
- Not orchestration or decision-to-control mapping logic.
- Not expression generation or user-visible text.
- Not model/LLM integration.
- Not UI, API, or product behavior.
- Not heuristic, probabilistic, or weighted scoring.

## Field Listing (bounded)
- `schema_version` (fixed: `"10.0.0"`)
- `phase_marker` (`PHASE_10`)
- `control_plan_id` (deterministic UUIDv5 from trace_id + decision_state_id + action + schema_version)
- `trace_id` (binds to Phase 7 trace)
- `decision_state_id` (binds to Phase 9 DecisionState)
- `created_at` (optional; does not affect determinism)
- `action` (`ANSWER_ALLOWED`, `ASK_ONE_QUESTION`, `REFUSE`, `CLOSE`, `ABORT_FAIL_CLOSED`)
- `rigor_level` (`MINIMAL`, `GUARDED`, `STRUCTURED`, `ENFORCED`, `UNKNOWN`)
- `friction_posture` (`NONE`, `SOFT_PAUSE`, `HARD_PAUSE`, `STOP`)
- `clarification_required` (bool)
- `clarification_reason` (`DISAMBIGUATION`, `MISSING_CONTEXT`, `SAFETY`, `SCOPE_CONFIRMATION`, `UNKNOWN`)
- `question_budget` (int, allowed values: 0 or 1)
- `question_class` (`INFORMATIONAL`, `SAFETY_GUARD`, `CONSENT`, `OTHER_BOUNDARY`, or None)
- `confidence_signaling_level` (`MINIMAL`, `GUARDED`, `EXPLICIT`)
- `unknown_disclosure_level` (`NONE`, `PARTIAL`, `FULL`)
- `initiative_allowed` (bool)
- `initiative_budget` (`NONE`, `ONCE`, `STRICT_ONCE`)
- `closure_state` (`OPEN`, `CLOSING`, `CLOSED`, `USER_TERMINATED`)
- `refusal_required` (bool)
- `refusal_category` (`NONE`, `CAPABILITY_REFUSAL`, `EPISTEMIC_REFUSAL`, `RISK_REFUSAL`, `IRREVERSIBILITY_REFUSAL`, `THIRD_PARTY_REFUSAL`, `GOVERNANCE_REFUSAL`, or None)

## Invariants (fail-closed)
- `question_budget` must be 0 or 1.
- `ASK_ONE_QUESTION` requires `question_budget == 1`.
- `ANSWER_ALLOWED` cannot have `refusal_required == True`.
- `REFUSE` requires `refusal_required == True` (except `ABORT_FAIL_CLOSED` path).
- `CLOSE` cannot require clarification.
- `closure_state == CLOSED` is incompatible with `ASK_ONE_QUESTION`.
- `control_plan_id` must equal deterministic UUIDv5(trace_id, decision_state_id, action, schema_version).
- `schema_version` must be `"10.0.0"`; `phase_marker` must be `PHASE_10`.

## Fail-Closed Behavior
- Any invariant violation raises `ControlPlanValidationError`.
- No partial or degraded ControlPlan is emitted on failure.

## Non-Goals
- No mapping from `DecisionState` to `ControlPlan`.
- No adaptive behavior, weights, probabilities, or heuristics.
- No free-form questions, refusals, or explanatory text.
- No cross-request memory, caches, or learning.
- No UI/API exposure.

## Closure Marker
- Step 0 schema is defined and locked for Phase 10.
- Any semantic or structural change to ControlPlan requires reopening Phase 10 and re-certification.
