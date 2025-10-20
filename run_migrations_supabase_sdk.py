#!/usr/bin/env python3
"""
Run Supabase migrations using the Supabase Python SDK
This bypasses DNS issues by using the REST API
"""

import sys
from pathlib import Path

from supabase import Client, create_client

# Supabase credentials
SUPABASE_URL = "https://bqokcxjusdkywfgfqhzo.supabase.co"
# Using service_role key for migrations (bypasses RLS)
SUPABASE_KEY = "***REMOVED***"

# Colors for output
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def run_migration_via_rpc(client: Client, migration_file: Path) -> bool:
    """
    Run a single migration file via Supabase RPC

    Note: This uses the PostgREST API which may have limitations.
    The anon key may not have permissions to create tables directly.
    We'll need to use the service_role key or execute via SQL editor.
    """
    print(f"{YELLOW}Running: {migration_file.name}{NC}")

    with open(migration_file) as f:
        sql = f.read()

    try:
        # Try to execute via RPC
        # Note: This will likely fail with anon key - we need service_role key
        result = client.rpc("exec_sql", {"sql": sql}).execute()
        print(f"{GREEN}✓ {migration_file.name} complete{NC}\n")
        return True
    except Exception as e:
        print(f"{RED}✗ {migration_file.name} failed{NC}")
        print(f"Error: {e}\n")
        return False


def main():
    print(f"{YELLOW}Testing Supabase connection...{NC}")

    # Test connection using Supabase SDK
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"{GREEN}✓ Supabase client created{NC}")
        print(f"Project URL: {SUPABASE_URL}\n")

        # Try to query a system table to verify connection
        # Note: With anon key, we may not have permissions for schema operations
        result = supabase.table("_supabase_migrations").select("*").limit(1).execute()
        print(f"{GREEN}✓ Successfully connected to Supabase{NC}\n")
    except Exception as e:
        error_msg = str(e)
        if "PGRST205" in error_msg or "Could not find the table" in error_msg:
            # This actually means connection WORKED but table doesn't exist
            print(
                f"{YELLOW}⚠ Note: _supabase_migrations table doesn't exist yet (expected for new project){NC}\n"
            )
            print(f"{GREEN}✓ Connection successful! API is responding{NC}\n")
        elif "anon" in error_msg.lower() or "permission" in error_msg.lower():
            print(f"{RED}✗ Permission denied with anon key{NC}")
            print(f"\n{YELLOW}This is expected - anon key has limited permissions.{NC}")
            print(f"{YELLOW}For migrations, we need the service_role key (not anon key).{NC}\n")
            print(f"{GREEN}✓ But connection to Supabase is working!{NC}\n")
        else:
            print(f"{RED}✗ Connection failed: {e}{NC}\n")
            sys.exit(1)

    # Important note about permissions
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{YELLOW}IMPORTANT: Running migrations via Supabase SDK{NC}")
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    print("The anon key has limited permissions (respects RLS policies).")
    print("To run migrations (CREATE TABLE, etc.), we need either:")
    print("  1. service_role key (bypasses RLS)")
    print("  2. Direct PostgreSQL connection (psycopg2)")
    print("  3. SQL Editor in Supabase Dashboard\n")

    print(f"{YELLOW}Recommended approach:{NC}")
    print("  1. Go to Supabase Dashboard → SQL Editor")
    print("  2. Click 'New query'")
    print("  3. Paste contents of each migration file (001-007)")
    print("  4. Click 'Run' for each one\n")

    print(f"{YELLOW}Or provide service_role key to this script{NC}")
    print("  (Found in: Project Settings → API → Project API keys → service_role)\n")

    # Migration files in order
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
            print(f"  ✓ {migration_path}")
        else:
            print(f"  ✗ {migration_path} (NOT FOUND)")

    print(f"\n{YELLOW}To continue: Get service_role key and update SUPABASE_KEY in this script{NC}")


if __name__ == "__main__":
    main()
