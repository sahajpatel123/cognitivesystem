-- Auth: users table for email+password authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- Update sessions table to support user sessions
-- (user_id column already exists from 001_init.sql)
-- Add index if not exists
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
