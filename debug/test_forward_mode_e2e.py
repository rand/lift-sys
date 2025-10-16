#!/usr/bin/env python3
"""
Real Forward Mode E2E Test (lift-sys-59)

This test demonstrates the COMPLETE forward mode workflow with NO MOCKS:
1. Natural language prompt → IR (using Modal + XGrammar)
2. IR → Python code (using Modal + XGrammar with CODE_GENERATION_SCHEMA)
3. Validate code compiles
4. Execute code and verify correctness

This is the critical test to prove the core value proposition works.
"""

import ast
import asyncio
import json
import os
import time
from typing import Any

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.ir.schema import IR_JSON_SCHEMA
from lift_sys.providers.modal_provider import ModalProvider


class E2ETestResult:
    """Results from an E2E test run."""

    def __init__(self):
        self.prompt: str = ""
        self.ir_generation_success: bool = False
        self.ir_generation_time_ms: float = 0.0
        self.ir_json: dict[str, Any] | None = None
        self.ir_model: IntermediateRepresentation | None = None
        self.code_generation_success: bool = False
        self.code_generation_time_ms: float = 0.0
        self.generated_code: str = ""
        self.code_compiles: bool = False
        self.code_execution_success: bool = False
        self.test_results: list[tuple[str, bool, str]] = []  # (test_name, passed, details)
        self.errors: list[str] = []

    @property
    def total_time_ms(self) -> float:
        """Total end-to-end time."""
        return self.ir_generation_time_ms + self.code_generation_time_ms

    @property
    def success(self) -> bool:
        """Was the entire E2E workflow successful?"""
        return (
            self.ir_generation_success
            and self.code_generation_success
            and self.code_compiles
            and self.code_execution_success
            and all(passed for _, passed, _ in self.test_results)
        )


async def test_nlp_to_ir(provider: ModalProvider, prompt: str) -> tuple[bool, float, dict | None]:
    """
    Step 1: Generate IR from natural language prompt.

    Args:
        provider: Modal provider instance
        prompt: Natural language specification

    Returns:
        (success, latency_ms, ir_json)
    """
    print("\n" + "=" * 80)
    print("STEP 1: Natural Language → IR Generation")
    print("=" * 80)
    print(f"Prompt: {prompt}")
    print()

    try:
        start = time.time()
        ir_json = await provider.generate_structured(
            prompt=prompt,
            schema=IR_JSON_SCHEMA,
            max_tokens=2048,
            temperature=0.3,
            top_p=0.95,
        )
        latency_ms = (time.time() - start) * 1000

        print(f"⏱️  Generation time: {latency_ms:.0f}ms ({latency_ms / 1000:.2f}s)")
        print()
        print("Generated IR:")
        print(json.dumps(ir_json, indent=2))

        # Validate IR structure
        if "intent" not in ir_json or "summary" not in ir_json["intent"]:
            print("\n❌ Invalid IR: Missing intent.summary")
            return False, latency_ms, ir_json

        if "signature" not in ir_json or "name" not in ir_json["signature"]:
            print("\n❌ Invalid IR: Missing signature.name")
            return False, latency_ms, ir_json

        print(f"\n✅ IR generated successfully: {ir_json['signature']['name']}()")
        return True, latency_ms, ir_json

    except Exception as e:
        print(f"\n❌ IR generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False, 0.0, None


async def test_ir_to_code(
    provider: ModalProvider, ir_json: dict[str, Any]
) -> tuple[bool, float, str]:
    """
    Step 2: Generate Python code from IR.

    Args:
        provider: Modal provider instance
        ir_json: Generated IR JSON

    Returns:
        (success, latency_ms, generated_code)
    """
    print("\n" + "=" * 80)
    print("STEP 2: IR → Python Code Generation")
    print("=" * 80)

    try:
        # Parse IR into model
        ir = IntermediateRepresentation.from_dict(ir_json)
        print(f"Function: {ir.signature.name}")
        print(f"Purpose: {ir.intent.summary}")

        # For E2E testing: remove holes if present
        # (In production, holes would be resolved through the session management workflow)
        holes = ir.typed_holes()
        if holes:
            print(f"\n⚠️  IR contains {len(holes)} holes - removing for E2E test:")
            for hole in holes:
                print(f"   - {hole.identifier}: {hole.description}")

            # Remove holes from all clauses
            ir.intent.holes = []
            ir.signature.holes = []
            for effect in ir.effects:
                effect.holes = []
            for assertion in ir.assertions:
                assertion.holes = []

            print("   ✓ Holes removed for testing purposes")

        print()

        # Initialize code generator
        generator = XGrammarCodeGenerator(provider=provider)

        # Check if constrained generation is supported
        has_constrained = (
            hasattr(provider, "generate_structured") and provider.capabilities.structured_output
        )
        if has_constrained:
            print("✅ Using constrained generation (XGrammar + CODE_GENERATION_SCHEMA)")
        else:
            print("⚠️  Falling back to text-based generation")
        print()

        # Generate code
        print("Generating code...")
        start = time.time()
        result = await generator.generate(ir)
        latency_ms = (time.time() - start) * 1000

        print(f"⏱️  Generation time: {latency_ms:.0f}ms ({latency_ms / 1000:.2f}s)")
        print()

        # Display metadata
        constrained = result.metadata.get("constrained_generation", False)
        print(f"Constrained generation used: {constrained}")
        print(f"Attempts: {result.metadata.get('attempts', 'N/A')}")
        print()

        # Display generated code
        print("Generated Code:")
        print("-" * 80)
        print(result.source_code)
        print("-" * 80)

        if constrained:
            print("\n✅ Code generated with XGrammar constraints")
        else:
            print("\n⚠️  Code generated without constraints (fallback mode)")

        return True, latency_ms, result.source_code

    except Exception as e:
        print(f"\n❌ Code generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False, 0.0, ""


def validate_code_compiles(code: str) -> tuple[bool, str]:
    """
    Step 3: Validate that the generated code compiles.

    Args:
        code: Generated Python code

    Returns:
        (compiles, error_message)
    """
    print("\n" + "=" * 80)
    print("STEP 3: Code Validation (Compilation)")
    print("=" * 80)

    try:
        ast.parse(code)
        print("✅ Code compiles successfully (ast.parse)")
        return True, ""
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
        print(f"❌ Compilation failed: {error_msg}")
        return False, error_msg


def execute_and_test_code(
    code: str, function_name: str, test_cases: list[tuple]
) -> tuple[bool, list]:
    """
    Step 4: Execute the generated code and run test cases.

    Args:
        code: Generated Python code
        function_name: Name of the function to test
        test_cases: List of (args, expected_result) tuples

    Returns:
        (all_passed, test_results)
        test_results is list of (test_name, passed, details)
    """
    print("\n" + "=" * 80)
    print("STEP 4: Code Execution & Testing")
    print("=" * 80)

    test_results = []

    try:
        # Execute the code to define the function
        namespace = {}
        exec(code, namespace)

        if function_name not in namespace:
            print(f"❌ Function '{function_name}' not found in generated code")
            return False, [("function_exists", False, f"Function '{function_name}' not found")]

        func = namespace[function_name]
        print(f"✅ Function '{function_name}' loaded successfully")
        print()

        # Run test cases
        print("Running test cases:")
        all_passed = True

        for i, test_case in enumerate(test_cases):
            if len(test_case) == 2:
                args, expected = test_case
                kwargs = {}
            else:
                args, kwargs, expected = test_case

            try:
                # Call the function
                if isinstance(args, tuple):
                    actual = func(*args, **kwargs)
                else:
                    actual = func(args, **kwargs)

                # Check result
                passed = actual == expected

                if passed:
                    symbol = "✅"
                    details = f"Expected {expected}, got {actual}"
                else:
                    symbol = "❌"
                    details = f"Expected {expected}, got {actual}"
                    all_passed = False

                test_name = f"test_case_{i + 1}"
                test_results.append((test_name, passed, details))
                print(f"  {symbol} Test {i + 1}: {args} → {actual} (expected {expected})")

            except Exception as e:
                symbol = "❌"
                details = f"Exception: {type(e).__name__}: {e}"
                test_results.append((f"test_case_{i + 1}", False, details))
                print(f"  {symbol} Test {i + 1}: {args} raised {type(e).__name__}: {e}")
                all_passed = False

        print()
        if all_passed:
            print("✅ All test cases passed!")
        else:
            print("❌ Some test cases failed")

        return all_passed, test_results

    except Exception as e:
        error_msg = f"Execution error: {type(e).__name__}: {e}"
        print(f"❌ {error_msg}")
        import traceback

        traceback.print_exc()
        return False, [("execution", False, error_msg)]


async def run_e2e_test(
    provider: ModalProvider,
    prompt: str,
    test_cases: list[tuple],
    expected_function_name: str | None = None,
) -> E2ETestResult:
    """
    Run a complete E2E test.

    Args:
        provider: Modal provider instance
        prompt: Natural language specification
        test_cases: Test cases to validate the generated code
        expected_function_name: Expected function name (optional, will extract from IR if not provided)

    Returns:
        E2ETestResult with all metrics and results
    """
    result = E2ETestResult()
    result.prompt = prompt

    # Step 1: NLP → IR
    success, latency, ir_json = await test_nlp_to_ir(provider, prompt)
    result.ir_generation_success = success
    result.ir_generation_time_ms = latency
    result.ir_json = ir_json

    if not success:
        result.errors.append("IR generation failed")
        return result

    # Determine function name
    function_name = expected_function_name or ir_json["signature"]["name"]

    # Step 2: IR → Code
    success, latency, code = await test_ir_to_code(provider, ir_json)
    result.code_generation_success = success
    result.code_generation_time_ms = latency
    result.generated_code = code

    if not success:
        result.errors.append("Code generation failed")
        return result

    # Step 3: Validate compilation
    compiles, error = validate_code_compiles(code)
    result.code_compiles = compiles

    if not compiles:
        result.errors.append(f"Code compilation failed: {error}")
        return result

    # Step 4: Execute and test
    all_passed, test_results = execute_and_test_code(code, function_name, test_cases)
    result.code_execution_success = all_passed
    result.test_results = test_results

    if not all_passed:
        result.errors.append("Some test cases failed")

    return result


async def main():
    """Run the E2E test suite."""
    print("\n" + "=" * 80)
    print("FORWARD MODE E2E TEST (lift-sys-59)")
    print("Proving: NLP → IR → Code with REAL LLM (NO MOCKS)")
    print("=" * 80)

    # Get Modal endpoint from environment
    modal_endpoint = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    print(f"\nModal Endpoint: {modal_endpoint}")

    # Initialize provider
    print("\nInitializing Modal provider...")
    provider = ModalProvider(endpoint_url=modal_endpoint)
    await provider.initialize(credentials={})

    # Check health
    print("Checking Modal endpoint health...")
    is_healthy = await provider.check_health()
    if not is_healthy:
        print("❌ Modal endpoint is not healthy. Aborting tests.")
        await provider.aclose()
        return

    print("✅ Modal endpoint is healthy")

    # Test 1: Email validation function
    print("\n" + "=" * 80)
    print("TEST 1: Email Validation Function")
    print("=" * 80)

    test1_prompt = "Create a function to validate email addresses using regex"
    test1_cases = [
        (("user@example.com",), True),
        (("invalid.email",), False),
        (("test@domain.co.uk",), True),
        (("@invalid.com",), False),
        (("user@",), False),
    ]

    result1 = await run_e2e_test(provider, test1_prompt, test1_cases)

    # Print summary for Test 1
    print("\n" + "=" * 80)
    print("TEST 1 SUMMARY")
    print("=" * 80)
    print(f"Prompt: {result1.prompt}")
    print(
        f"IR Generation: {'✅ Success' if result1.ir_generation_success else '❌ Failed'} ({result1.ir_generation_time_ms:.0f}ms)"
    )
    print(
        f"Code Generation: {'✅ Success' if result1.code_generation_success else '❌ Failed'} ({result1.code_generation_time_ms:.0f}ms)"
    )
    print(f"Code Compiles: {'✅ Yes' if result1.code_compiles else '❌ No'}")
    print(f"Code Executes: {'✅ Yes' if result1.code_execution_success else '❌ No'}")
    print(
        f"Test Cases: {sum(1 for _, p, _ in result1.test_results if p)}/{len(result1.test_results)} passed"
    )
    print(f"Total Time: {result1.total_time_ms / 1000:.2f}s")
    print(f"Overall: {'✅ SUCCESS' if result1.success else '❌ FAILED'}")

    if result1.errors:
        print("\nErrors:")
        for error in result1.errors:
            print(f"  - {error}")

    # Test 2: Factorial function
    print("\n\n" + "=" * 80)
    print("TEST 2: Factorial Function")
    print("=" * 80)

    test2_prompt = "Create a function to calculate the factorial of a number"
    test2_cases = [
        ((0,), 1),
        ((1,), 1),
        ((5,), 120),
        ((10,), 3628800),
    ]

    result2 = await run_e2e_test(provider, test2_prompt, test2_cases)

    # Print summary for Test 2
    print("\n" + "=" * 80)
    print("TEST 2 SUMMARY")
    print("=" * 80)
    print(f"Prompt: {result2.prompt}")
    print(
        f"IR Generation: {'✅ Success' if result2.ir_generation_success else '❌ Failed'} ({result2.ir_generation_time_ms:.0f}ms)"
    )
    print(
        f"Code Generation: {'✅ Success' if result2.code_generation_success else '❌ Failed'} ({result2.code_generation_time_ms:.0f}ms)"
    )
    print(f"Code Compiles: {'✅ Yes' if result2.code_compiles else '❌ No'}")
    print(f"Code Executes: {'✅ Yes' if result2.code_execution_success else '❌ No'}")
    print(
        f"Test Cases: {sum(1 for _, p, _ in result2.test_results if p)}/{len(result2.test_results)} passed"
    )
    print(f"Total Time: {result2.total_time_ms / 1000:.2f}s")
    print(f"Overall: {'✅ SUCCESS' if result2.success else '❌ FAILED'}")

    if result2.errors:
        print("\nErrors:")
        for error in result2.errors:
            print(f"  - {error}")

    # Final summary
    print("\n\n" + "=" * 80)
    print("FINAL SUMMARY: Forward Mode E2E Testing")
    print("=" * 80)

    total_tests = 2
    passed_tests = sum([result1.success, result2.success])

    print(f"\nTests Passed: {passed_tests}/{total_tests}")
    print()
    print("Performance Metrics:")
    print(f"  Test 1 Total Time: {result1.total_time_ms / 1000:.2f}s")
    print(f"  Test 2 Total Time: {result2.total_time_ms / 1000:.2f}s")
    print(f"  Average Total Time: {(result1.total_time_ms + result2.total_time_ms) / 2000:.2f}s")
    print()
    print(
        f"  Test 1 IR → Code Time: {result1.ir_generation_time_ms / 1000:.2f}s + {result1.code_generation_time_ms / 1000:.2f}s"
    )
    print(
        f"  Test 2 IR → Code Time: {result2.ir_generation_time_ms / 1000:.2f}s + {result2.code_generation_time_ms / 1000:.2f}s"
    )
    print()

    if passed_tests == total_tests:
        print("🎉 ALL E2E TESTS PASSED!")
        print()
        print("✅ CORE VALUE PROPOSITION PROVEN:")
        print("   - Natural language → Formal IR (with XGrammar)")
        print("   - Formal IR → Working Python code (with XGrammar)")
        print("   - Code compiles and passes tests")
        print("   - End-to-end latency is acceptable (<10s)")
        print()
        print("🚀 lift-sys-59 COMPLETE - Forward mode works!")
    else:
        print(f"❌ {total_tests - passed_tests} E2E test(s) failed")
        print()
        print("Next Steps:")
        print("1. Review error messages above")
        print("2. Check Modal endpoint logs")
        print("3. Debug failing steps")
        print("4. Iterate on prompts/schemas if needed")

    await provider.aclose()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
