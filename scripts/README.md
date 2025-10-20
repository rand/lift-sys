# Scripts Directory

Utility scripts for the lift-sys project, organized by category.

## Directory Structure

### benchmarks/
Performance benchmarking utilities.

- `run_benchmark.sh` - Quick runner for performance benchmarks

**Usage:**
```bash
./scripts/benchmarks/run_benchmark.sh
```

### database/
Database migration and connection utilities.

- `run_migrations.py` - Run Supabase database migrations
- `verify_supabase_connection.sh` - Interactive Supabase connection tester

**Usage:**
```bash
# Run migrations
python scripts/database/run_migrations.py

# Verify connection
./scripts/database/verify_supabase_connection.sh
```

### setup/
Project setup and startup scripts.

- `setup-oauth.sh` - OAuth configuration helper
- `start.sh` - Start development servers (backend + frontend)

**Usage:**
```bash
# Start dev servers
./scripts/setup/start.sh

# Setup OAuth
./scripts/setup/setup-oauth.sh
```

### website/
Website maintenance and deployment scripts.

- `update-plan-page.sh` - Update the plan progress page on site-lift-sys

**Usage:**
```bash
./scripts/website/update-plan-page.sh
```

## Notes

- All scripts are designed to be run from the repository root or from their current location
- Scripts automatically navigate to the correct working directory as needed
- Environment variables should be configured in `.env` or `.env.local` files
