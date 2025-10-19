-- Migration 001: Create sessions table
-- Description: Core table for storing prompt sessions
-- Author: lift-sys team
-- Date: 2025-10-19

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User identification (for RLS)
    user_id UUID NOT NULL,

    -- Session metadata
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'finalized', 'error')),
    source TEXT NOT NULL DEFAULT 'prompt' CHECK (source IN ('prompt', 'code')),

    -- Content (JSONB for flexibility and indexing)
    original_input TEXT NOT NULL,
    current_ir JSONB,
    current_code TEXT,

    -- Denormalized counters (updated by triggers)
    revision_count INTEGER NOT NULL DEFAULT 0,
    draft_count INTEGER NOT NULL DEFAULT 0,
    hole_count INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalized_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT sessions_user_id_not_empty CHECK (user_id::text != ''),
    CONSTRAINT sessions_original_input_not_empty CHECK (LENGTH(original_input) > 0)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status);

-- Create index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_sessions_current_ir ON sessions USING GIN (current_ir);
CREATE INDEX IF NOT EXISTS idx_sessions_metadata ON sessions USING GIN (metadata);

-- Add comments for documentation
COMMENT ON TABLE sessions IS 'Stores prompt sessions with IR and code generation state';
COMMENT ON COLUMN sessions.id IS 'Unique session identifier';
COMMENT ON COLUMN sessions.user_id IS 'Owner of this session (for RLS isolation)';
COMMENT ON COLUMN sessions.status IS 'Current state: active, paused, finalized, or error';
COMMENT ON COLUMN sessions.source IS 'How session was created: prompt (forward mode) or code (reverse mode)';
COMMENT ON COLUMN sessions.original_input IS 'Original prompt text or code input';
COMMENT ON COLUMN sessions.current_ir IS 'Latest intermediate representation (JSON)';
COMMENT ON COLUMN sessions.current_code IS 'Latest generated code';
COMMENT ON COLUMN sessions.revision_count IS 'Number of IR revisions (denormalized)';
COMMENT ON COLUMN sessions.draft_count IS 'Number of code drafts (denormalized)';
COMMENT ON COLUMN sessions.hole_count IS 'Number of unresolved holes (denormalized)';
COMMENT ON COLUMN sessions.metadata IS 'Additional session metadata (performance metrics, tags, etc.)';
COMMENT ON COLUMN sessions.created_at IS 'Session creation timestamp';
COMMENT ON COLUMN sessions.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN sessions.finalized_at IS 'When session was finalized (null if active)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 001 complete: sessions table created with % indexes',
        (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'sessions');
END $$;
