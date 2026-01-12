# Phase 6 — Step 3: Violation & Failure Attribution

_Date: 2026-01-08_

---

## A. Purpose & Role of Failure Attribution
Evidence alone can show what occurred, but audits also require a categorical view of what failed when outcomes are wrong, unsafe, or contested. Attribution here is strictly classification, not explanation: it labels the locus of failure without speculating on causes or assigning blame. This supports audits without narrative or interpretive language and keeps accountability aligned with evidence.

---

## B. Definition of Failure Attribution
Failure attribution is the categorical labeling of a decision-turn outcome as belonging to a bounded failure class. It is classification, not causation: no narratives, no severity, no intent inference. Attribution is constrained to what evidence can support and excludes interpretive or diagnostic language.

---

## C. Inputs & Hard Constraints
Allowed inputs:
- Decision traces (Phase 6 Step 1).  
- Rule & boundary evidence (Phase 6 Step 2).  
- Accountability scope (Phase 6 Step 0).  

Prohibited inputs:
- Raw user input or model outputs.  
- Reasoning artifacts or chain-of-thought.  
- Probabilities, heuristics, or post-hoc interpretation.  

Attribution must not exceed the scope or detail of prior steps.

---

## D. Attribution Dimensions (Categorical, Bounded)
1. **Failure Origin Dimension**  
   - Categories (examples): rule enforcement, boundary activation, system logic, external dependency, out-of-scope.  
   - Purpose: locate which subsystem contract failed, without causal claims.
2. **Failure Type Dimension**  
   - Categories (examples): omission, commission, misclassification, inconsistency, ambiguity exposure.  
   - Purpose: classify how the failure manifests structurally.  
3. **Accountability Class Dimension**  
   - Categories: within guarantees, outside guarantees, explicitly excluded.  
   - Purpose: map failure to declared accountability scope.  

All dimensions are bounded and orthogonal; no free-form labels.

---

## E. Evidence-Backed Attribution Rules
- No attribution without matching evidence from Steps 1–2.  
- No attribution beyond evidence scope or granularity.  
- No partial, probabilistic, or speculative attribution.  
- “Unattributable” must be explicitly allowed when evidence is insufficient or absent.  

---

## F. Unknown & Unattributable Outcomes
- Attribution must be withheld when required evidence is missing, conflicting, or insufficient.  
- “Unknown” / “Unattributable” is a valid outcome and must be recorded as such.  
- Uncertainty is preserved; it is not resolved by guesswork or inference.

---

## G. Relationship to Step 2 (Evidence)
- Attribution must cite evidence categories (rule evaluation, boundary activation, gating/suppression, outcome alignment).  
- Attribution cannot reinterpret or expand evidence; evidence gaps block attribution.  
- Consistency with Step 1 traces is required; no evidence without trace alignment.

---

## H. Relationship to Step 0 (Accountability Scope)
- Attribution cannot exceed declared guarantees or include excluded threats.  
- Scope limits precision: categories stay within the Step 0 threat and guarantee boundaries.  
- Non-goals from Step 0 remain enforced (no narratives, no policy-citation-as-proof).

---

## I. Failure Modes Prevented
- Blame inflation or scapegoating without evidence.  
- Silent responsibility shifting or speculative post-mortems.  
- Selective or inconsistent attribution across similar cases.  
- “Accountability theater” where labels are applied without evidentiary backing.  
- Pressure to expose reasoning or chain-of-thought for attribution.

---

## J. Non-Goals
- Does not explain decisions or suggest fixes.  
- Does not assign severity, impact, or remediation.  
- Does not generate reports or expose attribution externally.  
- Does not alter system behavior, logging, or storage.  
- Does not introduce heuristics, probabilities, or thresholds.

---

## K. Stability & Closure Marker
Failure attribution semantics are stable once closed. All later Phase 6 steps must conform. Any change requires explicitly re-opening Phase 6 Step 3; ad-hoc modifications elsewhere are prohibited.
