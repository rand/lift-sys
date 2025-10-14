"""Semantic context enhancement for code generation.

This module provides semantic context (types, imports, codebase patterns)
to improve code generation quality. It simulates what an LSP-based system
like ChatLSP would provide.

For PoC 2, this uses a knowledge base approach. In production, this would
integrate with actual LSP servers (pyright, typescript-language-server, etc.)

The relevance ranking system scores symbols based on:
- Keyword matching (60% weight)
- Semantic similarity (30% weight)
- Usage frequency (10% weight, placeholder for future)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TypeInfo:
    """Information about a type available in the codebase."""

    name: str
    module: str
    description: str
    example_usage: str | None = None


@dataclass
class FunctionInfo:
    """Information about a function available in the codebase."""

    name: str
    module: str
    signature: str
    description: str


@dataclass
class ImportPattern:
    """Common import pattern in the codebase."""

    module: str
    common_imports: list[str]
    usage_context: str


@dataclass
class RelevanceScore:
    """Relevance score with breakdown for a symbol.

    Attributes:
        total: Combined weighted score (0.0-1.0)
        keyword_match: Keyword matching score (0.0-1.0)
        semantic_similarity: Semantic pattern similarity (0.0-1.0)
        usage_frequency: Usage frequency score (0.0-1.0, placeholder)
    """

    total: float
    keyword_match: float
    semantic_similarity: float
    usage_frequency: float


def _split_camel_case(name: str) -> list[str]:
    """Split camelCase or PascalCase name into parts.

    Args:
        name: Name to split (e.g., "UserValidator")

    Returns:
        List of lowercase parts (e.g., ["user", "validator"])
    """
    import re

    # Insert space before uppercase letters, then split
    parts = re.sub(r"([A-Z])", r" \1", name).split()
    return [p.lower() for p in parts if p]


def compute_relevance(
    symbol_name: str,
    symbol_type: str,
    keywords: list[str],
    intent_summary: str,
) -> RelevanceScore:
    """Compute relevance score for a symbol based on intent.

    Scores symbols using multiple factors:
    - Keyword matching: Exact/partial matches in symbol name
    - Semantic similarity: Pattern-based matching (validation, calculation, etc.)
    - Usage frequency: Placeholder for future usage tracking

    Args:
        symbol_name: Name of type or function (e.g., "validate_email")
        symbol_type: "type" or "function"
        keywords: Extracted keywords from intent
        intent_summary: Full intent description

    Returns:
        RelevanceScore with total weighted score and breakdown
    """
    keyword_match = 0.0
    semantic_similarity = 0.0
    usage_frequency = 0.0  # Placeholder for future enhancement

    name_lower = symbol_name.lower()
    # Split camelCase before lowercasing to preserve word boundaries
    camel_parts = _split_camel_case(symbol_name)
    keywords_matched = 0  # Track number of keywords that match

    # Keyword matching (0.0-1.0)
    for keyword in keywords:
        keyword_lower = keyword.lower()
        matched_this_keyword = False

        if keyword_lower == name_lower:
            # Exact match: highest score
            keyword_match = 1.0
            matched_this_keyword = True
            keywords_matched += 1
            break
        elif keyword_lower in name_lower:
            # Substring match: high score
            keyword_match = max(keyword_match, 0.7)
            matched_this_keyword = True
        elif name_lower in keyword_lower:
            # Reverse substring match: moderate score
            keyword_match = max(keyword_match, 0.5)
            matched_this_keyword = True
        else:
            # Check for partial word matches with stem-like matching
            name_parts = name_lower.split("_")
            for part in name_parts:
                # Direct substring match in word part
                if keyword_lower in part or part in keyword_lower:
                    keyword_match = max(keyword_match, 0.4)
                    matched_this_keyword = True
                    break
                # Stem-like matching: check common prefixes for word variations
                # e.g., "validate" matches "validation", "validator"
                min_len = min(len(keyword_lower), len(part))
                if min_len >= 5:  # Only for words of reasonable length
                    # Check if first 5+ chars match (handles validate/validation/validator)
                    common_prefix = 0
                    for i in range(min_len):
                        if keyword_lower[i] == part[i]:
                            common_prefix += 1
                        else:
                            break
                    if common_prefix >= 5:
                        keyword_match = max(keyword_match, 0.4)
                        matched_this_keyword = True
                        break

        if matched_this_keyword:
            keywords_matched += 1

    # Add bonus for matching multiple keywords (up to +0.2)
    multi_keyword_bonus = min((keywords_matched - 1) * 0.1, 0.2) if keywords_matched > 1 else 0.0
    keyword_match = min(keyword_match + multi_keyword_bonus, 1.0)

    # Semantic similarity heuristics (0.0-1.0)
    # Match common patterns in programming
    intent_lower = intent_summary.lower()
    patterns = {
        "validation": ["validate", "check", "verify", "is_valid", "ensure"],
        "calculation": ["calculate", "compute", "get", "find", "determine"],
        "creation": ["create", "make", "build", "generate", "new"],
        "conversion": ["convert", "transform", "to_", "from_", "as_"],
        "retrieval": ["get", "fetch", "retrieve", "find", "load"],
        "storage": ["save", "store", "write", "persist", "set"],
        "parsing": ["parse", "decode", "read", "extract"],
        "formatting": ["format", "stringify", "encode", "serialize"],
    }

    for pattern_type, pattern_names in patterns.items():
        # Check if intent mentions this pattern
        if pattern_type in intent_lower or any(p in intent_lower for p in pattern_names):
            # Check if symbol name contains pattern indicators (with stem matching)
            for pattern_name in pattern_names:
                if pattern_name in name_lower:
                    semantic_similarity = 0.8
                    break
                # Check word parts for stem matching
                name_parts = name_lower.split("_") + camel_parts
                for part in name_parts:
                    if pattern_name in part or part in pattern_name:
                        semantic_similarity = 0.8
                        break
                    # Stem matching: common prefix for word variations
                    min_len = min(len(pattern_name), len(part))
                    if min_len >= 5:
                        common_prefix = 0
                        for i in range(min_len):
                            if pattern_name[i] == part[i]:
                                common_prefix += 1
                            else:
                                break
                        if common_prefix >= 5:
                            semantic_similarity = 0.8
                            break
                if semantic_similarity > 0:
                    break
            if semantic_similarity > 0:
                break

    # Combine scores with weights
    # Keyword match: 60%, Semantic similarity: 30%, Usage frequency: 10%
    total = (keyword_match * 0.6) + (semantic_similarity * 0.3) + (usage_frequency * 0.1)

    return RelevanceScore(
        total=total,
        keyword_match=keyword_match,
        semantic_similarity=semantic_similarity,
        usage_frequency=usage_frequency,
    )


@dataclass
class SemanticContext:
    """Semantic context about the codebase."""

    available_types: list[TypeInfo]
    available_functions: list[FunctionInfo]
    import_patterns: list[ImportPattern]
    codebase_conventions: dict[str, str]

    def to_prompt_context(self) -> str:
        """
        Convert semantic context to prompt text.

        Returns:
            Formatted context string for LLM prompts
        """
        lines = []

        if self.available_types:
            lines.append("Available Types:")
            for type_info in self.available_types[:5]:  # Limit to top 5
                lines.append(
                    f"  - {type_info.name} (from {type_info.module}): {type_info.description}"
                )
                if type_info.example_usage:
                    lines.append(f"    Example: {type_info.example_usage}")
            lines.append("")

        if self.available_functions:
            lines.append("Available Functions:")
            for func_info in self.available_functions[:5]:  # Limit to top 5
                lines.append(f"  - {func_info.signature} (from {type_info.module})")
                lines.append(f"    {func_info.description}")
            lines.append("")

        if self.import_patterns:
            lines.append("Common Import Patterns:")
            for pattern in self.import_patterns[:3]:  # Limit to top 3
                imports_str = ", ".join(pattern.common_imports)
                lines.append(f"  - from {pattern.module} import {imports_str}")
                lines.append(f"    Use for: {pattern.usage_context}")
            lines.append("")

        if self.codebase_conventions:
            lines.append("Codebase Conventions:")
            for key, value in self.codebase_conventions.items():
                lines.append(f"  - {key}: {value}")
            lines.append("")

        return "\n".join(lines)


class SemanticContextProvider:
    """
    Provides semantic context for code generation.

    In PoC 2, this uses a knowledge base. In production, this would
    integrate with LSP servers for real-time codebase analysis.
    """

    def __init__(self, language: str = "python"):
        """
        Initialize with target language.

        Args:
            language: Programming language (python, typescript, rust, go)
        """
        self.language = language
        self._knowledge_base = self._build_knowledge_base()

    def _build_knowledge_base(self) -> dict[str, Any]:
        """Build knowledge base with common patterns."""
        if self.language == "python":
            return {
                "types": [
                    TypeInfo(
                        name="Pattern",
                        module="re",
                        description="Compiled regular expression pattern",
                        example_usage="pattern = re.compile(r'^[a-z]+')",
                    ),
                    TypeInfo(
                        name="Path",
                        module="pathlib",
                        description="Object-oriented filesystem paths",
                        example_usage="path = Path('/path/to/file')",
                    ),
                    TypeInfo(
                        name="datetime",
                        module="datetime",
                        description="Date and time representation",
                        example_usage="now = datetime.now()",
                    ),
                    TypeInfo(
                        name="Decimal",
                        module="decimal",
                        description="Precise decimal arithmetic",
                        example_usage="price = Decimal('19.99')",
                    ),
                ],
                "functions": [
                    FunctionInfo(
                        name="match",
                        module="re",
                        signature="match(pattern: str, string: str) -> Match | None",
                        description="Match regex pattern at beginning of string",
                    ),
                    FunctionInfo(
                        name="search",
                        module="re",
                        signature="search(pattern: str, string: str) -> Match | None",
                        description="Search for regex pattern anywhere in string",
                    ),
                ],
                "imports": [
                    ImportPattern(
                        module="re",
                        common_imports=["match", "search", "compile", "Pattern"],
                        usage_context="String pattern matching and validation",
                    ),
                    ImportPattern(
                        module="pathlib",
                        common_imports=["Path"],
                        usage_context="File system operations",
                    ),
                    ImportPattern(
                        module="datetime",
                        common_imports=["datetime", "timedelta"],
                        usage_context="Date and time operations",
                    ),
                    ImportPattern(
                        module="typing",
                        common_imports=["Any", "Optional", "Union", "List", "Dict"],
                        usage_context="Type annotations",
                    ),
                ],
                "conventions": {
                    "error_handling": "Use try/except blocks for operations that may fail",
                    "type_hints": "Always include type hints for function parameters and returns",
                    "docstrings": "Use Google-style docstrings with Args and Returns sections",
                    "imports": "Group imports: standard library, third-party, local",
                },
            }
        else:
            # Placeholder for other languages
            return {"types": [], "functions": [], "imports": [], "conventions": {}}

    def get_context_for_intent(self, intent_summary: str) -> SemanticContext:
        """
        Get relevant semantic context based on function intent.

        Args:
            intent_summary: Summary of what the function should do

        Returns:
            Semantic context relevant to the intent
        """
        kb = self._knowledge_base
        intent_lower = intent_summary.lower()

        # Filter types by relevance
        relevant_types = []
        if "email" in intent_lower or "pattern" in intent_lower or "valid" in intent_lower:
            relevant_types.extend([t for t in kb.get("types", []) if t.name == "Pattern"])
        if "file" in intent_lower or "path" in intent_lower:
            relevant_types.extend([t for t in kb.get("types", []) if t.name == "Path"])
        if "time" in intent_lower or "date" in intent_lower:
            relevant_types.extend([t for t in kb.get("types", []) if t.name == "datetime"])
        if "price" in intent_lower or "money" in intent_lower or "decimal" in intent_lower:
            relevant_types.extend([t for t in kb.get("types", []) if t.name == "Decimal"])

        # Filter functions by relevance
        relevant_functions = []
        if "match" in intent_lower or "valid" in intent_lower or "check" in intent_lower:
            relevant_functions.extend(
                [f for f in kb.get("functions", []) if f.name in ["match", "search"]]
            )

        # Filter imports by relevance
        relevant_imports = []
        if any(
            keyword in intent_lower
            for keyword in ["email", "pattern", "valid", "match", "regex", "check"]
        ):
            relevant_imports.extend([i for i in kb.get("imports", []) if i.module == "re"])
        if "file" in intent_lower or "path" in intent_lower:
            relevant_imports.extend([i for i in kb.get("imports", []) if i.module == "pathlib"])
        if "time" in intent_lower or "date" in intent_lower:
            relevant_imports.extend([i for i in kb.get("imports", []) if i.module == "datetime"])

        # Always include typing imports
        relevant_imports.extend([i for i in kb.get("imports", []) if i.module == "typing"])

        return SemanticContext(
            available_types=relevant_types,
            available_functions=relevant_functions,
            import_patterns=relevant_imports,
            codebase_conventions=kb.get("conventions", {}),
        )


__all__ = [
    "SemanticContext",
    "SemanticContextProvider",
    "TypeInfo",
    "FunctionInfo",
    "ImportPattern",
    "RelevanceScore",
    "compute_relevance",
]
