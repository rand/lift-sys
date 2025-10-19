-- Migration 003: Create session_drafts table
-- Description: Tracks code generation drafts and attempts
-- Author: lift-sys team
-- Date: 2025-10-19

-- Create session_drafts table
CREATE TABLE IF NOT EXISTS session_drafts (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign keys
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ir_revision_id UUID REFERENCES session_revisions(id) ON DELETE SET NULL,

    -- Draft metadata
    draft_number INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('initial_generation', 'ast_repair', 'llm_regeneration', 'user_edit')),

    -- Content
    code_content TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',

    -- Validation
    syntax_valid BOOLEAN NOT NULL DEFAULT false,
    ast_valid BOOLEAN NOT NULL DEFAULT false,
    validation_errors JSONB DEFAULT '[]'::jsonb,

    -- Performance metrics
    generation_time_ms INTEGER,
    validation_time_ms INTEGER,
    llm_tokens_used INTEGER,
    llm_cost_usd NUMERIC(10, 6),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT session_drafts_unique_draft UNIQUE (session_id, draft_number),
    CONSTRAINT session_drafts_draft_number_positive CHECK (draft_number > 0),
    CONSTRAINT session_drafts_code_not_empty CHECK (LENGTH(code_content) > 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_drafts_session_id ON session_drafts(session_id);
CREATE INDEX IF NOT EXISTS idx_drafts_session_draft ON session_drafts(session_id, draft_number DESC);
CREATE INDEX IF NOT EXISTS idx_drafts_ir_revision_id ON session_drafts(ir_revision_id);
CREATE INDEX IF NOT EXISTS idx_drafts_created_at ON session_drafts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_drafts_source ON session_drafts(source);
CREATE INDEX IF NOT EXISTS idx_drafts_valid ON session_drafts(syntax_valid, ast_valid);

-- Create index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_drafts_validation_errors ON session_drafts USING GIN (validation_errors);
CREATE INDEX IF NOT EXISTS idx_drafts_metadata ON session_drafts USING GIN (metadata);

-- Add comments
COMMENT ON TABLE session_drafts IS 'Tracks code generation attempts with validation and performance metrics';
COMMENT ON COLUMN session_drafts.id IS 'Unique draft identifier';
COMMENT ON COLUMN session_drafts.session_id IS 'Session this draft belongs to';
COMMENT ON COLUMN session_drafts.ir_revision_id IS 'IR revision used to generate this draft (nullable)';
COMMENT ON COLUMN session_drafts.draft_number IS 'Sequential draft number within session';
COMMENT ON COLUMN session_drafts.source IS 'How this draft was created';
COMMENT ON COLUMN session_drafts.code_content IS 'Generated code';
COMMENT ON COLUMN session_drafts.language IS 'Programming language (default: python)';
COMMENT ON COLUMN session_drafts.syntax_valid IS 'Whether code has valid syntax';
COMMENT ON COLUMN session_drafts.ast_valid IS 'Whether code has valid AST';
COMMENT ON COLUMN session_drafts.validation_errors IS 'Syntax/AST validation errors';
COMMENT ON COLUMN session_drafts.generation_time_ms IS 'Time taken to generate code (milliseconds)';
COMMENT ON COLUMN session_drafts.validation_time_ms IS 'Time taken to validate code (milliseconds)';
COMMENT ON COLUMN session_drafts.llm_tokens_used IS 'Total tokens consumed (input + output)';
COMMENT ON COLUMN session_drafts.llm_cost_usd IS 'LLM API cost in USD';
COMMENT ON COLUMN session_drafts.metadata IS 'Additional draft metadata';
COMMENT ON COLUMN session_drafts.created_at IS 'Draft creation timestamp';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 003 complete: session_drafts table created';
END $$;
