# Phase 9 — Step 0: Decision State Schema (Definition & Lock)

## Scope
- Defines the immutable DecisionState schema for Phase 9 cognition.
- No decision logic, no classification, no inference, no text generation.
- Binds DecisionState to Phase 7 traces and accountability; does not modify Phases 1–8.

## What DecisionState IS
- A structured, bounded, auditable record of decision context for Phase 9.
- Composed only of enums, tuples of structured records, deterministic identifiers, and explicit unknown markers.
- Immutable once constructed; no free-form text fields beyond identifiers.

## What DecisionState IS NOT
- Not a reasoning trace, not a prompt, not a hypothesis set.
- Not a risk/proximity/intent classifier or inference engine.
- Not a UI, API, or model integration surface.
- Not a place for explanations, narratives, probabilities, or heuristics.

## Identity & Binding
- `decision_id`: deterministic, non-empty identifier for the decision.
- `trace_id`: bound to an existing Phase 7 DecisionTrace; exactly one trace_id per DecisionState.
- `phase_marker`: must equal `PHASE_9`.
- `schema_version`: fixed `9.0.0`; mismatches are invalid.

## Structural Placeholders (No Logic)
- `proximity_state`: enum (VERY_LOW, LOW, MEDIUM, HIGH, IMMINENT, UNKNOWN).
- `proximity_uncertainty`: boolean flag.
- `risk_domains`: tuple of {domain enum, confidence enum}; domains unique. Domains (bounded): FINANCIAL, LEGAL_REGULATORY, MEDICAL_BIOLOGICAL, PHYSICAL_SAFETY, PSYCHOLOGICAL_EMOTIONAL, ETHICAL_MORAL, REPUTATIONAL_SOCIAL, OPERATIONAL_SYSTEMIC, IRREVERSIBLE_PERSONAL_HARM, LEGAL_ADJACENT_GRAY_ZONE, UNKNOWN.
- `risk_domain` confidence: LOW, MEDIUM, HIGH, UNKNOWN (later steps may forbid UNKNOWN confidence on assessments).
- `reversibility_class`: enum.
- `consequence_horizon`: enum.
- `responsibility_scope`: enum.
- `outcome_classes`: tuple of outcome enums.
- `explicit_unknown_zone`: tuple of UnknownSource enums capturing every unknown/uncertain field.

## Explicit Unknown Handling
- Unknowns are explicit; UNKNOWN ≠ false and ≠ omitted.
- Sources of unknown/uncertainty must be enumerated in `explicit_unknown_zone` (e.g., proximity, risk domain, confidence, reversibility, horizon, responsibility scope, outcome classes).
- Absence of information or uncertainty requires marking UNKNOWN and listing its source.

## Invariants (Mandatory)
- All categorical fields are bounded enums; no free-form text except deterministic IDs.
- Exactly one `trace_id` per DecisionState; must not be empty.
- `phase_marker` must be `PHASE_9`; `schema_version` must be `9.0.0`.
- Risk domains must be unique; each risk assessment uses bounded domain and confidence enums.
- Explicit unknown coverage: `explicit_unknown_zone` must include all unknown/uncertain sources present in fields.
- No contradictions allowed; invalid or incomplete states fail closed.

## Failure Semantics
- If a valid DecisionState cannot be constructed, execution must abort fail-closed, emit required attribution per Phase 7, and produce no partial state.
- Unknowns must be explicit; collapsing unknowns into guesses is forbidden.

## Guarantees
- Deterministic structure; no heuristics, probabilities, or adaptive behavior.
- Immutable after construction; auditable via bounded enums and explicit unknown tracking.
- Ready for later Phase 9 steps to consume without reinterpreting Phase 1–8 semantics.

## Non-Guarantees
- No guarantee of correctness, completeness, or risk estimation quality.
- No guarantee of intent/proximity/risk inference—only placeholders.
- No performance, UX, or operational guarantees.

## Closure Marker
- Phase 9 — Step 0 Decision State Schema is DEFINED and LOCKED.
- Any change to fields, enums, invariants, or failure semantics requires reopening Phase 9.
