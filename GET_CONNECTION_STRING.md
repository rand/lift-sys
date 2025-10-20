# Get Correct Connection String from Supabase

You're absolutely right - after hours, this isn't a DNS propagation issue.

**The problem**: We've been guessing at the connection string format. We need the ACTUAL connection string from your Supabase dashboard.

---

## Step 1: Get Connection String from Dashboard

1. **Go to your project settings**:
   https://supabase.com/dashboard/project/bqokcxjusdkywfgfqhzo/settings/database

2. **Scroll down to "Connection string" section**

3. **You'll see two tabs**:
   - "Connection Pooling" (RECOMMENDED)
   - "Direct connection"

4. **Click "Connection Pooling" tab**

5. **Select "URI" mode** (not PSQL or JDBC)

6. **Copy the EXACT string shown**

It should look something like:
```
postgresql://postgres.bqokcxjusdkywfgfqhzo:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:6543/postgres
```

**Key details**:
- The host format is likely: `aws-0-[REGION].pooler.supabase.com`
- NOT `db.bqokcxjusdkywfgfqhzo.supabase.co` (that doesn't exist)
- Region could be: us-east-1, us-west-1, eu-west-1, ap-southeast-1, etc.

7. **Replace `[YOUR-PASSWORD]` with**: `sgVOFNCgIWk585q8`

---

## Step 2: Test Connection

Once you have the correct connection string:

```bash
# Set it
export DATABASE_URL="<paste the actual connection string here>"

# Test with psycopg2
uv run python -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cursor = conn.cursor()
cursor.execute('SELECT version();')
print('✓ Connection works!')
print(cursor.fetchone()[0])
conn.close()
"
```

---

## Step 3: Run Migrations

Once connection test passes:

```bash
# Update the DATABASE_URL in run_migrations.py
# Then run:
uv run python run_migrations.py
```

---

## Alternative: Just Paste the Connection String Here

If you paste the exact connection string from your dashboard (with `[YOUR-PASSWORD]` placeholder still in it), I can:
1. Update all the migration scripts
2. Run the migrations immediately
3. Proceed to implementing SupabaseSessionStore

**What I need**:
The exact string from: Dashboard → Settings → Database → Connection Pooling → URI mode

It should be one line starting with `postgresql://`
