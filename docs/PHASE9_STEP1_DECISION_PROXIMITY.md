# Phase 9 — Step 1: Decision-Proximity Engine (Deterministic, Bounded)

## Scope
- Classifies only proximity_state and proximity_uncertainty within DecisionState.
- No intent inference, no risk/harm/ethics assessment, no advice, no text generation.
- Uses only current user message and optional Phase 4 Step 0 intent framing.
- No models, probabilities, scores, or heuristics; strictly deterministic.

## What Proximity IS
- A categorical measure of distance-to-action: VERY_LOW, LOW, MEDIUM, HIGH, IMMINENT, UNKNOWN.
- Explicit uncertainty flag indicating ambiguity or insufficient evidence.
- Bounded, auditable output attached to DecisionState.

## What Proximity IS NOT
- Not intent, sentiment, motivation, or risk classification.
- Not rigor escalation, refusal logic, clarification, or advice.
- Not informed by user history, profiles, or external context.

## Allowed Inputs (Bounded)
- Current user message (single turn).
- Optional Phase 4 Step 0 intent framing text (bounded).
- Structural linguistic markers only (e.g., temporal language, commitment verbs, narrowing language, validation-seeking, execution framing).

## Forbidden Inputs/Methods
- Long-term memory, profiles, personalization.
- Sentiment/emotion analysis, model outputs, external tools or context.
- Keyword scoring, probabilities, learned models, adaptive logic.

## Proximity States (Ordered)
- VERY_LOW < LOW < MEDIUM < HIGH < IMMINENT; UNKNOWN for explicit unknown.

## Uncertainty Handling
- proximity_uncertainty MUST be set explicitly.
- Ambiguous/mixed/insufficient signals → set uncertainty true.
- If uncertain, choose the lowest defensible state; never default to IMMINENT.

## Invariants (Enforced)
- Exactly one proximity_state set; proximity_uncertainty explicitly set.
- IMMINENT requires non-empty explicit_unknown_zone.
- No regression of proximity within a single turn.
- Any invariant violation → abort/fail-closed with attribution per Phase 7.

## Failure Semantics
- If safe classification is impossible: choose lowest defensible state, set uncertainty true.
- Unknowns are explicit; never collapse unknown into guessed certainty.

## Guarantees
- Deterministic, bounded, auditable outputs; no behavior change elsewhere.
- Cognition remains model-free; outputs are categorical only.

## Non-Guarantees
- No correctness of user intent, risk, or outcome quality.
- No performance, UX, or operational guarantees.

## Closure Marker
- Phase 9 — Step 1 proximity engine is DEFINED and LOCKED; changes require reopening Phase 9.
