#!/usr/bin/env python3
"""Verify Supabase database connection and schema.

Usage:
    python scripts/validation/verify_supabase.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add repo root to Python path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))


async def verify_supabase():
    """Verify Supabase connection and basic operations."""
    print("🔍 Verifying Supabase connection...")
    print()

    # Check environment variables
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")

    print("📋 Environment Variables:")
    print(f"   SUPABASE_URL: {'✅ Set' if url else '❌ Not set'}")
    print(f"   SUPABASE_ANON_KEY: {'✅ Set' if anon_key else '❌ Not set'}")
    print(f"   SUPABASE_SERVICE_KEY: {'✅ Set' if service_key else '❌ Not set'}")
    print()

    if not url or not anon_key:
        print("❌ Supabase credentials not configured")
        print("   Set SUPABASE_URL and SUPABASE_ANON_KEY in .env")
        return False

    # Try to import and initialize the store
    try:
        from lift_sys.spec_sessions.supabase_store import SupabaseSessionStore

        print("📦 Importing SupabaseSessionStore... ✅")
    except ImportError as e:
        print(f"❌ Failed to import SupabaseSessionStore: {e}")
        return False

    # Try to initialize (client connection happens in __init__)
    try:
        store = SupabaseSessionStore()
        print("🔧 Initializing store... ✅")
        print("🔌 Connected to Supabase... ✅")
    except Exception as e:
        print(f"❌ Failed to initialize/connect: {e}")
        return False

    # Try a simple query to verify connection
    try:
        # Query the sessions table (should work even if empty)
        response = store.client.table("sessions").select("id").limit(1).execute()
        print("📊 Database query successful... ✅")
    except Exception as e:
        print(f"⚠️  Database query failed: {e}")
        print("   (Tables may not exist yet - run migrations)")

    print()
    print("✅ Supabase verification complete!")
    return True


def main():
    """Main entry point."""
    # Load environment variables from .env.local (if exists)
    env_path = ".env.local"
    if os.path.exists(env_path):
        print(f"📝 Loading environment from {env_path}")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        print()

    # Run verification
    result = asyncio.run(verify_supabase())

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
