# lift-sys

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Verifiable AI-native software development for everyone.**

---

## What is lift-sys?

Most AI coding tools assume an engineer will validate outputs, excluding non-technical users. Tools for non-technical users often create unmaintainable code and add risk.

**lift-sys flips this.** It makes high-quality software creation accessible while keeping engineers in control, across greenfield projects and existing codebases.

### Two Complementary Modes

**Forward Mode** - Natural language → Formal specification → Verified code
- Turns intent into human-readable specifications
- Generates code that satisfies types, policies, and executable proofs
- **Value**: Faster, safer feature creation with evidence attached

**Reverse Mode** - Existing code → Behavioral model → Structured IR
- Recovers behavioral models from code and traces
- Lifts legacy code into structured intermediate form
- **Value**: Safe refactoring in legacy code with provenance and correctness guarantees

Together, these modes let teams build new systems and responsibly evolve existing ones.

---

## Getting Started

### Prerequisites

1. **Python 3.11+** with [`uv`](https://github.com/astral-sh/uv) package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Node.js 18+** (for web UI)
   ```bash
   # macOS
   brew install node

   # Linux
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

3. **Clone the repository**
   ```bash
   git clone https://github.com/rand/lift-sys.git
   cd lift-sys
   ```

### Quick Start

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Start development servers**
   ```bash
   ./scripts/setup/start.sh
   ```

   This launches:
   - **Backend API**: http://localhost:8000 (docs at `/docs`)
   - **Web UI**: http://localhost:5173

3. **Try it out**
   - Navigate to http://localhost:5173
   - Click "Prompt Workbench"
   - Enter: `"A function that validates email addresses"`
   - Follow the interactive refinement workflow

### Alternative Interfaces

**Python SDK:**
```python
from lift_sys.client import SessionClient

client = SessionClient("http://localhost:8000")
session = client.create_session(prompt="A function that adds two numbers")
assists = client.get_assists(session.session_id)
# ... iterative refinement
```

**CLI:**
```bash
uv run python -m lift_sys.cli session create --prompt "Your task"
uv run python -m lift_sys.cli session list
```

**TUI (Terminal UI):**
```bash
uv run python -m lift_sys.main
```

For complete examples, see [`docs/WORKFLOW_GUIDES.md`](docs/WORKFLOW_GUIDES.md)

---

## Developing & Contributing

### Development Setup

1. **Install development dependencies**
   ```bash
   uv sync --all-extras
   cd frontend && npm install
   ```

2. **Run tests**
   ```bash
   # Backend tests
   uv run pytest

   # Frontend tests
   cd frontend && npm test

   # E2E tests
   cd frontend && npm run test:e2e
   ```

3. **Code quality checks**
   ```bash
   # Type checking
   uv run mypy lift_sys

   # Linting (runs automatically on commit)
   uv run ruff check .
   uv run ruff format .
   ```

### Project Structure

```
lift-sys/
├── lift_sys/              # Core Python package
│   ├── ir/               # IR definitions
│   ├── forward_mode/     # NLP → IR → Code pipeline
│   ├── reverse_mode/     # Code → IR recovery
│   ├── validation/       # IR and code validation
│   ├── providers/        # LLM integrations (Modal, Anthropic, OpenAI, Google)
│   ├── api/              # FastAPI backend
│   └── dspy_signatures/  # DSPy architecture (in progress)
│
├── frontend/              # Web UI (React + Vite + shadcn/ui)
├── tests/                 # Test suite (unit, integration, e2e)
├── docs/                  # Documentation
│   ├── tracks/           # Per-track organization (dspy, ics, testing, etc.)
│   ├── MASTER_ROADMAP.md # Single source of truth for project navigation
│   └── archive/          # Completed work
│
├── scripts/               # Utility scripts
├── migrations/            # Database migrations (Supabase)
└── debug/                 # Debug data and artifacts
```

**Full structure**: [`REPOSITORY_ORGANIZATION.md`](REPOSITORY_ORGANIZATION.md)

### Key Development Guidelines

**Critical Rules** (see [`CLAUDE.md`](CLAUDE.md) for complete guidelines):
- ✅ **ALWAYS use `uv`** for Python packages (never pip/poetry)
- ✅ **Commit BEFORE testing** - Tests must run against committed code
- ✅ **Use feature branches** - Never commit directly to main
- ✅ **Organize files** - Follow repository organization rules
- ❌ **NEVER commit secrets** - Use environment variables or Modal secrets
- 📋 **Track work with Beads** - Use beads framework for task management

### Contributing

1. Read the guidelines: [`CLAUDE.md`](CLAUDE.md)
2. Create feature branch: `git checkout -b feature/your-feature`
3. Write tests for new functionality
4. Follow organization rules (files in correct directories)
5. Create PR: `gh pr create --title "..." --body "..."`

---

## Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check Python version
python --version  # Must be 3.11+

# Reinstall dependencies
uv sync --reinstall
```

**Frontend won't start:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Tests failing:**
```bash
# Kill old background processes
pkill -f pytest
pkill -f uvicorn

# Fresh test run
uv run pytest -v
```

**Modal deployment issues:**
```bash
# Check Modal authentication
modal token list

# Verify secrets
modal secret list

# Check app status
modal app list
```

**Database connection issues:**
```bash
# Verify Supabase connection
./scripts/database/verify_supabase_connection.sh

# Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

### Getting Help

- **Documentation**: Check [`docs/MASTER_ROADMAP.md`](docs/MASTER_ROADMAP.md) for navigation
- **Known Issues**: See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)
- **Development Guide**: See [`CLAUDE.md`](CLAUDE.md)
- **Issues**: Report bugs at https://github.com/rand/lift-sys/issues

---

## Project Status

**Current Phase**: Documentation consolidation & test stabilization complete ✅

**Core Systems**:
- ✅ **Tests**: 148/148 core tests passing (100%)
- ✅ **Frontend (ICS)**: 74/74 E2E tests passing, Phase 1 complete
- ✅ **Backend API**: Session management, IR validation, code generation
- ✅ **Infrastructure**: Modal deployment, Supabase integration, llguidance migration complete
- 🚧 **DSPy Architecture**: 10/19 holes resolved (53%), Phase 3 active

**Active Tracks** (see [`docs/MASTER_ROADMAP.md`](docs/MASTER_ROADMAP.md)):
1. **DSPy** - Declarative LLM orchestration (53% complete)
2. **ICS** - Integrated Context Studio frontend (Phase 1 complete)
3. **Testing** - Test infrastructure and E2E validation (stabilization complete)
4. **Infrastructure** - Deployment and observability (stable)
5. **Observability** - Honeycomb integration (planning complete)

**Documentation**:
- 📚 44 planning documents with structured YAML frontmatter
- 📖 Master Roadmap for navigation
- 🗂️ Track-based organization (5 tracks)
- ⏱️ Session handoff: <2 minutes (15-30x improvement)

**For detailed status**: See track STATUS files in [`docs/tracks/`](docs/tracks/)

---

## Key Resources

- **Master Roadmap**: [`docs/MASTER_ROADMAP.md`](docs/MASTER_ROADMAP.md) - Project navigation and work selection
- **Development Guide**: [`CLAUDE.md`](CLAUDE.md) - Development practices and protocols
- **IR Specification**: [`docs/IR_SPECIFICATION.md`](docs/IR_SPECIFICATION.md) - Complete IR design (PRD + RFC)
- **Workflow Guides**: [`docs/WORKFLOW_GUIDES.md`](docs/WORKFLOW_GUIDES.md) - Step-by-step tutorials
- **API Documentation**: [`docs/tracks/infrastructure/API_SESSION_MANAGEMENT.md`](docs/tracks/infrastructure/API_SESSION_MANAGEMENT.md)

---

**License**: MIT (see [`LICENSE`](LICENSE))
