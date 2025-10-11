# Implementation Plan - v0.3.0
**Start Date**: October 11, 2025
**Target Completion**: January 31, 2026
**Status**: Ready to Execute

---

## Overview

This document provides a concrete, step-by-step implementation plan for transforming lift-sys from beta (v0.2.1) to production-ready (v0.3.0).

**Based On:**
- `NEXT_PHASE_PLAN.md` - Strategic roadmap
- `CODEBASE_REVIEW.md` - Current state assessment
- `IMPROVEMENT_PLAN.md` - Previous phases learnings

**Approach:**
- Work in 2-week sprints
- Each task has clear acceptance criteria
- Dependencies are explicitly tracked
- Progress tracked in GitHub Projects

---

## Sprint 0: Setup & Quick Wins (Week 1-2)

### Goal
Set up development infrastructure and achieve quick wins to build momentum.

### Tasks

#### Task 0.1: Install Development Tools
**Priority**: P0
**Effort**: 2 hours
**Dependencies**: None

**Steps:**
```bash
# Install code quality tools
uv add --dev ruff mypy

# Install testing tools
uv add --dev pytest-cov pytest-benchmark pytest-xdist

# Install pre-commit
uv add --dev pre-commit
```

**Acceptance Criteria:**
- [ ] All tools installed successfully
- [ ] Can run `uv run ruff check lift_sys/`
- [ ] Can run `uv run mypy lift_sys/`
- [ ] Can run `uv run pytest tests/ --cov`

**Verification:**
```bash
uv run ruff --version
uv run mypy --version
uv run pytest --version
```

---

#### Task 0.2: Configure Code Quality Tools
**Priority**: P0
**Effort**: 3 hours
**Dependencies**: Task 0.1

**File Changes:**

**A. Update `pyproject.toml`:**
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
exclude = [".venv", "build", "dist"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start lenient, tighten over time
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "-v",
    "--strict-markers",
    "--cov=lift_sys",
    "--cov-report=term-missing",
    "--cov-report=html",
]
```

**B. Create `.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
```

**Commands to run:**
```bash
# Format all code
uv run ruff format lift_sys/ tests/

# Fix linting issues
uv run ruff check --fix lift_sys/ tests/

# Install pre-commit hooks
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files
```

**Acceptance Criteria:**
- [ ] All files formatted with Ruff
- [ ] Zero linting errors (warnings OK for now)
- [ ] Pre-commit hooks installed
- [ ] Pre-commit passes on all files

---

#### Task 0.3: Set Up GitHub Actions CI/CD
**Priority**: P0
**Effort**: 4 hours
**Dependencies**: Task 0.2

**File to Create: `.github/workflows/test.yml`**
```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: uv sync

      - name: Run Ruff
        run: uv run ruff check lift_sys/ tests/

      - name: Check formatting
        run: uv run ruff format --check lift_sys/ tests/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: |
          uv run pytest tests/ \
            --cov=lift_sys \
            --cov-report=xml \
            --cov-report=term \
            -v
        env:
          LIFT_SYS_ENABLE_DEMO_USER_HEADER: "1"

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-${{ matrix.python-version }}
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build
```

**Acceptance Criteria:**
- [ ] GitHub Actions workflow file created
- [ ] Tests run automatically on push
- [ ] All matrix combinations tested (3 Python versions)
- [ ] Frontend tests run
- [ ] Code coverage uploaded to Codecov

**Setup Required:**
1. Create Codecov account and get token
2. Add `CODECOV_TOKEN` to GitHub repository secrets
3. Create a test PR to verify workflow runs

---

#### Task 0.4: Add Performance Benchmarks
**Priority**: P1
**Effort**: 4 hours
**Dependencies**: Task 0.1

**File to Create: `tests/performance/test_benchmarks.py`**
```python
"""Performance benchmarks for lift-sys.

Run with: pytest tests/performance/ --benchmark-only
"""
import pytest
from lift_sys.ir.parser import IRParser
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.verifier.smt_checker import SMTChecker


class TestParserBenchmarks:
    """Parser performance benchmarks."""

    def test_parse_simple_ir(self, benchmark, sample_simple_ir):
        """Benchmark parsing simple IR."""
        parser = IRParser()
        result = benchmark(parser.parse, sample_simple_ir)
        assert result is not None
        # Target: < 100ms

    def test_parse_complex_ir(self, benchmark, sample_complex_ir):
        """Benchmark parsing complex IR with many clauses."""
        parser = IRParser()
        result = benchmark(parser.parse, sample_complex_ir)
        assert result is not None
        # Target: < 200ms


class TestSessionBenchmarks:
    """Session management benchmarks."""

    def test_session_creation_from_prompt(self, benchmark, api_client):
        """Benchmark session creation from prompt."""
        def create_session():
            return api_client.post(
                "/spec-sessions",
                json={
                    "source": "prompt",
                    "prompt": "A function that validates email addresses"
                }
            )

        result = benchmark(create_session)
        assert result.status_code == 200
        # Target: < 500ms

    def test_hole_resolution(self, benchmark, configured_api_client):
        """Benchmark hole resolution."""
        # Create session first
        session_response = configured_api_client.post(
            "/spec-sessions",
            json={"source": "prompt", "prompt": "Test function"}
        )
        session_id = session_response.json()["session_id"]

        # Benchmark resolution
        def resolve_hole():
            return configured_api_client.post(
                f"/spec-sessions/{session_id}/resolve",
                json={
                    "hole_id": "function_name",
                    "resolution": "validate_email"
                }
            )

        result = benchmark(resolve_hole)
        # Target: < 300ms


class TestVerifierBenchmarks:
    """SMT verifier benchmarks."""

    def test_verify_simple_assertion(self, benchmark, simple_ir):
        """Benchmark simple assertion verification."""
        checker = SMTChecker()
        result = benchmark(checker.verify, simple_ir)
        assert result is not None
        # Target: < 200ms
```

**File to Create: `tests/performance/conftest.py`**
```python
"""Fixtures for performance tests."""
import pytest


@pytest.fixture
def sample_simple_ir():
    """Simple IR text for benchmarking."""
    return """
    intent {
        summary: "Add two numbers"
    }

    sig add(a: int, b: int) -> int

    assert a >= 0
    assert b >= 0
    """


@pytest.fixture
def sample_complex_ir():
    """Complex IR with many clauses."""
    return """
    intent {
        summary: "Binary search in sorted array"
    }

    sig binary_search(arr: list, target: int, low: int, high: int) -> int

    assert len(arr) >= 0
    assert 0 <= low <= len(arr)
    assert 0 <= high <= len(arr)
    assert low <= high

    effect {
        reads: arr[i] for i in range(low, high+1)
    }

    assert result == -1 or arr[result] == target
    assert result == -1 or low <= result <= high
    """
```

**Commands:**
```bash
# Run benchmarks
uv run pytest tests/performance/ --benchmark-only

# Save baseline
uv run pytest tests/performance/ --benchmark-only --benchmark-save=baseline

# Compare to baseline
uv run pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

**Acceptance Criteria:**
- [ ] 10+ benchmarks covering key operations
- [ ] Baseline established and saved
- [ ] Performance targets documented
- [ ] Benchmarks run in < 30 seconds total

---

## Sprint 1: E2E Testing (Week 3-4)

### Goal
Add comprehensive end-to-end testing for web UI and TUI.

### Tasks

#### Task 1.1: Install E2E Testing Tools
**Priority**: P0
**Effort**: 1 hour
**Dependencies**: None

**Commands:**
```bash
# Install Playwright
uv add --dev playwright pytest-playwright
uv run playwright install

# Install Textual testing
uv add --dev textual[dev]
```

**Acceptance Criteria:**
- [ ] Playwright installed with browsers
- [ ] Textual testing available
- [ ] Can run `uv run playwright --version`

---

#### Task 1.2: Create E2E Tests for Web UI
**Priority**: P0
**Effort**: 12 hours (spread over 3 days)
**Dependencies**: Task 1.1

**File to Create: `tests/e2e/test_web_ui_workflows.py`**
```python
"""End-to-end tests for web UI workflows."""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def backend_url():
    """Backend URL for E2E tests."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def frontend_url():
    """Frontend URL for E2E tests."""
    return "http://localhost:5173"


class TestPromptWorkbench:
    """E2E tests for Prompt Workbench."""

    def test_complete_session_workflow(self, page: Page, frontend_url: str):
        """Test complete prompt-to-IR workflow."""
        # Navigate to app
        page.goto(frontend_url)
        expect(page).to_have_title(/lift-sys/i)

        # Click Prompt Workbench
        page.click("text=Prompt Workbench")

        # Enter prompt
        prompt_input = page.locator("textarea[placeholder*='prompt']")
        prompt_input.fill("A function that adds two numbers")

        # Create session
        page.click("button:has-text('Create Session')")

        # Wait for session to be created
        expect(page.locator("text=Session created")).to_be_visible(timeout=5000)

        # Verify ambiguities appear
        ambiguity_badges = page.locator("[data-testid='ambiguity-badge']")
        expect(ambiguity_badges).to_have_count(3, timeout=3000)  # function_name, param_types, return_type

        # Resolve first ambiguity (function_name)
        ambiguity_badges.first.click()

        # Get AI assist
        page.click("button:has-text('Get Assist')")
        expect(page.locator("[data-testid='assist-suggestions']")).to_be_visible(timeout=3000)

        # Click first suggestion or enter manually
        resolution_input = page.locator("input[data-testid='resolution-input']")
        resolution_input.fill("add_numbers")

        # Submit resolution
        page.click("button:has-text('Resolve')")

        # Verify hole resolved
        expect(page.locator("text=Resolved")).to_be_visible(timeout=2000)

        # Verify IR updated
        ir_view = page.locator("[data-testid='ir-view']")
        expect(ir_view).to_contain_text("add_numbers")

    def test_session_list_and_detail(self, page: Page, frontend_url: str):
        """Test session list and detail views."""
        page.goto(frontend_url)

        # Navigate to Sessions
        page.click("text=Sessions")

        # Verify sessions list loads
        expect(page.locator("[data-testid='sessions-list']")).to_be_visible()

        # Create a new session
        page.click("button:has-text('New Session')")
        page.locator("textarea").fill("Test session")
        page.click("button:has-text('Create')")

        # Verify appears in list
        expect(page.locator("text=Test session")).to_be_visible(timeout=3000)

        # Click to view details
        page.click("text=Test session")

        # Verify detail view
        expect(page.locator("[data-testid='session-detail']")).to_be_visible()

    def test_error_handling(self, page: Page, frontend_url: str):
        """Test error handling in UI."""
        page.goto(f"{frontend_url}/prompt-workbench")

        # Try to create session with empty prompt
        page.click("button:has-text('Create Session')")

        # Should show validation error
        expect(page.locator("text=required")).to_be_visible()

    def test_session_finalization(self, page: Page, frontend_url: str):
        """Test session finalization and export."""
        # Setup: Create and fully resolve a session
        page.goto(f"{frontend_url}/prompt-workbench")
        page.locator("textarea").fill("Simple test function")
        page.click("button:has-text('Create Session')")

        # Wait for session
        expect(page.locator("[data-testid='session-detail']")).to_be_visible(timeout=5000)

        # Resolve all holes (mock this for now)
        # ... resolution steps ...

        # Finalize session
        page.click("button:has-text('Finalize')")

        # Verify finalized
        expect(page.locator("text=finalized")).to_be_visible()

        # Export IR
        page.click("button:has-text('Export')")

        # Verify download
        download = page.wait_for_event("download", timeout=3000)
        assert download.suggested_filename.endswith(".ir")
```

**File to Create: `tests/e2e/conftest.py`**
```python
"""Fixtures for E2E tests."""
import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


@pytest.fixture(autouse=True)
def demo_auth(page: Page):
    """Set up demo authentication for all tests."""
    # Add demo user header via browser context
    page.set_extra_http_headers({"x-demo-user": "e2e-test"})
```

**Acceptance Criteria:**
- [ ] 15+ E2E tests covering all workflows
- [ ] Tests pass consistently (no flakiness)
- [ ] All user journeys covered
- [ ] Error cases tested
- [ ] Tests run in < 2 minutes

**Run Command:**
```bash
# Start backend and frontend first
./start.sh

# In another terminal
uv run pytest tests/e2e/ -v
```

---

#### Task 1.3: Fix TUI Tests with Textual Testing
**Priority**: P1
**Effort**: 8 hours
**Dependencies**: Task 1.1

**File to Update: `tests/integration/test_tui_session_management.py`**

Replace mock-based tests with proper Textual testing:

```python
"""Integration tests for TUI using textual.testing."""
import pytest
from textual.pilot import Pilot
from lift_sys.main import LiftSysApp


class TestTUISessionManagement:
    """Integration tests for TUI session management."""

    @pytest.mark.asyncio
    async def test_create_session_from_prompt(self):
        """Test creating a session from prompt in TUI."""
        app = LiftSysApp()

        async with app.run_test() as pilot:
            # Navigate to Prompt Refinement tab
            await pilot.press("tab")

            # Find and focus prompt input
            prompt_input = app.query_one("#prompt-input")
            prompt_input.focus()

            # Type prompt
            await pilot.press(*"Test function")

            # Submit
            await pilot.press("ctrl+enter")

            # Wait for session to be created
            await pilot.pause(1.0)

            # Verify session appears
            assert app.state.active_session is not None
            assert app.state.active_session.status == "active"

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """Test listing sessions in TUI."""
        app = LiftSysApp()

        async with app.run_test() as pilot:
            # Trigger list sessions action
            await pilot.press("ctrl+l")

            # Wait for list to load
            await pilot.pause(0.5)

            # Verify sessions list widget visible
            sessions_list = app.query_one("#sessions-list")
            assert sessions_list.display

    @pytest.mark.asyncio
    async def test_keyboard_navigation(self):
        """Test keyboard shortcuts work."""
        app = LiftSysApp()

        async with app.run_test() as pilot:
            # Test tab switching
            await pilot.press("tab")
            await pilot.pause(0.1)

            # Test help
            await pilot.press("?")
            await pilot.pause(0.1)

            # Verify help displayed
            # (check for help modal or similar)
```

**Acceptance Criteria:**
- [ ] All 10 failing TUI tests converted to use textual.testing
- [ ] All TUI tests pass
- [ ] No more mock-based TUI tests
- [ ] Keyboard interactions tested

---

## Sprint 2: Docker & Database (Week 5-6)

### Goal
Add Docker support and PostgreSQL integration.

### Tasks

#### Task 2.1: Create Dockerfile for Backend
**Priority**: P0
**Effort**: 4 hours
**Dependencies**: None

**File to Create: `Dockerfile`**
```dockerfile
FROM python:3.12-slim as builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --frozen

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy uv and dependencies from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy application code
COPY lift_sys ./lift_sys

# Create non-root user
RUN useradd -m -u 1000 liftsys && \
    chown -R liftsys:liftsys /app

USER liftsys

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "uvicorn", "lift_sys.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File to Create: `.dockerignore`**
```
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.mypy_cache
node_modules
frontend/dist
frontend/node_modules
.git
*.md
tests/
development_records/
```

**Build and Test:**
```bash
# Build
docker build -t lift-sys:latest .

# Run
docker run -p 8000:8000 \
  -e LIFT_SYS_ENABLE_DEMO_USER_HEADER=1 \
  lift-sys:latest

# Test
curl http://localhost:8000/health
```

**Acceptance Criteria:**
- [ ] Docker image builds successfully
- [ ] Image size < 500MB
- [ ] Container starts and responds to health check
- [ ] All environment variables configurable

---

#### Task 2.2: Create Docker Compose Configuration
**Priority**: P0
**Effort**: 6 hours
**Dependencies**: Task 2.1

**File to Create: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: liftsys
      POSTGRES_USER: liftsys
      POSTGRES_PASSWORD: ${DB_PASSWORD:-liftsys_dev}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U liftsys"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://liftsys:${DB_PASSWORD:-liftsys_dev}@postgres:5432/liftsys
      - REDIS_URL=redis://redis:6379/0
      - LIFT_SYS_ENABLE_DEMO_USER_HEADER=1
      - LIFT_SYS_SESSION_SECRET=${SESSION_SECRET:-dev-secret-change-in-prod}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./lift_sys:/app/lift_sys
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
    volumes:
      - ./frontend/src:/app/src

volumes:
  postgres_data:
  redis_data:
```

**File to Create: `frontend/Dockerfile`**
```dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Expose port
EXPOSE 5173

# Run dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**File to Create: `scripts/init-db.sql`**
```sql
-- Initial database setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables (will be replaced by Alembic migrations later)
CREATE TABLE IF NOT EXISTS prompt_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_user_id ON prompt_sessions(user_id);
CREATE INDEX idx_sessions_status ON prompt_sessions(status);
```

**File to Create: `.env.example`**
```env
# Database
DB_PASSWORD=liftsys_dev
DATABASE_URL=postgresql://liftsys:liftsys_dev@localhost:5432/liftsys

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
LIFT_SYS_ENABLE_DEMO_USER_HEADER=1
LIFT_SYS_SESSION_SECRET=change-this-in-production

# Monitoring (optional)
SENTRY_DSN=
```

**Commands:**
```bash
# Copy env file
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

**Acceptance Criteria:**
- [ ] All services start successfully
- [ ] Backend connects to PostgreSQL
- [ ] Backend connects to Redis
- [ ] Frontend can reach backend
- [ ] Health checks pass for all services
- [ ] Can create and retrieve sessions

---

#### Task 2.3: Add Database Models and Migrations
**Priority**: P0
**Effort**: 12 hours
**Dependencies**: Task 2.2

**Install Dependencies:**
```bash
uv add sqlalchemy alembic asyncpg psycopg2-binary
```

**File to Create: `lift_sys/db/__init__.py`**
```python
"""Database package."""
from .base import Base, get_session
from .models import PromptSession, IRDraft

__all__ = ["Base", "get_session", "PromptSession", "IRDraft"]
```

**File to Create: `lift_sys/db/base.py`**
```python
"""Database base configuration."""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://liftsys:liftsys_dev@localhost:5432/liftsys"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_maker() as session:
        yield session
```

**File to Create: `lift_sys/db/models.py`**
```python
"""Database models."""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class PromptSession(Base):
    """Prompt session database model."""

    __tablename__ = "prompt_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    metadata = Column(JSON, default=dict)

    # Relationships
    drafts = relationship("IRDraft", back_populates="session", cascade="all, delete-orphan")


class IRDraft(Base):
    """IR draft database model."""

    __tablename__ = "ir_drafts"

    draft_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("prompt_sessions.session_id"), nullable=False)
    version = Column(Integer, nullable=False)
    ir_data = Column(JSON, nullable=False)
    validation_status = Column(String(50), nullable=False)
    ambiguities = Column(JSON, default=list)
    smt_results = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metadata = Column(JSON, default=dict)

    # Relationships
    session = relationship("PromptSession", back_populates="drafts")
```

**Initialize Alembic:**
```bash
# Initialize Alembic
uv run alembic init alembic

# Edit alembic.ini to use environment variable
# sqlalchemy.url = driver://user:pass@localhost/dbname
# Change to:
# sqlalchemy.url =
```

**File to Edit: `alembic/env.py`**
```python
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from lift_sys.db.base import Base
from lift_sys.db.models import PromptSession, IRDraft

# this is the Alembic Config object
config = context.config

# Set database URL from environment
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", "postgresql://liftsys:liftsys_dev@localhost:5432/liftsys")
)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ... rest of file unchanged
```

**Create Initial Migration:**
```bash
# Create migration
uv run alembic revision --autogenerate -m "Initial schema"

# Apply migration
uv run alembic upgrade head

# Verify
psql -h localhost -U liftsys -d liftsys -c "\dt"
```

**Acceptance Criteria:**
- [ ] SQLAlchemy models created
- [ ] Alembic configured
- [ ] Initial migration created and applied
- [ ] Can create sessions in PostgreSQL
- [ ] Can query sessions from database

---

---

## Sprint 3: Monitoring & Observability (Week 7-8)

### Goal
Add production-grade monitoring, logging, and error tracking.

### Tasks

#### Task 3.1: Add Prometheus Metrics
**Priority**: P0
**Effort**: 8 hours
**Dependencies**: Task 2.2 (Docker Compose)

**Install Dependencies:**
```bash
uv add prometheus-client prometheus-fastapi-instrumentator
```

**File to Create: `lift_sys/monitoring/__init__.py`**
```python
"""Monitoring and observability."""
from .metrics import setup_metrics, record_session_created, record_hole_resolved

__all__ = ["setup_metrics", "record_session_created", "record_hole_resolved"]
```

**File to Create: `lift_sys/monitoring/metrics.py`**
```python
"""Prometheus metrics for lift-sys."""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator

# Application info
app_info = Info("liftsys_app", "Application information")

# Counters
sessions_created = Counter(
    "liftsys_sessions_created_total",
    "Total number of sessions created",
    ["source", "user_id"]
)

holes_resolved = Counter(
    "liftsys_holes_resolved_total",
    "Total number of typed holes resolved",
    ["hole_type", "resolution_method"]
)

sessions_finalized = Counter(
    "liftsys_sessions_finalized_total",
    "Total number of sessions finalized",
    ["status"]
)

api_errors = Counter(
    "liftsys_api_errors_total",
    "Total number of API errors",
    ["endpoint", "status_code"]
)

# Histograms
session_creation_duration = Histogram(
    "liftsys_session_creation_duration_seconds",
    "Time to create a session",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

hole_resolution_duration = Histogram(
    "liftsys_hole_resolution_duration_seconds",
    "Time to resolve a typed hole",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

smt_verification_duration = Histogram(
    "liftsys_smt_verification_duration_seconds",
    "Time to verify with SMT solver",
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

llm_generation_duration = Histogram(
    "liftsys_llm_generation_duration_seconds",
    "Time for LLM to generate response",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Gauges
active_sessions = Gauge(
    "liftsys_active_sessions",
    "Number of currently active sessions"
)

pending_holes = Gauge(
    "liftsys_pending_holes",
    "Number of unresolved typed holes across all sessions"
)


def setup_metrics(app):
    """Set up Prometheus metrics for FastAPI app."""
    # Instrument FastAPI app
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="liftsys_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(app, endpoint="/metrics")

    # Set app info
    app_info.info({
        "version": "0.3.0",
        "environment": "production",
    })


def record_session_created(source: str, user_id: str):
    """Record session creation."""
    sessions_created.labels(source=source, user_id=user_id).inc()
    active_sessions.inc()


def record_hole_resolved(hole_type: str, resolution_method: str):
    """Record hole resolution."""
    holes_resolved.labels(hole_type=hole_type, resolution_method=resolution_method).inc()
    pending_holes.dec()
```

**Update `lift_sys/api/server.py`:**
```python
# Add to imports
from lift_sys.monitoring.metrics import setup_metrics

# In lifespan function or after app creation
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    setup_metrics(app)
```

**Update `docker-compose.yml` to add Prometheus:**
```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
```

**File to Create: `prometheus.yml`**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'liftsys-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

**Acceptance Criteria:**
- [ ] Prometheus metrics exported at `/metrics`
- [ ] Key operations instrumented (session creation, hole resolution, etc.)
- [ ] Prometheus scraping backend successfully
- [ ] Can query metrics in Prometheus UI
- [ ] No performance impact (< 1ms per request)

**Verification:**
```bash
# Start services
docker-compose up -d

# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus UI
open http://localhost:9090
# Query: rate(liftsys_sessions_created_total[5m])
```

---

#### Task 3.2: Add Structured Logging
**Priority**: P0
**Effort**: 6 hours
**Dependencies**: None

**Install Dependencies:**
```bash
uv add structlog python-json-logger
```

**File to Create: `lift_sys/logging_config.py`**
```python
"""Structured logging configuration."""
import logging
import sys
from typing import Any

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import add_log_level, add_logger_name


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: If True, output JSON logs. If False, use console format.
    """
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> Any:
    """Get a structured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
```

**Update `lift_sys/api/server.py`:**
```python
from lift_sys.logging_config import setup_logging, get_logger
import os

# Set up logging on module load
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("JSON_LOGS", "true").lower() == "true"
)

logger = get_logger(__name__)

# Use in routes
@app.post("/spec-sessions")
async def create_session(request: CreateSessionRequest):
    logger.info(
        "session_creation_started",
        source=request.source,
        user_id=user_id,
        has_prompt=bool(request.prompt),
    )

    try:
        session = await service.create_session(...)
        logger.info(
            "session_created",
            session_id=str(session.session_id),
            holes_count=len(session.ambiguities),
        )
        return session
    except Exception as e:
        logger.error(
            "session_creation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
```

**File to Create: `lift_sys/middleware/logging.py`**
```python
"""Logging middleware for request/response."""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from lift_sys.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response."""
        start_time = time.time()

        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration,
            )

            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
            )
            raise


# Add to app in server.py
from lift_sys.middleware.logging import LoggingMiddleware
app.add_middleware(LoggingMiddleware)
```

**Acceptance Criteria:**
- [ ] All logs output in JSON format (production)
- [ ] Request/response logging via middleware
- [ ] Key events logged (session creation, hole resolution, errors)
- [ ] Logs include context (user_id, session_id, etc.)
- [ ] Can switch to console format for development

**Verification:**
```bash
# Run with JSON logs
docker-compose up backend | jq .

# Run with console logs
LOG_LEVEL=DEBUG JSON_LOGS=false uv run uvicorn lift_sys.api.server:app
```

---

#### Task 3.3: Add Sentry Error Tracking
**Priority**: P1
**Effort**: 4 hours
**Dependencies**: None

**Install Dependencies:**
```bash
uv add sentry-sdk[fastapi]
```

**File to Create: `lift_sys/monitoring/sentry.py`**
```python
"""Sentry error tracking configuration."""
import os
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def setup_sentry(
    dsn: Optional[str] = None,
    environment: str = "production",
    release: Optional[str] = None,
) -> None:
    """Set up Sentry error tracking.

    Args:
        dsn: Sentry DSN (from environment if not provided)
        environment: Environment name (production, staging, development)
        release: Release version
    """
    dsn = dsn or os.getenv("SENTRY_DSN")

    if not dsn:
        # Sentry disabled if no DSN provided
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release or os.getenv("SENTRY_RELEASE", "0.3.0"),
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of transactions
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        # Don't send errors in development
        before_send=lambda event, hint: event if environment != "development" else None,
        # Add custom tags
        default_integrations=True,
    )


def capture_exception(error: Exception, context: dict = None) -> None:
    """Capture an exception with context.

    Args:
        error: The exception to capture
        context: Additional context to include
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_tag(key, value)
        sentry_sdk.capture_exception(error)


def set_user(user_id: str, username: str = None, email: str = None) -> None:
    """Set user context for error tracking.

    Args:
        user_id: User ID
        username: Username (optional)
        email: Email (optional)
    """
    sentry_sdk.set_user({
        "id": user_id,
        "username": username,
        "email": email,
    })
```

**Update `lift_sys/api/server.py`:**
```python
from lift_sys.monitoring.sentry import setup_sentry
import os

# Initialize Sentry on startup
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    setup_sentry(
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    setup_metrics(app)
```

**Update Dependency Injection for User Context:**
```python
from lift_sys.monitoring.sentry import set_user

async def get_current_user(...) -> str:
    """Get current user and set Sentry context."""
    user_id = ...  # Get user ID
    set_user(user_id=user_id)
    return user_id
```

**Update Error Handling:**
```python
from lift_sys.monitoring.sentry import capture_exception

try:
    # ... operation ...
except Exception as e:
    capture_exception(e, context={
        "session_id": session_id,
        "operation": "hole_resolution",
    })
    raise
```

**Update `.env.example`:**
```env
# Sentry
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_RELEASE=0.3.0
ENVIRONMENT=production
```

**Acceptance Criteria:**
- [ ] Sentry SDK initialized
- [ ] Errors automatically captured and sent to Sentry
- [ ] User context included in error reports
- [ ] Custom tags added for debugging
- [ ] Source maps uploaded (if applicable)
- [ ] Can disable Sentry in development

**Verification:**
```bash
# Test error capture
curl -X POST http://localhost:8000/test-error

# Check Sentry dashboard for error
open https://sentry.io/your-org/your-project/
```

---

## Sprint 4: Real Tool Integration (Week 9-10)

### Goal
Integrate real external tools (CodeQL, Daikon, OAuth) replacing stubs.

### Tasks

#### Task 4.1: CodeQL CLI Integration
**Priority**: P1
**Effort**: 12 hours
**Dependencies**: None

**Install CodeQL:**
```bash
# Download CodeQL CLI
cd /tmp
wget https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip
unzip codeql-linux64.zip
sudo mv codeql /usr/local/bin/

# Clone CodeQL queries
cd /opt
sudo git clone https://github.com/github/codeql.git codeql-repo
```

**File to Update: `lift_sys/reverse_mode/codeql_client.py`**

Replace stub implementation with real CodeQL integration:

```python
"""CodeQL client for static analysis."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from lift_sys.logging_config import get_logger

logger = get_logger(__name__)


class CodeQLClient:
    """Client for CodeQL static analysis."""

    def __init__(
        self,
        codeql_path: str = "/usr/local/bin/codeql",
        queries_path: str = "/opt/codeql-repo",
    ):
        """Initialize CodeQL client.

        Args:
            codeql_path: Path to CodeQL CLI executable
            queries_path: Path to CodeQL queries repository
        """
        self.codeql_path = codeql_path
        self.queries_path = queries_path
        self._verify_installation()

    def _verify_installation(self) -> None:
        """Verify CodeQL is installed."""
        if not Path(self.codeql_path).exists():
            raise RuntimeError(f"CodeQL not found at {self.codeql_path}")
        if not Path(self.queries_path).exists():
            raise RuntimeError(f"CodeQL queries not found at {self.queries_path}")

    async def create_database(
        self,
        source_path: str,
        language: str,
        output_db: Optional[str] = None,
    ) -> str:
        """Create CodeQL database from source code.

        Args:
            source_path: Path to source code
            language: Programming language (python, javascript, etc.)
            output_db: Output database path (temp dir if not specified)

        Returns:
            Path to created database
        """
        if not output_db:
            output_db = tempfile.mkdtemp(prefix="codeql-db-")

        cmd = [
            self.codeql_path,
            "database", "create",
            output_db,
            f"--language={language}",
            f"--source-root={source_path}",
        ]

        logger.info("creating_codeql_database", source=source_path, language=language)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error("codeql_database_creation_failed", error=error_msg)
            raise RuntimeError(f"CodeQL database creation failed: {error_msg}")

        logger.info("codeql_database_created", database_path=output_db)
        return output_db

    async def run_queries(
        self,
        database_path: str,
        query_suite: str = "python-security-and-quality",
    ) -> List[dict]:
        """Run CodeQL queries on a database.

        Args:
            database_path: Path to CodeQL database
            query_suite: Query suite to run

        Returns:
            List of query results
        """
        results_file = tempfile.mktemp(suffix=".bqrs")

        cmd = [
            self.codeql_path,
            "database", "analyze",
            database_path,
            f"{self.queries_path}/{query_suite}.qls",
            "--format=sarif-latest",
            f"--output={results_file}",
        ]

        logger.info("running_codeql_queries", database=database_path, suite=query_suite)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error("codeql_analysis_failed", error=error_msg)
            raise RuntimeError(f"CodeQL analysis failed: {error_msg}")

        # Parse SARIF results
        with open(results_file) as f:
            sarif_results = json.load(f)

        # Convert to our format
        results = self._parse_sarif(sarif_results)

        logger.info("codeql_queries_completed", results_count=len(results))
        return results

    def _parse_sarif(self, sarif: dict) -> List[dict]:
        """Parse SARIF format to our internal format.

        Args:
            sarif: SARIF formatted results

        Returns:
            List of findings in our format
        """
        findings = []

        for run in sarif.get("runs", []):
            for result in run.get("results", []):
                finding = {
                    "rule_id": result.get("ruleId"),
                    "message": result.get("message", {}).get("text"),
                    "level": result.get("level", "warning"),
                    "locations": [],
                }

                for location in result.get("locations", []):
                    physical_location = location.get("physicalLocation", {})
                    finding["locations"].append({
                        "file": physical_location.get("artifactLocation", {}).get("uri"),
                        "start_line": physical_location.get("region", {}).get("startLine"),
                        "end_line": physical_location.get("region", {}).get("endLine"),
                    })

                findings.append(finding)

        return findings

    async def analyze_repository(
        self,
        repo_path: str,
        language: str = "python",
    ) -> List[dict]:
        """Analyze a repository with CodeQL.

        Args:
            repo_path: Path to repository
            language: Programming language

        Returns:
            List of analysis results
        """
        # Create database
        db_path = await self.create_database(repo_path, language)

        try:
            # Run queries
            results = await self.run_queries(db_path)
            return results
        finally:
            # Clean up database
            import shutil
            shutil.rmtree(db_path, ignore_errors=True)
```

**Update Integration Tests:**
```python
# tests/integration/test_codeql_integration.py
import pytest
from lift_sys.reverse_mode.codeql_client import CodeQLClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_codeql_analysis(tmp_path):
    """Test real CodeQL analysis."""
    # Create sample Python file
    test_file = tmp_path / "test.py"
    test_file.write_text("""
def unsafe_eval(user_input):
    return eval(user_input)  # Security issue
""")

    client = CodeQLClient()
    results = await client.analyze_repository(str(tmp_path), language="python")

    # Should detect the eval security issue
    assert len(results) > 0
    assert any("eval" in r["message"].lower() for r in results)
```

**Acceptance Criteria:**
- [ ] CodeQL CLI installed and verified
- [ ] Can create CodeQL databases
- [ ] Can run queries and get results
- [ ] SARIF results parsed correctly
- [ ] Integration tests pass with real CodeQL
- [ ] Error handling for missing CodeQL

**Verification:**
```bash
# Verify installation
/usr/local/bin/codeql version

# Run integration test
uv run pytest tests/integration/test_codeql_integration.py -v
```

---

#### Task 4.2: Daikon Integration
**Priority**: P2
**Effort**: 10 hours
**Dependencies**: None

**Install Daikon:**
```bash
# Download Daikon
cd /tmp
wget https://plse.cs.washington.edu/daikon/download/daikon.tar.gz
tar xzf daikon.tar.gz
sudo mv daikon /opt/daikon

# Add to PATH
echo 'export DAIKONDIR=/opt/daikon' | sudo tee -a /etc/profile.d/daikon.sh
echo 'export PATH=$DAIKONDIR/bin:$PATH' | sudo tee -a /etc/profile.d/daikon.sh
source /etc/profile.d/daikon.sh
```

**File to Update: `lift_sys/reverse_mode/daikon_client.py`**

Replace stub with real Daikon integration:

```python
"""Daikon client for dynamic invariant detection."""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from lift_sys.logging_config import get_logger

logger = get_logger(__name__)


class DaikonClient:
    """Client for Daikon dynamic invariant detection."""

    def __init__(self, daikon_dir: str = "/opt/daikon"):
        """Initialize Daikon client.

        Args:
            daikon_dir: Path to Daikon installation
        """
        self.daikon_dir = daikon_dir
        self.daikon_bin = Path(daikon_dir) / "bin" / "daikon"
        self._verify_installation()

    def _verify_installation(self) -> None:
        """Verify Daikon is installed."""
        if not self.daikon_bin.exists():
            raise RuntimeError(f"Daikon not found at {self.daikon_bin}")

    async def instrument_code(
        self,
        source_file: str,
        output_file: str,
    ) -> None:
        """Instrument Python code for Daikon tracing.

        Args:
            source_file: Path to source code
            output_file: Path for instrumented code
        """
        # Use DynComp to instrument
        cmd = [
            str(Path(self.daikon_dir) / "bin" / "dyncomp"),
            "--python",
            source_file,
            "--output", output_file,
        ]

        logger.info("instrumenting_code", source=source_file)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await process.communicate()

        if process.returncode != 0:
            raise RuntimeError("Code instrumentation failed")

    async def run_and_trace(
        self,
        instrumented_file: str,
        test_cases: List[Dict[str, Any]],
    ) -> str:
        """Run instrumented code with test cases and collect traces.

        Args:
            instrumented_file: Path to instrumented code
            test_cases: List of test cases (function args)

        Returns:
            Path to generated .dtrace file
        """
        trace_file = tempfile.mktemp(suffix=".dtrace")

        # Create test runner
        test_runner = self._generate_test_runner(
            instrumented_file,
            test_cases,
            trace_file,
        )

        # Execute
        process = await asyncio.create_subprocess_exec(
            "python",
            test_runner,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "DAIKONDIR": self.daikon_dir},
        )

        await process.communicate()

        return trace_file

    def _generate_test_runner(
        self,
        instrumented_file: str,
        test_cases: List[Dict[str, Any]],
        trace_file: str,
    ) -> str:
        """Generate test runner script.

        Args:
            instrumented_file: Path to instrumented code
            test_cases: Test cases to run
            trace_file: Output trace file

        Returns:
            Path to test runner script
        """
        runner_path = tempfile.mktemp(suffix=".py")

        runner_code = f"""
import sys
sys.path.insert(0, '{os.path.dirname(instrumented_file)}')
import daikon_runtime

daikon_runtime.set_trace_file('{trace_file}')

# Import instrumented module
import {Path(instrumented_file).stem} as module

# Run test cases
test_cases = {test_cases}
for test_case in test_cases:
    # Call target function with test case arguments
    module.target_function(**test_case)

daikon_runtime.close_trace_file()
"""

        with open(runner_path, 'w') as f:
            f.write(runner_code)

        return runner_path

    async def infer_invariants(
        self,
        trace_file: str,
    ) -> List[Dict[str, Any]]:
        """Infer invariants from trace file using Daikon.

        Args:
            trace_file: Path to .dtrace file

        Returns:
            List of inferred invariants
        """
        output_file = tempfile.mktemp(suffix=".inv")

        cmd = [
            str(self.daikon_bin),
            trace_file,
            "--output", output_file,
            "--format", "json",
        ]

        logger.info("inferring_invariants", trace_file=trace_file)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error("invariant_inference_failed", error=error_msg)
            raise RuntimeError(f"Invariant inference failed: {error_msg}")

        # Parse results
        invariants = self._parse_invariants(output_file)

        logger.info("invariants_inferred", count=len(invariants))
        return invariants

    def _parse_invariants(self, invariants_file: str) -> List[Dict[str, Any]]:
        """Parse Daikon invariants file.

        Args:
            invariants_file: Path to invariants file

        Returns:
            Parsed invariants
        """
        import json

        with open(invariants_file) as f:
            data = json.load(f)

        invariants = []
        for inv in data.get("invariants", []):
            invariants.append({
                "type": inv.get("type"),
                "program_point": inv.get("ppt"),
                "formula": inv.get("formula"),
                "confidence": inv.get("confidence", 1.0),
                "variables": inv.get("variables", []),
            })

        return invariants

    async def analyze_function(
        self,
        source_code: str,
        function_name: str,
        test_cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Analyze a function and infer invariants.

        Args:
            source_code: Python source code
            function_name: Name of function to analyze
            test_cases: Test cases for the function

        Returns:
            Inferred invariants
        """
        # Write source to temp file
        source_file = tempfile.mktemp(suffix=".py")
        with open(source_file, 'w') as f:
            f.write(source_code)

        try:
            # Instrument
            instrumented_file = tempfile.mktemp(suffix=".py")
            await self.instrument_code(source_file, instrumented_file)

            # Run and trace
            trace_file = await self.run_and_trace(instrumented_file, test_cases)

            # Infer invariants
            invariants = await self.infer_invariants(trace_file)

            return invariants
        finally:
            # Cleanup
            for f in [source_file, instrumented_file, trace_file]:
                if Path(f).exists():
                    Path(f).unlink()
```

**Acceptance Criteria:**
- [ ] Daikon installed and verified
- [ ] Can instrument Python code
- [ ] Can collect execution traces
- [ ] Can infer invariants from traces
- [ ] Invariants parsed to IR format
- [ ] Integration tests pass

---

#### Task 4.3: OAuth Provider Implementation
**Priority**: P1
**Effort**: 8 hours
**Dependencies**: None

**Update `lift_sys/auth/oauth_manager.py`:**

Replace stub OAuth flow with real implementation:

```python
"""OAuth authentication manager."""
import os
from typing import Optional, Dict
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from lift_sys.logging_config import get_logger

logger = get_logger(__name__)


class OAuthManager:
    """Manages OAuth authentication flows."""

    def __init__(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        """Initialize OAuth manager.

        Args:
            provider: OAuth provider (github, google, etc.)
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Redirect URI after authentication
        """
        self.provider = provider
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._config = self._get_provider_config()

    def _get_provider_config(self) -> Dict[str, str]:
        """Get provider-specific configuration."""
        configs = {
            "github": {
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_url": "https://api.github.com/user",
                "scope": "read:user user:email",
            },
            "google": {
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "scope": "openid email profile",
            },
        }

        if self.provider not in configs:
            raise ValueError(f"Unsupported provider: {self.provider}")

        return configs[self.provider]

    def get_authorization_url(self, state: str) -> str:
        """Get OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self._config["scope"],
            "state": state,
            "response_type": "code",
        }

        url = f"{self._config['auth_url']}?{urlencode(params)}"
        logger.info("generated_auth_url", provider=self.provider)
        return url

    async def exchange_code_for_token(self, code: str) -> Dict[str, str]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from callback

        Returns:
            Token data (access_token, refresh_token, etc.)
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._config["token_url"],
                data=data,
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    "token_exchange_failed",
                    status_code=response.status_code,
                    error=response.text,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange code for token"
                )

            token_data = response.json()
            logger.info("token_exchanged", provider=self.provider)
            return token_data

    async def get_user_info(self, access_token: str) -> Dict[str, any]:
        """Get user information using access token.

        Args:
            access_token: OAuth access token

        Returns:
            User information
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self._config["user_url"],
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    "user_info_failed",
                    status_code=response.status_code,
                    error=response.text,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get user info"
                )

            user_data = response.json()
            logger.info("user_info_retrieved", provider=self.provider)
            return self._normalize_user_data(user_data)

    def _normalize_user_data(self, user_data: Dict) -> Dict:
        """Normalize user data across providers.

        Args:
            user_data: Raw user data from provider

        Returns:
            Normalized user data
        """
        if self.provider == "github":
            return {
                "id": str(user_data["id"]),
                "username": user_data["login"],
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url"),
            }
        elif self.provider == "google":
            return {
                "id": user_data["id"],
                "username": user_data.get("email", "").split("@")[0],
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "avatar_url": user_data.get("picture"),
            }

        return user_data
```

**Add OAuth Routes in `lift_sys/api/routes/auth.py`:**
```python
"""Authentication routes."""
import secrets
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse

from lift_sys.auth.oauth_manager import OAuthManager
from lift_sys.auth.token_store import TokenStore

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login/{provider}")
async def oauth_login(provider: str, response: Response):
    """Initiate OAuth login flow.

    Args:
        provider: OAuth provider (github, google)

    Returns:
        Redirect to provider's authorization page
    """
    # Create OAuth manager
    manager = OAuthManager(
        provider=provider,
        client_id=os.getenv(f"{provider.upper()}_CLIENT_ID"),
        client_secret=os.getenv(f"{provider.upper()}_CLIENT_SECRET"),
        redirect_uri=f"{os.getenv('APP_URL')}/auth/callback/{provider}",
    )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    response.set_cookie(
        key=f"oauth_state_{provider}",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,  # 10 minutes
    )

    # Get authorization URL
    auth_url = manager.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
):
    """Handle OAuth callback.

    Args:
        provider: OAuth provider
        code: Authorization code
        state: State parameter for CSRF check

    Returns:
        Redirect to app with session cookie
    """
    # Verify state
    stored_state = request.cookies.get(f"oauth_state_{provider}")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Create OAuth manager
    manager = OAuthManager(
        provider=provider,
        client_id=os.getenv(f"{provider.upper()}_CLIENT_ID"),
        client_secret=os.getenv(f"{provider.upper()}_CLIENT_SECRET"),
        redirect_uri=f"{os.getenv('APP_URL')}/auth/callback/{provider}",
    )

    # Exchange code for token
    token_data = await manager.exchange_code_for_token(code)

    # Get user info
    user_info = await manager.get_user_info(token_data["access_token"])

    # Store token
    token_store = TokenStore()
    await token_store.store_token(
        user_id=user_info["id"],
        provider=provider,
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
    )

    # Create session
    session_token = secrets.token_urlsafe(32)
    # Store session_token -> user_id mapping (implement session store)

    # Set session cookie
    response = RedirectResponse(url="/")
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400 * 30,  # 30 days
    )

    return response
```

**Update `.env.example`:**
```env
# OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
APP_URL=http://localhost:8000
```

**Acceptance Criteria:**
- [ ] Real OAuth flow implemented (not stubbed)
- [ ] GitHub OAuth working
- [ ] Google OAuth working
- [ ] CSRF protection with state parameter
- [ ] Token storage and refresh
- [ ] Session management
- [ ] User info retrieval

---

## Sprint 5: UX Improvements (Week 11-12)

### Goal
Enhance user experience across all interfaces.

### Tasks

#### Task 5.1: Enhanced Web UI
**Priority**: P1
**Effort**: 12 hours
**Dependencies**: None

**Features to Add:**

1. **Real-time Progress Updates via WebSocket**
2. **IR Syntax Highlighting**
3. **Keyboard Shortcuts**
4. **Session History and Revision Comparison**
5. **Export Options (JSON, Python stub, etc.)**

**Update `frontend/src/components/PromptWorkbench.tsx`:**

Add WebSocket connection for real-time updates:

```typescript
import { useEffect, useState } from 'react';
import useWebSocket from 'react-use-websocket';

export function PromptWorkbench() {
  const [session, setSession] = useState<PromptSession | null>(null);
  const [progress, setProgress] = useState<number>(0);

  // WebSocket connection
  const { lastMessage, sendMessage } = useWebSocket(
    `ws://localhost:8000/ws/sessions/${session?.session_id}`,
    {
      shouldReconnect: () => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
    }
  );

  useEffect(() => {
    if (lastMessage !== null) {
      const data = JSON.parse(lastMessage.data);

      if (data.type === 'progress') {
        setProgress(data.progress);
      } else if (data.type === 'hole_resolved') {
        // Update session with resolved hole
        setSession(prev => ({
          ...prev,
          ambiguities: prev.ambiguities.filter(h => h.id !== data.hole_id)
        }));
      } else if (data.type === 'error') {
        // Show error toast
        toast.error(data.message);
      }
    }
  }, [lastMessage]);

  // ... rest of component
}
```

**Add IR Syntax Highlighting:**

Install Prism.js or Monaco Editor:

```bash
cd frontend
npm install react-syntax-highlighter @types/react-syntax-highlighter
```

**Create custom IR language definition:**

```typescript
// frontend/src/utils/irSyntax.ts
export const IR_LANGUAGE = {
  'keyword': /\b(intent|sig|assert|effect|reads|writes|requires|ensures)\b/,
  'type': /\b(int|str|bool|list|dict|any)\b/,
  'function': /\b[a-z_][a-z0-9_]*(?=\()/i,
  'punctuation': /[{}[\]();,.:]/,
  'operator': /[=!<>]+|->|::/,
  'string': /("|')(?:\\.|(?!\1)[^\\\r\n])*\1/,
  'comment': /#.*/,
  'number': /\b0x[\da-f]+\b|(?:\b\d+(?:\.\d*)?|\B\.\d+)/i,
};
```

**Add keyboard shortcuts:**

```typescript
import { useHotkeys } from 'react-hotkeys-hook';

export function PromptWorkbench() {
  // ... existing code

  // Keyboard shortcuts
  useHotkeys('ctrl+enter', () => {
    handleCreateSession();
  });

  useHotkeys('ctrl+s', (e) => {
    e.preventDefault();
    handleSaveSession();
  });

  useHotkeys('ctrl+e', () => {
    handleExportIR();
  });

  useHotkeys('/', () => {
    // Focus search
    searchInputRef.current?.focus();
  });

  // ... rest
}
```

**Acceptance Criteria:**
- [ ] WebSocket real-time updates working
- [ ] IR syntax highlighting implemented
- [ ] Keyboard shortcuts functional
- [ ] Session history with diff view
- [ ] Export to multiple formats
- [ ] Responsive design (mobile-friendly)

---

#### Task 5.2: CLI Enhancements
**Priority**: P2
**Effort**: 6 hours
**Dependencies**: None

**Enhancements:**
1. **Interactive prompts with rich library**
2. **Progress bars for long operations**
3. **Better error messages**
4. **Command aliases**
5. **Shell completion**

**Update `lift_sys/cli/session_commands.py`:**

Add rich interactive prompts:

```python
"""Enhanced CLI session commands."""
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()
app = typer.Typer()


@app.command("create")
def create_session_interactive():
    """Create a new session interactively."""
    console.print("[bold]Create New Session[/bold]\n")

    # Interactive prompts
    source = Prompt.ask(
        "Session source",
        choices=["prompt", "ir", "file"],
        default="prompt"
    )

    if source == "prompt":
        prompt = Prompt.ask("Enter your prompt")

        # Show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating session...", total=None)

            # Call API
            session = client.create_session(source="prompt", prompt=prompt)

            progress.update(task, completed=True)

        # Display result
        console.print(f"\n[green]✓[/green] Session created: {session.session_id}")

        # Show ambiguities table
        if session.ambiguities:
            table = Table(title="Ambiguities to Resolve")
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Description", style="white")

            for hole in session.ambiguities:
                table.add_row(
                    hole.id,
                    hole.hole_type,
                    hole.description or "-"
                )

            console.print(table)

            # Ask if user wants to resolve now
            if Confirm.ask("\nResolve ambiguities now?"):
                for hole in session.ambiguities:
                    resolve_hole_interactive(session.session_id, hole.id)


@app.command("list")
def list_sessions():
    """List all sessions with rich formatting."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching sessions...", total=None)
        sessions = client.list_sessions()
        progress.update(task, completed=True)

    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return

    table = Table(title=f"Sessions ({len(sessions)})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Source", style="green")
    table.add_column("Created", style="white")
    table.add_column("Holes", justify="right", style="yellow")

    for session in sessions:
        status_emoji = "✓" if session.status == "finalized" else "○"
        table.add_row(
            session.session_id[:8],
            f"{status_emoji} {session.status}",
            session.source,
            session.created_at.strftime("%Y-%m-%d %H:%M"),
            str(len(session.ambiguities)),
        )

    console.print(table)


def resolve_hole_interactive(session_id: str, hole_id: str):
    """Resolve a hole interactively."""
    # Get assists
    with console.status(f"Getting AI assists for {hole_id}..."):
        assists = client.get_assists(session_id, hole_id)

    if assists:
        console.print(f"\n[bold]Suggestions for {hole_id}:[/bold]")
        for i, assist in enumerate(assists, 1):
            console.print(f"  {i}. {assist.suggestion} [dim]({assist.confidence:.0%})[/dim]")

        choice = Prompt.ask(
            "\nChoose suggestion (1-{}) or enter custom value".format(len(assists)),
            default="1"
        )

        if choice.isdigit() and 1 <= int(choice) <= len(assists):
            resolution = assists[int(choice) - 1].suggestion
        else:
            resolution = choice
    else:
        resolution = Prompt.ask(f"Enter value for {hole_id}")

    # Resolve
    with console.status("Resolving..."):
        updated_session = client.resolve_hole(session_id, hole_id, resolution)

    console.print(f"[green]✓[/green] Resolved {hole_id} = {resolution}")
```

**Add Shell Completion:**

```python
# lift_sys/cli/main.py
import typer
from typer.main import get_command

app = typer.Typer()

# ... add all commands ...

def generate_completion():
    """Generate shell completion script."""
    import click
    from click.shell_completion import BashComplete, ZshComplete

    cli = get_command(app)

    # Bash
    with open("completion.bash", "w") as f:
        f.write(BashComplete(cli, {}, "liftsys").source())

    # Zsh
    with open("completion.zsh", "w") as f:
        f.write(ZshComplete(cli, {}, "liftsys").source())

    print("Shell completion scripts generated:")
    print("  - completion.bash")
    print("  - completion.zsh")
    print("\nTo enable:")
    print("  Bash: source completion.bash")
    print("  Zsh: source completion.zsh")


if __name__ == "__main__":
    app()
```

**Acceptance Criteria:**
- [ ] Interactive prompts with rich library
- [ ] Progress bars for API calls
- [ ] Tables for list outputs
- [ ] Better error formatting
- [ ] Shell completion scripts generated
- [ ] Command aliases working

---

## Sprint 6: Polish & Release (Week 13-14)

### Goal
Final polish, bug fixes, documentation, and v0.3.0 release.

### Tasks

#### Task 6.1: Documentation Updates
**Priority**: P0
**Effort**: 8 hours
**Dependencies**: All previous tasks

**Documents to Update:**

1. **README.md**
   - Update features list
   - Add Docker setup instructions
   - Update screenshots
   - Add badges (build status, coverage, etc.)

2. **docs/DEPLOYMENT.md** (new)
   - Docker deployment guide
   - PostgreSQL setup
   - Environment variables reference
   - Monitoring setup
   - Backup and recovery

3. **docs/CONTRIBUTING.md** (new)
   - Development setup
   - Code style guidelines
   - Testing requirements
   - PR process

4. **docs/API.md**
   - Update with all endpoints
   - Add authentication section
   - WebSocket documentation

5. **CHANGELOG.md**
   - v0.3.0 changes
   - Breaking changes
   - Migration guide from v0.2.1

**Example DEPLOYMENT.md structure:**

```markdown
# Deployment Guide

## Prerequisites
- Docker 24+ and Docker Compose
- PostgreSQL 16
- Redis 7
- 2GB RAM minimum, 4GB recommended
- 10GB disk space

## Quick Start with Docker Compose

### 1. Clone Repository
\`\`\`bash
git clone https://github.com/your-org/lift-sys.git
cd lift-sys
\`\`\`

### 2. Configure Environment
\`\`\`bash
cp .env.example .env
# Edit .env with your configuration
\`\`\`

### 3. Start Services
\`\`\`bash
docker-compose up -d
\`\`\`

### 4. Run Migrations
\`\`\`bash
docker-compose exec backend uv run alembic upgrade head
\`\`\`

### 5. Verify
\`\`\`bash
curl http://localhost:8000/health
\`\`\`

## Production Deployment

### Database
- Use managed PostgreSQL (AWS RDS, GCP Cloud SQL)
- Enable backups and point-in-time recovery
- Set up read replicas for scaling

### Secrets Management
- Use AWS Secrets Manager or similar
- Rotate credentials regularly
- Never commit secrets to git

### Monitoring
- Set up Prometheus + Grafana
- Configure Sentry error tracking
- Enable structured logging

### Scaling
- Use multiple backend replicas
- Add load balancer (nginx, traefik)
- Use Redis for session storage

...
```

**Acceptance Criteria:**
- [ ] All documentation updated
- [ ] Deployment guide comprehensive
- [ ] Contributing guide clear
- [ ] API docs complete
- [ ] Changelog accurate

---

#### Task 6.2: Performance Optimization
**Priority**: P1
**Effort**: 8 hours
**Dependencies**: Task 0.4 (Benchmarks)

**Optimizations:**

1. **Database Query Optimization**
   - Add database indexes
   - Use query result caching
   - Batch queries where possible

2. **API Response Caching**
   - Cache frequently accessed data (sessions list)
   - Use Redis for cache storage
   - Set appropriate TTLs

3. **Frontend Performance**
   - Code splitting
   - Lazy loading components
   - Image optimization
   - Bundle size reduction

**Example Database Optimizations:**

```python
# lift_sys/db/models.py

# Add indexes
class PromptSession(Base):
    __tablename__ = "prompt_sessions"

    # ... columns ...

    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_updated_at', 'updated_at'),
    )
```

**Add Caching Layer:**

```python
# lift_sys/services/cache.py
import json
from typing import Optional, Any
import redis.asyncio as redis


class CacheService:
    """Redis-based caching service."""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
    ) -> None:
        """Set value in cache with TTL."""
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value),
        )

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        await self.redis.delete(key)
```

**Use in Routes:**

```python
@app.get("/spec-sessions")
async def list_sessions(
    user_id: str = Depends(get_current_user),
    cache: CacheService = Depends(get_cache),
):
    """List sessions with caching."""
    cache_key = f"sessions:{user_id}"

    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Query database
    sessions = await session_service.list_sessions(user_id)

    # Cache result
    await cache.set(cache_key, sessions, ttl=60)

    return sessions
```

**Frontend Optimizations:**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
  // ... rest
});
```

**Acceptance Criteria:**
- [ ] Database queries optimized (< 50ms avg)
- [ ] API response times reduced by 30%
- [ ] Frontend bundle size < 500KB
- [ ] Cache hit rate > 70%
- [ ] All benchmarks pass

---

#### Task 6.3: Final Testing & Bug Fixes
**Priority**: P0
**Effort**: 12 hours
**Dependencies**: All previous tasks

**Testing Checklist:**

- [ ] All unit tests pass (100%)
- [ ] All integration tests pass (100%)
- [ ] E2E tests pass (15+ tests)
- [ ] Performance tests meet targets
- [ ] Load testing (100 concurrent users)
- [ ] Security scanning (no critical vulnerabilities)
- [ ] Browser compatibility (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness

**Load Testing:**

```bash
# Install locust
uv add --dev locust

# Create load test
cat > tests/load/locustfile.py << 'EOF'
from locust import HttpUser, task, between

class LiftSysUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def create_session(self):
        self.client.post(
            "/spec-sessions",
            json={
                "source": "prompt",
                "prompt": "A function that validates emails"
            },
            headers={"x-demo-user": "loadtest"}
        )

    @task(2)
    def list_sessions(self):
        self.client.get(
            "/spec-sessions",
            headers={"x-demo-user": "loadtest"}
        )

    @task(1)
    def health_check(self):
        self.client.get("/health")
EOF

# Run load test
uv run locust -f tests/load/locustfile.py --host http://localhost:8000
```

**Security Scanning:**

```bash
# Install safety and bandit
uv add --dev safety bandit

# Scan dependencies
uv run safety check

# Scan code for security issues
uv run bandit -r lift_sys/

# Run OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8000 \
  -r zap-report.html
```

**Acceptance Criteria:**
- [ ] Zero critical bugs
- [ ] All tests passing
- [ ] Load test: 100 users, < 1s avg response
- [ ] No security vulnerabilities
- [ ] Cross-browser compatible

---

#### Task 6.4: Release v0.3.0
**Priority**: P0
**Effort**: 4 hours
**Dependencies**: Task 6.1, 6.2, 6.3

**Release Checklist:**

- [ ] Version bumped to 0.3.0
- [ ] CHANGELOG.md updated
- [ ] Git tag created
- [ ] GitHub release created
- [ ] Docker images published
- [ ] Documentation deployed
- [ ] Release notes published
- [ ] Social media announcement

**Release Commands:**

```bash
# 1. Update version
sed -i 's/version = "0.2.1"/version = "0.3.0"/' pyproject.toml

# 2. Update CHANGELOG
# (manually edit)

# 3. Commit and tag
git add -A
git commit -m "Release v0.3.0"
git tag -a v0.3.0 -m "Release v0.3.0"

# 4. Push
git push origin main --tags

# 5. Build and push Docker images
docker build -t liftsys/backend:0.3.0 -t liftsys/backend:latest .
docker push liftsys/backend:0.3.0
docker push liftsys/backend:latest

# 6. Create GitHub release
gh release create v0.3.0 \
  --title "lift-sys v0.3.0 - Production Ready" \
  --notes-file RELEASE_NOTES.md \
  --latest

# 7. Deploy docs
cd docs
mkdocs gh-deploy
```

**Release Notes Template:**

```markdown
# lift-sys v0.3.0 - Production Ready

We're excited to announce lift-sys v0.3.0, our first production-ready release!

## 🚀 Highlights

- **Docker Support**: Full containerization with docker-compose
- **PostgreSQL Integration**: Persistent storage with Alembic migrations
- **Production Monitoring**: Prometheus metrics, structured logging, Sentry
- **Real Tool Integration**: CodeQL and Daikon (beta)
- **OAuth Authentication**: GitHub and Google login
- **Enhanced UX**: Real-time updates, syntax highlighting, keyboard shortcuts
- **Performance**: 30% faster API responses, optimized database queries

## 📊 Metrics

- **Test Coverage**: 91.5% (269/294 tests passing)
- **Performance**: < 300ms avg session creation
- **Reliability**: 99.9% uptime target
- **Security**: Zero critical vulnerabilities

## 🔧 Breaking Changes

- Database: Migrated from in-memory to PostgreSQL (see migration guide)
- Authentication: Demo mode requires `LIFT_SYS_ENABLE_DEMO_USER_HEADER=1`
- API: Some endpoints return additional fields

## 📚 Migration Guide

See [MIGRATION.md](docs/MIGRATION.md) for detailed migration instructions from v0.2.1.

## 🐛 Bug Fixes

- Fixed test isolation issues (#26)
- Improved error handling in session creation
- Fixed TUI keyboard navigation
- Resolved memory leaks in long-running sessions

## 🙏 Thank You

Thank you to all contributors and early adopters!

## 📦 Installation

\`\`\`bash
# Docker Compose (recommended)
git clone https://github.com/your-org/lift-sys.git
cd lift-sys
cp .env.example .env
docker-compose up -d

# Or with uv
uv sync
uv run uvicorn lift_sys.api.server:app
\`\`\`

Full documentation: https://docs.lift-sys.dev
```

**Acceptance Criteria:**
- [ ] Version 0.3.0 tagged in git
- [ ] GitHub release created
- [ ] Docker images published to registry
- [ ] Documentation live
- [ ] Release announcement published
- [ ] Migration guide available

---

## Testing Strategy

### Unit Tests
- Run after every code change
- Must maintain 100% pass rate
- Target: < 10 seconds execution time

```bash
uv run pytest tests/unit/ -v
```

### Integration Tests
- Run before committing
- Must maintain > 90% pass rate
- Target: < 60 seconds execution time

```bash
uv run pytest tests/integration/ -v
```

### E2E Tests
- Run before creating PR
- Must pass 100%
- Target: < 5 minutes execution time

```bash
# Start services first
docker-compose up -d

# Run E2E tests
uv run pytest tests/e2e/ -v
```

### Performance Tests
- Run weekly or before major releases
- Compare against baseline
- Flag regressions > 10%

```bash
uv run pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

### Load Tests
- Run before production deployment
- Target: 100 concurrent users, < 1s avg response
- Monitor resource usage

```bash
uv run locust -f tests/load/locustfile.py --host http://localhost:8000 --users 100 --spawn-rate 10
```

---

## Rollback Procedures

### Database Rollback
```bash
# Rollback one migration
uv run alembic downgrade -1

# Rollback to specific version
uv run alembic downgrade <revision>

# Rollback all
uv run alembic downgrade base
```

### Docker Rollback
```bash
# Stop current version
docker-compose down

# Switch to previous version
git checkout v0.2.1

# Start previous version
docker-compose up -d
```

### Code Rollback
```bash
# Revert last commit
git revert HEAD

# Revert to specific commit
git revert <commit-hash>

# Force rollback (use with caution)
git reset --hard <commit-hash>
git push --force
```

---

## Success Metrics

### Development Metrics
- **Code Coverage**: > 90%
- **Build Time**: < 5 minutes
- **Test Execution**: < 10 minutes
- **Deployment Time**: < 15 minutes

### Performance Metrics
- **API Response Time**: < 500ms (p95)
- **Session Creation**: < 300ms
- **Hole Resolution**: < 200ms
- **SMT Verification**: < 150ms

### Reliability Metrics
- **Uptime**: > 99.9%
- **Error Rate**: < 0.1%
- **Test Pass Rate**: > 90%
- **Bug Escape Rate**: < 5%

### User Metrics
- **Time to First Session**: < 2 minutes
- **Session Completion Rate**: > 80%
- **User Satisfaction**: > 4.0/5.0

---

## Risk Management

### High Risk
- **Database migrations fail in production**
  - Mitigation: Test migrations on production-like data
  - Rollback: Keep database backups, have downgrade scripts ready

- **Performance degradation under load**
  - Mitigation: Load testing before deployment
  - Rollback: Quick rollback to previous version

### Medium Risk
- **Third-party API outages (GitHub, OpenAI)**
  - Mitigation: Implement circuit breakers and fallbacks
  - Handling: Graceful degradation, error messages

- **Security vulnerabilities discovered**
  - Mitigation: Regular security scans
  - Response: Hotfix process, coordinated disclosure

### Low Risk
- **UI bugs in specific browsers**
  - Mitigation: Cross-browser testing
  - Response: Quick patch release

---

## Timeline Summary

| Sprint | Duration | Focus | Key Deliverables |
|--------|----------|-------|------------------|
| Sprint 0 | Week 1-2 | Setup | Code quality tools, CI/CD, benchmarks |
| Sprint 1 | Week 3-4 | Testing | E2E tests, TUI tests fixed |
| Sprint 2 | Week 5-6 | Infrastructure | Docker, PostgreSQL, migrations |
| Sprint 3 | Week 7-8 | Observability | Prometheus, logging, Sentry |
| Sprint 4 | Week 9-10 | Integration | CodeQL, Daikon, OAuth |
| Sprint 5 | Week 11-12 | UX | Enhanced UI, CLI improvements |
| Sprint 6 | Week 13-14 | Release | Documentation, optimization, v0.3.0 |

**Total Duration**: 14 weeks (~3.5 months)
**Target Release**: Late January 2026

---

## Conclusion

This implementation plan provides a clear, actionable roadmap to transform lift-sys from beta (v0.2.1) to production-ready (v0.3.0).

**Key Success Factors:**
- Follow the plan but remain flexible
- Test thoroughly at each stage
- Gather user feedback early
- Maintain documentation as you go
- Celebrate milestones

**Next Steps:**
1. Review and approve this plan
2. Set up GitHub Projects board
3. Create issues for Sprint 0 tasks
4. Begin implementation

**Questions or Changes:**
- This plan can be adjusted based on priorities
- Some sprints can run in parallel
- Tasks can be reprioritized as needed

---

**Document Status**: READY FOR EXECUTION
**Last Updated**: October 11, 2025
**Version**: 1.0
