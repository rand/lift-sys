# Making Tests Actually Faster

**Problem**: Tests take 5-10 minutes
**Wrong Solution**: Skip slow tests ❌
**Right Solution**: Make tests faster ✅

---

## Root Causes of Slowness

### 1. Modal Endpoint Network Latency (30-60s per call)

**Current**:
```python
# Every test makes a real Modal call
provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
result = await provider.generate(...)  # 30-60s wait
```

**Problem**: Network round-trip + cold start + generation time

**Solutions**:

#### A. Local LLM for Testing
```python
# Use local Ollama/LLaMA for tests
TEST_PROVIDER = os.getenv("TEST_PROVIDER", "local")

if TEST_PROVIDER == "local":
    provider = LocalProvider()  # <1s response
else:
    provider = ModalProvider()  # 30s response
```

**Benefit**: 30x faster (1s vs 30s)

#### B. Cached Responses
```python
# Cache Modal responses for deterministic prompts
@lru_cache(maxsize=1000)
async def get_cached_generation(prompt: str, provider: str):
    # First call: hits Modal (slow)
    # Subsequent calls: returns cached (instant)
    return await provider.generate(prompt)
```

**Benefit**: First run slow, subsequent runs instant

#### C. Record/Replay Pattern
```python
# Record actual Modal responses, replay in tests
class RecordingProvider:
    def __init__(self, record_mode=False):
        self.record_mode = record_mode
        self.responses = load_responses("test_fixtures/responses.json")

    async def generate(self, prompt):
        if prompt in self.responses and not self.record_mode:
            return self.responses[prompt]  # Instant

        # Only call Modal if recording or new prompt
        result = await modal_provider.generate(prompt)

        if self.record_mode:
            self.responses[prompt] = result
            save_responses(self.responses)

        return result
```

**Benefit**: Deterministic, fast, can update fixtures when needed

---

### 2. Full E2E Pipeline for Every Test

**Current**:
```python
# Every test runs: prompt → IR → code → validate → execute
# Even when testing just one component
async def test_ast_repair():
    translator = XGrammarIRTranslator(provider)  # 30s
    ir = await translator.translate(prompt)      # 30s
    generator = XGrammarCodeGenerator(provider)  #
    code = await generator.generate(ir)          # 60s
    # Just to test AST repair!
```

**Problem**: Testing one thing requires running everything

**Solution**: Proper dependency injection and mocking

```python
# Unit test: just test AST repair logic
async def test_ast_repair_unit():
    engine = ASTRepairEngine()

    # Pre-generated buggy code (no Modal call)
    buggy_code = """
def find_index(lst, val):
    for i, v in enumerate(lst):
        if v == val:
            return i
        return -1  # BUG
"""

    # Test the repair logic directly (<1s)
    repaired = engine.repair(buggy_code, "find_index")

    assert "return -1" not in repaired.split('\n')[-2]  # Not in loop
```

**Benefit**: 100x faster (0.01s vs 60s)

---

### 3. Regenerating Same Responses

**Current**: Every test run regenerates the same responses

**Problem**: Wasting API calls and time on deterministic inputs

**Solution**: Pytest fixtures with session scope

```python
# conftest.py
@pytest.fixture(scope="session")
async def sample_irs():
    """Generate IRs once per test session, reuse everywhere."""
    provider = get_test_provider()
    translator = XGrammarIRTranslator(provider)

    # Generate all test IRs once
    irs = {}
    for test_case in TEST_CASES:
        irs[test_case.name] = await translator.translate(test_case.prompt)

    return irs

# In tests: reuse the cached IR
async def test_code_generation(sample_irs):
    ir = sample_irs["find_index"]  # Instant, no regeneration
    generator = XGrammarCodeGenerator(provider)
    code = await generator.generate(ir)
    ...
```

**Benefit**: Generate once, use many times

---

### 4. Sequential Execution

**Current**: Tests run one at a time

**Problem**: Not utilizing available parallelism

**Solution**: Actually parallelize (but do it right)

```python
# Tests are independent - run them in parallel
uv add --dev pytest-xdist

# Run with 4 workers
uv run pytest -n 4

# But be careful with:
# - Shared resources (databases, files)
# - Rate limits (Modal API)
# - Resource constraints (memory)
```

**With proper fixtures**:
```python
# Use worker-specific fixtures to avoid conflicts
@pytest.fixture(scope="session")
def worker_id(request):
    """Get unique worker ID for parallel tests."""
    if hasattr(request.config, 'workerinput'):
        return request.config.workerinput['workerid']
    return 'master'

@pytest.fixture
def temp_dir(worker_id, tmp_path_factory):
    """Worker-specific temp directory."""
    return tmp_path_factory.mktemp(f"worker_{worker_id}")
```

**Benefit**: 4x speedup (if tests are truly independent)

---

### 5. No Incremental Computation

**Current**: Regenerate everything from scratch

**Problem**: Not reusing intermediate results

**Solution**: Incremental testing with pytest-testmon

```bash
uv add --dev pytest-testmon

# Only run tests affected by code changes
uv run pytest --testmon
```

Or manual dependency tracking:
```python
# Cache expensive computations between test runs
IR_CACHE = Path(".pytest_cache/ir_cache.pkl")

@pytest.fixture(scope="session")
def ir_cache():
    if IR_CACHE.exists():
        return pickle.load(IR_CACHE.open("rb"))

    cache = {}
    # Generate and cache
    ...

    pickle.dump(cache, IR_CACHE.open("wb"))
    return cache
```

**Benefit**: Only recompute what changed

---

## Concrete Implementation Plan

### Step 1: Add Response Recording (2 hours)

```python
# tests/fixtures/modal_responses.py
import json
from pathlib import Path

class ResponseRecorder:
    """Record and replay Modal responses for testing."""

    def __init__(self, fixture_file: Path, record_mode: bool = False):
        self.fixture_file = fixture_file
        self.record_mode = record_mode
        self.responses = self._load_fixtures()

    def _load_fixtures(self):
        if self.fixture_file.exists():
            return json.loads(self.fixture_file.read_text())
        return {}

    async def get_or_record(self, key: str, generator_fn):
        """Get cached response or call generator and record."""
        if key in self.responses and not self.record_mode:
            return self.responses[key]

        # Call actual generator
        response = await generator_fn()

        if self.record_mode:
            self.responses[key] = response
            self._save_fixtures()

        return response

    def _save_fixtures(self):
        self.fixture_file.write_text(json.dumps(self.responses, indent=2))

# Usage in tests
@pytest.fixture
def modal_recorder():
    record_mode = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
    return ResponseRecorder(
        fixture_file=Path("tests/fixtures/modal_responses.json"),
        record_mode=record_mode
    )

async def test_with_recording(modal_recorder):
    # First run: calls Modal, records response
    # Subsequent runs: uses recorded response (instant)
    ir = await modal_recorder.get_or_record(
        key="find_index_prompt",
        generator_fn=lambda: translator.translate(FIND_INDEX_PROMPT)
    )
```

**Result**: First run slow, all subsequent runs instant

### Step 2: Create Test Fixtures (1 hour)

```python
# tests/conftest.py
import pytest
from pathlib import Path
import json

# Pre-generated test data (committed to repo)
FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def sample_irs():
    """Load pre-generated IRs for testing."""
    return json.loads((FIXTURES_DIR / "sample_irs.json").read_text())

@pytest.fixture(scope="session")
def sample_code():
    """Load pre-generated code for testing."""
    return json.loads((FIXTURES_DIR / "sample_code.json").read_text())

@pytest.fixture
def buggy_code_samples():
    """Pre-written buggy code for AST repair testing."""
    return {
        "loop_return": """
def find_index(lst, val):
    for i, v in enumerate(lst):
        if v == val:
            return i
        return -1  # BUG
""",
        "type_check": """
def get_type_name(value):
    return type(value).__name__.lower()  # BUG
""",
    }

# Generate fixtures once
# tests/generate_fixtures.py
async def generate_test_fixtures():
    """Generate and save test fixtures (run once)."""
    provider = ModalProvider(...)
    translator = XGrammarIRTranslator(provider)

    fixtures = {}
    for name, prompt in TEST_PROMPTS.items():
        ir = await translator.translate(prompt)
        fixtures[name] = ir.to_dict()

    (FIXTURES_DIR / "sample_irs.json").write_text(
        json.dumps(fixtures, indent=2)
    )

# Run once to generate, commit to repo
# Then tests use fixtures (instant)
```

**Result**: No Modal calls in most tests

### Step 3: Proper Unit Tests (2 hours)

```python
# tests/unit/test_ast_repair_unit.py
import pytest
from lift_sys.codegen.ast_repair import ASTRepairEngine

@pytest.mark.unit
class TestASTRepairUnit:
    """Pure unit tests with no external dependencies."""

    def test_loop_return_detection(self):
        """Test detection of returns in loop body."""
        engine = ASTRepairEngine()

        code = """
def find_index(lst, val):
    for i, v in enumerate(lst):
        if v == val:
            return i
        return -1
"""

        result = engine.repair(code, "find_index")

        # Verify repair was applied
        assert result is not None
        assert "return -1" in result

        # Verify it's after the loop (not indented)
        lines = result.split('\n')
        return_line = [l for l in lines if 'return -1' in l][0]
        assert return_line.startswith('    return -1')  # 4 spaces, not 8

    def test_no_repair_needed(self):
        """Test that correct code is not modified."""
        engine = ASTRepairEngine()

        correct_code = """
def find_index(lst, val):
    for i, v in enumerate(lst):
        if v == val:
            return i
    return -1
"""

        result = engine.repair(correct_code, "find_index")

        # No repair needed
        assert result is None

# Run time: <0.1s total for all unit tests
```

### Step 4: Cached Integration Tests (2 hours)

```python
# tests/integration/test_with_caching.py
import pytest
from functools import lru_cache

# Cache provider responses in memory during test session
@lru_cache(maxsize=100)
async def cached_translate(prompt: str, provider):
    """Cache IR generation results."""
    translator = XGrammarIRTranslator(provider)
    return await translator.translate(prompt)

@pytest.mark.integration
async def test_with_caching():
    """Integration test with caching."""
    # First call: hits Modal (slow)
    ir1 = await cached_translate("simple prompt", provider)

    # Second call: cached (instant)
    ir2 = await cached_translate("simple prompt", provider)

    assert ir1 == ir2  # Same result, but 30x faster

# Or use pytest-cache for persistence
@pytest.fixture
def ir_cache(request):
    """Persistent cache across test runs."""
    cache_key = f"ir_{request.node.name}"
    cached = request.config.cache.get(cache_key, None)

    if cached:
        return cached

    # Generate and cache
    ir = await generate_ir()
    request.config.cache.set(cache_key, ir)
    return ir
```

### Step 5: Local Test Provider (3 hours)

```python
# lift_sys/providers/local_test_provider.py
class LocalTestProvider:
    """Fast local provider for testing (no network calls)."""

    def __init__(self):
        # Use local Ollama or just mock responses
        self.mode = os.getenv("LOCAL_PROVIDER_MODE", "mock")

    async def generate(self, prompt: str, schema: dict) -> str:
        if self.mode == "mock":
            # Return deterministic mock based on prompt
            return self._mock_response(prompt, schema)
        else:
            # Use local Ollama (still fast, ~1-2s)
            return await self._ollama_generate(prompt, schema)

    def _mock_response(self, prompt: str, schema: dict) -> str:
        """Generate mock response matching schema."""
        # Simple heuristic based on prompt keywords
        if "find_index" in prompt.lower():
            return FIND_INDEX_MOCK_RESPONSE
        elif "get_type" in prompt.lower():
            return GET_TYPE_MOCK_RESPONSE
        else:
            return self._generate_from_schema(schema)

# In conftest.py
@pytest.fixture
def test_provider():
    """Get appropriate provider for testing."""
    mode = os.getenv("TEST_PROVIDER", "local")

    if mode == "local":
        return LocalTestProvider()  # Fast
    elif mode == "recorded":
        return RecordedProvider()   # Instant
    else:
        return ModalProvider()      # Slow but real
```

**Result**: Tests run in 1-2s instead of 30-60s

---

## Expected Improvements

### Before (Current)
```
Phase 2 Suite: 10 tests × 30-60s = 5-10 minutes
- Modal calls: 30-60s each
- No caching
- Sequential execution
- Full E2E every time
```

### After (Optimized)
```
Unit Tests: 20 tests × 0.01s = 0.2s
- Pure logic, no external deps
- Instant feedback

Integration Tests: 10 tests × 2s = 20s
- Cached responses or local provider
- Shared fixtures
- Fast feedback

E2E Tests: 5 tests × 30s = 150s (2.5 min)
- Only when needed
- Parallel execution (4 workers) → 40s
- Record/replay for CI
```

**Total**: 0.2s (unit) + 20s (integration) + 40s (E2E) = **60s total**

**Improvement**: **5x-10x faster** (60s vs 5-10 min)

---

## Implementation Priority

### Must Do (Phase 5 Prerequisites)

1. ✅ **Response Recording** (2 hours)
   - Record Modal responses
   - Replay in tests
   - Update fixtures when needed

2. ✅ **Test Fixtures** (1 hour)
   - Pre-generate sample IRs
   - Commit to repo
   - Use in tests

3. ✅ **Pure Unit Tests** (2 hours)
   - Test logic without external deps
   - Mock everything
   - <0.1s per test

### Should Do (Week 1)

4. **Cached Integration Tests** (2 hours)
   - Use pytest-cache
   - Share expensive setup
   - 10x faster integration tests

5. **Parallel Execution Setup** (1 hour)
   - Configure pytest-xdist properly
   - Worker-specific fixtures
   - 4x speedup

### Nice to Have (Week 2)

6. **Local Test Provider** (3 hours)
   - Ollama integration
   - Mock responses
   - No network dependency

---

## Bottom Line

**Wrong approach**: Skip slow tests → Tests don't run → Bugs slip through
**Right approach**: Make tests fast → Tests run constantly → Catch bugs early

**Target**: 60s for full suite (vs. 5-10 min currently)
**Method**: Recording, caching, fixtures, local providers, parallelism
**Effort**: ~10 hours total
**Payoff**: 5-10x faster, runs on every change

Let's implement the "Must Do" items before Phase 5.
