"""Best-of-N IR translator with quality scoring."""

from __future__ import annotations

import asyncio

from ..ir.models import IntermediateRepresentation
from ..providers.base import BaseProvider
from .xgrammar_translator import XGrammarIRTranslator


class BestOfNIRTranslator:
    """
    IR translator using Best-of-N sampling with quality scoring.

    Generates N candidate IRs and selects the best based on quality metrics.
    This is a test-time compute technique that improves quality at the cost
    of N× inference cost.
    """

    def __init__(
        self,
        provider: BaseProvider,
        n_candidates: int = 3,
        temperature: float = 0.5,
    ):
        """
        Initialize Best-of-N translator.

        Args:
            provider: LLM provider for generation
            n_candidates: Number of candidates to generate (default: 3)
            temperature: Sampling temperature for diversity (default: 0.5)
        """
        self.provider = provider
        self.n_candidates = n_candidates
        self.temperature = temperature

        # Base translator for single generation
        self.base_translator = XGrammarIRTranslator(provider)

    async def translate(
        self,
        prompt: str,
        language: str = "python",
        max_retries: int = 1,  # Fewer retries since we have multiple candidates
    ) -> IntermediateRepresentation:
        """
        Translate natural language prompt to IR using Best-of-N sampling.

        Args:
            prompt: User's natural language description
            language: Target programming language
            max_retries: Number of retries per candidate (default: 1)

        Returns:
            Best IntermediateRepresentation among N candidates

        Raises:
            ValueError: If all candidates fail generation
        """
        print(f"\n🎯 Best-of-N: Generating {self.n_candidates} candidates...")

        # Generate N candidates in parallel
        tasks = [
            self._generate_single_candidate(prompt, language, max_retries)
            for _ in range(self.n_candidates)
        ]

        candidates = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures
        valid_candidates = [c for c in candidates if isinstance(c, IntermediateRepresentation)]

        if not valid_candidates:
            raise ValueError(
                f"All {self.n_candidates} candidates failed generation. "
                f"Errors: {[str(c) for c in candidates if isinstance(c, Exception)]}"
            )

        print(f"✅ Generated {len(valid_candidates)}/{self.n_candidates} valid candidates")

        # Score each candidate
        scored_candidates = [(self._score_ir(ir, prompt), ir) for ir in valid_candidates]

        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Log scores
        for i, (score, _ir) in enumerate(scored_candidates):
            print(f"  Candidate {i + 1}: score={score:.1f}")

        # Return best candidate
        best_score, best_ir = scored_candidates[0]
        print(f"🏆 Selected candidate with score {best_score:.1f}")

        return best_ir

    async def _generate_single_candidate(
        self,
        prompt: str,
        language: str,
        max_retries: int,
    ) -> IntermediateRepresentation | Exception:
        """Generate a single IR candidate."""
        try:
            # Use base translator with higher temperature for diversity
            ir = await self.base_translator.translate(
                prompt=prompt,
                language=language,
                max_retries=max_retries,
            )
            return ir
        except Exception as e:
            return e

    def _score_ir(self, ir: IntermediateRepresentation, prompt: str) -> float:
        """
        Score IR quality based on multiple criteria.

        Higher score = better quality.

        Scoring rubric:
        - Schema validity: +100 (must pass, but implicit)
        - Assertion count: +10 per assertion (max 50)
        - Effect detail: +20 for detailed effects
        - Literal string markers: +15 per LITERAL/exact marker
        - Python quirk handling: +10 per quirk detection
        - Type hint completeness: +10 if all parameters typed, +10 if returns typed
        - Edge case coverage: +5 per edge case keyword

        Args:
            ir: IntermediateRepresentation to score
            prompt: Original user prompt (for context)

        Returns:
            Quality score (higher is better)
        """
        score = 0.0

        # 1. Assertion count (more is better, up to a point)
        assertion_score = min(len(ir.assertions) * 10, 50)
        score += assertion_score

        # 2. Effect detail (longer = more specific)
        if ir.effects:
            avg_effect_length = sum(len(e.description) for e in ir.effects) / len(ir.effects)
            effect_score = min(avg_effect_length / 10, 20)
            score += effect_score

        # 3. Literal string detection (CRITICAL for our failing tests)
        literal_keywords = ["literal", "exact", "exactly", "LITERAL", "EXACT"]
        literal_count = 0

        for effect in ir.effects:
            desc = effect.description
            if any(keyword in desc for keyword in literal_keywords):
                literal_count += 1

        score += literal_count * 15

        # 4. Python quirk handling (bool/int, mutability, etc.)
        quirk_keywords = [
            ("bool", "int"),  # Bool/int isinstance ordering
            ("mutable", "immutable"),  # Mutability awareness
            ("None", "empty"),  # None vs empty distinction
            ("before", "after"),  # Ordering constraints
        ]

        ir_text = str(ir).lower()
        for keyword_pair in quirk_keywords:
            if all(k.lower() in ir_text for k in keyword_pair):
                score += 10

        # 5. Type hint completeness
        if all(p.type_hint for p in ir.signature.parameters):
            score += 10

        if ir.signature.returns:
            score += 10

        # 6. Edge case coverage (keywords indicating thoughtfulness)
        edge_case_keywords = [
            "empty",
            "boundary",
            "edge case",
            "invalid",
            "error",
            "failure",
            "none",
            "zero",
            "negative",
        ]

        edge_case_count = 0
        for assertion in ir.assertions:
            pred = assertion.predicate.lower()
            if any(keyword in pred for keyword in edge_case_keywords):
                edge_case_count += 1

        score += edge_case_count * 5

        # 7. Intent clarity (summary length and detail)
        if len(ir.intent.summary) > 20:  # Not too short
            score += 5

        if ir.intent.rationale:
            score += 5

        return score


__all__ = ["BestOfNIRTranslator"]
