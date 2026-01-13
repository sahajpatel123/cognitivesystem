# CANONICAL PHASE MAP — Decision-Aware Cognitive System
Anchors the full program roadmap. Sequential, deterministic, bounded, fail-closed. Phases 1–11 are LOCKED and immutable without reopening/recertification.

## Principles
- Safety first: bounded taxonomies, no “other” buckets, fail-closed on contradictions.
- Determinism over stochasticity; models are tools, not authorities.
- Separation of phases: no skipping, no backdoors; UI cannot mutate governance artifacts.
- Lock discipline: a phase freezes when certified; later phases must not weaken prior guarantees.
- Minimal surface for leaks: governance first, rendering and UX later.

## Phase Table (summary)
| Phase | Name | Status | Nature | Lock Condition (summary) |
| --- | --- | --- | --- | --- |
| 1 | Cognitive Design | LOCKED | Docs/Definitional | Design spec approved & frozen |
| 2 | Minimal Correct Implementation (MCI) | LOCKED | Coding | Core correctness tests pass; no heuristics |
| 3 | Model Integration Safety Boundary | LOCKED | Docs/Definitional | Safety boundary defined; no model authority |
| 4 | Decision-Aware Cognition Layer (Definitions) | LOCKED | Docs/Definitional | Decision geometry defined; bounded enums |
| 5 | Rigor & Friction Orchestration (Definitions) | LOCKED | Docs/Definitional | Rigor/friction taxonomies frozen |
| 6 | Reasoning Accountability & Auditability (Definitions) | LOCKED | Docs/Definitional | Accountability schemas frozen |
| 7 | Accountability Runtime Implementation | LOCKED | Coding | Runtime accountability tests pass |
| 8 | Deployment, Governance & Trust Hardening | LOCKED | Infra/Ops | Governance/ops checks pass |
| 9 | Decision Engine Realization (Algorithmic Core) | LOCKED | Heavy Coding | DecisionState invariants & tests pass |
| 10 | Cognitive Orchestration & Control Logic | LOCKED | Coding | ControlPlan invariants & tests pass |
| 11 | Expression & Output Governance | LOCKED | Coding + Tests | OutputPlan governance tests (abuse) pass; certification |
| 12 | Model Integration (Tool-Only) | FUTURE | Coding | Model adapters obey Phase 3, 9–11; no authority |
| 13 | Human Interaction Surface (UI/API) | FUTURE | UI/Integration | UI displays; cannot mutate plans |
| 14 | Long-Horizon Testing & Adversarial Validation | FUTURE | Testing | Adversarial battery incl. honesty/refusal/closure/audit |
| 15 | Production Hardening & Public Release | FUTURE | Infra/Ops | SLOs, rollout, guardrails verified |
| 16 | Decision Debugger & Failure Inspector | FUTURE | Tools | Trace/audit debugger certified; no forbidden leaks |
| 17 | Cost of Wrongness Meter | FUTURE | Coding | Bounded downside estimate; non-probabilistic |
| 18 | Regret Simulator | FUTURE | Coding/Simulation | Scenario-bound regret minimization, bounded inputs |
| 19 | Deep Thinking / Research Mode (Tiered) | FUTURE | Coding/Runtime | Paid extended reasoning within governance caps |
| 20 | Subscription & Capability Gating | FUTURE | Infra/Runtime | Gating cannot weaken safety; enforces TTL/quotas |
| 21 | (Optional) Persona/Tone Governance | FUTURE (Optional) | Docs/Coding | Only if needed; high-risk; must not imitate users |

## Detailed Phase Breakdown

### Phase 1 — Cognitive Design (LOCKED) — Docs/Definitional
- Purpose: define cognitive objectives, constraints, non-anthropomorphic framing, bounded taxonomies.
- Inputs/Dependencies: product charter; safety constraints.
- Deliverables: design docs; taxonomy definitions.
- Forbidden: runtime code; probabilistic claims; unbounded categories.
- Lock condition: design sign-off; taxonomy frozen.
- Why: anchors all later work in safety-first framing.

### Phase 2 — Minimal Correct Implementation (MCI) (LOCKED) — Coding
- Purpose: minimal deterministic engine satisfying core invariants.
- Inputs: Phase 1 specs.
- Deliverables: core modules; unit tests; minimal runtime wiring.
- Forbidden: heuristics, LLM calls, UI.
- Lock condition: tests green; invariants enforced; no stochastic paths.
- Why: establish a correct baseline.

### Phase 3 — Model Integration Safety Boundary (LOCKED) — Docs/Definitional
- Purpose: define strict model boundary; models are tools, never authorities.
- Inputs: Phases 1–2.
- Deliverables: boundary docs; allowed/forbidden model uses.
- Forbidden: actual model calls; authority delegation.
- Lock condition: boundary approved and frozen.
- Why: prevent uncontrolled model influence.

### Phase 4 — Decision-Aware Cognition Layer (Definitions) (LOCKED) — Docs/Definitional
- Purpose: define decision geometry (proximity, risk, reversibility, horizon, responsibility).
- Inputs: Phases 1–3.
- Deliverables: schemas, enums, invariants.
- Forbidden: runtime heuristics; UI.
- Lock condition: schemas frozen; bounded enums.
- Why: structured decision substrate.

### Phase 5 — Rigor & Friction Orchestration (Definitions) (LOCKED) — Docs/Definitional
- Purpose: define rigor/friction ladders and semantics.
- Inputs: Phases 1–4.
- Deliverables: docs; bounded ladders.
- Forbidden: runtime logic.
- Lock condition: ladders frozen; no “other”.
- Why: controlled escalation.

### Phase 6 — Reasoning Accountability & Auditability (Definitions) (LOCKED) — Docs/Definitional
- Purpose: define accountability/audit schemas and invariants.
- Inputs: Phases 1–5.
- Deliverables: docs; schemas.
- Forbidden: runtime instrumentation.
- Lock condition: schemas frozen.
- Why: enforce traceability.

### Phase 7 — Accountability Runtime Implementation (LOCKED) — Coding
- Purpose: implement accountability runtime per Phase 6.
- Inputs: Phase 6 schemas.
- Deliverables: code modules; tests; observability hooks.
- Forbidden: heuristic shortcuts; model calls.
- Lock condition: tests pass; invariants enforced.
- Why: make accountability executable.

### Phase 8 — Deployment, Governance & Trust Hardening (LOCKED) — Infra/Ops
- Purpose: deployment patterns, governance controls, hardening.
- Inputs: Phases 1–7.
- Deliverables: ops docs; governance checks.
- Forbidden: UI features; model tuning.
- Lock condition: governance checklist satisfied.
- Why: operational safety.

### Phase 9 — Decision Engine Realization (Algorithmic Core) (LOCKED) — Heavy Coding
- Purpose: realize DecisionState computation and invariants.
- Inputs: Phases 4–8.
- Deliverables: DecisionState code; tests; deterministic enums.
- Forbidden: probabilistic scoring; unbounded categories.
- Lock condition: core tests/certification pass.
- Why: anchor decision geometry in code.

### Phase 10 — Cognitive Orchestration & Control Logic (LOCKED) — Coding
- Purpose: build ControlPlan orchestration with friction/rigor/action selection.
- Inputs: Phases 5, 9.
- Deliverables: ControlPlan code; invariants; tests.
- Forbidden: model calls; UI; stochastic routing.
- Lock condition: orchestration tests pass; dominance/invariants enforced.
- Why: deterministic control over system actions.

### Phase 11 — Expression & Output Governance (LOCKED) — Coding + Tests
- Purpose: OutputPlan governance: posture, disclosures, closure, assembly; abuse defenses.
- Inputs: Phases 9–10 outputs; schemas.
- Deliverables: OutputPlan modules; selectors (Steps 1–7); assembly (Step 8); abuse/honesty tests (Step 9); certification (Step 10).
- Forbidden: UI rendering, model calls, heuristic generation.
- Lock condition: abuse suite (17 tests) green; certification doc locked.
- Why: prevent leakage/dishonesty; enforce action dominance and fail-closed behavior.

### Phase 12 — Model Integration (Tool-Only) (FUTURE) — Coding
- Purpose: integrate neural models as tools only; cannot override ControlPlan/OutputPlan; respects Phase 3 boundary.
- Inputs: Locked Phases 3, 9–11 artifacts.
- Deliverables: model adapters; bounded prompts; safety wrappers; tests for non-authority compliance.
- Forbidden: model deciding actions/disclosures/posture; bypassing assembly; storing user text in governance artifacts.
- Lock condition: compliance tests ensuring model output is subordinate; no dominance ladder bypass.
- Why: add model utility without violating governance.

### Phase 13 — Human Interaction Surface (UI/API) (FUTURE) — UI/Integration
- Purpose: present outputs; capture inputs; zero mutation of DecisionState/ControlPlan/OutputPlan.
- Inputs: Phases 9–12 outputs; governance constraints.
- Deliverables: UI/API surfaces; display-only adapters; integration tests.
- Forbidden: mutating plans; reordering actions; model prompts in UI.
- Lock condition: tests proving read-only consumption; no bypass of governance.
- Why: safe presentation layer.

### Phase 14 — Long-Horizon Testing & Adversarial Validation (FUTURE) — Testing
- Purpose: adversarial battery for honesty leakage, refusal bypass, closure bypass, unknown suppression, audit manipulation.
- Inputs: Phases 9–13.
- Deliverables: adversarial test suites; red-team scenarios; regression harness.
- Forbidden: relaxing invariants; probabilistic acceptance of violations.
- Lock condition: adversarial suite green; no regressions on governance guarantees.
- Why: harden against sophisticated failures.

### Phase 15 — Production Hardening & Public Release (FUTURE) — Infra/Ops
- Purpose: SLOs, monitoring, rollout safety, blast-radius controls.
- Inputs: Phases 8, 12–14.
- Deliverables: infra configs; runbooks; alerting; staged rollout plans.
- Forbidden: feature drift; weakening safety boundaries.
- Lock condition: ops checklist complete; canary/rollback validated.
- Why: controlled release with guardrails.

### Phase 16 — Decision Debugger & Failure Inspector (FUTURE) — Tools
- Purpose: bounded debugger for traces/failures; explain decisions without leaking forbidden artifacts.
- Inputs: Phases 7–11, 14 outputs.
- Deliverables: debugger tools; trace viewers; redaction rules; tests for non-leakage.
- Forbidden: exposing raw user text beyond policy; altering plans; model authority.
- Lock condition: debugger leak tests pass; governance review sign-off.
- Why: safe introspection and failure analysis.

### Phase 17 — Cost of Wrongness Meter (FUTURE) — Coding
- Purpose: bounded, non-probabilistic downside magnitude/regret risk estimator.
- Inputs: Decision geometry (Phase 9), orchestration (Phase 10), governance (Phase 11).
- Deliverables: meter module; enums for downside classes; tests for bounds.
- Forbidden: probabilistic forecasts; unbounded scoring; UI personalization.
- Lock condition: bounded outputs; tests for deterministic mapping.
- Why: quantify stakes without speculative probabilities.

### Phase 18 — Regret Simulator (FUTURE) — Coding/Simulation
- Purpose: scenario-based regret minimization with bounded inputs/outputs.
- Inputs: Phases 9, 10, 17.
- Deliverables: simulator module; scenario library; tests for bound adherence.
- Forbidden: open-ended simulation; probabilistic sampling without bounds.
- Lock condition: scenarios bounded; invariants and fail-closed checks pass.
- Why: stress decisions against regret outcomes safely.

### Phase 19 — Deep Thinking / Research Mode (Tiered) (FUTURE) — Coding/Runtime
- Purpose: paid extended reasoning passes within governance caps; respects OutputPlan/ControlPlan dominance.
- Inputs: Phases 10–12; gating (Phase 20).
- Deliverables: extended-pass scheduler; bounds on depth/TTL; tests.
- Forbidden: weakening safety; unlimited recursion; model authority.
- Lock condition: depth/TTL enforced; governance invariants unchanged.
- Why: offer deeper analysis without compromising safety.

### Phase 20 — Subscription & Capability Gating (FUTURE) — Infra/Runtime
- Purpose: paid capability gating (TTL, extended memory if allowed, deeper reasoning, research tooling, model tier choices).
- Inputs: Phases 12, 19.
- Deliverables: gating service; quota enforcement; tests ensuring safety unaffected.
- Forbidden: altering cognition truthfulness; bypassing OutputPlan/ControlPlan; personalization of tone/persona without governance.
- Lock condition: gating tests confirm no safety downgrades; quotas and TTL enforced.
- Why: monetize capabilities while preserving safety guarantees.

### Phase 21 — Persona/Tone Governance (Optional, High-Risk) (FUTURE) — Docs/Coding
- Purpose: if ever needed, tightly governed tone/persona controls; must not imitate users; optional and high-risk.
- Inputs: Phases 11, 20.
- Deliverables: bounded tone enums; governance docs; tests for non-imitation.
- Forbidden: personalization without consent; user imitation; safety downgrades.
- Lock condition: governance approval; leak tests; bounded enums only.
- Why: isolate high-risk stylistic behavior under strict governance.
