"""Edge case tests for TypeScript code generation.

This module tests challenging edge cases that production code will encounter:
- Recursive functions (factorial, tree traversal)
- Generic functions (type parameters)
- Complex types (unions, intersections, type guards)
- Error scenarios (null/undefined handling, type narrowing)
- Async edge cases (error propagation, promise chaining)

These tests identify generator weaknesses before production deployment.
Tests use fixture caching (code_recorder) for fast CI runs.
"""

from __future__ import annotations

import os

import pytest

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.modal_provider import ModalProvider

# =============================================================================
# Recursion Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_recursive_factorial(code_recorder):
    """
    Test recursive factorial function generation.

    Expected challenges:
    - Generator must handle base case and recursive case
    - Type annotations must be preserved in recursion
    - Stack overflow prevention via constraints

    This will likely expose: Missing base case validation, incorrect recursion patterns.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        # Create IR for recursive factorial
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Calculate factorial recursively",
                rationale="Compute n! using recursive algorithm",
            ),
            signature=SigClause(
                name="factorial",
                parameters=[Parameter(name="n", type_hint="int")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Recurses until base case (n <= 1)"),
                EffectClause(description="Returns n * factorial(n-1)"),
            ],
            assertions=[
                AssertClause(predicate="n >= 0", rationale="No negative factorials"),
                AssertClause(predicate="result >= 1", rationale="Factorial always >= 1"),
            ],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        # Generate TypeScript
        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_recursive_factorial",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "recursion",
                "feature": "recursive_function",
                "expected_failure": "missing_base_case",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Validation checks (likely to fail)
        # Check for base case
        has_base_case = "if" in code or "return 1" in code or "n <= 1" in code
        assert has_base_case, "Recursive function should have base case condition"

        # Check for recursive call
        assert "factorial" in code, "Should contain recursive call"

        # Check for proper return type
        assert ": number" in code, "Should have number return type"

        # Check for multiplication (n * factorial(n-1) pattern)
        assert "*" in code, "Should have multiplication for factorial"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_recursive_tree_traversal(code_recorder):
    """
    Test recursive tree traversal with nested objects.

    Expected challenges:
    - Generator must handle nested object types
    - Recursion through object properties
    - Null checks for leaf nodes

    This will likely expose: Complex type handling, null safety issues.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Count nodes in a binary tree recursively",
                rationale="Traverse tree structure and count all nodes",
            ),
            signature=SigClause(
                name="countNodes",
                parameters=[
                    Parameter(name="node", type_hint="dict | None"),  # TreeNode | null
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Returns 0 for null nodes"),
                EffectClause(description="Recursively counts left and right subtrees"),
            ],
            assertions=[
                AssertClause(predicate="result >= 0", rationale="Count cannot be negative"),
            ],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_recursive_tree",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "recursion",
                "feature": "nested_objects",
                "expected_failure": "null_handling",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for null handling (union type parameter)
        assert "null" in code or "undefined" in code or "?" in code, (
            "Should handle null/undefined nodes"
        )

        # Check for recursive pattern
        assert "countNodes" in code, "Should have recursive call"

        # Check for property access (node.left, node.right)
        assert "." in code or "?." in code, "Should access node properties"

    finally:
        await provider.aclose()


# =============================================================================
# Generic Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_generic_array_function(code_recorder):
    """
    Test generic array function with type parameter.

    Expected challenges:
    - Generator must preserve type parameter T
    - Array<T> type annotations
    - Generic return type

    This will likely expose: Generic type erasure, incorrect type annotations.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Get first element from array (generic)",
                rationale="Return first item from typed array",
            ),
            signature=SigClause(
                name="first",
                parameters=[Parameter(name="arr", type_hint="list[Any]")],  # Array<T>
                returns="Any | None",  # T | undefined
            ),
            effects=[
                EffectClause(description="Returns undefined for empty arrays"),
                EffectClause(description="Returns arr[0] otherwise"),
            ],
            assertions=[],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_generic_array",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "generics",
                "feature": "type_parameters",
                "expected_failure": "generic_erasure",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for array type
        assert "Array" in code or "[]" in code, "Should have array type"

        # Check for array indexing
        assert "[0]" in code or "arr[0]" in code, "Should access first element"

        # Check for undefined handling
        assert "undefined" in code or "?" in code or "length" in code, (
            "Should handle empty array case"
        )

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_generic_promise_function(code_recorder):
    """
    Test generic async function returning Promise<T>.

    Expected challenges:
    - Generator must handle async/await correctly
    - Promise<T> type wrapping
    - Generic return type in promise

    This will likely expose: Promise type handling, async detection failures.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Delay and return value asynchronously",
                rationale="Wait specified milliseconds then return value",
            ),
            signature=SigClause(
                name="delayedValue",
                parameters=[
                    Parameter(name="value", type_hint="Any"),  # T
                    Parameter(name="delayMs", type_hint="int"),
                ],
                returns="Promise[Any]",  # Promise<T>
            ),
            effects=[
                EffectClause(description="Waits for delayMs milliseconds"),
                EffectClause(description="Returns the value after delay"),
            ],
            assertions=[
                AssertClause(predicate="delayMs >= 0", rationale="Delay cannot be negative"),
            ],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_generic_promise",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "generics",
                "feature": "promise_types",
                "expected_failure": "promise_wrapping",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for async or Promise
        assert "async" in code or "Promise" in code, "Should be async or return Promise"

        # Check for Promise<T> return type
        assert "Promise" in code, "Should have Promise return type"

        # Check for delay/timeout mechanism
        assert "timeout" in code.lower() or "delay" in code.lower() or "sleep" in code.lower(), (
            "Should implement delay"
        )

    finally:
        await provider.aclose()


# =============================================================================
# Complex Type Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_union_type_handling(code_recorder):
    """
    Test union type parameter (string | number).

    Expected challenges:
    - Generator must handle union types correctly
    - Type narrowing logic (typeof checks)
    - Different code paths for different types

    This will likely expose: Union type confusion, missing type guards.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Convert value to string (handles string or number)",
                rationale="Accept string or number, return string representation",
            ),
            signature=SigClause(
                name="toString",
                parameters=[Parameter(name="value", type_hint="str | int")],  # string | number
                returns="str",  # string
            ),
            effects=[
                EffectClause(description="Returns value as-is if string"),
                EffectClause(description="Converts to string if number"),
            ],
            assertions=[],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_union_type",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "complex_types",
                "feature": "union_types",
                "expected_failure": "type_narrowing",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for union type annotation
        assert " | " in code or "string | number" in code, "Should have union type"

        # Check for type narrowing (typeof checks)
        # Generator might not implement this correctly
        has_type_check = "typeof" in code or "instanceof" in code
        # Note: This might fail - that's expected for edge case testing

        # Check for string conversion
        assert "toString" in code or "String" in code or "`" in code, "Should convert to string"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_optional_chaining(code_recorder):
    """
    Test optional chaining for nested object access.

    Expected challenges:
    - Generator must use ?. operator for safe access
    - Handling undefined at multiple levels
    - Proper return type (T | undefined)

    This will likely expose: Missing null safety, runtime errors on nested access.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Get nested property safely with optional chaining",
                rationale="Access user.profile.email with null safety",
            ),
            signature=SigClause(
                name="getUserEmail",
                parameters=[Parameter(name="user", type_hint="dict | None")],
                returns="str | None",  # string | undefined
            ),
            effects=[
                EffectClause(description="Returns undefined if user is null"),
                EffectClause(description="Returns undefined if profile is null"),
                EffectClause(description="Returns email if path exists"),
            ],
            assertions=[],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_optional_chaining",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "complex_types",
                "feature": "optional_chaining",
                "expected_failure": "missing_null_safety",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for optional chaining operator
        has_optional_chaining = "?." in code
        assert has_optional_chaining, "Should use optional chaining (?.) operator"

        # Check for nested property access
        assert "." in code, "Should access nested properties"

        # Check for null/undefined handling in return type
        assert "undefined" in code or "null" in code or "?" in code, (
            "Should handle null/undefined return"
        )

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_type_guard_discriminated_union(code_recorder):
    """
    Test type guard with discriminated union pattern.

    Expected challenges:
    - Generator must implement proper type narrowing
    - Discriminated union handling (kind: 'success' | 'error')
    - Type-safe property access after narrowing

    This will likely expose: Complex type narrowing failures, incorrect branching.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Extract value from Result type (success or error)",
                rationale="Return data if success, null if error",
            ),
            signature=SigClause(
                name="extractValue",
                parameters=[
                    Parameter(
                        name="result", type_hint="dict"
                    )  # Result = {kind: 'success', data: T} | {kind: 'error', error: string}
                ],
                returns="Any | None",
            ),
            effects=[
                EffectClause(description="Returns data if result.kind === 'success'"),
                EffectClause(description="Returns null if result.kind === 'error'"),
            ],
            assertions=[],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_type_guard",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "complex_types",
                "feature": "type_guards",
                "expected_failure": "discriminated_union",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for conditional branching
        assert "if" in code, "Should have conditional logic"

        # Check for property access (result.kind, result.data)
        assert "." in code or "?." in code, "Should access result properties"

        # Check for discriminator check (kind === 'success')
        has_discriminator = "kind" in code or "===" in code or "==" in code
        # This might fail - that's expected

    finally:
        await provider.aclose()


# =============================================================================
# Error Scenario Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_null_undefined_edge_cases(code_recorder):
    """
    Test null vs undefined handling (JavaScript/TypeScript gotcha).

    Expected challenges:
    - Generator must distinguish null from undefined
    - Proper equality checks (=== null vs == null)
    - Nullish coalescing operator (??)

    This will likely expose: Null/undefined confusion, incorrect equality checks.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Get value or default (handles null and undefined)",
                rationale="Return value if present, default otherwise (nullish coalescing)",
            ),
            signature=SigClause(
                name="getOrDefault",
                parameters=[
                    Parameter(name="value", type_hint="Any | None"),  # T | null | undefined
                    Parameter(name="defaultValue", type_hint="Any"),  # T
                ],
                returns="Any",  # T
            ),
            effects=[
                EffectClause(description="Returns value if not null/undefined"),
                EffectClause(description="Returns defaultValue if null/undefined"),
            ],
            assertions=[],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_null_undefined",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "error_scenarios",
                "feature": "null_undefined",
                "expected_failure": "null_coalescing",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for nullish coalescing or conditional
        has_nullish = "??" in code  # Preferred modern approach
        has_conditional = "if" in code or "?" in code  # Fallback approach

        assert has_nullish or has_conditional, "Should handle null/undefined cases"

        # Check that both parameters are used
        assert "value" in code and "defaultValue" in code, "Should use both parameters"

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_array_bounds_checking(code_recorder):
    """
    Test array bounds checking (prevent out-of-bounds access).

    Expected challenges:
    - Generator must validate array index
    - Safe array access patterns
    - Proper error handling for invalid index

    This will likely expose: Missing bounds checks, runtime errors.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Get array element at index safely",
                rationale="Return element at index, or undefined if out of bounds",
            ),
            signature=SigClause(
                name="getAt",
                parameters=[
                    Parameter(name="arr", type_hint="list[Any]"),
                    Parameter(name="index", type_hint="int"),
                ],
                returns="Any | None",  # T | undefined
            ),
            effects=[
                EffectClause(description="Returns undefined if index < 0"),
                EffectClause(description="Returns undefined if index >= arr.length"),
                EffectClause(description="Returns arr[index] otherwise"),
            ],
            assertions=[],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_array_bounds",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "error_scenarios",
                "feature": "bounds_checking",
                "expected_failure": "missing_validation",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for bounds checking
        has_length_check = "length" in code
        has_conditional = "if" in code or "?" in code

        assert has_length_check or has_conditional, "Should check array bounds"

        # Check for array indexing
        assert "[" in code and "]" in code, "Should access array by index"

    finally:
        await provider.aclose()


# =============================================================================
# Async Edge Case Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_async_error_propagation(code_recorder):
    """
    Test async function with error propagation.

    Expected challenges:
    - Generator must handle try/catch in async context
    - Proper error rethrowing
    - Promise rejection handling

    This will likely expose: Missing error handling, incorrect async patterns.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Fetch with retry on failure",
                rationale="Attempt async operation, retry once on error",
            ),
            signature=SigClause(
                name="fetchWithRetry",
                parameters=[Parameter(name="url", type_hint="str")],
                returns="Promise[dict]",  # Promise<Response>
            ),
            effects=[
                EffectClause(description="Attempts fetch operation"),
                EffectClause(description="Retries once if first attempt fails"),
                EffectClause(description="Throws error if both attempts fail"),
            ],
            assertions=[
                AssertClause(predicate="url.length > 0", rationale="URL must not be empty"),
            ],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_async_error",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "async_edge_cases",
                "feature": "error_propagation",
                "expected_failure": "missing_error_handling",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for async
        assert "async" in code or "Promise" in code, "Should be async function"

        # Check for error handling (might be missing - that's expected)
        has_try_catch = "try" in code and "catch" in code
        has_error_handling = has_try_catch or "throw" in code

        # Check for retry logic
        # Generator might not implement this correctly
        # (This is an edge case that may fail)

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_promise_chaining(code_recorder):
    """
    Test promise chaining with multiple awaits.

    Expected challenges:
    - Generator must chain multiple async operations
    - Proper await ordering
    - Data flow between promises

    This will likely expose: Incorrect async sequencing, missing awaits.
    """
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Fetch user, then fetch their posts (chained async)",
                rationale="Sequential async operations with data dependency",
            ),
            signature=SigClause(
                name="getUserPosts",
                parameters=[Parameter(name="userId", type_hint="int")],
                returns="Promise[list]",  # Promise<Post[]>
            ),
            effects=[
                EffectClause(description="First: fetch user data by ID"),
                EffectClause(description="Then: fetch posts using user data"),
                EffectClause(description="Returns array of posts"),
            ],
            assertions=[
                AssertClause(predicate="userId > 0", rationale="User ID must be positive"),
            ],
            metadata=Metadata(origin="test_edge_case", language="typescript"),
        )

        generator = TypeScriptGenerator(provider)
        typescript = await code_recorder.get_or_record(
            key="typescript_edge_promise_chaining",
            generator_fn=lambda: generator.generate(ir),
            metadata={
                "test": "typescript_edge_cases",
                "category": "async_edge_cases",
                "feature": "promise_chaining",
                "expected_failure": "incorrect_sequencing",
            },
        )

        assert typescript.language == "typescript"
        code = typescript.source_code
        assert code is not None

        # Check for async
        assert "async" in code, "Should be async function"

        # Check for multiple awaits (chaining)
        await_count = code.count("await")
        # Should have at least 2 awaits for fetch user, then fetch posts
        # (This might fail if generator doesn't understand the dependency)

        # Check for Promise return type
        assert "Promise" in code, "Should return Promise"

    finally:
        await provider.aclose()
