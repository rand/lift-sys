"""
Robustness testing infrastructure for lift-sys.

This module provides tools for testing the robustness of LLM-based IR generation
and code generation by applying semantic-preserving transformations and measuring
sensitivity to input variations.

Inspired by TokDrift research (arXiv:2510.14972):
https://github.com/uw-swag/tokdrift

Key Components:
- ParaphraseGenerator: Generate semantic-preserving NL prompt variants
- IRVariantGenerator: Generate semantic-preserving IR variants
- EquivalenceChecker: Validate IR and code equivalence
- SensitivityAnalyzer: Measure robustness metrics

Usage:
    from lift_sys.robustness import ParaphraseGenerator, EquivalenceChecker

    # Generate paraphrases
    gen = ParaphraseGenerator(max_variants=10)
    variants = gen.generate("Create a function that sorts a list")

    # Check equivalence
    checker = EquivalenceChecker(normalize_naming=True)
    assert checker.ir_equivalent(ir1, ir2)
"""

from lift_sys.robustness.equivalence_checker import EquivalenceChecker
from lift_sys.robustness.ir_variant_generator import IRVariantGenerator
from lift_sys.robustness.paraphrase_generator import ParaphraseGenerator
from lift_sys.robustness.sensitivity_analyzer import (
    SensitivityAnalyzer,
    SensitivityResult,
    StatisticalTestResult,
)
from lift_sys.robustness.types import NamingStyle, ParaphraseStrategy

# Public API
__all__ = [
    "EquivalenceChecker",
    "IRVariantGenerator",
    "NamingStyle",
    "ParaphraseGenerator",
    "ParaphraseStrategy",
    "SensitivityAnalyzer",
    "SensitivityResult",
    "StatisticalTestResult",
]

__version__ = "0.1.0"
