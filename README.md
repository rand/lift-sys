# lift-sys

[![Test Suite](https://github.com/rand/lift-sys/actions/workflows/test.yml/badge.svg)](https://github.com/rand/lift-sys/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

`lift-sys` is a modular, verifiable AI-native software development environment, supporting next-generation constrained code generation and reverse-mode formalization, aiming to democratize high-quality software creation while keeping users in control.

> **Test Status**: 269/295 tests passing (91.2%). The 26 failing tests are known test isolation issues documented in `development_records/TEST_ISOLATION_FIXES.md`. All core functionality is verified and working.

Most AI coding tools still assume an engineer will clean up and validate outputs, which excludes semi-technical teammates and slows delivery. Tools aimed at non-technical users often amplify ambiguity, create unmaintainable code, and add risk in real codebases.

`lift-sys` flips this. It makes high-quality software creation accessible while keeping engineers in control, across both greenfield and existing repositories. `lift-sys` brings human-centered, machine-verifiable affordances to understanding, creating, and editing code, empowering semi-technical contributors and engineers.

Two complementary modes:

* **Forward mode** turns natural language into a formal, human-readable specification and generates code that must satisfy types, policies, and executable proofs. The value: faster, safer creation of new features from intent, with evidence attached.
* **Reverse mode** attaches to an existing repository, recovers a behavioral model from code and traces, and lifts it into a structured intermediate form. The value: safe edits and refactors in legacy code, with provenance and constraints ensuring correctness.

Together, these modes let teams move fluidly between building new systems and responsibly evolving the ones they already depend on.

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

1. Install [`uv`](https://github.com/astral-sh/uv).
2. Create the virtual environment and install dependencies:

```bash
uv sync
```

3. Start both the backend and frontend:

```bash
./start.sh
```

This will launch:
- **Backend API**: http://localhost:8000 (API docs at http://localhost:8000/docs)
- **Frontend**: http://localhost:5173

Alternatively, you can run services individually:

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

## Project Structure

- `lift_sys/`: Core backend, IR, verification, planning, and workflow modules.
- `frontend/`: Web client built with Vite + React following the shadcn-inspired design system.
- `design/`: Experience mapping, affordance inventory, and design system documentation.
- `tests/`: Automated tests for critical subsystems.
- `lift_sys/providers`: Provider adapters for Anthropic, OpenAI, Google Gemini, and the local vLLM runtime.
- `lift_sys/services`: Hybrid orchestration, reasoning, generation, and verification services.
- `lift_sys/auth`: OAuth and encrypted token storage utilities.
- `lift_sys/infrastructure`: Modal deployment configuration helpers.

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

## Development

Run tests with:

```bash
uv run pytest
```
