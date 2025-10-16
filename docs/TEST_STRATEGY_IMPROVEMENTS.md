# Test Strategy Improvements

**Date**: 2025-10-15
**Problem**: Long-running tests (5+ minutes) block development workflow
**Impact**: Wasted time, reduced productivity, context switching

---

## Current Problems

### 1. **Blocking on Full Test Suites**
- Phase 2 suite: 10 tests × 30-60s each = 5-10 minutes
- Must wait for completion before seeing results
- Single failure wastes entire run time

### 2. **Modal Endpoint Latency**
- Each AI generation call: 10-30 seconds
- Network round-trips add up quickly
- No local fallback for testing

### 3. **No Incremental Feedback**
- All-or-nothing test runs
- Can't see partial progress
- Hard to debug failures

### 4. **Inefficient Test Design**
- Full E2E tests when unit tests would suffice
- Testing same code paths repeatedly
- No test prioritization

---

## Solutions

### ✅ Solution 1: Layered Testing Strategy

**Principle**: Test at the appropriate level - unit tests for logic, integration for workflows, E2E sparingly.

```
Unit Tests (fast, <1s each)
    ↓ Only if passing
Integration Tests (medium, 5-10s each)
    ↓ Only if passing
E2E Tests (slow, 30-60s each)
    ↓ Only before release
Performance Tests (very slow, minutes)
```

**Implementation**:
```bash
# Fast feedback loop (<10s total)
uv run pytest tests/unit/ -v

# Medium feedback loop (<60s total)
uv run pytest tests/integration/ -v -k "not slow"

# Full validation (run when confident)
uv run pytest tests/e2e/ -v
```

**Benefits**:
- Fail fast on unit tests (catch 80% of bugs in <10s)
- Only run expensive tests when needed
- Clear separation of concerns

---

### ✅ Solution 2: Mock Expensive Operations

**Principle**: Don't call real APIs in unit tests.

**Current Problem**:
```python
# test_ast_repair.py calls actual Modal endpoint
generator = XGrammarCodeGenerator(provider)
code_result = await generator.generate(ir)  # 30s wait!
```

**Solution**:
```python
# tests/unit/test_ast_repair.py
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def mock_provider():
    """Mock provider that returns instant results."""
    provider = AsyncMock()
    provider.generate.return_value = "def foo(): return 42"
    return provider

async def test_loop_return_repair(mock_provider):
    """Test AST repair without calling Modal."""
    engine = ASTRepairEngine()

    buggy_code = """
def find_index(lst, val):
    for i, v in enumerate(lst):
        if v == val:
            return i
        return -1  # BUG
"""

    # Repair runs locally, no network calls
    repaired = engine.repair(buggy_code, "find_index")

    assert "return -1" in repaired
    # Verify it's after the loop (check indentation)
```

**Files to Create**:
- `tests/unit/test_ast_repair_unit.py` - Pure logic tests (<1s)
- `tests/integration/test_ast_repair_integration.py` - With real calls (30s)
- `conftest.py` - Shared fixtures for mocking

**Benefits**:
- Unit tests run in <1s (instant feedback)
- Integration tests run only when needed
- No wasted API calls during development

---

### ✅ Solution 3: Parallel Test Execution

**Principle**: Run independent tests concurrently.

**Current**:
```bash
# Sequential: 10 tests × 30s = 300s (5 minutes)
uv run python run_nontrivial_tests.py phase2
```

**Solution**:
```bash
# Parallel: 10 tests / 4 workers = 75s
uv run pytest tests/e2e/ -v -n 4
```

**Implementation**:
```bash
# Install pytest-xdist
uv add --dev pytest-xdist

# Run tests in parallel
uv run pytest tests/ -v -n auto  # Use all CPUs
uv run pytest tests/ -v -n 4     # Use 4 workers
```

**Benefits**:
- 4x speedup on independent tests
- Better CPU utilization
- Faster feedback

---

### ✅ Solution 4: Targeted Test Selection

**Principle**: Only run tests related to changes.

**Implementation**:
```bash
# Test only AST repair (not full suite)
uv run pytest tests/unit/test_ast_repair.py -v

# Test only specific function
uv run pytest tests/unit/test_ast_repair.py::test_loop_return_repair -v

# Test only fast tests
uv run pytest tests/ -v -m "not slow"
```

**Pytest markers**:
```python
# Mark slow tests
@pytest.mark.slow
async def test_full_e2e_pipeline():
    ...

# Mark by component
@pytest.mark.ast_repair
async def test_loop_return():
    ...
```

**Run configurations**:
```bash
# Fast: unit tests only (<10s)
uv run pytest -m "not slow and not e2e" -v

# Medium: include integration (<60s)
uv run pytest -m "not slow" -v

# Full: everything (run before commit)
uv run pytest -v
```

---

### ✅ Solution 5: Background Test Runs

**Principle**: Start tests, continue working, check results later.

**Current**: Block on test completion
**Solution**: Run in background, work on next task

**Implementation**:
```bash
# Start Phase 2 tests in background
uv run python run_nontrivial_tests.py phase2 > test_results.log 2>&1 &
TEST_PID=$!

# Continue working on Phase 5
# ... implement IR interpreter ...

# Check if tests done
if kill -0 $TEST_PID 2>/dev/null; then
    echo "Tests still running..."
else
    echo "Tests complete!"
    cat test_results.log | tail -50
fi
```

**For Claude Code**: Use run_in_background parameter
```python
# Already used this but didn't continue working!
Bash(command="long test", run_in_background=True)

# Then continue with other work
# Check later with BashOutput tool
```

**Benefits**:
- No blocking on long tests
- Can implement next feature while tests run
- Check results when convenient

---

### ✅ Solution 6: Incremental Test Reporting

**Principle**: Get feedback as tests complete, not at the end.

**Current**: All-or-nothing output
**Solution**: Stream results as they complete

**Implementation**:
```python
# run_nontrivial_tests.py
async def run_test_suite(phase="phase2"):
    for i, test in enumerate(tests, 1):
        print(f"\n[{i}/{len(tests)}] Testing {test['name']}...", flush=True)

        result = await run_single_test(test)

        # Immediate feedback
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"[{i}/{len(tests)}] {test['name']}: {status}", flush=True)

        if not result.success:
            print(f"  Error: {result.error}", flush=True)
```

**Benefits**:
- See progress in real-time
- Know which test is slow
- Can interrupt if needed

---

### ✅ Solution 7: Test Caching

**Principle**: Don't re-test unchanged code.

**Implementation**:
```bash
# pytest-cache (built-in)
uv run pytest --last-failed  # Only run previously failed tests
uv run pytest --failed-first  # Run failed tests first, then rest

# pytest-testmon (smart re-running)
uv add --dev pytest-testmon
uv run pytest --testmon  # Only run tests affected by code changes
```

**Benefits**:
- Skip passing tests on re-run
- Focus on failures
- Faster iteration

---

### ✅ Solution 8: Local Test Mode

**Principle**: Fast local mode for development, full mode for CI.

**Implementation**:
```python
# tests/conftest.py
import os
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def provider(request):
    """
    Provider fixture that switches based on TEST_MODE env var.

    TEST_MODE=local  - Use mocks (fast)
    TEST_MODE=full   - Use real Modal endpoint (slow)
    """
    mode = os.getenv("TEST_MODE", "local")

    if mode == "local":
        # Mock provider for unit tests
        mock = AsyncMock()
        mock.generate.return_value = MockResponse(...)
        return mock
    else:
        # Real provider for integration tests
        from lift_sys.providers.modal_provider import ModalProvider
        provider = ModalProvider(...)
        await provider.initialize()
        return provider
```

**Usage**:
```bash
# Fast local mode (mocks, <10s)
TEST_MODE=local uv run pytest tests/

# Full mode with real APIs (slow, before commit)
TEST_MODE=full uv run pytest tests/
```

---

## Implementation Plan for Phase 5

### Before Starting Phase 5

**Priority 1: Test Infrastructure** (2-3 hours)

1. ✅ **Create unit test suite with mocks**
   ```bash
   tests/unit/test_ir_interpreter.py  # Pure logic, <1s per test
   tests/conftest.py                  # Mock fixtures
   ```

2. ✅ **Add pytest markers**
   ```python
   # In tests
   @pytest.mark.unit       # Fast unit tests
   @pytest.mark.integration  # Medium integration tests
   @pytest.mark.slow       # Slow E2E tests
   ```

3. ✅ **Configure pytest.ini**
   ```ini
   [pytest]
   markers =
       unit: Fast unit tests (<1s each)
       integration: Integration tests (5-10s each)
       slow: Slow E2E tests (>30s each)
       ir_interpreter: Tests for IR interpreter
       ast_repair: Tests for AST repair

   # Default: skip slow tests
   addopts = -v -m "not slow"
   ```

4. ✅ **Install test tools**
   ```bash
   uv add --dev pytest-xdist pytest-timeout pytest-testmon
   ```

**Priority 2: Refactor Existing Tests** (1-2 hours)

1. Split `test_ast_repair.py` into:
   - `tests/unit/test_ast_repair_unit.py` - Logic only (mocked, <1s)
   - `tests/integration/test_ast_repair_integration.py` - With real calls (30s)

2. Add markers to Phase 2 tests:
   ```python
   @pytest.mark.slow
   @pytest.mark.e2e
   async def test_full_phase2_suite():
       ...
   ```

3. Create fast smoke test:
   ```python
   @pytest.mark.unit
   async def test_ast_repair_smoke():
       """Quick sanity check (<1s)."""
       engine = ASTRepairEngine()
       assert engine is not None
   ```

### During Phase 5 Development

**Test-Driven Development Workflow**:

```bash
# 1. Write unit test (mock everything)
# tests/unit/test_ir_interpreter.py
@pytest.mark.unit
async def test_ir_interpreter_validates_holes():
    ir = MockIR(holes=[...])
    interpreter = IRInterpreter()
    result = interpreter.validate(ir)
    assert result.is_valid == False

# 2. Run unit test (instant feedback, <1s)
uv run pytest tests/unit/test_ir_interpreter.py -v

# 3. Implement feature
# lift_sys/ir/interpreter.py
...

# 4. Re-run unit test (iterate quickly)
uv run pytest tests/unit/test_ir_interpreter.py -v

# 5. Once unit tests pass, run integration test
uv run pytest tests/integration/test_ir_interpreter.py -v

# 6. Only run full E2E when confident
TEST_MODE=full uv run pytest tests/e2e/ -v
```

**Parallel background runs**:
```bash
# Start slow tests in background
uv run pytest tests/e2e/ -v > e2e_results.log 2>&1 &

# Continue developing next feature
# ... implement abstract validator ...

# Check results when done
cat e2e_results.log | tail -100
```

---

## Test Pyramid for lift-sys

```
        E2E Tests (slow, few)
       10 tests, 5-10 min total
      Run before commit/release
           /\
          /  \
         /    \
        /      \
       /        \
      /  Integ.  \
     /   Tests    \
    /  30 tests,   \
   /   1-5 min      \
  /  Run on PR       \
 /                    \
/__Unit Tests (fast)__\
  100+ tests, <30s
  Run on every save
```

**Guidelines**:
- **Unit tests**: 70% of tests, <1s each, no external dependencies
- **Integration tests**: 25% of tests, 5-10s each, real components but mocked APIs
- **E2E tests**: 5% of tests, 30-60s each, everything real

---

## Quick Reference

### Fast Feedback Commands

```bash
# Fastest: Unit tests only (<10s)
uv run pytest tests/unit/ -v

# Medium: Unit + Integration (<60s)
uv run pytest -m "not slow" -v

# Full: Everything (before commit)
uv run pytest -v

# Parallel: 4x faster
uv run pytest -v -n 4

# Only failed: Skip passing tests
uv run pytest --failed-first -v

# Specific test: Focus on one thing
uv run pytest tests/unit/test_ir_interpreter.py::test_validate_holes -v
```

### Background Test Pattern

```bash
# Start in background
uv run pytest tests/e2e/ -v > results.log 2>&1 &

# Continue working
# ... develop next feature ...

# Check when convenient
tail -f results.log  # Watch progress
cat results.log | grep "PASSED\|FAILED"  # Summary
```

---

## Expected Improvements

### Before
- ❌ Wait 5-10 minutes for Phase 2 suite
- ❌ All-or-nothing feedback
- ❌ Blocked on test completion
- ❌ Re-test everything after small change

### After
- ✅ Unit tests give feedback in <10s
- ✅ Know results as tests complete
- ✅ Run tests in background, continue working
- ✅ Only re-test changed components

### Productivity Impact
- **80% reduction** in wait time (10s vs 5min for typical feedback)
- **4x faster** with parallel execution
- **Better debugging** with incremental feedback
- **Faster iteration** with targeted tests

---

## Phase 5 Test Plan

### Unit Tests (create first, <1s each)

```python
# tests/unit/test_ir_interpreter.py

@pytest.mark.unit
async def test_validate_filled_ir():
    """Interpreter accepts fully filled IR."""
    ir = create_mock_ir(holes=[])
    interpreter = IRInterpreter()
    result = interpreter.validate(ir)
    assert result.is_valid == True

@pytest.mark.unit
async def test_reject_unfilled_holes():
    """Interpreter rejects IR with holes."""
    ir = create_mock_ir(holes=[Hole(...)])
    interpreter = IRInterpreter()
    result = interpreter.validate(ir)
    assert result.is_valid == False
    assert "unfilled holes" in result.error

@pytest.mark.unit
async def test_validate_control_flow():
    """Interpreter validates control flow paths."""
    ir = create_mock_ir(
        branches=[Branch(condition=..., no_return=True)]
    )
    interpreter = IRInterpreter()
    result = interpreter.validate(ir)
    assert result.is_valid == False
    assert "missing return" in result.error
```

**Run time**: <5s for 20+ unit tests

### Integration Tests (create after unit tests pass, 5-10s each)

```python
# tests/integration/test_ir_interpreter_integration.py

@pytest.mark.integration
async def test_interpreter_with_real_ir():
    """Test interpreter with actual IR from translator."""
    translator = XGrammarIRTranslator(mock_provider)
    ir_result = await translator.translate("simple prompt")

    interpreter = IRInterpreter()
    validation = interpreter.validate(ir_result.ir)

    assert validation.is_valid == True
```

**Run time**: <60s for 10 integration tests

### E2E Tests (create last, run sparingly, 30-60s each)

```python
# tests/e2e/test_phase5_complete.py

@pytest.mark.slow
@pytest.mark.e2e
async def test_full_pipeline_with_interpreter():
    """Full pipeline: prompt → IR → validate → code."""
    # This runs with real Modal endpoint
    ...
```

**Run time**: 5-10 minutes for full E2E suite
**When to run**: Before commit, not during development

---

## Action Items Before Phase 5

- [ ] Create `tests/conftest.py` with mock fixtures
- [ ] Create `pytest.ini` with markers and default config
- [ ] Install `pytest-xdist`, `pytest-timeout`, `pytest-testmon`
- [ ] Refactor `test_ast_repair.py` → separate unit/integration
- [ ] Create unit test template for Phase 5
- [ ] Document background test pattern in CLAUDE.md
- [ ] Add fast feedback commands to README

**Estimated time**: 3-4 hours
**Payoff**: Save 2-3 hours per development session

---

## Bottom Line

**Problem**: Long tests block development workflow

**Solution**: Layered testing strategy
1. **Unit tests** (mocked, <10s) - Use during development
2. **Integration tests** (real components, <60s) - Use for verification
3. **E2E tests** (everything real, 5-10min) - Use before commit
4. **Background runs** - Start slow tests, continue working

**Implementation**: Before Phase 5, set up test infrastructure (3-4 hours)

**Result**: **80% faster feedback** during development, unblocked workflow
