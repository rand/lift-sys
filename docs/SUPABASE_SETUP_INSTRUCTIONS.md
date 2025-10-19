# Supabase Setup Instructions

**Task**: lift-sys-260 - Setup Supabase project and database schema
**Time Required**: 15-20 minutes
**Prerequisites**: Web browser, terminal with `psql` installed

---

## ✅ Checklist

- [ ] Create Supabase project via web UI
- [ ] Get connection credentials (URL, API keys, DATABASE_URL)
- [ ] Run database migrations
- [ ] Verify schema in Supabase Studio
- [ ] Test RLS policies
- [ ] Configure Modal secrets
- [ ] Document credentials securely

---

## Step 1: Create Supabase Project (5 min)

1. Go to https://supabase.com/dashboard
2. Sign in or create account (use company email)
3. Click **"New Project"** button
4. Fill in project details:
   - **Name**: `lift-sys`
   - **Database Password**: Click "Generate a password" (SAVE THIS!)
   - **Region**: `us-east-1` (or closest to your users/Modal deployment)
   - **Pricing Plan**: **Free** (sufficient for development)
5. Click **"Create new project"**
6. Wait ~2 minutes for provisioning (progress bar shown)

**Output**: You'll see the project dashboard

---

## Step 2: Get Connection Credentials (3 min)

### 2.1 Get API Credentials

1. In Supabase dashboard, click **"Project Settings"** (gear icon in left sidebar)
2. Navigate to **"API"** section
3. Copy and save these values:

```
Project URL: https://xxxxxxxxxxxxx.supabase.co
anon public: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (long JWT token)
service_role: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (even longer JWT token)
```

**CRITICAL**: Save these to a secure location (password manager, encrypted notes)

### 2.2 Get Database Connection String

1. Still in Project Settings, navigate to **"Database"** section
2. Scroll to **"Connection string"** section
3. Select **"URI"** tab
4. Copy the connection string:

```
postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

5. Replace `[YOUR-PASSWORD]` with the database password you generated in Step 1
6. Save this as `DATABASE_URL`

**Example**:
```bash
DATABASE_URL="postgresql://postgres.abcdefghijklmno:MySecurePassword123!@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

---

## Step 3: Verify psql Installation (2 min)

Check if `psql` is installed:

```bash
psql --version
```

**Expected output**: `psql (PostgreSQL) 15.x` or similar

**If not installed**:

**macOS**:
```bash
brew install postgresql@15
# Add to PATH if needed
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install postgresql-client-15
```

**Windows**:
- Download from https://www.postgresql.org/download/windows/
- Or use WSL and follow Ubuntu instructions

---

## Step 4: Run Database Migrations (5 min)

### 4.1 Test Connection

```bash
# Set DATABASE_URL (replace with your actual connection string)
export DATABASE_URL="postgresql://postgres.abcdefghijklmno:MyPassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# Test connection
psql "$DATABASE_URL" -c "SELECT 1"
```

**Expected output**:
```
 ?column?
----------
        1
(1 row)
```

**If connection fails**:
- Check password is correct
- Verify no quotes/spaces in DATABASE_URL
- Check firewall allows port 6543

### 4.2 Run All Migrations

```bash
# Navigate to project root
cd /Users/rand/src/lift-sys

# Run migration script
./migrations/run_all_migrations.sh "$DATABASE_URL"
```

**Expected output**:
```
Testing database connection...
✓ Connection successful

Running migrations...

Running: 001_create_sessions_table.sql
✓ 001_create_sessions_table.sql complete

Running: 002_create_revisions_table.sql
✓ 002_create_revisions_table.sql complete

... (all 7 migrations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All migrations completed successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Verifying schema...
✓ Tables created: 4
✓ RLS enabled on 4 tables
✓ Views created: 4
```

**If migrations fail**:
- Check error message
- Verify psql version ≥15
- Run failing migration manually: `psql "$DATABASE_URL" -f migrations/XXX.sql`
- Check Supabase dashboard for existing tables (may need to drop and retry)

---

## Step 5: Verify Schema in Supabase Studio (3 min)

1. Go back to Supabase dashboard
2. Click **"Table Editor"** in left sidebar
3. You should see 4 tables:
   - `sessions`
   - `session_revisions`
   - `session_drafts`
   - `hole_resolutions`

4. Click on `sessions` table
5. Verify columns exist:
   - id, user_id, status, source, original_input, current_ir, current_code
   - revision_count, draft_count, hole_count
   - metadata, created_at, updated_at, finalized_at

6. Check RLS is enabled (you'll see a shield icon 🛡️ next to table name)

---

## Step 6: Test RLS Policies (2 min)

### 6.1 Test with anon key (should be restricted)

Create `test_rls.py`:

```python
from supabase import create_client

# Use anon key (should enforce RLS)
SUPABASE_URL = "https://xxxxxxxxxxxxx.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGci..."  # Your anon public key

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# This should return empty (no auth context)
result = supabase.table("sessions").select("*").execute()
print(f"Rows returned with anon key (should be 0): {len(result.data)}")

# This should fail (no user_id in auth context)
try:
    supabase.table("sessions").insert({"user_id": "test-user", "status": "active", "source": "prompt", "original_input": "test"}).execute()
    print("ERROR: Insert should have failed without auth!")
except Exception as e:
    print(f"✓ RLS working: Insert blocked - {type(e).__name__}")
```

Run:
```bash
uv add supabase
uv run python test_rls.py
```

**Expected output**:
```
Rows returned with anon key (should be 0): 0
✓ RLS working: Insert blocked - APIError
```

### 6.2 Test with service_role key (should bypass RLS)

```python
from supabase import create_client
import uuid

# Use service_role key (bypasses RLS)
SUPABASE_URL = "https://xxxxxxxxxxxxx.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGci..."  # Your service_role key

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Insert test session (should succeed)
test_session = {
    "id": str(uuid.uuid4()),
    "user_id": str(uuid.uuid4()),
    "status": "active",
    "source": "prompt",
    "original_input": "Test prompt"
}

result = supabase.table("sessions").insert(test_session).execute()
print(f"✓ Insert succeeded with service_role key")

# Query should return the session
sessions = supabase.table("sessions").select("*").execute()
print(f"✓ Query returned {len(sessions.data)} sessions")

# Cleanup
supabase.table("sessions").delete().eq("id", test_session["id"]).execute()
print(f"✓ Cleanup complete")
```

**Expected output**:
```
✓ Insert succeeded with service_role key
✓ Query returned 1 sessions
✓ Cleanup complete
```

---

## Step 7: Configure Modal Secrets (3 min)

```bash
# Create Modal secret with Supabase credentials
modal secret create supabase \
  SUPABASE_URL="https://xxxxxxxxxxxxx.supabase.co" \
  SUPABASE_ANON_KEY="eyJhbGci..." \
  SUPABASE_SERVICE_KEY="eyJhbGci..."

# Verify secret exists
modal secret list | grep supabase
```

**Expected output**:
```
supabase    3 values    <timestamp>
```

**Note**: We'll use `SUPABASE_SERVICE_KEY` in Modal backend (bypasses RLS for backend operations)

---

## Step 8: Document Credentials (2 min)

Create `.env.local` file (DO NOT COMMIT):

```bash
# Supabase credentials (DO NOT COMMIT TO GIT)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_KEY=eyJhbGci...
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

Add to `.gitignore`:
```bash
echo ".env.local" >> .gitignore
```

Store backup copy in password manager or team secrets vault.

---

## Verification Checklist

Before marking lift-sys-260 complete, verify:

- [x] Supabase project created (free tier)
- [x] Database password saved securely
- [x] API keys (anon, service_role) saved
- [x] DATABASE_URL saved
- [x] `psql` installed and working
- [x] All 7 migrations ran successfully
- [x] 4 tables visible in Supabase Studio
- [x] RLS enabled (shield icon on tables)
- [x] RLS test passed (anon key blocked)
- [x] Service role test passed (bypassed RLS)
- [x] Modal secrets configured
- [x] Credentials documented in `.env.local`
- [x] `.env.local` added to `.gitignore`

---

## Next Steps

After completing this setup:

1. **Mark lift-sys-260 complete**:
   ```bash
   bd close lift-sys-260 --reason "Supabase project created, schema deployed, RLS verified"
   ```

2. **Start lift-sys-261**: Implement SupabaseSessionStore
   - Create `lift_sys/storage/supabase_store.py`
   - Implement SessionStore protocol
   - Add CRUD operations with RLS

3. **Reference**: See SUPABASE_INTEGRATION_PLAN.md Section 5 for SupabaseSessionStore implementation

---

## Troubleshooting

### Connection timeout
**Problem**: `psql` hangs or times out

**Solutions**:
- Check firewall allows port 6543
- Try pooler vs direct connection (Supabase provides both)
- Verify region matches (e.g., `us-east-1`)

### RLS not working
**Problem**: anon key can access all data

**Solutions**:
- Verify RLS is enabled: `SELECT * FROM pg_tables WHERE tablename = 'sessions' AND rowsecurity = true`
- Check policies exist: `SELECT * FROM pg_policies WHERE tablename = 'sessions'`
- Re-run migration 005: `psql "$DATABASE_URL" -f migrations/005_create_rls_policies.sql`

### Migrations fail mid-way
**Problem**: Some migrations succeed, others fail

**Solutions**:
- Note which migration failed
- Check Supabase logs (Dashboard → Database → Logs)
- Drop failed tables: `DROP TABLE IF EXISTS <table> CASCADE`
- Re-run from failed migration

### Can't find API keys
**Problem**: Lost anon or service_role keys

**Solutions**:
- Go to Project Settings → API
- Keys are always visible (can regenerate if needed)
- Service role key is shown at bottom of page

---

## Support

- Supabase Docs: https://supabase.com/docs
- Supabase Discord: https://discord.supabase.com
- PostgreSQL Docs: https://www.postgresql.org/docs/
- lift-sys Beads: lift-sys-260

---

**Status**: Ready to execute
**Estimated Time**: 15-20 minutes
**Next Task**: lift-sys-261 (Implement SupabaseSessionStore)
