-- Phase 15 Step 1 minimal operational schema (no memory/personalization)
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    plan_tier TEXT NULL CHECK (plan_tier IN ('FREE','STANDARD','MAX')),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS requests (
    id UUID PRIMARY KEY,
    session_id UUID NULL REFERENCES sessions(session_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action TEXT NOT NULL CHECK (action IN ('ANSWER','ASK_ONE','REFUSE','CLOSE','FALLBACK')),
    failure_type TEXT NULL,
    latency_ms INTEGER NULL,
    metadata JSONB NULL
);

-- Forbidden: raw prompts, model output, governed internals, traces, personalization artifacts.
