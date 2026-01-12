# Phase 5 — Step 3: Clarification Question Shaping

_Date: 2026-01-07_

---

## A. Purpose & Motivation
Asking a clarification question is a cognitive intervention that interrupts normal expression. Unnecessary questions increase user cost and can erode trust; silence is sometimes safer than speculative probing. Clarification must therefore be strictly justified, grounded in upstream posture, rigor disclosure, and confidence signaling, and used only when it reduces material uncertainty that affects safe expression.

---

## B. Definition of Clarification Question Shaping
Clarification question shaping defines when a single, bounded question is permitted and what it is intended to resolve. It exists to target specific uncertainties or assumptions that materially affect safe expression. It must not be used for engagement, preference mining, or deferring responsibility; it is a safety-aligned request for minimal disambiguation, not a dialogue strategy.

---

## C. Conditions for Asking a Question (Qualitative)
Questioning is permitted only when all of the following policy conditions hold:
- A critical assumption or ambiguity materially affects safe expression or outcome framing.  
- The system cannot safely infer the missing information from existing signals without risking distortion of rigor, posture, or confidence signaling constraints.  
- Asking is expected to reduce uncertainty more than remaining silent, with net benefit to safety/trust.  
- The need is directly tied to prior cognitive signals (posture, rigor disclosure, confidence signaling) and not to stylistic or engagement goals.  

No formulas or thresholds are defined; this is a qualitative gating policy.

---

## D. Single-Question Compression
- At most **one** clarification question is allowed per turn.  
- Multiple or cascading questions are forbidden.  
- The single question must target maximum information gain for the blocking ambiguity.  
- Partial answers are tolerated; the system must not chain additional questions in the same turn.  

This enforces minimal intrusion and avoids interrogative behavior.

---

## E. Allowed Question Classes (Bounded, Abstract)
1. **Missing Constraint Resolution**  
   - Purpose: obtain a critical parameter or boundary that determines safe expression scope.  
   - Resolves: absent constraints (e.g., required limits) that block safe expression.  
   - Must NOT: seek preferences, broaden scope, or collect extraneous context.
2. **Ambiguity Disambiguation**  
   - Purpose: resolve a specific ambiguity where multiple interpretations materially change safety.  
   - Resolves: divergent readings that alter applicable safeguards.  
   - Must NOT: solicit open-ended narratives or expand into engagement.
3. **Assumption Confirmation**  
   - Purpose: surface and confirm a single critical assumption the system would otherwise have to make.  
   - Resolves: latent assumptions that, if wrong, would misalign expression.  
   - Must NOT: offload responsibility or imply user fault; no multi-assumption bundling.

No wording examples or dialog trees are defined; categories are exhaustive for this step.

---

## F. Assumption Surfacing Without Punishment
- Assumptions are stated neutrally as dependencies, not as user errors.  
- User correction is enabled conceptually by presenting the dependency; no blame is implied.  
- Explicitly forbidden: accusatory framing, corrective tone, or language shifting responsibility to the user.  
- The goal is to expose a blocking dependency, not to score or evaluate the user.

---

## G. Failure Modes Prevented
- Question spam or interrogative behavior.  
- Analysis paralysis via repeated or cascading questions.  
- Using clarification to avoid refusal pathways or to persuade.  
- Over-questioning when silence would be safer.  
- Allowing critical ambiguities to persist because questioning was disallowed or undefined.

---

## H. Non-Goals (Mandatory)
- Does not decide wording or phrasing.  
- Does not design dialog flows or multi-turn strategies.  
- Does not optimize engagement or persuasion.  
- Does not ask multiple questions or resolve uncertainty by itself.  
- Does not modify earlier Phase 5 outputs or override Phase 4 cognition.  
- Does not introduce heuristics, thresholds, scoring, or runtime logic.

---

## I. Stability & Closure Marker
Clarification shaping rules are stable once closed. All later Phase 5 steps must conform to this policy. Any change requires explicitly re-opening Phase 5 Step 3; ad-hoc modifications elsewhere are prohibited.
