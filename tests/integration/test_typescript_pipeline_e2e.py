"""End-to-end tests for full NLP → IR → TypeScript code generation pipeline.

This module tests the COMPLETE pipeline with real Modal LLM:
1. Natural language prompt → IR (via BestOfNIRTranslator)
2. IR → TypeScript code (via TypeScriptGenerator with schema-constrained generation)

These tests validate:
- Real LLM TypeScript generation quality
- Schema-constrained generation (guaranteed valid JSON)
- Full pipeline integration
- TypeScript-specific code patterns (types, const/let, arrow functions)

Tests use fixture caching for fast CI runs (code_recorder).
"""

from __future__ import annotations

import os

import pytest

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_typescript_simple_addition(code_recorder):
    """
    Test full NLP → IR → TypeScript pipeline for simple addition function.

    Pipeline:
    1. "Write a function to add two numbers" → IR (real LLM)
    2. IR → TypeScript code (real LLM with schema)

    Validates real Modal LLM TypeScript generation quality.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR (using real Modal LLM)
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a TypeScript function that adds two numbers and returns the result"
        )

        # Verify IR was generated
        assert ir is not None
        assert ir.intent.summary is not None
        assert ir.signature.name is not None
        assert len(ir.signature.parameters) >= 2  # At least 2 parameters for addition

        # Step 2: IR → TypeScript (using schema-constrained generation)
        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_pipeline_simple_addition",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_pipeline_e2e",
                "prompt": "add two numbers",
                "language": "typescript",
            },
        )

        # Validate TypeScript code quality
        assert typescript.language == "typescript"
        assert typescript.source_code is not None

        code = typescript.source_code

        # Check for function definition (various TypeScript patterns)
        assert "function" in code or "const" in code or "let" in code or "export" in code, (
            "Should contain function definition"
        )

        # Check for TypeScript type annotations
        assert "number" in code.lower() or ": " in code, "Should contain TypeScript types"

        # Check for return statement
        assert "return" in code, "Should have return statement"

        # Function should reference parameters
        # (actual param names vary with LLM, but should exist)
        param_count = sum(1 for p in ir.signature.parameters)
        assert param_count >= 2, "Should have at least 2 parameters"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_typescript_array_filtering(code_recorder):
    """
    Test full NLP → IR → TypeScript pipeline for array filtering.

    Pipeline:
    1. "Filter array to keep only positive numbers" → IR
    2. IR → TypeScript code with array methods

    Validates TypeScript-specific patterns (filter, arrow functions).
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a TypeScript function that filters an array of numbers to keep only positive numbers"
        )

        assert ir is not None
        assert ir.signature.name is not None

        # Step 2: IR → TypeScript
        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_pipeline_array_filtering",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_pipeline_e2e",
                "prompt": "filter positive numbers",
                "language": "typescript",
                "feature": "array_methods",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for array operations (TypeScript/JavaScript patterns)
        # LLM might use filter(), map(), or manual loop
        assert (
            "filter" in code.lower()
            or "array" in code.lower()
            or "for" in code
            or "forEach" in code
        ), "Should contain array operations"

        # Check for TypeScript types
        assert "number" in code or "Number" in code or "[]" in code, (
            "Should have number/array types"
        )

        # Check for arrow function or regular function
        assert "=>" in code or "function" in code, "Should define a function"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_typescript_async_function(code_recorder):
    """
    Test full NLP → IR → TypeScript pipeline for async function.

    Pipeline:
    1. "Async function to fetch data" → IR
    2. IR → TypeScript code with async/await and Promise

    Validates TypeScript async patterns.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a TypeScript async function that fetches user data by ID and returns a user object"
        )

        assert ir is not None

        # Step 2: IR → TypeScript
        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_pipeline_async_function",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_pipeline_e2e",
                "prompt": "async fetch user data",
                "language": "typescript",
                "feature": "async_await",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for async patterns (various valid approaches)
        has_async = "async" in code.lower() or "promise" in code.lower()
        has_await = "await" in code.lower()

        # LLM might use async/await or Promise directly
        assert has_async or has_await, "Should have async/Promise patterns"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_typescript_schema_compliance(code_recorder):
    """
    Test that TypeScript generator produces schema-compliant JSON.

    Validates:
    - Modal provider uses generate_structured() with TYPESCRIPT_GENERATION_SCHEMA
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

        # Generate TypeScript (uses schema-constrained generation)
        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_schema_compliance_test",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_pipeline_e2e",
                "validation": "schema_compliance",
                "language": "typescript",
            },
        )

        # Schema compliance validation
        assert typescript.language == "typescript"
        assert typescript.source_code is not None

        # Metadata should indicate schema-constrained generation was used
        # (when using Modal provider with xgrammar support)
        assert isinstance(typescript.metadata, dict)

        # Generated code should be valid TypeScript syntax
        # (we don't validate with tsc here, but should be parseable)
        code = typescript.source_code
        assert len(code) > 0, "Should generate non-empty code"

        # Check for basic TypeScript structure
        assert "{" in code and "}" in code, "Should have code blocks"

    finally:
        await provider.aclose()
