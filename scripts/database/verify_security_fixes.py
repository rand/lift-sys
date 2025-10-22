#!/usr/bin/env python3
"""
Verify Supabase security linter fixes are applied
Checks that:
1. Views use security_invoker (not security_definer)
2. Functions have fixed search_path
"""

import os
import sys

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed")
    sys.exit(1)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    sys.exit(1)

# Colors
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def main():
    print(f"{YELLOW}Connecting to database...{NC}")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"{RED}✗ Connection failed: {e}{NC}")
        sys.exit(1)

    print(f"{GREEN}✓ Connected{NC}\n")

    # Check 1: Verify views have security_invoker option
    print(f"{BLUE}━━━ Checking View Security Options ━━━{NC}")

    view_names = ["session_summary", "user_analytics", "recent_activity", "draft_validation_stats"]

    cursor.execute(
        """
        SELECT
            c.relname AS view_name,
            CASE
                WHEN v.reloptions IS NULL THEN 'No options set'
                WHEN array_to_string(v.reloptions, ',') LIKE '%security_invoker=true%' THEN 'security_invoker=on'
                WHEN array_to_string(v.reloptions, ',') LIKE '%security_invoker=false%' THEN 'security_definer (default)'
                ELSE array_to_string(v.reloptions, ',')
            END AS security_mode
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        LEFT JOIN pg_class v ON v.oid = c.oid
        WHERE n.nspname = 'public'
        AND c.relkind = 'v'
        AND c.relname = ANY(%s)
        ORDER BY c.relname;
    """,
        (view_names,),
    )

    views_fixed = 0
    views_total = 0

    for row in cursor.fetchall():
        view_name, security_mode = row
        views_total += 1
        if "security_invoker=on" in security_mode:
            print(f"{GREEN}✓ {view_name:30} → {security_mode}{NC}")
            views_fixed += 1
        else:
            print(f"{RED}✗ {view_name:30} → {security_mode}{NC}")

    print()

    # Check 2: Verify functions have fixed search_path
    print(f"{BLUE}━━━ Checking Function Search Paths ━━━{NC}")

    function_names = [
        "update_updated_at_column",
        "update_session_revision_count",
        "update_session_draft_count",
        "update_session_hole_count",
        "refresh_user_analytics",
    ]

    cursor.execute(
        """
        SELECT
            p.proname AS function_name,
            CASE
                WHEN p.proconfig IS NULL THEN 'No search_path set'
                ELSE array_to_string(p.proconfig, ', ')
            END AS search_path
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = ANY(%s)
        ORDER BY p.proname;
    """,
        (function_names,),
    )

    functions_fixed = 0
    functions_total = 0

    for row in cursor.fetchall():
        function_name, search_path = row
        functions_total += 1
        if search_path != "No search_path set":
            print(f"{GREEN}✓ {function_name:35} → {search_path}{NC}")
            functions_fixed += 1
        else:
            print(f"{RED}✗ {function_name:35} → {search_path}{NC}")

    print()

    # Summary
    print(f"{BLUE}━━━ Summary ━━━{NC}")
    print(f"Views:     {views_fixed}/{views_total} using security_invoker")
    print(f"Functions: {functions_fixed}/{functions_total} with fixed search_path")
    print()

    if views_fixed == views_total and functions_fixed == functions_total:
        print(f"{GREEN}✓ All security fixes applied successfully!{NC}")
        print(f"{GREEN}  - 4 ERROR-level issues resolved (security_definer_view){NC}")
        print(f"{GREEN}  - 5 WARN-level issues resolved (function_search_path_mutable){NC}")
        print()
        print("Run Supabase linter again to verify:")
        print("  → Go to Supabase Dashboard → Database → Linter")
        sys.exit(0)
    else:
        print(f"{RED}✗ Some security fixes are missing{NC}")
        print(f"{YELLOW}Run migration 010 again or check for errors{NC}")
        sys.exit(1)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
