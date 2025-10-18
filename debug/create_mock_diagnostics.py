"""
Create mock diagnostic samples for testing the bottleneck analysis.

This generates synthetic data matching the structure of real samples,
with realistic completeness and preservation scores to demonstrate
the bottleneck detection logic.
"""

import json
from datetime import datetime
from pathlib import Path


def create_mock_samples(test_name: str, scenario: str) -> dict:
    """
    Create mock diagnostic samples for a test.

    Scenarios:
    - "conjecturing_bottleneck": Low completeness, high preservation
    - "formalization_bottleneck": High completeness, low preservation
    - "both_good": High completeness, high preservation (but tests still fail)
    """

    if scenario == "conjecturing_bottleneck":
        # IR missing constraints, but code honors what's there
        completeness = 0.4  # 40% of expected constraints detected
        preservation = 0.85  # 85% of IR constraints are honored
        pass_rate = 0.17  # Low pass rate due to missing constraints

    elif scenario == "formalization_bottleneck":
        # IR has good constraints, but code ignores them
        completeness = 0.9  # 90% of expected constraints detected
        preservation = 0.5  # Only 50% of constraints honored in code
        pass_rate = 0.25  # Low pass rate due to constraint violations

    else:  # both_good
        # Both completeness and preservation high, yet tests fail
        completeness = 0.95
        preservation = 0.90
        pass_rate = 0.20  # Still failing due to other issues

    # Create 12 mock samples
    samples = []
    for i in range(12):
        sample = {
            "test_name": test_name,
            "sample_num": i,
            "temperature": 0.3 + (i % 5) * 0.15,
            "timestamp": datetime.now().isoformat(),
            "code": f"def {test_name}(x):\n    # Mock implementation\n    pass",
            "ast_parseable": True,
            "ast_repair_applied": i % 3 == 0,
            "constraint_violations": []
            if i % 3 == 0
            else [{"type": "RETURN", "severity": "error"}],
            "conjecture_completeness": completeness + (i % 12 - 6) * 0.05,  # Slight variation
            "constraint_preservation": preservation + (i % 12 - 6) * 0.03,  # Slight variation
            "tests_passed": 1 if i % 6 == 0 else 0,  # Most fail
            "test_results": [
                {"passed": i % 6 == 0, "expected": "result", "actual": "None"} for _ in range(5)
            ],
        }
        samples.append(sample)

    # Calculate summary
    total = len(samples)
    passing = sum(1 for s in samples if s["tests_passed"] >= 5)
    ast_repairs = sum(1 for s in samples if s["ast_repair_applied"])
    constraint_violations = sum(1 for s in samples if len(s["constraint_violations"]) > 0)

    avg_completeness = sum(s["conjecture_completeness"] for s in samples) / total
    avg_preservation = sum(s["constraint_preservation"] for s in samples) / total

    return {
        "test_name": test_name,
        "spec": {
            "prompt": f"Create a function that {test_name}",
            "test_cases": [],
            "expected_constraint": "MockConstraint",
        },
        "num_samples": total,
        "samples": samples,
        "summary": {
            "total_samples": total,
            "fully_passing": passing,
            "pass_rate": pass_rate,
            "ast_repair_triggered": ast_repairs,
            "ast_repair_rate": ast_repairs / total,
            "constraint_violations_detected": constraint_violations,
            "constraint_violation_rate": constraint_violations / total,
            "avg_conjecture_completeness": avg_completeness,
            "avg_constraint_preservation": avg_preservation,
        },
    }


def main():
    """Generate mock diagnostic data for all three test scenarios."""
    output_dir = Path("logs/conjecturing_diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("Creating Mock Diagnostic Samples")
    print("=" * 80 + "\n")

    # Scenario 1: count_words - conjecturing bottleneck
    print("Creating count_words (conjecturing bottleneck)...")
    data = create_mock_samples("count_words", "conjecturing_bottleneck")
    with open(output_dir / "count_words_samples.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Completeness: {data['summary']['avg_conjecture_completeness']:.1%}")
    print(f"  Preservation: {data['summary']['avg_constraint_preservation']:.1%}")
    print("  ✓ Saved")

    # Scenario 2: find_index - formalization bottleneck
    print("\nCreating find_index (formalization bottleneck)...")
    data = create_mock_samples("find_index", "formalization_bottleneck")
    with open(output_dir / "find_index_samples.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Completeness: {data['summary']['avg_conjecture_completeness']:.1%}")
    print(f"  Preservation: {data['summary']['avg_constraint_preservation']:.1%}")
    print("  ✓ Saved")

    # Scenario 3: is_valid_email - both good (other issue)
    print("\nCreating is_valid_email (both metrics good)...")
    data = create_mock_samples("is_valid_email", "both_good")
    with open(output_dir / "is_valid_email_samples.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Completeness: {data['summary']['avg_conjecture_completeness']:.1%}")
    print(f"  Preservation: {data['summary']['avg_constraint_preservation']:.1%}")
    print("  ✓ Saved")

    print("\n" + "=" * 80)
    print("Mock Diagnostic Samples Created")
    print("=" * 80)
    print(f"\nReview samples in {output_dir}/")
    print("\nRun analyze_conjecturing_bottleneck.py to see bottleneck detection.\n")


if __name__ == "__main__":
    main()
