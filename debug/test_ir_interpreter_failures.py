#!/usr/bin/env python3
"""Test IR Interpreter on the 3 persistent failures."""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider
from lift_sys.validation.ir_interpreter import IRInterpreter

# The 3 persistent failures
TEST_PROMPTS = {
    "count_words": "Create a function that counts the number of words in a string, where words are separated by spaces",
    "find_index": "Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found.",
    "is_valid_email": "Create a function that checks if a string is a valid email address. Must contain @ symbol and a dot after the @",
}

# Expected issues for each test
EXPECTED_ISSUES = {
    "count_words": {
        "categories": ["missing_return", "implicit_return"],
        "description": "Should detect missing return value",
    },
    "find_index": {
        "categories": ["loop_behavior", "missing_return_path"],
        "description": "Should detect loop behavior issue (first match vs iteration)",
    },
    "is_valid_email": {
        "categories": ["type_mismatch", "incomplete_branch"],
        "description": "May detect adjacency or other validation issues",
    },
}


async def test_single_function(func_name: str, prompt: str, num_samples: int = 1) -> dict:
    """Generate IRs and test with IR Interpreter."""
    print("\n" + "=" * 80)
    print(f"Testing: {func_name}")
    print("=" * 80)
    print(f"Prompt: {prompt}\n")
    print(f"Expected issues: {EXPECTED_ISSUES[func_name]['description']}\n")

    # Initialize provider and translator
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    translator = XGrammarIRTranslator(provider)
    interpreter = IRInterpreter()

    # Results tracking
    results = {
        "test_name": func_name,
        "num_samples": num_samples,
        "detected": 0,
        "total": 0,
        "error_categories": Counter(),
        "warning_categories": Counter(),
        "samples": [],
    }

    # Generate multiple IR samples with different temperatures
    for i in range(num_samples):
        temperature = 0.3 + (i * 0.15)  # 0.3, 0.45, 0.6, 0.75, 0.9
        temperature = min(temperature, 0.9)

        print(f"  Sample {i + 1}/{num_samples} (temperature: {temperature:.2f})...")

        try:
            # Generate IR (translator doesn't support temperature parameter)
            ir = await translator.translate(prompt)

            # Interpret IR
            interpretation = interpreter.interpret(ir)

            results["total"] += 1

            # Check if appropriate errors detected
            expected_categories = EXPECTED_ISSUES[func_name]["categories"]
            has_expected_error = any(
                e.category in expected_categories for e in interpretation.errors
            )

            if has_expected_error or interpretation.has_errors():
                results["detected"] += 1

            # Track categories
            for error in interpretation.errors:
                results["error_categories"][error.category] += 1

            for warning in interpretation.warnings:
                results["warning_categories"][warning.category] += 1

            # Store sample details
            sample = {
                "sample_num": i,
                "temperature": temperature,
                "has_errors": interpretation.has_errors(),
                "has_warnings": interpretation.has_warnings(),
                "num_errors": len(interpretation.errors),
                "num_warnings": len(interpretation.warnings),
                "error_categories": [e.category for e in interpretation.errors],
                "warning_categories": [w.category for w in interpretation.warnings],
                "errors": [
                    {"category": e.category, "message": e.message} for e in interpretation.errors
                ],
                "warnings": [
                    {"category": w.category, "message": w.message} for w in interpretation.warnings
                ],
            }
            results["samples"].append(sample)

            # Print summary for this sample
            if interpretation.has_errors():
                print(
                    f"    ❌ {len(interpretation.errors)} error(s), "
                    f"{len(interpretation.warnings)} warning(s)"
                )
                for error in interpretation.errors[:2]:
                    print(f"       • [{error.category}] {error.message[:60]}...")
            elif interpretation.has_warnings():
                print(f"    ⚠️  {len(interpretation.warnings)} warning(s)")
            else:
                print("    ✅ No issues detected")

        except Exception as e:
            print(f"    ❌ Error generating/interpreting IR: {e}")
            results["samples"].append(
                {
                    "sample_num": i,
                    "temperature": temperature,
                    "error": str(e),
                }
            )

    # Calculate detection rate
    detection_rate = (results["detected"] / results["total"] * 100) if results["total"] > 0 else 0

    print(f"\n📊 Detection Rate: {detection_rate:.1f}% ({results['detected']}/{results['total']})")
    if results["error_categories"]:
        print("  Error categories:")
        for category, count in results["error_categories"].most_common(3):
            print(f"    • {category}: {count}")
    if results["warning_categories"]:
        print("  Warning categories:")
        for category, count in results["warning_categories"].most_common(3):
            print(f"    • {category}: {count}")

    results["detection_rate"] = detection_rate
    return results


async def main():
    """Test all 3 persistent failures."""
    print("\n" + "=" * 80)
    print("Testing IR Interpreter on 3 Persistent Failures")
    print("=" * 80)
    print("\nGoal: Measure how well IR Interpreter detects semantic errors")
    print("before code generation.\n")

    all_results = {}

    for func_name, prompt in TEST_PROMPTS.items():
        try:
            results = await test_single_function(func_name, prompt, num_samples=1)
            all_results[func_name] = results
        except Exception as e:
            print(f"\n❌ {func_name} failed with error: {e}")
            import traceback

            traceback.print_exc()
            all_results[func_name] = {"error": str(e)}

    # Generate markdown report
    report_lines = [
        "# IR Interpreter Validation Results",
        "",
        "Testing on 3 persistent failures from Phase 3 benchmarks.",
        "",
        "## Summary",
        "",
        "| Test | Detection Rate | Samples | Top Error Category |",
        "| ---- | -------------- | ------- | ------------------ |",
    ]

    for func_name, results in all_results.items():
        if "error" in results:
            report_lines.append(f"| {func_name} | ERROR | - | {results['error'][:30]} |")
        else:
            top_category = (
                results["error_categories"].most_common(1)[0][0]
                if results["error_categories"]
                else "N/A"
            )
            report_lines.append(
                f"| {func_name} | {results['detection_rate']:.1f}% | "
                f"{results['total']} | {top_category} |"
            )

    report_lines.extend(
        [
            "",
            "## Detailed Results",
            "",
        ]
    )

    for func_name, results in all_results.items():
        if "error" in results:
            report_lines.extend(
                [
                    f"### {func_name}",
                    "",
                    f"**Error**: {results['error']}",
                    "",
                ]
            )
            continue

        report_lines.extend(
            [
                f"### {func_name}",
                "",
                f"**Expected**: {EXPECTED_ISSUES[func_name]['description']}",
                "",
                f"**Detection Rate**: {results['detection_rate']:.1f}% ({results['detected']}/{results['total']})",
                "",
            ]
        )

        if results["error_categories"]:
            report_lines.append("**Errors Detected**:")
            report_lines.append("")
            for category, count in results["error_categories"].most_common():
                report_lines.append(f"- `{category}`: {count} sample(s)")
            report_lines.append("")

        if results["warning_categories"]:
            report_lines.append("**Warnings Detected**:")
            report_lines.append("")
            for category, count in results["warning_categories"].most_common():
                report_lines.append(f"- `{category}`: {count} sample(s)")
            report_lines.append("")

        # Sample details
        report_lines.append("<details>")
        report_lines.append("<summary>Sample Details</summary>")
        report_lines.append("")
        for sample in results["samples"]:
            if "error" in sample:
                report_lines.append(
                    f"- Sample {sample['sample_num']} (temp {sample['temperature']:.2f}): "
                    f"ERROR - {sample['error']}"
                )
            else:
                status = (
                    "ERRORS"
                    if sample["has_errors"]
                    else ("WARNINGS" if sample["has_warnings"] else "CLEAN")
                )
                report_lines.append(
                    f"- Sample {sample['sample_num']} (temp {sample['temperature']:.2f}): {status}"
                )
                if sample["errors"]:
                    for error in sample["errors"]:
                        report_lines.append(f"  - [{error['category']}] {error['message'][:60]}...")
        report_lines.append("")
        report_lines.append("</details>")
        report_lines.append("")

    # Add recommendations
    report_lines.extend(
        [
            "## Recommendations",
            "",
        ]
    )

    avg_detection = sum(
        r.get("detection_rate", 0) for r in all_results.values() if "detection_rate" in r
    ) / len(all_results)

    if avg_detection > 70:
        report_lines.extend(
            [
                f"✅ **Strong Performance**: Average detection rate of {avg_detection:.1f}%",
                "",
                "The IR Interpreter is effectively catching semantic errors before code generation.",
                "This should reduce failed code generation attempts and improve overall success rate.",
                "",
            ]
        )
    elif avg_detection > 40:
        report_lines.extend(
            [
                f"⚠️  **Moderate Performance**: Average detection rate of {avg_detection:.1f}%",
                "",
                "The IR Interpreter catches some errors but misses others. Consider:",
                "- Adding more specific validation rules for common patterns",
                "- Improving effect chain parsing to capture more semantics",
                "- Adding constraint-specific validators",
                "",
            ]
        )
    else:
        report_lines.extend(
            [
                f"❌ **Low Performance**: Average detection rate of {avg_detection:.1f}%",
                "",
                "The IR Interpreter is not catching most semantic errors. Consider:",
                "- Reviewing IR generation quality - are effects too vague?",
                "- Adding more aggressive validation rules",
                "- Using constraint information from IR metadata",
                "",
            ]
        )

    # Write report
    report_path = Path("VALIDATION_RESULTS_3_FAILURES.md")
    report_path.write_text("\n".join(report_lines))

    # Also save JSON for programmatic analysis
    json_path = Path("validation_results_3_failures.json")
    json_path.write_text(json.dumps(all_results, indent=2))

    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    for func_name, results in all_results.items():
        if "detection_rate" in results:
            print(
                f"  {func_name}: {results['detection_rate']:.1f}% "
                f"({results['detected']}/{results['total']} samples)"
            )

    print(f"\n📝 Report saved to: {report_path}")
    print(f"📊 Data saved to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
