# Next Phase Development Plan (v0.3.0)
**Date Created**: October 11, 2025
**Target Release**: Q1 2026
**Focus**: Production Readiness, Performance, and Advanced Features

---

## Executive Summary

**Current State**: v0.2.1 - Production-ready core features
- 268/294 tests passing (91.2%)
- All major features implemented and functional
- Comprehensive documentation (3000+ lines)
- Multi-interface support (Web, CLI, TUI, SDK)
- 7,480 lines of Python code

**Next Phase Goal**: Transform from "functional" to "production-grade"
- Add production infrastructure (monitoring, deployment, CI/CD)
- Improve performance and scalability
- Enhance user experience and developer productivity
- Add advanced features for power users

---

## Phase 3: Production Infrastructure (v0.3.0)

### Priority Levels
- 🔴 **P0 - Critical**: Must have for production deployment
- 🟡 **P1 - High**: Important for user experience
- 🟢 **P2 - Medium**: Nice to have, improves productivity
- 🔵 **P3 - Low**: Future enhancements

---

## Milestone 1: Quality & Reliability (2-3 weeks)

### 1.1 E2E Testing Infrastructure 🔴 **P0**
**Goal**: Add comprehensive end-to-end testing
**Effort**: 1 week

**Tasks:**

#### A. Playwright E2E Tests for Frontend
```bash
# Add dependencies
uv add --dev playwright pytest-playwright
playwright install
```

**Test Coverage:**
- Complete prompt-to-IR workflow
- Session creation and management
- Ambiguity resolution with AI assists
- IR finalization and export
- Error handling and edge cases

**Files to Create:**
- `tests/e2e/test_web_ui_complete.py` - Full workflow tests
- `tests/e2e/test_web_ui_errors.py` - Error handling tests
- `tests/e2e/conftest.py` - E2E fixtures

**Success Criteria:**
- ✅ 15+ E2E tests covering all user workflows
- ✅ Tests run in CI/CD pipeline
- ✅ Visual regression testing for critical views
- ✅ Tests catch frontend regressions

#### B. Textual Testing for TUI
```bash
# Add dependency
uv add --dev textual[dev]
```

**Test Coverage:**
- TUI navigation and interaction
- Session management workflows
- Keyboard shortcuts
- Widget rendering and updates

**Files to Update:**
- `tests/integration/test_tui_session_management.py` - Convert to proper Textual tests

**Success Criteria:**
- ✅ 10+ TUI tests using textual.testing
- ✅ All TUI interactions validated
- ✅ No more mock-based failures

**Estimated Impact**: Fix 10 remaining TUI test failures

---

### 1.2 CI/CD Pipeline 🔴 **P0**
**Goal**: Automated testing and deployment
**Effort**: 3 days

**Tasks:**

#### A. GitHub Actions Workflow
**File**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']

    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest tests/ -v --cov=lift_sys --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Install Playwright
        run: playwright install --with-deps
      - name: Run E2E tests
        run: uv run pytest tests/e2e/ -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: cd frontend && npm install
      - name: Run tests
        run: cd frontend && npm test
      - name: Build
        run: cd frontend && npm run build
```

#### B. Pre-commit Hooks
**File**: `.pre-commit-config.yaml`

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

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        args: [--strict]
        additional_dependencies: [types-all]
```

**Success Criteria:**
- ✅ All tests run automatically on push
- ✅ PRs require passing tests before merge
- ✅ Code coverage tracked and reported
- ✅ Pre-commit hooks enforce code quality

---

### 1.3 Code Quality Tools 🟡 **P1**
**Goal**: Enforce consistent code quality
**Effort**: 2 days

**Tasks:**

#### A. Add Ruff for Linting and Formatting
```bash
uv add --dev ruff
```

**Configuration** (pyproject.toml):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### B. Add MyPy for Type Checking
```bash
uv add --dev mypy types-requests types-pyyaml
```

**Configuration** (pyproject.toml):
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

#### C. Add Pytest Coverage
```bash
uv add --dev pytest-cov
```

**Success Criteria:**
- ✅ 95%+ type coverage
- ✅ All files pass ruff checks
- ✅ 90%+ code coverage maintained
- ✅ No linting errors in CI

**Estimated Impact**: Improve code maintainability, catch bugs earlier

---

### 1.4 Performance Benchmarking 🟡 **P1**
**Goal**: Establish performance baselines
**Effort**: 3 days

**Tasks:**

#### A. Add pytest-benchmark
```bash
uv add --dev pytest-benchmark
```

**Benchmarks to Add:**
- Session creation time
- IR parsing performance
- Hole resolution time
- SMT verification speed
- Planner performance
- API response times

**File**: `tests/performance/test_benchmarks.py`

```python
def test_session_creation_benchmark(benchmark, api_client):
    """Benchmark session creation from prompt."""
    result = benchmark(
        api_client.post,
        "/spec-sessions",
        json={"source": "prompt", "prompt": "Test function"}
    )
    assert result.status_code == 200
    # Target: < 500ms

def test_ir_parsing_benchmark(benchmark, parser, sample_ir_text):
    """Benchmark IR parsing performance."""
    result = benchmark(parser.parse, sample_ir_text)
    assert result is not None
    # Target: < 100ms

def test_smt_verification_benchmark(benchmark, verifier, sample_ir):
    """Benchmark SMT verification."""
    result = benchmark(verifier.verify, sample_ir)
    assert result is not None
    # Target: < 200ms
```

#### B. Performance Monitoring Dashboard
**Tool**: Locust for load testing

```bash
uv add --dev locust
```

**File**: `tests/performance/locustfile.py`

```python
from locust import HttpUser, task, between

class LiftSysUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def create_session(self):
        self.client.post(
            "/spec-sessions",
            json={"source": "prompt", "prompt": "Test"},
            headers={"x-demo-user": "loadtest"}
        )

    @task(1)
    def list_sessions(self):
        self.client.get(
            "/spec-sessions",
            headers={"x-demo-user": "loadtest"}
        )
```

**Success Criteria:**
- ✅ Performance baselines established for all operations
- ✅ Regression tests catch performance degradation
- ✅ Load testing shows system can handle 100+ concurrent users
- ✅ P95 latency < 1s for all operations

---

## Milestone 2: Production Deployment (2 weeks)

### 2.1 Docker & Container Support 🔴 **P0**
**Goal**: Easy deployment and scaling
**Effort**: 3 days

**Files to Create:**

#### A. Dockerfile for Backend
**File**: `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY lift_sys ./lift_sys

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "uvicorn", "lift_sys.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### B. Docker Compose for Full Stack
**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LIFT_SYS_ENABLE_DEMO_USER_HEADER=1
      - LIFT_SYS_SESSION_SECRET=${SESSION_SECRET}
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://backend:8000

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=liftsys
      - POSTGRES_USER=liftsys
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Success Criteria:**
- ✅ One-command deployment with docker-compose
- ✅ All services start and communicate correctly
- ✅ Health checks pass
- ✅ Volumes persist data correctly

---

### 2.2 Database Integration 🟡 **P1**
**Goal**: Replace in-memory storage with persistent database
**Effort**: 1 week

**Tasks:**

#### A. Add SQLAlchemy and Alembic
```bash
uv add sqlalchemy alembic asyncpg psycopg2-binary
```

#### B. Database Models
**File**: `lift_sys/db/models.py`

```python
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class PromptSession(Base):
    __tablename__ = "prompt_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False)
    source = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    metadata = Column(JSON, default={})

    drafts = relationship("IRDraft", back_populates="session")

class IRDraft(Base):
    __tablename__ = "ir_drafts"

    draft_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("prompt_sessions.session_id"))
    version = Column(Integer, nullable=False)
    ir_data = Column(JSON, nullable=False)
    validation_status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

    session = relationship("PromptSession", back_populates="drafts")
```

#### C. Session Store Implementation
**File**: `lift_sys/spec_sessions/db_session_store.py`

```python
class DatabaseSessionStore(SessionStore):
    """PostgreSQL-backed session store."""

    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_session(self, session: PromptSession) -> None:
        async with self.async_session() as db:
            db_session = models.PromptSession(...)
            db.add(db_session)
            await db.commit()

    async def get_session(self, session_id: str, user_id: str) -> PromptSession:
        async with self.async_session() as db:
            result = await db.execute(
                select(models.PromptSession).where(
                    models.PromptSession.session_id == session_id,
                    models.PromptSession.user_id == user_id
                )
            )
            db_session = result.scalar_one_or_none()
            if not db_session:
                raise SessionNotFoundError(session_id)
            return self._to_domain(db_session)
```

**Success Criteria:**
- ✅ Sessions persist across server restarts
- ✅ Multi-user isolation enforced at DB level
- ✅ Migration system in place with Alembic
- ✅ Performance comparable to in-memory store
- ✅ Backward compatibility with existing APIs

---

### 2.3 Monitoring & Observability 🟡 **P1**
**Goal**: Production-grade monitoring
**Effort**: 4 days

**Tasks:**

#### A. Add Prometheus Metrics
```bash
uv add prometheus-client
```

**File**: `lift_sys/api/middleware/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Metrics
session_creates = Counter(
    'liftsys_session_creates_total',
    'Total session creations',
    ['source', 'status']
)

session_duration = Histogram(
    'liftsys_session_duration_seconds',
    'Session creation duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

active_sessions = Gauge(
    'liftsys_active_sessions',
    'Number of active sessions'
)

hole_resolutions = Counter(
    'liftsys_hole_resolutions_total',
    'Total hole resolutions',
    ['hole_kind']
)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")
```

#### B. Structured Logging with structlog
```bash
uv add structlog python-json-logger
```

**Configuration:**
```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Usage
logger.info("session.created", session_id=session.session_id, user_id=user.id)
```

#### C. Error Tracking with Sentry
```bash
uv add sentry-sdk[fastapi]
```

**Configuration:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "development"),
)
```

**Success Criteria:**
- ✅ All key operations emit metrics
- ✅ Logs are structured and queryable
- ✅ Errors are captured and alerted
- ✅ Dashboards show system health

---

## Milestone 3: Advanced Features (3-4 weeks)

### 3.1 Real External Tool Integration 🟢 **P2**
**Goal**: Replace mocked analyzers with real implementations
**Effort**: 1 week

**Tasks:**

#### A. Real CodeQL Integration
- Download and install CodeQL CLI
- Create query packs for security and quality
- Integrate with reverse mode lifter
- Handle SARIF output parsing

#### B. Real Daikon Integration
- Install Daikon toolkit
- Generate Chicory traces from test execution
- Parse Daikon invariant output
- Map invariants to IR assertions

#### C. Stack Graphs Integration (already done)
- Enhance existing implementation
- Add more language support
- Improve symbol resolution

**Success Criteria:**
- ✅ Real security vulnerabilities detected
- ✅ Real invariants extracted from code
- ✅ Analysis results feed into IR generation

---

### 3.2 OAuth Provider Integration 🟢 **P2**
**Goal**: Real GitHub OAuth flow
**Effort**: 3 days

**Tasks:**

- Implement actual OAuth callback handling
- Add GitHub App registration
- Store and refresh tokens securely
- Add repository access permissions
- Test with real GitHub accounts

**Success Criteria:**
- ✅ Users can authenticate with GitHub
- ✅ Repository access works end-to-end
- ✅ Tokens are securely stored and refreshed

---

### 3.3 Additional LLM Providers 🟢 **P2**
**Goal**: Support more model providers
**Effort**: 1 week

**Providers to Add:**
- Cohere
- Mistral AI
- Together AI
- Replicate
- Ollama (local models)

**Benefits:**
- More model choices for users
- Cost optimization
- Offline support with Ollama
- Better performance for specific tasks

---

### 3.4 Advanced Planning Strategies 🔵 **P3**
**Goal**: Smarter planning algorithms
**Effort**: 2 weeks

**Enhancements:**
- Heuristic-based search (A*, beam search)
- Learning from user feedback
- Context-aware prioritization
- Multi-objective optimization
- Probabilistic planning

---

### 3.5 Code Generation Improvements 🟢 **P2**
**Goal**: Better quality generated code
**Effort**: 1 week

**Features:**
- Template-based generation with customization
- Style guide enforcement (PEP 8, Google, etc.)
- Documentation generation
- Test case generation
- Type hint inference and checking

---

## Milestone 4: User Experience (2 weeks)

### 4.1 Enhanced Web UI 🟡 **P1**
**Goal**: Better user experience
**Effort**: 1 week

**Features:**
- Dark mode support
- Keyboard shortcuts
- Command palette (Cmd+K)
- Session history and search
- Export to multiple formats (JSON, YAML, Python)
- Collaborative editing (multiple users)
- Real-time collaboration via WebSockets

---

### 4.2 CLI Improvements 🟡 **P1**
**Goal**: Better CLI UX
**Effort**: 3 days

**Features:**
- Rich output formatting with colors
- Progress bars for long operations
- Interactive prompts for ambiguities
- Configuration file support (~/.liftsysrc)
- Shell completion (bash, zsh, fish)
- Watch mode for continuous refinement

---

### 4.3 Plugin System 🔵 **P3**
**Goal**: Extensibility for power users
**Effort**: 1 week

**Features:**
- Custom analyzers
- Custom providers
- Custom IR transformations
- Custom export formats
- Hook system for lifecycle events

---

## Implementation Timeline

### Month 1: Quality & Reliability
- Week 1-2: E2E testing, CI/CD pipeline
- Week 3: Code quality tools, performance benchmarking
- Week 4: Buffer for issues, documentation

### Month 2: Production Infrastructure
- Week 1: Docker support, database integration
- Week 2-3: Monitoring and observability
- Week 4: Security hardening, load testing

### Month 3: Advanced Features
- Week 1: Real tool integration (CodeQL, Daikon)
- Week 2: OAuth and GitHub integration
- Week 3: Additional LLM providers
- Week 4: UX improvements (Web UI, CLI)

### Month 4: Polish & Launch
- Week 1-2: Bug fixes, performance optimization
- Week 3: Documentation updates, tutorials
- Week 4: v0.3.0 release preparation

---

## Success Metrics

### Quality Metrics
- ✅ 95%+ test pass rate
- ✅ 90%+ code coverage
- ✅ 95%+ type coverage
- ✅ Zero critical security vulnerabilities
- ✅ < 5 P0 bugs in production

### Performance Metrics
- ✅ P95 latency < 1s for all API calls
- ✅ Session creation < 500ms
- ✅ IR parsing < 100ms
- ✅ SMT verification < 200ms
- ✅ Support 100+ concurrent users

### Reliability Metrics
- ✅ 99.9% uptime
- ✅ < 1% error rate
- ✅ Database backups automated
- ✅ Zero data loss incidents
- ✅ Mean time to recovery < 5 minutes

### Adoption Metrics
- ✅ 100+ active users
- ✅ 1000+ sessions created
- ✅ < 10% churn rate
- ✅ 90%+ user satisfaction

---

## Risk Assessment

### High Risk
1. **Database Migration** - Could break existing data
   - Mitigation: Comprehensive migration tests, backup strategy

2. **Performance Degradation** - DB might be slower than in-memory
   - Mitigation: Caching layer, connection pooling, benchmarking

### Medium Risk
3. **External Tool Integration** - CodeQL, Daikon may be unreliable
   - Mitigation: Fallback to mocked versions, error handling

4. **OAuth Security** - Token management could have vulnerabilities
   - Mitigation: Use proven libraries, security audit

### Low Risk
5. **UI/UX Changes** - May not meet user expectations
   - Mitigation: User testing, gradual rollout, feedback loops

---

## Resource Requirements

### Development Team
- 1 Backend Engineer (full-time)
- 1 Frontend Engineer (part-time)
- 1 DevOps Engineer (part-time)
- 1 QA Engineer (part-time)

### Infrastructure
- Database: PostgreSQL 16 (managed service)
- Cache: Redis 7
- Monitoring: Prometheus + Grafana
- Error Tracking: Sentry
- CI/CD: GitHub Actions
- Hosting: AWS/GCP/Azure (TBD)

### Estimated Costs
- Infrastructure: $200-500/month
- Services (Sentry, etc.): $100-200/month
- Total: $300-700/month

---

## Decision Points

### After Milestone 1 (Quality & Reliability)
**Question**: Is test coverage and CI/CD sufficient?
**Decision Criteria**:
- All E2E tests passing
- CI/CD catching regressions
- Code quality metrics meet targets

**Go/No-Go**: If No, extend Milestone 1 before moving forward

### After Milestone 2 (Production Deployment)
**Question**: Is the system ready for beta users?
**Decision Criteria**:
- System running stable in Docker
- Database migration tested
- Monitoring shows no critical issues

**Go/No-Go**: If Yes, launch private beta

### After Milestone 3 (Advanced Features)
**Question**: Should we focus on features or polish?
**Decision Criteria**:
- User feedback from beta
- Bug count and severity
- Performance metrics

**Decision**: Adjust Month 4 plan based on feedback

---

## Future Phases (v0.4.0+)

### Phase 4: Enterprise Features
- Multi-tenancy and team collaboration
- Role-based access control (RBAC)
- Audit logging and compliance
- SSO integration (SAML, LDAP)
- Advanced analytics and reporting

### Phase 5: AI Improvements
- Fine-tuned models for specific tasks
- Active learning from user corrections
- Multi-modal input (diagrams, screenshots)
- Automated test generation
- Code review and suggestions

### Phase 6: Platform Expansion
- VS Code extension
- JetBrains plugin
- GitHub App integration
- CI/CD integrations (Jenkins, GitLab CI)
- Jupyter notebook support

---

## Conclusion

This plan transforms lift-sys from a functional prototype to a production-ready platform. The phased approach allows for:

1. **Early Wins**: Quality improvements and E2E tests in Month 1
2. **Foundation**: Production infrastructure in Month 2
3. **Differentiation**: Advanced features in Month 3
4. **Launch Readiness**: Polish and preparation in Month 4

**Key Success Factors:**
- Maintain test quality throughout
- Keep documentation up to date
- Gather user feedback early and often
- Be ready to pivot based on data

**Next Steps:**
1. Review and approve this plan
2. Set up project tracking (GitHub Projects)
3. Begin Milestone 1: E2E Testing Infrastructure
4. Schedule weekly progress reviews

---

**Plan Version**: 1.0
**Created By**: AI Assistant
**Review Date**: October 11, 2025
**Next Review**: After Milestone 1 completion
