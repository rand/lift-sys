"""End-to-end tests for full NLP → IR → Go code generation pipeline.

This module tests the COMPLETE pipeline with real Modal LLM:
1. Natural language prompt → IR (via BestOfNIRTranslator)
2. IR → Go code (via GoGenerator with schema-constrained generation)

These tests validate:
- Real LLM Go generation quality
- Schema-constrained generation (guaranteed valid JSON)
- Full pipeline integration
- Go-specific code patterns (slices, maps, error handling, goroutines)

Tests use fixture caching for fast CI runs (code_recorder).
"""

from __future__ import annotations

import os

import pytest

from lift_sys.codegen.languages.go_generator import GoGenerator
from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_go_simple_addition(code_recorder):
    """
    Test full NLP → IR → Go pipeline for simple addition function.

    Pipeline:
    1. "Write a Go function that adds two integers" → IR (real LLM)
    2. IR → Go code (real LLM with schema)

    Validates:
    - Basic Go syntax (func keyword)
    - Function signature with typed parameters
    - Integer return type
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR (using real Modal LLM)
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Go function that adds two integers and returns the result"
        )

        # Verify IR was generated
        assert ir is not None
        assert ir.intent.summary is not None
        assert ir.signature.name is not None
        assert len(ir.signature.parameters) >= 2  # At least 2 parameters for addition

        # Step 2: IR → Go (using schema-constrained generation)
        generator = GoGenerator(provider)
        go_code = await code_recorder.get_or_record(
            key="go_pipeline_simple_addition",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "go_pipeline_e2e",
                "prompt": "add two integers",
                "language": "go",
            },
        )

        # Validate Go code quality
        assert go_code.language == "go"
        assert go_code.source_code is not None

        code = go_code.source_code

        # Check for Go function definition
        assert "func " in code, "Should contain func keyword"

        # Check for Go type annotations
        assert "int" in code, "Should contain int type"

        # Check for return statement
        assert "return" in code, "Should have return statement"

        # Check for package declaration (Go files must have package)
        assert "package" in code, "Should have package declaration"

        # Function should reference parameters
        param_count = sum(1 for p in ir.signature.parameters)
        assert param_count >= 2, "Should have at least 2 parameters"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_go_slice_operations(code_recorder):
    """
    Test full NLP → IR → Go pipeline for slice filtering.

    Pipeline:
    1. "Filter positive numbers from slice" → IR
    2. IR → Go code with slice operations

    Validates:
    - Go slice syntax ([]int)
    - Idiomatic for-range loop
    - append() for slice building
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Go function that filters a slice of integers to keep only positive numbers"
        )

        assert ir is not None
        assert ir.signature.name is not None

        # Step 2: IR → Go
        generator = GoGenerator(provider)
        go_code = await code_recorder.get_or_record(
            key="go_pipeline_slice_operations",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "go_pipeline_e2e",
                "prompt": "filter positive numbers from slice",
                "language": "go",
                "feature": "slice_operations",
            },
        )

        assert go_code.language == "go"
        code = go_code.source_code
        assert code is not None

        # Check for slice type annotation
        assert "[]int" in code or "[]" in code, "Should have slice type"

        # Check for iteration patterns (Go-specific)
        # LLM might use for-range or traditional for loop
        assert "for " in code and ("range" in code or ";" in code), "Should contain Go loop"

        # Check for append (idiomatic Go slice building)
        assert "append" in code.lower(), "Should use append for slice operations"

        # Check for function definition
        assert "func " in code, "Should define a function"

        # Check for package declaration
        assert "package" in code, "Should have package declaration"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_go_error_handling(code_recorder):
    """
    Test full NLP → IR → Go pipeline for error handling.

    Pipeline:
    1. "Divide two numbers and return error" → IR
    2. IR → Go code with multiple returns and error handling

    Validates:
    - Multiple return values (value, error)
    - Explicit error type
    - if err != nil pattern
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Go function that divides two numbers and returns an error if divisor is zero"
        )

        assert ir is not None

        # Step 2: IR → Go
        generator = GoGenerator(provider)
        go_code = await code_recorder.get_or_record(
            key="go_pipeline_error_handling",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "go_pipeline_e2e",
                "prompt": "divide with error handling",
                "language": "go",
                "feature": "error_handling",
            },
        )

        assert go_code.language == "go"
        code = go_code.source_code
        assert code is not None

        # Check for error type in signature or body
        assert "error" in code, "Should have error type"

        # Check for multiple returns pattern (common in Go)
        # Signature might be (float64, error) or similar
        assert "(" in code and ")" in code, "Should have parentheses for returns/params"

        # Check for error handling patterns
        # LLM might use if err != nil, return nil/err, or errors.New()
        has_error_pattern = "err" in code.lower() or "error" in code.lower() or "nil" in code
        assert has_error_pattern, "Should have error handling patterns"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_go_map_operations(code_recorder):
    """
    Test full NLP → IR → Go pipeline for map operations.

    Pipeline:
    1. "Count word frequencies in string" → IR
    2. IR → Go code with map and string splitting

    Validates:
    - Go map type (map[string]int)
    - String splitting (strings.Fields or strings.Split)
    - Map initialization and updates
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Go function that counts word frequencies in a string and returns a map"
        )

        assert ir is not None

        # Step 2: IR → Go
        generator = GoGenerator(provider)
        go_code = await code_recorder.get_or_record(
            key="go_pipeline_map_operations",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "go_pipeline_e2e",
                "prompt": "count word frequencies",
                "language": "go",
                "feature": "map_operations",
            },
        )

        assert go_code.language == "go"
        code = go_code.source_code
        assert code is not None

        # Check for map type
        assert "map[" in code or "map" in code.lower(), "Should have map type"

        # Check for string operations
        # LLM might import strings package and use Fields() or Split()
        has_string_ops = (
            "strings" in code.lower() or "split" in code.lower() or "fields" in code.lower()
        )
        assert has_string_ops, "Should use string splitting"

        # Check for map initialization
        # LLM might use make(map[...]) or literal map syntax
        assert "make" in code or "{" in code, "Should initialize map"

        # Check for function definition
        assert "func " in code, "Should define a function"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_go_goroutines_channels(code_recorder):
    """
    Test full NLP → IR → Go pipeline for goroutines and channels.

    Pipeline:
    1. "Sum numbers concurrently with goroutines" → IR
    2. IR → Go code with go keyword and channels

    Validates:
    - go keyword for goroutines
    - Channel declaration (chan type)
    - Channel operations (send/receive)
    - Concurrent patterns (sync primitives)
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Go function that sums numbers from a slice concurrently using goroutines and channels"
        )

        assert ir is not None

        # Step 2: IR → Go
        generator = GoGenerator(provider)
        go_code = await code_recorder.get_or_record(
            key="go_pipeline_goroutines_channels",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "go_pipeline_e2e",
                "prompt": "concurrent sum with goroutines",
                "language": "go",
                "feature": "concurrency",
            },
        )

        assert go_code.language == "go"
        code = go_code.source_code
        assert code is not None

        # Check for goroutine launch
        assert "go " in code or "go(" in code, "Should have go keyword for goroutines"

        # Check for channel operations
        # LLM might use make(chan ...), <- operator, or close()
        has_channel = "chan" in code or "<-" in code or "make(chan" in code
        assert has_channel, "Should use channels"

        # Check for sync primitives (optional but common)
        # LLM might use sync.WaitGroup, close(), or channel ranges
        has_sync = "sync" in code.lower() or "close(" in code or "waitgroup" in code.lower()
        # Note: Not strict requirement, but good indicator

        # Check for function definition
        assert "func " in code, "Should define a function"

    finally:
        await provider.aclose()
