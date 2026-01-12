# Phase 6 — Step 5: External Audit Interface (Conceptual)

_Date: 2026-01-08_

---

## A. Purpose & Role of the External Audit Interface
Internal auditability is insufficient when external scrutiny is required. External audit pressure is inevitable; boundaries must be defined before audits occur. This interface is contractual, not conversational: it specifies what external auditors can verify using existing artifacts without gaining access to cognition or internal reasoning.

---

## B. Definition of “External Auditor”
Eligible roles: regulators, formally designated enterprise risk teams, or independent auditors contractually authorized to assess conformance. Exclusions: end users, the general public, casual reviewers, and any party without explicit audit authorization. Access is role-based and limited to the bounded interface defined here.

---

## C. Allowed Audit Question Classes
External auditors may ask only bounded, categorical verification questions that map directly to Steps 0–4 artifacts:
- Verification of rule enforcement (presence and outcomes of rule evidence).  
- Verification of boundary activation (refusal, closure, clarification exhaustion markers).  
- Confirmation of attribution category (bounded categories from Step 3).  
- Confirmation of scope adherence (within declared accountability scope from Step 0).  

No free-form or interpretive questions; all must align to existing categorical artifacts.

---

## D. Allowed Audit Responses
Responses are categorical only:
- Verdicts: pass / fail / inconclusive.  
- Evidence state: evidence-present / evidence-missing.  
- Scope state: within-scope / out-of-scope.  

Prohibited: explanations, narratives, probabilities, free-text reasoning, model outputs, prompts, or user content.

---

## E. Mandatory Refusals
The system must refuse to provide:
- Reasoning or chain-of-thought.  
- Prompts or model outputs.  
- Internal configuration details.  
- Retroactive scope expansion or speculative answers beyond evidence.  
- Any information that would expose cognition or private data.  

Refusal is mandatory even under legal, commercial, or reputational pressure.

---

## F. Determinism & Consistency Guarantees
- Same audit query → same categorical response.  
- No auditor-specific tailoring or negotiation of outcomes.  
- Responses are bounded by artifacts; no interpretive drift.

---

## G. Relationship to Steps 0–4
- Step 0 limits conclusions and threats in scope.  
- Step 1 defines replayable units (decision traces).  
- Step 2 defines enforcement evidence categories.  
- Step 3 defines bounded failure attribution categories.  
- Step 4 defines audit readiness and replay rules.  
Step 5 cannot expand or reinterpret these artifacts.

---

## H. Failure Modes Prevented
- Coercive transparency or reasoning leakage.  
- Selective disclosure or scope creep under pressure.  
- Accountability erosion through ad-hoc answers.  
- Retroactive guarantee inflation.  
- Audit theater that pretends to verify without bounded artifacts.

---

## I. Non-Goals
- Does not design tooling, APIs, dashboards, or UX.  
- Does not define regulatory standards, authentication, or access control.  
- Does not expose cognition, prompts, or internal state.  
- Does not define remediation, enforcement actions, or auditor UX.

---

## J. Stability & Closure Marker
External audit interface semantics are stable once closed. All later phases must conform. Any change requires explicitly re-opening Phase 6 Step 5; ad-hoc modifications elsewhere are prohibited.
