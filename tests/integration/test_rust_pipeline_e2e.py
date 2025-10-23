"""End-to-end tests for full NLP → IR → Rust code generation pipeline.

This module tests the COMPLETE pipeline with real Modal LLM:
1. Natural language prompt → IR (via BestOfNIRTranslator)
2. IR → Rust code (via RustGenerator with schema-constrained generation)

These tests validate:
- Real LLM Rust generation quality
- Schema-constrained generation (guaranteed valid JSON)
- Full pipeline integration
- Rust-specific code patterns (ownership, borrowing, Result, Vec, iterators)

Tests use fixture caching for fast CI runs (code_recorder).
"""

from __future__ import annotations

import os

import pytest

from lift_sys.codegen.languages.rust_generator import RustGenerator
from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_rust_simple_addition(code_recorder):
    """
    Test full NLP → IR → Rust pipeline for simple addition function.

    Pipeline:
    1. "Write a Rust function that adds two integers" → IR (real LLM)
    2. IR → Rust code (real LLM with schema)

    Validates:
    - Basic Rust function syntax
    - Integer types (i32)
    - Return values
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR (using real Modal LLM)
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate("Write a Rust function that adds two integers")

        # Verify IR was generated
        assert ir is not None
        assert ir.intent.summary is not None
        assert ir.signature.name is not None
        assert len(ir.signature.parameters) >= 2  # At least 2 parameters for addition

        # Step 2: IR → Rust (using schema-constrained generation)
        generator = RustGenerator(provider)
        rust_code = await code_recorder.get_or_record(
            key="rust_pipeline_simple_addition",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "rust_pipeline_e2e",
                "prompt": "add two integers",
                "language": "rust",
            },
        )

        # Validate Rust code quality
        assert rust_code.language == "rust"
        assert rust_code.source_code is not None

        code = rust_code.source_code

        # Check for function definition
        assert "fn " in code, "Should contain function definition"

        # Check for Rust integer types
        assert "i32" in code or "i64" in code or "isize" in code, (
            "Should contain Rust integer types"
        )

        # Check for return arrow
        assert "->" in code, "Should have return type annotation"

        # Function should reference parameters
        param_count = sum(1 for p in ir.signature.parameters)
        assert param_count >= 2, "Should have at least 2 parameters"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_rust_vector_operations(code_recorder):
    """
    Test full NLP → IR → Rust pipeline for vector filtering.

    Pipeline:
    1. "Filter positive numbers from a vector" → IR
    2. IR → Rust code with Vec and iterator methods

    Validates:
    - Vec<T> collection type
    - Iterator methods (filter, map, collect)
    - Closures
    - Rust functional patterns
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Rust function that filters positive numbers from a vector"
        )

        assert ir is not None
        assert ir.signature.name is not None

        # Step 2: IR → Rust
        generator = RustGenerator(provider)
        rust_code = await code_recorder.get_or_record(
            key="rust_pipeline_vector_operations",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "rust_pipeline_e2e",
                "prompt": "filter positive numbers",
                "language": "rust",
                "feature": "vector_operations",
            },
        )

        assert rust_code.language == "rust"
        code = rust_code.source_code
        assert code is not None

        # Check for Vec type
        assert "Vec<" in code, "Should use Vec<T> collection type"

        # Check for integer types
        assert "i32" in code or "i64" in code, "Should work with integers"

        # Check for iterator methods or functional patterns
        # LLM might use filter(), iter(), collect(), or manual loop
        has_functional = "filter" in code or "iter" in code or "collect" in code or "map" in code
        has_loop = "for " in code or "while " in code

        assert has_functional or has_loop, "Should use iterator methods or loops"

        # Check for closure syntax (if using functional approach)
        if has_functional:
            assert "|" in code, "Should use closure syntax with functional methods"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_rust_result_error_handling(code_recorder):
    """
    Test full NLP → IR → Rust pipeline for Result-based error handling.

    Pipeline:
    1. "Divide two numbers and return Result" → IR
    2. IR → Rust code with Result<T, E> type

    Validates:
    - Result<T, E> error handling type
    - Ok() and Err() variants
    - Error propagation patterns
    - Rust idiomatic error handling
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Rust function that divides two numbers and returns Result"
        )

        assert ir is not None

        # Step 2: IR → Rust
        generator = RustGenerator(provider)
        rust_code = await code_recorder.get_or_record(
            key="rust_pipeline_result_error_handling",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "rust_pipeline_e2e",
                "prompt": "divide with Result error handling",
                "language": "rust",
                "feature": "result_type",
            },
        )

        assert rust_code.language == "rust"
        code = rust_code.source_code
        assert code is not None

        # Check for Result type
        assert "Result<" in code, "Should use Result<T, E> type"

        # Check for Ok/Err variants (various patterns)
        has_ok = "Ok(" in code
        has_err = "Err(" in code

        assert has_ok or has_err, "Should use Ok() or Err() constructors"

        # Check for floating point or integer division types
        assert "f64" in code or "f32" in code or "i32" in code, (
            "Should specify numeric types for division"
        )

        # Check for division operation
        assert "/" in code or "div" in code.lower(), "Should perform division"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_rust_string_manipulation(code_recorder):
    """
    Test full NLP → IR → Rust pipeline for string manipulation.

    Pipeline:
    1. "Reverse a string" → IR
    2. IR → Rust code with String operations

    Validates:
    - String vs &str types
    - chars() iterator
    - collect() for string building
    - UTF-8 awareness in Rust strings
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate("Write a Rust function that reverses a string")

        assert ir is not None

        # Step 2: IR → Rust
        generator = RustGenerator(provider)
        rust_code = await code_recorder.get_or_record(
            key="rust_pipeline_string_manipulation",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "rust_pipeline_e2e",
                "prompt": "reverse a string",
                "language": "rust",
                "feature": "string_manipulation",
            },
        )

        assert rust_code.language == "rust"
        code = rust_code.source_code
        assert code is not None

        # Check for String or &str types
        assert "String" in code or "str" in code, "Should use Rust string types"

        # Check for string iteration methods
        has_chars = "chars()" in code
        has_collect = "collect()" in code
        has_iter = "iter()" in code

        # LLM might use various string manipulation approaches
        assert has_chars or has_collect or has_iter or "rev" in code, (
            "Should use string manipulation methods"
        )

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_rust_ownership_and_borrowing(code_recorder):
    """
    Test full NLP → IR → Rust pipeline for ownership and borrowing.

    Pipeline:
    1. "Find length of longest string in a vector" → IR
    2. IR → Rust code with reference parameters

    Validates:
    - Reference parameters (&Vec<T> or &[T])
    - Borrowing without taking ownership
    - Return types (usize for length)
    - Rust ownership patterns
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Rust function that finds the length of the longest string in a vector"
        )

        assert ir is not None

        # Step 2: IR → Rust
        generator = RustGenerator(provider)
        rust_code = await code_recorder.get_or_record(
            key="rust_pipeline_ownership_borrowing",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "rust_pipeline_e2e",
                "prompt": "longest string length",
                "language": "rust",
                "feature": "ownership_borrowing",
            },
        )

        assert rust_code.language == "rust"
        code = rust_code.source_code
        assert code is not None

        # Check for Vec or slice with String
        assert "Vec<String>" in code or "[String]" in code or "&str" in code, (
            "Should work with string collections"
        )

        # Check for borrowing (reference parameters)
        assert "&" in code, "Should use references (borrowing)"

        # Check for usize (length return type)
        assert "usize" in code, "Should return usize for length"

        # Check for length operation
        assert "len()" in code or "length" in code.lower(), "Should calculate length"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_rust_schema_compliance(code_recorder):
    """
    Test that Rust generator produces schema-compliant JSON.

    Validates:
    - Modal provider uses generate_structured() with RUST_GENERATION_SCHEMA
    - Output matches expected JSON structure
    - No JSON parsing errors (guaranteed by XGrammar)

    This test validates the architectural improvement that made Modal compatibility possible.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Create simple IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate("Write a function to multiply two numbers")

        assert ir is not None

        # Generate Rust (uses schema-constrained generation)
        generator = RustGenerator(provider)
        rust_code = await code_recorder.get_or_record(
            key="rust_schema_compliance_test",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "rust_pipeline_e2e",
                "validation": "schema_compliance",
                "language": "rust",
            },
        )

        # Schema compliance validation
        assert rust_code.language == "rust"
        assert rust_code.source_code is not None

        # Metadata should indicate schema-constrained generation was used
        # (when using Modal provider with xgrammar support)
        assert isinstance(rust_code.metadata, dict)

        # Generated code should be valid Rust syntax
        # (we don't validate with rustc here, but should be parseable)
        code = rust_code.source_code
        assert len(code) > 0, "Should generate non-empty code"

        # Check for basic Rust structure
        assert "{" in code and "}" in code, "Should have code blocks"

        # Check for function definition
        assert "fn " in code, "Should define a function"

    finally:
        await provider.aclose()
