# Phase 9 — Step 7: Unknown-Zone Consolidation (Deterministic, Bounded)

## Scope
- Consolidates `explicit_unknown_zone` in `DecisionState`.
- Enforces bounded unknown taxonomy for outputs of Steps 1–6.
- No other fields are modified; no new behavior is added.
- Step 7 is self-contained: it only reads already-computed fields and writes only `explicit_unknown_zone`.

## Purpose
- Ensure unknowns are explicit, deduplicated, and aligned with field states.
- Prevent silent omission of uncertainty.
- Provide a stable, auditable unknown representation for later phases.

## Inputs
- Current `DecisionState` after Steps 1–6 (proximity, risk domains, reversibility, horizon, responsibility, outcomes).
- No user text, no external data, no history.

## Forbidden
- No cognition, prediction, probability, advice, or orchestration.
- No UI, persistence, logging-as-state, or behavior changes.

## Taxonomy Enforcement
- Unknown sources are bounded: PROXIMITY, RISK_DOMAINS, REVERSIBILITY, HORIZON, RESPONSIBILITY_SCOPE, OUTCOME_CLASSES, CONFIDENCE.
- Required markers are added when corresponding fields are UNKNOWN/uncertain (e.g., proximity uncertainty, unknown risk domain, unknown outcome class).
- SYSTEMIC_PUBLIC with SHORT_HORIZON requires HORIZON unknown marker.
- IRREVERSIBLE or LONG_HORIZON require relevant unknown markers.

## Invariants
- `risk_domains` and `outcome_classes` must be non-empty and bounded.
- `explicit_unknown_zone` entries must all be `UnknownSource` enums.
- Required unknown markers must be present for all unknown/uncertain fields.
- Deduplication and deterministic ordering of unknown markers.
- Violations → fail-closed (abort) with attribution.

## Failure Semantics
- Any invalid or missing required unknown markers causes failure and abort; no partial state.

## Non-Goals
- No refactoring of Step 1–6 semantics.
- No scoring, heuristics, probabilities, or adaptation.
- No behavior or rigor changes.
- No edits to Step 1–6 engines; isolation is mandatory.

## Closure Marker
- Phase 9 — Step 7 (Unknown-Zone Consolidation) is DEFINED and LOCKED. Changes require reopening Phase 9.
