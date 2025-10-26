"""IR variant robustness tests for lift-sys.

Tests code generation consistency across IR variations.
Validates that semantically equivalent IRs produce equivalent code.
"""

import pytest


class TestIRVariantRobustness:
    """Test robustness to IR variations."""

    def test_naming_convention_robustness(
        self,
        ir_variant_generator,
        equivalence_checker,
        sensitivity_analyzer,
        sample_ir,
        robustness_threshold,
    ):
        """Test robustness to different naming conventions."""
        # Generate naming variants (snake_case, camelCase, PascalCase, SCREAMING_SNAKE)
        variants = ir_variant_generator.generate_naming_variants(sample_ir)

        assert len(variants) == 4, "Should generate 4 naming style variants"

        # Verify all variants are equivalent to original (with naming normalization)
        for variant in variants:
            assert equivalence_checker.ir_equivalent(sample_ir, variant), (
                f"Variant {variant.signature.name} should be equivalent to original"
            )

        # Mock code generation for testing
        def generate_code(ir):
            return f"def {ir.signature.name}(): pass"

        # Measure sensitivity (empty test_inputs since mock doesn't execute)
        result = sensitivity_analyzer.measure_code_sensitivity(
            [sample_ir, *variants], generate_code, test_inputs=[], timeout_seconds=5
        )

        # Naming variants should have very high robustness
        assert result.robustness >= robustness_threshold, (
            f"Naming variant robustness {result.robustness:.2%} below target {robustness_threshold:.2%}"
        )

        print(f"\nNaming Convention Robustness: {result.robustness:.2%}")
        print(f"Variants tested: {result.total_variants}")

    def test_effect_ordering_robustness(
        self,
        ir_variant_generator,
        sensitivity_analyzer,
        complex_ir,
        warning_threshold,
    ):
        """Test robustness to effect reordering."""
        # Generate effect ordering variants
        variants = ir_variant_generator.generate_effect_orderings(complex_ir)

        if not variants:
            pytest.skip("No valid effect orderings generated")

        # Mock code generation
        def generate_code(ir):
            effects_str = (
                "\\n    ".join(e.description for e in ir.effects) if ir.effects else "pass"
            )
            return f"def {ir.signature.name}():\\n    {effects_str}"

        # Measure sensitivity
        result = sensitivity_analyzer.measure_code_sensitivity(
            [complex_ir, *variants], generate_code, test_inputs=[], timeout_seconds=5
        )

        # Effect ordering should have good robustness (dependencies may limit reordering)
        assert result.robustness >= warning_threshold, (
            f"Effect ordering robustness {result.robustness:.2%} below warning threshold {warning_threshold:.2%}"
        )

        print(f"\nEffect Ordering Robustness: {result.robustness:.2%}")
        print(f"Variants tested: {result.total_variants}")

    def test_assertion_rephrasing_robustness(
        self,
        ir_variant_generator,
        equivalence_checker,
        sensitivity_analyzer,
        complex_ir,
        warning_threshold,
    ):
        """Test robustness to assertion rephrasing."""
        # Generate assertion rephrasing variants
        variants = ir_variant_generator.generate_assertion_variants(complex_ir)

        if not variants:
            pytest.skip("No assertion rephrasing variants generated")

        # Mock code generation
        def generate_code(ir):
            return f"def {ir.signature.name}(): pass"

        # Measure sensitivity
        result = sensitivity_analyzer.measure_code_sensitivity(
            [complex_ir, *variants], generate_code, test_inputs=[], timeout_seconds=5
        )

        # Assertion rephrasing should maintain good robustness
        assert result.robustness >= warning_threshold, (
            f"Assertion rephrasing robustness {result.robustness:.2%} below warning threshold {warning_threshold:.2%}"
        )

        print(f"\nAssertion Rephrasing Robustness: {result.robustness:.2%}")
        print(f"Variants tested: {result.total_variants}")

    def test_combined_ir_variants(
        self,
        ir_variant_generator,
        sensitivity_analyzer,
        complex_ir,
        failure_threshold,
    ):
        """Test robustness to combined IR transformations."""
        # Generate multiple types of variants
        naming_variants = ir_variant_generator.generate_naming_variants(complex_ir)
        effect_variants = ir_variant_generator.generate_effect_orderings(complex_ir)
        assertion_variants = ir_variant_generator.generate_assertion_variants(complex_ir)

        # Combine all variants
        all_variants = [*naming_variants, *effect_variants, *assertion_variants]

        if not all_variants:
            pytest.skip("No variants generated")

        # Mock code generation
        def generate_code(ir):
            return f"def {ir.signature.name}(): pass"

        # Measure sensitivity
        result = sensitivity_analyzer.measure_code_sensitivity(
            [complex_ir, *all_variants], generate_code, test_inputs=[], timeout_seconds=5
        )

        # Combined variants may have lower robustness (but above failure threshold)
        assert result.robustness >= failure_threshold, (
            f"Combined variant robustness {result.robustness:.2%} below failure threshold {failure_threshold:.2%}"
        )

        print(f"\nCombined IR Variant Robustness: {result.robustness:.2%}")
        print(f"Variants tested: {result.total_variants}")
        print(f"  - Naming: {len(naming_variants)}")
        print(f"  - Effect ordering: {len(effect_variants)}")
        print(f"  - Assertions: {len(assertion_variants)}")
