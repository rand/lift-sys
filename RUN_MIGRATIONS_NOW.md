# Run Supabase Migrations - Quick Guide

**Your Supabase database is ready, now run the migrations to create the schema.**

---

## ✅ Option 1: Python Script (Recommended)

This works without needing `psql` installed:

```bash
cd /Users/rand/src/lift-sys

# Run the migration script
uv run python run_migrations.py
```

**Expected output**:
```
Testing database connection...
✓ Connection successful
PostgreSQL version: PostgreSQL 15.8...

Running migrations...

Running: 001_create_sessions_table.sql
✓ 001_create_sessions_table.sql complete

Running: 002_create_revisions_table.sql
✓ 002_create_revisions_table.sql complete

... (all 7 migrations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All 7 migrations completed successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Tables created: 4
✓ RLS enabled on 4 tables
✓ Views created: 4
```

---

## ✅ Option 2: Bash Script (If you have psql)

If you have PostgreSQL client tools installed:

```bash
cd /Users/rand/src/lift-sys

# Set your database URL
export DATABASE_URL="postgresql://postgres:sgVOFNCgIWk585q8@db.bqokcxjusdkywfgfqhzo.supabase.co:5432/postgres"

# Run migrations
./migrations/run_all_migrations.sh "$DATABASE_URL"
```

---

## ✅ Verify in Supabase Studio

After migrations complete:

1. Go to https://supabase.com/dashboard
2. Click your `lift-sys` project
3. Click **"Table Editor"** in left sidebar
4. You should see 4 tables:
   - `sessions`
   - `session_revisions`
   - `session_drafts`
   - `hole_resolutions`

---

## ✅ Configure Modal Secrets

Once migrations are complete, configure Modal:

```bash
modal secret create supabase \
  SUPABASE_URL="https://bqokcxjusdkywfgfqhzo.supabase.co" \
  SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxb2tjeGp1c2RreXdmZ2ZxaHpvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA4ODEzMjQsImV4cCI6MjA3NjQ1NzMyNH0.jn5ypmawIKs-5oyn3MfrYWe95jfyaQzWLHZpnHWPjBQ" \
  SUPABASE_SERVICE_KEY="***REMOVED***"

# Verify secret exists
modal secret list | grep supabase
```

---

## ✅ Create .env.local (for local development)

```bash
cat > .env.local <<'EOF'
# Supabase credentials (DO NOT COMMIT TO GIT)
SUPABASE_URL=https://bqokcxjusdkywfgfqhzo.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxb2tjeGp1c2RreXdmZ2ZxaHpvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA4ODEzMjQsImV4cCI6MjA3NjQ1NzMyNH0.jn5ypmawIKs-5oyn3MfrYWe95jfyaQzWLHZpnHWPjBQ
SUPABASE_SERVICE_KEY=***REMOVED***
DATABASE_URL=postgresql://postgres:sgVOFNCgIWk585q8@db.bqokcxjusdkywfgfqhzo.supabase.co:5432/postgres
EOF

# Ensure it's in .gitignore
echo ".env.local" >> .gitignore
```

---

## ❌ Troubleshooting

### If migrations fail with "already exists" errors

This means tables already exist. You can either:

1. **Drop all tables and retry** (destructive):
   ```sql
   -- Connect to database and run:
   DROP TABLE IF EXISTS hole_resolutions CASCADE;
   DROP TABLE IF EXISTS session_drafts CASCADE;
   DROP TABLE IF EXISTS session_revisions CASCADE;
   DROP TABLE IF EXISTS sessions CASCADE;
   ```

2. **Or skip migrations** if schema looks correct in Supabase Studio

### If connection times out

- Check your internet connection
- Verify Supabase project is not paused
- Try connection pooler URL (port 6543) instead

### If password error

Double-check password: `sgVOFNCgIWk585q8` (case-sensitive)

---

## ✅ Next Steps After Success

1. **Mark lift-sys-260 complete**:
   ```bash
   bd close lift-sys-260 --reason "Supabase database schema deployed successfully"
   ```

2. **Start lift-sys-261**: Implement SupabaseSessionStore
   - I'll create the Python implementation
   - Add CRUD operations
   - Integrate with existing SessionStore protocol

3. **Verify everything works** by checking tables in Supabase Studio

---

**Run the script now and let me know when migrations complete!**

I'll then proceed with implementing the SupabaseSessionStore class (lift-sys-261).
