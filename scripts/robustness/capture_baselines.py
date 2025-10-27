#!/usr/bin/env python3
"""Capture baseline robustness measurements and update expected_results.json.

This script:
1. Runs baseline measurement tests
2. Parses robustness scores from output
3. Updates expected_results.json with measured baselines

Usage:
    python scripts/robustness/capture_baselines.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def run_baseline_tests():
    """Run baseline measurement tests and capture output."""
    print("Running baseline measurement tests...")

    # Run only the baseline measurement tests (not regression tests)
    cmd = [
        "uv",
        "run",
        "pytest",
        "tests/robustness/test_baseline_robustness.py::TestBaselineRobustness::test_measure_paraphrase_baseline_simple_functions",
        "tests/robustness/test_baseline_robustness.py::TestBaselineRobustness::test_measure_ir_variant_baseline_naming",
        "-v",
        "-s",
        "--tb=short",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    print(f"Tests completed with return code: {result.returncode}")
    return result.stdout + result.stderr


def parse_robustness_scores(output):
    """Parse robustness scores from test output.

    Looks for patterns like:
    - "Baseline Paraphrase Robustness (Simple Functions): 95.00%"
    - "Baseline IR Variant Robustness (Naming): 100.00%"

    Returns:
        dict: Mapping of test categories to robustness scores
    """
    scores = {}

    # Pattern: "Baseline <Type> Robustness (<Category>): <score>%"
    pattern = r"Baseline (.+?) Robustness \((.+?)\): ([\d.]+)%"

    for match in re.finditer(pattern, output):
        test_type = match.group(1).strip()  # "Paraphrase" or "IR Variant"
        category = match.group(2).strip()  # "Simple Functions", "Naming", etc.
        score = float(match.group(3)) / 100.0  # Convert percentage to decimal

        print(f"Found: {test_type} - {category} = {score:.2%}")
        scores[(test_type, category)] = score

    return scores


def update_expected_results(scores, fixtures_dir):
    """Update expected_results.json with measured baselines.

    Args:
        scores: Dict of (test_type, category) -> robustness_score
        fixtures_dir: Path to fixtures directory
    """
    results_file = fixtures_dir / "expected_results.json"

    print(f"\nLoading {results_file}...")
    with open(results_file) as f:
        data = json.load(f)

    # Update paraphrase robustness baselines
    if ("Paraphrase", "Simple Functions") in scores:
        data["paraphrase_robustness"]["simple_functions"]["baseline"] = scores[
            ("Paraphrase", "Simple Functions")
        ]
        print(
            f"Updated paraphrase_robustness.simple_functions.baseline = {scores[('Paraphrase', 'Simple Functions')]:.2%}"
        )

    # Update IR variant robustness baselines
    if ("IR Variant", "Naming") in scores:
        data["ir_variant_robustness"]["naming_variants"]["baseline"] = scores[
            ("IR Variant", "Naming")
        ]
        print(
            f"Updated ir_variant_robustness.naming_variants.baseline = {scores[('IR Variant', 'Naming')]:.2%}"
        )

    # Update notes
    data["notes"]["last_updated"] = "Phase 4 baseline capture"
    data["notes"]["measured_at"] = "2025-10-27"

    # Write back to file with pretty formatting
    print(f"\nWriting updated baselines to {results_file}...")
    with open(results_file, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")  # Add trailing newline

    print("✅ Baselines updated successfully!")
    return data


def main():
    """Main entry point."""
    # Get fixtures directory
    repo_root = Path(__file__).parent.parent.parent
    fixtures_dir = repo_root / "tests" / "robustness" / "fixtures"

    if not fixtures_dir.exists():
        print(f"❌ Fixtures directory not found: {fixtures_dir}")
        sys.exit(1)

    try:
        # Run baseline tests
        output = run_baseline_tests()

        # Parse scores
        scores = parse_robustness_scores(output)

        if not scores:
            print("❌ No robustness scores found in test output")
            print("\n--- Test Output ---")
            print(output)
            sys.exit(1)

        # Update expected_results.json
        data = update_expected_results(scores, fixtures_dir)

        # Print summary
        print("\n" + "=" * 60)
        print("BASELINE SUMMARY")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print("=" * 60)

        print("\n✅ Phase 4: Baselines captured successfully!")
        print("\nNext steps:")
        print("1. Commit updated expected_results.json")
        print("2. Run regression tests to validate")
        print("3. Push to CI for validation")

    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 120 seconds")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
