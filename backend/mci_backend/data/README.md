# MCI Data Semantics

This file documents what data exists in the Minimal Correct Implementation (MCI)
and why it exists.

## 1. Stored Data

### 1.1 Session-local Hypotheses

- Stored by `session_id` only.
- Represent internal assumptions about the current session.
- Are TTL-bound: after a fixed duration, they are discarded.
- Are non-deleting: updates adjust or add hypotheses but do not remove them.
- Are clamped: each update limits the magnitude of change per turn.

Location:
- Implemented in `mci_backend/app/memory.py`.

## 2. Transient Data

### 2.1 Internal Reasoning Trace

- Exists only during handling of a single request.
- Produced by the reasoning stage.
- Used to construct the ExpressionPlan.
- Is not persisted.
- Is not returned in responses.

### 2.2 Expression Plan

- Created by the reasoning stage.
- Passed directly to the expression stage.
- Defines the only content expression may render.
- Exists only for the duration of request handling.

## 3. Data That Is Explicitly Not Stored

The following types of data are not stored in MCI:

- User identity beyond opaque `session_id`.
- Cross-session memory or history.
- Long-term profiles, traits, or preferences.
- Logs of internal reasoning traces.
- Any data used for personalization.

There are no future plans or roadmap items recorded in this file.
