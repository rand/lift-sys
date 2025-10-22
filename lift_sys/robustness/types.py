"""Shared types for robustness testing."""

from enum import Enum


class NamingStyle(str, Enum):
    """Identifier naming conventions for code transformations."""

    SNAKE_CASE = "snake_case"
    CAMEL_CASE = "camelCase"
    PASCAL_CASE = "PascalCase"
    SCREAMING_SNAKE = "SCREAMING_SNAKE_CASE"


class ParaphraseStrategy(str, Enum):
    """Paraphrase generation strategies."""

    LEXICAL = "lexical"  # Synonym replacement
    STRUCTURAL = "structural"  # Clause reordering
    STYLISTIC = "stylistic"  # Voice, mood changes
    ALL = "all"  # Combine all strategies
