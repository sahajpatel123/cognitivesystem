# Phase 9 — Step 8: Decision State Assembly & Cross-Field Validation (Deterministic, Fail-Closed)

## Purpose
- Build one authoritative, immutable DecisionState by running Steps 1–5 and 7 in canonical order.
- Enforce cross-field invariants for coherence.
- Fail-closed on inconsistency; no partial state is emitted.

## Canonical Order (Mandatory)
1) Step 1: Proximity classification
2) Step 2: Risk domain classification
3) Step 3: Irreversibility + consequence horizon
4) Step 4: Responsibility scope
5) Step 5: Outcome-class awareness
6) Step 7: Unknown-zone consolidation
7) Step 8: Cross-field validation

No reordering, skipping, or conditional execution.

## Allowed Inputs
- Current user message (single turn).
- Optional Phase 4 intent framing (if available).
- Outputs of Steps 1–5 and 7.

## Forbidden Inputs
- History, profiles, personalization, external tools/data, model outputs.
- Any change to engine semantics or schema.

## Cross-Field Invariants (Step 8)
- `risk_domains` non-empty; bounded enums.
- `outcome_classes` non-empty; bounded enums.
- `explicit_unknown_zone` entries are bounded UnknownSource enums (taxonomy: PROXIMITY, RISK_DOMAINS, REVERSIBILITY, HORIZON, RESPONSIBILITY_SCOPE, OUTCOME_CLASSES, CONFIDENCE).
- IRREVERSIBLE → UnknownSource.REVERSIBILITY present.
- LONG_HORIZON → UnknownSource.HORIZON present.
- SYSTEMIC_PUBLIC + SHORT_HORIZON → UnknownSource.HORIZON present.
- UNKNOWN_OUTCOME_CLASS present → UnknownSource.OUTCOME_CLASSES present.
- Legal/regulatory risk present → LEGAL_REGULATORY_OUTCOME present OR UnknownSource.OUTCOME_CLASSES explains mismatch.
- Medical/biological risk present → MEDICAL_BIOLOGICAL_OUTCOME present OR UnknownSource.OUTCOME_CLASSES explains mismatch.
- DecisionState schema validation passes.

Any violation → fail-closed (typed assembly error).

## Failure Semantics
- Deterministic, fail-closed abort on invariant violation.
- No retries, fallbacks, or partial state.
- No user-facing output.

## Non-Goals
- No orchestration, rigor/friction, refusal, advice, or expression logic.
- No monitoring, persistence, or infra changes.
- No modification to Steps 1–7 semantics or schema.

## Closure Marker
- Phase 9 — Step 8 (Assembly & Cross-Field Validation) is DEFINED and LOCKED. Changes require reopening Phase 9.
