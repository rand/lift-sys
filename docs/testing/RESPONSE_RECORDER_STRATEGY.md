# ResponseRecorder Caching Strategy for Phase 2.2

**Date**: 2025-10-22
**Status**: Production-Ready Implementation Available
**Purpose**: Fast, offline-capable CI/CD tests using cached Modal responses

---

## Executive Summary

**Problem**: Modal cold starts take 5-7 minutes, making CI/CD tests impractically slow.

**Solution**: ResponseRecorder system that:
- Records real Modal API responses on first run
- Replays cached responses on subsequent runs (30-60x faster)
- Enables offline testing and fast CI/CD pipelines
- Maintains deterministic test results

**Impact**: Integration tests run in **<10 seconds** instead of **5-10 minutes**

---

## Table of Contents

1. [Current Implementation](#current-implementation)
2. [Architecture](#architecture)
3. [Usage Guide](#usage-guide)
4. [Phase 2.2 Integration Plan](#phase-22-integration-plan)
5. [Best Practices](#best-practices)
6. [Performance Characteristics](#performance-characteristics)
7. [Troubleshooting](#troubleshooting)
8. [Migration Examples](#migration-examples)

---

## Current Implementation

### Status: ✅ Production-Ready

The ResponseRecorder system is **already implemented** and **battle-tested** in the codebase.

**Implementation Files**:
- **Core**: `/Users/rand/src/lift-sys/tests/fixtures/response_recorder.py` (251 lines)
- **Pytest Integration**: `/Users/rand/src/lift-sys/tests/conftest.py` (fixtures at lines 382-470)
- **Examples**: `/Users/rand/src/lift-sys/tests/integration/test_response_recording_example.py`
- **Documentation**:
  - `/Users/rand/src/lift-sys/docs/RESPONSE_RECORDING_GUIDE.md` (588 lines)
  - `/Users/rand/src/lift-sys/docs/archive/RESPONSE_RECORDING_IMPLEMENTATION_SUMMARY.md`

**Implementation Date**: October 15, 2025
**Validation**: 3 example tests passing, used in existing integration tests

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                   ResponseRecorder System                    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│ResponseRecord│    │SerializableRespns│    │ Pytest       │
│er (Generic)  │    │eRecorder (IR)    │    │ Fixtures     │
└──────────────┘    └──────────────────┘    └──────────────┘
        │                     │                     │
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│modal_        │    │ir_recorder       │    │Test Files    │
│responses.json│    │.json             │    │Using Fixtures│
└──────────────┘    └──────────────────┘    └──────────────┘
```

### Class Hierarchy

#### 1. ResponseRecorder (Base Class)

**File**: `tests/fixtures/response_recorder.py`

**Purpose**: Generic response caching for any API calls

**Key Features**:
- Key-based caching (auto-hashes long keys >100 chars)
- Record/replay modes controlled by `RECORD_FIXTURES` env var
- Auto-save on record (configurable)
- Statistics tracking (cache hits, misses, hit rate)
- Metadata support for documentation

**Core Methods**:
```python
class ResponseRecorder:
    def __init__(
        self,
        fixture_file: Path,
        record_mode: bool = False,
        auto_save: bool = True
    ):
        """Initialize recorder with fixture file and mode."""

    async def get_or_record(
        self,
        key: str,
        generator_fn: Callable[[], Any],
        metadata: dict[str, Any] | None = None
    ) -> Any:
        """
        Get cached response OR call generator and record.

        Args:
            key: Unique identifier for this response
            generator_fn: Async/sync function to call if not cached
            metadata: Optional metadata to store

        Returns:
            Response (from cache or generator)
        """

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics (hits, misses, hit rate)."""

    def clear_cache(self) -> None:
        """Clear all cached responses."""
```

#### 2. SerializableResponseRecorder (Subclass)

**Purpose**: Enhanced recorder with custom serialization for complex objects (e.g., IR)

**Additional Features**:
- Custom serializer function (object → JSON)
- Custom deserializer function (JSON → object)
- Automatic serialization on record
- Automatic deserialization on replay

**Usage**:
```python
class SerializableResponseRecorder(ResponseRecorder):
    def __init__(
        self,
        fixture_file: Path,
        record_mode: bool = False,
        auto_save: bool = True,
        serializer: Callable[[Any], Any] | None = None,
        deserializer: Callable[[Any], Any] | None = None,
    ):
        """Initialize with custom serialization."""
```

### Pytest Fixtures

#### 1. `modal_recorder` (Generic)

**File**: `tests/conftest.py` (lines 382-423)

**Purpose**: Record/replay any Modal API responses

**Fixture File**: `tests/fixtures/modal_responses.json`

**Usage Example**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_modal_api(modal_recorder):
    result = await modal_recorder.get_or_record(
        key="test_unique_key",
        generator_fn=lambda: some_modal_call(),
        metadata={"test": "modal_api", "version": "1.0"}
    )

    assert result is not None
```

#### 2. `ir_recorder` (IR-Specific)

**File**: `tests/conftest.py` (lines 425-470)

**Purpose**: Record/replay IntermediateRepresentation objects with serialization

**Fixture File**: `tests/fixtures/ir_responses.json`

**Serialization**:
- **Record**: `IR.to_dict()` → JSON
- **Replay**: `IntermediateRepresentation.from_dict(data)` → IR object

**Usage Example**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ir_generation(ir_recorder):
    ir = await ir_recorder.get_or_record(
        key="test_find_index",
        generator_fn=lambda: translator.translate(prompt),
        metadata={"prompt": prompt[:50]}
    )

    # ir is a proper IntermediateRepresentation object
    assert ir.intent.summary is not None
    assert ir.signature.name == "find_index"
```

---

## Usage Guide

### Quick Start (3 Steps)

#### Step 1: Add Fixture to Test

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_feature(ir_recorder):  # ← Add fixture parameter
    """Test with response recording."""

    # Your existing code
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)
    prompt = "Write a function to find an element in a list"

    # Wrap expensive call with recorder
    ir = await ir_recorder.get_or_record(
        key="test_my_feature_find_index",  # Unique key
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "my_feature", "prompt": prompt[:50]}
    )

    # Your existing assertions
    assert ir.signature.name == "find_index"
```

#### Step 2: Record Responses (First Run)

```bash
# Record responses from real Modal API (slow, 30-60s per call)
RECORD_FIXTURES=true uv run pytest tests/integration/test_my_feature.py -v

# This will:
# - Call Modal API (slow)
# - Save response to tests/fixtures/ir_responses.json
# - Run assertions
```

#### Step 3: Use Cached Responses (Subsequent Runs)

```bash
# Use cached responses (fast, <1s per call)
uv run pytest tests/integration/test_my_feature.py -v

# This will:
# - Load response from tests/fixtures/ir_responses.json
# - Return cached response instantly
# - No Modal API calls
```

### Environment Variables

| Variable | Values | Default | Purpose |
|----------|--------|---------|---------|
| `RECORD_FIXTURES` | `true`/`false` | `false` | Record new responses (overwrites cache) |

**Recording Mode** (`RECORD_FIXTURES=true`):
- Calls actual Modal API
- Saves responses to fixture files
- Overwrites existing cached responses for same keys
- Slow but updates fixtures

**Replay Mode** (Default, `RECORD_FIXTURES=false` or unset):
- Loads responses from fixture files
- Returns cached responses instantly
- Never calls Modal API
- Fast and deterministic

---

## Phase 2.2 Integration Plan

### Context: Phase 2.2 Optimization Testing

**Goal**: Validate DSPy optimization improvements (MIPROv2, COPRO) against real Modal infrastructure

**Challenge**: Modal cold starts (5-7 min) make iterative testing impractical

**Solution**: Use ResponseRecorder for fast iteration, periodic real validation

### Implementation Strategy

#### 1. Initial Recording (One-Time Setup)

**When**: Beginning of Phase 2.2
**Duration**: ~30-60 minutes (one-time cost)
**Purpose**: Capture baseline responses for optimization testing

**Steps**:
```bash
# 1. Ensure Modal endpoint is running
modal app list
# Should show: lift-sys (running)

# 2. Record baseline responses for all optimization test cases
RECORD_FIXTURES=true uv run pytest tests/integration/optimization/ -v

# 3. Verify fixture files were created
ls -lh tests/fixtures/ir_responses.json
ls -lh tests/fixtures/modal_responses.json

# 4. Commit fixture files to git
git add tests/fixtures/*.json
git commit -m "Add ResponseRecorder fixtures for Phase 2.2 optimization tests"
git push
```

**Expected Fixture Files**:
- `tests/fixtures/ir_responses.json` - IR generation responses
- `tests/fixtures/modal_responses.json` - Other Modal API responses

**Size Estimate**: ~100-500 KB per fixture file (depends on number of test cases)

#### 2. Daily Development Workflow

**Typical Day**: Make optimization change → Test → Iterate

**Without ResponseRecorder** (Old Way):
```bash
# Make code change
vim lift_sys/optimization/mipro.py

# Run tests (SLOW - 5-10 minutes)
uv run pytest tests/integration/optimization/ -v
# Wait 5-10 minutes...

# Fix issues
vim lift_sys/optimization/mipro.py

# Run tests again (SLOW - 5-10 minutes)
uv run pytest tests/integration/optimization/ -v
# Wait 5-10 minutes...

# Total: 10-20 minutes per iteration
```

**With ResponseRecorder** (New Way):
```bash
# Make code change
vim lift_sys/optimization/mipro.py

# Run tests (FAST - <10 seconds using cache)
uv run pytest tests/integration/optimization/ -v
# Results in <10 seconds!

# Fix issues
vim lift_sys/optimization/mipro.py

# Run tests again (FAST - <10 seconds)
uv run pytest tests/integration/optimization/ -v
# Results in <10 seconds!

# Total: <1 minute per iteration
```

**Speedup**: **10-20x faster** iteration cycle

#### 3. Periodic Real Validation

**Frequency**: Weekly or after major changes
**Purpose**: Ensure cached responses still match real Modal behavior

**Steps**:
```bash
# 1. Re-record responses from real Modal API
RECORD_FIXTURES=true uv run pytest tests/integration/optimization/ -v

# 2. Check for differences (git diff)
git diff tests/fixtures/*.json

# 3. If responses changed significantly:
#    - Investigate why (Modal model updated? Prompts changed?)
#    - Update expectations in tests if needed
#    - Commit new fixtures

# 4. If responses unchanged:
#    - Great! Validation passed
#    - No commit needed
```

**When to Re-Record**:
- Weekly (scheduled validation)
- After changing prompts or DSPy signatures
- After Modal model updates
- After significant optimization algorithm changes
- Before important demos or releases

#### 4. CI/CD Integration

**Goal**: Fast, offline-capable CI pipeline using cached responses

**GitHub Actions Workflow**:
```yaml
# .github/workflows/test_optimization.yml
name: Optimization Tests

on:
  push:
    branches: [main, feature/*]
  pull_request:

jobs:
  test-optimization:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv sync

      - name: Run optimization tests (using cached responses)
        run: uv run pytest tests/integration/optimization/ -v
        # No RECORD_FIXTURES=true → uses cache
        # No Modal secrets needed
        # Runs offline in <10 seconds

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Benefits**:
- **No Modal secrets** in CI (uses cached responses)
- **No API costs** (no real Modal calls)
- **Fast CI runs** (<10 seconds vs 5-10 minutes)
- **Offline capable** (no network dependency)
- **Deterministic** (same responses every time)

**Weekly Validation Job** (Optional):
```yaml
# .github/workflows/validate_fixtures.yml
name: Validate Response Fixtures

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:      # Manual trigger

jobs:
  validate-fixtures:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: uv sync

      - name: Re-record fixtures from real Modal
        env:
          MODAL_API_KEY: ${{ secrets.MODAL_API_KEY }}
          RECORD_FIXTURES: true
        run: uv run pytest tests/integration/optimization/ -v

      - name: Check for fixture changes
        run: git diff --exit-code tests/fixtures/*.json
        # Fails if fixtures changed → investigate

      - name: Create issue if fixtures changed
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Response fixtures changed in weekly validation',
              body: 'Modal API responses have changed. Review and update fixtures.',
              labels: ['testing', 'validation']
            })
```

### Test File Organization

**Recommended Structure for Phase 2.2**:

```
tests/integration/optimization/
├── conftest.py                          # Shared fixtures (use ir_recorder)
├── test_mipro_optimizer.py              # MIPROv2 optimization tests
├── test_copro_optimizer.py              # COPRO optimization tests
├── test_baseline_comparison.py          # Before/after optimization
├── test_confidence_scores.py            # Confidence evaluation
└── test_optimization_e2e.py             # Full optimization pipeline

tests/fixtures/
├── ir_responses.json                    # Cached IR generation responses
├── modal_responses.json                 # Cached other Modal responses
└── optimization_baselines.json          # Baseline metrics for comparison
```

**Example Test File** (`test_mipro_optimizer.py`):
```python
"""Tests for MIPROv2 optimizer using ResponseRecorder."""

import pytest
from lift_sys.optimization.mipro import MIPROOptimizer
from lift_sys.providers.modal_provider import ModalProvider
from lift_sys.codegen.xgrammar_translator import XGrammarIRTranslator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mipro_improves_translation_quality(ir_recorder):
    """
    Test that MIPROv2 improves IR translation quality.

    First run: Calls real Modal API (slow, 30-60s)
    Subsequent runs: Uses cached responses (fast, <1s)
    """
    # Setup
    provider = ModalProvider(endpoint_url=MODAL_ENDPOINT)
    translator = XGrammarIRTranslator(provider)
    optimizer = MIPROOptimizer(provider)

    prompt = "Write a function to find an element in a list"

    # Baseline translation (before optimization)
    baseline_ir = await ir_recorder.get_or_record(
        key="mipro_baseline_find_index",
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "mipro_baseline", "prompt": prompt}
    )

    # Optimize translator
    optimized_translator = await optimizer.optimize(translator)

    # Optimized translation
    optimized_ir = await ir_recorder.get_or_record(
        key="mipro_optimized_find_index",
        generator_fn=lambda: optimized_translator.translate(prompt),
        metadata={"test": "mipro_optimized", "prompt": prompt}
    )

    # Assertions
    assert optimized_ir.confidence_score > baseline_ir.confidence_score
    assert optimized_ir.signature.name == "find_index"
    assert len(optimized_ir.effects) > 0  # More detailed effects

    # Log stats
    stats = ir_recorder.get_stats()
    print(f"\n📊 Cache stats: {stats['cache_hits']} hits, {stats['cache_misses']} misses")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mipro_optimization_time(ir_recorder):
    """Test that MIPRO optimization completes in reasonable time."""
    provider = ModalProvider(endpoint_url=MODAL_ENDPOINT)
    optimizer = MIPROOptimizer(provider)

    # Record optimization time
    import time
    start = time.time()

    result = await ir_recorder.get_or_record(
        key="mipro_optimization_time",
        generator_fn=lambda: optimizer.optimize_signatures(),
        metadata={"test": "optimization_time"}
    )

    duration = time.time() - start

    # First run (record): slow (30-60s)
    # Subsequent runs (replay): fast (<1s)
    if ir_recorder.record_mode:
        assert duration < 120  # Optimization should complete in 2 minutes
    else:
        assert duration < 5  # Cache replay should be <5s

    assert result is not None
```

---

## Best Practices

### 1. Key Naming Conventions

**Good Keys** (Descriptive, Unique):
```python
key="test_find_index_basic"
key="test_binary_search_with_edge_cases"
key="test_factorial_recursive_base_case"
key="mipro_baseline_find_index"
key="copro_optimized_sorting"
```

**Bad Keys** (Too Generic):
```python
key="test1"              # ❌ Not descriptive
key="ir"                 # ❌ Too generic
key="optimization"       # ❌ Ambiguous
```

**Long Keys** (Automatically Hashed):
```python
# Keys >100 chars are auto-hashed
key=f"translate_{entire_prompt}"  # ✅ OK - auto-hashed
key=f"optimize_{full_config_dict}"  # ✅ OK - auto-hashed
```

### 2. Metadata Usage

**Purpose**: Document cached responses for debugging and maintenance

**Good Metadata**:
```python
metadata={
    "test": "test_function_name",
    "prompt": prompt[:100],  # Truncate long strings
    "expected_function": "find_index",
    "version": "1.0",
    "date": "2025-10-22",
    "optimization_type": "mipro"
}
```

**Metadata is NOT used for caching** - only `key` determines cache lookup

### 3. Fixture File Management

**Commit Fixtures to Git**:
```bash
git add tests/fixtures/*.json
git commit -m "Add ResponseRecorder fixtures for optimization tests"
git push
```

**Why Commit Fixtures**:
- Team members can run tests offline
- CI can run tests without Modal secrets
- Deterministic test results across environments
- Faster onboarding (no need to record fixtures)

**When to Update Fixtures**:
```bash
# Re-record when:
# - Prompts change
# - DSPy signatures change
# - Modal model updates
# - Optimization algorithms change
# - Weekly validation (scheduled)

RECORD_FIXTURES=true uv run pytest tests/integration/optimization/ -v
git diff tests/fixtures/*.json  # Review changes
git add tests/fixtures/*.json
git commit -m "Update fixtures for new prompts"
```

### 4. Test Organization

**One Key Per Test Case**:
```python
# Each test case should have unique key
async def test_baseline(ir_recorder):
    ir = await ir_recorder.get_or_record(
        key="baseline_find_index",  # Unique
        generator_fn=...
    )

async def test_optimized(ir_recorder):
    ir = await ir_recorder.get_or_record(
        key="optimized_find_index",  # Different
        generator_fn=...
    )
```

**Share Common Setup**:
```python
# conftest.py
@pytest.fixture
async def baseline_ir(ir_recorder):
    """Shared baseline IR for multiple tests."""
    return await ir_recorder.get_or_record(
        key="shared_baseline_ir",
        generator_fn=lambda: translator.translate(BASELINE_PROMPT)
    )

# test_optimization.py
async def test_mipro(baseline_ir, ir_recorder):
    """Use shared baseline_ir fixture."""
    # baseline_ir already loaded
    optimized_ir = await ir_recorder.get_or_record(...)
    assert optimized_ir.confidence_score > baseline_ir.confidence_score
```

### 5. Statistics Tracking

**Monitor Cache Performance**:
```python
async def test_with_stats(modal_recorder):
    # Run test
    result = await modal_recorder.get_or_record(...)

    # Get statistics
    stats = modal_recorder.get_stats()
    print(f"\n📊 Response Recorder Stats:")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Cache misses: {stats['cache_misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.2%}")
    print(f"  Total cached: {stats['num_cached_responses']}")
```

**Expected Stats**:
- **First run** (recording): 100% cache misses
- **Subsequent runs** (replay): 100% cache hits
- **After fixture update**: Mix of hits and misses

---

## Performance Characteristics

### Timing Comparison

| Scenario | Without Recorder | With Recorder (First) | With Recorder (Cached) |
|----------|------------------|----------------------|----------------------|
| **Single IR Translation** | 30-60s | 30-60s (records) | <1s |
| **10 Integration Tests** | 5-10 minutes | 5-10 minutes (records) | <10 seconds |
| **Full Optimization Suite** | 30-60 minutes | 30-60 minutes (records) | <30 seconds |
| **CI/CD Pipeline** | 10-20 minutes | N/A (uses cache) | <1 minute |

**Speedup**: **30-60x faster** on cached runs

### Cold Start Behavior

**Modal Cold Start**:
- **Duration**: 5-7 minutes
- **Frequency**: First call after idle period (>10 minutes)
- **Impact**: Very slow first run

**ResponseRecorder Mitigation**:
- **First run**: Accept cold start (one-time cost)
- **Subsequent runs**: No cold start (uses cache)
- **Development workflow**: Record once, iterate fast

### Storage Requirements

**Fixture File Sizes**:
- **IR responses**: ~1-5 KB per response
- **100 test cases**: ~100-500 KB total
- **Git-friendly**: JSON format, human-readable, diff-friendly

**Recommendations**:
- Commit fixtures to git (enable offline testing)
- Use `.gitignore` for temporary fixtures (if needed)
- Periodically clean up unused fixtures (manual review)

---

## Troubleshooting

### Issue 1: Fixture File Not Found

**Symptom**:
```
FileNotFoundError: tests/fixtures/ir_responses.json not found
```

**Cause**: No cached responses yet (first run without `RECORD_FIXTURES=true`)

**Solution**:
```bash
# Record responses first
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_test.py -v

# Verify fixture created
ls -lh tests/fixtures/ir_responses.json

# Now run without RECORD_FIXTURES
uv run pytest tests/integration/test_your_test.py -v
```

### Issue 2: Responses Not Updating

**Symptom**: Changes to prompts not reflected in tests

**Cause**: Using cached responses (not re-recording)

**Solution**:
```bash
# Re-record fixtures
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_test.py -v

# Verify fixtures changed
git diff tests/fixtures/ir_responses.json

# Commit updated fixtures
git add tests/fixtures/ir_responses.json
git commit -m "Update fixtures for new prompts"
```

### Issue 3: Tests Still Slow

**Symptom**: Tests taking 30-60s despite using recorder

**Possible Causes**:
1. **`RECORD_FIXTURES=true` is set** → Recording every time
2. **Cache miss** → Wrong key, fixture not found
3. **Generator function called outside recorder** → Bypassing cache

**Debugging**:
```bash
# 1. Check environment
echo $RECORD_FIXTURES
# Should be empty or "false"

# 2. Enable verbose logging
uv run pytest tests/integration/test_your_test.py -v -s

# 3. Check cache stats
# Add to test:
stats = ir_recorder.get_stats()
print(f"Cache hits: {stats['cache_hits']}")  # Should be >0

# 4. Verify fixture file exists
ls -lh tests/fixtures/ir_responses.json
```

**Solution**:
```bash
# Unset RECORD_FIXTURES
unset RECORD_FIXTURES

# Verify cache is used
uv run pytest tests/integration/test_your_test.py -v -s
# Should see: Cache hits: 1 (or more)
```

### Issue 4: JSON Serialization Errors

**Symptom**:
```python
TypeError: Object of type IntermediateRepresentation is not JSON serializable
```

**Cause**: Using `modal_recorder` instead of `ir_recorder` for IR objects

**Solution**:
```python
# ❌ Wrong: modal_recorder doesn't handle IR serialization
async def test_ir(modal_recorder):
    ir = await modal_recorder.get_or_record(
        key="test_ir",
        generator_fn=lambda: translator.translate(prompt)
    )  # ❌ Fails - IR not JSON serializable

# ✅ Correct: ir_recorder handles IR serialization
async def test_ir(ir_recorder):
    ir = await ir_recorder.get_or_record(
        key="test_ir",
        generator_fn=lambda: translator.translate(prompt)
    )  # ✅ Works - ir_recorder serializes IR automatically
```

**For Custom Objects**:
```python
# Use SerializableResponseRecorder with custom serializers
from tests.fixtures import SerializableResponseRecorder

def serialize_custom(obj):
    return obj.to_dict()

def deserialize_custom(data):
    return CustomObject.from_dict(data)

recorder = SerializableResponseRecorder(
    fixture_file=Path("tests/fixtures/custom.json"),
    record_mode=False,
    serializer=serialize_custom,
    deserializer=deserialize_custom
)

result = await recorder.get_or_record(
    key="custom_test",
    generator_fn=lambda: generate_custom_object()
)
```

### Issue 5: Fixtures Out of Sync

**Symptom**: Tests pass locally but fail in CI (or vice versa)

**Cause**: Fixture files not committed or different between environments

**Solution**:
```bash
# 1. Ensure fixtures are committed
git add tests/fixtures/*.json
git commit -m "Add/update response fixtures"
git push

# 2. Pull latest fixtures
git pull

# 3. Verify fixture consistency
ls -lh tests/fixtures/*.json
md5sum tests/fixtures/*.json  # Compare checksums

# 4. If still out of sync, re-record
RECORD_FIXTURES=true uv run pytest tests/integration/ -v
git add tests/fixtures/*.json
git commit -m "Sync fixtures"
```

---

## Migration Examples

### Example 1: Simple Translation Test

**Before** (Slow):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ir_translation():
    """Test IR translation (slow - 30-60s every run)."""
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    prompt = "Write a function to find an element in a list"

    # 30-60 seconds EVERY TIME
    ir = await translator.translate(prompt)

    assert ir.signature.name == "find_index"
    assert len(ir.signature.parameters) >= 2
```

**After** (Fast):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ir_translation(ir_recorder):  # ← Add fixture
    """Test IR translation (first run: 30-60s, subsequent: <1s)."""
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    prompt = "Write a function to find an element in a list"

    # Wrap with recorder
    ir = await ir_recorder.get_or_record(
        key="test_ir_translation_find_index",  # ← Unique key
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "ir_translation", "prompt": prompt[:50]}
    )

    assert ir.signature.name == "find_index"
    assert len(ir.signature.parameters) >= 2
```

**Speedup**: 30-60x faster on cached runs

### Example 2: Optimization Comparison Test

**Before** (Very Slow):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_optimization_improves_quality():
    """Test that optimization improves quality (60-120s per run)."""
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)
    optimizer = MIPROOptimizer(provider)

    prompt = "Write a binary search function"

    # Baseline: 30-60s
    baseline_ir = await translator.translate(prompt)

    # Optimize: 30-60s
    optimized_translator = await optimizer.optimize(translator)
    optimized_ir = await optimized_translator.translate(prompt)

    assert optimized_ir.confidence_score > baseline_ir.confidence_score
```

**After** (Fast):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_optimization_improves_quality(ir_recorder):  # ← Add fixture
    """Test that optimization improves quality (first: 60-120s, subsequent: <2s)."""
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)
    optimizer = MIPROOptimizer(provider)

    prompt = "Write a binary search function"

    # Baseline (cached after first run)
    baseline_ir = await ir_recorder.get_or_record(
        key="optimization_baseline_binary_search",  # ← Unique key
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "optimization_baseline", "prompt": prompt}
    )

    # Optimized (cached after first run)
    optimized_ir = await ir_recorder.get_or_record(
        key="optimization_optimized_binary_search",  # ← Different key
        generator_fn=lambda: (
            optimizer.optimize(translator)
            .translate(prompt)
        ),
        metadata={"test": "optimization_optimized", "prompt": prompt}
    )

    assert optimized_ir.confidence_score > baseline_ir.confidence_score
```

**Speedup**: 30-60x faster on cached runs (60-120s → <2s)

### Example 3: Parametrized Tests

**Before** (Very Slow):
```python
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("prompt,expected_name", [
    ("Find an element", "find_index"),
    ("Binary search", "binary_search"),
    ("Sort a list", "sort_list"),
])
async def test_translation_parametrized(prompt, expected_name):
    """Test multiple prompts (90-180s per run for 3 cases)."""
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # 30-60s × 3 = 90-180s total
    ir = await translator.translate(prompt)

    assert ir.signature.name == expected_name
```

**After** (Fast):
```python
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("prompt,expected_name", [
    ("Find an element", "find_index"),
    ("Binary search", "binary_search"),
    ("Sort a list", "sort_list"),
])
async def test_translation_parametrized(ir_recorder, prompt, expected_name):  # ← Add fixture
    """Test multiple prompts (first: 90-180s, subsequent: <3s)."""
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # Use prompt-based key (auto-hashed if >100 chars)
    ir = await ir_recorder.get_or_record(
        key=f"parametrized_{expected_name}",  # ← Unique per case
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "parametrized", "prompt": prompt, "expected": expected_name}
    )

    assert ir.signature.name == expected_name
```

**Speedup**: 30-60x faster on cached runs (90-180s → <3s for 3 cases)

---

## Summary

### Key Takeaways

1. **ResponseRecorder is production-ready** - Already implemented and tested
2. **30-60x speedup** - Integration tests run in seconds instead of minutes
3. **Offline-capable** - No Modal dependency after first recording
4. **Deterministic** - Same responses every time
5. **CI/CD friendly** - Fast pipelines without Modal secrets

### Phase 2.2 Action Items

**Immediate** (Day 1):
- [x] Understand ResponseRecorder architecture ✅
- [ ] Add `ir_recorder` to all optimization tests
- [ ] Record initial fixtures: `RECORD_FIXTURES=true pytest tests/integration/optimization/`
- [ ] Commit fixtures to git

**Short-term** (Week 1):
- [ ] Update CI workflow to use cached responses
- [ ] Document fixture refresh policy (weekly validation)
- [ ] Create example optimization tests using recorder

**Ongoing**:
- [ ] Use `ir_recorder` in all new integration tests
- [ ] Re-record fixtures after prompt/signature changes
- [ ] Weekly validation: `RECORD_FIXTURES=true` to verify fixtures

### When to Use ResponseRecorder

**✅ Use ResponseRecorder When**:
- Testing against real Modal infrastructure
- Need deterministic test results
- Want fast iteration cycles
- Running tests in CI/CD
- Working offline
- Avoiding Modal cold starts

**❌ Don't Use ResponseRecorder When**:
- Testing error handling (use mocks)
- Unit testing pure logic
- Validating real-time behavior changes
- First time testing new prompts (record first!)

### References

**Implementation**:
- Core: `/Users/rand/src/lift-sys/tests/fixtures/response_recorder.py`
- Fixtures: `/Users/rand/src/lift-sys/tests/conftest.py` (lines 382-470)
- Examples: `/Users/rand/src/lift-sys/tests/integration/test_response_recording_example.py`

**Documentation**:
- User Guide: `/Users/rand/src/lift-sys/docs/RESPONSE_RECORDING_GUIDE.md`
- Implementation Summary: `/Users/rand/src/lift-sys/docs/archive/RESPONSE_RECORDING_IMPLEMENTATION_SUMMARY.md`
- Testing Strategy: `/Users/rand/src/lift-sys/docs/MAKING_TESTS_FASTER.md`

**Related**:
- Mock Inventory: `/Users/rand/src/lift-sys/docs/planning/MOCK_INVENTORY.md`
- E2E Validation Plan: `/Users/rand/src/lift-sys/docs/planning/E2E_VALIDATION_PLAN.md`

---

**Last Updated**: 2025-10-22
**Status**: Production-Ready
**Owner**: Testing Infrastructure Team
