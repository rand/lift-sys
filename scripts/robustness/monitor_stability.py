#!/usr/bin/env python3
"""Monitor robustness workflow stability and recommend Phase 5b timing.

This script tracks robustness test pass rates over time and provides
recommendations on when to proceed with full quality gate tightening (Phase 5b).

Usage:
    python scripts/robustness/monitor_stability.py [--limit N] [--json]

Requirements:
    - gh CLI must be installed and authenticated
    - Run from repository root

Phase 5 Context:
    - Phase 5a (Current): Modest tightening (warn threshold 88%)
    - Phase 5b (Future): Full tightening (warn 92%, fail 85%)
    - Criteria: Need 20+ successful runs at 100% pass rate
"""

import json
import subprocess
import sys


def get_workflow_runs(limit: int = 30) -> list[dict]:
    """Fetch recent robustness workflow runs using gh CLI."""
    cmd = [
        "gh",
        "run",
        "list",
        "--workflow=robustness.yml",
        f"--limit={limit}",
        "--json",
        "conclusion,displayTitle,databaseId,createdAt,status",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def parse_test_results(run_id: int) -> dict | None:
    """Parse test results from workflow run logs."""
    import re

    cmd = ["gh", "run", "view", str(run_id), "--log"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log = result.stdout

        # Look for Quality Gate Check output
        if "Quality Gate Check:" not in log:
            return None

        # Extract metrics (strip ANSI color codes)
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        passed = None
        failed = None
        pass_rate = None

        for line in log.split("\n"):
            # Remove ANSI codes
            clean_line = ansi_escape.sub("", line)

            if "Tests Passed:" in clean_line:
                value = clean_line.split(":")[-1].strip()
                try:
                    passed = int(value)
                except ValueError:
                    pass
            elif "Tests Failed:" in clean_line:
                value = clean_line.split(":")[-1].strip()
                try:
                    failed = int(value)
                except ValueError:
                    pass
            elif "Pass Rate:" in clean_line:
                # Extract pass rate percentage
                rate_str = clean_line.split(":")[-1].strip().replace("%", "")
                try:
                    pass_rate = float(rate_str)
                except ValueError:
                    pass

        if passed is not None and failed is not None and pass_rate is not None:
            return {"passed": passed, "failed": failed, "pass_rate": pass_rate}
    except subprocess.CalledProcessError:
        pass

    return None


def calculate_stability_metrics(runs: list[dict]) -> dict:
    """Calculate stability metrics from workflow runs.

    Returns:
        dict with:
        - total_runs: Total runs analyzed
        - runs_at_100: Number of runs at 100% pass rate
        - consecutive_100: Longest streak of 100% runs
        - avg_pass_rate: Average pass rate across all runs
        - stability_score: Percentage of runs at 100%
        - recommendation: Whether to proceed with Phase 5b
    """
    runs_at_100 = 0
    max_consecutive = 0
    current_consecutive = 0
    total_pass_rate = 0.0
    valid_runs = 0

    for run in runs:
        if run["conclusion"] == "success":
            results = parse_test_results(run["databaseId"])
            if results:
                valid_runs += 1
                pass_rate = results["pass_rate"]
                total_pass_rate += pass_rate

                if pass_rate == 100.0:
                    runs_at_100 += 1
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0

    avg_pass_rate = total_pass_rate / valid_runs if valid_runs > 0 else 0.0
    stability_score = (runs_at_100 / valid_runs * 100) if valid_runs > 0 else 0.0

    # Recommendation logic
    recommendation = "NOT_READY"
    reason = ""

    if valid_runs < 20:
        recommendation = "NOT_READY"
        reason = f"Need 20+ runs, currently have {valid_runs}"
    elif runs_at_100 < 20:
        recommendation = "NOT_READY"
        reason = f"Need 20+ runs at 100%, currently have {runs_at_100}"
    elif max_consecutive < 10:
        recommendation = "CAUTION"
        reason = f"Max consecutive 100% runs is {max_consecutive}, prefer 10+"
    else:
        recommendation = "READY"
        reason = "Sufficient stability demonstrated for Phase 5b"

    return {
        "total_runs": valid_runs,
        "runs_at_100": runs_at_100,
        "consecutive_100": max_consecutive,
        "avg_pass_rate": avg_pass_rate,
        "stability_score": stability_score,
        "recommendation": recommendation,
        "reason": reason,
    }


def print_report(metrics: dict, runs: list[dict], json_output: bool = False):
    """Print stability report."""
    if json_output:
        print(json.dumps(metrics, indent=2))
        return

    print("=" * 70)
    print("ROBUSTNESS WORKFLOW STABILITY REPORT")
    print("=" * 70)
    print()

    print(f"📊 Analysis Period: Last {len(runs)} workflow runs")
    print(f"   Analyzed: {metrics['total_runs']} runs with valid results")
    print()

    print("📈 Stability Metrics:")
    print(f"   Runs at 100% Pass Rate: {metrics['runs_at_100']}/{metrics['total_runs']}")
    print(f"   Stability Score: {metrics['stability_score']:.1f}%")
    print(f"   Average Pass Rate: {metrics['avg_pass_rate']:.1f}%")
    print(f"   Max Consecutive 100%: {metrics['consecutive_100']} runs")
    print()

    print("🎯 Phase 5b Readiness:")
    print(f"   Status: {metrics['recommendation']}")
    print(f"   Reason: {metrics['reason']}")
    print()

    # Criteria table
    print("📋 Phase 5b Criteria:")
    criteria = [
        ("Total Runs", metrics["total_runs"], 20, ">="),
        ("Runs at 100%", metrics["runs_at_100"], 20, ">="),
        ("Max Consecutive 100%", metrics["consecutive_100"], 10, ">="),
        ("Stability Score", f"{metrics['stability_score']:.0f}%", "90%", ">="),
    ]

    print("   ┌─────────────────────────┬─────────┬──────────┬────────┐")
    print("   │ Criterion               │ Current │ Target   │ Status │")
    print("   ├─────────────────────────┼─────────┼──────────┼────────┤")

    for name, current, target, _op in criteria:
        # Determine status
        if name == "Stability Score":
            current_val = metrics["stability_score"]
            target_val = 90
            status = "✅" if current_val >= target_val else "⏳"
        else:
            status = "✅" if current >= target else "⏳"

        print(f"   │ {name:<23} │ {str(current):>7} │ {str(target):>8} │ {status:^6} │")

    print("   └─────────────────────────┴─────────┴──────────┴────────┘")
    print()

    # Recommendations
    if metrics["recommendation"] == "READY":
        print("🚀 READY FOR PHASE 5b!")
        print()
        print("   You can now proceed with full quality gate tightening:")
        print("   - Warning threshold: 88% → 92%")
        print("   - Failure threshold: 80% → 85%")
        print()
        print("   Next steps:")
        print("   1. Review recent workflow runs for any anomalies")
        print("   2. Update .github/workflows/robustness.yml")
        print("   3. Document Phase 5b completion")
    elif metrics["recommendation"] == "CAUTION":
        print("⚠️  CAUTION: Close to ready, but recommend more data")
        print()
        print(f"   {metrics['reason']}")
        print()
        print("   Consider waiting for more consecutive successful runs")
        print("   to ensure stability across different conditions.")
    else:
        print("⏳ NOT READY: Need more stability data")
        print()
        print(f"   {metrics['reason']}")
        print()
        remaining = 20 - metrics["total_runs"]
        print(f"   Estimated: ~{remaining} more runs needed")
        print(f"   At 2-3 runs/day: ~{remaining // 2}-{remaining} days")

    print()
    print("=" * 70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor robustness workflow stability for Phase 5b readiness"
    )
    parser.add_argument(
        "--limit", type=int, default=30, help="Number of recent runs to analyze (default: 30)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON format instead of human-readable report"
    )

    args = parser.parse_args()

    try:
        # Fetch workflow runs
        runs = get_workflow_runs(args.limit)

        if not runs:
            print("❌ No workflow runs found", file=sys.stderr)
            sys.exit(1)

        # Calculate metrics
        metrics = calculate_stability_metrics(runs)

        # Print report
        print_report(metrics, runs, args.json)

        # Exit code based on recommendation
        if metrics["recommendation"] == "READY":
            sys.exit(0)
        else:
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"❌ Error running gh CLI: {e}", file=sys.stderr)
        print("   Ensure gh CLI is installed and authenticated", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
