# Phase 11 — Step 0: OutputPlan Schema & Invariants

## Purpose
Define the bounded, deterministic, immutable `OutputPlan` schema for governed output intent. No text generation, no rendering, no orchestration logic, no model calls.

## What OutputPlan IS / IS NOT
- IS: A bounded plan of output intent and controls (action, posture, disclosure, refusal/closure/question specs).
- IS NOT: Generated text, templates, UI, model prompts, or Phase 11 later steps (rendering, explanation).
- IS NOT: A place for free-form metadata or extensibility hooks.

## Inputs & Outputs (bounded)
- Inputs: Deterministic IDs (trace_id, decision_state_id, control_plan_id), selected action, bounded posture/disclosure knobs, optional bounded sub-specs.
- Output: Immutable `OutputPlan` with deterministic UUIDv5 id; no free text.

## Taxonomy (all bounded)
- Phase marker: `PHASE_11`; schema_version: `11.0.0`.
- Actions: `ANSWER`, `ASK_ONE_QUESTION`, `REFUSE`, `CLOSE`.
- ExpressionPosture: `BASELINE`, `GUARDED`, `CONSTRAINED`.
- RigorDisclosureLevel: `MINIMAL`, `GUARDED`, `STRUCTURED`, `ENFORCED`.
- ConfidenceSignalingLevel: `MINIMAL`, `GUARDED`, `EXPLICIT`.
- AssumptionSurfacingMode: `NONE`, `LIGHT`, `REQUIRED`.
- UnknownDisclosureMode: `NONE`, `IMPLICIT`, `EXPLICIT`.
- VerbosityCap: `TERSE`, `NORMAL`, `DETAILED`.
- RefusalExplanationMode: `BRIEF_BOUNDARY`, `BOUNDED_EXPLANATION`, `REDIRECT_TO_SAFE_FRAME`.
- ClosureRenderingMode: `SILENCE`, `CONFIRM_CLOSURE`, `BRIEF_SUMMARY_AND_STOP`.
- QuestionSpec: `question_class` (Phase 10 `QuestionClass`), `priority_reason` (Phase 10 `QuestionPriorityReason`).
- RefusalSpec: `refusal_category` (Phase 10 `RefusalCategory`), `explanation_mode` (bounded above).
- ClosureSpec: `closure_state` (Phase 10 `ClosureState`), `rendering_mode` (bounded above).

## Key Invariants (fail-closed)
- Phase marker must be `PHASE_11`; schema_version must be `11.0.0`; id must be deterministic UUIDv5 over (trace_id, decision_state_id, control_plan_id, action, schema_version).
- Action/scope exclusivity:
  - `ANSWER`: no question/refusal/closure spec.
  - `ASK_ONE_QUESTION`: requires `question_spec`; no refusal/closure spec; verbosity ≠ `DETAILED`; rigor_disclosure ≠ `ENFORCED`.
  - `REFUSE`: requires `refusal_spec`; refusal_category ≠ `NONE`; posture must be `CONSTRAINED`; confidence_signaling ≥ `GUARDED`; verbosity ≠ `DETAILED`; no question/closure spec.
  - `CLOSE`: requires `closure_spec`; verbosity ∈ {`TERSE`,`NORMAL`}; posture ≥ `GUARDED`; no question/refusal spec.
- Unknown disclosure: if rigor_disclosure == `ENFORCED`, then unknown_disclosure ≠ `NONE`.

## Fail-Closed Semantics
- Any invariant violation raises `OutputPlanInvariantViolation` (typed). No silent fallback, no partial plans.

## Non-Goals
- No rendering, templates, or text generation.
- No model/LLM usage.
- No UI, no orchestration integration in this step.
- No free-form fields or escape-hatch categories.

## Stability / Closure Marker
- Step 0 schema is defined and locked. Any change to enums, fields, or invariants (including schema_version) requires reopening Phase 11 and re-certification.
