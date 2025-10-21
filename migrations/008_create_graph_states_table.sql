-- Migration 008: Create graph_states table
-- Description: Table for storing Pydantic AI graph execution state
-- Author: lift-sys team
-- Date: 2025-10-21
-- Related: H2 (StatePersistence)

-- Create graph_states table for Pydantic AI graph state persistence
CREATE TABLE IF NOT EXISTS graph_states (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Execution identification
    execution_id TEXT NOT NULL UNIQUE,
    user_id UUID,  -- Optional: for user-scoped executions

    -- State content (JSONB for flexibility)
    state_snapshot JSONB NOT NULL,
    state_type TEXT NOT NULL,  -- Fully qualified type name for deserialization

    -- Provenance and metadata
    provenance JSONB DEFAULT '[]'::jsonb,  -- Execution trace
    metadata JSONB DEFAULT '{}'::jsonb,    -- Additional execution metadata

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT graph_states_execution_id_not_empty CHECK (LENGTH(execution_id) > 0),
    CONSTRAINT graph_states_state_type_not_empty CHECK (LENGTH(state_type) > 0)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_graph_states_execution_id ON graph_states(execution_id);
CREATE INDEX IF NOT EXISTS idx_graph_states_user_id ON graph_states(user_id);
CREATE INDEX IF NOT EXISTS idx_graph_states_updated_at ON graph_states(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_graph_states_user_updated ON graph_states(user_id, updated_at DESC);

-- Create indexes for JSONB queries (enables efficient querying of state fields)
CREATE INDEX IF NOT EXISTS idx_graph_states_state_snapshot ON graph_states USING GIN (state_snapshot);
CREATE INDEX IF NOT EXISTS idx_graph_states_provenance ON graph_states USING GIN (provenance);
CREATE INDEX IF NOT EXISTS idx_graph_states_metadata ON graph_states USING GIN (metadata);

-- Add comments for documentation
COMMENT ON TABLE graph_states IS 'Stores Pydantic AI graph execution state for kill/resume workflows';
COMMENT ON COLUMN graph_states.id IS 'Primary key (UUID)';
COMMENT ON COLUMN graph_states.execution_id IS 'Unique execution identifier (string)';
COMMENT ON COLUMN graph_states.user_id IS 'User who initiated execution (optional, for RLS)';
COMMENT ON COLUMN graph_states.state_snapshot IS 'Serialized graph state (Pydantic model as JSON)';
COMMENT ON COLUMN graph_states.state_type IS 'Fully qualified type name for state deserialization';
COMMENT ON COLUMN graph_states.provenance IS 'Execution provenance chain (array of node outputs)';
COMMENT ON COLUMN graph_states.metadata IS 'Additional execution metadata';
COMMENT ON COLUMN graph_states.created_at IS 'State creation timestamp';
COMMENT ON COLUMN graph_states.updated_at IS 'Last update timestamp';

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_graph_states_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_graph_states_updated_at
    BEFORE UPDATE ON graph_states
    FOR EACH ROW
    EXECUTE FUNCTION update_graph_states_updated_at();

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 008 complete: graph_states table created with % indexes',
        (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'graph_states');
END $$;
