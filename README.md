# lift-sys

`lift-sys` is a modular, verifiable AI-native software development environment.

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

