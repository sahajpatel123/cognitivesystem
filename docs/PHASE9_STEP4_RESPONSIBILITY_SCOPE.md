# Phase 9 — Step 4: Responsibility Scope Detection (Deterministic, Bounded)

## Scope
- Classifies only `responsibility_scope` in `DecisionState`.
- Optional: adds explicit unknown markers; no other fields are changed.
- Uses only current user message, existing DecisionState fields (proximity, risk domains, reversibility, horizon, unknowns), and optional Phase 4 intent framing.

## What Responsibility Scope IS
- A categorical geometry of who bears consequences: SELF_ONLY, SHARED, THIRD_PARTY, SYSTEMIC_PUBLIC, UNKNOWN.
- Deterministic, bounded, immutable, fail-closed, auditable.

## What It IS NOT
- Not blame, moral judgment, or legal responsibility.
- Not advice, warnings, refusal, or escalation.
- Not prediction, probability, severity, or desirability.
- Not informed by history, profiles, personalization, or external data.

## Allowed Inputs
- Current user message (single turn).
- DecisionState fields: proximity_state, risk_domains, reversibility_class, consequence_horizon, explicit_unknown_zone.
- Optional Phase 4 intent framing (if already available).

## Forbidden Inputs
- Earlier turns, user identity, profiles, external tools/data, sentiment/emotion, model outputs.
- No clarification or questioning.

## Taxonomy (Bounded)
- SELF_ONLY — consequences borne primarily by the user.
- SHARED — consequences shared with close group (family/team/shared resources).
- THIRD_PARTY — others impacted but not co-deciders; asymmetric responsibility (client, customer, employee, etc.).
- SYSTEMIC_PUBLIC — non-trivial public/systemic externalities.
- UNKNOWN — insufficient information; must be explicit.

Rules:
- Default must NOT be SELF_ONLY.
- Do not collapse SHARED vs THIRD_PARTY.
- SYSTEMIC_PUBLIC ≠ “high risk”; requires structural markers.

## Signals (Structural Only)
- Explicit references: family/parents/child/friend/partner/team/company/users/client/customer/employee.
- Decision-for-others patterns: allow/approve/deny/deciding for/they depend on me.
- Public/systemic markers: publish/broadcast/release/publicly/policy/vulnerability/exploit/mass/system-wide.
- Never infer from tone/emotion; no assumptions.

## Uncertainty Handling
- Ambiguity → responsibility_scope = UNKNOWN; add `UnknownSource.RESPONSIBILITY_SCOPE`.
- SYSTEMIC_PUBLIC with SHORT_HORIZON must add horizon unknown to acknowledge uncertainty.

## Invariants
- Exactly one responsibility_scope set.
- UNKNOWN → `UnknownSource.RESPONSIBILITY_SCOPE` present.
- SYSTEMIC_PUBLIC: risk_domains must be non-empty (enforced by DecisionState); if horizon is SHORT_HORIZON, `UnknownSource.HORIZON` must be present.
- No changes to proximity/risk/reversibility/horizon/outcomes.
- DecisionState must remain schema-valid; violations abort fail-closed with attribution.

## Failure Semantics
- If safe classification is impossible: set UNKNOWN with explicit unknown markers.
- Any invariant violation → fail-closed abort; no partial state.

## Non-Goals
- No orchestration, no rigor/friction/refusal, no advice or mitigation, no UI/API, no persistence or monitoring changes, no models or heuristics.

## Closure Marker
- Phase 9 — Step 4 responsibility scope detection is DEFINED and LOCKED. Changes require reopening Phase 9.
