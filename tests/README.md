# Lift-Sys Test Suite

Comprehensive test suite for the lift-sys modular platform for verifiable AI-native software development.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)

## Overview

This test suite follows the **Testing Pyramid** philosophy:
- **Large base of fast unit tests** - Testing isolated components
- **Medium layer of integration tests** - Testing service interactions
- **Small apex of E2E tests** - Testing complete user workflows

### Testing Philosophy

1. **Isolation**: External dependencies (CodeQL, Daikon, LLM APIs) are mocked
2. **Determinism**: Tests produce consistent results
3. **Speed**: Fast feedback loop for developers
4. **Clarity**: Descriptive test names and clear assertions
5. **Coverage**: High code coverage across all components

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures for all tests
├── fixtures/                # Test data and sample files
│   ├── sample_simple.ir    # Simple IR without holes
│   ├── sample_with_holes.ir # IR with TypedHoles
│   ├── sample_complex.ir   # Complex IR with effects
│   ├── sample_invalid.ir   # Invalid IR for error testing
│   └── sample_code.py      # Sample Python code for reverse mode
│
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_parser.py      # IR parser tests
│   ├── test_verifier.py    # SMT checker tests
│   ├── test_planner.py     # Planner with CDL tests
│   ├── test_models.py      # IR model serialization tests
│   └── test_synthesizer.py # Code synthesizer tests
│
├── integration/             # Integration tests (service interactions)
│   ├── test_api_endpoints.py  # FastAPI endpoint tests
│   └── test_reverse_mode.py   # Reverse mode lifter tests
│
└── e2e/                     # End-to-end tests (full workflows)
    ├── test_tui.py         # Textual TUI workflow tests
    └── test_web_ui.py      # Playwright web UI tests
```

## Running Tests

### Prerequisites

```bash
# Install dependencies
uv sync

# Install optional dev dependencies
uv add --dev pytest pytest-cov pytest-mock pytest-asyncio
```

### Run All Tests

```bash
# Run all tests with coverage
uv run pytest --cov=lift_sys --cov-report=html

# Run all tests verbosely
uv run pytest -v
```

### Run Specific Test Categories

```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Run only E2E tests (slow)
uv run pytest -m e2e

# Exclude slow tests
uv run pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Run parser tests
uv run pytest tests/unit/test_parser.py

# Run API endpoint tests
uv run pytest tests/integration/test_api_endpoints.py

# Run single test
uv run pytest tests/unit/test_parser.py::TestIRParser::test_parse_simple_ir
```

### Coverage Reports

```bash
# Generate HTML coverage report
uv run pytest --cov=lift_sys --cov-report=html
# Open htmlcov/index.html in browser

# Generate terminal coverage report
uv run pytest --cov=lift_sys --cov-report=term-missing

# Generate XML coverage report (for CI)
uv run pytest --cov=lift_sys --cov-report=xml
```

## Test Categories

### Unit Tests (80+ tests)

Fast, isolated tests for individual components.

#### IR Parser Tests (`test_parser.py`)
- ✅ Valid IR parsing
- ✅ TypedHole syntax parsing
- ✅ Syntax error handling
- ✅ Edge cases (empty files, comments)
- ✅ Round-trip serialization

#### SMT Verifier Tests (`test_verifier.py`)
- ✅ Provably true assertions (UNSAT)
- ✅ Provably false assertions (SAT with counterexample)
- ✅ Various comparison operators
- ✅ Multiple variables
- ✅ Arithmetic expressions
- ✅ Boundary conditions

#### Planner Tests (`test_planner.py`)
- ✅ Plan generation from IR
- ✅ Conflict-driven learning
- ✅ Fallback strategies
- ✅ Step progression
- ✅ Constraint learning

#### IR Models Tests (`test_models.py`)
- ✅ Model creation
- ✅ Serialization (to_dict)
- ✅ Deserialization (from_dict)
- ✅ Round-trip fidelity
- ✅ TypedHole handling

#### Code Synthesizer Tests (`test_synthesizer.py`)
- ✅ Configuration handling
- ✅ Prompt generation from IR
- ✅ Constraint compilation
- ✅ Request payload generation

### Integration Tests (21+ tests)

Tests for service interactions and API endpoints.

#### API Endpoint Tests (`test_api_endpoints.py`)
- ✅ All API endpoints
- ✅ Happy path (200 OK)
- ✅ Error handling (4xx)
- ✅ Request/response formats
- ✅ State management
- ✅ Concurrent requests

#### Reverse Mode Tests (`test_reverse_mode.py`)
- ✅ Specification lifting workflow
- ✅ Mocked CodeQL integration
- ✅ Mocked Daikon integration
- ✅ Conflicting analysis results
- ✅ TypedHole generation for ambiguity

### E2E Tests (Placeholder)

Complete user workflow tests (currently skipped, require full UI implementation).

#### TUI Tests (`test_tui.py`)
- ⏸️  TUI navigation
- ⏸️  IR file loading and editing
- ⏸️  Forward mode generation workflow
- ⏸️  User interactions with TypedHoles

#### Web UI Tests (`test_web_ui.py`)
- ⏸️  Complete user workflows
- ⏸️  Repository selection
- ⏸️  IR editor interactions
- ⏸️  Forward/reverse mode workflows

## Writing Tests

### Test Structure

Follow this structure for new tests:

```python
"""Module docstring describing what is tested."""
import pytest

from lift_sys.component import Component


@pytest.mark.unit  # or integration, e2e
class TestComponentName:
    """Test class for ComponentName."""

    def test_feature_does_something(self, fixture_name):
        """Test that feature does something specific."""
        # Arrange
        component = Component()

        # Act
        result = component.do_something()

        # Assert
        assert result == expected_value
```

### Using Fixtures

Shared fixtures are defined in `conftest.py`:

```python
def test_with_parser(ir_parser, sample_simple_ir):
    """Test using shared fixtures."""
    ir = ir_parser.parse(sample_simple_ir)
    assert ir is not None
```

### Mocking External Dependencies

Use `pytest-mock` or `unittest.mock` for external dependencies:

```python
from unittest.mock import patch

@patch("subprocess.run")
def test_with_mocked_subprocess(mock_run):
    """Test with mocked external tool."""
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
    # Test code that calls subprocess
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit  # Fast unit test
@pytest.mark.integration  # Integration test
@pytest.mark.e2e  # End-to-end test
@pytest.mark.slow  # Slow test (skipped by default)
```

## Test Coverage

### Current Coverage

- **Unit Tests**: 80+ tests covering core logic
- **Integration Tests**: 21+ tests covering API and services
- **E2E Tests**: Placeholder structure for future implementation

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| IR Parser | 90%+ | ✅ |
| SMT Verifier | 85%+ | ✅ |
| Planner | 85%+ | ✅ |
| IR Models | 90%+ | ✅ |
| API Endpoints | 80%+ | ✅ |
| Reverse Mode | 70%+ | ✅ |
| Forward Mode | 80%+ | ✅ |

### Viewing Coverage

```bash
# Generate and view HTML coverage report
uv run pytest --cov=lift_sys --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest --cov=lift_sys --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
uv run pytest -m "unit" --maxfail=1
```

## Best Practices

### DO ✅

1. Write tests for new features
2. Use descriptive test names
3. Test edge cases and error conditions
4. Keep tests isolated and independent
5. Mock external dependencies
6. Use fixtures for common setup
7. Run tests before committing

### DON'T ❌

1. Skip writing tests for "simple" code
2. Use magic numbers without explanation
3. Test implementation details
4. Create interdependent tests
5. Commit failing tests
6. Use sleep() for timing (use mocks)
7. Test private methods directly

## Troubleshooting

### Tests Hanging

- Check for unmocked external calls
- Use `pytest --timeout=30` to detect hangs

### Flaky Tests

- Ensure tests are isolated
- Mock time-dependent operations
- Use deterministic test data

### Import Errors

```bash
# Ensure package is installed in development mode
uv sync

# Verify Python path
uv run python -c "import lift_sys; print(lift_sys.__file__)"
```

### Coverage Not Working

```bash
# Ensure pytest-cov is installed
uv add --dev pytest-cov

# Check pytest config in pyproject.toml
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Textual Testing](https://textual.textualize.io/guide/testing/)
- [Playwright Python](https://playwright.dev/python/)

## Contributing

When adding new tests:

1. Follow the existing structure
2. Add appropriate markers (@pytest.mark.unit, etc.)
3. Update this README if adding new test categories
4. Ensure all tests pass before submitting PR
5. Aim for >80% coverage on new code

---

**Last Updated**: 2025-10-10
**Test Suite Version**: 1.0.0
**Total Tests**: 100+
