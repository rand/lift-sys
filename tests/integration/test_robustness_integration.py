"""Integration tests for TokDrift robustness framework.

Tests the complete workflow:
1. ParaphraseGenerator creates prompt variants
2. IRVariantGenerator creates IR variants
3. EquivalenceChecker validates equivalence
"""

import pytest

from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.robustness import (
    EquivalenceChecker,
    IRVariantGenerator,
    ParaphraseGenerator,
    ParaphraseStrategy,
)


class TestRobustnessIntegration:
    """Integration tests for complete robustness testing workflow."""

    def test_paraphrase_generation_workflow(self):
        """Test paraphrase generation end-to-end."""
        # Given a prompt
        prompt = "Create a function that validates email addresses"

        # When we generate paraphrases
        generator = ParaphraseGenerator(max_variants=5, min_diversity=0.1)
        paraphrases = generator.generate(prompt, strategy=ParaphraseStrategy.ALL)

        # Then we should get multiple variants
        assert len(paraphrases) >= 3, "Should generate at least 3 paraphrases"
        assert all(isinstance(p, str) for p in paraphrases)
        assert all(len(p) > 0 for p in paraphrases)
        assert all(p != prompt for p in paraphrases), "Paraphrases should differ from original"

    def test_ir_variant_generation_workflow(self):
        """Test IR variant generation end-to-end."""
        # Given an IR
        original_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sort_numbers",
                parameters=[Parameter(name="input_list", type_hint="list[int]")],
                returns="list[int]",
            ),
            effects=[],
            assertions=[AssertClause(predicate="result is sorted")],
        )

        # When we generate naming variants
        generator = IRVariantGenerator()
        variants = generator.generate_naming_variants(original_ir)

        # Then we should get variants for each naming style
        assert len(variants) == 4, "Should generate 4 naming style variants"

        # Verify different naming styles
        names = [v.signature.name for v in variants]
        assert "sort_numbers" in names  # snake_case
        assert "sortNumbers" in names  # camelCase
        assert "SortNumbers" in names  # PascalCase
        assert "SORT_NUMBERS" in names  # SCREAMING_SNAKE

    def test_equivalence_checking_workflow(self):
        """Test equivalence checking end-to-end."""
        # Given two IRs with different naming
        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sort_numbers",
                parameters=[Parameter(name="input_data", type_hint="list[int]")],
                returns="list[int]",
            ),
            effects=[],
            assertions=[],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sortNumbers",
                parameters=[Parameter(name="inputData", type_hint="list[int]")],
                returns="list[int]",
            ),
            effects=[],
            assertions=[],
        )

        # When we check equivalence with naming normalization
        checker = EquivalenceChecker(normalize_naming=True)
        result = checker.ir_equivalent(ir1, ir2)

        # Then they should be equivalent
        assert result is True, "IRs should be equivalent when normalizing naming"

    def test_code_equivalence_workflow(self):
        """Test code equivalence checking end-to-end."""
        # Given two functionally equivalent code snippets
        code1 = """
def sort_numbers(nums):
    return sorted(nums)
"""

        code2 = """
def sort_numbers(nums):
    result = list(nums)
    result.sort()
    return result
"""

        test_inputs = [
            {"nums": [3, 1, 4, 1, 5, 9, 2, 6]},
            {"nums": []},
            {"nums": [1]},
            {"nums": [5, 4, 3, 2, 1]},
        ]

        # When we check code equivalence
        checker = EquivalenceChecker()
        result = checker.code_equivalent(code1, code2, test_inputs, timeout_seconds=5)

        # Then they should be equivalent
        assert result is True, "Code snippets should be functionally equivalent"

    def test_full_robustness_workflow(self):
        """Test complete robustness testing workflow."""
        # Step 1: Generate paraphrases of a prompt
        prompt = "Create a function that sorts a list"
        para_gen = ParaphraseGenerator(max_variants=3, min_diversity=0.1)
        paraphrases = para_gen.generate(prompt, strategy=ParaphraseStrategy.LEXICAL)

        assert len(paraphrases) >= 2, "Should generate paraphrases"

        # Step 2: Create a sample IR (simulating translation from prompt)
        base_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Sort a list"),
            signature=SigClause(
                name="sort_list",
                parameters=[Parameter(name="items", type_hint="list")],
                returns="list",
            ),
            effects=[],
            assertions=[],
        )

        # Step 3: Generate IR variants
        ir_gen = IRVariantGenerator()
        ir_variants = ir_gen.generate_naming_variants(base_ir)

        assert len(ir_variants) == 4, "Should generate naming variants"

        # Step 4: Check IR equivalence across variants
        checker = EquivalenceChecker(normalize_naming=True)
        for variant in ir_variants[1:]:
            assert checker.ir_equivalent(base_ir, variant), (
                f"Variant {variant.signature.name} should be equivalent to base IR"
            )

        # Step 5: Verify we can detect non-equivalent IRs
        different_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Reverse a list"),  # Different intent!
            signature=SigClause(
                name="reverse_list",
                parameters=[Parameter(name="items", type_hint="list")],
                returns="list",
            ),
            effects=[],
            assertions=[],
        )

        assert not checker.ir_equivalent(base_ir, different_ir), (
            "Different IRs should not be equivalent"
        )

    def test_robustness_metrics_computation(self):
        """Test computation of robustness metrics."""
        # Given an IR and its variants
        base_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process_data",
                parameters=[Parameter(name="data", type_hint="dict")],
                returns="dict",
            ),
            effects=[],
            assertions=[],
        )

        generator = IRVariantGenerator()
        variants = generator.generate_naming_variants(base_ir)

        # When we check equivalence of all variants
        checker = EquivalenceChecker(normalize_naming=True)
        equivalent_count = sum(1 for v in variants if checker.ir_equivalent(base_ir, v))

        # Then we can compute robustness metrics
        total_variants = len(variants)
        robustness_score = equivalent_count / total_variants if total_variants > 0 else 0

        assert robustness_score >= 0.9, (
            f"Robustness score should be high (got {robustness_score:.2%})"
        )
        assert total_variants == 4, "Should have 4 naming variants"
        assert equivalent_count == 4, "All naming variants should be equivalent with normalization"


class TestRobustnessEdgeCases:
    """Test edge cases in robustness testing."""

    def test_empty_prompt_handling(self):
        """Test handling of empty prompts."""
        generator = ParaphraseGenerator()

        # Should handle empty prompt gracefully
        paraphrases = generator.generate("", strategy=ParaphraseStrategy.LEXICAL)
        assert isinstance(paraphrases, list)
        assert len(paraphrases) == 0, "Empty prompt should generate no paraphrases"

    def test_minimal_ir_variant_generation(self):
        """Test IR variant generation with minimal IR."""
        minimal_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Do something"),
            signature=SigClause(name="func", parameters=[], returns="None"),
            effects=[],
            assertions=[],
        )

        generator = IRVariantGenerator()
        variants = generator.generate_naming_variants(minimal_ir)

        assert len(variants) == 4, "Should generate variants even for minimal IR"

    def test_equivalence_with_empty_effects(self):
        """Test equivalence checking with empty effects."""
        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="None"),
            effects=[],
            assertions=[],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="None"),
            effects=[],
            assertions=[],
        )

        checker = EquivalenceChecker()
        assert checker.ir_equivalent(ir1, ir2), "Empty IRs should be equivalent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
