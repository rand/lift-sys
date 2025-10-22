#!/usr/bin/env python3
"""Generate structured robustness report from test results.

This script parses robustness test output and generates JSON/Markdown reports
for use in CI/CD pipelines and documentation.

Usage:
    python scripts/robustness/generate_report.py --input results.txt --format json
    python scripts/robustness/generate_report.py --input results.txt --format markdown
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RobustnessMetrics:
    """Robustness test metrics."""

    timestamp: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    average_robustness: float | None
    average_sensitivity: float | None
    quality_gate_status: str  # "passed", "warning", "failed"
    quality_gate_message: str


@dataclass
class TestResult:
    """Individual test result."""

    name: str
    status: str  # "PASSED", "FAILED", "SKIPPED"
    robustness: float | None
    sensitivity: float | None
    variants_tested: int | None


def parse_test_output(output_file: Path) -> tuple[RobustnessMetrics, list[TestResult]]:
    """Parse pytest output to extract robustness metrics.

    Args:
        output_file: Path to pytest output file

    Returns:
        Tuple of (overall metrics, individual test results)
    """
    with open(output_file) as f:
        content = f.read()

    # Count test results
    passed = len(re.findall(r"PASSED", content))
    failed = len(re.findall(r"FAILED", content))
    skipped = len(re.findall(r"SKIPPED", content))
    total = passed + failed + skipped

    # Calculate pass rate
    pass_rate = (passed / total * 100) if total > 0 else 0.0

    # Extract robustness scores
    robustness_scores = []
    sensitivity_scores = []

    # Look for patterns like "Robustness: 95.00%"
    for match in re.finditer(r"Robustness:\s*(\d+\.\d+)%", content):
        robustness_scores.append(float(match.group(1)))

    # Look for patterns like "Sensitivity: 5.00%"
    for match in re.finditer(r"Sensitivity:\s*(\d+\.\d+)%", content):
        sensitivity_scores.append(float(match.group(1)))

    # Calculate averages
    avg_robustness = sum(robustness_scores) / len(robustness_scores) if robustness_scores else None
    avg_sensitivity = (
        sum(sensitivity_scores) / len(sensitivity_scores) if sensitivity_scores else None
    )

    # Determine quality gate status
    warn_threshold = 90.0
    fail_threshold = 80.0

    if pass_rate < fail_threshold:
        status = "failed"
        message = (
            f"❌ CRITICAL: Pass rate {pass_rate:.1f}% below failure threshold {fail_threshold}%"
        )
    elif pass_rate < warn_threshold:
        status = "warning"
        message = (
            f"⚠️  WARNING: Pass rate {pass_rate:.1f}% below warning threshold {warn_threshold}%"
        )
    else:
        status = "passed"
        message = f"✅ PASSED: Robustness tests meet quality standards ({pass_rate:.1f}%)"

    metrics = RobustnessMetrics(
        timestamp=datetime.now().isoformat(),
        total_tests=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        pass_rate=pass_rate,
        average_robustness=avg_robustness,
        average_sensitivity=avg_sensitivity,
        quality_gate_status=status,
        quality_gate_message=message,
    )

    # Parse individual test results (simplified - would need more complex parsing for full details)
    test_results = []

    # Extract test names and statuses from pytest output
    test_pattern = r"tests/robustness/(\S+)::\S+\s+(PASSED|FAILED|SKIPPED)"
    for match in re.finditer(test_pattern, content):
        test_name = match.group(1)
        status_str = match.group(2)

        # Try to find robustness score for this test (simplified)
        result = TestResult(
            name=test_name,
            status=status_str,
            robustness=None,  # Would need more context to associate scores with tests
            sensitivity=None,
            variants_tested=None,
        )
        test_results.append(result)

    return metrics, test_results


def generate_json_report(
    metrics: RobustnessMetrics, test_results: list[TestResult]
) -> dict[str, Any]:
    """Generate JSON report.

    Args:
        metrics: Overall robustness metrics
        test_results: Individual test results

    Returns:
        JSON-serializable dictionary
    """
    return {
        "metrics": asdict(metrics),
        "test_results": [asdict(r) for r in test_results],
    }


def generate_markdown_report(metrics: RobustnessMetrics, test_results: list[TestResult]) -> str:
    """Generate Markdown report.

    Args:
        metrics: Overall robustness metrics
        test_results: Individual test results

    Returns:
        Markdown-formatted string
    """
    status_emoji = {
        "passed": "✅",
        "warning": "⚠️",
        "failed": "❌",
    }

    md = f"""# Robustness Testing Report

**Generated**: {metrics.timestamp}

## {status_emoji.get(metrics.quality_gate_status, "❓")} Overall Status

{metrics.quality_gate_message}

## Test Results Summary

| Metric | Value |
|--------|-------|
| Total Tests | {metrics.total_tests} |
| Passed | {metrics.passed} |
| Failed | {metrics.failed} |
| Skipped | {metrics.skipped} |
| Pass Rate | {metrics.pass_rate:.1f}% |
"""

    if metrics.average_robustness is not None:
        md += f"| Average Robustness | {metrics.average_robustness:.2f}% |\n"

    if metrics.average_sensitivity is not None:
        md += f"| Average Sensitivity | {metrics.average_sensitivity:.2f}% |\n"

    md += """
## Quality Gates

- ✅ **Target**: Pass rate ≥ 90%, Robustness ≥ 97% (<3% sensitivity)
- ⚠️  **Warning**: Pass rate < 90%
- ❌ **Failure**: Pass rate < 80%

## Methodology

Robustness tests follow the **TokDrift** methodology (arXiv:2510.14972):
- Semantic-preserving transformations (paraphrases, IR variants)
- Equivalence checking for outputs
- Statistical validation (Wilcoxon signed-rank test)

**Target sensitivity**: <3% (system should be robust to formatting variations)

## Individual Test Results

"""

    if test_results:
        md += "| Test | Status |\n"
        md += "|------|--------|\n"
        for result in test_results:
            status_icon = {
                "PASSED": "✅",
                "FAILED": "❌",
                "SKIPPED": "⏭️",
            }.get(result.status, "❓")
            md += f"| {result.name} | {status_icon} {result.status} |\n"
    else:
        md += "*No individual test results parsed*\n"

    md += """
## Next Steps

"""

    if metrics.quality_gate_status == "failed":
        md += """
- **CRITICAL**: Investigate failed tests immediately
- Review test output for specific failure reasons
- Consider rolling back changes that degraded robustness
"""
    elif metrics.quality_gate_status == "warning":
        md += """
- **WARNING**: Some tests are failing or sensitivity is elevated
- Review failing tests to understand robustness issues
- Consider improvements to reduce sensitivity
"""
    else:
        md += """
- ✅ All quality gates passed
- Continue monitoring robustness in future changes
- Consider updating baseline if this represents improvement
"""

    return md


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate robustness report from test output")
    parser.add_argument(
        "--input", "-i", type=Path, required=True, help="Path to pytest output file"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--output", "-o", type=Path, help="Output file (default: stdout)")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Parse test output
    metrics, test_results = parse_test_output(args.input)

    # Generate report
    if args.format == "json":
        report = generate_json_report(metrics, test_results)
        output = json.dumps(report, indent=2)
    else:  # markdown
        output = generate_markdown_report(metrics, test_results)

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"Report written to: {args.output}")
    else:
        print(output)

    # Exit with appropriate code based on quality gate
    if metrics.quality_gate_status == "failed":
        sys.exit(1)
    elif metrics.quality_gate_status == "warning":
        sys.exit(0)  # Don't fail on warnings
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
