# Phase 6 — Step 2: Rule & Boundary Evidence

_Date: 2026-01-08_

---

## A. Purpose & Role of Rule & Boundary Evidence
Decision traces (Step 1) show structure but are insufficient alone; enforcement must be evidenced to prove rules and boundaries were applied. Evidence is not reasoning: it is categorical confirmation that enforcement events occurred. Evidence supports post-hoc audits by demonstrating compliance without exposing internal content or chain-of-thought.

---

## B. Definition of Rule Evidence
Rule evidence is the categorical outcome of evaluating a declared rule during a turn. Allowed outcomes: `checked`, `pass`, `fail`, `not_applicable`. Rule evidence excludes internal thresholds, heuristics, or parameters; it is category-level only and does not reveal reasoning mechanics or probabilities.

---

## C. Definition of Boundary Evidence
Boundary evidence captures activation of boundary controls (e.g., refusal, closure, clarification exhaustion, gating/suppression). It records that a boundary was enforced and which boundary category applied. It does not explain content, provide wording, or expose underlying reasoning.

---

## D. Evidence Categories & Taxonomy
Allowed evidence categories:
- **Rule evaluation evidence** — categorical outcomes for declared rules.  
- **Boundary activation evidence** — categorical markers for refusal, closure, or clarification exhaustion.  
- **Gating/suppression evidence** — indicators that actions or outputs were suppressed or halted under policy.  
- **Outcome alignment evidence** — confirmation that produced outcomes align with permitted categories (e.g., risk domain tags) without revealing text.  

No text payloads, scores, or probabilities are included.

---

## E. Completeness Requirements
- Required when applicable: rule evaluation evidence for each rule exercised; boundary activation evidence for any enforced boundary; outcome alignment evidence when outcomes are produced.  
- Optional: none beyond explicitly allowed markers.  
- Missing required evidence constitutes an accountability failure.  
- Evidence absence must be explicit; silent omission is non-compliant.

---

## F. Consistency & Alignment Rules
- No outcome without matching evidence where a rule or boundary applies.  
- No evidence without a corresponding trace element from Step 1.  
- No conflicting evidence states for the same rule or boundary in a turn.  
- Evidence must align with trace scope and categories; misalignment is treated as a violation.

---

## G. Relationship to Step 1 (Trace Semantics)
- Evidence must fit within the trace elements defined in Step 1 and respect per-turn scope.  
- Evidence inherits immutability and deterministic interpretation expectations.  
- Evidence detail is bounded to trace granularity; no expansion beyond Step 1 allowances.

---

## H. Relationship to Step 0 (Accountability Scope)
- Only guarantees declared in Step 0 may be evidenced.  
- Only Step 0 failure classes may be attributed.  
- Threat model constraints apply: no reasoning exposure, no prompt leakage, no policy-citation-as-proof.  
- Non-goals from Step 0 remain enforced.

---

## I. Failure Modes Prevented
- Unjustified refusals lacking boundary evidence.  
- Silent boundary bypasses or missing gating indicators.  
- Selective enforcement logging that omits unfavorable outcomes.  
- Model blame without proof of rule evaluation results.  
- “Accountability theater” where evidence is partial or inconsistent with traces.

---

## J. Non-Goals
- Does not define logging mechanisms, storage, or retention.  
- Does not implement enforcement or evidence collection.  
- Does not expose evidence to users or design audit tools.  
- Does not introduce heuristics, thresholds, probabilities, or runtime behavior.

---

## K. Stability & Closure Marker
Rule & boundary evidence semantics are stable once closed. All later Phase 6 steps must conform. Any change requires explicitly re-opening Phase 6 Step 2; ad-hoc modifications elsewhere are prohibited.
