"""End-to-end robustness tests for lift-sys.

Tests full pipeline (NLP → IR → Code) robustness.
Validates that semantic-preserving transformations at each stage
maintain overall system robustness.
"""

import pytest

from lift_sys.ir.models import IntentClause, IntermediateRepresentation, Parameter, SigClause
from lift_sys.robustness import ParaphraseStrategy


class TestEndToEndRobustness:
    """Test end-to-end pipeline robustness."""

    def test_prompt_to_ir_to_code_robustness(
        self,
        paraphrase_generator,
        ir_variant_generator,
        sensitivity_analyzer,
        sample_prompts,
        failure_threshold,
    ):
        """Test full pipeline robustness with paraphrase → IR → code."""
        # Use first sample prompt
        prompt = sample_prompts[0]

        # Generate paraphrases
        paraphrases = paraphrase_generator.generate(prompt, strategy=ParaphraseStrategy.ALL)

        if len(paraphrases) < 2:
            pytest.skip("Not enough paraphrases generated")

        # Mock IR generation from prompts
        def generate_ir(p: str) -> IntermediateRepresentation:
            return IntermediateRepresentation(
                intent=IntentClause(summary=p),
                signature=SigClause(
                    name="sort_numbers",
                    parameters=[Parameter(name="nums", type_hint="list[int]")],
                    returns="list[int]",
                ),
                effects=[],
                assertions=[],
            )

        # Measure IR generation robustness
        ir_result = sensitivity_analyzer.measure_ir_sensitivity([prompt, *paraphrases], generate_ir)

        print(f"\nE2E Stage 1 (Prompt → IR) Robustness: {ir_result.robustness:.2%}")

        # Generate IR variants from first IR
        base_ir = generate_ir(prompt)
        ir_variants = ir_variant_generator.generate_naming_variants(base_ir)

        # Mock code generation
        def generate_code(ir):
            return f"def {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)}): return sorted({ir.signature.parameters[0].name if ir.signature.parameters else 'data'})"

        # Measure code generation robustness
        code_result = sensitivity_analyzer.measure_code_sensitivity(
            [base_ir, *ir_variants], generate_code, test_inputs=[], timeout_seconds=5
        )

        print(f"E2E Stage 2 (IR → Code) Robustness: {code_result.robustness:.2%}")

        # Overall robustness is minimum of both stages
        overall_robustness = min(ir_result.robustness, code_result.robustness)

        print(f"E2E Overall Robustness: {overall_robustness:.2%}")

        assert overall_robustness >= failure_threshold, (
            f"E2E robustness {overall_robustness:.2%} below failure threshold {failure_threshold:.2%}"
        )

    def test_compositional_robustness(
        self,
        paraphrase_generator,
        ir_variant_generator,
        sensitivity_analyzer,
        sample_prompts,
        failure_threshold,
    ):
        """Test robustness under composition of transformations."""
        # Use multiple prompts
        prompts = sample_prompts[:3]

        robustness_scores = []

        for prompt in prompts:
            # Generate paraphrases
            paraphrases = paraphrase_generator.generate(prompt, strategy=ParaphraseStrategy.LEXICAL)

            if len(paraphrases) < 2:
                continue

            # Mock IR generation
            def generate_ir(p: str) -> IntermediateRepresentation:
                return IntermediateRepresentation(
                    intent=IntentClause(summary=p),
                    signature=SigClause(name="func", parameters=[], returns="None"),
                    effects=[],
                    assertions=[],
                )

            # Measure for this prompt
            result = sensitivity_analyzer.measure_ir_sensitivity(
                [prompt, *paraphrases], generate_ir
            )
            robustness_scores.append(result.robustness)

        if not robustness_scores:
            pytest.skip("No valid measurements collected")

        # Average robustness across multiple scenarios
        avg_robustness = sum(robustness_scores) / len(robustness_scores)

        print(
            f"\nCompositional Robustness (avg of {len(robustness_scores)} scenarios): {avg_robustness:.2%}"
        )
        print(f"Individual scores: {[f'{s:.2%}' for s in robustness_scores]}")

        assert avg_robustness >= failure_threshold, (
            f"Compositional robustness {avg_robustness:.2%} below failure threshold {failure_threshold:.2%}"
        )

    def test_statistical_significance_of_robustness(
        self,
        sensitivity_analyzer,
    ):
        """Test statistical validation of robustness measurements."""
        # Create sample scores (robust system with random small variations)
        # Differences should be small and random (not consistently in one direction)
        robust_original = [0.95, 0.96, 0.94, 0.95, 0.96, 0.95, 0.94]
        robust_variant = [0.95, 0.95, 0.94, 0.96, 0.95, 0.95, 0.94]  # More random variation

        # Wilcoxon test should show no significant difference (robust)
        result = sensitivity_analyzer.wilcoxon_test(robust_original, robust_variant)

        assert result.p_value >= 0.05, "Robust system should show no significant difference"
        assert not result.significant, "Robust system should not be significantly different"

        print("\nRobust System Wilcoxon Test:")
        print(f"  p-value: {result.p_value:.4f}")
        print(f"  Significant: {result.significant}")
        print(f"  Interpretation: {result.interpretation}")

        # Create sample scores (fragile system)
        fragile_original = [0.90, 0.91, 0.89, 0.90, 0.91, 0.90, 0.89]
        fragile_variant = [0.60, 0.61, 0.58, 0.60, 0.61, 0.60, 0.59]

        # Wilcoxon test should show significant difference (fragile)
        result2 = sensitivity_analyzer.wilcoxon_test(fragile_original, fragile_variant)

        assert result2.p_value < 0.05, "Fragile system should show significant difference"
        assert result2.significant, "Fragile system should be significantly different"

        print("\nFragile System Wilcoxon Test:")
        print(f"  p-value: {result2.p_value:.4f}")
        print(f"  Significant: {result2.significant}")
        print(f"  Interpretation: {result2.interpretation}")

    @pytest.mark.skip(reason="Requires actual IR generation integration")
    def test_real_world_scenario_robustness(
        self,
        load_test_prompts,
        load_test_irs,
    ):
        """Test robustness on real-world scenarios.

        This test requires integration with actual IR and code generators.
        Skip for now until Phase 3 integration.
        """
        pass
