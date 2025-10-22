#!/usr/bin/env python3
"""Measure baseline robustness metrics for lift-sys.

This script runs comprehensive baseline measurements and updates
expected_results.json with current system performance.

Usage:
    # Dry run (show what would be measured)
    python scripts/robustness/measure_baseline.py --dry-run

    # Measure and save results
    python scripts/robustness/measure_baseline.py --output baseline_results.json

    # Measure and update expected_results.json
    python scripts/robustness/measure_baseline.py --update-baseline

Requirements:
    - Phase 3 integration (actual IR/code generators)
    - Full test environment (spaCy, NLTK models)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def measure_paraphrase_baseline() -> dict[str, Any]:
    """Measure baseline robustness for paraphrase tests.

    Returns:
        Dictionary with paraphrase robustness metrics
    """
    from lift_sys.robustness import ParaphraseGenerator, ParaphraseStrategy, SensitivityAnalyzer

    print("Measuring paraphrase robustness baseline...")

    # Load test prompts
    fixtures_path = Path(__file__).parent.parent.parent / "tests/robustness/fixtures"
    prompts_file = fixtures_path / "prompts.json"

    if not prompts_file.exists():
        print(f"Warning: Prompts file not found: {prompts_file}")
        return {}

    with open(prompts_file) as f:
        all_prompts = json.load(f)

    generator = ParaphraseGenerator(max_variants=10, min_diversity=0.2)
    analyzer = SensitivityAnalyzer(normalize_naming=True)

    results = {}

    for category, prompts in all_prompts.items():
        print(f"  Testing {category}...")
        category_results = []

        for prompt in prompts[:3]:  # Test first 3 in each category
            # Generate paraphrases
            try:
                paraphrases = generator.generate(prompt, strategy=ParaphraseStrategy.ALL)

                if len(paraphrases) < 2:
                    print(f"    Skipping '{prompt[:50]}...' (insufficient paraphrases)")
                    continue

                # TODO: Replace with actual IR generator in Phase 3
                # For now, use mock generator
                def mock_generate_ir(p: str):
                    from lift_sys.ir.models import (
                        IntentClause,
                        IntermediateRepresentation,
                        SigClause,
                    )

                    return IntermediateRepresentation(
                        intent=IntentClause(summary=p),
                        signature=SigClause(name="test_func", parameters=[], returns="None"),
                        effects=[],
                        assertions=[],
                    )

                # Measure sensitivity
                result = analyzer.measure_ir_sensitivity([prompt, *paraphrases], mock_generate_ir)

                category_results.append(
                    {
                        "prompt": prompt,
                        "robustness": result.robustness,
                        "sensitivity": result.sensitivity,
                        "variants_tested": result.total_variants,
                    }
                )

                print(
                    f"    '{prompt[:50]}...': Robustness {result.robustness:.2%}, "
                    f"Sensitivity {result.sensitivity:.2%}"
                )

            except Exception as e:
                print(f"    Error testing '{prompt[:50]}...': {e}")
                continue

        if category_results:
            avg_robustness = sum(r["robustness"] for r in category_results) / len(category_results)
            avg_sensitivity = sum(r["sensitivity"] for r in category_results) / len(
                category_results
            )

            results[category] = {
                "average_robustness": avg_robustness,
                "average_sensitivity": avg_sensitivity,
                "tests_run": len(category_results),
                "details": category_results,
            }

            print(
                f"  {category}: Avg Robustness {avg_robustness:.2%}, "
                f"Avg Sensitivity {avg_sensitivity:.2%}"
            )

    return results


def measure_ir_variant_baseline() -> dict[str, Any]:
    """Measure baseline robustness for IR variant tests.

    Returns:
        Dictionary with IR variant robustness metrics
    """
    from lift_sys.robustness import IRVariantGenerator, SensitivityAnalyzer

    print("Measuring IR variant robustness baseline...")

    # Load test IRs
    fixtures_path = Path(__file__).parent.parent.parent / "tests/robustness/fixtures"
    irs_file = fixtures_path / "irs.json"

    if not irs_file.exists():
        print(f"Warning: IRs file not found: {irs_file}")
        return {}

    with open(irs_file) as f:
        ir_data = json.load(f)

    from lift_sys.ir.models import (
        AssertClause,
        IntentClause,
        IntermediateRepresentation,
        Parameter,
        SigClause,
    )

    # Properly construct IR objects from JSON
    test_irs = []
    for ir_json in ir_data:
        ir = IntermediateRepresentation(
            intent=IntentClause(**ir_json["intent"]),
            signature=SigClause(
                name=ir_json["signature"]["name"],
                parameters=[Parameter(**p) for p in ir_json["signature"]["parameters"]],
                returns=ir_json["signature"]["returns"],
            ),
            effects=ir_json.get("effects", []),
            assertions=[AssertClause(**a) for a in ir_json.get("assertions", [])],
        )
        test_irs.append(ir)

    generator = IRVariantGenerator()
    analyzer = SensitivityAnalyzer()

    results = {}

    # Test naming variants
    print("  Testing naming variants...")
    naming_results = []

    for ir in test_irs[:3]:  # Test first 3 IRs
        try:
            variants = generator.generate_naming_variants(ir)

            # TODO: Replace with actual code generator in Phase 3
            def mock_generate_code(ir):
                return f"def {ir.signature.name}(): pass"

            result = analyzer.measure_code_sensitivity(
                [ir, *variants], mock_generate_code, test_inputs=[], timeout_seconds=5
            )

            naming_results.append(
                {
                    "ir_name": ir.signature.name,
                    "robustness": result.robustness,
                    "sensitivity": result.sensitivity,
                    "variants_tested": result.total_variants,
                }
            )

            print(
                f"    {ir.signature.name}: Robustness {result.robustness:.2%}, "
                f"Sensitivity {result.sensitivity:.2%}"
            )
        except Exception as e:
            print(f"    Error testing {ir.signature.name}: {e}")
            print("    (This will be fixed in Phase 3 with proper IR models)")
            continue

    if naming_results:
        avg_robustness = sum(r["robustness"] for r in naming_results) / len(naming_results)
        avg_sensitivity = sum(r["sensitivity"] for r in naming_results) / len(naming_results)

        results["naming_variants"] = {
            "average_robustness": avg_robustness,
            "average_sensitivity": avg_sensitivity,
            "tests_run": len(naming_results),
            "details": naming_results,
        }

        print(
            f"  Naming variants: Avg Robustness {avg_robustness:.2%}, "
            f"Avg Sensitivity {avg_sensitivity:.2%}"
        )

    return results


def generate_baseline_report(
    paraphrase_results: dict[str, Any], ir_variant_results: dict[str, Any]
) -> dict[str, Any]:
    """Generate comprehensive baseline report.

    Args:
        paraphrase_results: Paraphrase robustness results
        ir_variant_results: IR variant robustness results

    Returns:
        Complete baseline report
    """
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": "Phase 2 - Infrastructure Complete",
            "note": "Using mock generators - real measurements require Phase 3 integration",
        },
        "paraphrase_robustness": paraphrase_results,
        "ir_variant_robustness": ir_variant_results,
        "summary": {
            "total_tests_run": sum(
                r.get("tests_run", 0)
                for results in [paraphrase_results, ir_variant_results]
                for r in results.values()
            ),
            "phase": "Phase 2 - Baseline Framework",
            "ready_for_phase_3": True,
        },
    }


def update_expected_results(baseline_report: dict[str, Any], fixtures_path: Path):
    """Update expected_results.json with baseline measurements.

    Args:
        baseline_report: Baseline measurement results
        fixtures_path: Path to fixtures directory
    """
    expected_file = fixtures_path / "expected_results.json"

    if not expected_file.exists():
        print(f"Error: Expected results file not found: {expected_file}")
        return

    with open(expected_file) as f:
        expected = json.load(f)

    # Update baselines for paraphrase tests
    if "paraphrase_robustness" in baseline_report:
        for category, results in baseline_report["paraphrase_robustness"].items():
            if category in expected.get("paraphrase_robustness", {}):
                expected["paraphrase_robustness"][category]["baseline"] = results[
                    "average_robustness"
                ]

    # Update baselines for IR variant tests
    if "ir_variant_robustness" in baseline_report:
        for variant_type, results in baseline_report["ir_variant_robustness"].items():
            if variant_type in expected.get("ir_variant_robustness", {}):
                expected["ir_variant_robustness"][variant_type]["baseline"] = results[
                    "average_robustness"
                ]

    # Add metadata
    expected["last_baseline_update"] = datetime.now().isoformat()
    expected["baseline_note"] = baseline_report["metadata"]["note"]

    # Write back
    with open(expected_file, "w") as f:
        json.dump(expected, f, indent=2)

    print(f"\nUpdated expected results: {expected_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Measure baseline robustness metrics")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be measured without running tests",
    )
    parser.add_argument("--output", "-o", type=Path, help="Output file for baseline results (JSON)")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update expected_results.json with measurements",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - Would measure:")
        print("  - Paraphrase robustness (all prompt categories)")
        print("  - IR variant robustness (naming, effect ordering, assertions)")
        print("  - E2E pipeline robustness")
        print("\nNote: Actual measurements require Phase 3 integration")
        return

    print("=" * 60)
    print("Baseline Robustness Measurement")
    print("=" * 60)
    print()

    # Measure paraphrase baseline
    paraphrase_results = measure_paraphrase_baseline()
    print()

    # Measure IR variant baseline
    ir_variant_results = measure_ir_variant_baseline()
    print()

    # Generate report
    baseline_report = generate_baseline_report(paraphrase_results, ir_variant_results)

    print("=" * 60)
    print("Baseline Measurement Complete")
    print("=" * 60)
    print(f"Total tests run: {baseline_report['summary']['total_tests_run']}")
    print(f"Phase: {baseline_report['summary']['phase']}")
    print(f"Note: {baseline_report['metadata']['note']}")
    print()

    # Save results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(baseline_report, f, indent=2)
        print(f"Results saved to: {args.output}")

    # Update expected results
    if args.update_baseline:
        fixtures_path = Path(__file__).parent.parent.parent / "tests/robustness/fixtures"
        update_expected_results(baseline_report, fixtures_path)

    print()
    print("Next Steps:")
    print("  1. Complete Phase 3 integration (actual IR/code generators)")
    print("  2. Re-run this script with real generators")
    print("  3. Analyze fragile prompts/IRs (robustness < 90%)")
    print("  4. Update FRAGILE_PROMPTS.md with findings")
    print("  5. Plan optimization strategies for Phase 3")


if __name__ == "__main__":
    main()
