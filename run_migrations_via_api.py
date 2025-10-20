#!/usr/bin/env python3
"""
Run Supabase migrations via HTTP API using service_role key
This bypasses DNS issues by using the REST API endpoint
"""

import sys
from pathlib import Path

import httpx

# Supabase credentials
SUPABASE_URL = "https://bqokcxjusdkywfgfqhzo.supabase.co"
SERVICE_ROLE_KEY = "***REMOVED***"

# Colors for output
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def execute_sql_via_api(sql: str) -> dict:
    """
    Execute raw SQL via Supabase REST API using pg_net or similar

    Note: Standard Supabase REST API (PostgREST) doesn't support raw SQL execution.
    We need to use one of these approaches:
    1. Supabase Management API (requires separate API key)
    2. Database webhooks/functions
    3. Manual execution via SQL Editor in dashboard

    For now, this will demonstrate the API call pattern.
    """
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    # Try to use the database REST API
    # Note: This likely won't work for DDL operations
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"

    try:
        response = httpx.post(url, headers=headers, json={"query": sql}, timeout=30.0)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    print(f"{YELLOW}Checking Supabase API connectivity...{NC}")

    # Test basic API connectivity
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    }

    try:
        # Test REST API endpoint
        response = httpx.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=10.0)
        response.raise_for_status()
        print(f"{GREEN}✓ Supabase REST API is accessible{NC}")
        print(f"Project URL: {SUPABASE_URL}\n")
    except Exception as e:
        print(f"{RED}✗ API connection failed: {e}{NC}\n")
        sys.exit(1)

    # Important limitation
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{YELLOW}IMPORTANT: API Limitations{NC}")
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    print("The Supabase REST API (PostgREST) does NOT support raw SQL execution.")
    print("It's designed for CRUD operations on existing tables, not DDL.\n")

    print(f"{YELLOW}To run migrations, you have 3 options:{NC}\n")

    print(f"{GREEN}Option 1: SQL Editor in Dashboard (RECOMMENDED){NC}")
    print("  1. Go to: https://supabase.com/dashboard/project/bqokcxjusdkywfgfqhzo")
    print("  2. Click 'SQL Editor' in sidebar")
    print("  3. Click 'New query'")
    print("  4. Paste each migration file contents")
    print("  5. Click 'Run'\n")

    print(f"{GREEN}Option 2: Supabase CLI{NC}")
    print("  1. Install: brew install supabase/tap/supabase")
    print("  2. Login: supabase login")
    print("  3. Link: supabase link --project-ref bqokcxjusdkywfgfqhzo")
    print("  4. Run: supabase db push\n")

    print(f"{GREEN}Option 3: Wait for DNS propagation{NC}")
    print("  The db.bqokcxjusdkywfgfqhzo.supabase.co hostname should")
    print("  resolve within 24 hours. Then use run_migrations.py\n")

    # List migration files
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = [
        "001_create_sessions_table.sql",
        "002_create_revisions_table.sql",
        "003_create_drafts_table.sql",
        "004_create_resolutions_table.sql",
        "005_create_rls_policies.sql",
        "006_create_triggers.sql",
        "007_create_views.sql",
    ]

    print(f"{YELLOW}Migration files ready at:{NC}")
    for migration_name in migration_files:
        migration_path = migrations_dir / migration_name
        if migration_path.exists():
            size = migration_path.stat().st_size
            print(f"  ✓ {migration_path} ({size:,} bytes)")
        else:
            print(f"  ✗ {migration_path} (NOT FOUND)")

    print(f"\n{YELLOW}Recommended: Use SQL Editor (Option 1) - takes ~5 minutes{NC}\n")


if __name__ == "__main__":
    main()
