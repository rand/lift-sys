# Supabase Migration Options - Choose Your Path

**Good news**: Your Supabase project is fully provisioned and the API is working!

**Issue**: We have the `anon` key, but migrations require the `service_role` key.

---

## ✅ Option 1: SQL Editor in Dashboard (EASIEST - 5 minutes)

**No additional credentials needed. Use this if you want to proceed immediately.**

### Steps:

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard/project/bqokcxjusdkywfgfqhzo

2. **Click "SQL Editor"** in left sidebar

3. **Click "New query"** button

4. **Run each migration** (in order):

#### Migration 1: Sessions Table
```sql
-- Copy entire contents of migrations/001_create_sessions_table.sql
-- Paste here and click "Run"
```

#### Migration 2: Revisions Table
```sql
-- Copy entire contents of migrations/002_create_revisions_table.sql
-- Paste here and click "Run"
```

#### Migration 3: Drafts Table
```sql
-- Copy entire contents of migrations/003_create_drafts_table.sql
-- Paste here and click "Run"
```

#### Migration 4: Resolutions Table
```sql
-- Copy entire contents of migrations/004_create_resolutions_table.sql
-- Paste here and click "Run"
```

#### Migration 5: RLS Policies
```sql
-- Copy entire contents of migrations/005_create_rls_policies.sql
-- Paste here and click "Run"
```

#### Migration 6: Triggers
```sql
-- Copy entire contents of migrations/006_create_triggers.sql
-- Paste here and click "Run"
```

#### Migration 7: Views
```sql
-- Copy entire contents of migrations/007_create_views.sql
-- Paste here and click "Run"
```

5. **Verify in Table Editor**:
   - Click "Table Editor" in left sidebar
   - You should see 4 tables: `sessions`, `session_revisions`, `session_drafts`, `hole_resolutions`

---

## ✅ Option 2: Get Service Role Key (AUTOMATED - 2 minutes)

**Use this if you want to run migrations via Python script.**

### Steps:

1. **Get service_role key**:
   - Go to: https://supabase.com/dashboard/project/bqokcxjusdkywfgfqhzo/settings/api
   - Scroll to "Project API keys"
   - Find **"service_role"** (NOT "anon")
   - Copy the secret key (starts with `eyJhbGci...`)

2. **Update the migration script**:
   ```bash
   # Edit run_migrations_supabase_sdk.py
   # Replace SUPABASE_KEY with your service_role key
   ```

3. **Run migrations**:
   ```bash
   uv run python run_migrations_supabase_sdk.py
   ```

**Warning**: Service role key bypasses Row Level Security. Keep it secret!

---

## ✅ Option 3: Direct PostgreSQL Connection (IF YOU HAVE PSQL)

**Use this if you have `psql` installed and want direct database access.**

### Prerequisites:
- `psql` must be installed (`brew install libpq` on macOS)

### Steps:

1. **Get direct connection string**:
   - Go to: https://supabase.com/dashboard/project/bqokcxjusdkywfgfqhzo/settings/database
   - Scroll to "Connection string"
   - Click **"Direct connection"** tab (NOT "Connection pooling")
   - Select "URI" mode
   - Copy the connection string
   - Get password from Supabase dashboard

2. **Test connection**:
   ```bash
   export DATABASE_URL="<paste your connection string here>"
   psql "$DATABASE_URL" -c "SELECT version();"
   ```

3. **Run migrations**:
   ```bash
   ./migrations/run_all_migrations.sh "$DATABASE_URL"
   ```

**Note**: This bypasses the DNS issue we had earlier because we're now using the connection pooler or a different hostname format.

---

## 🎯 Recommendation

**Use Option 1 (SQL Editor)** if you want to proceed right now without any additional setup.

**Use Option 2 (Service Role Key)** if you want automated migrations and will deploy this to Modal later.

---

## After Migrations Complete

Once migrations are done (via any option), verify and proceed:

1. **Verify schema**:
   - Dashboard → Table Editor → See 4 tables
   - Check that RLS is enabled on each table

2. **Update Modal secrets** (for production deployment):
   ```bash
   modal secret create supabase \
     SUPABASE_URL="https://bqokcxjusdkywfgfqhzo.supabase.co" \
     SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     SUPABASE_SERVICE_KEY="<your service role key>"
   ```

3. **Proceed to lift-sys-261**: Implement SupabaseSessionStore class

---

## Which option do you want to use?

Let me know and I'll help you through it!
