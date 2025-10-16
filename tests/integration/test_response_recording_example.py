"""
Example integration test using response recording.

This test demonstrates how to use the response recorder to:
1. Record Modal API responses on first run (RECORD_FIXTURES=true)
2. Replay cached responses on subsequent runs (default)

This makes integration tests run in seconds instead of minutes.

Usage:
    # First run - records responses (slow, ~30-60s)
    RECORD_FIXTURES=true uv run pytest tests/integration/test_response_recording_example.py -v

    # Subsequent runs - uses cached responses (fast, <1s)
    uv run pytest tests/integration/test_response_recording_example.py -v

    # Run all integration tests with recording
    RECORD_FIXTURES=true uv run pytest tests/integration/ -v

    # Run all integration tests with cache (default)
    uv run pytest tests/integration/ -v
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_response_recorder_basic_usage(modal_recorder):
    """
    Demonstrate basic response recorder usage.

    This test shows how to wrap any async API call with the recorder.
    """

    # Simulate an expensive API call
    async def expensive_api_call():
        """Mock expensive operation that we want to cache."""
        # In real tests, this would be:
        # return await translator.translate(prompt)
        # return await generator.generate(ir)
        return {"result": "cached_response", "status": "success"}

    # First call: hits API (or cache if already recorded)
    response = await modal_recorder.get_or_record(
        key="test_basic_usage",
        generator_fn=expensive_api_call,
        metadata={"test": "basic_usage", "version": "1.0"},
    )

    # Verify response structure
    assert response["result"] == "cached_response"
    assert response["status"] == "success"

    # Second call with same key: guaranteed to hit cache
    cached_response = await modal_recorder.get_or_record(
        key="test_basic_usage", generator_fn=expensive_api_call
    )

    # Should be identical
    assert cached_response == response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_response_recorder_with_ir(ir_recorder):
    """
    Demonstrate IR-specific recorder usage.

    This recorder handles serialization/deserialization of IR objects.
    """
    from lift_sys.ir.models import (
        IntentClause,
        IntermediateRepresentation,
        Metadata,
        Parameter,
        SigClause,
    )

    # Simulate IR generation
    async def generate_sample_ir():
        """Mock IR generation."""
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
            assertions=[],
            metadata=Metadata(origin="test"),
        )

    # Record/replay IR
    ir = await ir_recorder.get_or_record(
        key="test_ir_recording", generator_fn=generate_sample_ir, metadata={"test": "ir_recording"}
    )

    # Verify IR structure
    assert ir.intent.summary == "Add two numbers"
    assert ir.signature.name == "add"
    assert len(ir.signature.parameters) == 2


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example - requires Modal endpoint")
async def test_response_recorder_with_real_modal():
    """
    Example: Real Modal API call with response recording.

    To use this test:
    1. Uncomment and ensure Modal endpoint is configured
    2. Run with RECORD_FIXTURES=true to record responses
    3. Run without flag to use cached responses

    This is skipped by default as it requires Modal setup.
    """
    import os

    from lift_sys.codegen.xgrammar_translator import XGrammarIRTranslator

    from lift_sys.providers.modal_provider import ModalProvider

    # Set up Modal provider
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL")
    if not endpoint_url:
        pytest.skip("MODAL_ENDPOINT_URL not configured")

    provider = ModalProvider(endpoint_url=endpoint_url)
    translator = XGrammarIRTranslator(provider)

    # Use recorder from conftest.py
    from pathlib import Path

    from tests.fixtures import ResponseRecorder

    recorder = ResponseRecorder(
        fixture_file=Path("tests/fixtures/modal_responses.json"),
        record_mode=os.getenv("RECORD_FIXTURES", "false").lower() == "true",
    )

    # Prompt to translate
    test_prompt = """
    Write a Python function that finds the index of an element in a list.
    If the element is not found, return -1.
    """

    # This will either:
    # - Call Modal API and record (RECORD_FIXTURES=true)
    # - Use cached response (RECORD_FIXTURES=false or not set)
    ir = await recorder.get_or_record(
        key=f"translate_{test_prompt[:50]}",
        generator_fn=lambda: translator.translate(test_prompt),
        metadata={"prompt": test_prompt, "test": "real_modal"},
    )

    # Verify IR was generated
    assert ir is not None
    assert ir.signature.name is not None


@pytest.mark.unit
def test_response_recorder_stats(fixtures_dir):
    """Test response recorder statistics tracking."""

    from tests.fixtures import ResponseRecorder

    recorder = ResponseRecorder(fixture_file=fixtures_dir / "test_stats.json", record_mode=False)

    # Initially no stats
    stats = recorder.get_stats()
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0
    assert stats["hit_rate"] == 0

    # Add a response manually
    recorder.responses["test_key"] = {"response": "test_data"}

    # Check stats after cache hit
    response = recorder.responses.get("test_key")
    assert response is not None

    # Clean up
    if (fixtures_dir / "test_stats.json").exists():
        (fixtures_dir / "test_stats.json").unlink()


# =============================================================================
# Migration Guide for Existing Tests
# =============================================================================

"""
To migrate existing integration tests to use response recording:

BEFORE:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_translation():
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # This call takes 30-60 seconds every time
    ir = await translator.translate(prompt)

    assert ir.signature.name == "find_index"
```

AFTER:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_translation(ir_recorder):
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # This call takes 30-60s first run, <1s subsequent runs
    ir = await ir_recorder.get_or_record(
        key="test_translation_find_index",
        generator_fn=lambda: translator.translate(prompt),
        metadata={"test": "translation", "prompt": prompt[:50]}
    )

    assert ir.signature.name == "find_index"
```

Benefits:
- ✅ First run: Same speed (records response)
- ✅ Subsequent runs: 30-60x faster (replays cache)
- ✅ Deterministic: Same response every time
- ✅ Offline: No Modal endpoint needed after recording
- ✅ CI/CD: Commit fixtures, run tests without API calls

Steps:
1. Add `ir_recorder` or `modal_recorder` fixture parameter
2. Wrap expensive call in `recorder.get_or_record()`
3. Provide unique key for the test case
4. Run once with RECORD_FIXTURES=true
5. Commit the generated fixtures/modal_responses.json or fixtures/ir_responses.json
6. All future runs use cached responses
"""
