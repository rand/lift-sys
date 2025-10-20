# Supabase Integration Implementation Plan

**Date**: 2025-10-19
**Epic**: Persistent Session Storage with Supabase
**Timeline**: 3 days (6-8 hours total)
**Priority**: P0 (blocks production launch)
**Dependencies**: Modal deployment, OAuth system

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Implementation Phases](#implementation-phases)
5. [Testing Strategy](#testing-strategy)
6. [Deployment Plan](#deployment-plan)
7. [Rollback Strategy](#rollback-strategy)
8. [Success Criteria](#success-criteria)

---

## 1. Overview

### 1.1 Current State

**Storage Implementation**: `InMemorySessionStore`
- Location: `lift_sys/spec_sessions/storage.py`
- Data lost on restart
- No multi-instance support
- No user isolation
- Used by: `SpecSessionManager`, `AppState` (server.py)

**Data Models**:
- `PromptSession`: Full refinement session state
- `PromptRevision`: User input history
- `IRDraft`: Versioned IR snapshots
- `HoleResolution`: Typed hole clarifications

### 1.2 Target State

**Storage Implementation**: `SupabaseSessionStore`
- Persistent across restarts
- Multi-instance support (shared state)
- Row-Level Security (RLS) for user isolation
- Audit trail and analytics
- Backup and point-in-time recovery

### 1.3 Why Supabase

✅ **Production-ready**: Managed Postgres with automatic backups
✅ **Modal-compatible**: HTTP client works from any container
✅ **Future-proof**: Aligns with proposed infrastructure (pgvector, RLS, Realtime)
✅ **No migration**: This IS the production solution
✅ **Free tier**: Sufficient for beta program (10k sessions)

---

## 2. Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Modal Functions                    │
│                                                      │
│  ┌────────────────┐          ┌──────────────────┐  │
│  │ FastAPI Server │          │ Session Manager  │  │
│  │  (server.py)   │────────▶ │  (manager.py)   │  │
│  └────────────────┘          └──────────────────┘  │
│           │                           │             │
│           │                           │             │
│           ▼                           ▼             │
│  ┌────────────────────────────────────────────┐    │
│  │      SupabaseSessionStore                  │    │
│  │      (supabase_storage.py)                 │    │
│  └────────────────────────────────────────────┘    │
│                     │                               │
└─────────────────────┼───────────────────────────────┘
                      │ HTTPS (supabase-py client)
                      ▼
         ┌────────────────────────────┐
         │     Supabase Cloud         │
         │                            │
         │  ┌──────────────────────┐  │
         │  │  Postgres Database   │  │
         │  │  - sessions          │  │
         │  │  - session_revisions │  │
         │  │  - session_drafts    │  │
         │  │  - hole_resolutions  │  │
         │  └──────────────────────┘  │
         │                            │
         │  ┌──────────────────────┐  │
         │  │  RLS Policies        │  │
         │  │  (user isolation)    │  │
         │  └──────────────────────┘  │
         └────────────────────────────┘
```

### 2.2 Data Flow

**Session Creation**:
1. User sends prompt via API
2. `SpecSessionManager.create_from_prompt()` → translates to IR
3. `SupabaseSessionStore.create()` → inserts to Supabase
4. Supabase RLS enforces `user_id = auth.uid()`
5. Returns session with ID

**Session Update**:
1. User resolves hole via API
2. `SpecSessionManager.resolve_hole()` → updates session
3. `SupabaseSessionStore.update()` → updates session + creates history snapshot
4. Concurrent update handling (optimistic locking via `updated_at`)

**Session Retrieval**:
1. User requests session list
2. `SupabaseSessionStore.list_active()` → queries with RLS filter
3. Only returns sessions where `user_id = auth.uid()`

---

## 3. Database Schema

### 3.1 Core Tables

#### sessions
```sql
CREATE TABLE sessions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    user_id UUID NOT NULL,

    -- Session metadata
    status TEXT NOT NULL DEFAULT 'active',
    source TEXT NOT NULL DEFAULT 'prompt',

    -- Current state (denormalized for performance)
    current_draft_version INT DEFAULT 0,
    current_ir JSONB,

    -- Metrics
    revision_count INT DEFAULT 0,
    hole_count INT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    finalized_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('active', 'finalized', 'abandoned')),
    CONSTRAINT valid_source CHECK (source IN ('prompt', 'reverse_mode'))
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status) WHERE status = 'active';
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_sessions_user_status ON sessions(user_id, status);
CREATE INDEX idx_sessions_metadata ON sessions USING gin(metadata);
```

#### session_revisions
```sql
CREATE TABLE session_revisions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Revision data
    content TEXT NOT NULL,
    revision_type TEXT NOT NULL,
    target_hole TEXT,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT valid_revision_type CHECK (revision_type IN (
        'initial', 'hole_fill', 'constraint_add', 'manual_edit'
    ))
);

-- Indexes
CREATE INDEX idx_revisions_session_id ON session_revisions(session_id, created_at DESC);
CREATE INDEX idx_revisions_type ON session_revisions(revision_type);
```

#### session_drafts
```sql
CREATE TABLE session_drafts (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Draft data
    version INT NOT NULL,
    ir JSONB NOT NULL,
    validation_status TEXT NOT NULL,

    -- Validation results
    smt_results JSONB DEFAULT '[]'::jsonb,
    ambiguities TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT valid_validation_status CHECK (validation_status IN (
        'pending', 'valid', 'contradictory', 'incomplete'
    )),
    UNIQUE(session_id, version)
);

-- Indexes
CREATE INDEX idx_drafts_session_id ON session_drafts(session_id, version DESC);
CREATE INDEX idx_drafts_validation ON session_drafts(validation_status);
CREATE INDEX idx_drafts_ir ON session_drafts USING gin(ir);
```

#### hole_resolutions
```sql
CREATE TABLE hole_resolutions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Resolution data
    hole_id TEXT NOT NULL,
    resolution_text TEXT NOT NULL,
    resolution_type TEXT NOT NULL,
    applied BOOLEAN DEFAULT FALSE,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    applied_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT valid_resolution_type CHECK (resolution_type IN (
        'clarify_intent', 'add_constraint', 'refine_signature', 'specify_effect'
    ))
);

-- Indexes
CREATE INDEX idx_resolutions_session_id ON hole_resolutions(session_id);
CREATE INDEX idx_resolutions_hole_id ON hole_resolutions(hole_id);
CREATE INDEX idx_resolutions_applied ON hole_resolutions(applied) WHERE applied = FALSE;
```

### 3.2 Row-Level Security (RLS)

```sql
-- Enable RLS
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE hole_resolutions ENABLE ROW LEVEL SECURITY;

-- Sessions policies
CREATE POLICY "Users can view their own sessions"
    ON sessions FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can create sessions"
    ON sessions FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own sessions"
    ON sessions FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete their own sessions"
    ON sessions FOR DELETE
    USING (user_id = auth.uid());

-- Session revisions policies (inherit from session)
CREATE POLICY "Users can view revisions of their sessions"
    ON session_revisions FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create revisions for their sessions"
    ON session_revisions FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- Similar policies for session_drafts and hole_resolutions
-- (repeated pattern: allow all operations if session owned by user)
```

### 3.3 Functions and Triggers

```sql
-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update revision count on sessions
CREATE OR REPLACE FUNCTION update_revision_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions
    SET revision_count = (
        SELECT COUNT(*) FROM session_revisions WHERE session_id = NEW.session_id
    )
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_revision_count
    AFTER INSERT ON session_revisions
    FOR EACH ROW
    EXECUTE FUNCTION update_revision_count();

-- Update hole count on sessions
CREATE OR REPLACE FUNCTION update_hole_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions
    SET hole_count = (
        SELECT COUNT(*) FROM hole_resolutions
        WHERE session_id = NEW.session_id AND applied = FALSE
    )
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_hole_count
    AFTER INSERT OR UPDATE ON hole_resolutions
    FOR EACH ROW
    EXECUTE FUNCTION update_hole_count();
```

### 3.4 Views (Analytics)

```sql
-- Session summary view
CREATE VIEW session_summary AS
SELECT
    s.id,
    s.user_id,
    s.status,
    s.source,
    s.current_draft_version,
    s.revision_count,
    s.hole_count,
    s.created_at,
    s.updated_at,
    s.finalized_at,
    EXTRACT(EPOCH FROM (COALESCE(s.finalized_at, NOW()) - s.created_at)) / 60 AS duration_minutes,
    COUNT(DISTINCT sd.id) AS total_drafts,
    COUNT(DISTINCT hr.id) FILTER (WHERE hr.applied) AS resolved_holes
FROM sessions s
LEFT JOIN session_drafts sd ON s.id = sd.session_id
LEFT JOIN hole_resolutions hr ON s.id = hr.session_id
GROUP BY s.id;

-- Active sessions by user
CREATE VIEW active_sessions_by_user AS
SELECT
    user_id,
    COUNT(*) AS active_count,
    AVG(revision_count) AS avg_revisions,
    AVG(hole_count) AS avg_unresolved_holes
FROM sessions
WHERE status = 'active'
GROUP BY user_id;
```

---

## 4. Implementation Phases

### 4.1 Phase 1: Setup & Schema (Day 1 - 2 hours)

**Tasks**:
1. Create Supabase project
2. Run schema migrations
3. Configure RLS policies
4. Test in Supabase Studio

**Deliverables**:
- Supabase project created (free tier)
- Database schema deployed
- RLS policies active
- Test data inserted manually

**Beads**: `lift-sys-260` (P0)

---

### 4.2 Phase 2: Python Client Integration (Day 1-2 - 3 hours)

**Tasks**:
1. Add `supabase-py` to dependencies
2. Create Modal secret for Supabase credentials
3. Implement `SupabaseSessionStore`
4. Write unit tests
5. Write integration tests

**Files Created**:
- `lift_sys/spec_sessions/supabase_storage.py` (~300 lines)
- `tests/spec_sessions/test_supabase_storage.py` (~400 lines)
- `tests/integration/test_supabase_integration.py` (~200 lines)

**Deliverables**:
- `SupabaseSessionStore` implements `SessionStore` protocol
- All CRUD operations working
- RLS enforcement verified
- 100% test coverage for storage layer

**Beads**: `lift-sys-261` (P0)

---

### 4.3 Phase 3: API Integration (Day 2 - 1 hour)

**Tasks**:
1. Update `AppState` to use `SupabaseSessionStore`
2. Add user_id to session creation
3. Update API endpoints
4. Test multi-user isolation

**Files Modified**:
- `lift_sys/api/server.py` (AppState initialization)
- `lift_sys/spec_sessions/models.py` (add user_id field)
- `lift_sys/spec_sessions/manager.py` (pass user_id)

**Deliverables**:
- Sessions persist across server restarts
- User isolation working (RLS)
- API tests passing

**Beads**: `lift-sys-262` (P0)

---

### 4.4 Phase 4: Modal Deployment (Day 2-3 - 1 hour)

**Tasks**:
1. Update Modal image to include `supabase-py`
2. Add Supabase secrets to Modal
3. Deploy to staging
4. Test end-to-end
5. Deploy to production

**Files Modified**:
- `lift_sys/infrastructure/modal_image.py`
- `lift_sys/modal_app.py`

**Deliverables**:
- Modal functions can access Supabase
- Secrets properly configured
- End-to-end test passing

**Beads**: `lift-sys-263` (P0)

---

### 4.5 Phase 5: Monitoring & Documentation (Day 3 - 1 hour)

**Tasks**:
1. Add Supabase connection health check
2. Document Supabase setup
3. Create runbook for common operations
4. Update architecture docs

**Files Created**:
- `docs/SUPABASE_SETUP.md`
- `docs/SUPABASE_RUNBOOK.md`

**Deliverables**:
- Health check endpoint working
- Documentation complete
- Team can troubleshoot issues

**Beads**: `lift-sys-264` (P1)

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Location**: `tests/spec_sessions/test_supabase_storage.py`

**Test Cases**:
```python
class TestSupabaseSessionStore:
    """Unit tests for SupabaseSessionStore."""

    def test_create_session(self, supabase_store, mock_user_id):
        """Test creating a new session."""
        # Arrange
        session = PromptSession.create_new()
        session.user_id = mock_user_id

        # Act
        session_id = supabase_store.create(session)

        # Assert
        assert session_id == session.session_id
        retrieved = supabase_store.get(session_id)
        assert retrieved.user_id == mock_user_id

    def test_get_session_enforces_rls(self, supabase_store):
        """Test RLS prevents accessing other users' sessions."""
        # Arrange
        user1_session = create_session_for_user("user-1")
        supabase_store.create(user1_session)

        # Act (as user-2)
        with set_auth_context("user-2"):
            result = supabase_store.get(user1_session.session_id)

        # Assert
        assert result is None  # RLS blocks access

    def test_update_session_optimistic_locking(self, supabase_store):
        """Test concurrent updates are handled correctly."""
        # Arrange
        session = create_session()
        supabase_store.create(session)

        # Act - simulate concurrent update
        session_copy = supabase_store.get(session.session_id)
        session.status = "finalized"
        session_copy.status = "abandoned"

        supabase_store.update(session)

        # Assert - last write wins (or use optimistic locking)
        with pytest.raises(ConcurrentModificationError):
            supabase_store.update(session_copy)

    def test_list_active_filters_by_status(self, supabase_store):
        """Test list_active only returns active sessions."""
        # Arrange
        active = create_session(status="active")
        finalized = create_session(status="finalized")
        supabase_store.create(active)
        supabase_store.create(finalized)

        # Act
        results = supabase_store.list_active()

        # Assert
        assert len(results) == 1
        assert results[0].session_id == active.session_id

    def test_delete_session_cascades(self, supabase_store):
        """Test deleting session cascades to revisions/drafts."""
        # Arrange
        session = create_complex_session_with_history()
        supabase_store.create(session)

        # Act
        supabase_store.delete(session.session_id)

        # Assert
        assert supabase_store.get(session.session_id) is None
        # Verify cascade deleted revisions/drafts
        assert count_revisions(session.session_id) == 0
```

### 5.2 Integration Tests

**Location**: `tests/integration/test_supabase_integration.py`

**Test Cases**:
```python
@pytest.mark.integration
class TestSupabaseIntegration:
    """Integration tests with real Supabase (test database)."""

    async def test_full_session_lifecycle(self, supabase_client):
        """Test complete session workflow."""
        # Create session
        manager = create_session_manager(supabase_client)
        session = await manager.create_from_prompt("Create a function")

        # Resolve hole
        session = await manager.resolve_hole(
            session.session_id,
            "hole_function_name",
            "calculate_sum"
        )

        # Finalize
        await manager.finalize_session(session.session_id)

        # Verify persistence
        retrieved = supabase_client.get(session.session_id)
        assert retrieved.status == "finalized"
        assert len(retrieved.revisions) == 2

    async def test_multi_user_isolation(self, supabase_client):
        """Test RLS isolates users correctly."""
        # User 1 creates session
        with auth_context("user-1"):
            session1 = await create_session("User 1 session")

        # User 2 creates session
        with auth_context("user-2"):
            session2 = await create_session("User 2 session")

            # User 2 cannot see User 1's session
            results = supabase_client.list_all()
            assert len(results) == 1
            assert results[0].session_id == session2.session_id

    async def test_concurrent_updates_same_session(self, supabase_client):
        """Test concurrent updates to same session."""
        session = await create_session()

        # Simulate concurrent API requests
        tasks = [
            manager.resolve_hole(session.session_id, f"hole_{i}", f"value_{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all updates succeeded (or handled correctly)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0

        # Verify final state
        final = supabase_client.get(session.session_id)
        assert len(final.pending_resolutions) == 5
```

### 5.3 End-to-End Tests

**Location**: `tests/e2e/test_session_persistence.py`

**Test Cases**:
```python
@pytest.mark.e2e
class TestSessionPersistence:
    """End-to-end tests via API."""

    async def test_session_survives_restart(self, api_client):
        """Test session persists across API restarts."""
        # Create session via API
        response = await api_client.post("/api/sessions", json={
            "prompt": "Create a function that adds two numbers"
        })
        session_id = response.json()["session_id"]

        # Simulate server restart (reset AppState)
        await api_client.restart_server()

        # Retrieve session
        response = await api_client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    async def test_session_shared_across_modal_instances(self):
        """Test session accessible from different Modal containers."""
        # Create session in container 1
        session_id = await modal_invoke_function(
            "create_session",
            prompt="Test prompt"
        )

        # Retrieve from container 2
        session = await modal_invoke_function(
            "get_session",
            session_id=session_id
        )

        assert session["session_id"] == session_id
```

### 5.4 Performance Tests

**Location**: `tests/performance/test_supabase_performance.py`

**Test Cases**:
```python
@pytest.mark.performance
class TestSupabasePerformance:
    """Performance benchmarks for Supabase operations."""

    def test_create_session_latency(self, benchmark):
        """Benchmark session creation latency."""
        result = benchmark(create_and_store_session)
        assert result.stats.mean < 0.2  # < 200ms

    def test_list_sessions_with_1000_sessions(self, benchmark):
        """Benchmark list performance with many sessions."""
        # Setup: create 1000 sessions
        setup_1000_sessions()

        result = benchmark(supabase_store.list_active)
        assert result.stats.mean < 0.5  # < 500ms

    def test_concurrent_updates_throughput(self):
        """Test concurrent update throughput."""
        # Create 100 sessions
        sessions = [create_session() for _ in range(100)]

        # Update all concurrently
        start = time.time()
        await asyncio.gather(*[
            update_session(s) for s in sessions
        ])
        elapsed = time.time() - start

        throughput = 100 / elapsed
        assert throughput > 20  # > 20 updates/sec
```

---

## 6. Deployment Plan

### 6.1 Pre-Deployment Checklist

- [ ] Supabase project created (free tier)
- [ ] Schema migrations tested locally
- [ ] RLS policies validated
- [ ] Unit tests passing (100% coverage)
- [ ] Integration tests passing
- [ ] Modal secrets configured
- [ ] Rollback plan documented
- [ ] Team notified of deployment

### 6.2 Deployment Steps

**Step 1: Create Supabase Project**
```bash
# Option 1: Web UI
# Go to https://supabase.com/dashboard
# Click "New Project"
# Name: lift-sys
# Region: us-east-1 (or closest to Modal)
# Tier: Free

# Option 2: CLI
supabase projects create lift-sys --region us-east-1 --tier free
```

**Step 2: Run Migrations**
```bash
# Save schema SQL to migrations/001_initial_schema.sql
# Apply to Supabase
psql $DATABASE_URL -f migrations/001_initial_schema.sql

# Or use Supabase CLI
supabase db push
```

**Step 3: Create Modal Secrets**
```bash
# Get credentials from Supabase dashboard
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_ANON_KEY="eyJhbGci..."  # From API settings

# Create Modal secret
modal secret create supabase \
  SUPABASE_URL="$SUPABASE_URL" \
  SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"
```

**Step 4: Update Code**
```bash
# Add supabase-py to pyproject.toml
uv add supabase

# Commit changes
git add pyproject.toml lift_sys/spec_sessions/supabase_storage.py
git commit -m "feat: Add Supabase session storage"
```

**Step 5: Deploy to Staging**
```bash
# Deploy Modal app
modal deploy lift_sys/modal_app.py --env staging

# Run smoke test
curl https://lift-sys-staging.modal.run/health
```

**Step 6: Validate**
```bash
# Create test session
curl -X POST https://lift-sys-staging.modal.run/api/sessions \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"prompt": "Test persistence"}'

# Verify in Supabase Studio
# Check sessions table has 1 row
```

**Step 7: Deploy to Production**
```bash
# Deploy to production
modal deploy lift_sys/modal_app.py --env production

# Monitor logs
modal app logs lift-sys
```

### 6.3 Post-Deployment Verification

**Checklist**:
- [ ] Health check passing
- [ ] Session creation working
- [ ] Session retrieval working
- [ ] RLS enforcing user isolation
- [ ] No errors in logs
- [ ] Supabase dashboard shows activity
- [ ] Performance acceptable (<500ms p95)

---

## 7. Rollback Strategy

### 7.1 Rollback Triggers

**Rollback if**:
- Supabase connection failures >5 minutes
- Data corruption detected
- RLS bypass discovered (security issue)
- Performance degradation >3x baseline
- Critical bugs blocking user workflows

### 7.2 Rollback Procedure

**Step 1: Activate Fallback Storage**
```python
# lift_sys/api/server.py
USE_SUPABASE = os.getenv("USE_SUPABASE", "true").lower() == "true"

if USE_SUPABASE:
    try:
        state.session_store = SupabaseSessionStore(...)
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        state.session_store = InMemorySessionStore()
else:
    state.session_store = InMemorySessionStore()
```

**Step 2: Set Environment Variable**
```bash
# Disable Supabase
modal secret update lift-sys USE_SUPABASE=false

# Redeploy
modal deploy lift_sys/modal_app.py
```

**Step 3: Notify Users**
```
Subject: Temporary session persistence disabled

We're experiencing issues with session persistence. Your current
sessions will be lost on server restart. We're working on a fix.

Expected resolution: <time>
```

**Step 4: Fix and Restore**
```bash
# Fix issue
# ...

# Re-enable Supabase
modal secret update lift-sys USE_SUPABASE=true

# Deploy
modal deploy lift_sys/modal_app.py

# Verify
curl https://lift-sys.modal.run/health
```

### 7.3 Data Recovery

**If data lost during rollback**:
1. Check Supabase point-in-time recovery (Pro tier)
2. Restore from daily backup (automatic on Pro)
3. Export data: `pg_dump $DATABASE_URL > backup.sql`
4. Import to new database: `psql $NEW_DATABASE_URL < backup.sql`

---

## 8. Success Criteria

### 8.1 Functional Requirements

✅ **Session Persistence**:
- Sessions survive server restarts
- Sessions accessible across Modal instances

✅ **User Isolation**:
- Users can only access their own sessions
- RLS policies enforce boundaries

✅ **Data Integrity**:
- No data loss during normal operations
- Concurrent updates handled correctly
- History preserved (revisions, drafts)

✅ **Performance**:
- Session creation: <500ms p95
- Session retrieval: <200ms p95
- List operations: <500ms p95 (up to 1000 sessions)

### 8.2 Non-Functional Requirements

✅ **Reliability**:
- 99.9% uptime (Supabase SLA)
- Automatic failover to in-memory on Supabase outage

✅ **Security**:
- RLS enforces user isolation
- Credentials stored in Modal secrets
- No SQL injection vulnerabilities

✅ **Maintainability**:
- 100% test coverage for storage layer
- Clear documentation for operations
- Runbooks for common issues

✅ **Observability**:
- Health check endpoint working
- Connection pool metrics logged
- Slow query alerts configured

### 8.3 Acceptance Criteria

**For Product Owner**:
- [ ] User can create session and see it after restart
- [ ] User cannot see other users' sessions
- [ ] Session history preserved (can rollback)
- [ ] Performance acceptable (<1s for all operations)

**For Engineering**:
- [ ] All unit tests passing (100% coverage)
- [ ] All integration tests passing
- [ ] End-to-end test passing
- [ ] Documentation complete
- [ ] Rollback plan tested

**For Operations**:
- [ ] Health check endpoint working
- [ ] Monitoring dashboards created
- [ ] Alerting configured
- [ ] Runbook validated

---

## 9. Risk Assessment

### 9.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Supabase outage | Low | High | Fallback to in-memory store |
| Connection pool exhaustion | Medium | Medium | Connection pooling (pgBouncer) |
| RLS bypass bug | Low | Critical | Security audit, penetration test |
| Migration data loss | Low | High | Thorough testing, backup before deploy |
| Performance degradation | Medium | Medium | Load testing, caching layer |
| Cost overrun | Low | Low | Free tier sufficient for beta |

### 9.2 Mitigation Strategies

**Supabase Outage**:
- Automatic fallback to `InMemorySessionStore`
- Feature flag: `USE_SUPABASE=false`
- User notification of reduced functionality

**Connection Pool Exhaustion**:
- Use Supabase connection pooler (pgBouncer)
- Set max connections limit
- Monitor connection count

**RLS Bypass**:
- Security audit by external team
- Penetration testing
- Regular RLS policy review

**Performance**:
- Load testing with 10k sessions
- Add caching for hot queries (Redis)
- Use database indexes

---

## 10. Timeline and Dependencies

### 10.1 Timeline

```
Day 1 (4 hours):
├─ Morning (2h): Phase 1 (Setup & Schema)
└─ Afternoon (2h): Phase 2 (Python Client) - Part 1

Day 2 (3 hours):
├─ Morning (1h): Phase 2 (Python Client) - Part 2
├─ Midday (1h): Phase 3 (API Integration)
└─ Afternoon (1h): Phase 4 (Modal Deployment)

Day 3 (1 hour):
└─ Morning (1h): Phase 5 (Monitoring & Docs)
```

**Total**: 8 hours (3 days elapsed)

### 10.2 Dependencies

**Blockers** (must complete first):
- Modal deployment working (`lift_sys/modal_app.py`)
- OAuth system functional (user authentication)

**Blocked by this**:
- Production launch (need persistent storage)
- Beta program (need session history)
- Analytics (need query capabilities)

**Parallel Work** (can happen simultaneously):
- Semantic IR features (Phase 1 roadmap)
- UI improvements (frontend team)
- Documentation updates

---

## 11. Monitoring and Observability

### 11.1 Metrics to Track

**Application Metrics**:
- `supabase_connection_pool_size` - Current connections
- `supabase_connection_pool_available` - Available connections
- `supabase_query_duration_ms` - Query latency histogram
- `supabase_query_errors_total` - Error count by type

**Business Metrics**:
- `sessions_created_total` - Counter
- `sessions_finalized_total` - Counter
- `sessions_abandoned_total` - Counter
- `session_duration_minutes` - Histogram
- `holes_resolved_total` - Counter

### 11.2 Alerts

**Critical**:
- Supabase connection failures >5 consecutive
- RLS bypass detected
- Data corruption detected

**Warning**:
- Query latency p95 >1s
- Connection pool utilization >80%
- Error rate >5%

### 11.3 Dashboards

**Supabase Dashboard** (in Supabase Studio):
- Active connections
- Query performance
- Table sizes
- Index usage

**Application Dashboard** (Grafana/Datadog):
- Session lifecycle metrics
- User activity
- Error rates
- Performance trends

---

## 12. Documentation Requirements

### 12.1 User Documentation

**For API Users** (`docs/API_SESSIONS.md`):
- How sessions work
- Session lifecycle
- API endpoints
- Example workflows

### 12.2 Developer Documentation

**For Contributors** (`docs/SUPABASE_SETUP.md`):
- Local development setup
- Running migrations
- Testing against Supabase
- Debugging tips

**Architecture** (`docs/ARCHITECTURE.md`):
- Data model diagram
- Storage layer architecture
- RLS policy design
- Performance considerations

### 12.3 Operations Documentation

**Runbook** (`docs/SUPABASE_RUNBOOK.md`):
- Common operations (backup, restore, migration)
- Troubleshooting guide
- Incident response procedures
- Rollback procedures

---

## Appendix A: Code Templates

### A.1 SupabaseSessionStore Implementation

See `lift_sys/spec_sessions/supabase_storage.py` (to be created).

### A.2 Migration Files

See `migrations/001_initial_schema.sql` (to be created).

### A.3 Test Fixtures

See `tests/fixtures/supabase.py` (to be created).

---

## Appendix B: SQL Migration Files

All SQL in section 3 (Database Schema) should be saved to:
- `migrations/001_create_sessions_table.sql`
- `migrations/002_create_revisions_table.sql`
- `migrations/003_create_drafts_table.sql`
- `migrations/004_create_resolutions_table.sql`
- `migrations/005_create_rls_policies.sql`
- `migrations/006_create_triggers.sql`
- `migrations/007_create_views.sql`

---

**Document Status**: Complete
**Next Action**: Create Beads work items for each phase
**Owner**: Engineering team
**Review Date**: After Phase 5 completion
