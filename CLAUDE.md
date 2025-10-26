# lift-sys Development Guidelines

**Last Updated**: 2025-10-26

> **Project-Specific Rules**: This file contains development guidelines specific to the lift-sys project. For global Claude development guidelines, see `~/.claude/CLAUDE.md`.

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Meta-Framework: Hole-Driven Development](#2-meta-framework-hole-driven-development)
3. [Repository Organization](#3-repository-organization)
4. [Tech Stack & Architecture](#4-tech-stack--architecture)
5. [Development Workflow](#5-development-workflow)
6. [Testing Strategy](#6-testing-strategy)
7. [Infrastructure & Deployment](#7-infrastructure--deployment)
8. [Security & Secrets](#8-security--secrets)
9. [Code Quality Standards](#9-code-quality-standards)
10. [Documentation Requirements](#10-documentation-requirements)
11. [Anti-Patterns & Gotchas](#11-anti-patterns--gotchas)

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

**For up-to-date status, see [CURRENT_STATE.md](CURRENT_STATE.md) and [docs/issues/BACKEND_STATUS.md](docs/issues/BACKEND_STATUS.md)**

**Active Work:**
- 🎯 **ICS (Integrated Context Studio)** - PRIMARY UI in development (Phase 4 complete, Phase 1 starting)
- 🎯 **Backend Pipeline** - Partially working (80% success, 132 known gaps labeled `backend-gap`)

**Working:**
- ✅ Modal.com deployment operational (LLM inference)
- ✅ Forward mode partially functional (100% compilation, 80% execution)
- ✅ AST Repair (Phase 4), Assertion Checking (Phase 5), Constraints (Phase 7)

**Queued:**
- ⏸️ **DSPy + Pydantic AI Architecture** - Designed, queued for post-ICS implementation (H1-H19)
- ⏸️ **ACE Enhancement** - Researched, queued (3 issues: lift-sys-167, 168, 169)
- ⏸️ **MUSLR Enhancement** - Researched, queued (4 issues: lift-sys-163, 164, 165, 166)
- ⏸️ **Supabase** - Schema designed, deployment pending (lift-sys-71 in progress)
- ⏸️ **Honeycomb** - Observability planned, not started
- 🚧 **Reverse mode** - Planning phase

---

## 2. Meta-Framework: Hole-Driven Development

> **⚠️ STATUS NOTE**: This section describes the methodology for **future DSPy + Pydantic AI architecture work** (queued, post-ICS).
> For **current active work** (ICS implementation), see [CURRENT_STATE.md](CURRENT_STATE.md) and [plans/ics-execution-plan.md](plans/ics-execution-plan.md).

### Overview

**WHEN WORKING ON DSPY ARCHITECTURE**: This section describes the **typed holes meta-framework** for systematic DSPy implementation. These guidelines apply when you begin work on H1-H19 holes (currently queued).

**What is it**: We treat the DSPy + Pydantic AI architecture proposal as an "IR with typed holes" that we systematically resolve through constraint propagation.

**Why it matters**: This approach ensures:
- Resumable progress across sessions (AI or human)
- Systematic constraint propagation
- Clear dependencies and ordering
- Gate-validated quality at each phase
- Full provenance of all design decisions

### Core Documents (MUST READ)

**Before ANY development work, read these in order:**

1. **`docs/planning/SESSION_BOOTSTRAP.md`** - 5-minute quick start guide
2. **`docs/planning/SESSION_STATE.md`** - Current state and active hole
3. **`docs/planning/HOLE_INVENTORY.md`** - All 19 holes and dependencies
4. **`docs/planning/REIFICATION_SUMMARY.md`** - How the system works

### Session Start Protocol (MANDATORY)

```bash
# 1. Read current state
cat docs/planning/SESSION_STATE.md | head -50

# 2. Check what's ready (optional - state doc tells you)
python3 scripts/planning/track_holes.py ready --phase 1

# 3. Read active hole details
# See "Current Work Context" in SESSION_STATE.md

# 4. Begin implementation following hole specification
```

### Hole Resolution Workflow

**For EVERY hole you work on:**

```
1. READ hole specification from HOLE_INVENTORY.md
   - Understand type signature required
   - Note all constraints MUST satisfy
   - Check what this blocks/blocked by

2. IMPLEMENT following acceptance criteria
   - Create files at specified paths
   - Write comprehensive tests (pytest)
   - Validate with mypy --strict

3. COMMIT implementation before testing
   git add . && git commit -m "Implement HX: HoleName"

4. TEST implementation
   pkill -f pytest  # Kill old tests
   uv run pytest tests/... > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
   wait && tail -100 /tmp/test_*.log

5. DOCUMENT constraint propagation
   - Add Event N to CONSTRAINT_PROPAGATION_LOG.md
   - Document constraints to ALL dependent holes
   - Calculate solution space reduction

6. UPDATE session state
   - Mark hole as RESOLVED in SESSION_STATE.md
   - Update phase progress
   - Set next hole in "Current Work Context"

7. COMMIT documentation
   git add docs/planning/*.md
   git commit -m "Document HX constraint propagation"
```

### Critical Rules

**❌ NEVER:**
- Start a new hole without reading SESSION_STATE.md
- Skip constraint propagation documentation
- Mark a hole resolved without all acceptance criteria passing
- Implement a hole out of dependency order (check `blocked_by`)

**✅ ALWAYS:**
- Read SESSION_STATE.md at session start
- Follow hole specification exactly (type signatures, constraints)
- Document constraint propagation to dependent holes
- Update SESSION_STATE.md after completing a hole
- Commit changes following the hole resolution workflow

### Phase Gates

**Before moving to next phase:**

1. All phase holes must be RESOLVED
2. All gate criteria must PASS (see `PHASE_GATES_VALIDATION.md`)
3. No failing tests
4. Type checker passes (mypy --strict)
5. All constraint propagation documented

**Current Phase**: Phase 1 (Interface Completeness)
- H6: ✅ RESOLVED
- H9: ⏳ Next
- H14: ⏳ Pending
- Gate 1: 4/14 criteria satisfied (28%)

### Constraint Propagation

**When you resolve a hole, constraints propagate to dependent holes.**

**Example from H6 resolution:**
```
H6: NodeSignatureInterface resolved with async design
  ↓ Propagates to:
  → H1: ProviderAdapter MUST support async DSPy calls
  → H4: Parallelization MUST use asyncio.gather()
  → H5: ErrorRecovery MUST handle ValueError
```

**Document in `CONSTRAINT_PROPAGATION_LOG.md`:**
- Which hole was resolved
- What constraints propagated where
- How solution spaces narrowed (% reduction)
- Design decisions locked in

### Tools Available

```bash
# Check ready holes
python3 scripts/planning/track_holes.py ready [--phase N]

# Show hole details
python3 scripts/planning/track_holes.py show H6

# Mark hole resolved (script updates inventory)
python3 scripts/planning/track_holes.py resolve H6 --resolution path/to/impl.py

# Check phase status
python3 scripts/planning/track_holes.py phase-status 1

# Visualize dependencies
python3 scripts/planning/track_holes.py visualize --output deps.dot
```

### Session Handoff Pattern

**End of session:**
```bash
# Update state
vim docs/planning/SESSION_STATE.md  # Mark progress, set next hole

# Commit
git add docs/planning/*.md
git commit -m "Session N: Resolved HX, updated state"
git push
```

**Start of next session:**
```bash
# Pull latest
git pull

# Read state
cat docs/planning/SESSION_STATE.md | head -100

# Continue from "Current Work Context"
```

### Mental Model

```
Architecture Proposal
  ↓ (viewed as)
IR with 19 Typed Holes
  ↓ (resolve iteratively)
Holes → Constraints → Propagation → Narrowing
  ↓ (validate at each phase)
7 Phase Gates
  ↓ (result)
Complete, Validated Architecture
```

**You are currently**: Filling in typed holes systematically
**Timeline**: 7 weeks, 7 phases, 19 holes total
**Current**: Phase 1, Week 1, Hole H9 next

---

## 3. Repository Organization

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

## 4. Tech Stack & Architecture

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

### Architecture Redesign: DSPy + Pydantic AI

**Active Initiative**: Replacing hardcoded prompts with declarative DSPy signatures and Pydantic AI graphs.

**Core Technologies:**
- **DSPy**: Declarative LLM programming with automatic optimization (MIPROv2, COPRO)
- **Pydantic AI**: Type-safe agent framework with graph-based workflows
- **Current IR**: Remains central, enhanced with DSPy-compatible fields

**Key Implementations:**
- `lift_sys/dspy_signatures/` - DSPy signature definitions and node interfaces
- See `docs/planning/DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md` for complete design

---

## 5. Development Workflow

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

### Hole-Driven Development Workflow

**When working on architecture holes, use the meta-framework workflow (Section 2).**

**For other development:**

## 6. Testing Strategy

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

## 7. Infrastructure & Deployment

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

## 8. Security & Secrets

**See [SECURITY.md](SECURITY.md) for comprehensive security policy, incident response, and checklists.**

### Secret Management Rules

**CRITICAL: Secrets in this project were compromised once. NEVER AGAIN.**

1. **NEVER commit secrets** to git
2. **NEVER hardcode secrets** in code
3. **ALWAYS use environment variables** or Modal secrets
4. **ALWAYS check before committing**: `git diff` for secrets
5. **ALWAYS use template placeholders** in documentation

### Template Placeholder Format

**When documenting credentials or connection strings, use clearly fake placeholders:**

```bash
# ✅ CORRECT - Clearly a template
DATABASE_URL=postgresql://postgres.<YOUR_PROJECT_REF>:<YOUR_PASSWORD>@aws-1-us-east-1.pooler.supabase.com:5432/postgres
SUPABASE_ANON_KEY=<YOUR_ANON_KEY>
SUPABASE_SERVICE_KEY=<YOUR_SERVICE_KEY>

# ❌ WRONG - Looks like it could be real
DATABASE_URL=postgresql://postgres.project:password@aws-1-us-east-1.pooler.supabase.com:5432/postgres
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.actual_jwt_token_here
```

**Pattern**: Use `<YOUR_*>` format for all placeholders to avoid triggering secret scanners.

### Supabase Keys

**Types of keys:**
- **Anon key**: Safe to commit in docs (public, low privilege)
- **Service role key**: ⚠️ **NEVER commit** (bypasses RLS, full access)
- **Database password**: ⚠️ **NEVER commit**

**Where keys go:**
- `.env.local` (gitignored) - Local development
- Modal secrets (for production) - `modal secret create`
- Documentation - Use `<YOUR_*>` placeholders only

### Secret Detection Tools

**Pre-commit hook (detect-secrets):**
```bash
# Automatically scans for secrets on every commit
# Configured in .pre-commit-config.yaml

# Manual scan
uv run detect-secrets scan

# Update baseline for new false positives
uv run detect-secrets scan --baseline .secrets.baseline

# Audit current baseline
uv run detect-secrets audit .secrets.baseline
```

**Local scanning (gitleaks - optional):**
```bash
# Install
brew install gitleaks

# Scan repository
gitleaks detect --config .gitleaks.toml

# Scan git history
gitleaks protect --config .gitleaks.toml
```

**GitHub Secret Scanning:**
- Automatically enabled for this repository
- False positives excluded via `.github/secret_scanning.yml`
- If you receive an alert:
  1. Verify if it's a real secret or template
  2. If real: **IMMEDIATELY** rotate the credential and remove from git history
  3. If template: Update to use `<YOUR_*>` placeholder format

### False Positive Handling

**Template strings in documentation may trigger scanners. This is expected.**

**Allowed patterns:**
- `<YOUR_PROJECT_REF>`, `<YOUR_PASSWORD>`, etc.
- `PROJECT_REF`, `PASSWORD@aws` in template context
- Truncated JWTs with `...`: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Excluded paths:**
- `docs/**/*.md` - Documentation
- `tests/fixtures/**` - Test data
- `*_test.py`, `test_*.py` - Test files

**If you get a false positive:**
1. Verify it's actually a template (not a real secret)
2. Update template to use `<YOUR_*>` format
3. Run `detect-secrets scan` to update baseline
4. Commit updated `.secrets.baseline`

### Git History Scrubbing

**If secrets leak:**
```bash
# 1. Revoke the secret immediately (CRITICAL!)
# Supabase: Dashboard → Settings → API → Reset keys
# Modal: Dashboard → Secrets → Regenerate

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

**See [SECURITY.md](SECURITY.md) for detailed incident response process.**

### Security Checklist

**Before committing:**
- [ ] No actual credentials in code
- [ ] `.env.local` exists and is gitignored
- [ ] Templates use `<YOUR_*>` placeholder format
- [ ] Pre-commit hooks passed (`detect-secrets`)
- [ ] No secrets in commit message or diff

**Before pushing:**
- [ ] Double-check `git diff` for secrets
- [ ] Verify GitHub secret scanning won't trigger
- [ ] Modal/Supabase secrets are environment-based

**Before deploying:**
- [ ] Environment variables set in deployment platform
- [ ] Secrets rotated if exposed during development
- [ ] RLS policies enabled on database tables

---

## 9. Code Quality Standards

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

## 10. Documentation Requirements

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

## 11. Anti-Patterns & Gotchas

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

**Last major update: 2025-10-26 (Secret detection tools, template placeholders, pre-commit hooks)**
