-- Migration 007: Create views for common queries
-- Description: Materialized and standard views for analytics and dashboards
-- Author: lift-sys team
-- Date: 2025-10-19

-- ====================
-- VIEW: session_summary
-- ====================

CREATE OR REPLACE VIEW session_summary AS
SELECT
    s.id,
    s.user_id,
    s.status,
    s.source,
    s.revision_count,
    s.draft_count,
    s.hole_count,
    s.created_at,
    s.updated_at,
    s.finalized_at,
    -- Latest revision info
    (
        SELECT revision_number
        FROM session_revisions sr
        WHERE sr.session_id = s.id
        ORDER BY revision_number DESC
        LIMIT 1
    ) AS latest_revision_number,
    -- Latest draft info
    (
        SELECT draft_number
        FROM session_drafts sd
        WHERE sd.session_id = s.id
        ORDER BY draft_number DESC
        LIMIT 1
    ) AS latest_draft_number,
    (
        SELECT syntax_valid AND ast_valid
        FROM session_drafts sd
        WHERE sd.session_id = s.id
        ORDER BY draft_number DESC
        LIMIT 1
    ) AS latest_draft_valid,
    -- Performance metrics
    (
        SELECT SUM(generation_time_ms)
        FROM session_drafts sd
        WHERE sd.session_id = s.id
    ) AS total_generation_time_ms,
    (
        SELECT SUM(llm_cost_usd)
        FROM session_drafts sd
        WHERE sd.session_id = s.id
    ) AS total_llm_cost_usd,
    (
        SELECT SUM(llm_tokens_used)
        FROM session_drafts sd
        WHERE sd.session_id = s.id
    ) AS total_llm_tokens_used,
    -- Timestamps
    EXTRACT(EPOCH FROM (s.updated_at - s.created_at)) AS session_duration_seconds,
    EXTRACT(EPOCH FROM (s.finalized_at - s.created_at)) AS time_to_finalization_seconds
FROM sessions s;

COMMENT ON VIEW session_summary IS 'Aggregated session metrics for dashboards and analytics';

-- ====================
-- VIEW: user_analytics
-- ====================

CREATE OR REPLACE VIEW user_analytics AS
SELECT
    user_id,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE status = 'finalized') AS finalized_sessions,
    COUNT(*) FILTER (WHERE status = 'active') AS active_sessions,
    COUNT(*) FILTER (WHERE status = 'error') AS error_sessions,
    SUM(revision_count) AS total_revisions,
    SUM(draft_count) AS total_drafts,
    AVG(revision_count) AS avg_revisions_per_session,
    AVG(draft_count) AS avg_drafts_per_session,
    MIN(created_at) AS first_session_at,
    MAX(created_at) AS last_session_at,
    -- Performance metrics
    (
        SELECT SUM(sd.llm_cost_usd)
        FROM session_drafts sd
        JOIN sessions s ON s.id = sd.session_id
        WHERE s.user_id = sessions.user_id
    ) AS total_llm_cost_usd,
    (
        SELECT SUM(sd.llm_tokens_used)
        FROM session_drafts sd
        JOIN sessions s ON s.id = sd.session_id
        WHERE s.user_id = sessions.user_id
    ) AS total_llm_tokens_used,
    -- Avg time to finalization
    (
        SELECT AVG(EXTRACT(EPOCH FROM (finalized_at - created_at)))
        FROM sessions
        WHERE user_id = sessions.user_id
        AND finalized_at IS NOT NULL
    ) AS avg_time_to_finalization_seconds
FROM sessions
GROUP BY user_id;

COMMENT ON VIEW user_analytics IS 'Per-user aggregate metrics for usage tracking and billing';

-- ====================
-- VIEW: recent_activity
-- ====================

CREATE OR REPLACE VIEW recent_activity AS
SELECT
    'session_created' AS event_type,
    s.id AS session_id,
    s.user_id,
    NULL::UUID AS revision_id,
    NULL::UUID AS draft_id,
    NULL::UUID AS resolution_id,
    s.created_at AS event_time,
    jsonb_build_object(
        'status', s.status,
        'source', s.source
    ) AS event_data
FROM sessions s

UNION ALL

SELECT
    'revision_created' AS event_type,
    sr.session_id,
    s.user_id,
    sr.id AS revision_id,
    NULL::UUID AS draft_id,
    NULL::UUID AS resolution_id,
    sr.created_at AS event_time,
    jsonb_build_object(
        'revision_number', sr.revision_number,
        'source', sr.source
    ) AS event_data
FROM session_revisions sr
JOIN sessions s ON s.id = sr.session_id

UNION ALL

SELECT
    'draft_created' AS event_type,
    sd.session_id,
    s.user_id,
    NULL::UUID AS revision_id,
    sd.id AS draft_id,
    NULL::UUID AS resolution_id,
    sd.created_at AS event_time,
    jsonb_build_object(
        'draft_number', sd.draft_number,
        'syntax_valid', sd.syntax_valid,
        'ast_valid', sd.ast_valid,
        'source', sd.source
    ) AS event_data
FROM session_drafts sd
JOIN sessions s ON s.id = sd.session_id

UNION ALL

SELECT
    'hole_resolved' AS event_type,
    hr.session_id,
    s.user_id,
    hr.ir_revision_id AS revision_id,
    NULL::UUID AS draft_id,
    hr.id AS resolution_id,
    hr.created_at AS event_time,
    jsonb_build_object(
        'hole_type', hr.hole_type,
        'resolution_method', hr.resolution_method,
        'confidence_score', hr.confidence_score
    ) AS event_data
FROM hole_resolutions hr
JOIN sessions s ON s.id = hr.session_id

ORDER BY event_time DESC;

COMMENT ON VIEW recent_activity IS 'Unified activity feed across all tables for timeline views';

-- ====================
-- VIEW: draft_validation_stats
-- ====================

CREATE OR REPLACE VIEW draft_validation_stats AS
SELECT
    sd.session_id,
    s.user_id,
    COUNT(*) AS total_drafts,
    COUNT(*) FILTER (WHERE sd.syntax_valid) AS syntax_valid_count,
    COUNT(*) FILTER (WHERE sd.ast_valid) AS ast_valid_count,
    COUNT(*) FILTER (WHERE sd.syntax_valid AND sd.ast_valid) AS fully_valid_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sd.syntax_valid) / NULLIF(COUNT(*), 0), 2) AS syntax_valid_percent,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sd.ast_valid) / NULLIF(COUNT(*), 0), 2) AS ast_valid_percent,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sd.syntax_valid AND sd.ast_valid) / NULLIF(COUNT(*), 0), 2) AS fully_valid_percent,
    -- Performance
    AVG(sd.generation_time_ms) AS avg_generation_time_ms,
    AVG(sd.validation_time_ms) AS avg_validation_time_ms,
    SUM(sd.llm_cost_usd) AS total_llm_cost_usd
FROM session_drafts sd
JOIN sessions s ON s.id = sd.session_id
GROUP BY sd.session_id, s.user_id;

COMMENT ON VIEW draft_validation_stats IS 'Code generation success rates and performance metrics';

-- ====================
-- FUNCTION: Refresh user analytics (for future materialized view)
-- ====================

-- Note: For now using standard views. If performance becomes an issue,
-- convert user_analytics to a materialized view and refresh on schedule.

CREATE OR REPLACE FUNCTION refresh_user_analytics()
RETURNS VOID AS $$
BEGIN
    -- Placeholder for future materialized view refresh
    -- REFRESH MATERIALIZED VIEW CONCURRENTLY user_analytics;
    RAISE NOTICE 'User analytics view refreshed';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_user_analytics() IS 'Placeholder for future materialized view refresh';

-- Success message
DO $$
DECLARE
    view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO view_count
    FROM pg_views
    WHERE schemaname = 'public'
    AND viewname IN ('session_summary', 'user_analytics', 'recent_activity', 'draft_validation_stats');

    RAISE NOTICE 'Migration 007 complete: % views created', view_count;
    RAISE NOTICE 'Views: session_summary, user_analytics, recent_activity, draft_validation_stats';
END $$;
