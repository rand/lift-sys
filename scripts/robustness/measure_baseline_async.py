#!/usr/bin/env python3
"""Measure baseline robustness metrics with real IR generation.

This script runs comprehensive baseline measurements using actual
BestOfNIRTranslator and updates expected_results.json with current
system performance.

Usage:
    # Dry run (show what would be measured)
    python scripts/robustness/measure_baseline_async.py --dry-run

    # Measure with MockProvider (fast, free)
    python scripts/robustness/measure_baseline_async.py --provider mock --output baseline_mock.json

    # Measure with OpenAI (requires API key, costs money)
    OPENAI_API_KEY=<key> python scripts/robustness/measure_baseline_async.py --provider openai --output baseline_openai.json

    # Measure and update expected_results.json
    python scripts/robustness/measure_baseline_async.py --provider mock --update-baseline

Requirements:
    - Phase 3 integration complete
    - Full test environment (spaCy, NLTK models)
    - API keys (for non-mock providers)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def measure_paraphrase_baseline(provider_type: str = "mock") -> dict[str, Any]:
    """Measure baseline robustness for paraphrase tests with real IR generation.

    Args:
        provider_type: Provider to use ("mock", "openai", "anthropic")

    Returns:
        Dictionary with paraphrase robustness metrics
    """
    from lift_sys.forward_mode import BestOfNIRTranslator
    from lift_sys.robustness import ParaphraseGenerator, SensitivityAnalyzer

    print(f"Measuring paraphrase robustness baseline (provider: {provider_type})...")

    # Load test prompts
    fixtures_path = Path(__file__).parent.parent.parent / "tests/robustness/fixtures"
    prompts_file = fixtures_path / "prompts.json"

    if not prompts_file.exists():
        print(f"Warning: Prompts file not found: {prompts_file}")
        return {}

    with open(prompts_file) as f:
        all_prompts = json.load(f)

    # Initialize components
    generator = ParaphraseGenerator(max_variants=10, min_diversity=0.2)
    analyzer = SensitivityAnalyzer(normalize_naming=True)

    # Initialize provider
    provider = _get_provider(provider_type)
    translator = BestOfNIRTranslator(provider, n_candidates=3, temperature=0.5)

    results = {}

    for category, prompts in all_prompts.items():
        print(f"\n  Testing {category}...")
        category_results = []

        # Test first 3 in each category (to keep runtime reasonable)
        for prompt in prompts[:3]:
            try:
                # Use hardcoded paraphrases for reliability (learned from Component 1)
                paraphrases = _get_hardcoded_paraphrases(prompt)

                if not paraphrases:
                    print(f"    Skipping '{prompt[:50]}...' (no paraphrases available)")
                    continue

                print(f"    Testing: '{prompt[:50]}...'")
                print(f"      Paraphrases: {len(paraphrases)}")

                # Generate IRs for all variants (async)
                all_prompts_list = [prompt, *paraphrases]
                irs = []

                for p in all_prompts_list:
                    try:
                        ir = await translator.translate(p)
                        irs.append(ir)
                    except Exception as e:
                        print(f"      Warning: Failed to generate IR for '{p[:30]}...': {e}")

                if len(irs) < 2:
                    print(f"      Skipping (not enough valid IRs: {len(irs)})")
                    continue

                # Measure equivalence manually (since analyzer.measure_ir_sensitivity expects sync function)
                from lift_sys.robustness import EquivalenceChecker

                checker = EquivalenceChecker(normalize_naming=True)
                base_ir = irs[0]
                equivalence_results = []

                for variant_ir in irs[1:]:
                    try:
                        equivalent = checker.ir_equivalent(base_ir, variant_ir)
                        equivalence_results.append(equivalent)
                    except Exception as e:
                        print(f"      Warning: Equivalence check failed: {e}")
                        equivalence_results.append(False)

                # Compute robustness
                if equivalence_results:
                    robustness = sum(equivalence_results) / len(equivalence_results)
                    sensitivity = 1 - robustness

                    category_results.append(
                        {
                            "prompt": prompt,
                            "robustness": robustness,
                            "sensitivity": sensitivity,
                            "variants_tested": len(equivalence_results),
                            "equivalent_count": sum(equivalence_results),
                        }
                    )

                    print(
                        f"      Robustness: {robustness:.2%}, "
                        f"Sensitivity: {sensitivity:.2%} "
                        f"({sum(equivalence_results)}/{len(equivalence_results)} equivalent)"
                    )
                else:
                    print("      Skipping (no equivalence results)")

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
                f"Avg Sensitivity {avg_sensitivity:.2%} "
                f"({len(category_results)} tests)"
            )

    return results


def _get_provider(provider_type: str):
    """Get provider instance based on type.

    Args:
        provider_type: "mock", "openai", "anthropic", etc.

    Returns:
        Provider instance
    """
    if provider_type == "mock":
        from lift_sys.providers.mock import MockProvider

        provider = MockProvider()

        # Configure realistic IR response
        realistic_ir_dict = {
            "intent": {"summary": "Sort a list of numbers in ascending order"},
            "signature": {
                "name": "sort_numbers",
                "parameters": [{"name": "numbers", "type_hint": "list[int]"}],
                "returns": "list[int]",
            },
            "effects": [
                {"description": "Return a new sorted list"},
                {"description": "Original list is not modified"},
            ],
            "assertions": [
                {"predicate": "result is sorted in ascending order"},
                {"predicate": "len(result) == len(numbers)"},
            ],
        }

        provider.set_structured_response(realistic_ir_dict)
        return provider

    elif provider_type == "openai":
        from lift_sys.providers import OpenAIProvider

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        return OpenAIProvider(api_key=api_key)

    elif provider_type == "anthropic":
        from lift_sys.providers import AnthropicProvider

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        return AnthropicProvider(api_key=api_key)

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def _get_hardcoded_paraphrases(prompt: str) -> list[str]:
    """Get hardcoded paraphrases for known prompts.

    For baseline measurement reliability, we use predefined paraphrases
    instead of dynamic generation (which can be variable).

    Args:
        prompt: Original prompt

    Returns:
        List of paraphrases (may be empty if prompt not recognized)
    """
    # Map of known prompts to their paraphrases
    paraphrase_map = {
        "Create a function that sorts a list of numbers": [
            "Build a function to sort a numeric list",
            "Write a function that arranges numbers in order",
        ],
        "Write a function to filter even numbers from a list": [
            "Create a function to extract even numbers from a list",
            "Build a function that filters out even numbers from a list",
        ],
        "Implement a function that reverses a string": [
            "Create a function to reverse a string",
            "Write a function that reverses the characters in a string",
        ],
        "Create a function that validates email addresses": [
            "Write a function to validate email addresses",
            "Build a function for email address validation",
        ],
        "Write a function to check if a password is strong": [
            "Create a function to validate password strength",
            "Build a function that checks password strength",
        ],
        "Implement a function that validates phone numbers": [
            "Create a function to validate phone numbers",
            "Write a function for phone number validation",
        ],
        "Create a function that converts snake_case to camelCase": [
            "Write a function to convert snake_case to camelCase",
            "Build a function that transforms snake_case into camelCase",
        ],
        "Write a function to normalize whitespace in strings": [
            "Create a function to normalize whitespace in strings",
            "Build a function that normalizes string whitespace",
        ],
        "Implement a function that removes duplicates from a list": [
            "Create a function to remove duplicates from a list",
            "Write a function that eliminates duplicate list elements",
        ],
        "Create a function that handles empty lists gracefully": [
            "Write a function to handle empty lists gracefully",
            "Build a function that gracefully handles empty lists",
        ],
        "Write a function to process None values in data": [
            "Create a function to process None values in data",
            "Build a function that handles None values in data",
        ],
    }

    return paraphrase_map.get(prompt, [])


async def measure_ir_variant_baseline(provider_type: str = "mock") -> dict[str, Any]:
    """Measure baseline robustness for IR variant tests.

    Note: This requires code generation which is not yet integrated in Phase 3.
    For now, returns placeholder data.

    Args:
        provider_type: Provider to use

    Returns:
        Dictionary with IR variant robustness metrics
    """
    print(f"\nMeasuring IR variant robustness baseline (provider: {provider_type})...")
    print("  Note: Code generation not yet integrated - returning placeholder data")

    return {
        "naming_variants": {
            "average_robustness": None,
            "average_sensitivity": None,
            "tests_run": 0,
            "details": [],
            "note": "Code generation integration pending (Phase 3, Component 3+)",
        }
    }


def generate_baseline_report(
    paraphrase_results: dict[str, Any],
    ir_variant_results: dict[str, Any],
    provider_type: str,
) -> dict[str, Any]:
    """Generate comprehensive baseline report.

    Args:
        paraphrase_results: Paraphrase robustness results
        ir_variant_results: IR variant robustness results
        provider_type: Provider used for measurement

    Returns:
        Complete baseline report
    """
    # Calculate overall robustness across all categories
    all_robustness_values = []
    for category_data in paraphrase_results.values():
        if "average_robustness" in category_data:
            all_robustness_values.append(category_data["average_robustness"])

    overall_robustness = (
        sum(all_robustness_values) / len(all_robustness_values) if all_robustness_values else None
    )

    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": "Phase 3 Component 2 - Real IR Generation",
            "provider": provider_type,
            "note": "Using real BestOfNIRTranslator with hardcoded paraphrases for reliability",
        },
        "paraphrase_robustness": paraphrase_results,
        "ir_variant_robustness": ir_variant_results,
        "summary": {
            "total_tests_run": sum(
                r.get("tests_run", 0)
                for results in [paraphrase_results, ir_variant_results]
                for r in results.values()
                if isinstance(r, dict)
            ),
            "overall_robustness": overall_robustness,
            "overall_sensitivity": 1 - overall_robustness if overall_robustness else None,
            "phase": "Phase 3 Component 2 - Baseline Measurement",
            "ready_for_component_3": True,
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
            if (
                variant_type in expected.get("ir_variant_robustness", {})
                and results.get("average_robustness") is not None
            ):
                expected["ir_variant_robustness"][variant_type]["baseline"] = results[
                    "average_robustness"
                ]

    # Add metadata
    expected["last_baseline_update"] = datetime.now().isoformat()
    expected["baseline_provider"] = baseline_report["metadata"]["provider"]
    expected["baseline_note"] = baseline_report["metadata"]["note"]

    # Write back
    with open(expected_file, "w") as f:
        json.dump(expected, f, indent=2)

    print(f"\n✅ Updated expected results: {expected_file}")


async def main_async():
    """Main async entry point."""
    parser = argparse.ArgumentParser(
        description="Measure baseline robustness with real IR generation"
    )
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
    parser.add_argument(
        "--provider",
        "-p",
        choices=["mock", "openai", "anthropic"],
        default="mock",
        help="Provider to use for IR generation (default: mock)",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - Would measure:")
        print(f"  - Paraphrase robustness (all prompt categories) with {args.provider} provider")
        print("  - IR variant robustness (placeholder - code generation pending)")
        print(f"\nProvider: {args.provider}")
        return

    print("=" * 60)
    print("Baseline Robustness Measurement (Real IR Generation)")
    print("=" * 60)
    print(f"Provider: {args.provider}")
    print()

    # Measure paraphrase baseline
    paraphrase_results = await measure_paraphrase_baseline(args.provider)
    print()

    # Measure IR variant baseline (placeholder for now)
    ir_variant_results = await measure_ir_variant_baseline(args.provider)
    print()

    # Generate report
    baseline_report = generate_baseline_report(
        paraphrase_results, ir_variant_results, args.provider
    )

    print("=" * 60)
    print("Baseline Measurement Complete")
    print("=" * 60)
    print(f"Total tests run: {baseline_report['summary']['total_tests_run']}")
    if baseline_report["summary"]["overall_robustness"]:
        print(f"Overall robustness: {baseline_report['summary']['overall_robustness']:.2%}")
        print(f"Overall sensitivity: {baseline_report['summary']['overall_sensitivity']:.2%}")
    print(f"Provider: {baseline_report['metadata']['provider']}")
    print()

    # Save results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(baseline_report, f, indent=2)
        print(f"✅ Results saved to: {args.output}")

    # Update expected results
    if args.update_baseline:
        fixtures_path = Path(__file__).parent.parent.parent / "tests/robustness/fixtures"
        update_expected_results(baseline_report, fixtures_path)

    print()
    print("Next Steps:")
    print("  1. Review baseline results in output file")
    print("  2. Identify fragile prompts (robustness < 90%)")
    print("  3. Update FRAGILE_PROMPTS.md with findings")
    print("  4. Plan optimization strategies for Phase 3 Component 3")


def main():
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
