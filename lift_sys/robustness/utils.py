"""Utility functions for robustness testing."""

from typing import Any


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def edit_distance(str1: str, str2: str) -> int:
    """
    Compute Levenshtein edit distance between two strings.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Minimum number of edits to transform str1 into str2
    """
    if len(str1) < len(str2):
        return edit_distance(str2, str1)

    if len(str2) == 0:
        return len(str1)

    previous_row = range(len(str2) + 1)
    for i, c1 in enumerate(str1):
        current_row = [i + 1]
        for j, c2 in enumerate(str2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def deep_equal(obj1: Any, obj2: Any, ignore_keys: set[str] | None = None) -> bool:
    """
    Deep equality check for nested structures.

    Args:
        obj1: First object
        obj2: Second object
        ignore_keys: Keys to ignore in dict comparisons

    Returns:
        True if objects are deeply equal, False otherwise
    """
    ignore_keys = ignore_keys or set()

    if not isinstance(obj1, type(obj2)):
        return False

    if isinstance(obj1, dict):
        keys1 = set(obj1.keys()) - ignore_keys
        keys2 = set(obj2.keys()) - ignore_keys
        if keys1 != keys2:
            return False
        return all(deep_equal(obj1[k], obj2[k], ignore_keys) for k in keys1)

    elif isinstance(obj1, (list, tuple)):
        if len(obj1) != len(obj2):
            return False
        return all(deep_equal(a, b, ignore_keys) for a, b in zip(obj1, obj2, strict=False))

    else:
        return obj1 == obj2
