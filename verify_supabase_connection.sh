#!/bin/bash
# verify_supabase_connection.sh
# Interactive script to verify Supabase connection

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Supabase Connection Verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Get connection string from user
echo -e "${YELLOW}Step 1: Get Connection String${NC}"
echo ""
echo "Go to Supabase Dashboard → Project Settings → Database"
echo "Under 'Connection string', click 'Connection Pooling' tab"
echo "Select 'URI' mode and copy the string"
echo ""
echo -e "${BLUE}Your connection string should look like:${NC}"
echo "postgresql://postgres.PROJECT_REF:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:6543/postgres"
echo ""
read -p "Paste your connection string here: " RAW_DATABASE_URL

# Check if password needs to be filled in
if [[ "$RAW_DATABASE_URL" == *"[YOUR-PASSWORD]"* ]]; then
    echo ""
    echo -e "${YELLOW}Your connection string has [YOUR-PASSWORD] placeholder${NC}"
    echo -e "${YELLOW}Please enter your actual database password:${NC}"
    read -s DATABASE_PASSWORD
    echo ""

    # Replace placeholder
    DATABASE_URL="${RAW_DATABASE_URL//\[YOUR-PASSWORD\]/$DATABASE_PASSWORD}"
else
    DATABASE_URL="$RAW_DATABASE_URL"
fi

echo -e "${GREEN}✓ Connection string set${NC}"
echo ""

# Step 2: Check psql is installed
echo -e "${YELLOW}Step 2: Check psql Installation${NC}"
echo ""

if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version | head -n1)
    echo -e "${GREEN}✓ psql found: $PSQL_VERSION${NC}"
else
    echo -e "${RED}✗ psql not found${NC}"
    echo ""
    echo "Install psql:"
    echo "  macOS:   brew install libpq"
    echo "           brew link --force libpq"
    echo "  Ubuntu:  sudo apt-get install postgresql-client"
    echo ""
    exit 1
fi
echo ""

# Step 3: Test basic connection
echo -e "${YELLOW}Step 3: Test Basic Connection${NC}"
echo ""

if psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection successful!${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
    echo ""
    echo -e "${YELLOW}Trying to diagnose the issue...${NC}"
    echo ""

    # Try to get more specific error
    ERROR_OUTPUT=$(psql "$DATABASE_URL" -c "SELECT 1" 2>&1 || true)
    echo "Error details:"
    echo "$ERROR_OUTPUT"
    echo ""

    # Check common issues
    if [[ "$ERROR_OUTPUT" == *"password authentication failed"* ]]; then
        echo -e "${RED}Issue: Wrong password${NC}"
        echo "Fix:"
        echo "  1. Go to Supabase Dashboard → Settings → Database"
        echo "  2. Click 'Reset database password'"
        echo "  3. Save the new password and retry"
        echo ""
    elif [[ "$ERROR_OUTPUT" == *"could not connect"* ]] || [[ "$ERROR_OUTPUT" == *"Connection refused"* ]]; then
        echo -e "${RED}Issue: Cannot reach Supabase server${NC}"
        echo "Fix:"
        echo "  1. Check you're using port 6543 (pooler) in connection string"
        echo "  2. Try port 5432 (direct) if pooler doesn't work"
        echo "  3. Check firewall/VPN isn't blocking connection"
        echo ""
    elif [[ "$ERROR_OUTPUT" == *"database"*"does not exist"* ]]; then
        echo -e "${RED}Issue: Wrong database name${NC}"
        echo "Fix:"
        echo "  1. Use 'postgres' as database name (at end of connection string)"
        echo ""
    fi

    exit 1
fi
echo ""

# Step 4: Test PostgreSQL version
echo -e "${YELLOW}Step 4: Verify PostgreSQL Version${NC}"
echo ""

PG_VERSION=$(psql "$DATABASE_URL" -t -c "SELECT version();" 2>/dev/null | head -n1)

if [[ "$PG_VERSION" == *"PostgreSQL 15"* ]]; then
    echo -e "${GREEN}✓ PostgreSQL 15.x detected${NC}"
    echo "  $PG_VERSION"
elif [[ "$PG_VERSION" == *"PostgreSQL"* ]]; then
    echo -e "${YELLOW}⚠ PostgreSQL version: $PG_VERSION${NC}"
    echo "  (Expected PostgreSQL 15.x)"
else
    echo -e "${RED}✗ Could not determine PostgreSQL version${NC}"
fi
echo ""

# Step 5: Check if migrations already ran
echo -e "${YELLOW}Step 5: Check Existing Tables${NC}"
echo ""

TABLE_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" 2>/dev/null | tr -d ' ')

if [ "$TABLE_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✓ Found $TABLE_COUNT tables (migrations already ran)${NC}"

    # List tables
    echo ""
    echo "Existing tables:"
    psql "$DATABASE_URL" -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
    echo ""

    echo -e "${YELLOW}Migrations appear to have already run.${NC}"
    echo "Do you want to re-run them? (This will likely fail with 'already exists' errors)"
    read -p "Re-run migrations? [y/N]: " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✅ Connection verified! Migrations already complete.${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Verify schema in Supabase Studio"
        echo "  2. Configure Modal secrets"
        echo "  3. Continue with lift-sys-261 (SupabaseSessionStore)"
        echo ""
        exit 0
    fi
else
    echo -e "${YELLOW}Found $TABLE_COUNT tables (migrations not yet run)${NC}"
fi
echo ""

# Step 6: Run migrations
echo -e "${YELLOW}Step 6: Run Database Migrations${NC}"
echo ""

if [ ! -f "migrations/run_all_migrations.sh" ]; then
    echo -e "${RED}✗ Migration script not found${NC}"
    echo "Expected: migrations/run_all_migrations.sh"
    echo "Are you in the project root directory?"
    exit 1
fi

# Make script executable
chmod +x migrations/run_all_migrations.sh

echo "Running migrations..."
echo ""

if ./migrations/run_all_migrations.sh "$DATABASE_URL"; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ All steps complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Verify schema in Supabase Studio (Dashboard → Table Editor)"
    echo "  2. Configure Modal secrets:"
    echo "     modal secret create supabase \\"
    echo "       SUPABASE_URL=\"https://YOUR_PROJECT.supabase.co\" \\"
    echo "       SUPABASE_ANON_KEY=\"your-anon-key\" \\"
    echo "       SUPABASE_SERVICE_KEY=\"your-service-key\""
    echo ""
    echo "  3. Continue with lift-sys-261 (Implement SupabaseSessionStore)"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Migrations failed${NC}"
    echo ""
    echo "Check the error messages above for details"
    echo "See docs/SUPABASE_CONNECTION_TROUBLESHOOTING.md for help"
    exit 1
fi
