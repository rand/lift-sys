#!/bin/bash
# run_all_migrations.sh
# Runs all Supabase migrations in order
# Usage: ./run_all_migrations.sh <database_url>

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Database URL required${NC}"
    echo ""
    echo "Usage: $0 <database_url>"
    echo ""
    echo "Example:"
    echo "  $0 'postgresql://postgres:PASSWORD@db.xxxxx.supabase.co:5432/postgres'"
    echo ""
    echo "Get your database URL from Supabase:"
    echo "  Settings → Database → Connection String → URI"
    exit 1
fi

DATABASE_URL="$1"

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql not found${NC}"
    echo "Install PostgreSQL client:"
    echo "  macOS: brew install postgresql"
    echo "  Ubuntu: sudo apt-get install postgresql-client"
    exit 1
fi

# Test connection
echo -e "${YELLOW}Testing database connection...${NC}"
if ! psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    echo "Check your DATABASE_URL is correct"
    exit 1
fi
echo -e "${GREEN}✓ Connection successful${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Migration files in order
MIGRATIONS=(
    "001_create_sessions_table.sql"
    "002_create_revisions_table.sql"
    "003_create_drafts_table.sql"
    "004_create_resolutions_table.sql"
    "005_create_rls_policies.sql"
    "006_create_triggers.sql"
    "007_create_views.sql"
)

# Run each migration
echo -e "${YELLOW}Running migrations...${NC}"
echo ""

for migration in "${MIGRATIONS[@]}"; do
    migration_path="$SCRIPT_DIR/$migration"

    if [ ! -f "$migration_path" ]; then
        echo -e "${RED}Error: Migration file not found: $migration${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Running: $migration${NC}"
    if psql "$DATABASE_URL" -f "$migration_path" -v ON_ERROR_STOP=1 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $migration complete${NC}"
    else
        echo -e "${RED}✗ $migration failed${NC}"
        echo ""
        echo "Run manually to see error details:"
        echo "  psql \"$DATABASE_URL\" -f \"$migration_path\""
        exit 1
    fi
    echo ""
done

# Success summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}All migrations completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Verify tables created
echo -e "${YELLOW}Verifying schema...${NC}"
TABLE_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'" 2>/dev/null | tr -d ' ')

if [ "$TABLE_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✓ Tables created: $TABLE_COUNT${NC}"
else
    echo -e "${YELLOW}Warning: Expected 4+ tables, found $TABLE_COUNT${NC}"
fi

# Verify RLS enabled
RLS_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true" 2>/dev/null | tr -d ' ')

if [ "$RLS_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✓ RLS enabled on $RLS_COUNT tables${NC}"
else
    echo -e "${YELLOW}Warning: RLS may not be enabled on all tables${NC}"
fi

# Verify views created
VIEW_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM pg_views WHERE schemaname = 'public'" 2>/dev/null | tr -d ' ')

if [ "$VIEW_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✓ Views created: $VIEW_COUNT${NC}"
else
    echo -e "${YELLOW}Warning: Expected 4+ views, found $VIEW_COUNT${NC}"
fi

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Verify schema in Supabase Studio → Table Editor"
echo "2. Test RLS: Try querying without auth context"
echo "3. Insert test data to verify triggers"
echo "4. Configure Modal secrets with Supabase credentials"
echo ""
echo "See SUPABASE_QUICK_START.md for full setup guide"
