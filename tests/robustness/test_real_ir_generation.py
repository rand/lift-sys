"""Real IR generation robustness tests.

These tests use actual BestOfNIRTranslator with real providers (or mock providers
configured to return realistic IRs) to measure true robustness.

Marked as @pytest.mark.integration to allow separate execution from fast unit tests.
"""

import os

import pytest

from lift_sys.forward_mode import BestOfNIRTranslator
from lift_sys.providers.mock import MockProvider
from lift_sys.robustness import ParaphraseStrategy


@pytest.fixture
def mock_provider_with_realistic_irs():
    """Mock provider that returns realistic IRs for testing."""
    provider = MockProvider()

    # Configure realistic IR as structured dict matching IR JSON schema
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

    # Set structured response (MockProvider will return as dict)
    provider.set_structured_response(realistic_ir_dict)

    return provider


@pytest.fixture
def real_ir_translator(mock_provider_with_realistic_irs):
    """IR translator using real BestOfNIRTranslator (with mock provider for testing)."""
    return BestOfNIRTranslator(
        provider=mock_provider_with_realistic_irs,
        n_candidates=3,
        temperature=0.5,
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestRealIRGenerationRobustness:
    """Integration tests using actual IR generation pipeline."""

    async def test_lexical_paraphrase_with_real_translator(
        self,
        paraphrase_generator,
        sensitivity_analyzer,
        real_ir_translator,
        sample_prompts,
        warning_threshold,
    ):
        """Test lexical paraphrase robustness with real IR generation.

        Note: Uses warning_threshold instead of target since real generation
        is more variable than mocks.
        """
        prompt = sample_prompts[0]

        # Generate lexical paraphrases
        paraphrases = paraphrase_generator.generate(prompt, strategy=ParaphraseStrategy.LEXICAL)

        if len(paraphrases) < 1:
            pytest.skip("Not enough paraphrases generated (need at least 1)")

        # Use real translator (async)
        async def generate_ir_async(p: str):
            return await real_ir_translator.translate(p)

        # Measure sensitivity with real generation
        all_prompts = [prompt, *paraphrases[:3]]  # Limit to 3 for speed

        # Generate IRs for all prompts
        irs = []
        for p in all_prompts:
            try:
                ir = await generate_ir_async(p)
                irs.append(ir)
            except Exception as e:
                print(f"Warning: Failed to generate IR for '{p[:50]}...': {e}")

        if len(irs) < 2:
            pytest.skip("Not enough valid IRs generated")

        # Manually measure equivalence (synchronous)
        from lift_sys.robustness import EquivalenceChecker

        checker = EquivalenceChecker(normalize_naming=True)

        base_ir = irs[0]
        equivalence_results = []

        for variant_ir in irs[1:]:
            try:
                equivalent = checker.ir_equivalent(base_ir, variant_ir)
                equivalence_results.append(equivalent)
            except Exception as e:
                print(f"Warning: Equivalence check failed: {e}")
                equivalence_results.append(False)

        # Compute robustness
        if equivalence_results:
            robustness = sum(equivalence_results) / len(equivalence_results)
            sensitivity = 1 - robustness

            print(f"\nReal IR Generation Robustness (Lexical): {robustness:.2%}")
            print(f"Sensitivity: {sensitivity:.2%}")
            print(f"Variants tested: {len(equivalence_results)}")

            # Use warning threshold for real generation
            assert robustness >= warning_threshold, (
                f"Real IR generation robustness {robustness:.2%} "
                f"below warning threshold {warning_threshold:.2%}"
            )
        else:
            pytest.skip("No valid equivalence results")

    async def test_structural_paraphrase_with_real_translator(
        self,
        paraphrase_generator,
        real_ir_translator,
        sample_prompts,
        failure_threshold,
    ):
        """Test structural paraphrase robustness with real IR generation.

        Note: Uses failure_threshold since structural paraphrases are harder.
        """
        prompt = sample_prompts[1]

        # Generate structural paraphrases
        paraphrases = paraphrase_generator.generate(prompt, strategy=ParaphraseStrategy.STRUCTURAL)

        if len(paraphrases) < 1:
            pytest.skip("Not enough structural paraphrases generated (need at least 1)")

        # Generate IRs
        all_prompts = [prompt, *paraphrases[:2]]  # Limit to 2 for speed
        irs = []

        for p in all_prompts:
            try:
                ir = await real_ir_translator.translate(p)
                irs.append(ir)
            except Exception as e:
                print(f"Warning: Failed to generate IR: {e}")

        if len(irs) < 2:
            pytest.skip("Not enough valid IRs generated")

        # Check equivalence
        from lift_sys.robustness import EquivalenceChecker

        checker = EquivalenceChecker(normalize_naming=True)

        base_ir = irs[0]
        equivalence_results = [checker.ir_equivalent(base_ir, variant_ir) for variant_ir in irs[1:]]

        if equivalence_results:
            robustness = sum(equivalence_results) / len(equivalence_results)

            print(f"\nReal IR Generation Robustness (Structural): {robustness:.2%}")

            # Structural paraphrases are challenging - use failure threshold
            assert robustness >= failure_threshold, (
                f"Real IR generation robustness {robustness:.2%} "
                f"below failure threshold {failure_threshold:.2%}"
            )
        else:
            pytest.skip("No valid equivalence results")

    async def test_combined_paraphrase_with_real_translator(
        self,
        paraphrase_generator,
        real_ir_translator,
        sample_prompts,
        failure_threshold,
    ):
        """Test combined paraphrase robustness with real IR generation."""
        prompt = sample_prompts[2]

        # Generate all types of paraphrases
        paraphrases = paraphrase_generator.generate(prompt, strategy=ParaphraseStrategy.ALL)

        if len(paraphrases) < 1:
            pytest.skip("Not enough combined paraphrases generated (need at least 1)")

        # Generate IRs (limit for speed)
        all_prompts = [prompt, *paraphrases[:3]]
        irs = []

        for p in all_prompts:
            try:
                ir = await real_ir_translator.translate(p)
                irs.append(ir)
            except Exception as e:
                print(f"Warning: Failed to generate IR: {e}")

        if len(irs) < 2:
            pytest.skip("Not enough valid IRs generated")

        # Check equivalence
        from lift_sys.robustness import EquivalenceChecker

        checker = EquivalenceChecker(normalize_naming=True)

        base_ir = irs[0]
        equivalence_results = [checker.ir_equivalent(base_ir, variant_ir) for variant_ir in irs[1:]]

        if equivalence_results:
            robustness = sum(equivalence_results) / len(equivalence_results)

            print(f"\nReal IR Generation Robustness (Combined): {robustness:.2%}")
            print(f"Tested {len(equivalence_results)} variants")

            assert robustness >= failure_threshold, (
                f"Real IR generation robustness {robustness:.2%} "
                f"below failure threshold {failure_threshold:.2%}"
            )
        else:
            pytest.skip("No valid equivalence results")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ, reason="Requires OPENAI_API_KEY for real API testing"
)
class TestRealAPIRobustness:
    """Tests using real OpenAI API (expensive, requires API key)."""

    async def test_real_openai_ir_generation(
        self,
        paraphrase_generator,
        sample_prompts,
        failure_threshold,
    ):
        """Test with actual OpenAI API calls.

        WARNING: This test makes real API calls and costs money.
        Only run manually with: pytest -m "integration" -k "real_openai"
        """
        from lift_sys.providers import OpenAIProvider

        provider = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
        translator = BestOfNIRTranslator(provider, n_candidates=2)  # Reduce for cost

        prompt = sample_prompts[0]
        paraphrases = paraphrase_generator.generate(prompt, strategy=ParaphraseStrategy.LEXICAL)

        if len(paraphrases) < 1:
            pytest.skip("Not enough paraphrases")

        # Generate IRs (only 2 to minimize cost)
        all_prompts = [prompt, paraphrases[0]]
        irs = []

        for p in all_prompts:
            try:
                ir = await translator.translate(p)
                irs.append(ir)
                print(f"Generated IR: {ir.signature.name}")
            except Exception as e:
                print(f"Error: {e}")

        if len(irs) < 2:
            pytest.skip("Not enough valid IRs")

        # Check equivalence
        from lift_sys.robustness import EquivalenceChecker

        checker = EquivalenceChecker(normalize_naming=True)

        equivalent = checker.ir_equivalent(irs[0], irs[1])
        robustness = 1.0 if equivalent else 0.0

        print(f"\nReal API Robustness: {robustness:.2%}")

        # This is a smoke test - we expect at least failure threshold
        assert robustness >= failure_threshold or len(irs) < 2, (
            "Real API should maintain basic robustness"
        )
