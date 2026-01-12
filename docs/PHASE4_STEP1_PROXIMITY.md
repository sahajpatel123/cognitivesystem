# Phase 4 — Step 1: Decision Proximity Detection

_Date: 2026-01-07_

## A. Proximity Concept Definition
Decision proximity quantifies how near a user is to executing a real-world action, independent of whether the action is safe or advisable. It differs from:
- **Intent** (Step 0) — intent clarifies what kind of conversation is happening; proximity clarifies how close that intent is to becoming reality.
- **Risk** — risk assesses harm; proximity only gauges imminence.
- **Urgency** — urgency reflects time pressure; proximity reflects readiness. A user may be urgent but undecided, or calm yet minutes away from action.
Proximity is probabilistic because textual cues can be ambiguous; the system must retain uncertainty and default toward lower proximity when signals conflict.

## B. Proximity States (Ordered, Internal)
1. **Very Low** — User is far from acting; requests are purely informational or general curiosity. Not a prediction of safety, merely distance from action.  
2. **Low** — User is exploring but has no stated constraints or plans. They may compare options abstractly but show no commitment language. Not a guarantee that a decision cannot occur.  
3. **Medium** — User shows early convergence signals (narrowing options, referencing personal context) yet retains reversibility. Does **not** imply impending execution; only indicates movement toward it.  
4. **High** — User references specific plans, deadlines, or validation needs. Action seems near but not yet confirmed. Does **not** authorize refusals; it signals that later steps may need scrutiny.  
5. **Imminent** — User states intent to act, requests confirmation, or describes steps already in progress. This does **not** evaluate safety; it only marks that execution seems moments away.  
These states drive no direct behavior; they are internal signals consumed by later Phase 4 steps.

## C. Conceptual Signal Classes
Step 1 may examine the current user turn for the following signal families (without assigning weights or rules):
- **Temporal language** — mentions of deadlines, “now”, “today”.
- **Commitment phrasing** — statements of intent (“I will”, “I’m going to”).
- **Option narrowing** — elimination of alternatives or explicit comparisons.
- **Validation-seeking** — requests for confirmation, double-checking plans.
- **Execution framing** — detailed steps, resource allocations, or consequence mentions.
These signals are descriptive only. No formulas or thresholds are defined here.

## D. Input Scope & Boundaries
Allowed inputs: the current user utterance, metadata derived from Step 0 (intent category), and immediate conversational context within the current exchange. 
Forbidden inputs: prior sessions, user identity, emotional state, long-term memory, external profiles, or any Phase 3 artifacts. Proximity detection operates statelessly within the current interaction snapshot.

## E. Output Contract
Step 1 outputs a tuple:
- `proximity_state` ∈ {very_low, low, medium, high, imminent}
- `uncertainty_flag` ∈ {certain, low_confidence}
The output is strictly internal. It is never surfaced to the user and triggers no action by itself. Later steps may consume it to determine whether deeper analysis is permitted.

## F. Failure & Uncertainty Handling
When cues conflict or are weak, Step 1:
- Defaults to the lower of the contending states.
- Sets `uncertainty_flag = low_confidence` to signal ambiguity.  
This avoids false urgency while still surfacing uncertainty to downstream components.

## G. Non-Goals of Step 1
Step 1 does **not**:
- Assess harm or legality.  
- Decide rigor, friction, or refusal behavior.  
- Score severity or outcome likelihood.  
- Ask clarifying questions or adapt the conversation.  
- Modify prompts, enforcement, or adapter logic.  
It merely produces an internal proximity signal, preserving ambiguity when necessary.

> **Phase 4 Step 1 is now defined.** Any future proximity detection implementation must conform to this document’s scope, outputs, and non-goals.
