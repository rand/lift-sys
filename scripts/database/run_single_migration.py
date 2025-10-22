#!/usr/bin/env python3
"""
Run a single Supabase migration
Usage: python run_single_migration.py 010_fix_security_linter_issues.sql
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

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    print("Please set it in .env.local or export it")
    sys.exit(1)

# Colors
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def run_migration(migration_file: Path):
    """Run a single migration file"""
    print(f"{YELLOW}Running: {migration_file.name}{NC}")

    with open(migration_file) as f:
        sql = f.read()

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        print(f"{GREEN}✓ {migration_file.name} complete{NC}\n")
        return True
    except Exception as e:
        print(f"{RED}✗ {migration_file.name} failed{NC}")
        print(f"Error: {e}\n")
        if "conn" in locals():
            conn.rollback()
            conn.close()
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_single_migration.py <migration_file.sql>")
        print("Example: python run_single_migration.py 010_fix_security_linter_issues.sql")
        sys.exit(1)

    migration_name = sys.argv[1]
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    migration_path = migrations_dir / migration_name

    if not migration_path.exists():
        print(f"{RED}✗ Migration file not found: {migration_path}{NC}")
        sys.exit(1)

    print(f"{YELLOW}Testing database connection...{NC}")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"{GREEN}✓ Connection successful{NC}")
        print(f"PostgreSQL version: {version[:50]}...\n")
    except Exception as e:
        print(f"{RED}✗ Connection failed: {e}{NC}")
        sys.exit(1)

    if run_migration(migration_path):
        print(f"{GREEN}{'━' * 42}{NC}")
        print(f"{GREEN}Migration completed successfully!{NC}")
        print(f"{GREEN}{'━' * 42}{NC}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
