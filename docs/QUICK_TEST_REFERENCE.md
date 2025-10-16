# Quick Test Reference

Fast feedback loops for lift-sys development.

---

## Default Behavior

```bash
# Fast tests only (unit + integration, skips slow/e2e)
uv run pytest
```

**Default config** (in `pytest.ini`):
- `-m "not slow"` - Skip slow tests
- `-v` - Verbose output
- `--tb=short` - Shorter tracebacks
- Only runs tests < 30s

**Result**: Fast feedback in <60s instead of 5-10 minutes

---

## Common Commands

### Fast Feedback (<10s)

```bash
# Unit tests only
uv run pytest tests/unit/

# Specific test file
uv run pytest tests/unit/test_ast_repair.py

# Specific test
uv run pytest tests/unit/test_ast_repair.py::test_loop_return_repair
```

### Medium Feedback (<60s)

```bash
# All fast tests (unit + integration)
uv run pytest -m "not slow"

# Integration tests only
uv run pytest tests/integration/
```

### Full Validation (5-10 min)

```bash
# Everything including slow E2E tests
uv run pytest -m ""

# Or explicitly run slow tests
uv run pytest -m slow
```

### Parallel Execution (4x faster)

```bash
# Install first (if not installed)
uv add --dev pytest-xdist

# Run with 4 workers
uv run pytest -n 4

# Auto-detect CPUs
uv run pytest -n auto
```

---

## Response Recording (30-60x Faster Integration Tests)

**Problem**: Modal API calls take 30-60s, making integration tests slow

**Solution**: Record responses once, replay them instantly

```bash
# First run: Record Modal responses (slow, ~30-60s)
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_test.py -v

# Subsequent runs: Use cached responses (fast, <1s)
uv run pytest tests/integration/test_your_test.py -v

# Re-record when prompts/API changes
RECORD_FIXTURES=true uv run pytest tests/integration/ -v
```

**See**: `docs/RESPONSE_RECORDING_GUIDE.md` for complete guide

---

## Test by Component

```bash
# AST repair tests
uv run pytest -m ast_repair

# IR interpreter tests (Phase 5)
uv run pytest -m ir_interpreter

# Code generation tests
uv run pytest -m code_generator

# XGrammar tests
uv run pytest -m xgrammar
```

---

## Useful Flags

```bash
# Run only failed tests from last run
uv run pytest --failed-first

# Run only tests that failed last time
uv run pytest --last-failed

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l

# More detailed output
uv run pytest -vv

# Show print statements
uv run pytest -s
```

---

## Background Test Pattern

For long-running tests, start them in background and continue working:

```bash
# Start slow tests in background
uv run pytest -m slow > slow_results.log 2>&1 &

# Continue working on next task
# ... implement next feature ...

# Check progress
tail -f slow_results.log

# Check if done
cat slow_results.log | grep "passed\|failed"
```

---

## Test-Driven Development Workflow

```bash
# 1. Write unit test (fast)
# tests/unit/test_new_feature.py

# 2. Run unit test (<1s)
uv run pytest tests/unit/test_new_feature.py -v

# 3. Implement feature
# lift_sys/module/new_feature.py

# 4. Re-run unit test (iterate quickly)
uv run pytest tests/unit/test_new_feature.py -v

# 5. Once passing, run integration tests
uv run pytest tests/integration/ -v

# 6. Before commit, run full suite
uv run pytest -m ""
```

---

## Markers Cheat Sheet

| Marker | Speed | When to Use |
|--------|-------|-------------|
| `@pytest.mark.unit` | <1s | Pure logic, no external deps |
| `@pytest.mark.integration` | 5-10s | Real components, mocked APIs |
| `@pytest.mark.slow` | >30s | Full E2E, real APIs |
| `@pytest.mark.e2e` | 30-60s | Complete user workflows |
| `@pytest.mark.modal` | Variable | Requires Modal endpoint |

---

## Expected Performance

### Before

```bash
# Wait for everything (no choice)
$ uv run python run_nontrivial_tests.py phase2
... 5-10 minutes ...
```

### After

```bash
# Fast feedback for development
$ uv run pytest tests/unit/
... <10 seconds ... ✅

# Medium feedback for verification
$ uv run pytest -m "not slow"
... <60 seconds ... ✅

# Full validation before commit
$ uv run pytest -m ""
... 5-10 minutes ... (same as before, but optional)
```

**Result**: **80-95% faster feedback** during development

---

## Tips

1. **Default to fast tests**: Let pytest.ini skip slow tests automatically
2. **Run targeted tests**: Test only what you changed
3. **Use markers**: Organize tests by speed and component
4. **Background long tests**: Start slow tests, continue working
5. **Parallel when possible**: Use `-n auto` for independent tests
6. **Failed-first iteration**: `--failed-first` for debugging

---

## Phase 5 Recommended Workflow

```bash
# 1. Write unit test for IR interpreter
vim tests/unit/test_ir_interpreter.py

# 2. Run it (instant feedback)
uv run pytest tests/unit/test_ir_interpreter.py -v

# 3. Implement IR interpreter
vim lift_sys/ir/interpreter.py

# 4. Iterate on unit tests (fast loop)
uv run pytest tests/unit/test_ir_interpreter.py -v

# 5. Once unit tests pass, integration
uv run pytest tests/integration/test_ir_interpreter.py -v

# 6. Start E2E in background, continue to Phase 6
uv run pytest -m slow > phase5_e2e.log 2>&1 &

# 7. Work on Phase 6 while Phase 5 E2E runs
vim lift_sys/validation/abstract_validator.py
```

---

## Troubleshooting

**Q: Tests still running slow?**
```bash
# Check if slow tests are running
uv run pytest --collect-only | grep "slow"

# Ensure pytest.ini is being used
uv run pytest --version
```

**Q: Want to see which tests are slow?**
```bash
# Show durations of slowest 10 tests
uv run pytest --durations=10
```

**Q: Need to run just one slow test?**
```bash
# Override the default marker filter
uv run pytest -m slow tests/e2e/test_specific.py
```

---

## Bottom Line

**Old way**: Wait 5-10 minutes for every test run
**New way**: Get feedback in 10 seconds, run slow tests only when needed

Use the test pyramid:
- **70% unit tests** (<1s) - Run constantly
- **25% integration** (5-10s) - Run before commit
- **5% E2E** (30-60s) - Run before release

This is now configured in `pytest.ini` - just run `pytest` for fast feedback!
