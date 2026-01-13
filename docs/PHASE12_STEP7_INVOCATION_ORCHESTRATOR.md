# Phase 12 — Step 7: LLM Invocation Orchestrator (Final Integration Layer)

## Purpose
- Provide a single canonical entrypoint that wires Phases 9–12 to produce governed output.
- Enforce OutputPlan dominance; model is a renderer only, never authoritative.
- Ensure deterministic, fail-closed behavior with deterministic fallback if the model or verification fails.

## Trust Boundary
- Inputs: user_text (current message only).
- Constructs DecisionState (Phase 9), ControlPlan (Phase 10), OutputPlan (Phase 11), then calls the Phase 12 pipeline (prompt builder → runtime adapter → schema validation → verification → fallback).
- No retries, no provider selection, no prompt evolution. Model output is untrusted until verified.

## Canonical Execution Order
1) Deterministic ids: trace_id, decision_id (UUIDv5).
2) Assemble DecisionState (Phase 9).
3) Assemble ControlPlan (Phase 10).
4) Assemble OutputPlan (Phase 11).
5) Invoke Phase 12 pipeline: prompt builder (Step 2) → runtime adapter (Step 1) → schema (Step 4) → verification (Step 5) → fallback (Step 6).
6) Return final ModelInvocationResult (text or JSON) with fail_closed typed failures if anything breaks.

## Allowed / Forbidden Behaviors
- Allowed: deterministic assembly calls; single pipeline invocation; deterministic fallback use; no mutation of upstream phases.
- Forbidden: new decision logic, retries, loops, tool calls, prompt tweaks, model authority, memory/personalization, bypassing OutputPlan.

## Failure Mapping Rules
- Any assembly failure → CONTRACT_VIOLATION fail-closed result.
- Model/runtime/schema/verification failures are handled inside Phase 12 pipeline; fallback renders safe bounded output. If fallback fails, return CONTRACT_VIOLATION fail-closed.

## Non-Goals
- No UX, no streaming, no provider orchestration, no caching, no heuristics or scoring, no adjacent features.

## Stability Marker
- Step 7 semantics are locked. Any change to ordering, action dominance, or fallback integration requires reopening Phase 12 and recertification.
