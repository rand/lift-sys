"""Generate semantic-preserving paraphrases of NL prompts.

This module provides tools for generating diverse paraphrases of natural language
prompts using three strategies:
1. Lexical: Synonym replacement using WordNet
2. Structural: Clause reordering
3. Stylistic: Voice and mood transformations

The paraphrases are designed to be semantically equivalent to the original while
providing sufficient diversity for robustness testing.
"""

from __future__ import annotations

import itertools
from typing import Any

from lift_sys.robustness.types import ParaphraseStrategy
from lift_sys.robustness.utils import edit_distance


class ParaphraseGenerator:
    """Generate semantic-preserving paraphrases of NL prompts.

    This class implements three paraphrasing strategies:
    - Lexical: Replace words with synonyms using WordNet
    - Structural: Reorder independent clauses
    - Stylistic: Transform voice and mood

    Attributes:
        max_variants: Maximum number of paraphrases to generate
        preserve_semantics: Ensure semantic preservation (always True)
        min_diversity: Minimum normalized edit distance from original (0.0-1.0)
    """

    def __init__(
        self,
        max_variants: int = 10,
        preserve_semantics: bool = True,
        min_diversity: float = 0.3,
    ):
        """Initialize paraphrase generator.

        Args:
            max_variants: Maximum number of paraphrases to generate
            preserve_semantics: Whether to preserve semantics (must be True)
            min_diversity: Minimum normalized edit distance from original
        """
        self.max_variants = max_variants
        self.preserve_semantics = preserve_semantics
        self.min_diversity = min_diversity
        self._cache: dict[str, list[str]] = {}
        self._nlp: Any = None
        self._wordnet: Any = None
        self._sentence_model: Any = None  # Lazy-loaded sentence transformer
        self._initialize_nlp()

    def _initialize_nlp(self) -> None:
        """Load spaCy model and NLTK resources."""
        try:
            import spacy

            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Model not found, download it
                import subprocess
                import sys

                subprocess.run(
                    [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
                    check=True,
                    capture_output=True,
                )
                self._nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            raise RuntimeError(f"Failed to load spaCy model: {e}") from e

        try:
            import nltk

            # Download required NLTK data
            for resource in ["wordnet", "averaged_perceptron_tagger", "omw-1.4"]:
                try:
                    nltk.data.find(f"corpora/{resource}")
                except LookupError:
                    nltk.download(resource, quiet=True)

            from nltk.corpus import wordnet

            self._wordnet = wordnet
        except Exception as e:
            raise RuntimeError(f"Failed to load NLTK resources: {e}") from e

    @property
    def sentence_model(self):
        """Lazy-load sentence transformer model for semantic similarity."""
        if self._sentence_model is None:
            from sentence_transformers import SentenceTransformer

            self._sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._sentence_model

    def generate(
        self,
        prompt: str,
        strategy: ParaphraseStrategy = ParaphraseStrategy.ALL,
    ) -> list[str]:
        """Generate paraphrase variants using specified strategy.

        Args:
            prompt: Original prompt to paraphrase
            strategy: Paraphrasing strategy to use

        Returns:
            List of paraphrase variants (up to max_variants)

        Raises:
            ValueError: If prompt is empty or invalid
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Check cache
        cache_key = f"{prompt}:{strategy.value}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Generate variants based on strategy
        if strategy == ParaphraseStrategy.LEXICAL:
            variants = self._generate_lexical(prompt)
        elif strategy == ParaphraseStrategy.STRUCTURAL:
            variants = self._generate_structural(prompt)
        elif strategy == ParaphraseStrategy.STYLISTIC:
            variants = self._generate_stylistic(prompt)
        else:  # ALL
            variants = []
            variants.extend(self._generate_lexical(prompt))
            variants.extend(self._generate_structural(prompt))
            variants.extend(self._generate_stylistic(prompt))

        # Deduplicate and rank
        result = self._deduplicate_and_rank(variants, prompt)

        # Cache result
        self._cache[cache_key] = result

        return result

    def _generate_lexical(self, prompt: str) -> list[str]:
        """Generate variants via synonym replacement.

        Strategy:
        - Parse prompt with spaCy
        - Identify content words (nouns, verbs, adjectives)
        - Find synonyms via WordNet
        - Replace words maintaining POS tags
        - Filter by semantic similarity to preserve meaning

        Args:
            prompt: Original prompt

        Returns:
            List of lexical paraphrases
        """
        doc = self._nlp(prompt)
        variants: list[str] = []

        # Find content words (but avoid replacing critical technical terms)
        content_tokens = [
            token
            for token in doc
            if token.pos_ in ("NOUN", "VERB", "ADJ")
            and not token.is_stop
            and token.text.lower() not in self._get_technical_terms()
        ]

        # Collect all valid (token, synonym) pairs
        replacement_options: list[tuple[Any, list[str]]] = []
        for token in content_tokens:
            wordnet_pos = self._get_wordnet_pos(token.pos_)
            if not wordnet_pos:
                continue

            synsets = self._wordnet.synsets(token.text.lower(), pos=wordnet_pos)

            # Get synonyms from top 2 synsets for better coverage
            # Semantic similarity filter will reject wrong word senses
            synonyms: set[str] = set()
            if synsets:
                # Use top 2 synsets to get more synonym candidates
                for synset in synsets[:2]:
                    for lemma in synset.lemmas()[:5]:  # Top 5 lemmas per synset
                        synonym = lemma.name().replace("_", " ")
                        if synonym.lower() != token.text.lower():
                            # Check if synonym is semantically similar in context
                            if self._is_semantically_similar_synonym(prompt, token.text, synonym):
                                synonyms.add(synonym)

            if synonyms:
                replacement_options.append(
                    (token, list(synonyms)[:2])
                )  # Keep top 2 synonyms per token

        # Generate single-replacement variants
        for token, synonyms in replacement_options:
            for synonym in synonyms:
                variant = self._replace_token(prompt, token, synonym)
                if variant and variant != prompt:
                    variants.append(variant)

        # Generate double-replacement variants for higher diversity
        # Only if we have multiple tokens with synonyms and haven't hit max_variants
        if len(replacement_options) >= 2 and len(variants) < self.max_variants:
            for i, (token1, syns1) in enumerate(replacement_options):
                for j, (token2, syns2) in enumerate(replacement_options):
                    if i < j:  # Avoid duplicates and self-pairs
                        # Try combining first synonym of each token
                        if syns1 and syns2:
                            # Apply first replacement
                            variant = self._replace_token(prompt, token1, syns1[0])
                            # Re-parse to get updated token positions
                            variant_doc = self._nlp(variant)
                            # Find the token to replace in the new doc
                            for variant_token in variant_doc:
                                if (
                                    variant_token.text == token2.text
                                    and variant_token.pos_ == token2.pos_
                                ):
                                    variant = self._replace_token(variant, variant_token, syns2[0])
                                    break
                            if variant and variant != prompt:
                                variants.append(variant)
                                if len(variants) >= self.max_variants:
                                    break
                if len(variants) >= self.max_variants:
                    break

        return variants

    def _generate_structural(self, prompt: str) -> list[str]:
        """Generate variants via clause reordering.

        Strategy:
        - Parse into clauses (coordinating conjunctions)
        - Identify independent clauses
        - Reorder if semantically valid
        - Maintain coherence

        Args:
            prompt: Original prompt

        Returns:
            List of structural paraphrases
        """
        doc = self._nlp(prompt)

        # Extract clauses split by coordinating conjunctions (and, or)
        clauses = self._extract_clauses(doc)

        if len(clauses) < 2:
            return []  # Need at least 2 clauses to reorder

        # Check if clauses are independent (no temporal/causal dependencies)
        if not self._are_independent_clauses(clauses):
            return []

        variants: list[str] = []
        # Generate permutations of clauses
        for permutation in itertools.permutations(clauses):
            if list(permutation) != clauses:  # Skip original order
                variant = " and ".join(perm.strip() for perm in permutation)
                variants.append(variant)
                if len(variants) >= self.max_variants:
                    break

        return variants

    def _generate_stylistic(self, prompt: str) -> list[str]:
        """Generate variants via voice/mood changes.

        Strategy:
        - Detect current voice and mood
        - Apply transformations:
          - Imperative → Declarative: "Create X" → "X should be created"
          - Active → Passive voice transformations
        - Use rule-based templates for common patterns

        Args:
            prompt: Original prompt

        Returns:
            List of stylistic paraphrases
        """
        variants: list[str] = []

        # Imperative → Declarative transformations
        if self._is_imperative(prompt):
            declarative = self._imperative_to_declarative(prompt)
            if declarative:
                variants.append(declarative)

        # Additional stylistic transformations
        # Pattern: "Create a X that Y" → "Write a X that Y"
        for action_verb in ["Create", "Make", "Build", "Implement", "Develop"]:
            if prompt.startswith(action_verb):
                for replacement in ["Write", "Build", "Implement", "Construct", "Design"]:
                    if replacement != action_verb:
                        variant = prompt.replace(action_verb, replacement, 1)
                        variants.append(variant)

        # Pattern: "function that X" → "function to X"
        if " that " in prompt:
            variants.append(prompt.replace(" that ", " to ", 1))

        # Pattern: "function to X" → "function that X"
        if " to " in prompt:
            variants.append(prompt.replace(" to ", " that ", 1))

        return variants

    def _deduplicate_and_rank(self, variants: list[str], original: str) -> list[str]:
        """Remove duplicates and rank by diversity.

        Args:
            variants: List of paraphrase candidates
            original: Original prompt

        Returns:
            Deduplicated and ranked variants (up to max_variants)
        """
        # Remove duplicates (case-insensitive)
        seen: set[str] = {original.lower()}
        unique_variants: list[str] = []

        for variant in variants:
            variant_lower = variant.lower()
            if variant_lower not in seen:
                seen.add(variant_lower)
                unique_variants.append(variant)

        # Filter by diversity
        diverse_variants: list[str] = []
        for variant in unique_variants:
            diversity = self._compute_diversity(original, variant)
            if diversity >= self.min_diversity:
                diverse_variants.append(variant)

        # Adaptive diversity threshold: if we don't have enough variants,
        # progressively lower the threshold to get more variants
        if len(diverse_variants) < 2:
            # Try with half the diversity threshold
            relaxed_threshold = self.min_diversity / 2
            diverse_variants = []
            for variant in unique_variants:
                diversity = self._compute_diversity(original, variant)
                if diversity >= relaxed_threshold:
                    diverse_variants.append(variant)

        # Sort by diversity (higher is better)
        diverse_variants.sort(key=lambda v: self._compute_diversity(original, v), reverse=True)

        return diverse_variants[: self.max_variants]

    def _compute_diversity(self, str1: str, str2: str) -> float:
        """Compute normalized edit distance (diversity score).

        Args:
            str1: First string
            str2: Second string

        Returns:
            Diversity score between 0.0 (identical) and 1.0 (completely different)
        """
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 0.0

        distance = edit_distance(str1, str2)
        return distance / max_len

    def _get_wordnet_pos(self, spacy_pos: str) -> str | None:
        """Convert spaCy POS tag to WordNet POS tag.

        Args:
            spacy_pos: spaCy POS tag

        Returns:
            WordNet POS tag or None
        """
        from nltk.corpus.reader.wordnet import ADJ, ADV, NOUN, VERB

        pos_map = {
            "NOUN": NOUN,
            "VERB": VERB,
            "ADJ": ADJ,
            "ADV": ADV,
        }
        return pos_map.get(spacy_pos)

    def _replace_token(self, text: str, token: Any, replacement: str) -> str:
        """Replace a token in text with replacement, preserving case.

        Args:
            text: Original text
            token: spaCy token to replace
            replacement: Replacement text

        Returns:
            Text with token replaced
        """
        # Preserve case of first character
        if token.text[0].isupper():
            replacement = replacement.capitalize()

        # Replace using position indices
        start = token.idx
        end = start + len(token.text)
        return text[:start] + replacement + text[end:]

    def _extract_clauses(self, doc: Any) -> list[str]:
        """Extract clauses from spaCy doc.

        Args:
            doc: spaCy Doc object

        Returns:
            List of clause strings
        """
        clauses: list[str] = []
        current_clause: list[str] = []

        for token in doc:
            # Split on coordinating conjunctions
            if token.pos_ == "CCONJ" and token.text.lower() in ("and", "or"):
                if current_clause:
                    clauses.append(" ".join(current_clause))
                    current_clause = []
            else:
                current_clause.append(token.text)

        # Add final clause
        if current_clause:
            clauses.append(" ".join(current_clause))

        return clauses

    def _are_independent_clauses(self, clauses: list[str]) -> bool:
        """Check if clauses are independent (no temporal/causal dependencies).

        Args:
            clauses: List of clause strings

        Returns:
            True if clauses can be safely reordered
        """
        # Heuristic: Check for temporal/causal markers
        temporal_markers = ["first", "then", "after", "before", "finally", "next"]
        causal_markers = ["because", "since", "so", "therefore", "thus"]

        text = " ".join(clauses).lower()
        for marker in temporal_markers + causal_markers:
            if marker in text:
                return False

        return True

    def _is_imperative(self, prompt: str) -> bool:
        """Check if prompt is in imperative mood.

        Args:
            prompt: Prompt text

        Returns:
            True if imperative
        """
        doc = self._nlp(prompt)

        # Imperative sentences typically start with a verb
        if len(doc) > 0 and doc[0].pos_ == "VERB":
            # Common imperative verbs
            imperative_verbs = {
                "create",
                "make",
                "build",
                "write",
                "implement",
                "design",
                "develop",
                "generate",
                "construct",
            }
            return doc[0].text.lower() in imperative_verbs

        return False

    def _imperative_to_declarative(self, prompt: str) -> str | None:
        """Convert imperative to declarative mood.

        Args:
            prompt: Imperative prompt

        Returns:
            Declarative version or None
        """
        doc = self._nlp(prompt)

        if len(doc) == 0:
            return None

        # Pattern: "Create/Make/Build X" → "X should be created/made/built"
        verb_to_passive = {
            "create": "created",
            "make": "made",
            "build": "built",
            "write": "written",
            "implement": "implemented",
            "design": "designed",
            "develop": "developed",
            "generate": "generated",
            "construct": "constructed",
        }

        first_token = doc[0].text.lower()
        if first_token in verb_to_passive:
            # Extract the object phrase (everything after the verb)
            object_phrase = prompt[len(doc[0].text) :].strip()

            # Handle "a X that Y" pattern
            if object_phrase.startswith("a ") or object_phrase.startswith("an "):
                passive_verb = verb_to_passive[first_token]
                return f"{object_phrase.capitalize()} should be {passive_verb}"

        return None

    def _get_technical_terms(self) -> set[str]:
        """Get set of technical terms that should not be replaced.

        These are critical programming/technical terms where synonym replacement
        would change the semantic meaning too much.

        Returns:
            Set of lowercase technical terms to preserve
        """
        return {
            "function",
            "class",
            "method",
            "variable",
            "parameter",
            "argument",
            "return",
            "list",
            "array",
            "dictionary",
            "object",
            "string",
            "integer",
            # Removed "number" - too generic, prevents useful paraphrases
            "boolean",
            "file",
            "database",
            "api",
            "endpoint",
            "request",
            "response",
        }

    def _is_semantically_similar_synonym(
        self, original_text: str, original_word: str, synonym: str
    ) -> bool:
        """Check if a synonym preserves semantic meaning in context.

        Uses sentence embeddings to compare the semantic similarity of the
        original text vs. text with the synonym substituted.

        Args:
            original_text: Original prompt text
            original_word: Original word being replaced
            synonym: Proposed synonym replacement

        Returns:
            True if synonym preserves semantic meaning (similarity >= 0.85)
        """
        from sklearn.metrics.pairwise import cosine_similarity

        # Reject multi-word synonyms that contain the original word
        # Example: "numbers" → "Book of Numbers" (wrong sense!)
        if " " in synonym and original_word.lower() in synonym.lower():
            return False

        # Create variant with synonym
        variant_text = original_text.replace(original_word, synonym, 1)

        # Get embeddings
        emb1 = self.sentence_model.encode([original_text])
        emb2 = self.sentence_model.encode([variant_text])

        # Compute similarity
        similarity = cosine_similarity(emb1, emb2)[0][0]

        # Require high similarity (>= 0.75) to accept synonym
        # Lower threshold allows more lexical variants while still filtering
        # semantically incorrect ones (e.g., "Book of Numbers")
        return similarity >= 0.75
