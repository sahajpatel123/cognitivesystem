# Phase 12 — Step 3: Invocation Pipeline Integration (Canonical Path)

## Purpose
- Integrate prompt builder (Step 2) and runtime adapter (Step 1) into a single deterministic pipeline.
- Keep the model tool-only; OutputPlan dominance is enforced.
- Deliver a bounded candidate output with fail-closed behavior.

## Trust Boundary
- All invocations pass through the Phase 3 choke point (enforcement + LLM client).
- Inputs: DecisionState, ControlPlan, OutputPlan (from Phases 9–11); user_text (current turn).
- No direct provider calls outside the adapter; no bypass of governance artifacts.

## Canonical Call Order
1) Validate OutputPlan (fail-closed).
2) Build ModelInvocationRequest (Step 2 prompt builder).
3) Invoke model via runtime adapter (Step 1) through Phase 3 boundary.
4) Validate candidate output against OutputPlan and contract.
5) Return ModelInvocationResult (or typed failure), fail-closed.

## OutputPlan Dominance Rules
- Model cannot change action/posture/disclosures/closure/refusal/question budgeting.
- Model output is only a candidate payload; governance decisions stay upstream.
- Data minimization: no DecisionState/ControlPlan/governance internals in prompts.

## Candidate Validation Rules
- No empty outputs; length bounded.
- ASK_ONE_QUESTION: strict JSON `{ "question": "string" }`, one sentence, no extra keys, no multi-question phrasing.
- REFUSE: no loopholes, no policy/internal-rule language.
- CLOSE: no reopening, no questions, terse.
- ANSWER: no new questions, no refusal phrasing; honor unknown disclosure and guarded/explicit confidence.
- No tool-claim phrases; no hidden metadata (e.g., `<analysis>`, system prompt leaks).
- Any violation → typed failure (CONTRACT_VIOLATION/SCHEMA_MISMATCH/FORBIDDEN_CONTENT/PROVIDER_ERROR/TIMEOUT/NON_JSON).

## Failure Mapping (Fail-Closed)
- Validation failures → CONTRACT_VIOLATION or SCHEMA_MISMATCH.
- Non-JSON when JSON expected → NON_JSON.
- External/timeout → TIMEOUT/PROVIDER_ERROR.
- Forbidden content/tool-claims → FORBIDDEN_CONTENT.
- All failures include `fail_closed=True`; no partial acceptance.

## Non-Goals
- No provider/model selection, no retries/fallbacks, no prompt tuning, no streaming/tools/function-calling, no UI, no personalization/memory.

## Stability Marker
- Step 3 pipeline is locked upon approval. Any change requires reopening Phase 12 and re-certifying contract, prompt builder, runtime adapter, and validator together. OutputPlan dominance cannot be weakened.
