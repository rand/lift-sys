#!/usr/bin/env python3
"""Test Phase 7 constraint validation impact on the 3 persistent failures."""

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
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider

# The 3 persistent failures - designed to trigger specific constraints
TEST_PROMPTS = {
    "count_words": "Create a function that counts the number of words in a string, where words are separated by spaces",
    "find_index": "Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found.",
    "is_valid_email": "Create a function that checks if a string is a valid email address. Must contain @ symbol and a dot after the @",
}

TEST_CASES = {
    "count_words": [
        ({"text": "hello world"}, 2),
        ({"text": "one"}, 1),
        ({"text": ""}, 0),
        ({"text": "a b c d e"}, 5),
    ],
    "find_index": [
        ({"items": [1, 2, 3], "target": 2}, 1),
        ({"items": [1, 2, 3], "target": 4}, -1),
        ({"items": [], "target": 1}, -1),
        ({"items": [1, 2, 1], "target": 1}, 0),  # FIRST match, not last!
    ],
    "is_valid_email": [
        ({"email": "test@example.com"}, True),
        ({"email": "invalid"}, False),
        ({"email": "no@at"}, False),
        ({"email": "test@.com"}, False),  # Dot immediately after @ - the bug!
        ({"email": "@example.com"}, True),  # Basic validation allows this
    ],
}


async def test_function(func_name: str, prompt: str, test_cases: list):
    """Test a single function with ValidatedCodeGenerator + Phase 7 constraints."""
    print("\n" + "=" * 80)
    print(f"Testing: {func_name}")
    print("=" * 80)
    print(f"Prompt: {prompt}\n")

    # Initialize
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    translator = XGrammarIRTranslator(provider)
    base_generator = XGrammarCodeGenerator(provider)  # Has Phase 7 integrated
    validated_generator = ValidatedCodeGenerator(
        base_generator=base_generator,
        test_generator=TestCaseGenerator(),
        validator=ExecutionValidator(),
        max_attempts=3,
    )

    # Translate to IR
    print("📝 Translating prompt to IR...")
    ir = await translator.translate(prompt)

    # Show detected constraints (Phase 7 Week 1)
    if ir.constraints:
        print(f"\n🎯 Phase 7 Detected Constraints: {len(ir.constraints)}")
        for i, constraint in enumerate(ir.constraints, 1):
            print(f"  {i}. {constraint.__class__.__name__}: {constraint.description}")
    else:
        print("\n⚠️  No constraints detected for this IR")

    # Generate code with validation (includes Phase 7 validation)
    print("\n🔧 Generating code with validation...")
    result = await validated_generator.generate(ir)

    # Check validation status
    validated = result.metadata.get("validated", False)
    tests_passed = result.metadata.get("tests_passed", 0)
    total_tests = result.metadata.get("total_tests", 0)

    print("\n📊 Validation Results:")
    print(f"  Validated: {validated}")
    print(f"  Tests passed: {tests_passed}/{total_tests}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.warnings:
        for warning in result.warnings:
            print(f"    ⚠️  {warning}")

    # Check if Phase 7 validation was triggered
    if "constraint_validation" in result.metadata:
        print(f"\n✅ Phase 7 Constraint Validation: {result.metadata['constraint_validation']}")

    print("\n📝 Generated Code:")
    print("-" * 80)
    print(result.source_code)
    print("-" * 80)

    # Execute with actual test cases
    print(f"\n🧪 Running {len(test_cases)} test cases...")
    exec_namespace = {}
    try:
        exec(result.source_code, exec_namespace)
    except Exception as e:
        print(f"  ❌ Execution error: {e}")
        return False, ir.constraints

    # Find the generated function
    detected_func = None
    for name in exec_namespace:
        if callable(exec_namespace[name]) and not name.startswith("_"):
            detected_func = exec_namespace[name]
            break

    if detected_func is None:
        print("  ❌ No function found in generated code")
        return False, ir.constraints

    # Run test cases
    passed = 0
    failed = 0

    for test_input, expected in test_cases:
        try:
            actual = detected_func(**test_input)
            if actual == expected:
                passed += 1
                print(f"  ✅ {test_input} → {actual}")
            else:
                failed += 1
                print(f"  ❌ {test_input} → Expected {expected}, got {actual}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test_input} → Error: {e}")

    print(f"\n📊 Test Results: {passed}/{len(test_cases)} passed")

    if failed == 0:
        print(f"✅ {func_name}: PASS")
        return True, ir.constraints
    else:
        print(f"❌ {func_name}: FAIL ({failed} tests failed)")
        return False, ir.constraints


async def main():
    """Test all 3 persistent failures with Phase 7 constraint validation."""
    print("\n" + "=" * 80)
    print("Phase 7 Impact Test: 3 Persistent Failures")
    print("=" * 80)
    print("\nTesting with:")
    print("  ✅ Phase 1-2: IR Translation & Code Generation")
    print("  ✅ Phase 4: AST Repair")
    print("  ✅ Phase 5a: IR Interpretation & Semantic Validation")
    print("  ✅ Phase 5b: Assertion-based Validation")
    print("  ✅ Phase 7: IR-Level Constraints (NEW)")
    print("    - Constraint Detection (Week 1)")
    print("    - Constraint Validation (Week 2)")

    results = {}
    constraints_detected = {}

    for func_name, prompt in TEST_PROMPTS.items():
        test_cases = TEST_CASES[func_name]
        try:
            success, constraints = await test_function(func_name, prompt, test_cases)
            results[func_name] = success
            constraints_detected[func_name] = constraints
        except Exception as e:
            print(f"\n❌ {func_name} failed with error: {e}")
            import traceback

            traceback.print_exc()
            results[func_name] = False
            constraints_detected[func_name] = []

    # Summary
    print("\n" + "=" * 80)
    print("PHASE 7 IMPACT SUMMARY")
    print("=" * 80)

    for func_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        constraints = constraints_detected.get(func_name, [])
        print(f"  {func_name}: {status}")
        if constraints:
            print(f"    Constraints: {', '.join(c.__class__.__name__ for c in constraints)}")
        else:
            print("    Constraints: None detected")

    total = sum(results.values())
    baseline = 0  # From logs/test_3_failures_integration_final.log: 0/3 successful
    improvement = total - baseline

    print("\n📊 Results:")
    print(f"  Baseline (without Phase 7): {baseline}/3 tests successful (0%)")
    print(f"  With Phase 7:               {total}/3 tests successful ({total / 3 * 100:.0f}%)")

    if improvement > 0:
        print(f"  Improvement:                +{improvement} tests fixed! 🎉")
    elif improvement == 0:
        print("  Improvement:                No change (still investigating)")

    if total == 3:
        print("\n🎉 SUCCESS! All 3 persistent failures are now fixed!")
        print("\nPhase 7 Constraint Validation Impact: 100%")
        return 0
    elif total > 0:
        print(f"\n✅ PARTIAL SUCCESS: {total}/3 tests passing")
        print(f"Phase 7 Constraint Validation helped fix {improvement} test(s)")
        return 0
    else:
        print("\n❌ FAILURE: All 3 tests still failing")
        print("Phase 7 needs further investigation")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
