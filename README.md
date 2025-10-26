# lift-sys


[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

`lift-sys` is a modular, verifiable AI-native software development environment, supporting next-generation constrained code generation and reverse-mode formalization, aiming to democratize high-quality software creation while keeping users in control.

Most AI coding tools still assume an engineer will clean up and validate outputs, which excludes semi-technical teammates and slows delivery. Tools aimed at non-technical users often amplify ambiguity, create unmaintainable code, and add risk in real codebases.

`lift-sys` flips this. It makes high-quality software creation accessible while keeping engineers in control, across both greenfield and existing repositories. `lift-sys` brings human-centered, machine-verifiable affordances to understanding, creating, and editing code, empowering semi-technical contributors and engineers.

Two complementary modes:

* **Forward mode** turns natural language into a formal, human-readable specification and generates code that must satisfy types, policies, and executable proofs. The value: faster, safer creation of new features from intent, with evidence attached.
* **Reverse mode** attaches to an existing repository, recovers a behavioral model from code and traces, and lifts it into a structured intermediate form. The value: safe edits and refactors in legacy code, with provenance and constraints ensuring correctness.

Together, these modes let teams move fluidly between building new systems and responsibly evolving the ones they already depend on.

## 📊 Current Status (Updated October 25, 2025)

**📌 For detailed status, see [CURRENT_STATE.md](CURRENT_STATE.md) and [docs/issues/BACKEND_STATUS.md](docs/issues/BACKEND_STATUS.md)**

**Active Work**:
- 🎯 **ICS (Integrated Context Studio)** - Primary user interface in development
  - Interactive specification editor with real-time semantic analysis
  - Phase 4 complete (32 Beads issues created), Phase 1 implementation starting
  - Timeline: 8-10 days for MVP (22/22 E2E tests passing)

**Forward Mode Pipeline**: **PARTIALLY WORKING** ⚠️
- ✅ **Compilation**: 100% success (generated code is syntactically valid)
- ✅ **Execution**: 80% success (8/10 tests pass)
- ❌ **Known Failures**: 3 persistent issues (find_index, get_type_name, is_valid_email)
- ⚠️ **XGrammar Status**: Unclear if fully functional (llguidance migration in progress)
- ⚠️ **132 Known Gaps**: Backend issues labeled `backend-gap` (features incomplete or broken)
- ✅ **Working Components**: AST Repair (Phase 4), Assertion Checking (Phase 5), Constraints (Phase 7, 97.8% tests passing)

**Infrastructure**: **MIXED STATUS**
- ✅ **Modal.com**: Operational (LLM inference, some latency issues)
- ⏸️ **Supabase**: Schema designed, deployment pending (lift-sys-71 in progress)
- ⏸️ **Honeycomb**: Observability planned, not started

**Queued Enhancements** (Researched, Not Implemented):
- ⏸️ **DSPy Architecture** (H1-H19): Systematic LLM orchestration, queued post-ICS
- ⏸️ **ACE Enhancement** (3 issues): Advanced code evolution, researched
- ⏸️ **MUSLR Enhancement** (4 issues): Multi-stage reasoning, researched

**Reverse Mode**: **PLANNING PHASE** 🚧
- Infrastructure planning in progress
- Not yet implemented

**Current Priorities**:
1. ICS Phase 1 implementation (ACTIVE)
2. Backend stabilization (fix 3 persistent failures, investigate XGrammar)
3. Infrastructure deployment (Supabase, Honeycomb)
4. Backend gap closure (systematic)

See [`docs/IR_SPECIFICATION.md`](docs/IR_SPECIFICATION.md) for the complete IR design specification (PRD + RFC + Reference Spec).

## Key Features

### Iterative Prompt-to-IR Refinement

`lift-sys` now includes a complete session management system for iterative specification refinement:

- **Natural Language Start**: Begin with a simple prompt describing your intent
- **Typed Holes**: System identifies ambiguities (missing types, unclear constraints)
- **AI-Assisted Resolution**: Get smart suggestions for each ambiguity
- **Incremental Refinement**: Resolve one ambiguity at a time, see IR evolve
- **SMT Verification**: Automatic validation ensures logical consistency
- **Multi-Interface**: Same workflow available via Web UI, CLI, TUI, and Python SDK

**Example workflow:**
```
Prompt: "A function that validates email addresses"
  ↓
System identifies holes: function_name, parameter_type, return_type
  ↓
You resolve iteratively with AI assists
  ↓
Get validated IR ready for code generation
```

See [Workflow Guides](docs/WORKFLOW_GUIDES.md) for detailed examples across all interfaces.

## Getting Started

### Prerequisites

1. **Install [`uv`](https://github.com/astral-sh/uv)** - Python package manager (NEVER use pip/poetry)
2. **Install Node.js 18+** - For frontend development (if using web UI)
3. **Clone the repository**:
   ```bash
   git clone https://github.com/rand/lift-sys.git
   cd lift-sys
   ```

### Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Start development servers**:
   ```bash
   ./scripts/setup/start.sh
   ```

   This launches:
   - **Backend API**: http://localhost:8000 (API docs at http://localhost:8000/docs)
   - **Frontend**: http://localhost:5173

### Alternative: Run Services Individually

**Backend only:**
```bash
uv run uvicorn lift_sys.api.server:app --reload
```

**Frontend only:**
```bash
cd frontend && npm run dev
```

**Textual TUI:**
```bash
uv run python -m lift_sys.main
```

### Database Setup (Optional - for persistence)

If using Supabase for session storage:

1. **Set up Supabase** (see [`docs/supabase/SUPABASE_QUICK_START.md`](docs/supabase/SUPABASE_QUICK_START.md))
2. **Run migrations**:
   ```bash
   python scripts/database/run_migrations.py
   ```
3. **Configure environment** (create `.env.local`):
   ```bash
   SUPABASE_URL=<your-url>
   SUPABASE_ANON_KEY=<your-anon-key>
   SUPABASE_SERVICE_KEY=<your-service-key>
   ```

### Running Tests

```bash
# Run full test suite
uv run pytest

# Run with coverage
uv run pytest --cov=lift_sys

# Run specific test file
uv run pytest tests/test_ir.py
```

**See [`CLAUDE.md`](CLAUDE.md) for complete development guidelines.**

## Quick Start: Session Management

### Web UI

1. Navigate to http://localhost:5173
2. Click "Prompt Workbench"
3. Enter a prompt: "A function that adds two numbers"
4. Click "Create Session"
5. Resolve ambiguities with AI assists
6. Finalize and export IR

### CLI

```bash
# Create session
uv run python -m lift_sys.cli session create \
  --prompt "A function that adds two numbers"

# List sessions
uv run python -m lift_sys.cli session list

# Get assists
uv run python -m lift_sys.cli session assists <session-id>

# Resolve a hole
uv run python -m lift_sys.cli session resolve \
  <session-id> hole_function_name "add_numbers"

# Finalize
uv run python -m lift_sys.cli session finalize <session-id> --output ir.json
```

### Python SDK

```python
from lift_sys.client import SessionClient

client = SessionClient("http://localhost:8000")

# Create session
session = client.create_session(prompt="A function that adds two numbers")

# Get AI suggestions
assists = client.get_assists(session.session_id)

# Resolve holes
session = client.resolve_hole(
    session_id=session.session_id,
    hole_id="hole_function_name",
    resolution_text="add_numbers"
)

# Finalize
result = client.finalize_session(session.session_id)
ir = result.ir
```

For complete examples and workflows, see:
- [Workflow Guides](docs/WORKFLOW_GUIDES.md) - Step-by-step tutorials
- [API Documentation](docs/API_SESSION_MANAGEMENT.md) - Complete API reference
- [Example Script](examples/session_workflow.py) - Working Python example

## Reverse Mode: Analyzing Existing Code

Reverse mode extracts specifications from existing codebases using static and dynamic analysis. It supports both single-file and whole-project analysis modes.

### Two Analysis Modes

**Project Mode** (default): Analyzes all Python files in a repository
- Automatically discovers and analyzes all `.py` files
- Excludes common directories (venv, node_modules, __pycache__)
- Shows progress tracking for multi-file analysis
- Returns multiple IRs, one per file

**File Mode**: Analyzes a specific module
- Targets a single Python file
- Backward compatible with previous behavior
- Returns a single IR

### Web UI

1. Navigate to http://localhost:5173
2. Click "Repository"
3. Connect a GitHub repository or use local repository
4. Choose analysis mode:
   - **Entire Project**: Analyze all files in the repository
   - **Single File**: Analyze a specific module
5. Click "Analyze" to start reverse mode analysis
6. View results with search and filtering
7. Click "View Details" on any file to see the complete specification

### API

**Project Mode** (analyze entire repository):
```bash
curl -X POST http://localhost:8000/api/reverse \
  -H "Content-Type: application/json" \
  -d '{
    "module": null,
    "analyze_all": true,
    "queries": ["security/default"],
    "entrypoint": "main"
  }'
```

**File Mode** (analyze single file):
```bash
curl -X POST http://localhost:8000/api/reverse \
  -H "Content-Type: application/json" \
  -d '{
    "module": "src/utils.py",
    "queries": ["security/default"],
    "entrypoint": "main"
  }'
```

Response format:
```json
{
  "irs": [
    {
      "intent": {"summary": "Function description"},
      "signature": {"name": "function_name", "parameters": [], "returns": "str"},
      "effects": [],
      "assertions": [],
      "metadata": {
        "source_path": "src/utils.py",
        "origin": "reverse",
        "language": "python"
      }
    }
  ],
  "progress": []
}
```

### Python SDK

```python
from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

# Initialize lifter
config = LifterConfig(
    codeql_queries=["security/default"],
    run_codeql=True,
    run_daikon=True
)
lifter = SpecificationLifter(config)

# Load repository
lifter.load_repository("/path/to/repo")

# Project mode: analyze all files
irs = lifter.lift_all(max_files=100)  # Optional limit
print(f"Analyzed {len(irs)} files")

# File mode: analyze single file
ir = lifter.lift("src/utils.py")
print(f"Function: {ir.signature.name}")
```

### Progress Tracking

When analyzing multiple files, the API provides real-time progress updates via WebSocket:

```json
{
  "type": "progress",
  "scope": "reverse",
  "stage": "file_analysis",
  "status": "running",
  "message": "Analyzing src/utils.py (5/20)",
  "current": 5,
  "total": 20,
  "file": "src/utils.py"
}
```

### Analysis Features

- **File Discovery**: Automatically finds all Python files, excluding common build/cache directories
- **Partial Results**: Analysis continues even if individual files fail
- **Progress Callbacks**: Real-time updates during multi-file analysis
- **Metadata Preservation**: Each IR includes source file path and analysis provenance
- **Search & Filter**: Results can be filtered by file path, function name, or content
- **Navigation**: Click through from overview to detailed specifications

For more details, see:
- [Reverse Mode Documentation](docs/REVERSE_MODE.md) - Complete feature guide
- [Performance Guide](docs/PERFORMANCE.md) - Benchmarks and optimization

## Project Structure

```
lift-sys/
├── lift_sys/              # Core Python package
│   ├── ir/               # Intermediate Representation definitions
│   ├── forward_mode/     # NLP → IR → Code pipeline
│   ├── reverse_mode/     # Code → IR recovery
│   ├── validation/       # IR and code validation
│   ├── providers/        # LLM provider integrations (Modal, Anthropic, OpenAI, Google)
│   ├── api/              # FastAPI backend server
│   ├── storage/          # Session storage (InMemory, Supabase)
│   ├── services/         # Hybrid orchestration and verification
│   ├── auth/             # OAuth and encrypted token storage
│   └── infrastructure/   # Modal deployment configuration
│
├── frontend/              # Web UI (Vite + React + shadcn/ui)
├── design/                # Design system and UX documentation
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── e2e/              # End-to-end tests
│   └── archive/          # Deprecated tests
│
├── docs/                  # Documentation (organized by category)
│   ├── supabase/         # Database setup and migrations
│   ├── observability/    # Monitoring and telemetry
│   ├── conjecturing/     # Conjecturing feature docs
│   ├── benchmarks/       # Performance testing results
│   ├── phases/           # Phase completion reports
│   ├── planning/         # Project planning documents
│   ├── fixes/            # Bug fix summaries
│   └── archive/          # Deprecated documentation
│
├── scripts/               # Utility scripts (organized by purpose)
│   ├── benchmarks/       # Performance testing scripts
│   ├── database/         # Database utilities and migrations
│   ├── setup/            # Project setup scripts
│   └── website/          # Website maintenance
│
├── migrations/            # Supabase database migrations (ordered SQL files)
├── debug/                 # Debug data and test artifacts
│
├── CLAUDE.md             # Project-specific development guidelines
├── REPOSITORY_ORGANIZATION.md  # File organization rules
├── SEMANTIC_IR_ROADMAP.md      # Product roadmap
└── KNOWN_ISSUES.md       # Current bugs and limitations
```

**See [`REPOSITORY_ORGANIZATION.md`](REPOSITORY_ORGANIZATION.md) for complete structure guidelines.**

## Modal Hybrid Deployment

The backend can now deploy as a [Modal](https://modal.com) application using `lift_sys/modal_app.py`. The deployment boots
custom images for API serving and vLLM-based constrained generation, provisions shared volumes for model weights, and
initialises Modal Dicts for encrypted token and preference storage. During local development the same abstractions are
available through in-memory shims so the API can be exercised without Modal credentials.

### Infrastructure automation

`lift_sys/infrastructure/iac.py` provides repeatable deployment automation so teams can manage infrastructure from
source control. The following commands are available:

- Deploy the current app definition:

  ```bash
  uv run python -m lift_sys.infrastructure.iac deploy
  ```

- Force an update after code or image changes:

  ```bash
  uv run python -m lift_sys.infrastructure.iac update
  ```

- Adjust worker counts and redeploy:

  ```bash
  uv run python -m lift_sys.infrastructure.iac scale --api-replicas 2 --vllm-concurrency 8 --apply
  ```

Scaling commands write to `lift_sys/infrastructure/deployment_settings.json`, ensuring the desired state of the Modal
deployment is versioned alongside the application code.

### Multi-provider orchestration

- External providers (Anthropic, OpenAI, Gemini) expose planning and reasoning capabilities. OAuth flows are coordinated
  through `/api/auth/*` endpoints, backed by `TokenStore` which encrypts tokens at rest.
- The local vLLM provider handles structured code generation with Outlines-compatible prompts.
- `HybridOrchestrator` routes work between providers, falling back to the local runner if an external API becomes
  unavailable.

### Frontend controls

The configuration view now includes a provider selector that surfaces provider capability flags, connection status, and
quick OAuth initiation. Administrators can choose the primary provider and configure hybrid failover policies directly
from the UI.

## Development Workflow

### Repository Organization

This repository follows strict organization rules to maintain cleanliness and discoverability:

- **Documentation**: All `.md` files go to `docs/{category}/` subdirectories
- **Scripts**: All utility scripts go to `scripts/{category}/` subdirectories
- **Debug Data**: All debug files go to `debug/` directory
- **Root Directory**: Only core project files (README, LICENSE, config files)

**See [`REPOSITORY_ORGANIZATION.md`](REPOSITORY_ORGANIZATION.md) for complete rules.**

### Development Guidelines

**Project-specific guidelines**: [`CLAUDE.md`](CLAUDE.md) - Development practices, testing protocols, security rules

**Key rules:**
- **ALWAYS use `uv`** for Python package management (never pip/poetry)
- **NEVER commit before testing** - Critical: Commit first, then test to avoid stale results
- **NEVER commit secrets** - Use environment variables or Modal secrets
- **Use Beads** for task tracking - All agentic work uses the Beads framework
- **Organize files** - No loose files in root directory

### Running Tests

```bash
# Run full test suite
uv run pytest

# Run with coverage
uv run pytest --cov=lift_sys

# Run specific category
uv run pytest tests/unit/
uv run pytest tests/integration/

# Run benchmarks
./scripts/benchmarks/run_benchmark.sh
```

### Utility Scripts

```bash
# Start development servers (backend + frontend)
./scripts/setup/start.sh

# Run database migrations
python scripts/database/run_migrations.py

# Verify Supabase connection
./scripts/database/verify_supabase_connection.sh

# Run performance benchmarks
./scripts/benchmarks/run_benchmark.sh

# Update website plan page
./scripts/website/update-plan-page.sh
```

See [`scripts/README.md`](scripts/README.md) for complete script documentation.

### Contributing

1. **Read the guidelines**: [`CLAUDE.md`](CLAUDE.md) and [`REPOSITORY_ORGANIZATION.md`](REPOSITORY_ORGANIZATION.md)
2. **Create feature branch**: `git checkout -b feature/your-feature`
3. **Follow organization rules**: Put files in correct directories
4. **Write tests**: Add tests for new functionality
5. **Update documentation**: Document new features in `docs/{category}/`
6. **Create PR**: Use `gh pr create` with descriptive title and body

### Documentation

All documentation is organized in the `docs/` directory:

- **Supabase**: [`docs/supabase/`](docs/supabase/) - Database setup, migrations, schema
- **Observability**: [`docs/observability/`](docs/observability/) - Monitoring and telemetry
- **Benchmarks**: [`docs/benchmarks/`](docs/benchmarks/) - Performance results
- **Planning**: [`docs/planning/`](docs/planning/) - Project planning and assessments
- **Phases**: [`docs/phases/`](docs/phases/) - Phase completion reports

### Key Resources

- **Development Guidelines**: [`CLAUDE.md`](CLAUDE.md)
- **Organization Rules**: [`REPOSITORY_ORGANIZATION.md`](REPOSITORY_ORGANIZATION.md)
- **IR Design Specification**: [`docs/IR_SPECIFICATION.md`](docs/IR_SPECIFICATION.md) - Complete PRD, RFC, and reference spec
- **Known Issues**: [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)
- **Release Notes**: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)
