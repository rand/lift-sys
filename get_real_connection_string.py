#!/usr/bin/env python3
"""
Get the actual database connection string from Supabase API
"""

import httpx

SUPABASE_URL = "https://bqokcxjusdkywfgfqhzo.supabase.co"
SERVICE_ROLE_KEY = "***REMOVED***"

headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
}

print("Querying Supabase for project info...")

# Try to get project settings via REST API
try:
    # Query for any table to see what info we get back
    response = httpx.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=10.0)
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print()

    # The connection info should be in the Supabase dashboard
    # Let's try to construct it based on standard patterns
    print("Standard Supabase connection patterns:")
    print()
    print("1. Connection Pooler (Transaction mode - port 6543):")
    print(
        "   postgresql://postgres.bqokcxjusdkywfgfqhzo:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
    )
    print()
    print("2. Connection Pooler (Session mode - port 5432):")
    print(
        "   postgresql://postgres.bqokcxjusdkywfgfqhzo:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
    )
    print()
    print("3. Direct Connection (port 6543):")
    print(
        "   postgresql://postgres.bqokcxjusdkywfgfqhzo:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
    )
    print()

    print("Replace [PASSWORD] with: sgVOFNCgIWk585q8")
    print()
    print("Note: The region (us-west-1) is a guess. Check your Supabase dashboard at:")
    print("https://supabase.com/dashboard/project/bqokcxjusdkywfgfqhzo/settings/database")
    print()
    print("Look for 'Connection string' section and copy the exact host.")

except Exception as e:
    print(f"Error: {e}")
