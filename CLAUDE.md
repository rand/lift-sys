# lift-sys Development Guidelines

**Last Updated**: 2025-10-19

> **Project-Specific Rules**: This file contains development guidelines specific to the lift-sys project. For global Claude development guidelines, see `~/.claude/CLAUDE.md`.

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Repository Organization](#2-repository-organization)
3. [Tech Stack & Architecture](#3-tech-stack--architecture)
4. [Development Workflow](#4-development-workflow)
5. [Testing Strategy](#5-testing-strategy)
6. [Infrastructure & Deployment](#6-infrastructure--deployment)
7. [Security & Secrets](#7-security--secrets)
8. [Code Quality Standards](#8-code-quality-standards)
9. [Documentation Requirements](#9-documentation-requirements)
10. [Anti-Patterns & Gotchas](#10-anti-patterns--gotchas)

---

## 1. Project Overview

### What is lift-sys?

`lift-sys` is a modular, verifiable AI-native software development environment supporting:

- **Forward Mode**: Natural language → Formal IR → Verified code generation
- **Reverse Mode**: Existing code → Behavioral model → Safe refactoring

### Key Components

```
lift_sys/
├── ir/                    # Intermediate Representation (IR) definitions
├── forward_mode/          # NLP → IR → Code pipeline
├── reverse_mode/          # Code → IR recovery (future)
├── validation/            # IR and code validation
├── providers/             # LLM provider integrations (Modal, etc.)
├── api/                   # FastAPI backend
└── storage/               # Session storage (InMemory, Supabase)
```

### Current Status (October 2025)

- ✅ Forward mode proven end-to-end (NLP → IR → Code)
- ✅ Modal.com deployment with GPU workers
- ✅ Supabase database integration complete
- ✅ Performance: ~16s median latency, 60% real success rate
- 🚧 Reverse mode in planning phase
- 🚧 Honeycomb observability integration planned

---

## 2. Repository Organization

### Mandatory Structure

**See `REPOSITORY_ORGANIZATION.md` for complete rules.**

**Quick Reference:**
```
lift-sys/
├── docs/                  # All documentation (categorized)
│   ├── supabase/         # Database docs
│   ├── observability/    # Monitoring docs
│   ├── conjecturing/     # Conjecturing feature
│   ├── benchmarks/       # Performance results
│   ├── phases/           # Phase completion reports
│   ├── planning/         # Project planning
│   ├── fixes/            # Bug fix summaries
│   └── archive/          # Deprecated docs
├── scripts/               # Utility scripts (categorized)
│   ├── benchmarks/       # Performance scripts
│   ├── database/         # DB utilities
│   ├── setup/            # Setup scripts
│   └── website/          # Website maintenance
├── debug/                 # Debug data (never in root!)
├── migrations/            # Supabase migrations
└── lift_sys/             # Main package
```

### Critical Rules

1. **NEVER create files in root** except core project files
2. **ALL documentation** goes to `docs/{category}/`
3. **ALL scripts** go to `scripts/{category}/`
4. **ALL debug data** goes to `debug/`
5. **Use `git mv`** to preserve history when organizing

### Enforcement

**Before creating ANY file:**
```
Is it documentation? → docs/{category}/
Is it a script?      → scripts/{category}/
Is it debug data?    → debug/
Is it source code?   → lift_sys/ or appropriate package
Does it belong in root? → Probably NOT!
```

---

## 3. Tech Stack & Architecture

### Core Technologies

**Backend:**
- **Python 3.11+** (via `uv` package manager - NEVER use pip/poetry)
- **FastAPI** - API server
- **Pydantic v2** - Data validation and IR models
- **Modal.com** - Serverless GPU compute for LLM inference

**Database:**
- **Supabase** (PostgreSQL + Auth + RLS)
- **Session storage**: InMemorySessionStore, SupabaseSessionStore
- **Migrations**: Located in `migrations/`, run via `scripts/database/run_migrations.py`

**Frontend (if applicable):**
- **React** or **Next.js** (TBD based on UI requirements)
- **shadcn/ui** - UI component library (MANDATORY - always check blocks first)

**Deployment:**
- **Modal.com** - Primary compute platform
- **Vercel** or **Cloudflare** - Static hosting (if needed)

### Package Management

**ALWAYS use `uv` for Python:**
```bash
# ✅ CORRECT
uv add package-name
uv run python script.py
uv run pytest

# ❌ WRONG - NEVER USE
pip install package-name
poetry add package-name
```

### Modal.com Patterns

**See `~/.claude/skills/modal-*.md` for comprehensive guides.**

**Key patterns:**
```python
import modal

app = modal.App("lift-sys")

# Images with uv
image = modal.Image.debian_slim().pip_install_from_pyproject("pyproject.toml")

# GPU selection (L40S for cost/perf balance)
@app.function(gpu="L40S", secrets=[modal.Secret.from_name("supabase")])
def generate_ir(prompt: str) -> IR:
    # Implementation
    pass

# Web endpoints
@app.function()
@modal.web_endpoint()
def api_endpoint(request):
    # Implementation
    pass
```

**CRITICAL: Always stop dev resources after sessions:**
```bash
modal app stop [app-name]
```

---

## 4. Development Workflow

### Session Start Protocol

```bash
# 1. Install/update beads
go install github.com/steveyegge/beads/cmd/bd@latest

# 2. Import state
bd import -i .beads/issues.jsonl

# 3. Check ready work
bd ready --json --limit 5

# 4. Claim task or create new work
bd update <id> --status in_progress
# OR
bd create "Task description" -t feature -p P0 --json
```

### Development Loop

```
1. Code changes
2. Run tests locally: uv run pytest tests/
3. Commit (DON'T test before committing!)
4. Push to branch
5. Create PR via gh CLI
6. Merge after review
```

### Beads Workflow

**MANDATORY for all agentic work:**

1. **File issues immediately** when discovered
2. **Use dependencies**: `bd dep add <parent> <child> --type blocks`
3. **Export state**: `bd export -o .beads/issues.jsonl`
4. **Commit .beads/issues.jsonl** with changes

**See `docs/` for beads summaries** (e.g., `docs/supabase/SUPABASE_BEADS_SUMMARY.md`)

---

## 5. Testing Strategy

### Critical Testing Protocol

**ABSOLUTE RULE: NEVER run tests before committing**

```bash
# ✅ CORRECT FLOW
git add . && git commit -m "Description"
git log -1 --oneline
pkill -f "pytest"  # Kill old tests
uv run pytest tests/ > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
wait  # Wait for completion
tail -f /tmp/test_*.log

# ❌ WRONG FLOW
# Code → Test → Commit (tests stale code!)
```

### Test Structure

```
tests/
├── unit/              # Pure functions, isolated tests
├── integration/       # System interactions (DB, API)
├── e2e/              # Full workflows
├── fixtures/         # Test data
├── conftest.py       # Shared pytest config
└── archive/          # Deprecated tests
```

### Test Standards

- Use **pytest** with **pytest-cov** for coverage
- Mock external services (LLMs, DB) in unit tests
- Integration tests use real services (with test data)
- E2E tests validate full workflows
- Benchmarks in `performance_benchmark.py` (run via `scripts/benchmarks/run_benchmark.sh`)

---

## 6. Infrastructure & Deployment

### Modal.com Configuration

**Secrets management:**
```bash
# Supabase secrets
modal secret create supabase \
  SUPABASE_URL="https://bqokcxjusdkywfgfqhzo.supabase.co" \
  SUPABASE_ANON_KEY="<from-dashboard>" \
  SUPABASE_SERVICE_KEY="<from-dashboard>"

# List secrets
modal secret list

# Use in functions
@app.function(secrets=[modal.Secret.from_name("supabase")])
def my_function():
    import os
    url = os.getenv("SUPABASE_URL")
```

### Supabase Configuration

**Connection:**
- URL: `https://bqokcxjusdkywfgfqhzo.supabase.co`
- Database URL: Available in Supabase dashboard
- Region: US East 1 (Virginia)

**Migrations:**
```bash
# Run from repo root or via script
python scripts/database/run_migrations.py

# Migrations located in: migrations/*.sql
# Ordered: 001, 002, 003...
```

**RLS (Row Level Security):**
- ENABLED on all tables
- User isolation: `auth.uid() = user_id`
- See `docs/supabase/SUPABASE_SCHEMA.md` for details

### Environment Variables

**Local development: `.env.local` (gitignored)**
```bash
SUPABASE_URL=https://bqokcxjusdkywfgfqhzo.supabase.co
SUPABASE_ANON_KEY=<public-key>
SUPABASE_SERVICE_KEY=<secret-key>
DATABASE_URL=<connection-string>
```

**Production: Modal secrets** (managed via `modal secret create`)

---

## 7. Security & Secrets

### Secret Management Rules

**CRITICAL: Secrets in this project were compromised once. NEVER AGAIN.**

1. **NEVER commit secrets** to git
2. **NEVER hardcode secrets** in code
3. **ALWAYS use environment variables** or Modal secrets
4. **ALWAYS check before committing**: `git diff` for secrets

### Supabase Keys

**Types of keys:**
- **Anon key**: Safe to commit (public, low privilege)
- **Service role key**: NEVER commit (bypasses RLS, full access)
- **Database password**: NEVER commit

**Where keys go:**
- `.env.local` (gitignored)
- Modal secrets (for production)
- Documentation uses `<placeholder>` format

### Git History Scrubbing

**If secrets leak:**
```bash
# 1. Revoke the secret immediately
# 2. Install git-filter-repo
brew install git-filter-repo

# 3. Create replacement file
echo "leaked-secret-text" > /tmp/remove_secret.txt

# 4. Remove from history
git filter-repo --replace-text /tmp/remove_secret.txt --force

# 5. Re-add remote and force push
git remote add origin git@github.com:rand/lift-sys.git
git push --force origin main

# 6. Update all secrets with new values
```

**See session logs (2025-10-19) for complete recovery process.**

---

## 8. Code Quality Standards

### Python Style

**Enforced by pre-commit hooks:**
- **ruff** - Linting and formatting (replaces black, flake8, isort)
- **ruff format** - Code formatting

**Standards:**
- Type hints on all functions (Pydantic models preferred)
- Docstrings on public APIs (Google style)
- Maximum line length: 100 characters (ruff default)

### IR Design Principles

**Immutability:**
- IR objects are **immutable** (Pydantic `frozen=True`)
- Use `.model_copy(update={...})` for modifications

**Validation:**
- All IR nodes validate at construction time
- Use Pydantic validators for constraints
- Validation errors should be descriptive

**Example:**
```python
from pydantic import BaseModel, Field, field_validator

class Parameter(BaseModel, frozen=True):
    name: str = Field(..., pattern=r'^[a-z_][a-z0-9_]*$')
    type_hint: str
    default: Optional[str] = None

    @field_validator('type_hint')
    def validate_type_hint(cls, v):
        if not v:
            raise ValueError("type_hint cannot be empty")
        return v
```

### Error Handling

**API errors:**
```python
from fastapi import HTTPException

# Use appropriate status codes
raise HTTPException(status_code=400, detail="Invalid IR structure")
raise HTTPException(status_code=404, detail="Session not found")
raise HTTPException(status_code=500, detail="Internal error")
```

**Validation errors:**
```python
from pydantic import ValidationError

try:
    ir = IR(**data)
except ValidationError as e:
    # Log and return helpful error
    logger.error(f"IR validation failed: {e}")
    raise
```

---

## 9. Documentation Requirements

### When to Document

**ALWAYS document:**
- New features (in `docs/planning/`)
- Phase completions (in `docs/phases/`)
- Bug fixes (in `docs/fixes/`)
- Architecture changes (in appropriate `docs/` subdirectory)
- Performance benchmarks (in `docs/benchmarks/`)

**NEVER document in root** - use `docs/{category}/`

### Documentation Standards

**Naming:**
- Use SCREAMING_SNAKE_CASE
- Include descriptive prefix: `SUPABASE_`, `PHASE_`, `HONEYCOMB_`
- Include date in status docs: `STATUS_20251019.md`

**Structure:**
```markdown
# Title

**Date**: YYYY-MM-DD
**Status**: Complete/In Progress/Blocked
**Related Issues**: bd-123, bd-456

## Summary
Brief overview (2-3 sentences)

## Details
Comprehensive information

## Next Steps
What comes after this

## References
- Related docs
- External links
```

### Cross-References

**Use relative paths:**
```markdown
# From docs/observability/
[Supabase Setup](../supabase/SUPABASE_SETUP_STATUS.md)
[Project Roadmap](../../SEMANTIC_IR_ROADMAP.md)
```

---

## 10. Anti-Patterns & Gotchas

### Critical Violations (Will Break Things)

**❌ NEVER:**
1. Run tests before committing (tests stale code)
2. Use pip/poetry instead of uv
3. Commit secrets to git
4. Create files in root directory
5. Force push to main without justification
6. Skip pre-commit hooks with `--no-verify`
7. Leave Modal dev resources running
8. Hardcode database credentials

### Common Mistakes

**❌ Wrong:**
```python
# Hardcoded endpoint
provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")

# Mutable IR
class IR(BaseModel):
    effects: list[Effect]  # Not frozen!

# Missing error handling
ir = translator.translate(prompt)  # What if it fails?
```

**✅ Correct:**
```python
# Environment-based endpoint
endpoint = os.getenv("MODAL_ENDPOINT", "https://rand--generate.modal.run")
provider = ModalProvider(endpoint_url=endpoint)

# Immutable IR
class IR(BaseModel, frozen=True):
    effects: tuple[Effect, ...]  # Immutable!

# Proper error handling
try:
    ir = await translator.translate(prompt)
except TranslationError as e:
    logger.error(f"Translation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### Debugging Workflow

**When things break:**

1. **Check logs** - Where did it fail?
2. **Save debug data** to `debug/` (with descriptive name)
3. **Create bead** if it's a real bug: `bd create "Bug: ..." -t bug`
4. **Document** the fix in `docs/fixes/` if complex
5. **Add test** to prevent regression

**Debug file naming:**
```
debug/debug_<feature>_<issue>_<date>.json
debug/validation_results_<test_case>.json
debug/<ir_type>_ir_example.json
```

### Performance Gotchas

**Cold start latency:**
- Modal functions: ~3min on first call
- Warm: ~16s median latency
- Budget accordingly in tests

**Database:**
- Supabase connection pooling recommended (port 6543)
- RLS adds overhead but is mandatory for security
- Use views for common analytics queries

**LLM calls:**
- Cache when possible
- Use streaming for long responses
- Temperature=0.0 for deterministic output

---

## Project-Specific Patterns

### IR Translation Pipeline

```python
# Forward mode flow:
# 1. NLP → IR (via BestOfNIRTranslator)
# 2. IR → Code (via TemplatedCodeGenerator)
# 3. Validation (syntax, AST, execution)

from lift_sys.forward_mode import BestOfNIRTranslator, TemplatedCodeGenerator
from lift_sys.providers import ModalProvider
from lift_sys.validation import validate_ir, validate_code

# Initialize
provider = ModalProvider(...)
translator = BestOfNIRTranslator(provider, n_candidates=3)
generator = TemplatedCodeGenerator()

# Translate
ir = await translator.translate(prompt)
validate_ir(ir)  # Raises if invalid

# Generate
code = generator.generate(ir)
validate_code(code)  # Syntax, AST checks

# Execute (optional)
result = execute_code(code, test_inputs)
```

### Session Management

```python
from lift_sys.storage import SupabaseSessionStore

# Initialize (uses env vars or Modal secrets)
store = SupabaseSessionStore()
await store.initialize()

# CRUD operations
session_id = await store.create_session(user_id="user-123", initial_ir=ir)
session = await store.get_session(session_id)
await store.update_session(session_id, current_ir=new_ir)
await store.delete_session(session_id)

# RLS automatically enforces user_id isolation
```

### Benchmarking

```bash
# Run from repo root
./scripts/benchmarks/run_benchmark.sh

# Or directly
uv run python performance_benchmark.py

# Results saved to timestamped files
# Analyze with debug/ tools
```

---

## Quick Command Reference

### Development
```bash
# Setup
uv sync                          # Install dependencies
uv run pytest                    # Run tests
uv run uvicorn lift_sys.api.server:app --reload  # Start API

# Scripts
./scripts/setup/start.sh         # Start dev servers
./scripts/database/run_migrations.py  # Run DB migrations
./scripts/benchmarks/run_benchmark.sh # Run benchmarks
```

### Beads
```bash
bd ready --json --limit 5        # Check ready work
bd create "Task" -t feature -p P0 --json  # Create task
bd update bd-123 --status in_progress     # Claim task
bd close bd-123 --reason "Done"           # Complete task
bd export -o .beads/issues.jsonl          # Export state
```

### Git
```bash
git checkout -b feature/name     # New feature branch
git add . && git commit -m "..."  # Commit changes
git push -u origin feature/name  # Push branch
gh pr create --title "..." --body "..."  # Create PR
```

### Modal
```bash
modal app list                   # List apps
modal app logs lift-sys          # View logs
modal app stop lift-sys          # Stop dev resources
modal secret list                # List secrets
```

---

## Maintenance Checklist

### Weekly
- [ ] Scan root for misplaced files (`find . -maxdepth 1 -type f`)
- [ ] Review and close completed beads
- [ ] Update phase documentation if in active phase
- [ ] Check for open PRs that need review

### Monthly
- [ ] Review and archive old documentation
- [ ] Update benchmark baselines if performance changed
- [ ] Review open beads for stale/blocked items
- [ ] Check Modal costs and optimize if needed

### Before Major Releases
- [ ] Full test suite pass
- [ ] Benchmark regression check
- [ ] Documentation updates
- [ ] Migration dry-runs (if schema changes)
- [ ] Security audit (no secrets leaked)

---

## Getting Help

### Documentation
- **This file** - Project-specific guidelines
- **Global CLAUDE.md** - `~/.claude/CLAUDE.md` for general development guidelines
- **Repository Organization** - `REPOSITORY_ORGANIZATION.md` for file structure
- **Semantic Roadmap** - `SEMANTIC_IR_ROADMAP.md` for product direction
- **Known Issues** - `KNOWN_ISSUES.md` for current bugs

### External Resources
- **Modal.com Docs** - https://modal.com/docs
- **Supabase Docs** - https://supabase.com/docs
- **Beads Framework** - https://github.com/steveyegge/beads

### Internal Documentation
- **Supabase Setup** - `docs/supabase/SUPABASE_QUICK_START.md`
- **Conjecturing** - `docs/conjecturing/CONJECTURING_INDEX.md`
- **Phase Summaries** - `docs/phases/PHASE*.md`
- **Planning Docs** - `docs/planning/`

---

**This is a living document. Update it when patterns emerge or project structure evolves.**

**Last major update: 2025-10-19 (Repository organization, secret management, Modal patterns)**
