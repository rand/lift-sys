# Response Recording Guide

**Making Integration Tests 30-60x Faster**

This guide explains how to use the response recording system to make integration tests run in seconds instead of minutes.

---

## Overview

**Problem**: Modal API calls take 30-60 seconds each, making integration tests painfully slow (5-10 minutes).

**Solution**: Record API responses on first run, replay them on subsequent runs.

**Result**:
- First run: Same speed (records responses)
- Subsequent runs: **30-60x faster** (replays from cache)
- Deterministic: Same response every time
- Offline: No API needed after recording

---

## Quick Start

### 1. Use the Fixture in Your Test

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ir_translation(ir_recorder):
    """Test using recorded IR responses."""
    from lift_sys.providers.modal_provider import ModalProvider
    from lift_sys.codegen.xgrammar_translator import XGrammarIRTranslator

    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    prompt = "Write a function to find an element in a list"

    # This call is wrapped with recording
    ir = await ir_recorder.get_or_record(
        key="test_find_index",
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "translation", "prompt": prompt}
    )

    # Assertions
    assert ir.signature.name == "find_index"
```

### 2. Record Responses (First Run)

```bash
# Record responses from Modal API
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_test.py -v

# This will:
# - Call Modal API (slow, 30-60s)
# - Save responses to tests/fixtures/ir_responses.json
# - Run normally
```

### 3. Use Cached Responses (Subsequent Runs)

```bash
# Use cached responses (default)
uv run pytest tests/integration/test_your_test.py -v

# This will:
# - Load responses from tests/fixtures/ir_responses.json
# - Return cached responses instantly (<1s)
# - No Modal API calls
```

---

## Available Fixtures

### `modal_recorder`

General-purpose recorder for any Modal API responses.

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_modal_recorder(modal_recorder):
    """Use modal_recorder for raw API responses."""

    response = await modal_recorder.get_or_record(
        key="unique_test_key",
        generator_fn=lambda: some_async_api_call(),
        metadata={"test": "name", "version": "1.0"}
    )

    assert response["status"] == "success"
```

**Stores**: `tests/fixtures/modal_responses.json`

### `ir_recorder`

Specialized recorder for `IntermediateRepresentation` objects.

Handles serialization/deserialization automatically.

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_ir_recorder(ir_recorder):
    """Use ir_recorder for IR objects."""

    ir = await ir_recorder.get_or_record(
        key="test_ir_generation",
        generator_fn=lambda: translator.translate(prompt),
        metadata={"prompt": prompt[:50]}
    )

    # ir is a proper IntermediateRepresentation object
    assert ir.intent.summary is not None
```

**Stores**: `tests/fixtures/ir_responses.json`

---

## Key Concepts

### Recording Mode

**Enabled** (`RECORD_FIXTURES=true`):
- Calls actual API
- Saves response to fixture file
- Overwrites existing cached response for that key

**Disabled** (default, `RECORD_FIXTURES=false` or not set):
- Loads response from fixture file
- Returns cached response instantly
- Never calls API

### Keys

Keys uniquely identify cached responses. Use descriptive keys:

```python
# Good keys
key="test_find_index_basic"
key="test_binary_search_with_holes"
key="test_factorial_recursive"

# Bad keys (too generic)
key="test1"
key="ir"
```

**Long keys are automatically hashed** (>100 chars), so you can use entire prompts:

```python
# This works - automatically hashed
key=f"translate_{prompt}"
```

### Metadata

Optional metadata for documentation and debugging:

```python
await recorder.get_or_record(
    key="test_key",
    generator_fn=lambda: api_call(),
    metadata={
        "test": "test_function_name",
        "prompt": prompt[:100],
        "version": "1.0",
        "date": "2025-10-15"
    }
)
```

Metadata is stored in fixture file but not used for caching.

---

## Workflow

### Development Workflow

```bash
# 1. Write test with recorder fixture
vim tests/integration/test_new_feature.py

# 2. Record responses (first run, slow)
RECORD_FIXTURES=true uv run pytest tests/integration/test_new_feature.py -v

# 3. Verify fixture file was created
ls -la tests/fixtures/ir_responses.json

# 4. Run with cache (fast)
uv run pytest tests/integration/test_new_feature.py -v

# 5. Commit fixture file
git add tests/fixtures/ir_responses.json
git commit -m "Add recorded fixtures for new feature tests"
```

### CI/CD Workflow

```yaml
# .github/workflows/test.yml
- name: Run integration tests
  run: |
    # Use cached fixtures (fast, no Modal API calls)
    uv run pytest tests/integration/ -v
  # No RECORD_FIXTURES needed - fixtures committed to repo
```

### Updating Fixtures

When API responses change or prompts change:

```bash
# Re-record specific test
RECORD_FIXTURES=true uv run pytest tests/integration/test_specific.py -v

# Re-record all tests
RECORD_FIXTURES=true uv run pytest tests/integration/ -v

# Commit updated fixtures
git add tests/fixtures/*.json
git commit -m "Update test fixtures for new API version"
```

---

## Migration Guide

### Before (Slow)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_translation():
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # 30-60 seconds EVERY TIME
    ir = await translator.translate(prompt)

    assert ir.signature.name == "find_index"
```

**Runtime**: 30-60 seconds every run

### After (Fast)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_translation(ir_recorder):
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # 30-60s first run, <1s subsequent runs
    ir = await ir_recorder.get_or_record(
        key="test_translation_find_index",
        generator_fn=lambda: translator.translate(prompt)
    )

    assert ir.signature.name == "find_index"
```

**Runtime**:
- First run (recording): 30-60 seconds
- Subsequent runs: <1 second
- **30-60x faster**

---

## Performance Comparison

### Without Response Recording

```bash
$ uv run pytest tests/integration/ -v
... 10 tests × 30-60s each = 5-10 minutes ...
```

### With Response Recording

```bash
# First run (record once)
$ RECORD_FIXTURES=true uv run pytest tests/integration/ -v
... 10 tests × 30-60s each = 5-10 minutes (same as before) ...
# Fixtures saved to tests/fixtures/

# All subsequent runs (use cache)
$ uv run pytest tests/integration/ -v
... 10 tests × <1s each = <10 seconds ...
```

**Speedup**: **30-60x faster** on subsequent runs

---

## Best Practices

### 1. Use Descriptive Keys

```python
# Good
key="test_find_index_with_validation"
key="test_factorial_recursive_base_case"

# Bad
key="test1"
key="ir"
```

### 2. Include Metadata

```python
await ir_recorder.get_or_record(
    key="test_binary_search",
    generator_fn=lambda: translator.translate(prompt),
    metadata={
        "test": "test_binary_search",
        "prompt": prompt[:100],
        "expected_function": "binary_search"
    }
)
```

### 3. Commit Fixture Files

```bash
# After recording, commit fixtures
git add tests/fixtures/*.json
git commit -m "Add test fixtures for integration tests"
git push
```

Now team members and CI can use cached responses.

### 4. Update Fixtures When Needed

```bash
# When prompts or API changes, re-record
RECORD_FIXTURES=true uv run pytest tests/integration/ -v
git add tests/fixtures/*.json
git commit -m "Update test fixtures for new prompts"
```

### 5. One Key Per Test Case

```python
# Each test case should have unique key
async def test_find_index(ir_recorder):
    ir = await ir_recorder.get_or_record(
        key="test_find_index",  # Unique
        generator_fn=...
    )

async def test_binary_search(ir_recorder):
    ir = await ir_recorder.get_or_record(
        key="test_binary_search",  # Different
        generator_fn=...
    )
```

---

## Advanced Usage

### Custom Serialization

For complex objects, use `SerializableResponseRecorder`:

```python
from tests.fixtures import SerializableResponseRecorder
from pathlib import Path

def serialize_custom(obj):
    """Convert custom object to JSON-serializable form."""
    return {
        "type": type(obj).__name__,
        "data": obj.to_dict()
    }

def deserialize_custom(data):
    """Convert JSON back to custom object."""
    return CustomObject.from_dict(data["data"])

recorder = SerializableResponseRecorder(
    fixture_file=Path("tests/fixtures/custom_responses.json"),
    record_mode=False,
    serializer=serialize_custom,
    deserializer=deserialize_custom
)

response = await recorder.get_or_record(
    key="custom_test",
    generator_fn=lambda: generate_custom_object()
)
```

### Statistics Tracking

```python
@pytest.mark.integration
async def test_with_stats(modal_recorder):
    # Run test
    response = await modal_recorder.get_or_record(...)

    # Get statistics
    stats = modal_recorder.get_stats()
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache misses: {stats['cache_misses']}")
    print(f"Hit rate: {stats['hit_rate']:.2%}")
```

### Clear Cache

```python
# In test
modal_recorder.clear_cache()

# Or delete fixture file
rm tests/fixtures/modal_responses.json
```

---

## Troubleshooting

### Fixture file not found

**Symptom**: `FileNotFoundError` when running test

**Solution**: Run with `RECORD_FIXTURES=true` first:

```bash
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_test.py -v
```

### Responses not updating

**Symptom**: Changes to prompts not reflected in tests

**Solution**: Re-record fixtures:

```bash
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_test.py -v
```

### Tests still slow

**Symptom**: Tests taking 30-60s despite using recorder

**Possible causes**:
1. `RECORD_FIXTURES=true` is set (records every time)
2. Cache miss due to wrong key
3. Generator function called outside recorder

**Solution**:
```bash
# Check environment
echo $RECORD_FIXTURES  # Should be empty or "false"

# Verify cache hit
uv run pytest tests/integration/test_your_test.py -v -s
# Should see "Cache hits: X" in output
```

### JSON serialization errors

**Symptom**: `TypeError: Object of type X is not JSON serializable`

**Solution**: Use `SerializableResponseRecorder` with custom serializers:

```python
@pytest.fixture
def custom_recorder():
    from tests.fixtures import SerializableResponseRecorder

    def serialize(obj):
        return obj.to_dict()

    def deserialize(data):
        return CustomObject.from_dict(data)

    return SerializableResponseRecorder(
        fixture_file=Path("tests/fixtures/custom.json"),
        record_mode=False,
        serializer=serialize,
        deserializer=deserialize
    )
```

---

## Example: Complete Integration Test

```python
"""
Complete example showing response recording in action.
"""

import pytest
import os
from lift_sys.providers.modal_provider import ModalProvider
from lift_sys.codegen.xgrammar_translator import XGrammarIRTranslator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_index_translation(ir_recorder):
    """
    Test IR translation with response recording.

    First run (RECORD_FIXTURES=true): ~30-60s
    Subsequent runs: <1s
    """
    # Setup
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    translator = XGrammarIRTranslator(provider)

    # Test prompt
    prompt = """
    Write a Python function that finds the index of an element in a list.
    Return -1 if the element is not found.
    """

    # Record/replay IR generation
    ir = await ir_recorder.get_or_record(
        key="test_find_index_translation",
        generator_fn=lambda: translator.translate(prompt),
        metadata={
            "test": "test_find_index_translation",
            "prompt": prompt.strip()[:100],
            "expected_function": "find_index"
        }
    )

    # Assertions
    assert ir is not None
    assert ir.signature.name == "find_index"
    assert len(ir.signature.parameters) >= 2
    assert ir.signature.returns == "int"

    # Get stats
    stats = ir_recorder.get_stats()
    print(f"\n📊 Recorder stats: {stats['cache_hits']} hits, {stats['cache_misses']} misses")


# Run this test:
# First time (record):  RECORD_FIXTURES=true uv run pytest test_example.py -v  (slow)
# Second+ times:        uv run pytest test_example.py -v                      (fast)
```

---

## Summary

**Response Recording Benefits**:
- ✅ **30-60x faster** integration tests
- ✅ Deterministic results
- ✅ Offline testing
- ✅ No API rate limits
- ✅ Easy to implement
- ✅ Team-wide benefit (commit fixtures)

**Implementation**:
1. Add `ir_recorder` or `modal_recorder` fixture to test
2. Wrap API call in `recorder.get_or_record()`
3. Run once with `RECORD_FIXTURES=true`
4. Commit fixture files
5. All future runs use cached responses

**Result**: Integration tests that run in seconds instead of minutes 🚀

For more details, see:
- `tests/fixtures/response_recorder.py` - Implementation
- `tests/conftest.py` - Pytest fixtures
- `tests/integration/test_response_recording_example.py` - Examples
- `docs/MAKING_TESTS_FASTER.md` - Overall testing strategy
