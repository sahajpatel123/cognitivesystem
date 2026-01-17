-- Phase 15 Step 2: bounded persistence schema
-- Sessions: minimal identity with TTL boundary
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    user_id UUID NULL,
    anon_id TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_sessions_anon_id ON sessions (anon_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);

-- Quotas: per-subject daily counters
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'quota_subject') THEN
        CREATE TYPE quota_subject AS ENUM ('anon', 'user', 'ip');
    END IF;
END
$$;
CREATE TABLE IF NOT EXISTS quotas (
    id UUID PRIMARY KEY,
    subject_type quota_subject NOT NULL,
    subject_id TEXT NOT NULL,
    date DATE NOT NULL,
    requests_count INT NOT NULL DEFAULT 0,
    tokens_count INT NOT NULL DEFAULT 0,
    reset_at TIMESTAMPTZ NOT NULL,
    UNIQUE(subject_type, subject_id, date)
);

-- Rate limits: windowed hit tracking
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rate_subject') THEN
        CREATE TYPE rate_subject AS ENUM ('anon', 'user', 'ip');
    END IF;
END
$$;
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY,
    subject_type rate_subject NOT NULL,
    subject_id TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_seconds INT NOT NULL,
    hits INT NOT NULL DEFAULT 0,
    blocked_until TIMESTAMPTZ NULL,
    UNIQUE(subject_type, subject_id, window_start, window_seconds)
);

-- Invocation logs: minimal, non-content
CREATE TABLE IF NOT EXISTS invocation_logs (
    id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id UUID NULL,
    route TEXT NOT NULL,
    status_code INT NOT NULL,
    latency_ms INT NOT NULL,
    model_used TEXT NULL,
    error_code TEXT NULL,
    hashed_subject TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_invocation_logs_ts ON invocation_logs (ts);
CREATE INDEX IF NOT EXISTS idx_invocation_logs_session_id ON invocation_logs (session_id);

-- Retention (documentation-only notes):
-- sessions.expires_at: cleanup after TTL (e.g., 7 days)
-- invocation_logs: planned cleanup after 14 days
-- quotas: planned cleanup after reset_at (e.g., 90 days window)
-- rate_limits: cleanup when blocked_until elapsed / windows expire
