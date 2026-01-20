# Phase 15 — Step 9: Public Readiness (Legal / Policy / UX)

## Purpose & Guardrails
- Phases 1–14 locked: no cognition logic or governed runtime changes.
- Observability stays passive; no user_text or prompts logged.
- Responses preserve the /api/chat contract (action, rendered_text, failure_type, failure_reason).
- Data boundaries: anon cookie, sessions, quotas/rate limits, minimal invocation metadata (route, status_code, latency_ms, error_code, hashed_subject, session_id); no transcripts.

## What Was Added (Step 9)
- Public-facing legal pages: /terms, /privacy, /acceptable-use.
- Footer links to legal pages in the global layout.
- Chat disclaimer (not advice; verify independently; rate limits/quota may apply).
- Friendly error copy for common HTTP errors (415/429/5xx) in chat UI.
- Documentation lock file (this doc) for Step 9 drills and verification.
- No backend or cognition logic changes.

## Routes & UI
- Legal pages: `/terms`, `/privacy`, `/acceptable-use`.
- Footer links: visible on all pages (Terms, Privacy, Acceptable Use).
- Chat disclaimer: displayed in chat header.
- Error UX: chat shows friendly messages for 415 (content type), 429 (rate/quota), 5xx (service unavailable); no stack traces.

## Data & Hosting Alignment
- Frontend: Vercel.
- Backend: Railway (FastAPI).
- DB/Auth: Supabase Postgres; optional Supabase JWT verification; anon cookie for session consistency.
- Storage: sessions, quotas, rate_limits, minimal invocation logs (no prompts/user_text).
- WAF + plan guard enforce limits deterministically; circuit breakers stay active.

## Smoke Tests (must pass)
- Open `/terms`, `/privacy`, `/acceptable-use` (200, readable).
- Footer shows Terms/Privacy/Acceptable Use links.
- Chat page shows disclaimer.
- /api/chat happy path returns governed contract.
- 415 path: POST /api/chat with text/plain returns friendly message client-side.
- 429 path: burst to trigger rate limit returns friendly message client-side.
- 5xx path (simulated) shows friendly fallback client-side; no stack trace.

## Evidence Capture
- Paste sample curl responses (happy path, 415, 429).
- Paste one structured log line with request_id (no user_text).
- Confirm footer links are visible (screenshot or note).
- Confirm legal pages render with version date.

## Status
- Phase 15 Step 9 Status: COMPLETE ✅
