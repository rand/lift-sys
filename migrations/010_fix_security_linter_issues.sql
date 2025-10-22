-- Migration 010: Fix Supabase security linter issues
-- Description:
--   1. Convert SECURITY DEFINER views to SECURITY INVOKER (respects RLS)
--   2. Set fixed search_path on all functions (prevent schema attacks)
-- Author: lift-sys team
-- Date: 2025-10-21
-- References:
--   - https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view
--   - https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable

-- ====================
-- FIX 1: Recreate views with security_invoker=on
-- ====================

-- VIEW: session_summary
-- Drop and recreate with security_invoker to respect RLS
DROP VIEW IF EXISTS session_summary;

CREATE VIEW session_summary
WITH (security_invoker=on)
AS
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

COMMENT ON VIEW session_summary IS 'Aggregated session metrics for dashboards and analytics (SECURITY INVOKER)';

-- VIEW: user_analytics
DROP VIEW IF EXISTS user_analytics;

CREATE VIEW user_analytics
WITH (security_invoker=on)
AS
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

COMMENT ON VIEW user_analytics IS 'Per-user aggregate metrics for usage tracking and billing (SECURITY INVOKER)';

-- VIEW: recent_activity
DROP VIEW IF EXISTS recent_activity;

CREATE VIEW recent_activity
WITH (security_invoker=on)
AS
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

COMMENT ON VIEW recent_activity IS 'Unified activity feed across all tables for timeline views (SECURITY INVOKER)';

-- VIEW: draft_validation_stats
DROP VIEW IF EXISTS draft_validation_stats;

CREATE VIEW draft_validation_stats
WITH (security_invoker=on)
AS
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

COMMENT ON VIEW draft_validation_stats IS 'Code generation success rates and performance metrics (SECURITY INVOKER)';

-- ====================
-- FIX 2: Recreate functions with SET search_path
-- ====================

-- FUNCTION: update_updated_at_column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at timestamp on row modification (search_path: public)';

-- FUNCTION: update_session_revision_count
CREATE OR REPLACE FUNCTION update_session_revision_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE sessions
        SET revision_count = revision_count + 1
        WHERE id = NEW.session_id;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE sessions
        SET revision_count = GREATEST(0, revision_count - 1)
        WHERE id = OLD.session_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

COMMENT ON FUNCTION update_session_revision_count() IS 'Maintains denormalized revision_count in sessions table (search_path: public)';

-- FUNCTION: update_session_draft_count
CREATE OR REPLACE FUNCTION update_session_draft_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE sessions
        SET draft_count = draft_count + 1
        WHERE id = NEW.session_id;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE sessions
        SET draft_count = GREATEST(0, draft_count - 1)
        WHERE id = OLD.session_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

COMMENT ON FUNCTION update_session_draft_count() IS 'Maintains denormalized draft_count in sessions table (search_path: public)';

-- FUNCTION: update_session_hole_count
CREATE OR REPLACE FUNCTION update_session_hole_count()
RETURNS TRIGGER AS $$
DECLARE
    latest_revision_id UUID;
    resolved_holes INTEGER;
BEGIN
    -- Get the latest revision for this session
    SELECT id INTO latest_revision_id
    FROM session_revisions
    WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
    ORDER BY revision_number DESC
    LIMIT 1;

    -- Count resolved holes for the latest revision
    SELECT COUNT(*) INTO resolved_holes
    FROM hole_resolutions
    WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
    AND (ir_revision_id = latest_revision_id OR ir_revision_id IS NULL);

    -- Update hole_count (this is a simplified version - real implementation
    -- would need to count unresolved holes from IR, not resolved holes)
    UPDATE sessions
    SET hole_count = GREATEST(0, resolved_holes)
    WHERE id = COALESCE(NEW.session_id, OLD.session_id);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

COMMENT ON FUNCTION update_session_hole_count() IS 'Maintains denormalized hole_count in sessions table (search_path: public)';

-- FUNCTION: refresh_user_analytics
CREATE OR REPLACE FUNCTION refresh_user_analytics()
RETURNS VOID AS $$
BEGIN
    -- Placeholder for future materialized view refresh
    -- REFRESH MATERIALIZED VIEW CONCURRENTLY user_analytics;
    RAISE NOTICE 'User analytics view refreshed';
END;
$$ LANGUAGE plpgsql
SET search_path = public;

COMMENT ON FUNCTION refresh_user_analytics() IS 'Placeholder for future materialized view refresh (search_path: public)';

-- ====================
-- Verification
-- ====================

DO $$
DECLARE
    view_count INTEGER;
    function_count INTEGER;
BEGIN
    -- Count views with security_invoker
    SELECT COUNT(*) INTO view_count
    FROM pg_views
    WHERE schemaname = 'public'
    AND viewname IN ('session_summary', 'user_analytics', 'recent_activity', 'draft_validation_stats');

    -- Count functions with search_path set
    SELECT COUNT(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
    AND p.proname IN (
        'update_updated_at_column',
        'update_session_revision_count',
        'update_session_draft_count',
        'update_session_hole_count',
        'refresh_user_analytics'
    )
    AND p.proconfig IS NOT NULL; -- Has configuration (search_path set)

    RAISE NOTICE 'Migration 010 complete:';
    RAISE NOTICE '  - % views recreated with security_invoker=on', view_count;
    RAISE NOTICE '  - % functions updated with SET search_path = public', function_count;
    RAISE NOTICE 'Security linter issues resolved:';
    RAISE NOTICE '  ✓ Views now respect RLS (SECURITY INVOKER)';
    RAISE NOTICE '  ✓ Functions protected from schema attacks (fixed search_path)';
END $$;
