"""Shared pytest fixtures for lift-sys test suite."""
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from git import Repo

from lift_sys.api.server import app, reset_state
from lift_sys.ir.parser import IRParser
from lift_sys.ir.models import (
    IntermediateRepresentation,
    IntentClause,
    SigClause,
    Parameter,
    AssertClause,
    EffectClause,
    Metadata,
)


# =============================================================================
# Directory and File Fixtures
# =============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_simple_ir(fixtures_dir: Path) -> str:
    """Load simple IR sample."""
    return (fixtures_dir / "sample_simple.ir").read_text()


@pytest.fixture
def sample_with_holes_ir(fixtures_dir: Path) -> str:
    """Load IR sample with typed holes."""
    return (fixtures_dir / "sample_with_holes.ir").read_text()


@pytest.fixture
def sample_complex_ir(fixtures_dir: Path) -> str:
    """Load complex IR sample."""
    return (fixtures_dir / "sample_complex.ir").read_text()


@pytest.fixture
def sample_invalid_ir(fixtures_dir: Path) -> str:
    """Load invalid IR sample."""
    return (fixtures_dir / "sample_invalid.ir").read_text()


@pytest.fixture
def sample_code(fixtures_dir: Path) -> str:
    """Load sample Python code."""
    return (fixtures_dir / "sample_code.py").read_text()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_repo(temp_dir: Path) -> Repo:
    """Create temporary git repository."""
    repo = Repo.init(temp_dir)
    # Configure git user
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    return repo


# =============================================================================
# Parser Fixtures
# =============================================================================


@pytest.fixture
def ir_parser() -> IRParser:
    """Create IR parser instance."""
    return IRParser()


@pytest.fixture
def parsed_simple_ir(ir_parser: IRParser, sample_simple_ir: str) -> IntermediateRepresentation:
    """Parse simple IR and return object."""
    return ir_parser.parse(sample_simple_ir)


@pytest.fixture
def parsed_with_holes_ir(ir_parser: IRParser, sample_with_holes_ir: str) -> IntermediateRepresentation:
    """Parse IR with holes and return object."""
    return ir_parser.parse(sample_with_holes_ir)


# =============================================================================
# IR Model Fixtures
# =============================================================================


@pytest.fixture
def simple_ir() -> IntermediateRepresentation:
    """Create simple IR object programmatically."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Add two numbers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[],
        assertions=[
            AssertClause(predicate="a >= 0"),
            AssertClause(predicate="b >= 0"),
        ],
        metadata=Metadata(origin="test"),
    )


@pytest.fixture
def complex_ir() -> IntermediateRepresentation:
    """Create complex IR object with effects and multiple assertions."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Search for element in sorted array"),
        signature=SigClause(
            name="binary_search",
            parameters=[
                Parameter(name="arr", type_hint="list"),
                Parameter(name="target", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[
            EffectClause(description="reads array elements"),
            EffectClause(description="may return -1 if not found"),
        ],
        assertions=[
            AssertClause(predicate="len(arr) >= 0"),
            AssertClause(predicate="result >= -1"),
        ],
        metadata=Metadata(origin="test", language="python"),
    )


# =============================================================================
# API Fixtures
# =============================================================================


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client."""
    reset_state()
    with TestClient(app) as client:
        yield client
    reset_state()


@pytest.fixture
def configured_api_client(api_client: TestClient) -> TestClient:
    """Create configured API client with synthesizer config."""
    response = api_client.post(
        "/config",
        json={"model_endpoint": "http://localhost:8001", "temperature": 0.7}
    )
    assert response.status_code == 200
    return api_client


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for external tool calls."""
    mock = Mock()
    mock.return_value = Mock(
        returncode=0,
        stdout="",
        stderr=""
    )
    monkeypatch.setattr("subprocess.run", mock)
    return mock


@pytest.fixture
def mock_codeql_output() -> str:
    """Mock CodeQL SARIF output."""
    return """
    {
      "runs": [{
        "results": [{
          "ruleId": "py/sql-injection",
          "level": "error",
          "message": {"text": "SQL injection vulnerability"},
          "locations": [{
            "physicalLocation": {
              "artifactLocation": {"uri": "test.py"},
              "region": {"startLine": 10}
            }
          }]
        }]
      }]
    }
    """


@pytest.fixture
def mock_daikon_output() -> str:
    """Mock Daikon invariant output."""
    return """
    factorial(int n) -> int
    n >= 0
    result > 0
    result >= n
    """


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_test_state():
    """Reset application state before each test."""
    reset_state()
    yield
    reset_state()


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
