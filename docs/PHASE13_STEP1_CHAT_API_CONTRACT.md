# Phase 13 — Step 1: Chat API Contract (UI ↔ Backend)

## 1) Purpose & Trust Boundary
- Establish a strict, stable contract so UI remains an untrusted, rendering-only surface while the governed core stays authoritative.
- Prevent authority inversion: UI must not influence ControlPlan/OutputPlan or cognition; backend validates and enforces all constraints.
- Bound all inputs/outputs to avoid leakage of internal artifacts, traces, or prompts; fail-closed on violations.

## 2) Endpoint
- `POST /api/chat`
- Single governed surface for chat (Product → Chat, `/product/chat`).

## 3) Request Schema (fail-closed)
- JSON body: `{ "user_text": string }`
- `user_text`: required, non-empty, min length 1, max length 2000 chars.
- Extra/unknown fields: **forbidden** (fail-closed).
- Payload size: if Content-Length exceeds 16KB, reject with 413.
- No message history, no identity fields, no mode/flag overrides.

## 4) Response Schema (bounded, sanitized)
- `action`: enum [`ANSWER`, `ASK_ONE_QUESTION`, `REFUSE`, `CLOSE`, `FALLBACK`]
- `rendered_text`: required string (may be empty only on hard failure fallback).
- `failure_type` (optional enum):
  - `REQUEST_SCHEMA_INVALID`
  - `REQUEST_TOO_LARGE`
  - `EMPTY_INPUT`
  - `MODEL_FAILED_FALLBACK_USED`
  - `GOVERNED_PIPELINE_ABORTED`
  - `INTERNAL_ERROR_SANITIZED`
- `failure_reason` (optional short string, max 200 chars, sanitized; no internals).
- Forbidden in response: DecisionState, ControlPlan, OutputPlan, trace IDs, audit/evidence, prompts, raw model output, schema versions.

## 5) Status Code Policy
- `200`: governed response returned (including governed fallback).
- `4xx`: client/request faults (schema invalid, too large, empty input, unknown fields).
- `5xx`: only for unexpected backend crash; still sanitize via bounded failure response where possible.

## 6) Forbidden Behaviors
- No history arrays, no personalization, no identity, no analytics, no streaming, no subscriptions, no prompt exposure, no “agent mode.”
- UI cannot bypass throttling/governance or request alternate modes.

## 7) Stability Marker & Invalidation Triggers
- This contract is locked for Phase 13 Step 1.
- Any schema or enum change requires reopening/re-certifying Phase 13 Step 1 before code updates.

## 8) Non-Goals
- No UI design/polish, no new features, no model tuning, no storage, no telemetry expansion.
