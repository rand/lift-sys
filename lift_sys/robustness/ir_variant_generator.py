"""IR variant generator for robustness testing.

This module generates semantic-preserving variants of IR objects through:
1. Naming convention transformations (snake_case, camelCase, PascalCase, SCREAMING_SNAKE_CASE)
2. Effect reordering (respecting dependencies)
3. Assertion rephrasing (logically equivalent forms)

Inspired by TokDrift research (arXiv:2510.14972):
https://github.com/uw-swag/tokdrift
"""

import re

import networkx as nx

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.robustness.types import NamingStyle


class IRVariantGenerator:
    """Generates semantic-preserving IR variants.

    This class provides methods to generate IR variants through:
    - Naming convention rewriting (all identifiers)
    - Effect reordering (respecting dependencies)
    - Assertion rephrasing (logical equivalence)

    Example:
        >>> gen = IRVariantGenerator()
        >>> variants = gen.generate_naming_variants(ir)
        >>> len(variants)
        4  # One per NamingStyle
    """

    def __init__(self, max_variants: int = 5):
        """Initialize generator.

        Args:
            max_variants: Maximum number of variants to generate per method
        """
        self.max_variants = max_variants

    def generate_naming_variants(
        self, ir: IntermediateRepresentation
    ) -> list[IntermediateRepresentation]:
        """Generate IR variants with different naming conventions.

        Converts all identifiers in the IR to each naming style:
        - snake_case
        - camelCase
        - PascalCase
        - SCREAMING_SNAKE_CASE

        Args:
            ir: Original IR

        Returns:
            List of IR variants, one per naming style
        """
        variants = []

        for style in NamingStyle:
            variant_ir = self._rewrite_naming(ir, style)
            variants.append(variant_ir)

        return variants

    def generate_effect_orderings(
        self, ir: IntermediateRepresentation
    ) -> list[IntermediateRepresentation]:
        """Generate IR variants with reordered effects.

        Only reorders effects that are independent. Uses dependency graph
        analysis to find valid topological orderings.

        Args:
            ir: Original IR

        Returns:
            List of IR variants with different effect orderings (max: max_variants)
        """
        if not ir.effects or len(ir.effects) <= 1:
            return []  # No reordering possible

        # Build dependency graph
        dep_graph = self._build_effect_dependency_graph(ir.effects)

        # Find valid orderings
        valid_orderings = self._find_valid_orderings(dep_graph, ir.effects)

        # Generate IR for each valid ordering
        variants = []
        for ordering in valid_orderings[: self.max_variants]:
            # Create new IR with reordered effects
            ir_dict = ir.to_dict()
            ir_dict["effects"] = [effect.to_dict() for effect in ordering]
            variant_ir = IntermediateRepresentation.from_dict(ir_dict)
            variants.append(variant_ir)

        return variants

    def generate_assertion_variants(
        self, ir: IntermediateRepresentation
    ) -> list[IntermediateRepresentation]:
        """Generate IR variants with rephrased assertions.

        Rephrases assertions in logically equivalent ways:
        - "x > 0" → "x >= 1" (for integers)
        - "len(lst) > 0" → "lst != []"
        - "result == True" → "result"

        Args:
            ir: Original IR

        Returns:
            List of IR variants with rephrased assertions
        """
        if not ir.assertions:
            return []

        variants = []

        # Generate variants by rephrasing each assertion
        for i, assertion in enumerate(ir.assertions):
            rephrased_list = self._rephrase_assertion(assertion.predicate)

            for rephrased in rephrased_list:
                # Create new IR with rephrased assertion
                ir_dict = ir.to_dict()
                ir_dict["assertions"][i]["predicate"] = rephrased
                variant_ir = IntermediateRepresentation.from_dict(ir_dict)
                variants.append(variant_ir)

                if len(variants) >= self.max_variants:
                    return variants

        return variants

    def generate_variants(
        self, ir: IntermediateRepresentation, max_variants: int = 5
    ) -> list[IntermediateRepresentation]:
        """Generate all types of IR variants.

        Combines naming, effect, and assertion variants.

        Args:
            ir: Original IR
            max_variants: Maximum total variants to return

        Returns:
            List of IR variants (all types)
        """
        variants = []

        # Add naming variants
        variants.extend(self.generate_naming_variants(ir))

        # Add effect variants
        variants.extend(self.generate_effect_orderings(ir))

        # Add assertion variants
        variants.extend(self.generate_assertion_variants(ir))

        return variants[:max_variants]

    def _rewrite_naming(
        self, ir: IntermediateRepresentation, style: NamingStyle
    ) -> IntermediateRepresentation:
        """Rewrite all identifiers in IR to specified naming style.

        Recursively rewrites:
        - Signature name
        - Parameter names
        - Effect descriptions (identifiers within)
        - Assertion predicates (identifiers within)

        Args:
            ir: Original IR
            style: Target naming style

        Returns:
            New IR with rewritten identifiers
        """
        # Convert to dict for manipulation
        ir_dict = ir.to_dict()

        # Rewrite signature name
        if "signature" in ir_dict and "name" in ir_dict["signature"]:
            ir_dict["signature"]["name"] = self._convert_name(ir_dict["signature"]["name"], style)

        # Rewrite parameter names
        if "signature" in ir_dict and "parameters" in ir_dict["signature"]:
            for param in ir_dict["signature"]["parameters"]:
                if "name" in param:
                    param["name"] = self._convert_name(param["name"], style)

        # Rewrite identifiers in effects (descriptions may contain identifiers)
        if "effects" in ir_dict:
            for effect in ir_dict["effects"]:
                if "description" in effect:
                    effect["description"] = self._rewrite_identifiers_in_text(
                        effect["description"], style
                    )

        # Rewrite identifiers in assertions
        if "assertions" in ir_dict:
            for assertion in ir_dict["assertions"]:
                if "predicate" in assertion:
                    assertion["predicate"] = self._rewrite_identifiers_in_text(
                        assertion["predicate"], style
                    )

        # Reconstruct IR from dict
        return IntermediateRepresentation.from_dict(ir_dict)

    def _rewrite_identifiers_in_text(self, text: str, style: NamingStyle) -> str:
        """Rewrite identifiers in free-form text.

        Finds identifier-like patterns and converts them to target style.

        Args:
            text: Text containing identifiers
            style: Target naming style

        Returns:
            Text with rewritten identifiers
        """
        # Match Python identifiers (simplified)
        # Pattern: word characters, underscores, but not starting with digit
        pattern = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        def replace_identifier(match):
            word = match.group(0)
            # Don't convert reserved words or single characters
            if (
                word in {"len", "is", "not", "and", "or", "in", "True", "False", "None"}
                or len(word) == 1
            ):
                return word
            return self._convert_name(word, style)

        return re.sub(pattern, replace_identifier, text)

    def _convert_name(self, name: str, style: NamingStyle) -> str:
        """Convert identifier to target naming style.

        Args:
            name: Original identifier
            style: Target naming style

        Returns:
            Converted identifier
        """
        # Parse identifier into words
        words = self._parse_identifier(name)

        if not words:
            return name

        # Convert to target style
        if style == NamingStyle.SNAKE_CASE:
            return "_".join(w.lower() for w in words)
        elif style == NamingStyle.CAMEL_CASE:
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])
        elif style == NamingStyle.PASCAL_CASE:
            return "".join(w.capitalize() for w in words)
        elif style == NamingStyle.SCREAMING_SNAKE:
            return "_".join(w.upper() for w in words)

        return name  # Fallback

    def _parse_identifier(self, name: str) -> list[str]:
        """Parse identifier into words.

        Handles:
        - snake_case: split on underscores
        - camelCase/PascalCase: split on case changes
        - SCREAMING_SNAKE_CASE: split on underscores, lowercase

        Args:
            name: Identifier to parse

        Returns:
            List of words
        """
        if not name:
            return []

        # Handle snake_case (including SCREAMING_SNAKE_CASE)
        if "_" in name:
            return [word.lower() for word in name.split("_") if word]

        # Handle camelCase/PascalCase
        # Pattern matches:
        # - Lowercase letters followed by uppercase (camelCase boundary)
        # - Multiple uppercase letters followed by lowercase (acronyms)
        # - Numbers
        words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+", name)

        if words:
            return [w.lower() for w in words]

        # Single word, no special casing
        return [name.lower()]

    def _build_effect_dependency_graph(self, effects: list) -> nx.DiGraph:
        """Build directed graph of effect dependencies.

        Creates graph where:
        - Each node is an effect index
        - Edge (i, j) means effect j depends on effect i

        Args:
            effects: List of EffectClause objects

        Returns:
            NetworkX directed graph
        """
        graph = nx.DiGraph()

        # Add nodes
        for i in range(len(effects)):
            graph.add_node(i)

        # Add edges for dependencies
        for i in range(len(effects)):
            for j in range(len(effects)):
                if i != j and self._depends_on(effects[j], effects[i]):
                    graph.add_edge(i, j)  # j depends on i

        return graph

    def _depends_on(self, effect_a, effect_b) -> bool:
        """Check if effect_a depends on effect_b.

        Heuristic-based dependency detection:
        - File operations: write depends on read if same target
        - Database operations: similar logic
        - Generic: check if effect_a description references effect_b

        Args:
            effect_a: First EffectClause
            effect_b: Second EffectClause

        Returns:
            True if effect_a depends on effect_b
        """
        desc_a = effect_a.description.lower()
        desc_b = effect_b.description.lower()

        # File operations
        if "write" in desc_a and "read" in desc_b:
            # Check if they reference same file (heuristic: same words)
            words_a = set(desc_a.split())
            words_b = set(desc_b.split())
            if words_a & words_b:  # Non-empty intersection
                return True

        # Database operations
        if "database" in desc_a and "database" in desc_b:
            if "write" in desc_a and "read" in desc_b:
                return True

        # Generic: check if effect_a description contains effect_b keywords
        # (conservative: assume dependency if descriptions overlap significantly)
        if desc_b in desc_a:
            return True

        return False

    def _find_valid_orderings(self, graph: nx.DiGraph, effects: list) -> list[list]:
        """Find all valid topological orderings.

        Uses networkx to find topological sorts respecting dependencies.

        Args:
            graph: Dependency graph
            effects: Original effects list

        Returns:
            List of valid effect orderings
        """
        # Check if graph is DAG (required for topological sort)
        if not nx.is_directed_acyclic_graph(graph):
            # Circular dependencies - return original ordering only
            return [effects]

        # Get all topological orderings
        orderings = []
        try:
            # all_topological_sorts returns generator
            for ordering_indices in nx.all_topological_sorts(graph):
                # Convert indices back to effects
                ordering = [effects[i] for i in ordering_indices]
                orderings.append(ordering)

                # Limit number of orderings
                if len(orderings) >= self.max_variants * 2:
                    break
        except nx.NetworkXError:
            # Fallback: single ordering
            orderings = [effects]

        # Remove duplicates (same ordering)
        unique_orderings = []
        seen = set()
        for ordering in orderings:
            # Create hashable representation
            ordering_key = tuple(e.description for e in ordering)
            if ordering_key not in seen:
                seen.add(ordering_key)
                unique_orderings.append(ordering)

        return unique_orderings

    def _rephrase_assertion(self, predicate: str) -> list[str]:
        """Rephrase assertion in logically equivalent ways.

        Transformations:
        - "x > 0" → "x >= 1" (integers)
        - "len(x) > 0" → "x != []"
        - "x == True" → "x"
        - "x == False" → "not x"

        Args:
            predicate: Original assertion predicate

        Returns:
            List of rephrased predicates
        """
        variants = []

        # Pattern 1: x > 0 → x >= 1 (for integers)
        if re.search(r"\b(\w+)\s*>\s*0\b", predicate):
            variant = re.sub(r"\b(\w+)\s*>\s*0\b", r"\1 >= 1", predicate)
            variants.append(variant)

        # Pattern 2: x >= 1 → x > 0
        if re.search(r"\b(\w+)\s*>=\s*1\b", predicate):
            variant = re.sub(r"\b(\w+)\s*>=\s*1\b", r"\1 > 0", predicate)
            variants.append(variant)

        # Pattern 3: len(x) > 0 → x != []
        if re.search(r"len\((\w+)\)\s*>\s*0", predicate):
            variant = re.sub(r"len\((\w+)\)\s*>\s*0", r"\1 != []", predicate)
            variants.append(variant)

        # Pattern 4: x == True → x
        if re.search(r"\b(\w+)\s*==\s*True\b", predicate):
            variant = re.sub(r"\b(\w+)\s*==\s*True\b", r"\1", predicate)
            variants.append(variant)

        # Pattern 5: x == False → not x
        if re.search(r"\b(\w+)\s*==\s*False\b", predicate):
            variant = re.sub(r"\b(\w+)\s*==\s*False\b", r"not \1", predicate)
            variants.append(variant)

        # Pattern 6: not x → x == False
        if re.search(r"\bnot\s+(\w+)\b", predicate) and "not in" not in predicate.lower():
            variant = re.sub(r"\bnot\s+(\w+)\b", r"\1 == False", predicate)
            variants.append(variant)

        return variants


__all__ = ["IRVariantGenerator"]
