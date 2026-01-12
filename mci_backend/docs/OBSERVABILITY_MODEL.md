# MCI Observability Model

This document describes what is observed in the Minimal Correct Implementation
(MCI), why it is observed, and what is explicitly not observed.

## 1. Purpose

Observability exists only to check whether the Cognitive Contract held for a
request. It does not change system behavior, does not evaluate answer quality,
and is not visible to users.

## 2. What Is Logged

For each request, internally recorded data includes:

- **Request metadata**
  - `request_id` (generated internally).
  - `session_id` (from the request).
  - Timestamp.

- **Invariant results**
  - For each audited invariant:
    - `invariant_id`.
    - Description.
    - Pass/fail flag.
    - Failure reason if failed.

- **Stage boundary events**
  - For each stage (`request_boundary`, `reasoning`, `memory_update`, `expression`):
    - Stage entered/exited.
    - Success/failure.
    - Failure reason if applicable.

- **Hard failure reason**
  - When a hard error occurs, a short internal reason string is recorded.

## 3. What Is Explicitly Not Logged

The following data is not logged by the observability model:

- Full user message text.
- Internal reasoning traces.
- Full hypotheses content beyond what is necessary for core logic.
- Any data used for personalization or profiling.
- Any evaluation of correctness or usefulness of answers.

Observability stores only structural facts needed to check whether
invariants and stage boundaries behaved according to the Cognitive Contract.

## 4. Scope

- Observability is internal only.
- No observability data is returned to users.
- Observability does not alter responses or control flow.

This model is limited to correctness monitoring and auditing for MCI.
