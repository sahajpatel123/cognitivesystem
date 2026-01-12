# Phase 11 — Step 9: Abuse & Honesty Tests (Expression Governance Attack Suite)

## Purpose
Proves Phase 11 cannot leak dishonest or contract-violating outputs; enforces fail-closed behavior under adversarial combinations.

## What is tested
- Action dominance (closure > refusal > ask > answer)
- Fail-closed contradictions
- Unknown honesty
- Posture + refusal coupling
- Closure discipline
- Single-question guarantees

## What is NOT tested
- Output text quality
- User satisfaction or usefulness
- Rendering or templates
- Model calls or prompts

## Coverage Matrix (Categories A–F)
- A: Action dominance — tests: test_action_dominance_closure_wins, test_action_dominance_refusal_wins_over_answer, test_action_dominance_ask_path, test_action_dominance_answer_allowed
- B: Fail-closed contradictions — tests: test_fail_closed_stop_friction_blocks_answer, test_fail_closed_ask_with_zero_budget, test_fail_closed_refusal_without_category, test_fail_closed_closure_with_question_budget, test_fail_closed_missing_closure_rendering
- C: Honesty / unknown disclosure — tests: test_unknown_zone_forbids_unknown_disclosure_none, test_high_stakes_with_unknowns_escalates_confidence
- D: Posture safety — tests: test_refusal_requires_constrained_posture, test_stop_friction_enforces_strong_posture_and_disclosures
- E: Single-question invariants — tests: test_ask_one_has_single_question_spec, test_ask_one_forbids_enforced_rigor
- F: Closure discipline — tests: test_user_terminated_closure_silence, test_closed_forbids_summary

## Failure Taxonomy
- Structural contradiction (schema/invariant break)
- Honesty leak (unknowns hidden or minimal signaling in high-stakes unknowns)
- Dominance violation (closure/refusal/ask hierarchy broken)

## Stability Marker
These tests are part of Phase 11 governance certification. Weakening or removing requires reopening Phase 11.
