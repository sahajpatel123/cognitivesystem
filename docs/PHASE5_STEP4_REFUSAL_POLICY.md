# Phase 5 — Step 4: Refusal & Boundary Explanation Policy

_Date: 2026-01-07_

---

## A. Purpose & Trust Role
Refusal is a trust-critical moment where the system must stop rather than risk unsafe or misleading output. Evasive or soft refusals erode trust by inviting debate or implying negotiability. Refusal must be explicit, final, and owned by the system; stopping is safer than proceeding under uncertainty when stakes or boundaries demand it.

---

## B. Definition of Refusal
A refusal is the system’s terminal decision not to proceed on the current path because doing so would breach safety, epistemic, or capability boundaries. It differs from uncertainty (which may allow clarification), from clarification (which seeks minimal disambiguation), and from deferral (which postpones action). Refusal ends the current path and enforces a boundary. Refusal is not advice, not negotiation, not a partial answer, and not a redirection.

---

## C. Conditions That Require Refusal (Qualitative)
Refusal is mandatory when qualitative conditions indicate that proceeding would violate system guarantees:
- **Risk-dominant**: outcome domains or proximity imply unacceptable harm potential that cannot be mitigated by expression posture or disclosure.  
- **Irreversibility under uncertainty**: actions with low reversibility/long horizons combined with unresolved ambiguity.  
- **Epistemic insufficiency in high-stakes contexts**: the system lacks grounded knowledge and cannot safely infer, even after allowed clarification.  
- **Capability-bound or scope-bound**: request is outside authorized scope or requires capacities the system does not provide.  
- **Violation of system guarantees**: proceeding would contradict locked Phase 1–4 commitments or established invariants.  

No heuristics, thresholds, or probabilities are defined; these are policy gates only.

---

## D. Refusal Categories (Bounded, Ordered)
1. **Capability-Bound Refusal**  
   - Why: required capability is unavailable or out of scope.  
   - Boundary enforced: system scope limits.  
   - Allowed explanation (in principle): cannot perform the requested class of action.
2. **Epistemic-Bound Refusal**  
   - Why: insufficient grounded knowledge; inference would be unsafe.  
   - Boundary enforced: epistemic adequacy and certainty requirements.  
   - Allowed explanation (in principle): lacks the reliable basis to proceed.
3. **Risk-Dominant Refusal**  
   - Why: outcome domains and proximity imply unacceptable risk that cannot be reduced by posture/disclosure.  
   - Boundary enforced: harm-prevention obligations.  
   - Allowed explanation (in principle): proceeding would breach safety boundaries.
4. **Irreversibility-Bound Refusal**  
   - Why: low reversibility/long horizon with unresolved ambiguity makes safe expression impossible.  
   - Boundary enforced: prevention of irreversible or cascading consequences.  
   - Allowed explanation (in principle): cannot proceed without risking irreversible impact.

Categories are finite and ordered by scope: capability → epistemic → risk → irreversibility.

---

## E. Boundary Explanation Principles
- System-owned: explanations state the system cannot proceed; responsibility is not shifted to the user.  
- Non-judgmental and non-defensive: no blame, no moral language, no self-justification narratives.  
- Final and non-negotiable: refusals do not invite reconsideration or debate.  
- Non-policy-referencing: no citations of external policies, rules, or authorities.  
- Concise and bounded: avoid justification overload; only the boundary is explained.  

---

## F. Prohibited Refusal Patterns
- Policy-shielding refusals that cite external rules or authorities.  
- Refusals that embed alternatives, redirections, or suggestions.  
- Refusals followed by questions or negotiation prompts.  
- Refusals framed as user failure or blame.  
- Refusals that invite debate, hedging, or partial compliance.  

---

## G. Failure Modes Prevented
- Soft refusals that users can push past.  
- Leakage of safety language that implies negotiability.  
- Negotiation loops or debate invitations.  
- Erosion of system authority through evasive or apologetic framing.  
- User confusion about whether the boundary is final.  

---

## H. Non-Goals (Mandatory)
- Does not provide wording, phrasing, tone, or empathy design.  
- Does not reference safety policies or external guidelines.  
- Does not suggest alternatives or design follow-up.  
- Does not close the interaction (handled elsewhere).  
- Does not modify earlier Phase 5 outputs or override Phase 4 cognition.  
- Does not introduce heuristics, thresholds, scoring, or runtime logic.  

---

## I. Stability & Closure Marker
Refusal policy definitions are stable once closed. All later Phase 5 steps must conform to this policy. Any change requires explicitly re-opening Phase 5 Step 4; ad-hoc modifications elsewhere are prohibited.
