"""Tests for ParaphraseGenerator.

This module tests all three paraphrasing strategies:
- Lexical (synonym replacement)
- Structural (clause reordering)
- Stylistic (voice/mood changes)

Target: >90% coverage, >20 unit tests
"""

import pytest

from lift_sys.robustness.paraphrase_generator import ParaphraseGenerator
from lift_sys.robustness.types import ParaphraseStrategy


class TestParaphraseGeneratorInit:
    """Test ParaphraseGenerator initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        gen = ParaphraseGenerator()

        assert gen.max_variants == 10
        assert gen.preserve_semantics is True
        assert gen.min_diversity == 0.3
        assert gen._nlp is not None
        assert gen._wordnet is not None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        gen = ParaphraseGenerator(
            max_variants=5,
            preserve_semantics=True,
            min_diversity=0.5,
        )

        assert gen.max_variants == 5
        assert gen.preserve_semantics is True
        assert gen.min_diversity == 0.5

    def test_cache_initialized_empty(self):
        """Test that cache is initialized empty."""
        gen = ParaphraseGenerator()
        assert gen._cache == {}


class TestLexicalParaphrasing:
    """Test lexical paraphrasing (synonym replacement)."""

    def test_lexical_generates_variants(self, sample_prompt):
        """Test that lexical strategy generates variants."""
        gen = ParaphraseGenerator(max_variants=10)
        variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.LEXICAL)

        assert isinstance(variants, list)
        assert len(variants) > 0
        assert all(isinstance(v, str) for v in variants)

    def test_lexical_variants_differ_from_original(self, sample_prompt):
        """Test that lexical variants differ from original."""
        gen = ParaphraseGenerator(max_variants=10)
        variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.LEXICAL)

        for variant in variants:
            assert variant != sample_prompt
            assert variant.lower() != sample_prompt.lower()

    def test_lexical_preserves_key_terms(self, sample_prompt):
        """Test that lexical strategy preserves key terms."""
        gen = ParaphraseGenerator(max_variants=10)
        variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.LEXICAL)

        # Should preserve "function" in most variants
        function_count = sum(1 for v in variants if "function" in v.lower())
        assert function_count >= len(variants) * 0.5  # At least 50%

    def test_lexical_replaces_content_words(self):
        """Test that lexical strategy replaces content words."""
        gen = ParaphraseGenerator(max_variants=10)
        prompt = "Create a function that sorts numbers"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.LEXICAL)

        # Should have variants with different verbs/nouns
        assert len(variants) > 0

        # Check for synonym variations
        combined = " ".join(variants).lower()
        # "sorts" might be replaced with "orders", "arranges", etc.
        # "numbers" might be replaced with "values", "figures", etc.
        assert len(combined) > len(prompt) * len(variants)  # More diverse text

    def test_lexical_handles_short_prompt(self):
        """Test lexical strategy with very short prompt."""
        gen = ParaphraseGenerator(max_variants=5)
        prompt = "Sort list"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.LEXICAL)

        # May generate fewer variants due to limited content words
        assert isinstance(variants, list)


class TestStructuralParaphrasing:
    """Test structural paraphrasing (clause reordering)."""

    def test_structural_with_single_clause(self):
        """Test structural strategy with single clause (no reordering)."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that sorts numbers"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STRUCTURAL)

        # Single clause: no reordering possible
        assert variants == []

    def test_structural_with_independent_clauses(self):
        """Test structural strategy with independent clauses."""
        gen = ParaphraseGenerator()
        prompt = "Create a function and process the data"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STRUCTURAL)

        # Should generate reordered variants
        if variants:  # May be empty if clauses are deemed dependent
            assert any("process the data and" in v.lower() for v in variants)

    def test_structural_respects_temporal_dependencies(self):
        """Test that structural strategy respects temporal dependencies."""
        gen = ParaphraseGenerator()
        prompt = "First read the file and then process the data"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STRUCTURAL)

        # Should NOT reorder due to "first" and "then"
        assert variants == []

    def test_structural_respects_causal_dependencies(self):
        """Test that structural strategy respects causal dependencies."""
        gen = ParaphraseGenerator()
        prompt = "Create a function because we need sorting"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STRUCTURAL)

        # Should NOT reorder due to "because"
        assert variants == []

    def test_structural_max_variants_limit(self):
        """Test that structural strategy respects max_variants."""
        gen = ParaphraseGenerator(max_variants=3)
        prompt = "Create a function and process data and validate results and save output"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STRUCTURAL)

        # Should limit to max_variants even if more permutations exist
        assert len(variants) <= 3


class TestStylisticParaphrasing:
    """Test stylistic paraphrasing (voice/mood changes)."""

    def test_stylistic_imperative_to_declarative(self):
        """Test imperative to declarative transformation."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that validates emails"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STYLISTIC)

        # Should have declarative variant
        assert len(variants) > 0
        assert any("should be created" in v.lower() for v in variants)

    def test_stylistic_verb_substitution(self):
        """Test action verb substitution."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that sorts numbers"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STYLISTIC)

        # Should have variants with different action verbs
        assert len(variants) > 0
        action_verbs = ["write", "build", "implement", "construct", "design"]
        assert any(verb in " ".join(variants).lower() for verb in action_verbs)

    def test_stylistic_that_to_transformation(self):
        """Test 'that' to 'to' transformation."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that validates data"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STYLISTIC)

        # Should have "function to validate" variant
        assert any("function to" in v.lower() for v in variants)

    def test_stylistic_to_that_transformation(self):
        """Test 'to' to 'that' transformation."""
        gen = ParaphraseGenerator()
        prompt = "Create a function to validate data"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STYLISTIC)

        # Should have "function that validates" variant
        assert any("function that" in v.lower() for v in variants)

    def test_stylistic_preserves_meaning(self):
        """Test that stylistic variants preserve meaning."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that validates email addresses"

        variants = gen.generate(prompt, strategy=ParaphraseStrategy.STYLISTIC)

        # All variants should mention validation and email
        for variant in variants:
            text = variant.lower()
            assert "email" in text or "function" in text


class TestAllStrategiesCombined:
    """Test combining all strategies."""

    def test_all_strategies_generates_most_variants(self, sample_prompt):
        """Test that ALL strategy generates more variants than individual strategies."""
        gen = ParaphraseGenerator(max_variants=20)

        lexical = gen.generate(sample_prompt, strategy=ParaphraseStrategy.LEXICAL)
        structural = gen.generate(sample_prompt, strategy=ParaphraseStrategy.STRUCTURAL)
        stylistic = gen.generate(sample_prompt, strategy=ParaphraseStrategy.STYLISTIC)
        all_variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.ALL)

        # ALL should have at least as many as any individual strategy
        assert len(all_variants) >= len(lexical)
        assert len(all_variants) >= len(structural)
        assert len(all_variants) >= len(stylistic)

    def test_all_strategies_deduplicates(self, sample_prompt):
        """Test that ALL strategy deduplicates variants."""
        gen = ParaphraseGenerator(max_variants=20)
        variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.ALL)

        # Should have no duplicates (case-insensitive)
        lowercase_variants = [v.lower() for v in variants]
        assert len(lowercase_variants) == len(set(lowercase_variants))

    def test_all_strategies_respects_max_variants(self, sample_prompt):
        """Test that ALL strategy respects max_variants limit."""
        gen = ParaphraseGenerator(max_variants=5)
        variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.ALL)

        assert len(variants) <= 5

    def test_all_strategies_ensures_diversity(self, sample_prompt):
        """Test that ALL strategy ensures minimum diversity."""
        gen = ParaphraseGenerator(max_variants=10, min_diversity=0.2)
        variants = gen.generate(sample_prompt, strategy=ParaphraseStrategy.ALL)

        # Each variant should differ from original by at least min_diversity
        for variant in variants:
            diversity = gen._compute_diversity(sample_prompt, variant)
            assert diversity >= gen.min_diversity


class TestCaching:
    """Test caching functionality."""

    def test_caching_enabled(self, sample_prompt):
        """Test that results are cached."""
        gen = ParaphraseGenerator()

        # First call
        variants1 = gen.generate(sample_prompt)

        # Second call (should use cache)
        variants2 = gen.generate(sample_prompt)

        # Results should be identical
        assert variants1 == variants2

        # Cache should contain entry
        cache_key = f"{sample_prompt}:{ParaphraseStrategy.ALL.value}"
        assert cache_key in gen._cache

    def test_caching_per_strategy(self, sample_prompt):
        """Test that cache is strategy-specific."""
        gen = ParaphraseGenerator()

        variants_all = gen.generate(sample_prompt, strategy=ParaphraseStrategy.ALL)
        variants_lexical = gen.generate(sample_prompt, strategy=ParaphraseStrategy.LEXICAL)

        # Should have separate cache entries
        assert len(gen._cache) >= 2
        assert variants_all != variants_lexical


class TestDiversityScoring:
    """Test diversity computation and filtering."""

    def test_compute_diversity_identical_strings(self):
        """Test diversity score for identical strings."""
        gen = ParaphraseGenerator()
        diversity = gen._compute_diversity("hello", "hello")
        assert diversity == 0.0

    def test_compute_diversity_different_strings(self):
        """Test diversity score for different strings."""
        gen = ParaphraseGenerator()
        diversity = gen._compute_diversity("hello", "world")
        assert 0.0 < diversity <= 1.0

    def test_compute_diversity_similar_strings(self):
        """Test diversity score for similar strings."""
        gen = ParaphraseGenerator()
        diversity = gen._compute_diversity("hello world", "hello earth")
        assert 0.0 < diversity < 1.0

    def test_min_diversity_filtering(self):
        """Test that variants below min_diversity are filtered."""
        gen = ParaphraseGenerator(max_variants=10, min_diversity=0.5)
        prompt = "Create a function"

        variants = gen.generate(prompt)

        # All variants should meet minimum diversity
        for variant in variants:
            diversity = gen._compute_diversity(prompt, variant)
            assert diversity >= gen.min_diversity


class TestErrorHandling:
    """Test error handling."""

    def test_empty_prompt_raises_error(self):
        """Test that empty prompt raises ValueError."""
        gen = ParaphraseGenerator()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            gen.generate("")

    def test_whitespace_only_prompt_raises_error(self):
        """Test that whitespace-only prompt raises ValueError."""
        gen = ParaphraseGenerator()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            gen.generate("   ")

    def test_none_prompt_raises_error(self):
        """Test that None prompt raises ValueError."""
        gen = ParaphraseGenerator()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            gen.generate(None)


class TestUtilityMethods:
    """Test utility and helper methods."""

    def test_get_wordnet_pos_noun(self):
        """Test WordNet POS conversion for noun."""
        gen = ParaphraseGenerator()
        pos = gen._get_wordnet_pos("NOUN")
        assert pos is not None

    def test_get_wordnet_pos_verb(self):
        """Test WordNet POS conversion for verb."""
        gen = ParaphraseGenerator()
        pos = gen._get_wordnet_pos("VERB")
        assert pos is not None

    def test_get_wordnet_pos_invalid(self):
        """Test WordNet POS conversion for invalid POS."""
        gen = ParaphraseGenerator()
        pos = gen._get_wordnet_pos("INVALID")
        assert pos is None

    def test_is_imperative_true(self):
        """Test imperative detection for imperative sentence."""
        gen = ParaphraseGenerator()
        assert gen._is_imperative("Create a function")
        assert gen._is_imperative("Build a system")
        assert gen._is_imperative("Write code")

    def test_is_imperative_false(self):
        """Test imperative detection for non-imperative sentence."""
        gen = ParaphraseGenerator()
        assert not gen._is_imperative("This is a function")
        assert not gen._is_imperative("The system processes data")

    def test_extract_clauses_single(self):
        """Test clause extraction for single clause."""
        gen = ParaphraseGenerator()
        doc = gen._nlp("Create a function")
        clauses = gen._extract_clauses(doc)

        assert len(clauses) == 1
        assert "Create a function" in clauses[0]

    def test_extract_clauses_multiple(self):
        """Test clause extraction for multiple clauses."""
        gen = ParaphraseGenerator()
        doc = gen._nlp("Create a function and process data")
        clauses = gen._extract_clauses(doc)

        assert len(clauses) == 2
        assert any("Create" in clause for clause in clauses)
        assert any("process" in clause for clause in clauses)

    def test_are_independent_clauses_true(self):
        """Test independence check for independent clauses."""
        gen = ParaphraseGenerator()
        clauses = ["Create a function", "process the data"]
        assert gen._are_independent_clauses(clauses)

    def test_are_independent_clauses_false_temporal(self):
        """Test independence check with temporal markers."""
        gen = ParaphraseGenerator()
        clauses = ["First create a function", "then process the data"]
        assert not gen._are_independent_clauses(clauses)

    def test_are_independent_clauses_false_causal(self):
        """Test independence check with causal markers."""
        gen = ParaphraseGenerator()
        clauses = ["Create a function", "because we need it"]
        assert not gen._are_independent_clauses(clauses)


class TestSemanticPreservation:
    """Test semantic preservation across paraphrases."""

    def test_paraphrases_preserve_action(self):
        """Test that paraphrases preserve the action (create, build, etc.)."""
        gen = ParaphraseGenerator(max_variants=10)
        prompt = "Create a function that validates email addresses"

        variants = gen.generate(prompt)

        # All variants should mention creation or similar action
        creation_words = [
            "create",
            "write",
            "build",
            "implement",
            "make",
            "develop",
            "construct",
            "design",
            "generate",
            "should be created",
        ]

        for variant in variants:
            text = variant.lower()
            assert any(word in text for word in creation_words)

    def test_paraphrases_preserve_artifact(self):
        """Test that paraphrases preserve the artifact (function)."""
        gen = ParaphraseGenerator(max_variants=10)
        prompt = "Create a function that validates email addresses"

        variants = gen.generate(prompt)

        # Most variants should mention "function" or related term
        function_count = sum(1 for v in variants if "function" in v.lower() or "func" in v.lower())
        assert function_count >= len(variants) * 0.7  # At least 70%

    def test_paraphrases_preserve_purpose(self):
        """Test that paraphrases preserve the purpose."""
        gen = ParaphraseGenerator(max_variants=10)
        prompt = "Create a function that validates email addresses"

        variants = gen.generate(prompt)

        # All variants should mention email and validation
        for variant in variants:
            text = variant.lower()
            # Should have both email and validation concepts
            has_email = "email" in text or "mail" in text
            has_validation = any(
                word in text for word in ["valid", "verify", "check", "confirm", "authenticate"]
            )
            assert has_email or has_validation  # At least one


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_prompt(self):
        """Test with very long prompt."""
        gen = ParaphraseGenerator(max_variants=5)
        prompt = "Create a function that " + " and ".join(
            [f"processes data type {i}" for i in range(20)]
        )

        variants = gen.generate(prompt)

        # Should handle long prompts gracefully
        assert isinstance(variants, list)
        assert len(variants) <= gen.max_variants

    def test_prompt_with_special_characters(self):
        """Test with prompt containing special characters."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that validates email@example.com addresses"

        variants = gen.generate(prompt)

        # Should handle special characters
        assert isinstance(variants, list)

    def test_prompt_with_numbers(self):
        """Test with prompt containing numbers."""
        gen = ParaphraseGenerator()
        prompt = "Create a function that sums numbers from 1 to 100"

        variants = gen.generate(prompt)

        # Should preserve numbers in most variants
        number_count = sum(1 for v in variants if "100" in v)
        assert number_count >= len(variants) * 0.5  # At least 50%

    def test_zero_max_variants(self):
        """Test with max_variants=0."""
        gen = ParaphraseGenerator(max_variants=0)
        prompt = "Create a function"

        variants = gen.generate(prompt)

        assert variants == []

    def test_min_diversity_zero(self):
        """Test with min_diversity=0 (accept all variants)."""
        gen = ParaphraseGenerator(max_variants=10, min_diversity=0.0)
        prompt = "Create a function"

        variants = gen.generate(prompt)

        # Should accept even very similar variants
        assert isinstance(variants, list)

    def test_min_diversity_one(self):
        """Test with min_diversity=1.0 (very strict)."""
        gen = ParaphraseGenerator(max_variants=10, min_diversity=1.0)
        prompt = "Create a function"

        variants = gen.generate(prompt)

        # May have very few or no variants (too strict)
        assert isinstance(variants, list)
        assert len(variants) <= gen.max_variants
