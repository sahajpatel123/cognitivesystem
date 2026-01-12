# Phase 6 — Step 1: Decision Trace Semantics

_Date: 2026-01-08_

---

## A. Purpose & Role of Decision Traces
Decision traces are required for accountability: they provide verifiable evidence that the system followed its declared rules without revealing internal reasoning. Reasoning transcripts are forbidden; traces must remain structural and minimal. Traces differ from logs or explanations: they are scoped artifacts for audit, not narratives. They preserve privacy and integrity by excluding user content replay and chain-of-thought.

---

## B. Definition of a Decision Trace
A decision trace is the minimal, per-turn, structural record that demonstrates which rule checks, boundaries, and outcomes occurred during a system turn. It proves conformance to declared safeguards without exposing internal reasoning or prompts. It cannot reveal model outputs, chain-of-thought, or user text beyond categorical references needed for boundary evidence.

---

## C. Non-Definition (Explicit Exclusions)
A decision trace is **not**:
- Chain-of-thought or internal reasoning.  
- Prompt content or raw model outputs.  
- User input replay.  
- Explanation narrative.  
- Probability, score, or ranking artifact.  
- Engagement or UX transcript.  

---

## D. Trace Scope & Granularity
- Scope: single system turn only; no cross-session or cross-turn aggregation.  
- Coverage: captures Phase 4–5 outcomes (as categories/flags) and Phase 3 by outcome reference only (no model internals).  
- Boundaries: no historical accumulation; each trace stands alone for its turn.  
- Granularity: sufficient to prove rule/boundary application, no finer-grained reasoning steps.

---

## E. Trace Elements (Conceptual)
Allowed conceptual elements:
- **Trace identifier**: opaque, non-semantic.  
- **Phase traversal markers**: which phases/steps were exercised this turn.  
- **Rule evaluation evidence**: pass / fail / not-applicable for declared contracts.  
- **Boundary activation markers**: refusal category, closure invoked, clarification exhaustion.  
- **Outcome classification**: category-level (e.g., risk domain tags), without underlying text.  

No timestamps unless strictly required; no probabilities; no scores.

---

## F. Completeness Guarantees
- **Required elements**: trace ID, phase traversal markers, rule evaluation evidence, boundary activation markers when triggered, outcome classification when produced.  
- **Optional elements**: none beyond explicit allowances; omission is treated as absence.  
- **Incomplete trace**: missing any required element → accountability failure.  
- Missing required evidence must be surfaced as a violation, not silently tolerated.

---

## G. Determinism & Immutability
- Trace interpretation is deterministic: given a trace, audit conclusions are stable.  
- Traces are immutable after creation; no post-hoc edits.  
- Audit conclusions must not depend on execution order beyond what the trace encodes.  
- Traces support replay of evidence (not cognition) without re-running models.

---

## H. Relationship to Phase 6 Step 0
- Constrained by Step 0: only guarantees declared there may appear as trace evidence.  
- Threat model limits trace detail; no leakage of reasoning or prompts.  
- Non-goals from Step 0 remain enforced: no narrative proof, no policy citation as evidence, no best-effort transparency.

---

## I. Failure Modes Prevented
- Post-hoc rationalization masquerading as evidence.  
- Selective logging or omission of boundary events.  
- Pressure to expose chain-of-thought.  
- Untraceable refusals or closures.  
- “Accountability theater” where traces lack required completeness.

---

## J. Non-Goals
- Does not define logging mechanisms or storage backends.  
- Does not implement trace collection or replay.  
- Does not design audit tooling or user-facing exposure.  
- Does not add heuristics, thresholds, or runtime behavior.

---

## K. Stability & Closure Marker
Decision trace semantics are stable once closed. All later Phase 6 steps must conform. Any change requires explicitly reopening Phase 6 Step 1; ad-hoc modifications elsewhere are prohibited.
