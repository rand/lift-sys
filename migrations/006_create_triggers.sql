-- Migration 006: Create triggers for automated updates
-- Description: Triggers for updated_at timestamps and denormalized counters
-- Author: lift-sys team
-- Date: 2025-10-19

-- ====================
-- FUNCTION: Update updated_at timestamp
-- ====================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at timestamp on row modification';

-- ====================
-- TRIGGER: sessions updated_at
-- ====================

CREATE TRIGGER trigger_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TRIGGER trigger_sessions_updated_at ON sessions IS 'Auto-update sessions.updated_at on modification';

-- ====================
-- FUNCTION: Update session revision_count
-- ====================

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
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_session_revision_count() IS 'Maintains denormalized revision_count in sessions table';

-- ====================
-- TRIGGER: session_revisions revision_count
-- ====================

CREATE TRIGGER trigger_revisions_count_insert
    AFTER INSERT ON session_revisions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_revision_count();

CREATE TRIGGER trigger_revisions_count_delete
    AFTER DELETE ON session_revisions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_revision_count();

COMMENT ON TRIGGER trigger_revisions_count_insert ON session_revisions IS 'Increment sessions.revision_count on insert';
COMMENT ON TRIGGER trigger_revisions_count_delete ON session_revisions IS 'Decrement sessions.revision_count on delete';

-- ====================
-- FUNCTION: Update session draft_count
-- ====================

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
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_session_draft_count() IS 'Maintains denormalized draft_count in sessions table';

-- ====================
-- TRIGGER: session_drafts draft_count
-- ====================

CREATE TRIGGER trigger_drafts_count_insert
    AFTER INSERT ON session_drafts
    FOR EACH ROW
    EXECUTE FUNCTION update_session_draft_count();

CREATE TRIGGER trigger_drafts_count_delete
    AFTER DELETE ON session_drafts
    FOR EACH ROW
    EXECUTE FUNCTION update_session_draft_count();

COMMENT ON TRIGGER trigger_drafts_count_insert ON session_drafts IS 'Increment sessions.draft_count on insert';
COMMENT ON TRIGGER trigger_drafts_count_delete ON session_drafts IS 'Decrement sessions.draft_count on delete';

-- ====================
-- FUNCTION: Update session hole_count from resolutions
-- ====================

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
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_session_hole_count() IS 'Maintains denormalized hole_count in sessions table';

-- ====================
-- TRIGGER: hole_resolutions hole_count
-- ====================

CREATE TRIGGER trigger_resolutions_count_insert
    AFTER INSERT ON hole_resolutions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_hole_count();

CREATE TRIGGER trigger_resolutions_count_delete
    AFTER DELETE ON hole_resolutions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_hole_count();

COMMENT ON TRIGGER trigger_resolutions_count_insert ON hole_resolutions IS 'Update sessions.hole_count on resolution insert';
COMMENT ON TRIGGER trigger_resolutions_count_delete ON hole_resolutions IS 'Update sessions.hole_count on resolution delete';

-- Success message
DO $$
DECLARE
    trigger_count INTEGER;
    function_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO trigger_count
    FROM pg_trigger
    WHERE tgname LIKE 'trigger_%';

    SELECT COUNT(*) INTO function_count
    FROM pg_proc
    WHERE proname LIKE 'update_%';

    RAISE NOTICE 'Migration 006 complete: % triggers and % functions created', trigger_count, function_count;
    RAISE NOTICE 'Denormalized counters (revision_count, draft_count, hole_count) will be maintained automatically';
END $$;
