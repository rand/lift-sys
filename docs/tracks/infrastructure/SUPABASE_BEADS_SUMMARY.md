---
track: infrastructure
document_type: beads_summary
status: complete
priority: P0
completion: 100%
last_updated: 2025-10-19
session_protocol: |
  For new Claude Code session:
  1. Supabase integration is COMPLETE (epic lift-sys-259)
  2. SupabaseSessionStore replaced InMemorySessionStore
  3. Features: RLS user isolation, multi-instance sharing, persistent storage
  4. Deployment: Live on Modal with secrets configured
  5. Historical record - use for understanding Supabase integration decisions
related_docs:
  - docs/tracks/infrastructure/SUPABASE_QUICK_START.md
  - docs/tracks/infrastructure/INFRASTRUCTURE_STATUS.md
  - docs/MASTER_ROADMAP.md
---

# Supabase Integration: Beads Work Items Summary

**Epic**: lift-sys-259
**Timeline**: 3 days (8 hours total)
**Priority**: P0 (blocks production launch)
**Status**: Ready to start

---

## Overview

Replace `InMemorySessionStore` with Supabase-backed persistent storage to enable:
- Sessions survive server restarts
- Multi-instance session sharing (Modal containers)
- User isolation via Row-Level Security (RLS)
- Production-ready persistence for beta launch

---

## Work Item Hierarchy

```
lift-sys-259: Epic - Supabase Integration (P0)
├── lift-sys-260: Setup Supabase project and schema (P0, 2h)
├── lift-sys-261: Implement SupabaseSessionStore (P0, 3h)
├── lift-sys-262: Integrate with API layer (P0, 1h)
├── lift-sys-263: Deploy to Modal (P0, 1h)
└── lift-sys-264: Monitoring and documentation (P1, 1h)
```

**Total estimated time**: 8 hours over 3 days

---

## Bead Details

### lift-sys-259: Epic - Supabase Integration

**Type**: Epic
**Priority**: P0
**Status**: Open
**Timeline**: 3 days

**Goal**: Replace InMemorySessionStore with Supabase for production persistence

**Success Criteria**:
- ✅ Sessions persist across restarts
- ✅ User isolation via RLS
- ✅ <500ms p95 latency
- ✅ 100% test coverage
- ✅ Rollback plan validated

**Documentation**:
- `SUPABASE_INTEGRATION_PLAN.md` - Full implementation plan
- `DATASTORE_RECOMMENDATION.md` - Why Supabase
- `SUPABASE_QUICK_START.md` - 30-minute setup guide

---

### lift-sys-260: Setup Supabase project and schema

**Type**: Task
**Priority**: P0
**Status**: Open
**Estimated Time**: 2 hours
**Dependencies**: lift-sys-259 (epic)

**What**: Create Supabase project and deploy database schema

**Tasks**:
1. Create Supabase project (free tier)
2. Create 4 tables: sessions, session_revisions, session_drafts, hole_resolutions
3. Add indexes for performance
4. Implement RLS policies for user isolation
5. Create triggers (updated_at, counters)
6. Create views (analytics)
7. Test in Supabase Studio

**Deliverables**:
- Supabase project created
- Database schema deployed
- RLS policies active
- Migration SQL files in `migrations/`

**Files**:
- `migrations/001_create_sessions_table.sql`
- `migrations/002_create_revisions_table.sql`
- `migrations/003_create_drafts_table.sql`
- `migrations/004_create_resolutions_table.sql`
- `migrations/005_create_rls_policies.sql`
- `migrations/006_create_triggers.sql`
- `migrations/007_create_views.sql`

**Acceptance Criteria**:
- ✅ All tables created with constraints
- ✅ Indexes optimize common queries
- ✅ RLS prevents cross-user access
- ✅ Can insert/query test data

**Reference**: SUPABASE_INTEGRATION_PLAN.md Section 3 + 4.1

---

### lift-sys-261: Implement SupabaseSessionStore

**Type**: Task
**Priority**: P0
**Status**: Open
**Estimated Time**: 3 hours
**Dependencies**: lift-sys-259, lift-sys-260

**What**: Implement `SupabaseSessionStore` class replacing `InMemorySessionStore`

**Tasks**:
1. Add `supabase-py` to pyproject.toml
2. Implement `SupabaseSessionStore`:
   - create(), get(), update(), delete()
   - list_active(), list_all()
   - Connection management
   - Error handling
3. Add `user_id` field to `PromptSession` model
4. JSON serialization helpers
5. Write unit tests (100% coverage)
6. Write integration tests with real Supabase
7. Performance benchmarks

**Deliverables**:
- `SupabaseSessionStore` implementation (~300 lines)
- Updated `PromptSession` with user_id
- Unit tests (~400 lines, 100% coverage)
- Integration tests (~200 lines)
- Performance benchmarks

**Files**:
- `lift_sys/spec_sessions/supabase_storage.py` (new)
- `lift_sys/spec_sessions/models.py` (modified)
- `tests/spec_sessions/test_supabase_storage.py` (new)
- `tests/integration/test_supabase_integration.py` (new)
- `tests/performance/test_supabase_performance.py` (new)

**Acceptance Criteria**:
- ✅ All SessionStore methods implemented
- ✅ RLS enforcement verified
- ✅ Concurrent updates handled
- ✅ Error handling robust
- ✅ Tests passing (unit + integration)
- ✅ Performance <500ms p95

**Reference**: SUPABASE_INTEGRATION_PLAN.md Section 4.2 + 5

---

### lift-sys-262: Integrate with API layer

**Type**: Task
**Priority**: P0
**Status**: Open
**Estimated Time**: 1 hour
**Dependencies**: lift-sys-259, lift-sys-261

**What**: Update FastAPI server to use `SupabaseSessionStore`

**Tasks**:
1. Update `AppState` in server.py:
   - Initialize `SupabaseSessionStore`
   - Add fallback to `InMemorySessionStore`
   - Pass user_id from authenticated requests
2. Update `SpecSessionManager`:
   - Accept user_id in create_from_prompt()
3. Update API endpoints to extract user_id
4. Add Supabase health check
5. Update API tests
6. Test multi-user isolation

**Deliverables**:
- AppState using SupabaseSessionStore
- User isolation working (RLS)
- API tests passing
- Health check endpoint

**Files**:
- `lift_sys/api/server.py` (modified)
- `lift_sys/spec_sessions/manager.py` (modified)
- `tests/api/test_sessions_api.py` (modified)
- `tests/e2e/test_session_persistence.py` (new)

**Acceptance Criteria**:
- ✅ Sessions persist across restarts
- ✅ User A cannot access User B's sessions
- ✅ All existing API tests passing
- ✅ Graceful degradation if Supabase down

**Reference**: SUPABASE_INTEGRATION_PLAN.md Section 4.3

---

### lift-sys-263: Deploy to Modal

**Type**: Task
**Priority**: P0
**Status**: Open
**Estimated Time**: 1 hour
**Dependencies**: lift-sys-259, lift-sys-262

**What**: Deploy Supabase integration to Modal staging and production

**Tasks**:
1. Update Modal image (add supabase-py)
2. Create Modal secrets (Supabase credentials)
3. Test locally with `modal serve`
4. Deploy to staging
5. Run smoke tests
6. Deploy to production
7. Monitor logs
8. Verify cross-instance sharing

**Deliverables**:
- Modal image includes supabase
- Supabase secrets configured
- Staging deployment successful
- Production deployment successful

**Files**:
- `lift_sys/infrastructure/modal_image.py` (modified)
- `lift_sys/modal_app.py` (modified)
- `tests/e2e/test_modal_supabase.py` (new)

**Modal Commands**:
```bash
modal secret create supabase SUPABASE_URL=... SUPABASE_ANON_KEY=...
modal deploy lift_sys/modal_app.py --env staging
modal deploy lift_sys/modal_app.py --env production
```

**Acceptance Criteria**:
- ✅ Modal functions connect to Supabase
- ✅ Sessions persist across container restarts
- ✅ Sessions shared across instances
- ✅ No connection pool issues
- ✅ Latency <500ms p95
- ✅ No errors in logs

**Reference**: SUPABASE_INTEGRATION_PLAN.md Section 4.4 + 6

---

### lift-sys-264: Monitoring and documentation

**Type**: Task
**Priority**: P1
**Status**: Open
**Estimated Time**: 1 hour
**Dependencies**: lift-sys-259, lift-sys-263

**What**: Add monitoring, alerting, and comprehensive documentation

**Tasks**:
1. Add Supabase health check endpoint
2. Configure metrics:
   - Connection pool metrics
   - Query latency histogram
   - Error rates
   - Business metrics (sessions created)
3. Set up alerts:
   - Connection failures
   - High latency
   - RLS bypass attempts
4. Create dashboards
5. Write documentation:
   - SUPABASE_SETUP.md
   - SUPABASE_RUNBOOK.md
   - Architecture diagrams

**Deliverables**:
- Health check working
- Metrics collected
- Alerts configured
- Dashboards created
- Documentation complete

**Files**:
- `lift_sys/api/routes/health.py` (modified)
- `docs/SUPABASE_SETUP.md` (new)
- `docs/SUPABASE_RUNBOOK.md` (new)
- `docs/ARCHITECTURE.md` (updated)
- `docs/diagrams/supabase_architecture.png` (new)

**Acceptance Criteria**:
- ✅ Health check returns status
- ✅ Metrics visible
- ✅ Alerts fire correctly
- ✅ Documentation clear
- ✅ Team can troubleshoot

**Reference**: SUPABASE_INTEGRATION_PLAN.md Section 4.5 + 11 + 12

---

## Execution Strategy

### Day 1 (4 hours)

**Morning (2 hours)**:
- Complete lift-sys-260 (Setup)
- Create Supabase project
- Run all migrations
- Verify in Studio

**Afternoon (2 hours)**:
- Start lift-sys-261 (Implementation)
- Implement SupabaseSessionStore
- Add user_id to models
- Start unit tests

### Day 2 (3 hours)

**Morning (1 hour)**:
- Complete lift-sys-261
- Finish unit tests (100% coverage)
- Write integration tests
- Performance benchmarks

**Midday (1 hour)**:
- Complete lift-sys-262 (API Integration)
- Update AppState
- Update endpoints
- API tests passing

**Afternoon (1 hour)**:
- Complete lift-sys-263 (Modal Deployment)
- Update Modal image
- Create secrets
- Deploy staging → production

### Day 3 (1 hour)

**Morning (1 hour)**:
- Complete lift-sys-264 (Monitoring)
- Add health check
- Configure metrics
- Write documentation

---

## Success Metrics

**Functional**:
- ✅ Sessions persist across restarts
- ✅ User isolation enforced (RLS)
- ✅ No data loss
- ✅ Concurrent updates handled

**Performance**:
- ✅ Session creation <500ms p95
- ✅ Session retrieval <200ms p95
- ✅ List operations <500ms p95

**Quality**:
- ✅ 100% test coverage (storage layer)
- ✅ All integration tests passing
- ✅ End-to-end test passing
- ✅ Documentation complete

**Operations**:
- ✅ Health check working
- ✅ Metrics collected
- ✅ Alerts configured
- ✅ Rollback plan validated

---

## Risk Management

**High-Risk Issues**:
- Supabase outage → Fallback to InMemorySessionStore
- RLS bypass → Security audit, penetration test
- Connection pool exhaustion → Use pgBouncer

**Mitigation**:
- Feature flag: `USE_SUPABASE=false`
- Comprehensive testing (unit + integration + e2e)
- Monitoring and alerts
- Documented rollback procedure

---

## Rollback Plan

**If issues occur**:

1. **Set feature flag**:
   ```bash
   modal secret update lift-sys USE_SUPABASE=false
   modal deploy lift_sys/modal_app.py
   ```

2. **Fallback code** (already in server.py):
   ```python
   if USE_SUPABASE:
       try:
           state.session_store = SupabaseSessionStore(...)
       except Exception:
           state.session_store = InMemorySessionStore()
   else:
       state.session_store = InMemorySessionStore()
   ```

3. **Notify users** of temporary session loss

4. **Fix issue**, re-enable Supabase

**Recovery time**: <10 minutes

---

## Commands Quick Reference

### Beads Commands

```bash
# List Supabase work items
bd list --search supabase --json

# Check epic status
bd show lift-sys-259 --json

# Start working on a task
bd update lift-sys-260 --status in_progress

# Complete a task
bd close lift-sys-260 --reason "Schema deployed and tested"

# Check dependencies
bd show lift-sys-261 --json | jq '.dependencies'
```

### Development Commands

```bash
# Setup Supabase locally
supabase start

# Run migrations
psql $DATABASE_URL -f migrations/*.sql

# Test connection
uv run python test_supabase_connection.py

# Run tests
uv run pytest tests/spec_sessions/test_supabase_storage.py -v

# Deploy to Modal
modal deploy lift_sys/modal_app.py
```

---

## Resources

**Documents**:
- `SUPABASE_INTEGRATION_PLAN.md` - Full implementation plan (12 sections)
- `DATASTORE_RECOMMENDATION.md` - Why Supabase (10 sections)
- `SUPABASE_QUICK_START.md` - 30-minute setup guide
- `INFRASTRUCTURE_RESEARCH_REPORT.md` - Infrastructure strategy

**External**:
- Supabase Docs: https://supabase.com/docs
- Python Client: https://supabase.com/docs/reference/python
- RLS Guide: https://supabase.com/docs/guides/auth/row-level-security

**Beads**:
- Epic: lift-sys-259
- Tasks: lift-sys-260 through lift-sys-264

---

## Next Actions

1. ✅ **Review this summary** - Understand the plan
2. ✅ **Read SUPABASE_QUICK_START.md** - Get familiar with setup
3. ✅ **Start lift-sys-260** - Create Supabase project
4. ✅ **Follow SUPABASE_INTEGRATION_PLAN.md** - Detailed guidance for each phase

**Ready to start**: Yes
**Estimated completion**: 3 days from start
**Blocker for**: Production launch, beta program

---

**Last Updated**: 2025-10-19
**Status**: Ready for execution
**Owner**: Engineering team
