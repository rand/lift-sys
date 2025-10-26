#!/usr/bin/env python3
"""
Run Supabase migrations using psycopg2
No need for psql command-line tool
"""

import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed")
    print("Installing now...")
    os.system("uv add psycopg2-binary")
    import psycopg2

# Colors for output
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

# Supabase database connection
# REQUIRED: Set DATABASE_URL environment variable or create .env.local file
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print(f"{RED}❌ ERROR: DATABASE_URL environment variable not set{NC}")
    print(f"{YELLOW}Set it in your shell or create .env.local file:{NC}")
    print(
        "  export DATABASE_URL='postgresql://postgres.<YOUR_PROJECT_REF>:<YOUR_PASSWORD>@aws-1-us-east-1.pooler.supabase.com:5432/postgres'"
    )
    print(f"{YELLOW}Or add to .env.local (gitignored):{NC}")
    print(
        "  DATABASE_URL=postgresql://postgres.<YOUR_PROJECT_REF>:<YOUR_PASSWORD>@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
    )
    sys.exit(1)


def run_migration(conn, migration_file):
    """Run a single migration file"""
    print(f"{YELLOW}Running: {migration_file.name}{NC}")

    with open(migration_file) as f:
        sql = f.read()

    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        print(f"{GREEN}✓ {migration_file.name} complete{NC}\n")
        return True
    except Exception as e:
        print(f"{RED}✗ {migration_file.name} failed{NC}")
        print(f"Error: {e}\n")
        conn.rollback()
        return False


def main():
    print(f"{YELLOW}Testing database connection...{NC}")

    # Test connection
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        print(f"{GREEN}✓ Connection successful{NC}")
        print(f"PostgreSQL version: {version[:50]}...\n")
    except Exception as e:
        print(f"{RED}✗ Connection failed: {e}{NC}")
        sys.exit(1)

    # Migration files in order
    # Navigate to repo root, then to migrations/
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    migration_files = [
        "001_create_sessions_table.sql",
        "002_create_revisions_table.sql",
        "003_create_drafts_table.sql",
        "004_create_resolutions_table.sql",
        "005_create_rls_policies.sql",
        "006_create_triggers.sql",
        "007_create_views.sql",
    ]

    print(f"{YELLOW}Running migrations...{NC}\n")

    # Run each migration
    success_count = 0
    for migration_name in migration_files:
        migration_path = migrations_dir / migration_name

        if not migration_path.exists():
            print(f"{RED}✗ Migration file not found: {migration_name}{NC}")
            conn.close()
            sys.exit(1)

        if run_migration(conn, migration_path):
            success_count += 1
        else:
            print(f"\n{RED}Migration failed. Stopping.{NC}")
            conn.close()
            sys.exit(1)

    conn.close()

    # Success summary
    print(f"{GREEN}{'━' * 42}{NC}")
    print(f"{GREEN}All {success_count} migrations completed successfully!{NC}")
    print(f"{GREEN}{'━' * 42}{NC}\n")

    # Verify tables created
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    """)
    table_count = cursor.fetchone()[0]
    print(f"{GREEN}✓ Tables created: {table_count}{NC}")

    # Verify RLS enabled
    cursor.execute("""
        SELECT COUNT(*)
        FROM pg_tables
        WHERE schemaname = 'public'
        AND rowsecurity = true
    """)
    rls_count = cursor.fetchone()[0]
    print(f"{GREEN}✓ RLS enabled on {rls_count} tables{NC}")

    # Verify views created
    cursor.execute("""
        SELECT COUNT(*)
        FROM pg_views
        WHERE schemaname = 'public'
    """)
    view_count = cursor.fetchone()[0]
    print(f"{GREEN}✓ Views created: {view_count}{NC}\n")

    cursor.close()
    conn.close()

    # Next steps
    print(f"{GREEN}Next steps:{NC}")
    print("1. Verify schema in Supabase Studio → Table Editor")
    print("2. Configure Modal secrets (see below)")
    print("3. Continue with lift-sys-261 (SupabaseSessionStore)\n")

    print(f"{YELLOW}Configure Modal secrets:{NC}")
    print("modal secret create supabase \\")
    print('  SUPABASE_URL="https://bqokcxjusdkywfgfqhzo.supabase.co" \\')
    print('  SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \\')
    print('  SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."')
    print()


if __name__ == "__main__":
    main()
