-- Migration 005: Create Row-Level Security (RLS) policies
-- Description: Implement user isolation to prevent cross-user data access
-- Author: lift-sys team
-- Date: 2025-10-19

-- Enable RLS on all tables
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE hole_resolutions ENABLE ROW LEVEL SECURITY;

-- ====================
-- SESSIONS TABLE POLICIES
-- ====================

-- Policy: Users can view their own sessions
CREATE POLICY "Users can view their own sessions"
    ON sessions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own sessions
CREATE POLICY "Users can insert their own sessions"
    ON sessions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own sessions
CREATE POLICY "Users can update their own sessions"
    ON sessions
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own sessions
CREATE POLICY "Users can delete their own sessions"
    ON sessions
    FOR DELETE
    USING (auth.uid() = user_id);

-- ====================
-- SESSION_REVISIONS TABLE POLICIES
-- ====================

-- Policy: Users can view revisions of their own sessions
CREATE POLICY "Users can view their own session revisions"
    ON session_revisions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_revisions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can insert revisions for their own sessions
CREATE POLICY "Users can insert revisions for their own sessions"
    ON session_revisions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_revisions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can update revisions of their own sessions
CREATE POLICY "Users can update their own session revisions"
    ON session_revisions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_revisions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can delete revisions of their own sessions
CREATE POLICY "Users can delete their own session revisions"
    ON session_revisions
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_revisions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- ====================
-- SESSION_DRAFTS TABLE POLICIES
-- ====================

-- Policy: Users can view drafts of their own sessions
CREATE POLICY "Users can view their own session drafts"
    ON session_drafts
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_drafts.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can insert drafts for their own sessions
CREATE POLICY "Users can insert drafts for their own sessions"
    ON session_drafts
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_drafts.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can update drafts of their own sessions
CREATE POLICY "Users can update their own session drafts"
    ON session_drafts
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_drafts.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can delete drafts of their own sessions
CREATE POLICY "Users can delete their own session drafts"
    ON session_drafts
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = session_drafts.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- ====================
-- HOLE_RESOLUTIONS TABLE POLICIES
-- ====================

-- Policy: Users can view resolutions of their own sessions
CREATE POLICY "Users can view their own hole resolutions"
    ON hole_resolutions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = hole_resolutions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can insert resolutions for their own sessions
CREATE POLICY "Users can insert resolutions for their own sessions"
    ON hole_resolutions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = hole_resolutions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can update resolutions of their own sessions
CREATE POLICY "Users can update their own hole resolutions"
    ON hole_resolutions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = hole_resolutions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- Policy: Users can delete resolutions of their own sessions
CREATE POLICY "Users can delete their own hole resolutions"
    ON hole_resolutions
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.id = hole_resolutions.session_id
            AND sessions.user_id = auth.uid()
        )
    );

-- ====================
-- SERVICE ROLE BYPASS (for backend operations)
-- ====================

-- Note: The service_role key bypasses RLS entirely
-- Use service_role for:
-- - Background jobs
-- - Analytics queries
-- - Admin operations
-- - Modal backend API calls (when not acting on behalf of a user)

-- Add comments
COMMENT ON POLICY "Users can view their own sessions" ON sessions IS 'RLS: Users can only SELECT their own sessions';
COMMENT ON POLICY "Users can insert their own sessions" ON sessions IS 'RLS: Users can only INSERT sessions with their own user_id';
COMMENT ON POLICY "Users can update their own sessions" ON sessions IS 'RLS: Users can only UPDATE their own sessions';
COMMENT ON POLICY "Users can delete their own sessions" ON sessions IS 'RLS: Users can only DELETE their own sessions';

-- Success message
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    AND tablename IN ('sessions', 'session_revisions', 'session_drafts', 'hole_resolutions');

    RAISE NOTICE 'Migration 005 complete: RLS enabled with % policies', policy_count;
    RAISE NOTICE 'RLS prevents cross-user data access. Use service_role for backend operations.';
END $$;
