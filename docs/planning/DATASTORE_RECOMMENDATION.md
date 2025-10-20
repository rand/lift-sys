# Datastore Recommendation: lift-sys Progressive Data Strategy

**Date**: 2025-10-19
**Context**: Need persistent storage for sessions, user data, and IR specifications
**Alignment**: Infrastructure research report recommendations (defer complex migration, ship fast)

---

## Executive Summary

**Recommendation**: Use **Supabase (hosted Postgres)** from Day 1, accessed directly from Modal functions.

**Why**:
- ✅ **Production-ready immediately**: No migration later
- ✅ **Clear upgrade path**: Start with free tier, scale to Pro/Team as needed
- ✅ **Modal-compatible**: Works perfectly with Modal functions via supabase-py
- ✅ **Future-proof**: Aligns with proposed architecture (experiments/infrastructure)
- ✅ **Simple setup**: <30 minutes to get running

**Migration path**: None needed - this IS the production solution.

---

## 1. Current State Analysis

### 1.1 What You Have Now

**Storage Implementation**: `InMemorySessionStore` (server.py:137)
```python
# lift_sys/spec_sessions/storage.py
class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, PromptSession] = {}
```

**Usage**:
- Session management (prompt → IR workflow)
- Repository metadata caching
- Progress log (in-memory deque)

**Problems**:
- ❌ Data lost on restart
- ❌ Can't scale horizontally (sessions not shared across instances)
- ❌ No persistence for user data
- ❌ No way to query/analyze historical sessions

### 1.2 Data Storage Requirements

**Immediate Needs** (Beta launch):
1. **Session persistence**: PromptSession objects survive restarts
2. **User associations**: Link sessions to authenticated users
3. **IR history**: Store generated IRs for analysis/improvement
4. **Repository metadata**: Cache GitHub repo info

**Near-term Needs** (Months 2-6):
1. **Enhanced IR metadata**: Entity graphs, typed holes, refinement history (Phase 1 roadmap)
2. **User preferences**: Settings, favorited repositories
3. **Analytics**: Track success rates, latency by prompt type
4. **Collaborative features**: Share sessions, comment on IRs

**Future Needs** (Month 7+):
1. **Vector search**: Similarity search on IRs (pgvector)
2. **Time-series data**: Performance metrics, usage patterns
3. **Real-time collaboration**: Multi-user editing (Supabase Realtime)

---

## 2. Option Analysis

### Option 1: Modal Dict (Current Modal primitive)

**What it is**: Key-value store provided by Modal
```python
import modal
app = modal.App()
session_dict = modal.Dict.from_name("lift-sessions", create_if_missing=True)

@app.function()
def save_session(session_id: str, data: dict):
    session_dict[session_id] = data
```

**Pros**:
- ✅ Native Modal integration (already using for tokens)
- ✅ Zero setup (automatic provisioning)
- ✅ Simple API

**Cons**:
- ❌ **Key-value only** (no queries, joins, indexes)
- ❌ **No schema validation** (JSON blobs only)
- ❌ **No migration path** to relational DB (data model mismatch)
- ❌ **Limited observability** (can't run SQL to debug)
- ❌ **Not production-grade** for complex data (Modal docs say use for config/cache)

**Verdict**: ❌ **Not recommended** - Technical debt trap, forces migration later

---

### Option 2: Modal Volume + SQLite

**What it is**: SQLite file on Modal Volume
```python
import modal
import sqlite3

volume = modal.Volume.from_name("lift-db", create_if_missing=True)
app = modal.App()

@app.function(volumes={"/db": volume})
def query_sessions():
    conn = sqlite3.connect("/db/lift.db")
    # ... queries
```

**Pros**:
- ✅ Full SQL (queries, joins, indexes)
- ✅ Schema validation
- ✅ Local development easy (same SQLite file)

**Cons**:
- ❌ **Single-writer** (Modal Volume concurrency limits)
- ❌ **Manual backups** (volume snapshots, not automatic)
- ❌ **No managed features** (no auth, no real-time, no edge functions)
- ❌ **Migration required** for production scale (SQLite → Postgres)
- ❌ **No connection pooling** (open/close per request = slow)

**Verdict**: ⚠️ **Acceptable for MVP**, but forces migration at scale

---

### Option 3: Supabase (Hosted Postgres)

**What it is**: Postgres-as-a-service with auth, storage, real-time
```python
from supabase import create_client, Client

# In Modal function
supabase: Client = create_client(
    supabase_url=os.environ["SUPABASE_URL"],
    supabase_key=os.environ["SUPABASE_KEY"]
)

# Query sessions
sessions = supabase.table("sessions").select("*").eq("user_id", user_id).execute()

# Insert new session
supabase.table("sessions").insert({
    "id": session_id,
    "user_id": user_id,
    "prompt": prompt,
    "status": "active",
    "created_at": datetime.now().isoformat()
}).execute()
```

**Pros**:
- ✅ **Production-ready from Day 1** (no migration needed)
- ✅ **Postgres** (pgvector for embeddings, JSONB for flexible schemas)
- ✅ **Managed** (automatic backups, scaling, monitoring)
- ✅ **Auth built-in** (Row Level Security policies)
- ✅ **Real-time** (Supabase Realtime for collaborative features)
- ✅ **Storage** (file uploads for artifacts)
- ✅ **Edge Functions** (serverless functions if needed later)
- ✅ **Great DX** (Web UI, migrations, Studio for debugging)
- ✅ **Modal-compatible** (just HTTP client, works from any container)
- ✅ **Aligns with proposed architecture** (experiments/infrastructure already specced Supabase)

**Cons**:
- ⚠️ **Paid service** (but free tier generous: 500MB DB, 2GB bandwidth)
- ⚠️ **Network latency** (vs local SQLite, but Modal Volume also has latency)
- ⚠️ **External dependency** (but Modal is also external)

**Costs**:
- **Free tier**: 500MB DB, 2GB bandwidth, 50MB file storage
  - Sufficient for: 5k-10k sessions
- **Pro ($25/mo)**: 8GB DB, 50GB bandwidth, 100GB storage
  - Sufficient for: 100k+ sessions
- **Team ($599/mo)**: 100GB DB, 250GB bandwidth
  - Sufficient for: Millions of sessions

**Verdict**: ✅ **RECOMMENDED** - Production solution from Day 1

---

### Option 4: Neon, PlanetScale, or other hosted Postgres

**What they are**: Alternative managed Postgres/MySQL services

**Pros**: Similar to Supabase (managed, scalable)
**Cons**:
- Missing Supabase extras (auth, real-time, storage, edge functions)
- Don't align with proposed infrastructure experiments

**Verdict**: ⚠️ **Acceptable alternatives** if Supabase unavailable, but Supabase preferred

---

## 3. Recommendation: Supabase

### 3.1 Why Supabase Wins

**Aligns with all priorities**:
1. ✅ **Ship fast**: Setup in <30 min, no infrastructure work
2. ✅ **Production-ready**: This IS the production solution (no migration)
3. ✅ **Future-proof**: Matches proposed architecture from experiments/infrastructure
4. ✅ **Clear upgrade path**: Free → Pro → Team as you scale
5. ✅ **Modal-compatible**: Works perfectly with Modal functions

**Specific advantages for lift-sys**:
- **pgvector**: For semantic IR search (Phase 2+ roadmap)
- **JSONB**: Store flexible IR schemas that evolve
- **RLS**: User isolation (required for multi-tenant)
- **Realtime**: Collaborative editing (Phase 3+ roadmap)
- **Auth**: User management (already needed for OAuth)

**Risk mitigation**:
- Supabase is open-source (can self-host if needed)
- Standard Postgres (can migrate to any Postgres provider)
- 100k+ customers (Figma, GitHub Copilot, etc.)

### 3.2 Setup Timeline

**Day 1** (30 minutes):
1. Create Supabase project (free tier)
2. Define initial schema (sessions, users, irs tables)
3. Add supabase-py to Modal image
4. Store credentials in Modal secrets
5. Test connection from Modal function

**Day 2** (2 hours):
1. Implement `SupabaseSessionStore` (replace InMemorySessionStore)
2. Add migrations (SQL files in git)
3. Update API endpoints to use new store
4. Test session persistence

**Day 3** (1 hour):
1. Add indexes for common queries
2. Set up RLS policies (user isolation)
3. Configure backups (automatic on Pro tier)

**Total**: ~4 hours to production-ready datastore

---

## 4. Implementation Plan

### 4.1 Phase 1: Core Session Storage (Day 1-3)

**Schema** (initial):
```sql
-- Users table (from OAuth)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL, -- 'anthropic', 'openai', etc.
    provider_user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    prompt TEXT NOT NULL,
    status TEXT NOT NULL, -- 'active', 'finalized', 'abandoned'
    ir_version INT DEFAULT 0,
    current_ir JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Session history (for rollback)
CREATE TABLE session_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    version INT NOT NULL,
    ir_snapshot JSONB NOT NULL,
    change_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, version)
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_history_session_id ON session_history(session_id, version);

-- RLS policies
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Users can only see their own sessions
CREATE POLICY "Users can view their own sessions"
    ON sessions FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own sessions"
    ON sessions FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own sessions"
    ON sessions FOR UPDATE
    USING (user_id = auth.uid());
```

**Python Implementation**:
```python
# lift_sys/spec_sessions/supabase_storage.py
from supabase import create_client, Client
from .storage import SessionStore
from .models import PromptSession

class SupabaseSessionStore:
    """Supabase-backed storage for PromptSessions."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)

    def create(self, session: PromptSession) -> str:
        """Store a new session."""
        data = {
            "id": session.session_id,
            "user_id": session.user_id,  # Add to PromptSession model
            "prompt": session.prompt,
            "status": session.status,
            "ir_version": len(session.history),
            "current_ir": session.current_ir.to_dict() if session.current_ir else None,
            "metadata": {
                "holes": [h.to_dict() for h in session.holes],
                "assists": session.assists,
            }
        }
        self.client.table("sessions").insert(data).execute()
        return session.session_id

    def get(self, session_id: str) -> PromptSession | None:
        """Retrieve a session by ID."""
        result = self.client.table("sessions").select("*").eq("id", session_id).execute()
        if not result.data:
            return None
        return self._to_session(result.data[0])

    def update(self, session: PromptSession) -> None:
        """Update an existing session."""
        data = {
            "status": session.status,
            "ir_version": len(session.history),
            "current_ir": session.current_ir.to_dict() if session.current_ir else None,
            "metadata": {
                "holes": [h.to_dict() for h in session.holes],
                "assists": session.assists,
            },
            "updated_at": "NOW()"
        }
        self.client.table("sessions").update(data).eq("id", session.session_id).execute()

        # Save to history
        self.client.table("session_history").insert({
            "session_id": session.session_id,
            "version": len(session.history),
            "ir_snapshot": data["current_ir"],
            "change_description": "Update"
        }).execute()

    def list_active(self) -> list[PromptSession]:
        """List active sessions for current user."""
        result = self.client.table("sessions")\
            .select("*")\
            .eq("status", "active")\
            .order("created_at", desc=True)\
            .execute()
        return [self._to_session(row) for row in result.data]

    def list_all(self) -> list[PromptSession]:
        """List all sessions for current user."""
        result = self.client.table("sessions")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()
        return [self._to_session(row) for row in result.data]

    def delete(self, session_id: str) -> None:
        """Delete a session (cascades to history)."""
        self.client.table("sessions").delete().eq("id", session_id).execute()

    def _to_session(self, row: dict) -> PromptSession:
        """Convert database row to PromptSession."""
        # Reconstruct PromptSession from row data
        # ... implementation details
```

**Modal Integration**:
```python
# lift_sys/modal_app.py
import modal
import os

app = modal.App("lift-sys")

# Add Supabase credentials as secrets
supabase_secret = modal.Secret.from_dict({
    "SUPABASE_URL": "https://xxxxx.supabase.co",
    "SUPABASE_KEY": "your-anon-key-here"
})

# Update image to include supabase-py
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "supabase==2.3.0",
    # ... other deps
)

@app.function(image=image, secrets=[supabase_secret])
def api_handler():
    from lift_sys.spec_sessions.supabase_storage import SupabaseSessionStore

    store = SupabaseSessionStore(
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_key=os.environ["SUPABASE_KEY"]
    )
    # Use store in API endpoints
```

### 4.2 Phase 2: Enhanced Features (Month 2-3)

**Add as needed**:
1. **IR embeddings** (pgvector for semantic search)
```sql
CREATE EXTENSION vector;

ALTER TABLE sessions ADD COLUMN ir_embedding vector(1536);
CREATE INDEX idx_sessions_embedding ON sessions
    USING ivfflat (ir_embedding vector_cosine_ops);
```

2. **Analytics tables** (query patterns, success rates)
```sql
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    event_type TEXT NOT NULL,
    event_data JSONB,
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_session ON analytics_events(session_id);
CREATE INDEX idx_analytics_type ON analytics_events(event_type, created_at DESC);
```

3. **Real-time collaboration** (Supabase Realtime)
```python
# Subscribe to session changes
session_channel = supabase.channel(f"session:{session_id}")
session_channel.on_postgres_changes(
    event="UPDATE",
    schema="public",
    table="sessions",
    filter=f"id=eq.{session_id}",
    callback=lambda payload: handle_session_update(payload)
).subscribe()
```

### 4.3 Phase 3: Scale Optimizations (Month 7+, if needed)

**If hitting limits** (>100k sessions/mo):
1. **Connection pooling**: Use Supabase Pooler (pgBouncer)
2. **Read replicas**: Separate read/write workloads
3. **Partitioning**: Partition sessions by created_at (monthly)
4. **Caching**: Add Redis for hot queries (Modal + Upstash Redis)

---

## 5. Migration Path (None Required!)

**The beauty of this approach**: No migration needed!

**Day 1**: Supabase free tier
**Month 3**: Upgrade to Pro ($25/mo)
**Month 12**: Upgrade to Team ($599/mo) or self-host

**Data portability**:
- ✅ Standard Postgres (can dump and restore anywhere)
- ✅ Supabase CLI for local development
- ✅ Can switch to Neon, RDS, self-hosted Postgres if needed

**Contrast with other options**:
- Modal Dict → Supabase: **Hard migration** (KV to relational)
- SQLite → Postgres: **Medium migration** (schema changes, connection pooling)
- Supabase → Supabase: **No migration** (just upgrade tier)

---

## 6. Comparison with Proposed Architecture

**From experiments/infrastructure/lift-sys-cloud-migration-spec-v3.md**:
> Database – Supabase Postgres with pgvector and RLS

**This recommendation**: ✅ **Exact match**

**Difference**:
- Proposed: Supabase + Cloudflare Workers + AWS Fargate (complex)
- This recommendation: Supabase + Modal (simple)

**Future migration**:
- When you do the full cloud migration (if ever), Supabase stays the same
- Just change: Modal functions → ECS Fargate
- Database: **No change required**

**Alignment**: This recommendation **future-proofs** for the proposed architecture while keeping immediate setup simple.

---

## 7. Implementation Checklist

### Week 1: Setup & Basic Storage

**Day 1** (Setup):
- [ ] Create Supabase project (free tier)
- [ ] Run initial schema SQL (users, sessions, session_history)
- [ ] Add RLS policies
- [ ] Test queries in Supabase Studio

**Day 2** (Integration):
- [ ] Add supabase-py to pyproject.toml
- [ ] Create Modal secret with Supabase credentials
- [ ] Update Modal image to include supabase
- [ ] Implement SupabaseSessionStore class
- [ ] Write unit tests (test with test database)

**Day 3** (API Update):
- [ ] Update server.py to use SupabaseSessionStore
- [ ] Update AppState initialization
- [ ] Test session CRUD operations
- [ ] Test RLS policies (user isolation)
- [ ] Deploy to Modal staging

**Day 4-5** (Migration & Launch):
- [ ] No data to migrate (starting fresh)
- [ ] Update documentation
- [ ] Deploy to Modal production
- [ ] Monitor query performance

### Month 2-3: Enhanced Features (as needed)

- [ ] Add analytics tables
- [ ] Add IR embeddings (pgvector)
- [ ] Set up Supabase Realtime for collaborative features
- [ ] Add indexes based on query patterns
- [ ] Upgrade to Pro tier if approaching free tier limits

---

## 8. Cost Projections

**Scenario 1: Beta (10-20 users)**
- Estimate: 500 sessions/month
- Database size: ~50 MB
- Bandwidth: <1 GB/month
- **Cost**: $0 (free tier)

**Scenario 2: Early Adopters (100 users)**
- Estimate: 5k sessions/month
- Database size: ~500 MB
- Bandwidth: ~5 GB/month
- **Cost**: $0 (free tier, just under limits)

**Scenario 3: Growth (1k users)**
- Estimate: 50k sessions/month
- Database size: ~5 GB
- Bandwidth: ~40 GB/month
- **Cost**: $25/month (Pro tier)

**Scenario 4: Scale (10k users)**
- Estimate: 500k sessions/month
- Database size: ~50 GB
- Bandwidth: ~200 GB/month
- **Cost**: $599/month (Team tier)

**At scale**: $599/mo for database supporting 10k users = $0.06/user/month (negligible)

---

## 9. Alternative: If You Don't Want External Service

**If you absolutely must avoid external dependencies**:

Use **SQLite on Modal Volume** with this plan:

**Phase 1** (Beta): SQLite
- Good enough for <1k sessions
- Single-writer acceptable (low traffic)

**Phase 2** (Growth): Supabase
- Migrate when hitting SQLite limits
- Use pgloader for SQLite → Postgres migration

**Migration cost**: ~2 days engineering time

**Why I still recommend Supabase from Day 1**:
- 2 days saved (no migration)
- Better DX (Studio UI for debugging)
- More features (auth, real-time, storage)
- Same cost ($0 until you scale)

---

## 10. Decision Framework

**Use Supabase if**:
- ✅ You want to ship fast (recommended)
- ✅ You want production-ready from Day 1
- ✅ You plan to use auth/real-time/storage features
- ✅ You're okay with managed service

**Use SQLite on Modal Volume if**:
- ⚠️ You absolutely must avoid external dependencies
- ⚠️ You're willing to migrate later
- ⚠️ You're comfortable with single-writer limits

**Use Modal Dict if**:
- ❌ Never (forces hard migration, no query capabilities)

---

## 11. Recommendation Summary

**Primary Recommendation**: **Supabase**

**Setup timeline**: 3 days
**Migration required**: None (this IS production)
**Cost**: $0 until scale (then $25/mo)
**Risk**: Low (standard Postgres, can migrate if needed)

**Next steps**:
1. Create Supabase project today
2. Run schema SQL (copy from section 4.1)
3. Add supabase-py to Modal image
4. Implement SupabaseSessionStore (copy from section 4.1)
5. Ship to production

**Result**: Production-ready persistence in 3 days, aligned with future architecture, no migration needed.

---

## Appendix A: Supabase Setup Script

```bash
#!/bin/bash
# setup_supabase.sh

# 1. Create project at https://supabase.com (or use CLI)
# supabase projects create lift-sys --org-id <your-org-id>

# 2. Get credentials
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-role-key"  # For migrations only

# 3. Run migrations
supabase db push

# 4. Add to Modal secrets
modal secret create supabase \
  SUPABASE_URL="$SUPABASE_URL" \
  SUPABASE_KEY="$SUPABASE_ANON_KEY"

echo "✅ Supabase setup complete!"
```

## Appendix B: Local Development

```bash
# Use Supabase CLI for local development
supabase start  # Starts local Postgres + Studio

# Run against local Supabase
export SUPABASE_URL="http://localhost:54321"
export SUPABASE_KEY="local-anon-key"

uv run python -m lift_sys.api.server

# Run tests against local DB
uv run pytest
```

## Appendix C: Emergency Rollback Plan

**If Supabase has issues** (unlikely):
1. Implement `InMemorySessionStore` fallback (already exists)
2. Add feature flag: `USE_SUPABASE=false`
3. Sessions lost but service continues
4. Restore from Supabase backup when service recovers

**Supabase SLA** (Pro tier):
- 99.9% uptime guarantee
- <1ms p50 latency
- Point-in-time recovery (7 days)

---

**Status**: Ready to implement
**Recommendation confidence**: High (9/10)
**Risk**: Low
**Time to production**: 3 days
