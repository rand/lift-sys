# Supabase Connection Troubleshooting

**Issue**: Cannot connect to Supabase database
**Date**: 2025-10-19

---

## Quick Diagnostics

### Step 1: Get the Correct Connection String

Supabase provides **two types** of connection strings - make sure you're using the right one:

#### Option A: Connection Pooler (Recommended - Port 6543)

1. Go to Supabase Dashboard → Project Settings → Database
2. Scroll to "Connection string" section
3. Click **"Connection Pooling"** tab (not "Direct connection")
4. Select **"URI"** mode
5. Copy the string - it should look like:

```
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
```

**Key indicators**:
- Port **6543** (pooler)
- Contains `.pooler.supabase.com`
- Mode: "Transaction" (default)

#### Option B: Direct Connection (Port 5432)

If pooler doesn't work, try direct connection:

1. Same location (Project Settings → Database)
2. Click **"Direct connection"** tab
3. Select **"URI"** mode
4. Copy the string - it should look like:

```
postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
```

**Key indicators**:
- Port **5432** (direct)
- Contains `db.PROJECT_REF.supabase.co`

---

## Step 2: Fix the Password

The connection string has `[YOUR-PASSWORD]` placeholder. Replace it with your actual database password:

### If you saved the password:
```bash
# Replace [YOUR-PASSWORD] with actual password
DATABASE_URL="postgresql://postgres.abcdefgh:MyActualPassword123@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

### If you forgot the password:
1. Go to Supabase Dashboard → Project Settings → Database
2. Scroll to "Database password" section
3. Click **"Reset database password"**
4. Generate new password and **save it this time**
5. Update connection string

---

## Step 3: Test Connection with psql

### Test basic connectivity:

```bash
# Set the DATABASE_URL (with actual password)
export DATABASE_URL="postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres"

# Test connection
psql "$DATABASE_URL" -c "SELECT version();"
```

**Expected output**:
```
                                                 version
---------------------------------------------------------------------------------------------------------
 PostgreSQL 15.x on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 9.4.0-1ubuntu1~20.04) 9.4.0, 64-bit
(1 row)
```

**If this fails**, try these fixes:

### Fix 1: Check psql is installed
```bash
psql --version
```

If not installed:
- **macOS**: `brew install libpq` then `brew link --force libpq`
- **Ubuntu**: `sudo apt-get install postgresql-client`

### Fix 2: Try without SSL (for testing only)
```bash
psql "$DATABASE_URL?sslmode=disable" -c "SELECT 1;"
```

### Fix 3: Try direct connection instead of pooler
```bash
# Switch from port 6543 to 5432
DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres"
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Fix 4: Check for special characters in password

If your password has special characters like `@`, `$`, `#`, `:`, `/`, you need to URL-encode them:

**Common URL encodings**:
- `@` → `%40`
- `$` → `%24`
- `#` → `%23`
- `:` → `%3A`
- `/` → `%2F`
- `%` → `%25`
- Space → `%20`

**Example**:
```bash
# Original password: MyP@ss$123
# Encoded password: MyP%40ss%2124
DATABASE_URL="postgresql://postgres.ref:MyP%40ss%2124@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

**Or quote the entire URL**:
```bash
DATABASE_URL='postgresql://postgres.ref:MyP@ss$123@aws-0-us-east-1.pooler.supabase.com:6543/postgres'
psql "$DATABASE_URL" -c "SELECT 1;"
```

---

## Step 4: Verify Project Details

Make sure these match your actual Supabase project:

1. **Project Reference ID** (`PROJECT_REF`):
   - Go to Supabase Dashboard → Project Settings → General
   - Copy "Reference ID" (e.g., `abcdefghijklmno`)
   - Should be in the connection string

2. **Region**:
   - Check Project Settings → General → Region
   - Should match in connection string (e.g., `us-east-1`, `eu-west-1`)

3. **Database Name**:
   - Default is `postgres` - don't change this

---

## Step 5: Test from Python

Once psql works, test from Python:

```python
# test_supabase_connection.py
import os
import sys

# Test 1: Check psycopg2 is installed
try:
    import psycopg2
    print("✓ psycopg2 installed")
except ImportError:
    print("✗ psycopg2 not installed")
    print("  Install: pip install psycopg2-binary")
    sys.exit(1)

# Test 2: Connect with psycopg2
DATABASE_URL = "postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"✓ psycopg2 connection successful")
    print(f"  PostgreSQL version: {version}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"✗ psycopg2 connection failed: {e}")
    sys.exit(1)

# Test 3: Check supabase-py is installed
try:
    from supabase import create_client
    print("✓ supabase-py installed")
except ImportError:
    print("✗ supabase-py not installed")
    print("  Install: pip install supabase")
    sys.exit(1)

# Test 4: Connect with supabase-py
SUPABASE_URL = "https://PROJECT_REF.supabase.co"
SUPABASE_KEY = "YOUR_ANON_KEY"  # From Project Settings → API

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Simple query (won't work if no tables, but tests connection)
    result = supabase.table("_supabase_migrations").select("*").limit(1).execute()
    print(f"✓ supabase-py connection successful")
except Exception as e:
    print(f"✗ supabase-py connection failed: {e}")
    # This might fail if no tables exist yet - that's OK for now

print("\n✅ All connection tests passed!")
```

Run:
```bash
python test_supabase_connection.py
```

---

## Step 6: Run Migrations

Once connection works, run migrations:

```bash
# Navigate to project
cd /Users/rand/src/lift-sys

# Run migrations
./migrations/run_all_migrations.sh "$DATABASE_URL"
```

**If migrations fail with "permission denied"**:
```bash
chmod +x migrations/run_all_migrations.sh
./migrations/run_all_migrations.sh "$DATABASE_URL"
```

---

## Common Error Messages

### Error: "could not connect to server: Connection refused"

**Cause**: Wrong host, port, or firewall blocking

**Fix**:
1. Check firewall allows outbound connection to port 6543 (pooler) or 5432 (direct)
2. Verify host is correct: `aws-0-REGION.pooler.supabase.com` or `db.PROJECT_REF.supabase.co`
3. Try switching between pooler (6543) and direct (5432)

### Error: "FATAL: password authentication failed"

**Cause**: Wrong password

**Fix**:
1. Verify password is correct (copy-paste from saved location)
2. Check for special characters that need URL encoding
3. Reset password in Supabase dashboard if needed
4. Ensure no extra spaces before/after password

### Error: "FATAL: database does not exist"

**Cause**: Wrong database name

**Fix**:
- Use `postgres` as database name (default)
- Don't use custom database names with Supabase

### Error: "connection timeout"

**Cause**: Network issue, wrong region, or Supabase outage

**Fix**:
1. Check Supabase status: https://status.supabase.com
2. Verify region in connection string matches project region
3. Try from different network (e.g., phone hotspot to rule out firewall)
4. Check if VPN is interfering

### Error: "SSL connection required"

**Cause**: Supabase requires SSL by default

**Fix**:
- Don't use `sslmode=disable` in production
- Ensure psql/psycopg2 supports SSL (should be default)
- If using pooler, SSL is handled automatically

---

## Interactive Troubleshooting

**Tell me which error you're seeing** and I can provide specific fixes:

1. What's the exact error message from `psql`?
2. Are you using pooler (port 6543) or direct (port 5432)?
3. Does your password have special characters?
4. Which region is your Supabase project in?

---

## Quick Reference: Connection String Anatomy

```
postgresql://USER:PASSWORD@HOST:PORT/DATABASE
           ↑    ↑         ↑    ↑    ↑
           |    |         |    |    └─ Database name (always "postgres")
           |    |         |    └────── Port: 6543 (pooler) or 5432 (direct)
           |    |         └─────────── Host: varies by method
           |    └───────────────────── Your database password
           └────────────────────────── Username (always "postgres")
```

**Pooler example**:
```
postgresql://postgres.abcdefgh:MyPass123@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Direct example**:
```
postgresql://postgres:MyPass123@db.abcdefgh.supabase.co:5432/postgres
```

---

## Next Steps After Connection Works

1. Run migrations: `./migrations/run_all_migrations.sh "$DATABASE_URL"`
2. Verify tables in Supabase Studio (Dashboard → Table Editor)
3. Configure Modal secrets
4. Test supabase-py connection
5. Continue with lift-sys-261 (SupabaseSessionStore implementation)

---

**Need more help?** Provide:
- Exact error message
- Connection string (with password redacted)
- Output of `psql --version`
- Your OS (macOS/Linux/Windows)
