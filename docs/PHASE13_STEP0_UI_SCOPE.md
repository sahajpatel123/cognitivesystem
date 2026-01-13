# Phase 13 — Step 0: UI Scope, Boundaries & Page Map

## A) Purpose
- Lock UI scope before any implementation so Phase 13 cannot drift into feature creep, chatbot behavior, or governance bypass.
- Prevent UI-driven leakage of governed internals or authority inversion where UI choices influence rigor, friction, or action dominance.
- Establish non-negotiable guardrails for interaction surfaces that consume governed outputs while keeping the governed core sealed.

## B) Definitions
- **Governed core**: The certified pipeline (DecisionState, ControlPlan, OutputPlan, invocation, verification, fallback, orchestrator) that determines action and rendered text; only trusted locus of cognition and enforcement.
- **Untrusted UI**: Any client or frontend surface; treated as attacker-controlled, incapable of cognition, must never influence control/output dominance.
- **Authority boundary**: The hard separation where UI stops and governed core begins; UI may only submit user_text and render returned fields.
- **Output dominance**: The OutputPlan action chosen by the governed core; UI must honor it and must not attempt overrides or alternative actions.
- **Rendering-only surface**: UI behavior limited to capturing user_text, displaying returned rendered_text, and showing bounded action badges with minimal affordances.

## C) Scope (What UI is allowed to do)
- Accept `user_text` input from the person.
- Send `{ user_text: string }` to the backend governed endpoint.
- Display returned `rendered_text` verbatim from the governed core.
- Display bounded action badge limited to: ANSWER, ASK_ONE_QUESTION, REFUSE, CLOSE (FALLBACK treated as governed failure state, not a UI-driven action choice).
- Disable further input when closure/refusal/terminal state is indicated.
- Show minimal, generic errors without exposing internals.
- Maintain transient, session-local UI state only; no persistence beyond session unless a future certified phase allows.

## D) Non-Scope / Forbidden UI Capabilities
- No decision logic, no plan construction, no action selection by UI.
- No memory/personalization, profiling, or identity-based adaptation.
- No long-history injection or replay outside current governed session scope.
- No exposure of DecisionState, ControlPlan, OutputPlan, trace IDs, evidence, attribution, audit artifacts, or internal prompts.
- No auto follow-ups, multi-question rendering, or agentic behaviors.
- No prompt rewriting, prompt stuffing, or attempts to alter internal system prompts.
- No “agent mode,” personality layers, or autonomous reasoning in UI.

## E) Trust Boundaries
- UI/client is untrusted; inputs must be validated server-side.
- Network is untrusted; contracts must be explicit and validated on arrival.
- Model layer is untrusted; governed pipeline must verify and fallback.
- Only governed core is trusted; trust is non-transitive and must not be delegated to UI or transport.

## F) UI Page Map / Sitemap (Phase 13 lock)
- Allowed canonical routes: `/` (home), `/product`, `/product/chat` (primary governed interaction surface), optional `/product/about`, optional `/product/docs`, legal/compliance pages as existing.
- Prohibited/deferrable routes unless a future certified phase authorizes: internal dashboards, memory viewers, trace viewers, audit artifact viewers, personalization panels, experimental labs.
- The governed chat interaction MUST remain at: Product navbar → Chat page, route `/product/chat`.

## G) UI ↔ Backend Interface Contract
- Request schema (UI → backend): `{ user_text: string }` only; no additional fields, flags, or modes.
- Response schema (backend → UI): `{ action: enum(ANSWER | ASK_ONE_QUESTION | REFUSE | CLOSE | FALLBACK), rendered_text: string, optional failure_type: string, optional failure_reason: string }`.
- No DecisionState/ControlPlan/OutputPlan objects, trace IDs, evidence, audit bundles, or model artifacts may be returned.
- UI must render only these bounded fields and must not attempt inference beyond them.

## H) Failure & Abuse Handling
- Fail-closed: on malformed input, rate limiting, or governance refusal, backend returns bounded error/REFUSE/FALLBACK; UI must not retry with altered semantics automatically.
- UI cannot bypass throttling, auth, or governance; must surface minimal generic error text only.
- Unauthorized access must yield minimal refusal/error without revealing internals.
- No “best effort” degradation that leaks internals; prefer hard stop with bounded message.

## I) Monitoring & Logging (UI/Client Side)
- No sending raw user text to third-party analytics.
- No storing decision internals or action metadata beyond session-local transient state.
- Session-only UI state allowed for rendering; must not create hidden feedback loops into cognition.
- Any telemetry (if later allowed) must exclude raw prompts and governed internals unless explicitly re-certified.

## J) Dependency Rules
- UI must follow Phase 10 ControlPlan and Phase 11 OutputPlan dominance; cannot override or branch.
- Phase 12 model is tool-only; UI cannot request alternate modes or non-governed paths.
- Any contract/schema changes require reopening Phase 13 Step 0 and re-certification before code changes.

## K) Non-Goals
- No UI design, animation, branding polish, or aesthetic expansion in this step.
- No personalization, optimization, or experimentation features.
- No model tuning, prompt tuning, or pipeline alterations.

## L) Stability Marker / Closure
- Phase 13 Step 0 is defined and locked.
- Any change to UI boundaries, sitemap, or interface contract requires reopening Phase 13 Step 0 under governance.
