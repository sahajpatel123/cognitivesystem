# Phase 4 — Step 2: Risk & Outcome Classification

_Date: 2026-01-07_

## A. Risk & Outcome Concept Definition
In this system, “risk” refers to the **type of harm or consequence domain** that could arise if the user were to execute the action implied by their request. It is purely categorical: identifying *what kind* of fallout might exist. Risk here is **not** probability, severity, advice, or moral judgment. Step 2 only tags domains so later phases can reason about them; it never labels something as safe or unsafe.

## B. Outcome Domain Taxonomy
The following domains are exhaustive for this phase. Each inclusion statement defines the scope; exclusions prevent overreach. Flagging a domain simply notes relevance and carries no recommendation.

1. **Financial**  
   - *Includes*: money transfers, investments, debt operations, purchasing/selling assets, business transactions.  
   - *Excludes*: purely theoretical economics discussions with no personal stake.  

2. **Legal / Regulatory**  
   - *Includes*: compliance obligations, contracts, litigation risk, immigration status, intellectual property.  
   - *Excludes*: academic study of laws without personal application.  

3. **Medical / Biological**  
   - *Includes*: treatments, medications, diagnostics, physiological interventions, biohacking.  
   - *Excludes*: historical medical analyses or fictional scenarios.  

4. **Operational / Physical Safety**  
   - *Includes*: manufacturing, engineering processes, hazardous equipment, transportation safety, infrastructure.  
   - *Excludes*: purely digital workflows with no physical ramifications.

5. **Psychological / Emotional**  
   - *Includes*: mental well-being, stress impacts, therapy-related choices, interpersonal conflict decisions.  
   - *Excludes*: general mood descriptions without an impending action.  

6. **Ethical / Moral**  
   - *Includes*: dilemmas involving values, fairness, confidentiality breaches, manipulation.  
   - *Excludes*: philosophical debates with no personal action path.  

7. **Reputational / Social Standing**  
   - *Includes*: public statements, disclosures, brand risk, social trust.  
   - *Excludes*: anonymous curiosity with no linkage to identifiable parties.  

8. **Irreversible Personal Harm**  
   - *Includes*: self-harm, violent actions, actions causing permanent loss (life, bodily integrity).  
   - *Excludes*: reversible setbacks or hypothetical drama.  

9. **Legal-Adjacent Ethical Gray Zones** (Optional bridging domain)  
   - *Includes*: actions that may skirt regulations or rely on loopholes.  
   - *Excludes*: legitimately compliant behavior with clear authorization.  

These domains may overlap; Step 2 may flag multiple simultaneously when cues indicate combined consequences.

## C. Input Scope & Dependencies
Step 2 may observe: the current user message, Step 0’s intent category, and Step 1’s proximity signal. No additional history, user identity, reputational data, or external APIs may be consulted. The classification is stateless beyond these immediate signals.

## D. Output Contract
Step 2 emits an internal-only structure:
- `domains`: list of outcome domains deemed potentially applicable.  
- `domain_confidence`: optional per-domain tags such as `clear`, `ambiguous`, `unknown`.  
This output does **not** reach the user, does not alter behavior, and only feeds later Phase 4 steps (e.g., consequence horizon analysis).

## E. Uncertainty Handling Principles
- When evidence is weak, bias toward inclusion with an `ambiguous` tag rather than exclusion.  
- When signals conflict, list both domains with corresponding uncertainty.  
- When nothing indicates a domain, leave the list empty but set an overall `unknown` flag to avoid implying safety.

## F. Failure & Misclassification Risks
Step 2 is designed to prevent: 
1. **Omission** — failing to flag relevant domains (e.g., ignoring legal exposure).  
2. **Overgeneralization** — tagging everything as risky, which dilutes downstream rigor.  
3. **False safety** — assuming no risk because cues are subtle.  
4. **Topic bias** — treating well-known domains as automatically risky while overlooking niche harms.  
5. **Probability leakage** — silently converting domain tags into “safe/unsafe” judgments.

## G. Non-Goals of Step 2
Step 2 does **not**:
- Estimate likelihood or severity.  
- Judge morality or legality.  
- Provide advice, alternatives, or warnings.  
- Trigger refusals or friction.  
- Ask clarifying questions.  
- Modify prompts or enforcement logic.  
Its sole function is domain tagging with explicit uncertainty.

> **Phase 4 Step 2 is now defined.** Subsequent steps must treat this classification as stable and purely informational.
