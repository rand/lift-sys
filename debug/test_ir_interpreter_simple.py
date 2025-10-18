#!/usr/bin/env python3
"""Test IR Interpreter on manually created IRs for the 3 failures."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.validation.ir_interpreter import IRInterpreter


def create_count_words_ir() -> IntermediateRepresentation:
    """Create IR for count_words - should have missing return."""
    return IntermediateRepresentation(
        intent=IntentClause(
            summary="Count the number of words in a string",
            rationale=None,
        ),
        signature=SigClause(
            name="count_words",
            parameters=[Parameter(name="text", type_hint="str")],
            returns="int",
        ),
        effects=[
            EffectClause(description="Split the text by spaces into words"),
            EffectClause(description="Count the number of words"),
            # Missing: Return the count
        ],
    )


def create_find_index_ir() -> IntermediateRepresentation:
    """Create IR for find_index - should have loop behavior issue."""
    return IntermediateRepresentation(
        intent=IntentClause(
            summary="Find the first index of a value in a list",
            rationale=None,
        ),
        signature=SigClause(
            name="find_index",
            parameters=[
                Parameter(name="items", type_hint="list"),
                Parameter(name="target", type_hint="Any"),
            ],
            returns="int",
        ),
        effects=[
            EffectClause(description="Use enumerate to iterate through the items list"),
            EffectClause(description="If current item equals target, return the index immediately"),
            EffectClause(description="After loop ends, return -1"),
        ],
    )


def create_is_valid_email_ir() -> IntermediateRepresentation:
    """Create IR for is_valid_email - may have various issues."""
    return IntermediateRepresentation(
        intent=IntentClause(
            summary="Check if a string is a valid email address",
            rationale=None,
        ),
        signature=SigClause(
            name="is_valid_email",
            parameters=[Parameter(name="email", type_hint="str")],
            returns="bool",
        ),
        effects=[
            EffectClause(description="Check if email contains @ symbol"),
            EffectClause(description="Check if there is a dot after @"),
            EffectClause(description="Return True if both conditions are met"),
            # Missing: else branch for False case
        ],
    )


def test_ir(name: str, ir: IntermediateRepresentation, expected_categories: list[str]):
    """Test a single IR."""
    print("\n" + "=" * 80)
    print(f"Testing: {name}")
    print("=" * 80)

    print("\nIR Details:")
    print(f"  Function: {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)})")
    print(f"  Returns: {ir.signature.returns}")
    print(f"  Effects: {len(ir.effects)}")
    for i, effect in enumerate(ir.effects):
        print(f"    {i + 1}. {effect.description}")

    # Interpret IR
    interpreter = IRInterpreter()
    result = interpreter.interpret(ir)

    print("\n" + str(result))

    # Check detection
    detected_categories = {e.category for e in result.errors}
    expected_set = set(expected_categories)

    if detected_categories & expected_set:
        print(f"\n✅ DETECTED expected issue(s): {detected_categories & expected_set}")
    else:
        print(f"\n⚠️  Did not detect expected categories: {expected_set}")
        if detected_categories:
            print(f"   But found other errors: {detected_categories}")

    return {
        "name": name,
        "has_errors": result.has_errors(),
        "has_warnings": result.has_warnings(),
        "num_errors": len(result.errors),
        "num_warnings": len(result.warnings),
        "error_categories": list(detected_categories),
        "warning_categories": [w.category for w in result.warnings],
        "expected_categories": expected_categories,
        "detected_expected": bool(detected_categories & expected_set),
    }


def main():
    """Test all 3 cases."""
    print("\n" + "=" * 80)
    print("Testing IR Interpreter on 3 Persistent Failures (Manual IRs)")
    print("=" * 80)

    tests = [
        ("count_words", create_count_words_ir(), ["missing_return", "implicit_return"]),
        ("find_index", create_find_index_ir(), ["loop_behavior", "missing_return_path"]),
        (
            "is_valid_email",
            create_is_valid_email_ir(),
            ["incomplete_branch", "missing_return_path"],
        ),
    ]

    results = []
    for name, ir, expected in tests:
        try:
            result = test_ir(name, ir, expected)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {name}: {e}")
            import traceback

            traceback.print_exc()
            results.append({"name": name, "error": str(e)})

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for result in results:
        if "error" in result:
            print(f"  {result['name']}: ❌ ERROR - {result['error']}")
        else:
            status = "✅" if result["detected_expected"] else "⚠️ "
            print(
                f"  {result['name']}: {status} "
                f"{result['num_errors']} error(s), {result['num_warnings']} warning(s)"
            )
            if result["detected_expected"]:
                detected = set(result["error_categories"]) & set(result["expected_categories"])
                print(f"     Detected: {', '.join(detected)}")
            else:
                print(f"     Expected: {', '.join(result['expected_categories'])}")
                if result["error_categories"]:
                    print(f"     Got: {', '.join(result['error_categories'])}")

    # Generate markdown report
    report_lines = [
        "# IR Interpreter Validation Results (Manual IRs)",
        "",
        "Testing IR Interpreter on manually created IRs for the 3 persistent failures.",
        "",
        "## Summary",
        "",
        "| Test | Errors | Warnings | Expected Detected | Categories Found |",
        "| ---- | ------ | -------- | ----------------- | ---------------- |",
    ]

    for result in results:
        if "error" in result:
            report_lines.append(f"| {result['name']} | ERROR | - | - | - |")
        else:
            detected = "✅ Yes" if result["detected_expected"] else "❌ No"
            categories = (
                ", ".join(result["error_categories"]) if result["error_categories"] else "None"
            )
            report_lines.append(
                f"| {result['name']} | {result['num_errors']} | {result['num_warnings']} | "
                f"{detected} | {categories} |"
            )

    report_lines.extend(
        [
            "",
            "## Test Details",
            "",
        ]
    )

    for result in results:
        if "error" in result:
            continue

        report_lines.extend(
            [
                f"### {result['name']}",
                "",
                f"**Expected categories**: {', '.join(result['expected_categories'])}",
                "",
                f"**Detected**: {result['detected_expected']}",
                "",
            ]
        )

        if result["error_categories"]:
            report_lines.append("**Error categories found**:")
            for cat in result["error_categories"]:
                report_lines.append(f"- `{cat}`")
            report_lines.append("")

        if result["warning_categories"]:
            report_lines.append("**Warning categories found**:")
            for cat in result["warning_categories"]:
                report_lines.append(f"- `{cat}`")
            report_lines.append("")

    # Calculate detection rate
    detected_count = sum(1 for r in results if r.get("detected_expected", False))
    total = len(results)
    detection_rate = (detected_count / total * 100) if total > 0 else 0

    report_lines.extend(
        [
            "## Overall Performance",
            "",
            f"**Detection Rate**: {detection_rate:.1f}% ({detected_count}/{total} tests)",
            "",
        ]
    )

    if detection_rate >= 66:
        report_lines.extend(
            [
                "✅ **Good Performance**: The IR Interpreter successfully detects most semantic errors.",
                "",
                "This validates the Phase 5 approach - catching errors at IR interpretation",
                "time before expensive code generation.",
                "",
            ]
        )
    elif detection_rate >= 33:
        report_lines.extend(
            [
                "⚠️  **Moderate Performance**: The IR Interpreter catches some but not all errors.",
                "",
                "Consider refining validation rules to better match the 3 failure patterns.",
                "",
            ]
        )
    else:
        report_lines.extend(
            [
                "❌ **Needs Improvement**: The IR Interpreter is missing most errors.",
                "",
                "The validation rules may need to be more specific to the failure patterns,",
                "or the IRs may need more detailed effects to enable detection.",
                "",
            ]
        )

    # Write report
    report_path = Path("VALIDATION_RESULTS_3_FAILURES.md")
    report_path.write_text("\n".join(report_lines))

    print(f"\n📝 Report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
