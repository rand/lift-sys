-- Migration 002: Create session_revisions table
-- Description: Tracks IR revision history for each session
-- Author: lift-sys team
-- Date: 2025-10-19

-- Create session_revisions table
CREATE TABLE IF NOT EXISTS session_revisions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign key to sessions
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Revision metadata
    revision_number INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('initial', 'refinement', 'repair', 'user_edit')),

    -- Content
    ir_content JSONB NOT NULL,
    validation_result JSONB,

    -- Change tracking
    changed_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
    change_summary TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT session_revisions_unique_revision UNIQUE (session_id, revision_number),
    CONSTRAINT session_revisions_revision_number_positive CHECK (revision_number > 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_revisions_session_id ON session_revisions(session_id);
CREATE INDEX IF NOT EXISTS idx_revisions_session_revision ON session_revisions(session_id, revision_number DESC);
CREATE INDEX IF NOT EXISTS idx_revisions_created_at ON session_revisions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revisions_source ON session_revisions(source);

-- Create index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_revisions_ir_content ON session_revisions USING GIN (ir_content);
CREATE INDEX IF NOT EXISTS idx_revisions_metadata ON session_revisions USING GIN (metadata);

-- Add comments
COMMENT ON TABLE session_revisions IS 'Tracks IR revision history with change tracking';
COMMENT ON COLUMN session_revisions.id IS 'Unique revision identifier';
COMMENT ON COLUMN session_revisions.session_id IS 'Session this revision belongs to';
COMMENT ON COLUMN session_revisions.revision_number IS 'Sequential revision number within session';
COMMENT ON COLUMN session_revisions.source IS 'How this revision was created';
COMMENT ON COLUMN session_revisions.ir_content IS 'IR snapshot for this revision';
COMMENT ON COLUMN session_revisions.validation_result IS 'IR interpreter validation result';
COMMENT ON COLUMN session_revisions.changed_fields IS 'Which IR fields changed from previous revision';
COMMENT ON COLUMN session_revisions.change_summary IS 'Human-readable description of changes';
COMMENT ON COLUMN session_revisions.metadata IS 'Additional revision metadata';
COMMENT ON COLUMN session_revisions.created_at IS 'Revision creation timestamp';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 complete: session_revisions table created';
END $$;
