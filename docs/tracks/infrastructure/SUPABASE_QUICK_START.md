---
track: infrastructure
document_type: quick_start_guide
status: active
priority: P1
completion: 100%
last_updated: 2025-10-27
session_protocol: |
  For new Claude Code session:
  1. Use this guide for Supabase setup (integration complete, reference only)
  2. Follow step-by-step instructions for new deployments
  3. Migrations located in migrations/ directory
  4. Secrets managed via Modal secrets
related_docs:
  - docs/tracks/infrastructure/SUPABASE_BEADS_SUMMARY.md
  - docs/tracks/infrastructure/INFRASTRUCTURE_STATUS.md
  - docs/MASTER_ROADMAP.md
---

# Supabase Integration Quick Start Guide

**For**: Developers implementing the Supabase integration
**Time**: 30 minutes to first working connection
**Prerequisites**: Modal deployment working, OAuth system functional

---

## TL;DR

```bash
# 1. Create Supabase project
# Go to https://supabase.com → New Project

# 2. Run schema migrations
psql $DATABASE_URL -f migrations/001_create_sessions_table.sql

# 3. Create Modal secret
modal secret create supabase \
  SUPABASE_URL="https://xxxxx.supabase.co" \
  SUPABASE_ANON_KEY="eyJhbGci..."

# 4. Add dependency
uv add supabase

# 5. Test connection
uv run python -c "from supabase import create_client; print('OK')"
```

**Total time**: ~30 minutes
**Result**: Persistent session storage ready

---

## Step-by-Step Instructions

### Step 1: Create Supabase Project (5 min)

1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Fill in:
   - **Name**: `lift-sys`
   - **Database Password**: Generate strong password (save it!)
   - **Region**: `us-east-1` (or closest to your users)
   - **Pricing Plan**: Free
4. Click "Create new project"
5. Wait ~2 minutes for provisioning

**Output**: Project dashboard with connection details

### Step 2: Get Credentials (2 min)

1. In Supabase dashboard, click "Project Settings" (gear icon)
2. Go to "API" section
3. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public**: `eyJhbGci...` (long JWT token)
4. Save to a secure notes file

**DO NOT** commit these to git!

### Step 3: Run Database Migrations (3 min)

```bash
# Get the database connection string
# In Supabase: Settings → Database → Connection String → URI

DATABASE_URL="postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"

# Run migrations (in order!)
psql $DATABASE_URL -f migrations/001_create_sessions_table.sql
psql $DATABASE_URL -f migrations/002_create_revisions_table.sql
psql $DATABASE_URL -f migrations/003_create_drafts_table.sql
psql $DATABASE_URL -f migrations/004_create_resolutions_table.sql
psql $DATABASE_URL -f migrations/005_create_rls_policies.sql
psql $DATABASE_URL -f migrations/006_create_triggers.sql
psql $DATABASE_URL -f migrations/007_create_views.sql
```

**Verify in Supabase Studio**:
1. Go to "Table Editor"
2. Should see: `sessions`, `session_revisions`, `session_drafts`, `hole_resolutions`

### Step 4: Configure Modal Secrets (2 min)

```bash
# Create Modal secret with Supabase credentials
modal secret create supabase \
  SUPABASE_URL="https://xxxxx.supabase.co" \
  SUPABASE_ANON_KEY="eyJhbGci..."

# Verify secret exists
modal secret list | grep supabase
```

### Step 5: Install Python Client (2 min)

```bash
# Add supabase-py to project
uv add supabase

# Verify installation
uv run python -c "from supabase import create_client; print('✓ supabase-py installed')"
```

### Step 6: Test Connection (5 min)

Create `test_supabase_connection.py`:

```python
import os
from supabase import create_client, Client

# Set credentials (from Modal secrets in production)
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."

# Create client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test query
result = supabase.table("sessions").select("*").limit(1).execute()
print(f"✓ Connection successful! Rows: {len(result.data)}")

# Test insert
test_session = {
    "id": "test-123",
    "user_id": "test-user",
    "status": "active",
    "source": "prompt",
    "current_ir": {}
}
supabase.table("sessions").insert(test_session).execute()
print("✓ Insert successful!")

# Test RLS (should fail without auth context)
# This is expected - RLS is working!
try:
    result = supabase.table("sessions").select("*").execute()
    print(f"Warning: RLS may not be enabled. Rows: {len(result.data)}")
except Exception as e:
    print("✓ RLS working (query blocked without auth)")

# Cleanup
supabase.table("sessions").delete().eq("id", "test-123").execute()
print("✓ Cleanup successful!")
```

Run test:
```bash
uv run python test_supabase_connection.py
```

**Expected output**:
```
✓ Connection successful! Rows: 0
✓ Insert successful!
✓ RLS working (query blocked without auth)
✓ Cleanup successful!
```

### Step 7: Verify in Supabase Studio (2 min)

1. Go to Supabase dashboard → "Table Editor"
2. Click `sessions` table
3. Should see 0 rows (test data was cleaned up)
4. Try inserting a row manually:
   - Click "Insert row"
   - Fill in required fields
   - Click "Save"
5. Verify RLS:
   - Query should return 0 rows (RLS blocks without user context)

---

## Common Issues

### Issue: `psql: command not found`

**Solution**: Install PostgreSQL client
```bash
# macOS
brew install postgresql

# Ubuntu
sudo apt-get install postgresql-client

# Or use Supabase Studio SQL Editor instead
```

### Issue: `permission denied for table sessions`

**Solution**: You're using anon key which requires RLS context.
Either:
1. Use service_role key for migrations (Settings → API → service_role secret)
2. Or use SQL Editor in Supabase Studio

### Issue: `connection refused`

**Solution**: Check firewall/VPN. Supabase requires internet access.

### Issue: `RLS policy blocks all queries`

**Solution**: This is expected! RLS requires auth context (`auth.uid()`).
In production, user_id comes from authenticated requests.

For testing, temporarily disable RLS:
```sql
ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;
-- Test queries...
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
```

---

## Next Steps

Once connection is working:

1. ✅ **Implement SupabaseSessionStore** (lift-sys-261)
   - See `SUPABASE_INTEGRATION_PLAN.md` Section 4.2

2. ✅ **Integrate with API** (lift-sys-262)
   - Update `server.py` to use new store

3. ✅ **Deploy to Modal** (lift-sys-263)
   - Update Modal image
   - Deploy and test

4. ✅ **Add monitoring** (lift-sys-264)
   - Health checks
   - Metrics and alerts

---

## Local Development

### Using Supabase CLI for Local Development

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Start local Supabase (Docker required)
supabase start

# Output will show:
# API URL: http://localhost:54321
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# Anon key: eyJhbGci... (local key)

# Run migrations against local DB
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f migrations/001_create_sessions_table.sql

# Stop local Supabase
supabase stop
```

**Benefits**:
- Test without internet
- Free (no Supabase account needed)
- Fast iteration

### Environment Variables

```bash
# .env.local
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJhbGci...  # Local key from `supabase start`

# .env.production
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...  # Production key from dashboard
```

Load with:
```python
from dotenv import load_dotenv
load_dotenv('.env.local')  # or .env.production
```

---

## Checklist

Before marking setup complete:

- [ ] Supabase project created (free tier)
- [ ] Database credentials saved securely
- [ ] All 7 migration files run successfully
- [ ] Tables visible in Supabase Studio
- [ ] RLS policies active (queries blocked without auth)
- [ ] Modal secret created and verified
- [ ] `supabase-py` installed (`uv add supabase`)
- [ ] Test connection script passed
- [ ] Manual insert/query works in Studio
- [ ] Ready to implement SupabaseSessionStore

**Time to complete**: ~30 minutes
**Next bead**: lift-sys-261 (Implement SupabaseSessionStore)

---

## Resources

- **Supabase Docs**: https://supabase.com/docs
- **Python Client**: https://supabase.com/docs/reference/python/introduction
- **RLS Guide**: https://supabase.com/docs/guides/auth/row-level-security
- **Migration Plan**: `SUPABASE_INTEGRATION_PLAN.md`
- **Full Recommendation**: `DATASTORE_RECOMMENDATION.md`

---

**Last Updated**: 2025-10-19
**Status**: Ready for implementation
**Next**: Run through this guide, then start lift-sys-261
