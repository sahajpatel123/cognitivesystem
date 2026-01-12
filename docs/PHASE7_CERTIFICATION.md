# Phase 7 — Certification, Conformance, and Lock

## Scope
- Formalizes and freezes Phase 7 semantics for accountability runtime.
- Applies to: decision traces, rule & boundary evidence, failure attribution, internal audit replay, external audit interface.
- Excludes any new runtime behavior, cognition changes, or extensions beyond Phases 1–6 inputs and Phase 7 outputs.

## Guarantees (Positive)
- Every decision instance has exactly one decision trace; creation is deterministic and trace-bound.
- Trace lifecycle is immutable and closes exactly once as COMPLETED or ABORTED; closed traces cannot be mutated.
- Rule and boundary evidence are categorical, bounded enums, and bound to the originating trace (trace_id match required).
- Evidence must be present (rule and/or boundary) before closure; missing evidence fails closed.
- Aborted decisions require exactly one failure attribution, categorical and bounded, bound to the trace, deterministic for identical inputs.
- Failure attribution never performs inference, heuristics, or causal reasoning; it is categorical with explicit UNKNOWN/UNATTRIBUTABLE handling.
- Internal audit replay is deterministic, read-only, and replay-only: it verifies artifacts without re-execution of cognition or models.
- Internal audit outcomes are categorical (PASS, FAIL_*, INCONCLUSIVE); missing or unverifiable artifacts cannot yield PASS.
- External audit interface is verdict-only, deterministic, read-only; it maps completed internal audit outcomes to bounded external verdicts without exposing artifacts.
- Dependency direction is enforced: artifacts flow into audits; audits never modify or generate artifacts.

## Non-Guarantees (Negative Scope)
- No guarantee of correctness, optimality, fairness, bias mitigation, ethics, or value alignment of answers or decisions.
- No guarantee of preventing harmful, low-quality, or undesirable decisions.
- No explanation, justification, causal account, or narrative of reasoning or attribution.
- No guarantee of human agreement, satisfaction, or preference alignment.
- No persistence, storage durability, or archival guarantees for traces, evidence, attribution, or audits.
- No performance, latency, throughput, or availability guarantees.
- No probabilistic confidence, scoring, ranking, or heuristic outputs.

## Certification Invalidation Triggers (Any single trigger voids certification)
- Mutating a trace, evidence record, or failure attribution after creation/closure.
- Allowing trace closure without required evidence or (for aborted) attribution.
- Persisting or externalizing traces/evidence/attribution beyond approved scope.
- Adding explanations, metadata, or artifact exposure to external audit responses.
- Re-executing cognition, models, or decision logic during audit (internal or external).
- Introducing heuristics, probabilities, retries, or fallbacks into audit or attribution.
- Capturing reasoning text, user text, prompts, or model outputs inside accountability artifacts.
- Adding new audit outcomes, roles, scopes, or semantics beyond the bounded enums.
- Allowing missing or unverifiable artifacts to yield PASS.

## Recertification Rules
- Any invalidation trigger requires reopening Phase 7 and full re-certification.
- Re-certification must explicitly review all Phase 7 artifacts (trace, evidence, attribution, internal audit, external audit interface) against Phase 6 semantics.
- Later phases may consume Phase 7 outputs but may not alter Phase 7 semantics; any such alteration requires Phase 7 to be reopened and re-certified.

## Dependency Constraints
- Phase 7 depends only on Phases 1–6 semantics and artifacts.
- Phases 8+ may depend on Phase 7 outputs but must not mutate or reinterpret Phase 7 semantics.
- No reverse dependencies: Phase 7 must remain unaffected by later phases.

## Closure Declaration
- Phase 7 is COMPLETE.
- Phase 7 is CERTIFIED.
- Phase 7 is LOCKED.
- Any certification invalidation trigger voids this certification and mandates re-certification before further changes proceed.
