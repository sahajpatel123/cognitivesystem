# Contract Conformance (STEP D)

This document describes STEP D: Contract Conformance & Failure Testing for the
Minimal Correct Implementation (MCI).

## 1. Purpose

STEP D verifies that the existing implementation enforces the Cognitive
Contract by failing when violations occur. It does not change cognition or
add features.

Passing STEP D does not mean the system is useful.
It means the system is correct with respect to the contract.

## 2. What Is Tested

The following categories are tested:

- **Request boundary invariants**
  - session_id presence.
  - text presence.
- **Reasoning invariants**
  - Single reasoning pass returns non-empty internal output.
  - An ExpressionPlan is produced.
- **Memory invariants**
  - Session-only scoping of hypotheses.
  - TTL expiry resets hypotheses.
  - Non-deleting updates.
  - Clamped per-turn updates.
- **Expression invariants**
  - Expression receives only an ExpressionPlan.
  - Output is non-empty.
- **Stage isolation**
  - Only ExpressionPlan crosses from reasoning to expression.
  - Expression has no access to reasoning traces or hypotheses.

## 3. What Is Explicitly Not Tested

STEP D does not test:

- Answer quality or usefulness.
- Performance, latency, or cost.
- User experience or ergonomics.
- Any behavior beyond what is required by the Cognitive Contract.

## 4. Why Passing STEP D Matters

Passing STEP D provides evidence that:

- Contract violations trigger hard failures instead of silent behavior changes.
- Observability records invariant checks and failures for each request.
- Forbidden behaviors, such as cross-session memory or silent expression
  failures, cannot proceed undetected.

STEP D focuses on correctness and enforcement, not improvement.
