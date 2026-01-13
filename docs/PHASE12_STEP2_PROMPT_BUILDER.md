# Phase 12 — Step 2: Model Prompt Builder + OutputPlan Binding

## Purpose / Scope
- Deterministic translation of (user_text + OutputPlan) → ModelInvocationRequest.
- Enforces OutputPlan dominance; model is tool-only and non-authoritative.
- No provider choice, no prompt tuning beyond minimal envelope, no retries/fallbacks.

## Trust Boundary
- Uses Phase 12 contract types; output_plan already validated (Phase 11).
- Builder outputs ModelInvocationRequest only; actual invocation still goes through Phase 3 choke point (enforcement + LLM client).
- No DecisionState/ControlPlan/raw governance data passed to model; data minimization applied.

## Mapping Rules (OutputPlan → Invocation Class/Format)
- OutputAction.ANSWER → ModelInvocationClass.EXPRESSION_CANDIDATE, output_format=TEXT.
- OutputAction.ASK_ONE_QUESTION → ModelInvocationClass.CLARIFICATION_CANDIDATE, output_format=JSON (strict schema).
- OutputAction.REFUSE → ModelInvocationClass.REFUSAL_EXPLANATION_CANDIDATE, output_format=TEXT.
- OutputAction.CLOSE → ModelInvocationClass.CLOSURE_MESSAGE_CANDIDATE, output_format=TEXT (terse, non-expanding).

## Envelope Structure
1) SYSTEM HEADER: non-authoritative, must follow format, must not mention internal phases/constraints.
2) TASK BLOCK: action-specific (answer/clarify/refuse/close) with prohibitions on adding actions/questions.
3) CONSTRAINT TAGS: posture, rigor_disclosure, confidence_signaling, unknown_disclosure, assumption_surfacing, verbosity_cap, action.
4) USER INPUT: current user_text only (verbatim).
5) OUTPUT FORMAT CONTRACT:
   - TEXT: plain text only, no rule/governance language.
   - JSON (ASK_ONE_QUESTION): schema `{ "question": "string" }`, one sentence, no extra keys.

## Forbidden Data / Terms
- No DecisionState, ControlPlan, trace_id, audit, governance, memory, or internal rule language in the envelope.
- Model cannot set or alter actions, disclosures, posture, refusal/closure states, or question budgets.

## Fail-Closed Rules
- Invalid OutputPlan invariants → ModelPromptBuilderError.
- Mismatch of action→format mapping → ModelPromptBuilderError.
- Forbidden terms present → ModelPromptBuilderError.
- Resulting request validated via `validate_model_request`; any violation raises ModelPromptBuilderError.

## Non-Goals
- No provider/model selection, no prompt tuning, no retries, no streaming/tools/function-calling, no history/memory, no UI.

## Stability Marker
- Step 2 is locked once approved; any change requires reopening Phase 12 and re-certification together with the contract and runtime adapter. OutputPlan dominance must not be weakened.
