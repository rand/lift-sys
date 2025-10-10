# lift-sys

`lift-sys` is a modular, verifiable AI-native software development environment.

## Getting Started

1. Install [`uv`](https://github.com/astral-sh/uv).
2. Create the virtual environment and install dependencies:

```bash
uv sync
```

3. Run the FastAPI server:

```bash
uv run uvicorn lift_sys.api.server:app --reload
```

4. Launch the Textual TUI:

```bash
uv run python -m lift_sys.main
```

## Project Structure

- `lift_sys/`: Core backend, IR, verification, planning, and workflow modules.
- `frontend/`: Web client built with Vite + React following the shadcn-inspired design system.
- `design/`: Experience mapping, affordance inventory, and design system documentation.
- `tests/`: Automated tests for critical subsystems.

## Development

Run tests with:

```bash
uv run pytest
```

