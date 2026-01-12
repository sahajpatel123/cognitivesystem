# Phase 9 — Step 3: Irreversibility & Consequence Horizon (Deterministic, Bounded)

## Scope
- Classifies only `reversibility_class` and `consequence_horizon` within `DecisionState`.
- No prediction, severity estimation, advice, refusals, or orchestration.
- Uses only current user message, existing DecisionState fields (proximity, risk domains, unknowns), and optional Phase 4 intent framing.

## What This Step IS
- Pure state enrichment: categorical, deterministic, immutable, fail-closed.
- Produces bounded enums and explicit unknown markers.

## What This Step IS NOT
- Not outcome prediction, probability, severity, or desirability.
- Not rigor/friction escalation, refusal, or questioning.
- Not model use, heuristics, weights, scores, personalization, or memory.

## Enums (Bounded)
- `ReversibilityClass`: EASILY_REVERSIBLE, COSTLY_REVERSIBLE, IRREVERSIBLE, UNKNOWN.
- `ConsequenceHorizon`: SHORT_HORIZON, MEDIUM_HORIZON, LONG_HORIZON, UNKNOWN.

## Allowed Inputs
- Current user message (single turn).
- DecisionState fields: proximity_state, proximity_uncertainty, risk_domains, explicit_unknown_zone.
- Optional Phase 4 intent framing (if already present).

## Forbidden Inputs
- Prior turns, user identity, profiles, external data, model outputs, or future-step outputs.

## Classification Rules
- Reversibility: prefer UNKNOWN over optimistic guess; IRREVERSIBLE only when clearly indicated.
- Horizon: describes propagation duration, not likelihood; prefer UNKNOWN when ambiguous.
- Bias conservative: ambiguity → UNKNOWN with explicit unknown markers.

## Uncertainty Handling
- UNKNOWN must be explicitly captured in `explicit_unknown_zone` (REVERISBILITY or HORIZON sources).
- IMMINENT/LONG selections require unknown markers to avoid overconfidence.

## Invariants (Mandatory)
- Exactly one reversibility_class and one consequence_horizon set.
- UNKNOWN is valid and preferred over guessing.
- IRREVERSIBLE → `UnknownSource.REVERSIBILITY` must be present.
- LONG_HORIZON → `UnknownSource.HORIZON` must be present.
- DecisionState must remain schema-valid; violations abort fail-closed.

## Failure Semantics
- If safe classification is impossible: set UNKNOWN with explicit unknown markers; abort on invariant violations.

## Guarantees
- Deterministic, bounded, auditable classifications; no behavior or downstream logic changes.
- No probabilities, no severity, no advice.

## Non-Goals
- No mitigation, escalation, UI, or control logic.
- No logging/monitoring/persistence changes.
- No performance or infra considerations.

## Closure Marker
- Phase 9 — Step 3 irreversibility & horizon classification is DEFINED and LOCKED. Changes require reopening Phase 9.
