# Phase 4 — Step 0: Decision Framing

_Date: 2026-01-07_

## A. Purpose of Decision Framing
Decision framing establishes a stable vocabulary for distinguishing between user interactions that are merely informational and those that qualify as decision-relevant. Without this scaffold, later risk-aware cognition would collapse into ad-hoc heuristics, leading to inconsistent handling of high-stakes prompts. The framing prevents two failure modes:
1. **False urgency** — escalating routine questions into heavy-handed interventions.  
2. **Silent drift** — neglecting situations where the user is approaching a pivotal commitment.  
By clarifying where “decisions” begin and end, the system can later layer risk analysis without redefining its scope each time.

## B. Intent State Taxonomy
The taxonomy below is exhaustive for Phase 4 baseline reasoning. Categories describe the user’s situational stance, not the system’s confidence. Detection is *not* part of Step 0; only semantics are defined.

| Category | Represents | Explicitly Not | Downstream Activation (conceptual permission) |
|---|---|---|---|
| **Informational** | User asks for facts, definitions, or explanations detached from immediate action (e.g., “What is TCP?”). | Requests for instructions, commitments, or decisions. | Risk modules remain idle; no escalation permitted. |
| **Exploratory** | User surveys options without narrowing toward action (e.g., “Different ways to learn Python”). | Anything implying selection, prioritization, or constraints. | Low-level sensemaking allowed, but risk analysis stays off. |
| **Advisory** | User asks for tailored guidance while still deferring the final choice (e.g., “Should I learn React or Vue?”). | Binding commitments or statements of imminence (“I must choose today”). | Future steps may gather context but must not enforce decisions. |
| **Decision-Adjacent** | Signals that a user is converging on a choice (deadlines, stakes, or comparisons) but has not explicitly committed (e.g., “I need to pick a bootcamp this week”). | Casual curiosity, historical review, or purely hypothetical musings. | Risk awareness may activate; rigor escalation is allowed conceptually; refusal remains out-of-scope unless the situation becomes unsafe. |
| **Decision-Imminent** | User declares intent to act imminently or requests confirmation for a specific action path (e.g., “I’m going to liquidate my savings—confirm this plan”). | Hypothetical narratives, academic case studies, or post-hoc analyses. | Full decision safeguards may engage: risk analysis permitted, contextual probing allowed (if future steps implement it), refusal conceptually possible. |

Notes:
- Categories are mutually exclusive per interaction snapshot.  
- The system does *not* infer psychological state; labels only reflect textual commitments.  
- Transitions between categories occur over time but Step 0 does not model transitions.

## C. Decision vs. Non-Decision Boundary
A user input is **decision-relevant** if it references an impending or irrevocable real-world action that the user can plausibly take, along with an implicit expectation that the system’s response could influence that action. Conditions include:
1. Stated timelines or deadlines (“today”, “before Friday”).  
2. Requests for confirmation or endorsement of an action plan.  
3. Explicit mention of stakes or consequences tied to an action (“risking savings”, “affects my job”).  

An input remains **non-decision** when it is:
- Purely educational or historical (“How did the 2008 crisis unfold?”).  
- Hypothetical without a bridge to real action (“If someone were to invest…”).  
- Safety-related curiosity absent personal intent (“What is the lethal dose of X?” without self-application).  

Edge cases:
- **Dangerous curiosity** (e.g., asking about harmful techniques) stays non-decision unless the user ties it to personal action. Later phases may still refuse, but Step 0 labels it outside the decision boundary.  
- **Academic case studies** are non-decision even if topics are high stakes; they become decision-relevant only when the user links them to personal action.  
- **Retrospective analysis** (“Why did my trade fail?”) is non-decision unless paired with imminent next steps.

## D. Behavioral Implications (Conceptual Only)
- **Informational / Exploratory**: No risk analysis or refusal pathways should activate; the system may respond normally.  
- **Advisory**: Later steps *may* contextualize but must not treat the request as binding; escalation is optional and bounded.  
- **Decision-Adjacent**: Risk-aware cognition is permitted; probing or cautionary framing becomes conceptually valid.  
- **Decision-Imminent**: Full protective measures (analysis, escalation, possible refusal) become permissible, provided future steps implement them.  

These implications define *permissions*, not obligations, and they do not prescribe algorithms.

## E. Non-Goals of Step 0
- No scoring, weighting, or probability estimation.  
- No urgency detection or countdown timers.  
- No automatic question-asking or friction insertion.  
- No classification of illegal vs. legal content.  
- No refusal logic or risk thresholds.  
- No personalization or adaptive memory.  
- No references to specific models or inference endpoints.  
Step 0 solely names categories and boundaries.

## F. Stability & Reuse Guarantee
The definitions above are stable across domains, users, and contexts. All later Phase 4 steps must consume these categories without redefining them. If future discoveries require different categories, Phase 4 must be formally re-opened and Step 0 re-certified; ad-hoc tweaks elsewhere are prohibited.

> **Phase 4 Step 0 is now complete.** Any attempt to detect or operationalize decisions must rely exactly on the taxonomy and boundaries defined here.
