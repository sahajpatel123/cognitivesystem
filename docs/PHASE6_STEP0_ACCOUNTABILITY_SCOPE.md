# Phase 6 — Step 0: Accountability Scope & Threat Model

_Date: 2026-01-08_

---

## A. Purpose & Role of Accountability
Accountability is required to preserve trust in a decision-grade system where outputs may influence real-world actions. Post-hoc correctness matters because downstream effects can be audited after the fact; the system must be able to demonstrate that its safeguards were applied as designed. Explanation alone is insufficient: narrative justifications are not equivalent to verifiable proof. This system rejects “trust us” narratives and demands evidence-backed accountability.

---

## B. Accountability Audience
Primary audiences:
- **Internal maintainers and auditors** — verify adherence to contracts and invariants.  
- **Regulators or external auditors (when applicable)** — assess conformance to declared guarantees.  
- **Automated validators** — mechanically check invariant compliance and boundary enforcement.  

Non-primary audiences:
- **End users or casual inspection** — accountability artifacts are not optimized for conversational exposure.  

Separation is necessary to maintain rigor, avoid leaking internal reasoning, and ensure that accountability artifacts target verification, not persuasion.

---

## C. Accountability Guarantees
What must be provable (structurally):
- **Rule adherence** — actions followed declared contracts and constraints.  
- **Boundary enforcement** — refusals and limits were applied when mandatory.  
- **Refusal legitimacy** — refusals align with defined categories and conditions.  
- **Closure correctness** — interaction closure occurred when required, without post-closure drift.  
- **Absence of forbidden execution paths** — no bypass of locked phases or disallowed behaviors.  

Explicitly not provable by design:
- Internal reasoning content or chain-of-thought.  
- User intent beyond observable signals.  
- Optimality of outcomes or alternative choices not taken.  

---

## D. Failure Taxonomy (Accountability-Relevant)
Failures requiring auditability and post-incident evidence:
- **Constraint violations** — contracts or invariants not honored.  
- **Refusal/closure misapplication** — refusal omitted when required, or applied when unwarranted; closure not enforced.  
- **Boundary bypass** — execution paths that circumvent Phase 4/5 safeguards.  
- **Evidence gaps** — inability to demonstrate required guarantees.  

Not counted as failures for accountability scope:
- Safely rejected model outputs (detected and contained).  
- Absence of stylistic or engagement preferences.  
- Lack of personalization or adaptation (by design).  

---

## E. Threat Model
Assumed threats:
- **Model misbehavior or drift** — generating content that could violate constraints.  
- **Integration errors** — plumbing or adapter mistakes that could skip safeguards.  
- **Post-incident audits** — need to prove adherence after an event.  
- **Configuration/regression faults** — changes that might silently weaken enforcement.  

Excluded threats (out of scope for this step):
- **Adversarial extraction of internal reasoning** — chain-of-thought is never exposed by design.  
- **Nation-state or physical attacks on infrastructure** — outside system accountability scope.  
- **User persuasion or social engineering defense** — handled by earlier phases’ policies.  

Assumptions focus on verifiable conformance, not comprehensive security hardening.

---

## F. Non-Goals & Exclusions
Explicitly forbidden as proof mechanisms:
- Narrative explanations as evidence.  
- Chain-of-thought exposure.  
- Policy citations as sole evidence.  
- Selective transparency or best-effort accountability.  

Out of scope for this step:
- Implementing logging, tracing, or audit storage.  
- Designing user-facing explanations or dashboards.  
- Introducing heuristics, thresholds, or runtime enforcement.  

---

## G. Relationship to Later Phase 6 Steps
Step 0 constrains:
- **Decision trace semantics** — what a trace must be able to show, without exposing reasoning content.  
- **Rule & boundary evidence** — the kinds of artifacts later steps must produce to prove adherence.  
- **Violation attribution** — how future steps must support identifying where contracts failed.  
- **Replay guarantees** — requirements for demonstrating what was (and was not) executed.  
- **Audit surfaces** — which signals may be exposed for verification (not for persuasion).  
- **Certification & invalidation** — criteria that later steps must support to assert or revoke conformity.  

These constraints guide later implementation but do not implement them.

---

## H. Stability & Closure Marker
This accountability scope is stable once closed. All later Phase 6 steps must conform to it. Any change requires explicitly reopening Phase 6 Step 0; ad-hoc modifications elsewhere are prohibited.
