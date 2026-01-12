# Phase 10 — Step 6: Decision Closure Detection

## Purpose
Deterministically set `closure_state` to end interactions when the user explicitly ends, finalizes a decision, or refuses to engage. Prevents continued elaboration, repeated clarifications, or agent-like escalation. No text generation or orchestration occurs here.

## Allowed Inputs
- `DecisionState`: `proximity_state`, `risk_domains` (+ confidence), `reversibility_class`, `consequence_horizon`, `responsibility_scope`, `outcome_classes`, `explicit_unknown_zone`.
- Phase 10 context: `rigor_level`, `friction_posture`, `clarification_required`, `question_budget`, `initiative_budget`, `warning_budget`, `question_class`.
- Current user text: only for bounded marker detection (deterministic string checks).

Forbidden: history, profiles, external data/tools, model outputs, heuristics, weights, probabilities, free-form interpretation beyond bounded markers.

## ClosureState Taxonomy (bounded)
- `OPEN`
- `CLOSING`
- `CLOSED`
- `USER_TERMINATED`

## Marker Sets (bounded)
- Strong termination: “i decided”, “i’ve decided”, “i will do it”, “i’m going ahead”, “done”, “stop”, “no more”, “end”, “i’m leaving”, “don’t ask”, “close this”.
- Refusal-to-engage: “i won’t answer”, “doesn’t matter”, “just answer”, variants like “i will not answer”.
- Weak markers (polite acknowledgments): “ok”, “okay”, “cool”, “thanks”, “thank you”, “got it”.

## Deterministic Rule Ladder (first match wins)
1) Strong termination markers → `USER_TERMINATED`.
2) Refusal markers:
   - If high stakes (critical domain, IRREVERSIBLE, third-party/systemic responsibility, or friction ≥ HARD_PAUSE) → `USER_TERMINATED`.
   - Else → `CLOSED`.
3) Strong decision-finalization markers → `CLOSED`.
4) Weak markers:
   - If low stakes (low proximity, reversible, no critical domain, self-only responsibility) AND no pending clarification → `CLOSING`.
   - Else remain `OPEN`.
5) Default → `OPEN`.

Critical domains: `LEGAL_REGULATORY`, `MEDICAL_BIOLOGICAL`, `PHYSICAL_SAFETY`.  
Significant unknowns: presence of `explicit_unknown_zone` markers (not used for text parsing but informs stakes).

## Interaction with Clarification/Initiative
- If `closure_state` is `CLOSED` or `USER_TERMINATED`, downstream steps must not ask further questions; any `question_budget` should be treated as canceled.
- Closure overrides additional clarifications or warnings in later steps.

## Invariants
- `closure_state` is bounded enum; no free text.
- No multi-turn assumptions; single-call decision only.
- No scoring, weights, or probabilities.
- Inputs must respect prior step invariants (e.g., `question_budget` ∈ {0,1}; if `clarification_required` then `question_budget=1`).

## Fail-Closed Behavior
- Invalid inputs → `ClosureDetectionError`.
- If no marker matches, returns a bounded `OPEN` state (not silent failure).

## Non-Goals
- No refusal logic, kill-switch, or orchestration assembly.
- No answer generation, warnings, or UI behavior.
- No model calls or personalization.

## Closure Marker
- Step 6 decision closure is defined and locked. Any semantic change requires reopening Phase 10 and re-certification.
