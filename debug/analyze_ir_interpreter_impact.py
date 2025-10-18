"""Analyze IR Interpreter impact on success rate."""

import json
import sys
from pathlib import Path
from typing import Any


def load_latest_benchmark(pattern: str) -> tuple[Path, dict[str, Any]]:
    """Load the latest benchmark file matching pattern."""
    benchmark_dir = Path("benchmark_results")
    files = sorted(benchmark_dir.glob(pattern), reverse=True)

    if not files:
        raise FileNotFoundError(f"No benchmark files found matching {pattern}")

    latest_file = files[0]
    with open(latest_file) as f:
        data = json.load(f)

    return latest_file, data


def analyze_impact(baseline_file: str, validation_file: str) -> dict[str, Any]:
    """Compare baseline vs IR validation results."""

    try:
        baseline_path, baseline = load_latest_benchmark(baseline_file)
        print(f"Baseline: {baseline_path}")
    except FileNotFoundError as e:
        print(f"Error loading baseline: {e}")
        sys.exit(1)

    try:
        validation_path, validation = load_latest_benchmark(validation_file)
        print(f"With IR Validation: {validation_path}")
    except FileNotFoundError as e:
        print(f"Error loading validation results: {e}")
        sys.exit(1)

    # Extract summary statistics
    baseline_summary = baseline.get("summary", {})
    validation_summary = validation.get("summary", {})

    baseline_success = baseline_summary.get("overall_rate", 0.0)
    validation_success = validation_summary.get("overall_rate", 0.0)

    baseline_passed = baseline_summary.get("overall_success", 0)
    validation_passed = validation_summary.get("overall_success", 0)

    baseline_total = baseline_summary.get("total_tests", 0)
    validation_total = validation_summary.get("total_tests", 0)

    # Find newly passing and newly failing tests
    baseline_results = {r["test_name"]: r["success"] for r in baseline.get("results", [])}
    validation_results = {r["test_name"]: r["success"] for r in validation.get("results", [])}

    baseline_passing = {name for name, passed in baseline_results.items() if passed}
    validation_passing = {name for name, passed in validation_results.items() if passed}

    newly_passing = validation_passing - baseline_passing
    newly_failing = baseline_passing - validation_passing

    # Count IRs rejected by interpreter (if tracked)
    irs_rejected = 0
    # Note: This would require adding telemetry to ValidatedCodeGenerator
    # For now, we can infer from compilation failures

    # Generate report
    improvement = validation_success - baseline_success
    improvement_pct = improvement * 100

    report = {
        "baseline": {
            "file": str(baseline_path),
            "success_rate": baseline_success,
            "passed": baseline_passed,
            "total": baseline_total,
            "passing_tests": sorted(baseline_passing),
        },
        "with_ir_validation": {
            "file": str(validation_path),
            "success_rate": validation_success,
            "passed": validation_passed,
            "total": validation_total,
            "passing_tests": sorted(validation_passing),
        },
        "impact": {
            "improvement": improvement,
            "improvement_pct": improvement_pct,
            "newly_passing": sorted(newly_passing),
            "newly_failing": sorted(newly_failing),
            "irs_rejected": irs_rejected,
        },
        "analysis": {
            "meets_85_target": validation_success >= 0.85,
            "meets_90_target": validation_success >= 0.90,
            "recommendation": (
                "Phase 5 complete - success rate meets 85% target"
                if validation_success >= 0.85
                else "Continue to Phase 2 (Prompt Enhancement) - below 85% target"
            ),
        },
    }

    return report


def format_report(analysis: dict[str, Any]) -> str:
    """Format analysis as markdown report."""

    baseline = analysis["baseline"]
    validation = analysis["with_ir_validation"]
    impact = analysis["impact"]
    summary = analysis["analysis"]

    lines = [
        "# IR Interpreter Impact Analysis",
        "",
        "## Success Rate",
        "",
        f"- **Baseline**: {baseline['success_rate']:.1%} ({baseline['passed']}/{baseline['total']})",
        f"- **With IR Validation**: {validation['success_rate']:.1%} ({validation['passed']}/{validation['total']})",
        f"- **Improvement**: {impact['improvement']:+.1%} ({impact['improvement_pct']:+.1f} percentage points)",
        "",
        "## Test Results",
        "",
        "### Newly Passing Tests",
    ]

    if impact["newly_passing"]:
        for test in impact["newly_passing"]:
            lines.append(f"- {test}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "### Newly Failing Tests",
        ]
    )

    if impact["newly_failing"]:
        for test in impact["newly_failing"]:
            lines.append(f"- {test}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Baseline Tests",
            "",
            "### Passing",
        ]
    )

    for test in baseline["passing_tests"]:
        lines.append(f"- {test}")

    lines.extend(
        [
            "",
            "## IR Validation Tests",
            "",
            "### Passing",
        ]
    )

    for test in validation["passing_tests"]:
        lines.append(f"- {test}")

    lines.extend(
        [
            "",
            "## Analysis",
            "",
            f"- **Meets 85% Target**: {'✅ YES' if summary['meets_85_target'] else '❌ NO'}",
            f"- **Meets 90% Target**: {'✅ YES' if summary['meets_90_target'] else '❌ NO'}",
            "",
            "## Recommendation",
            "",
            f"{summary['recommendation']}",
            "",
            "## Files Analyzed",
            "",
            f"- Baseline: `{baseline['file']}`",
            f"- With IR Validation: `{validation['file']}`",
            "",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    # Default patterns to find latest files
    baseline_pattern = "nontrivial_phase2_20251017*.json"
    validation_pattern = "nontrivial_phase2_20251018*.json"

    # Allow override from command line
    if len(sys.argv) >= 2:
        baseline_pattern = sys.argv[1]
    if len(sys.argv) >= 3:
        validation_pattern = sys.argv[2]

    print("Analyzing IR Interpreter Impact...")
    print(f"Baseline pattern: {baseline_pattern}")
    print(f"Validation pattern: {validation_pattern}")
    print()

    # Run analysis
    analysis = analyze_impact(baseline_pattern, validation_pattern)

    # Generate markdown report
    report_md = format_report(analysis)

    # Save to file
    output_file = Path("PHASE_5_IR_INTERPRETER_RESULTS.md")
    output_file.write_text(report_md)

    # Also save JSON for programmatic access
    json_file = Path("PHASE_5_IR_INTERPRETER_RESULTS.json")
    json_file.write_text(json.dumps(analysis, indent=2))

    # Print report
    print(report_md)
    print()
    print(f"✅ Report saved to: {output_file}")
    print(f"✅ JSON saved to: {json_file}")
