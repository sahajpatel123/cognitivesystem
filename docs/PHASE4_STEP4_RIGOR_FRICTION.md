# Phase 4 — Step 4: Rigor & Friction Orchestration

_Date: 2026-01-07_

---

## A. Purpose & Scope
Rigor and friction are internal control signals that set how cautious the system must be once decision framing (Step 0), proximity (Step 1), outcome domains (Step 2), and reversibility/horizon (Step 3) are known. They are defined only after those signals exist so that strictness is grounded in decision relevance, risk domain coverage, and consequence structure. These signals are internal-only policy selectors; they do not render text, change tone, or directly alter model behavior.

---

## B. Core Concept Definitions
**Rigor**  
- Internal constraint density: how tightly reasoning steps must adhere to formal definitions and exclusions already established in Steps 0–3.  
- Precision requirement: the degree of exactness and disallowance of speculative leaps when consuming upstream signals.  
- Tolerance for ambiguity: how much uncertainty is permitted before escalation to tighter guardrails is mandatory.
- Rigor is **not** tone, verbosity, moral judgment, policy enforcement, or user-facing phrasing.

**Friction**  
- Deliberate structural resistance: intentional insertion of slowdown gates between cognition and downstream expression layers.  
- Intentional slowdown: paced progression that demands additional internal confirmations before proceeding.  
- Regret-minimization mechanism: internal brake designed to reduce impulsive progression when stakes or irreversibility increase.  
- Friction is **not** refusal, punishment, persuasion, or UX design; it does not script wording.

---

## C. Rigor Level Taxonomy (Ordered, Internal)
1. **Minimal Rigor**  
   - Posture: light constraint density; accepts higher ambiguity.  
   - Constraints: downstream steps may operate with broad allowances; speculative links are tolerated but still within Phase 4 definitions.  
   - Restrictions: none beyond baseline Phase 4 invariants.  
   - Content note: does not choose wording or advice.
2. **Moderate Rigor**  
   - Posture: balanced constraint density; ambiguity is documented and bounded.  
   - Constraints: downstream behaviors must align with clearly tagged uncertainties; loose speculation is disallowed.  
   - Restrictions: requires explicit acknowledgment of uncertainty before downstream use.  
   - Content note: does not choose wording or advice.
3. **High Rigor**  
   - Posture: tight constraint density; low tolerance for ambiguity.  
   - Constraints: downstream steps must avoid unverifiable assumptions; only clearly supported inferences proceed.  
   - Restrictions: forbids reliance on weak cues; mandates conservative defaults when signals conflict.  
   - Content note: does not choose wording or advice.
4. **Extreme Rigor**  
   - Posture: maximal constraint density; ambiguity forces halt or deferral to later safeguards.  
   - Constraints: downstream behaviors are confined to the most conservative interpretations; speculative bridges are barred.  
   - Restrictions: any unresolved uncertainty blocks progression until explicitly cleared by downstream governance.  
   - Content note: does not choose wording or advice.

---

## D. Friction Posture Taxonomy (Ordered, Internal)
1. **No Friction**  
   - Slowdown meaning: no added internal pacing beyond base sequencing.  
   - Relation to rigor: may pair with any rigor level; absence of friction does not imply low rigor.  
   - Note: friction ≠ refusal; this posture merely omits additional delay.
2. **Soft Friction**  
   - Slowdown meaning: inserts lightweight internal pauses or confirmations before advancing.  
   - Relation to rigor: can accompany moderate or high rigor; provides time to re-check ambiguity tags.  
   - Note: friction ≠ refusal; it does not block output, only tempers speed.
3. **Enforced Friction**  
   - Slowdown meaning: requires explicit internal checkpoints and conservative sequencing; progression is gated until checks are satisfied.  
   - Relation to rigor: often co-occurs with high or extreme rigor but remains conceptually separate.  
   - Note: friction ≠ refusal; it delays and audits but does not terminate.

---

## E. Synthesis Principles (No Formulas)
- Proximity (Step 1) informs how near the user is to acting; closer proximity can justify higher rigor and more friction, but no fixed thresholds are defined.  
- Outcome domains (Step 2) indicate harm categories; presence of sensitive domains supports elevating rigor or friction qualitatively.  
- Irreversibility and consequence horizon (Step 3) shape persistence and recoverability; longer horizons or lower reversibility bias toward stricter rigor and stronger friction postures.  
- These relationships are policy-level and qualitative. No scores, weights, or heuristics are introduced here.

---

## F. Separation Guarantees
- Rigor and friction are distinct: either can increase without the other.  
- Neither signal implies advice, refusal, or questioning.  
- Both are internal-only; they do not surface content, tone, or user-facing behavior.  
- Friction is not a proxy for refusal, and rigor is not a proxy for severity or morality.

---

## G. Failure Modes Prevented
- Uniform strictness across trivial and critical decisions.  
- Late-stage leniency when proximity is high or reversibility is low.  
- Early-stage overbearing friction that slows harmless exploration.  
- Arbitrary or inconsistent resistance unrelated to upstream signals.  
- Silent merging of rigor into refusal or friction into persuasion.

---

## H. Non-Goals (Mandatory)
- Step 4 does not choose wording, ask questions, or refuse requests.  
- It does not optimize outcomes, assess probability, or score severity.  
- It does not modify model behavior directly or touch Phase 3 artifacts.  
- It does not design UX, tone, or interaction flows.

---

## I. Stability & Closure Marker
The vocabulary and taxonomies in this document are stable. Later steps must conform to them without alteration. Any change requires formally re-opening Phase 4 Step 4; ad-hoc modifications elsewhere are prohibited.
