#!/usr/bin/env python3
"""Run Phase 3 tests with ValidatedCodeGenerator."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.execution_validator import ExecutionValidator
from lift_sys.codegen.test_generator import TestCaseGenerator
from lift_sys.codegen.validated_generator import ValidatedCodeGenerator
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.providers.modal_provider import ModalProvider
from tests.integration.test_xgrammar_translator import PHASE_3_TESTS


async def run_phase3_with_validation():
    """Run Phase 3 tests with ValidatedCodeGenerator."""
    print("\n" + "=" * 80)
    print("Phase 3: Full Suite with ValidatedCodeGenerator")
    print("=" * 80)
    print(f"\nTotal tests: {len(PHASE_3_TESTS)}")
    print("=" * 80)

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create ValidatedCodeGenerator
    base_generator = XGrammarCodeGenerator(provider)
    validated_generator = ValidatedCodeGenerator(
        base_generator=base_generator,
        test_generator=TestCaseGenerator(),
        validator=ExecutionValidator(),
        max_attempts=3,  # Up to 3 attempts per function
    )

    results = {}
    passed = 0
    failed = 0

    for idx, test in enumerate(PHASE_3_TESTS, 1):
        func_name = test["function_name"]
        prompt = test["prompt"]
        category = test.get("category", "unknown")

        print(f"\n[Test {idx}/{len(PHASE_3_TESTS)}] {func_name}")
        print(f"Category: {category}")
        print(f"Prompt: {prompt[:80]}...")
        print("-" * 80)

        try:
            # Import translator to generate IR
            from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator

            translator = XGrammarIRTranslator(provider)
            ir = await translator.translate(prompt)

            # Generate code with validation
            result = await validated_generator.generate(ir)

            # Check if validated
            validated = result.metadata.get("validated", False)
            tests_passed = result.metadata.get("tests_passed", 0)
            total_tests = result.metadata.get("total_tests", 0)

            print("\n📊 Validation Results:")
            print(f"  Validated: {validated}")
            print(f"  Tests passed: {tests_passed}/{total_tests}")

            if result.warnings:
                print(f"  ⚠️  Warnings: {len(result.warnings)}")
                for warning in result.warnings[:3]:  # Show first 3
                    print(f"    - {warning}")

            # Execute with actual test cases
            exec_namespace = {}
            exec(result.source_code, exec_namespace)

            detected_func = None
            for name in exec_namespace:
                if callable(exec_namespace[name]) and not name.startswith("_"):
                    detected_func = exec_namespace[name]
                    break

            if detected_func is None:
                print("  ❌ FAIL: No function found in generated code")
                results[func_name] = False
                failed += 1
                continue

            # Run test cases
            test_cases = test.get("test_cases", [])
            test_passed = 0
            test_failed = 0

            for test_case in test_cases:
                try:
                    actual = detected_func(**test_case["input"])
                    expected = test_case["expected"]

                    if actual == expected:
                        test_passed += 1
                    else:
                        test_failed += 1
                        print(f"    ❌ Expected {expected}, got {actual}")
                except Exception as e:
                    test_failed += 1
                    print(f"    ❌ Error: {e}")

            if test_failed == 0:
                print(f"  ✅ PASS ({test_passed}/{len(test_cases)} tests)")
                results[func_name] = True
                passed += 1
            else:
                print(f"  ❌ FAIL ({test_passed}/{len(test_cases)} tests passed)")
                results[func_name] = False
                failed += 1

        except Exception as e:
            print(f"  ❌ FAIL: {e}")
            results[func_name] = False
            failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests:       {len(PHASE_3_TESTS)}")
    print(
        f"Passed:            {passed}/{len(PHASE_3_TESTS)} ({passed / len(PHASE_3_TESTS) * 100:.1f}%)"
    )
    print(
        f"Failed:            {failed}/{len(PHASE_3_TESTS)} ({failed / len(PHASE_3_TESTS) * 100:.1f}%)"
    )

    # Failed tests
    failed_tests = [name for name, success in results.items() if not success]
    if failed_tests:
        print(f"\nFailed tests ({len(failed_tests)}):")
        for name in failed_tests:
            print(f"  - {name}")

    print("=" * 80)

    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(run_phase3_with_validation())
    sys.exit(0 if failed == 0 else 1)
