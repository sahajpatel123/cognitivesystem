# Phase 10 — Step 1: Rigor Selection Engine

## Purpose
Deterministically select `RigorLevel` for the ControlPlan from a given `DecisionState`, reflecting constraint density and epistemic strictness (not verbosity). No orchestration, text generation, or model calls occur here.

## What Rigor Means (and is not)
- **Is:** Categorical constraint/strictness posture for downstream control.
- **Is NOT:** Verbosity, politeness, tone, or friction placement; not answer content or templates; not probabilistic confidence.

## Allowed Inputs
- `DecisionState` fields only: `proximity_state`, `proximity_uncertainty`, `risk_domains` (with confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Optional Phase 4 framing if already provided by caller (no new framing logic added).

Forbidden: user history, external tools/data, model outputs, persisted memory, heuristics, weights, probabilities.

## Deterministic Mapping Principle
Rule ladder, monotonic escalation only; no weights or scoring.

## Rule Ladder (escalation bullets)
- **Baseline:** `MINIMAL` only if proximity is VERY_LOW/LOW, no critical domains, reversible, self scope, and unknowns minimal.
- **Proximity:** `MEDIUM` → at least `GUARDED`; `HIGH/IMMINENT` → at least `STRUCTURED`.
- **Unknowns with proximity ≥ MEDIUM:** bump to at least `GUARDED`; MINIMAL forbidden when unknowns exist at elevated proximity.
- **Critical domains:** LEGAL_REGULATORY / MEDICAL_BIOLOGICAL / PHYSICAL_SAFETY
  - With LOW confidence → at least `GUARDED`.
  - With MEDIUM/HIGH confidence → at least `STRUCTURED`.
- **Irreversibility:** `IRREVERSIBLE` → at least `STRUCTURED`.
- **Consequence horizon:** `LONG_HORIZON` → at least `GUARDED`.
- **Responsibility:** `THIRD_PARTY` → at least `GUARDED`; `SYSTEMIC_PUBLIC` → at least `STRUCTURED`.
- **ENFORCED reserved for:** `IMMINENT` plus (irreversible OR systemic_public OR critical domain at ≥ MEDIUM), OR high/imminent with significant unknowns and critical domain, OR imminent with significant unknowns.

## Key Invariants (MINIMAL forbidden when …)
- proximity in {HIGH, IMMINENT}
- irreversibility is IRREVERSIBLE
- responsibility_scope in {THIRD_PARTY, SYSTEMIC_PUBLIC}
- critical risk domains (legal, medical, physical safety) at MEDIUM/HIGH confidence
- unknowns present with proximity MEDIUM/HIGH/IMMINENT

## Fail-Closed Semantics
- Invalid or missing DecisionState → `RigorSelectionError`.
- No partial/approximate outputs; result is a single bounded `RigorLevel`.

## Non-Goals
- No friction logic (Step 2), clarification (Steps 3–4), closure (Step 6), refusal (Step 7), or answer generation.
- No model calls, scoring, weights, or probabilities.
- No modifications to Phase 9 artifacts or ControlPlan schema.

## Closure Marker
- Step 1 rigor selection is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
