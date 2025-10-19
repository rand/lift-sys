-- Migration 004: Create hole_resolutions table
-- Description: Tracks typed hole resolutions and user decisions
-- Author: lift-sys team
-- Date: 2025-10-19

-- Create hole_resolutions table
CREATE TABLE IF NOT EXISTS hole_resolutions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign keys
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ir_revision_id UUID REFERENCES session_revisions(id) ON DELETE SET NULL,

    -- Hole identification
    hole_id TEXT NOT NULL,
    hole_type TEXT NOT NULL CHECK (hole_type IN ('type', 'parameter', 'return_value', 'validation', 'entity', 'constraint', 'other')),

    -- Resolution
    resolution_method TEXT NOT NULL CHECK (resolution_method IN ('user_selection', 'ai_suggestion', 'inference', 'default')),
    resolved_value JSONB NOT NULL,
    confidence_score NUMERIC(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),

    -- Context
    original_hole_data JSONB,
    suggestions_provided JSONB DEFAULT '[]'::jsonb,
    user_feedback TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT hole_resolutions_unique_hole_revision UNIQUE (session_id, ir_revision_id, hole_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_resolutions_session_id ON hole_resolutions(session_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_ir_revision_id ON hole_resolutions(ir_revision_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_hole_type ON hole_resolutions(hole_type);
CREATE INDEX IF NOT EXISTS idx_resolutions_resolution_method ON hole_resolutions(resolution_method);
CREATE INDEX IF NOT EXISTS idx_resolutions_created_at ON hole_resolutions(created_at DESC);

-- Create index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_resolutions_resolved_value ON hole_resolutions USING GIN (resolved_value);
CREATE INDEX IF NOT EXISTS idx_resolutions_original_data ON hole_resolutions USING GIN (original_hole_data);
CREATE INDEX IF NOT EXISTS idx_resolutions_suggestions ON hole_resolutions USING GIN (suggestions_provided);
CREATE INDEX IF NOT EXISTS idx_resolutions_metadata ON hole_resolutions USING GIN (metadata);

-- Add comments
COMMENT ON TABLE hole_resolutions IS 'Tracks how typed holes were resolved during interactive refinement';
COMMENT ON COLUMN hole_resolutions.id IS 'Unique resolution identifier';
COMMENT ON COLUMN hole_resolutions.session_id IS 'Session this resolution belongs to';
COMMENT ON COLUMN hole_resolutions.ir_revision_id IS 'IR revision where hole was resolved';
COMMENT ON COLUMN hole_resolutions.hole_id IS 'Identifier of the hole being resolved';
COMMENT ON COLUMN hole_resolutions.hole_type IS 'Category of hole';
COMMENT ON COLUMN hole_resolutions.resolution_method IS 'How the hole was resolved';
COMMENT ON COLUMN hole_resolutions.resolved_value IS 'The final value/type chosen for this hole';
COMMENT ON COLUMN hole_resolutions.confidence_score IS 'Confidence in this resolution (0-1)';
COMMENT ON COLUMN hole_resolutions.original_hole_data IS 'Snapshot of hole before resolution';
COMMENT ON COLUMN hole_resolutions.suggestions_provided IS 'AI-generated suggestions shown to user';
COMMENT ON COLUMN hole_resolutions.user_feedback IS 'User comments about this resolution';
COMMENT ON COLUMN hole_resolutions.metadata IS 'Additional resolution metadata';
COMMENT ON COLUMN hole_resolutions.created_at IS 'Resolution timestamp';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 004 complete: hole_resolutions table created';
END $$;
