-- Migration 009: Add execution history columns
-- Description: Extends graph_states table with timing and performance metadata for H11
-- Author: lift-sys team
-- Date: 2025-10-21
-- Related: H11 (ExecutionHistorySchema), H2 (StatePersistence)

-- Add new columns for execution history (H11)
ALTER TABLE graph_states
ADD COLUMN IF NOT EXISTS graph_type TEXT DEFAULT 'forward_mode',
ADD COLUMN IF NOT EXISTS original_inputs JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS timing JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS performance JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS is_replay BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS original_execution_id TEXT;

-- Add constraints
ALTER TABLE graph_states
ADD CONSTRAINT graph_states_graph_type_not_empty
    CHECK (LENGTH(graph_type) > 0);

-- Create indexes for new columns (query optimization)

-- Index for graph type filtering
CREATE INDEX IF NOT EXISTS idx_graph_states_graph_type
    ON graph_states(graph_type);

-- Index for replay lookups
CREATE INDEX IF NOT EXISTS idx_graph_states_original_execution_id
    ON graph_states(original_execution_id)
    WHERE original_execution_id IS NOT NULL;

-- Index for replay flag
CREATE INDEX IF NOT EXISTS idx_graph_states_is_replay
    ON graph_states(is_replay)
    WHERE is_replay = TRUE;

-- GIN indexes for new JSONB columns (enables efficient querying of nested fields)
CREATE INDEX IF NOT EXISTS idx_graph_states_original_inputs
    ON graph_states USING GIN (original_inputs);

CREATE INDEX IF NOT EXISTS idx_graph_states_timing
    ON graph_states USING GIN (timing);

CREATE INDEX IF NOT EXISTS idx_graph_states_performance
    ON graph_states USING GIN (performance);

-- Composite index for common query pattern: user + graph_type + created_at
CREATE INDEX IF NOT EXISTS idx_graph_states_user_graph_type_created
    ON graph_states(user_id, graph_type, created_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN graph_states.graph_type IS 'Type of graph executed (forward_mode, reverse_mode, etc.)';
COMMENT ON COLUMN graph_states.original_inputs IS 'Original inputs for replay support (JSONB)';
COMMENT ON COLUMN graph_states.timing IS 'Execution timing information (start_time, end_time, duration, node_timings)';
COMMENT ON COLUMN graph_states.performance IS 'Performance metrics (tokens, llm_calls, memory, cache hits/misses)';
COMMENT ON COLUMN graph_states.is_replay IS 'Whether this execution is a replay of another';
COMMENT ON COLUMN graph_states.original_execution_id IS 'Original execution ID if this is a replay';

-- Create helper function for extracting timing metrics
CREATE OR REPLACE FUNCTION get_execution_duration(timing_json JSONB)
RETURNS FLOAT AS $$
BEGIN
    RETURN (timing_json->>'total_duration_ms')::FLOAT;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create helper function for extracting token counts
CREATE OR REPLACE FUNCTION get_total_tokens(performance_json JSONB)
RETURNS INTEGER AS $$
BEGIN
    RETURN (performance_json->>'total_tokens')::INTEGER;
EXCEPTION
    WHEN OTHERS THEN
        RETURN 0;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create view for execution history analytics
CREATE OR REPLACE VIEW execution_history_analytics AS
SELECT
    execution_id,
    graph_type,
    user_id,
    created_at,
    get_execution_duration(timing) as duration_ms,
    get_total_tokens(performance) as total_tokens,
    (performance->>'total_llm_calls')::INTEGER as llm_calls,
    (performance->>'cache_hits')::INTEGER as cache_hits,
    (performance->>'cache_misses')::INTEGER as cache_misses,
    is_replay,
    original_execution_id
FROM graph_states
WHERE timing IS NOT NULL;

-- Add comment on view
COMMENT ON VIEW execution_history_analytics IS 'Analytics view for execution history queries (H11)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 009 complete: execution history columns added with % total indexes',
        (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'graph_states');
END $$;
