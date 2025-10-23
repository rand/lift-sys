# Mock Inventory - Detailed Breakdown

**Date**: 2025-10-22
**Purpose**: E2E Validation Phase 1 - Catalog all mocked/stubbed components
**Status**: Complete

---

## Executive Summary

**Total Mocking**: 1246 occurrences across 50 files
**Test Files with Mocking**: 43 files
**Mock Import/Decorator Lines**: 71

### Breakdown by Category

| Category | Occurrences | Files | Replacement Strategy |
|----------|-------------|-------|---------------------|
| Provider Mocks | ~400 | 11 files | Add real tests + ResponseRecorder for CI |
| DSPy Signature Mocks | ~100 | 9 files | Keep for unit, add integration tests |
| Database Mocks (Supabase) | ~150 | 15 files | Keep for unit, use real DB for integration |
| GitHub Client Stubs | ~50 | 1 file | Keep stub (external dependency) |
| Response Recorders | ~100 | 4 files | Keep (CI caching mechanism) |
| File/Session Mocks | ~200 | 12 files | Keep for unit tests |
| Miscellaneous | ~246 | 8 files | Evaluate case-by-case |

---

## Category 1: Provider Mocks

**Purpose**: Mock LLM providers (ModalProvider, AnthropicProvider, etc.) to avoid real API calls during testing

**Occurrences**: ~400 across 11 files

### Files Using MockProvider

1. `tests/unit/dspy_signatures/test_provider_adapter.py` - 99 occurrences
2. `tests/unit/test_typescript_generator.py` - 19 occurrences
3. `tests/robustness/test_real_ir_generation.py` - 10 occurrences
4. `tests/integration/test_xgrammar_translator_with_constraints.py` - 30 occurrences
5. `tests/integration/test_xgrammar_code_generator.py` - 17 occurrences
6. `tests/integration/test_typescript_e2e.py` - 8 occurrences
7. `tests/integration/test_typescript_quality.py` - 10 occurrences
8. `tests/integration/test_xgrammar_translator.py` - 9 occurrences
9. `tests/integration/test_xgrammar_generator_with_constraints.py` - 41 occurrences
10. `tests/integration/test_semantic_generator_lsp.py` - 10 occurrences
11. `tests/e2e/conftest.py` - 7 occurrences

### MockProvider Implementation

**File**: `lift_sys/providers/mock.py`
**Lines**: 100+ lines
**Methods**:
- `set_response(response: str)` - Set single response
- `set_responses(responses: list[str])` - Set sequential responses
- `set_structured_response(response: dict)` - Set structured response
- `generate_text()` - Returns pre-configured text
- `generate_structured()` - Returns pre-configured dict
- `generate_stream()` - Returns mock stream

**Usage Pattern**:
```python
from lift_sys.providers.mock import MockProvider

provider = MockProvider()
provider.set_structured_response({
    "intent": {"summary": "Add two numbers"},
    "signature": {"name": "add", "parameters": [...]}
})

# Now all generate calls return this response
result = await provider.generate_structured(prompt, schema)
```

### Replacement Strategy

**Unit Tests**: Keep MockProvider
- Fast, isolated, deterministic
- No external dependencies
- Good for testing error handling, edge cases

**Integration Tests**: Add real ModalProvider tests
- New files: `tests/integration/test_modal_provider_real.py`
- Mark with `@pytest.mark.real_modal`
- Use ResponseRecorder for CI caching (see Category 5)

**Action Items**:
- [ ] Create `tests/integration/test_modal_provider_real.py`
- [ ] Add `@pytest.mark.real_modal` marker to pytest.ini
- [ ] Run with `RECORD_FIXTURES=true` to create fixture cache
- [ ] Validate cached responses work offline

**Files to Keep Mocked**: All unit tests
**Files to Add Real Tests**: All integration tests currently using MockProvider

---

## Category 2: DSPy Signature Mocks

**Purpose**: Mock DSPy modules (Predict, ChainOfThought, ReAct) and node interfaces to test architecture without real LLM calls

**Occurrences**: ~100 across 9 files

### Files with DSPy Mocking

1. `tests/unit/dspy_signatures/test_caching.py` - 33 occurrences
2. `tests/unit/dspy_signatures/test_provider_adapter.py` - 99 occurrences
3. `tests/unit/dspy_signatures/test_state_persistence.py` - 62 occurrences
4. `tests/unit/dspy_signatures/test_error_recovery.py` - 22 occurrences
5. `tests/unit/dspy_signatures/test_execution_history.py` - 72 occurrences
6. `tests/unit/dspy_signatures/test_parallel_executor.py` - 1 occurrence
7. `tests/unit/dspy_signatures/test_node_interface.py` - 14 occurrences
8. `tests/unit/dspy_signatures/test_trace_visualization.py` - 100 occurrences
9. `tests/unit/dspy_signatures/test_concurrency_model.py` - 8 occurrences

### Mock Patterns

**Pattern 1: Mock DSPy Modules**
```python
from unittest.mock import Mock
import dspy

# Mock Predict module
mock_predict = Mock(spec=dspy.Predict)
mock_predict.return_value = dspy.Prediction(output="mocked result")
```

**Pattern 2: Mock Node Execution**
```python
# Mock node.run()
mock_node = Mock(spec=BaseNode)
mock_node.run.return_value = End()  # Terminal node
```

**Pattern 3: Mock Provider Calls**
```python
# Mock provider.generate_structured()
mock_provider = Mock()
mock_provider.generate_structured.return_value = {"mocked": "data"}
```

### Replacement Strategy

**Unit Tests**: Keep mocks
- Holes H1-H19 implementations are **interfaces**, not end-to-end workflows
- Unit tests validate interface contracts, not real LLM behavior
- Mocking is appropriate for unit testing

**Integration Tests**: Add real DSPy + Modal tests
- New files: `tests/integration/test_h{N}_real.py` for each hole
- Test critical path (H6→H1→H10→H8→H17) with real Modal calls
- Validate actual DSPy modules work with ProviderAdapter

**Action Items**:
- [ ] Create `tests/integration/test_h6_real.py` (NodeSignatureInterface)
- [ ] Create `tests/integration/test_h1_real.py` (ProviderAdapter)
- [ ] Create `tests/integration/test_critical_path_e2e.py`
- [ ] Validate holes work with real infrastructure

**Files to Keep Mocked**: All unit tests in `tests/unit/dspy_signatures/`
**Files to Add Real Tests**: New integration test files

---

## Category 3: Database Mocks (Supabase)

**Purpose**: Mock Supabase database operations to test persistence logic without real DB

**Occurrences**: ~150 across 15 files

### Files with Database Mocking

**Supabase-specific tests**:
1. `tests/spec_sessions/test_supabase_store.py` - 3 occurrences (uses real DB)
2. `tests/integration/test_session_import.py` - 2 occurrences
3. `tests/unit/dspy_signatures/test_state_persistence.py` - 62 occurrences
4. `tests/unit/dspy_signatures/test_execution_history.py` - 72 occurrences

**Other DB/storage mocking**:
- Session storage mocks in various integration tests
- In-memory storage used as default (no mock needed)

### Mock Patterns

**Pattern 1: Mock Supabase Client**
```python
from unittest.mock import Mock, AsyncMock

mock_supabase = Mock()
mock_supabase.table.return_value.insert.return_value.execute = AsyncMock(
    return_value={"data": [{"id": 1}], "error": None}
)
```

**Pattern 2: Mock Database Queries**
```python
# Mock select query
mock_supabase.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
    return_value={"data": [{"session_id": "test-123"}], "error": None}
)
```

**Pattern 3: Use InMemorySessionStore**
```python
from lift_sys.storage import InMemorySessionStore

# No mock needed - real in-memory implementation
store = InMemorySessionStore()
await store.create_session(user_id="test", initial_ir=ir)
```

### Replacement Strategy

**Unit Tests**: Keep mocks OR use InMemorySessionStore
- Fast, isolated, no external dependencies
- InMemorySessionStore is better than mocking (real implementation, no DB)

**Integration Tests**: Use real Supabase test instance
- Already have: `tests/spec_sessions/test_supabase_store.py` uses real DB
- Use test database (not production)
- Use transaction rollback for test isolation
- Clean up test data after runs

**Action Items**:
- [ ] Prefer InMemorySessionStore over mocks in unit tests
- [ ] Expand `test_supabase_store.py` to cover H2 (StatePersistence) and H11 (ExecutionHistorySchema)
- [ ] Add real Supabase tests for graph state persistence
- [ ] Document test database setup in TESTING.md

**Files to Keep Mocked**: Unit tests testing error handling, edge cases
**Files to Use InMemoryStore**: Unit tests testing normal flow
**Files to Use Real DB**: Integration tests in `tests/integration/`, `tests/spec_sessions/`

---

## Category 4: GitHub Client Stubs

**Purpose**: Stub GitHub API client to avoid real GitHub API calls

**Occurrences**: ~50 in 1 file

### Files with GitHub Stubs

1. `tests/conftest.py` - _StubGitHubClient class

### Stub Implementation

**File**: `tests/conftest.py`
**Lines**: 40-86
**Class**: `_StubGitHubClient`

**Methods**:
- `list_repositories(user_id)` - Returns stub repository list
- `ensure_repository(user_id, identifier)` - Creates temp git repository

**Usage**:
```python
# In conftest.py
@pytest.fixture
def github_client():
    return _StubGitHubClient()

# In tests
async def test_something(github_client):
    repos = await github_client.list_repositories("user-123")
    # Returns stub data
```

### Replacement Strategy

**Keep Stub**: This is correct
- GitHub API is external, rate-limited, requires auth
- Stubbing is appropriate for testing lift-sys logic
- Real GitHub tests would be slow and brittle

**Improvements**:
- Add more realistic stub data (multiple repos, branches, etc.)
- Add error simulation (rate limiting, auth failures)

**Action Items**:
- [ ] None - stub is appropriate

**Files to Keep Stubbed**: All files using `_StubGitHubClient`

---

## Category 5: Response Recorders (Caching)

**Purpose**: Record real Modal API responses for CI caching - first run hits API, subsequent runs use cache

**Occurrences**: ~100 across 4 files

### Files with ResponseRecorder

1. `tests/conftest.py` - Fixture definitions
2. `tests/integration/test_response_recording_example.py` - Usage examples
3. `tests/fixtures/response_recorder.py` - Implementation
4. `tests/fixtures/__init__.py` - Exports

### ResponseRecorder Implementation

**File**: `tests/fixtures/response_recorder.py`
**Purpose**: Smart caching for expensive API calls

**Usage Pattern**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_modal_generation(modal_recorder):
    """First run: hits Modal (slow). Subsequent: uses cache (fast)."""

    result = await modal_recorder.get_or_record(
        key="test_simple_function",
        generator_fn=lambda: provider.generate_structured(prompt, schema),
        metadata={"test": "modal_generation"}
    )

    # Validate result
    assert result["intent"]["summary"] is not None
```

**Modes**:
- `RECORD_FIXTURES=true` - Hit real API, save responses
- Default - Use cached responses (fast, offline)

**Fixture Files**:
- `tests/fixtures/modal_responses.json` - Cached Modal responses
- `tests/fixtures/ir_responses.json` - Cached IR responses

### Replacement Strategy

**Keep and Expand**: This is the RIGHT pattern
- Allows real Modal testing on first run
- Fast CI runs using cached responses
- Periodic refresh (weekly) to update fixtures

**Action Items**:
- [ ] Use ResponseRecorder in ALL new integration tests
- [ ] Run `RECORD_FIXTURES=true pytest -m real_modal` to create initial cache
- [ ] Commit fixture files to git (enables offline CI)
- [ ] Add CI job to periodically refresh fixtures

**Files to Keep**: All ResponseRecorder files
**Files to Expand**: Add recorder to all new integration tests

---

## Category 6: File/Session Mocks

**Purpose**: Mock file system operations, session management, temporary directories

**Occurrences**: ~200 across 12 files

### Common Patterns

**Pattern 1: Temporary Directories**
```python
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    temp_path = Path(tmpdir)
    # Use temp_path for testing
```

**Pattern 2: Mock File Operations**
```python
from unittest.mock import mock_open, patch

mock_file = mock_open(read_data="file contents")
with patch("builtins.open", mock_file):
    # Test code that reads files
```

**Pattern 3: Mock Path.exists()**
```python
from unittest.mock import patch

with patch("pathlib.Path.exists", return_value=True):
    # Test code that checks file existence
```

### Files with File/Session Mocking

- `tests/integration/test_tui_session_management.py` - 32 occurrences
- `tests/integration/test_cli_session_commands.py` - 1 occurrence
- `tests/integration/test_multifile_analysis.py` - 40 occurrences
- `tests/unit/test_tui_session_methods.py` - 12 occurrences
- `tests/unit/test_cli_commands.py` - 72 occurrences
- Various other test files

### Replacement Strategy

**Keep Mocks**: Appropriate for unit tests
- Fast, isolated, deterministic
- Real file operations would pollute test environment

**Use Real Files in Tmpdir**: Better for integration tests
```python
# Instead of mocking, use real temp files
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.py"
    test_file.write_text("def hello(): pass")
    # Now test with real file
```

**Action Items**:
- [ ] Review file mocking in integration tests
- [ ] Prefer real tmpdir files over mocks where possible
- [ ] Keep mocks in unit tests

**Files to Keep Mocked**: Unit tests
**Files to Consider Real Files**: Integration tests

---

## Category 7: Miscellaneous Mocks

**Purpose**: Various other mocking (CLI, TUI, orchestrator, etc.)

**Occurrences**: ~246 across 8 files

### Subcategories

**CLI/TUI Mocking**:
- `tests/e2e/test_tui.py` - 2 occurrences
- `tests/e2e/test_web_ui.py` - 3 occurrences
- `tests/unit/test_cli_commands.py` - 72 occurrences

**Orchestrator Mocking**:
- `tests/test_orchestrator/test_task_routing.py` - 6 occurrences
- `tests/robustness/test_e2e_robustness.py` - 3 occurrences

**Other**:
- `tests/test_infrastructure/test_iac.py` - 4 occurrences
- `tests/reverse_mode/test_lifter.py` - 8 occurrences
- Various others

### Replacement Strategy

**Evaluate Case-by-Case**:
- CLI/TUI: Keep mocks (testing user interaction)
- Orchestrator: May need real tests if critical path
- Infrastructure: Keep mocks (external services)

**Action Items**:
- [ ] Review orchestrator tests - may need real validation
- [ ] Keep CLI/TUI mocks
- [ ] Keep infrastructure mocks

---

## Summary and Priorities

### Critical Path (Replace with Real Tests)

**High Priority**:
1. ✅ **Provider Mocks** → Add real ModalProvider tests (Phase 2)
2. ✅ **DSPy Signature Mocks** → Add H1-H19 integration tests (Phase 3)
3. ⚠️ **Database Mocks** → Expand real Supabase tests (Phase 2-3)

**Medium Priority**:
4. ⚠️ **Response Recorders** → Expand usage in new tests (Ongoing)
5. ⚠️ **File/Session Mocks** → Prefer real tmpdir files (Phase 3-4)

**Low Priority**:
6. ✓ **GitHub Stubs** → Keep as-is (correct pattern)
7. ✓ **CLI/TUI Mocks** → Keep as-is (appropriate)
8. ✓ **Misc Mocks** → Evaluate case-by-case

### Action Plan by Phase

**Phase 1** (Current):
- [x] Complete mock inventory
- [ ] Document findings

**Phase 2** (Week 1, Days 3-5):
- [ ] Add `test_modal_provider_real.py`
- [ ] Add `test_provider_adapter_real.py`
- [ ] Record initial ResponseRecorder fixtures
- [ ] Expand Supabase integration tests

**Phase 3** (Week 2, Days 1-3):
- [ ] Add H6, H1, H10, H8, H17 real tests
- [ ] Test critical path end-to-end
- [ ] Validate all 19 holes against real infrastructure

**Phase 4** (Week 2, Days 4-5):
- [ ] Test full NLP→IR→Code pipeline
- [ ] Robustness tests with real Modal
- [ ] Fix any discovered gaps

---

## Appendix: Grep Commands Used

```bash
# Count files with mocking
grep -r "Mock\|mock" tests --include="*.py" -l | wc -l
# Result: 43 files

# Count mock import/decorator lines
grep -r "from unittest.mock import\|@patch\|@mock" tests --include="*.py" -c
# Result: 71 lines

# Find MockProvider usage
find tests -name "*.py" -exec grep -l "MockProvider" {} \;

# Find ResponseRecorder usage
find tests -name "*.py" -exec grep -l "ResponseRecorder\|modal_recorder" {} \;

# Find GitHub stub usage
find tests -name "*.py" -exec grep -l "_StubGitHubClient" {} \;

# Count mocks per file
grep -c "Mock\|patch\|monkeypatch" tests/unit/dspy_signatures/*.py
```

---

**Status**: Complete
**Next**: Configure Modal endpoint (✅ Done) → Run baseline benchmarks
**Owner**: Architecture Team
