---
track: testing
status: active
priority: P0
phase: stabilization_complete
completion: 100%
last_updated: 2025-10-27
session_protocol: |
  For new Claude Code session:
  1. Read this STATUS.md (< 30 seconds context)
  2. Check latest test results: `tail -100 validation/*_tests_*.log`
  3. Verify all passing: 148/148 core tests ✅
  4. Run tests AFTER committing: `git commit` → `pkill -f pytest` → `uv run pytest`
  5. Begin test expansion or quality improvements
related_docs:
  - docs/SESSION_SUMMARY_20251027.md
  - docs/MASTER_ROADMAP.md
  - CLAUDE.md (Section 6: Testing & Validation)
---

# Testing & Quality Track Status

**Last Updated**: 2025-10-27
**Track Priority**: P0 (Stability foundation)
**Current Phase**: Core stabilization complete, expansion planning

---

## For New Claude Code Session

**Quick Context** (30 seconds):
- **148/148 core tests passing** (100% pass rate achieved today!)
- Test suites: Unit (90), Integration (30), E2E (74), DSPy (394/409)
- Critical fixes today: MockProvider, Prediction conversion, validation severity
- Next: Performance benchmarks, integration test expansion

**Check Test Status**:
```bash
# Run full test suite (AFTER committing!)
git add . && git commit -m "Changes"
pkill -f pytest
uv run pytest tests/ > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
wait && tail -100 /tmp/test_*.log

# Check specific suites
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
cd frontend && npm run test:e2e
```

---

## Current Status (2025-10-27)

### ✅ Major Achievement: 148/148 Core Tests Passing

**Stabilization Complete** (Phase 1):
- TypeScript Generator: 17/17 ✅ (fixed today)
- TUI Session Methods: 16/16 ✅ (already passing)
- DSPy Concurrency: 15/15 ✅ (already passing)
- Parallel LSP: 11/11 ✅
- Effect Analyzer: 6/6 ✅
- Semantic Validator: 9/9 ✅ (fixed today)
- ICS E2E: 74/74 ✅

**Test Breakdown**:
```
Core Tests:        148/148 ✅ (100%)
├─ TypeScript:      17/17 ✅
├─ TUI:             16/16 ✅
├─ DSPy:            15/15 ✅
├─ Parallel LSP:    11/11 ✅
├─ Effect Analyzer:  6/6  ✅
├─ Sem Validator:    9/9  ✅
└─ ICS E2E:         74/74 ✅

Extended Tests:
├─ DSPy Full:      394/409 (96%) - 15 skipped (DoWhy env)
└─ Backend API:    All passing ✅
```

---

## Recent Work (2025-10-27)

### Test Fixes (4 commits)

**Commit 1**: `738db95` - MockProvider structured_output fix
```python
# Changed: structured_output=False → True
# Impact: Fixed 17 TypeScript generator tests
# Root cause: MockProvider capability mismatch
```

**Commit 2**: `e7c9545` - TypeScript test schema fixes
```python
# Changed: Test JSON to match TYPESCRIPT_GENERATION_SCHEMA
# Impact: Fixed 2 tests (imports at top level, not in implementation)
```

**Commit 3**: `9973eda` - dspy.Prediction dict conversion
```python
# Changed: prediction.__dict__ → dict(prediction)
# Impact: Fixed 2 tests (Prediction data in _store, not __dict__)
# Root cause: DSPy stores data in _store attribute
```

**Commit 4**: `70f77bf` - missing_return severity fix
```python
# Changed: severity="warning" → "error"
# Impact: Fixed 3 validation tests
# Root cause: Warnings don't fail validation, only errors do
```

---

## Test Architecture

### Test Pyramid

```
           E2E (74 tests)
          ╱              ╲
    Integration (30)
   ╱                    ╲
Unit (90)
```

**Philosophy**:
- **Unit**: Fast, isolated, many tests
- **Integration**: Medium speed, system interactions
- **E2E**: Slower, full workflows, critical paths only

### Test Organization

```
tests/
├── unit/                      # 90 tests
│   ├── test_ir_models.py     # IR data models
│   ├── test_typescript_generator.py  # TS codegen
│   ├── test_tui_session_methods.py   # TUI methods
│   └── dspy_signatures/      # DSPy architecture tests
├── integration/               # 30 tests
│   ├── test_api_endpoints.py # FastAPI integration
│   ├── test_supabase_store.py  # Database integration
│   └── test_provider_adapter.py  # LLM provider integration
├── e2e/                       # E2E scenarios (backend)
│   └── test_full_workflow.py # NLP → IR → Code
├── causal/                    # 19 tests (skipped - needs env)
│   └── test_scm_fitter_dynamic.py
├── fixtures/                  # Test data
│   ├── irs/                  # Example IRs
│   ├── code_responses.json   # LLM responses
│   └── schemas/              # JSON schemas
└── conftest.py               # Shared pytest config

frontend/playwright/
├── ics.spec.ts               # 74 E2E tests
└── auth.setup.ts             # Auth fixtures
```

---

## Testing Protocols

### Critical Testing Protocol (MANDATORY)

**ABSOLUTE RULE**: NEVER run tests before committing

```bash
# ✅ CORRECT FLOW
1. Make changes
2. git add . && git commit -m "Description"
3. git log -1 --oneline  # Verify commit
4. pkill -f "pytest"     # Kill old tests
5. uv run pytest tests/ > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
6. wait                  # Wait for completion
7. tail -f /tmp/test_*.log  # Verify results

# ❌ WRONG FLOW
Code → Test → Commit  # Tests stale code, hours wasted!
```

**Why This Order Matters**:
```
WRONG: Code → Test → Commit
  → Tests run against uncommitted code
  → False positives/negatives
  → Hours debugging wrong issues

CORRECT: Code → Commit → Kill Old → Test
  → Tests run against committed code
  → Valid results
  → Clear debugging path
```

### Test Isolation

**Between Tests**:
- `conftest.py` provides `reset_state()` fixture
- Each test gets fresh provider/adapter instances
- No shared state between tests

**Mocking Strategy**:
- **Unit tests**: Mock external services (LLM, DB)
- **Integration tests**: Use real services with test data
- **E2E tests**: Full system with real API

---

## Test Coverage

### Current Coverage (by module)

```
Module                          Coverage
─────────────────────────────────────────
lift_sys/ir/                    95%
lift_sys/codegen/               90%
lift_sys/validation/            92%
lift_sys/forward_mode/          85%
lift_sys/dspy_signatures/       80%
lift_sys/api/                   75%
lift_sys/storage/               70%
lift_sys/providers/             65%
```

### Coverage Goals

- **Core IR**: >95% (mission-critical)
- **Code Generation**: >90%
- **Validation**: >90%
- **API**: >80%
- **Providers**: >70% (external dependencies)

### Measuring Coverage

```bash
# Full coverage report
uv run pytest --cov=lift_sys --cov-report=html tests/

# View report
open htmlcov/index.html

# Terminal summary
uv run pytest --cov=lift_sys --cov-report=term-missing tests/
```

---

## Test Fixtures & Data

### Fixture Categories

**1. Provider Fixtures** (`conftest.py`):
- `mock_provider` - MockProvider for unit tests
- `modal_provider` - Real Modal.com provider (integration)
- `reset_state` - Clean state between tests

**2. IR Fixtures** (`tests/fixtures/irs/`):
- Example IRs for different scenarios
- Valid IRs (positive tests)
- Invalid IRs (negative tests)

**3. Code Response Fixtures** (`code_responses.json`):
- LLM responses for code generation
- Structured output examples
- Error responses

**4. Schema Fixtures** (`tests/fixtures/schemas/`):
- JSON schemas for validation
- TypeScript schema definitions

### Recording Live Fixtures

```bash
# Record real LLM responses (for integration tests)
RECORD_FIXTURES=true uv run pytest tests/integration/

# Replay from fixtures (faster, deterministic)
uv run pytest tests/integration/
```

---

## Performance Benchmarking

### Benchmark Suite

**Location**: `performance_benchmark.py`
**Run**: `./scripts/benchmarks/run_benchmark.sh`

**Metrics Tracked**:
- **Latency**: p50, p95, p99 (seconds)
- **Throughput**: Requests per second
- **Success Rate**: % valid outputs
- **Token Usage**: Input/output tokens

**Current Baseline** (Oct 2025):
```
Metric                Value
─────────────────────────────
p50 Latency:          16s
p95 Latency:          28s
Success Rate:         60%
Cost per Request:     $0.02
```

### Benchmark Scenarios

1. **Simple Function** (add two numbers)
2. **Medium Function** (filter list, transform data)
3. **Complex Function** (nested logic, multiple effects)
4. **Error Cases** (invalid prompts, edge cases)

---

## Known Issues

### Active Issues

**DoWhy Tests Skipped** (19 tests):
- Requires `.venv-dowhy` with Python 3.11
- Not blocking current work
- TODO: Set up proper environment

### Resolved Issues (Today!)

✅ **TypeScript Generator** (17 tests) - MockProvider capability mismatch
✅ **Validation Tests** (3 tests) - missing_return severity classification
✅ **DSPy Concurrency** (15 tests) - Already passing, background tests stale

---

## Testing Standards

### Code Quality

**Enforced by pre-commit**:
- **ruff**: Linting (replaces flake8, isort)
- **ruff format**: Formatting (replaces black)
- **mypy**: Type checking (--strict on DSPy modules)
- **pytest**: Test execution
- **secrets detection**: No secrets in commits

**Running Checks**:
```bash
# Pre-commit hooks (runs on git commit)
pre-commit run --all-files

# Manual checks
ruff check lift_sys/
ruff format lift_sys/
mypy lift_sys/dspy_signatures/ --strict
```

### Test Writing Standards

**Structure** (AAA pattern):
```python
def test_feature():
    # Arrange: Set up test data and mocks
    provider = MockProvider()
    adapter = ProviderAdapter(provider)

    # Act: Execute the code under test
    result = adapter.generate(prompt="test")

    # Assert: Verify expected outcomes
    assert result is not None
    assert "implementation" in result
```

**Naming Convention**:
- `test_<feature>_<scenario>_<expected_outcome>`
- Examples:
  - `test_typescript_generator_valid_ir_returns_code`
  - `test_validation_missing_return_raises_error`
  - `test_adapter_structured_output_uses_xgrammar`

**Markers**:
```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow test (>1s)
@pytest.mark.skip(reason="...")  # Skip with reason
```

---

## Roadmap

### Phase 2: Test Expansion (Q4 2025)

**Integration Tests** (expand from 30 → 60):
- Supabase RLS enforcement
- Modal.com provider edge cases
- API endpoint error handling
- Session concurrency

**Performance Tests**:
- Benchmark suite automation (CI)
- Regression detection (alert on >10% slowdown)
- Load testing (100 concurrent requests)
- Memory profiling

**E2E Tests** (expand from 74 → 100):
- Multi-session workflows
- Error recovery scenarios
- Real-time updates
- Collaboration features

### Phase 3: Quality Automation (Q1 2026)

**CI/CD Integration**:
- GitHub Actions: Run tests on every PR
- Automated coverage reporting
- Performance benchmarks in CI
- Fail PR if coverage drops >5%

**Mutation Testing**:
- Use `mutmut` to detect untested code paths
- Measure test suite quality (not just coverage)

**Property-Based Testing**:
- Use `hypothesis` for IR validation
- Generate random IRs and verify invariants
- Detect edge cases automatically

---

## Resources

### Documentation

- **Testing Protocol**: `CLAUDE.md` Section 6 (Testing & Validation)
- **Benchmark Results**: `docs/benchmarks/`
- **Session Summary**: `docs/SESSION_SUMMARY_20251027.md` (today's fixes)

### External Tools

- **pytest**: https://docs.pytest.org
- **Playwright**: https://playwright.dev
- **pytest-cov**: https://pytest-cov.readthedocs.io
- **hypothesis**: https://hypothesis.readthedocs.io

---

## Quick Commands

```bash
# Run all tests (AFTER committing!)
git add . && git commit -m "Changes"
pkill -f pytest
uv run pytest tests/ > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Run specific suite
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
cd frontend && npm run test:e2e

# Coverage
uv run pytest --cov=lift_sys --cov-report=html tests/

# Benchmarks
./scripts/benchmarks/run_benchmark.sh

# Pre-commit checks
pre-commit run --all-files
```

---

**End of Testing Track Status**

**For next session**: Expand integration tests or set up CI automation.
