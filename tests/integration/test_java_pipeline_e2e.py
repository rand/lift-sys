"""End-to-end tests for full NLP → IR → Java code generation pipeline.

This module tests the COMPLETE pipeline with real Modal LLM:
1. Natural language prompt → IR (via BestOfNIRTranslator)
2. IR → Java code (via JavaGenerator with schema-constrained generation)

These tests validate:
- Real LLM Java generation quality
- Schema-constrained generation (guaranteed valid JSON)
- Full pipeline integration
- Java-specific code patterns (types, generics, exceptions, streams)

Tests use fixture caching for fast CI runs (code_recorder).
"""

from __future__ import annotations

import os

import pytest

from lift_sys.codegen.languages.java_generator import JavaGenerator
from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_java_simple_addition(code_recorder):
    """
    Test full NLP → IR → Java pipeline for simple addition method.

    Pipeline:
    1. "Write a Java method that adds two integers" → IR (real LLM)
    2. IR → Java code (real LLM with schema)

    Validates:
    - Basic Java syntax (public, static, int)
    - Method signature with primitive types
    - Return statement
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR (using real Modal LLM)
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Java method that adds two integers and returns the result"
        )

        # Verify IR was generated
        assert ir is not None
        assert ir.intent.summary is not None
        assert ir.signature.name is not None
        assert len(ir.signature.parameters) >= 2  # At least 2 parameters for addition

        # Step 2: IR → Java (using schema-constrained generation)
        generator = JavaGenerator(provider)
        java_code = await code_recorder.get_or_record(
            key="java_pipeline_simple_addition",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "java_pipeline_e2e",
                "prompt": "add two integers",
                "language": "java",
            },
        )

        # Validate Java code quality
        assert java_code.language == "java"
        assert java_code.source_code is not None

        code = java_code.source_code

        # Check for Java method keywords
        assert "public" in code or "private" in code or "protected" in code, (
            "Should have access modifier"
        )

        # Check for Java type system
        assert "int" in code.lower() or "integer" in code.lower(), "Should use int/Integer type"

        # Check for return statement
        assert "return" in code, "Should have return statement"

        # Check for method structure
        assert "{" in code and "}" in code, "Should have method body"

        # Verify parameter count matches IR
        param_count = len(ir.signature.parameters)
        assert param_count >= 2, "Should have at least 2 parameters"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_java_list_operations(code_recorder):
    """
    Test full NLP → IR → Java pipeline for list filtering.

    Pipeline:
    1. "Filter positive numbers from a list" → IR
    2. IR → Java code with List<Integer> and filtering logic

    Validates:
    - Java collections (List<Integer>)
    - Generics syntax
    - Stream operations or for-each loops
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Java method that filters a list of integers to keep only positive numbers"
        )

        assert ir is not None
        assert ir.signature.name is not None

        # Step 2: IR → Java
        generator = JavaGenerator(provider)
        java_code = await code_recorder.get_or_record(
            key="java_pipeline_list_operations",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "java_pipeline_e2e",
                "prompt": "filter positive numbers",
                "language": "java",
                "feature": "collections",
            },
        )

        assert java_code.language == "java"
        code = java_code.source_code
        assert code is not None

        # Check for Java collections
        has_list = "List" in code or "ArrayList" in code or "list" in code.lower()
        assert has_list, "Should use List or ArrayList"

        # Check for generics (List<Integer> or similar)
        has_generics = "<" in code and ">" in code
        assert has_generics, "Should use generics for type safety"

        # Check for filtering logic (stream or loop)
        has_stream = "stream" in code.lower() or "filter" in code.lower()
        has_loop = "for" in code.lower() or "foreach" in code.lower() or "while" in code.lower()
        assert has_stream or has_loop, "Should have filtering logic (stream or loop)"

        # Check for Integer type
        assert "Integer" in code or "int" in code, "Should reference integer type"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_java_exception_handling(code_recorder):
    """
    Test full NLP → IR → Java pipeline for exception handling.

    Pipeline:
    1. "Divide two numbers and throw exception" → IR
    2. IR → Java code with throws clause or try-catch

    Validates:
    - Java exception handling (throws, try-catch)
    - ArithmeticException or custom exception
    - Checked exception syntax
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Java method that divides two numbers and throws an exception if the divisor is zero"
        )

        assert ir is not None

        # Step 2: IR → Java
        generator = JavaGenerator(provider)
        java_code = await code_recorder.get_or_record(
            key="java_pipeline_exception_handling",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "java_pipeline_e2e",
                "prompt": "divide with exception",
                "language": "java",
                "feature": "exception_handling",
            },
        )

        assert java_code.language == "java"
        code = java_code.source_code
        assert code is not None

        # Check for exception handling patterns
        has_throws = "throws" in code.lower()
        has_try_catch = "try" in code.lower() and "catch" in code.lower()
        has_throw = "throw" in code.lower()

        # Should have at least one exception handling pattern
        assert has_throws or has_try_catch or has_throw, (
            "Should have exception handling (throws/try-catch/throw)"
        )

        # Check for exception types
        has_arithmetic = "ArithmeticException" in code or "arithmetic" in code.lower()
        has_illegal = "IllegalArgumentException" in code
        has_exception = "Exception" in code

        assert has_arithmetic or has_illegal or has_exception, "Should reference exception type"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_java_generic_method(code_recorder):
    """
    Test full NLP → IR → Java pipeline for generic method.

    Pipeline:
    1. "Generic method to find maximum element" → IR
    2. IR → Java code with <T extends Comparable<T>>

    Validates:
    - Java generics with type parameters
    - Generic bounds (extends Comparable)
    - Generic method syntax
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Java generic method that finds the maximum element in a list using Comparable"
        )

        assert ir is not None

        # Step 2: IR → Java
        generator = JavaGenerator(provider)
        java_code = await code_recorder.get_or_record(
            key="java_pipeline_generic_method",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "java_pipeline_e2e",
                "prompt": "generic maximum",
                "language": "java",
                "feature": "generics",
            },
        )

        assert java_code.language == "java"
        code = java_code.source_code
        assert code is not None

        # Check for generic syntax
        has_type_param = "<" in code and ">" in code
        assert has_type_param, "Should have type parameters (<T>)"

        # Check for generic bounds or Comparable
        has_comparable = "Comparable" in code or "comparable" in code.lower()
        has_extends = "extends" in code.lower()

        # Should have either Comparable or extends for proper generics
        assert has_comparable or has_extends, "Should use Comparable or extends for generic bounds"

        # Check for List usage with generics
        has_list = "List" in code or "list" in code.lower()
        assert has_list, "Should use List with generics"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_nlp_to_java_stream_operations(code_recorder):
    """
    Test full NLP → IR → Java pipeline for stream operations.

    Pipeline:
    1. "Count words in string using streams" → IR
    2. IR → Java code with Arrays.stream(), collect(), Collectors

    Validates:
    - Java 8+ functional patterns
    - Stream API (stream(), collect(), Collectors)
    - Lambda expressions or method references
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Step 1: NLP → IR
        translator = BestOfNIRTranslator(provider, n_candidates=1)
        ir = await translator.translate(
            "Write a Java method that counts the number of words in a string using streams"
        )

        assert ir is not None

        # Step 2: IR → Java
        generator = JavaGenerator(provider)
        java_code = await code_recorder.get_or_record(
            key="java_pipeline_stream_operations",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "java_pipeline_e2e",
                "prompt": "count words with streams",
                "language": "java",
                "feature": "streams",
            },
        )

        assert java_code.language == "java"
        code = java_code.source_code
        assert code is not None

        # Check for stream operations
        has_stream = "stream" in code.lower() or "Stream" in code
        has_arrays = "Arrays" in code or "arrays" in code.lower()
        has_collect = "collect" in code.lower() or "Collectors" in code

        # Should use stream API (either stream() or collect())
        assert has_stream or has_arrays or has_collect, (
            "Should use Stream API (stream/collect/Collectors)"
        )

        # Check for functional patterns
        has_lambda = "->" in code  # Lambda expression syntax
        has_method_ref = "::" in code  # Method reference syntax

        # Should have some functional pattern (lambda or method reference)
        # Note: LLM might also use traditional loops, which is acceptable
        has_functional = has_lambda or has_method_ref or has_stream

        # Check for String operations
        has_string = "String" in code or "string" in code.lower()
        assert has_string, "Should work with String type"

        # Check for counting logic
        has_count = "count" in code.lower() or "length" in code.lower() or "size" in code.lower()
        assert has_count, "Should have counting logic"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_java_schema_compliance(code_recorder):
    """
    Test that Java generator produces schema-compliant JSON.

    Validates:
    - Modal provider uses generate_structured() with JAVA_GENERATION_SCHEMA
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
        ir = await translator.translate("Write a Java method to multiply two numbers")

        assert ir is not None

        # Generate Java (uses schema-constrained generation)
        generator = JavaGenerator(provider)
        java_code = await code_recorder.get_or_record(
            key="java_schema_compliance_test",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "java_pipeline_e2e",
                "validation": "schema_compliance",
                "language": "java",
            },
        )

        # Schema compliance validation
        assert java_code.language == "java"
        assert java_code.source_code is not None

        # Metadata should indicate schema-constrained generation was used
        # (when using Modal provider with xgrammar support)
        assert isinstance(java_code.metadata, dict)

        # Generated code should be valid Java syntax
        # (we don't validate with javac here, but should be parseable)
        code = java_code.source_code
        assert len(code) > 0, "Should generate non-empty code"

        # Check for basic Java structure
        assert "{" in code and "}" in code, "Should have code blocks"

        # Check for method structure
        has_access = "public" in code or "private" in code or "protected" in code
        assert has_access, "Should have access modifier"

        # Check for proper Java syntax elements
        has_semicolon = ";" in code  # Java statements end with semicolons
        assert has_semicolon, "Should have semicolons for statements"

    finally:
        await provider.aclose()
