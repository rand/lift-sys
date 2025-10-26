"""Shared pytest fixtures for the lift-sys test suite."""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Generator, Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest

os.environ.setdefault("LIFT_SYS_ENABLE_DEMO_USER_HEADER", "1")

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from git import Repo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import UTC, datetime

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.ir.parser import IRParser
from lift_sys.services.github_repository import RepositoryMetadata, RepositorySummary


class _StubGitHubClient:
    """Minimal GitHub client stub used during API tests."""

    def __init__(self) -> None:
        self._summary = RepositorySummary(
            identifier="octocat/example",
            owner="octocat",
            name="example",
            description="stub repo",
            default_branch="main",
            private=False,
        )

    async def list_repositories(self, user_id: str) -> list[RepositorySummary]:
        return [self._summary]

    async def ensure_repository(
        self,
        user_id: str,
        identifier: str,
        *,
        branch: str | None = None,
        force_refresh: bool = False,
    ) -> RepositoryMetadata:
        repo_dir = Path(tempfile.mkdtemp(prefix="lift_stub_repo_"))
        repo = Repo.init(repo_dir)
        # Configure git user for commits
        with repo.config_writer() as writer:
            writer.set_value("user", "name", "Test User")
            writer.set_value("user", "email", "test@example.com")
        # Create initial commit on main branch
        (repo_dir / "README.md").write_text("stub repository", encoding="utf-8")
        repo.index.add(["README.md"])
        repo.index.commit("initial commit")
        # Rename default branch to 'main' to match GitHub's default
        repo.git.branch("-M", "main")
        return RepositoryMetadata(
            identifier=identifier,
            owner=self._summary.owner,
            name=self._summary.name,
            description=self._summary.description,
            default_branch=self._summary.default_branch,
            private=self._summary.private,
            clone_url="https://example.com/octocat/example.git",
            workspace_path=repo_dir,
            last_synced=datetime.now(UTC),
        )


# =============================================================================
# Directory and File Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_ir_text(fixtures_dir: Path) -> str:
    """Load valid IR sample text."""
    return (fixtures_dir / "sample_valid.ir").read_text(encoding="utf8")


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
def parser() -> IRParser:
    """Create IR parser instance."""
    return IRParser()


@pytest.fixture
def ir_parser() -> IRParser:
    """Create IR parser instance (alias)."""
    return IRParser()


@pytest.fixture
def parsed_simple_ir(ir_parser: IRParser, sample_simple_ir: str) -> IntermediateRepresentation:
    """Parse simple IR and return object."""
    return ir_parser.parse(sample_simple_ir)


@pytest.fixture
def parsed_with_holes_ir(
    ir_parser: IRParser, sample_with_holes_ir: str
) -> IntermediateRepresentation:
    """Parse IR with holes and return object."""
    return ir_parser.parse(sample_with_holes_ir)


# =============================================================================
# IR Model Fixtures
# =============================================================================


@pytest.fixture
def sample_ir() -> IntermediateRepresentation:
    """Create sample IR object programmatically."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Verify sample"),
        signature=SigClause(
            name="sample_module",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        ),
        effects=[EffectClause(description="No side effects")],
        assertions=[AssertClause(predicate="x > 0")],
        metadata=Metadata(origin="tests"),
    )


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
def api_client() -> Iterator[TestClient]:
    """Create FastAPI test client with proper state isolation.

    This fixture ensures:
    1. State is reset before the test
    2. Stub GitHub client is configured
    3. Demo auth is enabled
    4. State is reset after the test for the next test
    """
    from lift_sys.api.server import app, reset_state

    # Reset state before creating client
    reset_state()

    # Set up stub client and demo auth
    stub_client = _StubGitHubClient()
    app.state.github_repositories = stub_client
    app.state.allow_demo_user_header = True

    # Create test client with demo user header
    with TestClient(app) as client:
        client.headers.update({"x-demo-user": "pytest"})

        # Ensure app.state is set on the client's app instance too
        client.app.state.github_repositories = stub_client
        client.app.state.allow_demo_user_header = True

        yield client

    # Clean up after test - reset_state() now clears both STATE and app.state
    reset_state()


@pytest.fixture
def api_state():
    """Get API server state."""
    from lift_sys.api import server

    return server.STATE


@pytest.fixture
def configured_api_client(api_client: TestClient) -> TestClient:
    """Create configured API client with synthesizer config."""
    response = api_client.post(
        "/api/config",
        json={
            "model_endpoint": "http://localhost:8001",
            "temperature": 0.7,
            "provider_type": "vllm",
            "schema_uri": "memory://schema.json",
            "grammar_source": "start -> statement",
        },
    )
    assert response.status_code == 200
    return api_client


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_provider():
    """
    Create mock provider for testing code generation without real LLM calls.

    This mock provider supports structured output generation and can be
    configured to return specific responses for testing.
    """
    from typing import Any

    from lift_sys.providers.base import BaseProvider, ProviderCapabilities

    class MockProvider(BaseProvider):
        """Mock provider for testing."""

        def __init__(self) -> None:
            super().__init__(
                name="mock",
                capabilities=ProviderCapabilities(
                    streaming=False,
                    structured_output=True,
                    reasoning=True,
                ),
            )
            self._initialized = True
            self._response: str | None = None

        def set_generate_response(self, response: str) -> None:
            """Set the response to return from generate_structured."""
            self._response = response

        async def initialize(self, credentials: dict) -> None:
            self._initialized = True

        async def generate_text(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            **kwargs: Any,
        ) -> str:
            if self._response:
                return self._response
            return '{"implementation": "return 0;", "imports": [], "helper_functions": []}'

        async def generate_stream(self, prompt: str, **kwargs: Any):
            raise NotImplementedError("Streaming not implemented in mock")

        async def generate_structured(
            self,
            prompt: str,
            schema: dict,
            **kwargs: Any,
        ) -> dict:
            import json

            if self._response:
                return json.loads(self._response)
            return {
                "implementation": "return 0;",
                "imports": [],
                "helper_functions": [],
            }

        async def check_health(self) -> bool:
            return self._initialized

        @property
        def supports_streaming(self) -> bool:
            return False

        @property
        def supports_structured_output(self) -> bool:
            return True

    return MockProvider()


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for external tool calls."""
    mock = Mock()
    mock.return_value = Mock(returncode=0, stdout="", stderr="")
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
    from lift_sys.api.server import reset_state

    reset_state()
    yield
    reset_state()


# =============================================================================
# Response Recording Fixtures
# =============================================================================


@pytest.fixture
def modal_recorder(fixtures_dir: Path):
    """
    Provide response recorder for Modal API calls.

    Records API responses on first run (RECORD_FIXTURES=true),
    replays them on subsequent runs (default).

    This enables:
    - Integration tests to run in seconds instead of minutes
    - Deterministic test results
    - Offline testing
    - No Modal API rate limits during testing

    Usage:
        async def test_translation(modal_recorder):
            ir = await modal_recorder.get_or_record(
                key="find_index_prompt",
                generator_fn=lambda: translator.translate(prompt)
            )

    Environment Variables:
        RECORD_FIXTURES=true  - Record new responses
        RECORD_FIXTURES=false - Use cached responses (default)
    """
    from tests.fixtures import ResponseRecorder

    record_mode = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
    fixture_file = fixtures_dir / "modal_responses.json"

    recorder = ResponseRecorder(fixture_file=fixture_file, record_mode=record_mode, auto_save=True)

    yield recorder

    # Print stats at end of test
    if record_mode:
        stats = recorder.get_stats()
        print("\n📊 Response Recorder Stats:")
        print(f"  Cache hits: {stats['cache_hits']}")
        print(f"  Cache misses: {stats['cache_misses']}")
        print(f"  Total cached: {stats['num_cached_responses']}")


@pytest.fixture
def ir_recorder(fixtures_dir: Path):
    """
    Provide response recorder for IR generation.

    Similar to modal_recorder but with IR-specific serialization.
    Handles IntermediateRepresentation objects.

    Usage:
        async def test_ir_generation(ir_recorder):
            ir = await ir_recorder.get_or_record(
                key="test_prompt_1",
                generator_fn=lambda: translator.translate(prompt)
            )
    """
    from lift_sys.ir.models import IntermediateRepresentation
    from tests.fixtures import SerializableResponseRecorder

    record_mode = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
    fixture_file = fixtures_dir / "ir_responses.json"

    def serialize_ir(ir: IntermediateRepresentation) -> dict:
        """Convert IR to JSON-serializable dict."""
        return ir.to_dict()

    def deserialize_ir(data: dict) -> IntermediateRepresentation:
        """Convert dict back to IR object."""
        return IntermediateRepresentation.from_dict(data)

    recorder = SerializableResponseRecorder(
        fixture_file=fixture_file,
        record_mode=record_mode,
        auto_save=True,
        serializer=serialize_ir,
        deserializer=deserialize_ir,
    )

    yield recorder

    if record_mode:
        stats = recorder.get_stats()
        print("\n📊 IR Recorder Stats:")
        print(f"  Cache hits: {stats['cache_hits']}")
        print(f"  Cache misses: {stats['cache_misses']}")
        print(f"  Total cached IRs: {stats['num_cached_responses']}")


@pytest.fixture
def code_recorder(fixtures_dir: Path):
    """
    Provide response recorder for code generation.

    Similar to ir_recorder but for GeneratedCode objects.
    Handles code generation results from XGrammarCodeGenerator.

    Usage:
        async def test_code_generation(code_recorder):
            code = await code_recorder.get_or_record(
                key="test_sum_function",
                generator_fn=lambda: generator.generate(ir)
            )
    """
    from lift_sys.codegen.models import GeneratedCode
    from tests.fixtures import SerializableResponseRecorder

    record_mode = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
    fixture_file = fixtures_dir / "code_responses.json"

    def serialize_code(code: GeneratedCode) -> dict:
        """Convert GeneratedCode to JSON-serializable dict."""
        return {
            "source_code": code.source_code,
            "language": code.language,
            "ir_version": code.ir_version,
            "metadata": code.metadata,
            "warnings": code.warnings,
        }

    def deserialize_code(data: dict) -> GeneratedCode:
        """Convert dict back to GeneratedCode object."""
        return GeneratedCode(**data)

    recorder = SerializableResponseRecorder(
        fixture_file=fixture_file,
        record_mode=record_mode,
        auto_save=True,
        serializer=serialize_code,
        deserializer=deserialize_code,
    )

    yield recorder

    if record_mode:
        stats = recorder.get_stats()
        print("\n📊 Code Recorder Stats:")
        print(f"  Cache hits: {stats['cache_hits']}")
        print(f"  Cache misses: {stats['cache_misses']}")
        print(f"  Total cached codes: {stats['num_cached_responses']}")
