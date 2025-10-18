#!/usr/bin/env python3
"""
Phase 2 test with Claude 3.5 Sonnet for IR generation, Qwen for code generation.

Tests the hypothesis that better reasoning (Claude 3.5) improves IR quality
enough to push Phase 2 from 80% → 90%+.
"""

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from performance_benchmark import PerformanceBenchmark
from test_cases_nontrivial import TEST_SUITES

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.anthropic_provider import AnthropicProvider
from lift_sys.providers.modal_provider import ModalProvider


async def run_hybrid_test():
    """
    Run Phase 2 tests with Claude 3.5 for IR generation.

    Architecture:
    - IR generation: Claude 3.5 Sonnet (better reasoning)
    - Code generation: Qwen2.5-32B-Instruct on Modal (fast, cheap)
    """
    suite = TEST_SUITES["phase2"]
    tests = suite["tests"]

    # Initialize providers
    print("Initializing providers...")

    # Claude 3.5 for IR generation
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    claude_provider = AnthropicProvider()
    await claude_provider.initialize({"api_key": api_key})

    # Qwen for code generation
    qwen_provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await qwen_provider.initialize(credentials={})

    # Create translator and generator
    translator = XGrammarIRTranslator(provider=claude_provider)
    generator = XGrammarCodeGenerator(provider=qwen_provider)

    print("\n" + "=" * 70)
    print(f"{suite['name']} - Claude 3.5 IR + Qwen Code")
    print("=" * 70)
    print(f"{suite['description']}")
    print(f"Total tests: {len(tests)}")
    print("=" * 70)

    results = []
    category_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    complexity_stats = defaultdict(lambda: {"total": 0, "passed": 0})

    for i, test_case in enumerate(tests, 1):
        print(f"\n[Test {i}/{len(tests)}] {test_case['name']}")
        print(f"Category: {test_case['category']}, Complexity: {test_case['complexity']}")
        print(f"Prompt: {test_case['prompt'][:80]}...")
        print("-" * 70)

        try:
            # Step 1: Generate IR with Claude 3.5
            print("  [1/2] Generating IR with Claude 3.5...")
            ir = await translator.translate(prompt=test_case["prompt"], language="python")
            print(f"    ✓ IR generated: {ir.signature.name}()")

            # Step 2: Generate code with Qwen
            print("  [2/2] Generating code with Qwen...")
            generated_code = await generator.generate(ir=ir, language="python")

            if generated_code.is_valid:
                print("    ✓ Code generated successfully")
                compiled = True
                code = generated_code.source_code
            else:
                print(f"    ✗ Code generation failed: {generated_code.validation_errors}")
                compiled = False
                code = None
        except Exception as e:
            print(f"    ✗ Error: {e}")
            compiled = False
            code = None

        # Step 3: Execute tests if compiled
        executed = False
        exec_results = []

        if compiled and code:
            # Create temporary benchmark just for execution
            temp_benchmark = PerformanceBenchmark(
                provider=qwen_provider, output_dir=Path("benchmark_results"), estimate_costs=False
            )

            exec_results = temp_benchmark.execute_generated_code(
                code=code,
                function_name=test_case["function_name"],
                test_cases=test_case["test_cases"],
            )

            executed = all(t.passed for t in exec_results)

            # Print execution results
            passed_count = sum(1 for t in exec_results if t.passed)
            print(f"  Execution: {passed_count}/{len(exec_results)} tests passed")

            if not executed:
                # Show first failure
                failed = [t for t in exec_results if not t.passed]
                if failed:
                    print(f"  ❌ First failure: {failed[0].error}")
        elif not compiled:
            print("  ❌ Compilation failed - skipping execution")

        # Overall status
        success = compiled and executed
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} (Compiled: {compiled}, Executed: {executed})")

        # Update stats
        category_stats[test_case["category"]]["total"] += 1
        complexity_stats[test_case["complexity"]]["total"] += 1

        if success:
            category_stats[test_case["category"]]["passed"] += 1
            complexity_stats[test_case["complexity"]]["passed"] += 1

        # Store result
        results.append(
            {
                "test_name": test_case["name"],
                "category": test_case["category"],
                "complexity": test_case["complexity"],
                "prompt": test_case["prompt"],
                "compiled": compiled,
                "executed": executed,
                "success": success,
                "execution_tests": [
                    {
                        "test_name": t.test_name,
                        "passed": t.passed,
                        "expected": str(t.expected),
                        "actual": str(t.actual),
                        "error": t.error,
                    }
                    for t in exec_results
                ],
            }
        )

    # Print summary
    total = len(results)
    compilation_success = sum(1 for r in results if r["compiled"])
    execution_success = sum(1 for r in results if r["executed"])
    overall_success = sum(1 for r in results if r["success"])

    print("\n" + "=" * 70)
    print("SUMMARY - Claude 3.5 IR Generation")
    print("=" * 70)
    print(f"Total tests:       {total}")
    print(
        f"Compilation:       {compilation_success}/{total} ({compilation_success / total * 100:.1f}%)"
    )
    print(
        f"Execution:         {execution_success}/{total} ({execution_success / total * 100:.1f}%)"
    )
    print(f"Overall success:   {overall_success}/{total} ({overall_success / total * 100:.1f}%)")

    print("\nBy Category:")
    for category, stats in sorted(category_stats.items()):
        pct = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {category:20s}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")

    print("\nBy Complexity:")
    for complexity, stats in sorted(complexity_stats.items()):
        pct = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {complexity:20s}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")

    # Comparison with baseline (80%)
    print("\n" + "=" * 70)
    print("COMPARISON TO BASELINE")
    print("=" * 70)
    baseline_pct = 80.0
    current_pct = overall_success / total * 100 if total > 0 else 0
    delta = current_pct - baseline_pct

    print(f"Baseline (Qwen IR + Qwen Code): {baseline_pct:.1f}%")
    print(f"Claude IR + Qwen Code:          {current_pct:.1f}%")
    print(f"Delta:                          {delta:+.1f}%")

    if current_pct >= 90:
        print("\n✅ SUCCESS: Claude 3.5 IR achieves ≥90% - ready for Phase 3!")
    elif current_pct > baseline_pct:
        print(f"\n⚠️  IMPROVEMENT: +{delta:.1f}% but below 90% target")
        print("   Consider: Hybrid approach or Constraint Propagation")
    else:
        print("\n❌ NO IMPROVEMENT: Claude 3.5 IR doesn't help")
        print("   Recommend: Implement Constraint Propagation")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path("logs") / f"phase2_claude_ir_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(
            {
                "suite": "phase2",
                "ir_provider": "claude-3.5-sonnet",
                "code_provider": "qwen2.5-32b-instruct",
                "timestamp": timestamp,
                "summary": {
                    "total": total,
                    "compilation": compilation_success,
                    "execution": execution_success,
                    "overall": overall_success,
                    "baseline_pct": baseline_pct,
                    "current_pct": current_pct,
                    "delta_pct": delta,
                },
                "results": results,
                "category_stats": dict(category_stats),
                "complexity_stats": dict(complexity_stats),
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results saved to: {output_file}")
    print("=" * 70)

    # Cleanup
    await claude_provider.aclose()
    await qwen_provider.aclose()

    return results


if __name__ == "__main__":
    asyncio.run(run_hybrid_test())
