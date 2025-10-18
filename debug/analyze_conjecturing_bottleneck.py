"""
Bottleneck Analysis for Conjecturing Framework Phase 1.

Analyzes diagnostic samples to determine if the bottleneck is in:
1. Conjecturing (IR generation) - IR missing/incomplete constraints
2. Formalization (code generation) - Code doesn't honor IR constraints
3. Neither - Different problem

Generates DIAGNOSTIC_REPORT_CONJECTURING.md with recommendation.

Run with: PYTHONPATH=/Users/rand/src/lift-sys uv run python debug/analyze_conjecturing_bottleneck.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_diagnostic_samples(diagnostics_dir: Path) -> dict[str, Any]:
    """Load all diagnostic sample files."""
    samples_by_test = {}

    for json_file in diagnostics_dir.glob("*_samples.json"):
        with open(json_file) as f:
            data = json.load(f)
            test_name = data["test_name"]
            samples_by_test[test_name] = data

    return samples_by_test


def analyze_bottleneck(samples_by_test: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze samples to determine bottleneck.

    Returns:
        Dictionary with analysis results and recommendation
    """
    analysis = {
        "per_test": {},
        "overall": {},
        "recommendation": "",
    }

    all_completeness = []
    all_preservation = []

    for test_name, data in samples_by_test.items():
        summary = data.get("summary", {})

        # Extract metrics
        completeness = summary.get("avg_conjecture_completeness", 0.0)
        preservation = summary.get("avg_constraint_preservation", 0.0)
        pass_rate = summary.get("pass_rate", 0.0)
        num_samples = summary.get("total_samples", 0)

        all_completeness.append(completeness)
        all_preservation.append(preservation)

        # Determine bottleneck for this test
        bottleneck = "unknown"
        confidence = "low"

        if completeness < 0.8:
            bottleneck = "conjecturing"
            confidence = "high" if completeness < 0.5 else "medium"
        elif preservation < 0.7:
            bottleneck = "formalization"
            confidence = "high" if preservation < 0.5 else "medium"
        elif completeness >= 0.8 and preservation >= 0.7:
            bottleneck = "other"
            confidence = "high"

        analysis["per_test"][test_name] = {
            "completeness": completeness,
            "preservation": preservation,
            "pass_rate": pass_rate,
            "num_samples": num_samples,
            "bottleneck": bottleneck,
            "confidence": confidence,
        }

    # Overall analysis
    avg_completeness = sum(all_completeness) / len(all_completeness) if all_completeness else 0.0
    avg_preservation = sum(all_preservation) / len(all_preservation) if all_preservation else 0.0

    analysis["overall"]["avg_completeness"] = avg_completeness
    analysis["overall"]["avg_preservation"] = avg_preservation

    # Overall recommendation
    if avg_completeness < 0.8:
        analysis["recommendation"] = "GO"
        analysis["rationale"] = (
            f"Conjecturing bottleneck detected (avg completeness: {avg_completeness:.1%}). "
            "IR is missing/incomplete constraints. Proceed to Phase 2 (Prompt Enhancement)."
        )
    elif avg_preservation < 0.7:
        analysis["recommendation"] = "NO-GO"
        analysis["rationale"] = (
            f"Formalization bottleneck detected (avg preservation: {avg_preservation:.1%}). "
            "IR has good constraints but code generation doesn't honor them. "
            "Focus on improving code generation templates/prompts instead of IR."
        )
    else:
        analysis["recommendation"] = "INVESTIGATE"
        analysis["rationale"] = (
            f"Both completeness ({avg_completeness:.1%}) and preservation ({avg_preservation:.1%}) "
            "are high, yet tests still fail. The bottleneck is likely elsewhere "
            "(e.g., test harness, edge case handling, semantic bugs)."
        )

    return analysis


def generate_report(analysis: dict[str, Any], output_path: Path):
    """Generate markdown diagnostic report."""
    report = []

    report.append("# Conjecturing Framework Phase 1 Diagnostic Report")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## Executive Summary")
    report.append("")
    report.append(f"**Recommendation:** {analysis['recommendation']}")
    report.append("")
    report.append(f"**Rationale:** {analysis['rationale']}")
    report.append("")

    report.append("## Overall Metrics")
    report.append("")
    overall = analysis["overall"]
    report.append(f"- **Average Conjecture Completeness:** {overall['avg_completeness']:.1%}")
    report.append(f"- **Average Constraint Preservation:** {overall['avg_preservation']:.1%}")
    report.append("")

    report.append("## Per-Test Analysis")
    report.append("")

    for test_name, metrics in analysis["per_test"].items():
        report.append(f"### {test_name}")
        report.append("")
        report.append(f"- **Samples:** {metrics['num_samples']}")
        report.append(f"- **Pass Rate:** {metrics['pass_rate']:.1%}")
        report.append(f"- **Conjecture Completeness:** {metrics['completeness']:.1%}")
        report.append(f"- **Constraint Preservation:** {metrics['preservation']:.1%}")
        report.append(
            f"- **Bottleneck:** {metrics['bottleneck']} (confidence: {metrics['confidence']})"
        )
        report.append("")

    report.append("## Interpretation Guide")
    report.append("")
    report.append("### Completeness Thresholds")
    report.append("- **< 50%:** Critical conjecturing failure - IR severely incomplete")
    report.append("- **50-80%:** Moderate conjecturing issue - IR missing some constraints")
    report.append("- **> 80%:** Good conjecturing - IR has most/all expected constraints")
    report.append("")
    report.append("### Preservation Thresholds")
    report.append("- **< 50%:** Critical formalization failure - code ignores IR constraints")
    report.append("- **50-70%:** Moderate formalization issue - code partially honors constraints")
    report.append("- **> 70%:** Good formalization - code respects IR constraints")
    report.append("")

    report.append("## Next Steps")
    report.append("")

    if analysis["recommendation"] == "GO":
        report.append("### Proceed to Phase 2: Prompt Enhancement")
        report.append("")
        report.append("The IR generation (conjecturing) is the bottleneck. Next steps:")
        report.append("")
        report.append("1. **Review IR samples** - Examine what constraints are being missed")
        report.append(
            "2. **Enhance prompts** - Add examples/instructions to improve constraint detection"
        )
        report.append(
            "3. **Test prompt variations** - Use temperature/prompt tweaks to improve completeness"
        )
        report.append(
            "4. **Measure improvement** - Re-run diagnostics to verify completeness increase"
        )
        report.append("")

    elif analysis["recommendation"] == "NO-GO":
        report.append("### DO NOT Proceed to Phase 2")
        report.append("")
        report.append("The code generation (formalization) is the bottleneck. Alternative actions:")
        report.append("")
        report.append(
            "1. **Review code generation templates** - Check if constraints are being passed correctly"
        )
        report.append(
            "2. **Improve code generation prompts** - Make constraint adherence more explicit"
        )
        report.append(
            "3. **Add constraint-aware patterns** - Build specific patterns for each constraint type"
        )
        report.append("4. **Consider post-processing** - Add validation/repair after generation")
        report.append("")

    else:  # INVESTIGATE
        report.append("### Investigate Root Cause")
        report.append("")
        report.append(
            "Neither conjecturing nor formalization appear to be the bottleneck. Investigate:"
        )
        report.append("")
        report.append("1. **Test harness issues** - Are tests actually testing the right thing?")
        report.append("2. **Semantic bugs** - Are there edge cases not covered by constraints?")
        report.append("3. **Edge case handling** - Review specific test failures for patterns")
        report.append("4. **Manual code review** - Inspect generated code to identify issues")
        report.append("")

    # Write report
    with open(output_path, "w") as f:
        f.write("\n".join(report))

    print(f"\n✓ Report written to {output_path}")


def main():
    """Run bottleneck analysis."""
    print("\n" + "=" * 80)
    print("Conjecturing Framework Phase 1: Bottleneck Analysis")
    print("=" * 80 + "\n")

    # Load diagnostic samples
    diagnostics_dir = Path("logs/conjecturing_diagnostics")
    if not diagnostics_dir.exists():
        print(f"✗ Diagnostics directory not found: {diagnostics_dir}")
        print("  Run collect_failure_samples.py first to generate diagnostic samples.")
        sys.exit(1)

    print(f"Loading samples from {diagnostics_dir}...")
    samples_by_test = load_diagnostic_samples(diagnostics_dir)

    if not samples_by_test:
        print("✗ No diagnostic samples found.")
        print("  Run collect_failure_samples.py first.")
        sys.exit(1)

    print(f"✓ Loaded {len(samples_by_test)} test sets")

    # Analyze bottleneck
    print("\nAnalyzing bottleneck...")
    analysis = analyze_bottleneck(samples_by_test)

    print(f"\n{'=' * 80}")
    print("ANALYSIS RESULTS")
    print(f"{'=' * 80}")
    print(f"\nRecommendation: {analysis['recommendation']}")
    print(f"Rationale: {analysis['rationale']}")
    print("\nOverall Metrics:")
    print(f"  - Avg Completeness: {analysis['overall']['avg_completeness']:.1%}")
    print(f"  - Avg Preservation: {analysis['overall']['avg_preservation']:.1%}")
    print()

    # Generate report
    report_path = Path("DIAGNOSTIC_REPORT_CONJECTURING.md")
    print("Generating report...")
    generate_report(analysis, report_path)

    print(f"\n{'=' * 80}")
    print("Analysis Complete")
    print(f"{'=' * 80}\n")
    print(f"Review {report_path} for full diagnostic report and recommendations.")
    print()


if __name__ == "__main__":
    main()
