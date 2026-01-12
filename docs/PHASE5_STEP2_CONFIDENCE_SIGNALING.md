# Phase 5 — Step 2: Confidence & Uncertainty Signaling

_Date: 2026-01-07_

---

## A. Purpose & Motivation
Confidence must be governed explicitly so the system does not sound more certain than its epistemic basis allows. Fluent language under uncertainty is dangerous because it can mask gaps, inflate trust, and lead to premature action. Sounding confident is not equivalent to being correct; conversely, suppressing uncertainty can hide material risks. Uncertainty sometimes must be visible to preserve epistemic honesty and decision safety.

---

## B. Definition of Confidence Signaling
Confidence signaling is the policy that governs how the system conveys its certainty, inferences, and unknowns in outward expression. It controls:
- Assertiveness bounds (how strongly statements may be framed)
- Explicitness of limits, caveats, and uncertainty
- Clarity of boundaries between grounded facts, inferences, and unknowns

Confidence signaling does **not** govern tone, style, persuasion, verbosity, or engagement. It does not provide wording or templates; it sets the allowed signaling posture only.

---

## C. Epistemic Category Awareness
Step 2 assumes the following internal epistemic categories exist upstream:
- **Grounded knowledge** — supported by explicit evidence or definitions within scope.  
- **Inferred knowledge** — derived or extrapolated from available signals.  
- **Unknown / Ambiguous** — not supported or conflicting; epistemically open.  

Step 2 does not compute these categories; it governs how each category may be communicated under the chosen signaling level.

---

## D. Confidence Signaling Taxonomy (Ordered, Internal)
1. **Minimal Signaling**  
   - Assertions: presented plainly when grounded; avoid foregrounding inference mechanics.  
   - Uncertainty: surfaced only when material; non-critical unknowns remain implicit.  
   - Restrictions: no strong assertiveness on inferred content; no portrayal of inference as fact.  
   - Note: does not choose wording.
2. **Guarded Signaling**  
   - Assertions: grounded statements allowed; inferred statements must indicate conditionality.  
   - Uncertainty: surfaced for any element that affects safe interpretation.  
   - Restrictions: prohibits confident framing of inferred or ambiguous items; requires boundary clarity.  
   - Note: does not choose wording.
3. **Explicit Signaling**  
   - Assertions: grounded items may be stated; all inferred items must be clearly marked; unknowns are explicitly acknowledged when relevant.  
   - Uncertainty: proactively signaled; ambiguity is surfaced to prevent misinterpretation.  
   - Restrictions: forbids unmarked inference; disallows omission of relevant unknowns.  
   - Note: does not choose wording.

Ordering reflects increasing explicitness of constraints and uncertainty, not verbosity or tone.

---

## E. Alignment Principles (Qualitative Only)
- High confidence signaling requires high epistemic certainty; inference must not masquerade as fact.  
- High-risk contexts (from prior phases) demand conservative signaling; ambiguity should not be hidden.  
- Unknowns are first-class and must be visible when they change interpretation or risk.  
- Higher signaling levels emphasize boundary clarity, not response length.  
- Expression posture and rigor disclosure bound how signaling is expressed; signaling cannot override them.

---

## F. Failure Modes Prevented
- Users acting on inferred claims as if they were grounded facts.  
- Irreversible decisions made under false certainty.  
- Verbosity or fluency being misused as a proxy for confidence.  
- Excessive hedging that erodes trust without conveying actual epistemic state.  
- Inconsistent confidence signaling across similar situations.  
- Hiding ambiguity that materially affects decision risk.

---

## G. Non-Goals (Mandatory)
- Does not compute certainty or probabilities.  
- Does not expose internal reasoning traces.  
- Does not decide content, phrasing, tone, or ask questions.  
- Does not refuse requests or optimize persuasion/engagement.  
- Does not modify Phase 4 outputs or Phase 5 Steps 0–1.  
- Does not introduce thresholds, heuristics, scoring, or runtime logic.

---

## H. Stability & Closure Marker
Confidence signaling definitions are stable once closed. All later Phase 5 steps must conform to this policy. Any change requires explicitly re-opening Phase 5 Step 2; ad-hoc modifications elsewhere are prohibited.
