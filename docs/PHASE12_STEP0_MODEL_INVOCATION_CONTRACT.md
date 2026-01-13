# Phase 12 — Step 0: Model Invocation Contract + Trust Boundary Lock

## A. Purpose of Step 0
- Establish a canonical contract for all future model (LLM) invocations.
- Bind model calls to the existing governance chain (DecisionState → ControlPlan → OutputPlan).
- Ensure all invocations are deterministic, bounded, and fail-closed before any provider integration.
- Prevent scope drift into model choice, prompt tuning, or runtime heuristics.

## B. Model Role Framing (IS / IS NOT)
- **IS:** A tool for rendering bounded outputs (text/JSON/refusal/closure) under OutputPlan dominance.
- **IS NOT:** A decision-maker, planner, orchestrator, memory store, policy interpreter, or authority.
- Model output is never authoritative; OutputPlan dominates model output.

## C. Trust Boundary & Dependency Direction
- Inputs are untrusted user text; trust flows only through certified artifacts: DecisionState (Phase 9) → ControlPlan (Phase 10) → OutputPlan (Phase 11).
- All model calls must pass through the Phase 3 adapter + enforcement choke point.
- No direct or side-channel model access outside this boundary.

## D. Invocation Classes (bounded taxonomy)
- `TEXT_RENDERING_ONLY`
- `JSON_RENDERING_ONLY`
- `REFUSAL_RENDERING_ONLY`
- `CLOSURE_RENDERING_ONLY`
- No “other” class allowed.

## E. Input Contract (allowed/forbidden fields)
- Allowed fields: `trace_id`, `decision_state_id`, `control_plan_id`, `output_plan_id`, `invocation_class`, `output_format`, `user_text` (current request only), `required_elements` (bounded tuple), `forbidden_requirements` (bounded tuple), `max_output_tokens`, `schema_version=12.0.0`, `phase_marker=PHASE_12`.
- Forbidden: provider selection, retries, fallbacks, tool-use, browsing, memory, user identity, audit logs, raw model prompts beyond structural placeholders.
- OutputPlan dominance: invocation must respect the precomputed OutputPlan; model cannot change action/posture/disclosures.

## F. Output Contract (allowed/forbidden patterns)
- Allowed outputs: bounded text or JSON matching the requested format; refusal/closure renderings when specified.
- Forbidden: multi-action planning, policy changes, memory claims, confidence fabrication, undisclosed assumptions, or bypass of OutputPlan/ControlPlan decisions.
- Model output is never authoritative; any contradiction must be rejected.

## G. Failure Semantics (typed failures, fail-closed)
- Typed failures: `TIMEOUT`, `PROVIDER_ERROR`, `NON_JSON`, `SCHEMA_MISMATCH`, `CONTRACT_VIOLATION`, `FORBIDDEN_CONTENT`.
- Fail-closed: any violation yields a failure object with `fail_closed=True`; no partial acceptance.
- Invalid inputs or outputs must raise contract errors before any downstream use.

## H. Non-Goals + Stability Marker
- Non-goals: provider choice, prompt engineering, retries, caching, memory extensions, UI wiring, model tuning.
- Stability marker: Step 0 is a locked contract for Phase 12; modifications require reopening the phase and recertification.  
- This step does not implement live model calls; it only defines the interface and validation.
