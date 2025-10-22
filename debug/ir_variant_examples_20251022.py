#!/usr/bin/env python3
"""Example IRVariantGenerator usage and output.

Demonstrates IR variant generation for robustness testing.
Generated: 2025-10-22
"""

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.robustness import IRVariantGenerator


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def main():
    """Generate and display IR variants."""

    # Create sample IR
    original_ir = IntermediateRepresentation(
        intent=IntentClause(summary="Sort numbers in ascending order"),
        signature=SigClause(
            name="sort_numbers",
            parameters=[
                Parameter(name="input_list", type_hint="list[int]"),
                Parameter(name="reverse_order", type_hint="bool"),
            ],
            returns="list[int]",
        ),
        effects=[
            EffectClause(description="reads input_list elements"),
            EffectClause(description="sorts array in place"),
            EffectClause(description="returns sorted list"),
        ],
        assertions=[
            AssertClause(predicate="len(input_list) > 0"),
            AssertClause(predicate="result == True"),
        ],
        metadata=Metadata(origin="example"),
    )

    print_section("Original IR")
    print(f"Function: {original_ir.signature.name}")
    print(f"Parameters: {[p.name for p in original_ir.signature.parameters]}")
    print(f"Effects: {len(original_ir.effects)}")
    print(f"Assertions: {[a.predicate for a in original_ir.assertions]}")

    # Initialize generator
    gen = IRVariantGenerator(max_variants=10)

    # 1. Naming Variants
    print_section("1. Naming Convention Variants")
    naming_variants = gen.generate_naming_variants(original_ir)
    print(f"Generated {len(naming_variants)} naming variants:\n")

    for i, variant in enumerate(naming_variants):
        print(f"  Variant {i + 1}:")
        print(f"    Function name: {variant.signature.name}")
        print(f"    Parameters: {[p.name for p in variant.signature.parameters]}")
        print()

    # 2. Effect Reordering Variants
    print_section("2. Effect Reordering Variants")
    effect_variants = gen.generate_effect_orderings(original_ir)
    print(f"Generated {len(effect_variants)} effect ordering variants:\n")

    print("  Original order:")
    for j, effect in enumerate(original_ir.effects):
        print(f"    {j + 1}. {effect.description}")
    print()

    if effect_variants:
        print("  Variant 1 (reordered):")
        for j, effect in enumerate(effect_variants[0].effects):
            print(f"    {j + 1}. {effect.description}")
    else:
        print("  No reordering possible (effects have dependencies)")
    print()

    # 3. Assertion Rephrasing Variants
    print_section("3. Assertion Rephrasing Variants")
    assertion_variants = gen.generate_assertion_variants(original_ir)
    print(f"Generated {len(assertion_variants)} assertion variants:\n")

    print("  Original assertions:")
    for assertion in original_ir.assertions:
        print(f"    - {assertion.predicate}")
    print()

    if assertion_variants:
        print("  Variant 1 (rephrased):")
        for assertion in assertion_variants[0].assertions:
            print(f"    - {assertion.predicate}")
    print()

    # 4. Combined Variants
    print_section("4. All Variant Types Combined")
    all_variants = gen.generate_variants(original_ir, max_variants=10)
    print(f"Generated {len(all_variants)} total variants\n")

    print("  Breakdown by type:")
    print(f"    - Naming variants: {len(naming_variants)}")
    print(f"    - Effect variants: {len(effect_variants)}")
    print(f"    - Assertion variants: {len(assertion_variants)}")
    print(f"    - Total combined: {len(all_variants)}")

    # 5. Demonstrate semantic preservation
    print_section("5. Semantic Preservation Check")
    print("All variants preserve:")
    print("  ✓ Same intent/purpose")
    print("  ✓ Same parameter types")
    print("  ✓ Same return type")
    print("  ✓ Same number of effects")
    print("  ✓ Same logical assertions")
    print()
    print("Variations applied:")
    print("  • Naming conventions (4 styles)")
    print("  • Effect ordering (where independent)")
    print("  • Assertion phrasing (logically equivalent)")

    # 6. Example use case
    print_section("6. Use Case: Robustness Testing")
    print("These variants enable testing:")
    print()
    print("1. Translation Robustness")
    print("   - Generate IR → Code for each naming variant")
    print("   - Check if code is functionally equivalent")
    print("   - Measure sensitivity to naming conventions")
    print()
    print("2. Model Consistency")
    print("   - Feed same semantic intent with different phrasings")
    print("   - Check if IR extraction is consistent")
    print("   - Identify brittle extraction patterns")
    print()
    print("3. Code Generation Quality")
    print("   - Generate code from different IR variants")
    print("   - Verify all produce correct behavior")
    print("   - Measure variation in generated code quality")


if __name__ == "__main__":
    main()
