"""
Test script to verify constraint detection hypothesis.

Tests constraint detection on the 3 failing test cases to understand
why detection is failing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.ir.constraint_detector import ConstraintDetector
from lift_sys.providers.modal_provider import ModalProvider


async def test_constraint_detection():
    """Test constraint detection on the 3 failing tests."""

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    translator = XGrammarIRTranslator(provider)
    detector = ConstraintDetector()

    test_cases = {
        "count_words": "Create a function that counts the number of words in a string",
        "find_index": "Create a function that finds the first index of a value in a list, returning -1 if not found",
        "is_valid_email": "Create a function that validates if a string is a valid email address (must have @ and . with characters in between)",
    }

    for test_name, prompt in test_cases.items():
        print(f"\n{'=' * 80}")
        print(f"Test: {test_name}")
        print(f"{'=' * 80}")
        print(f"Prompt: {prompt}\n")

        # Generate IR
        ir = await translator.translate(prompt, language="python")

        # Show IR details
        print(f"Function: {ir.signature.name}")
        print(f"Returns: {ir.signature.returns}")
        print("\nIntent:")
        print(f"  Summary: {ir.intent.summary}")
        print(f"  Rationale: {ir.intent.rationale}")

        print("\nEffects:")
        for i, effect in enumerate(ir.effects, 1):
            print(f"  {i}. {effect.description}")

        # Check what constraint detector sees
        print("\n--- Constraint Detection Analysis ---")

        # Manually check the logic
        intent_text = f"{ir.intent.summary} {ir.intent.rationale or ''}".lower()
        effects_text = " ".join(effect.description.lower() for effect in ir.effects)
        combined_text = f"{intent_text} {effects_text}"

        print("\nCombined text (lowercased):")
        print(f"  {combined_text[:200]}...")

        # Check for return keywords
        return_keywords = [
            "return",
            "returns",
            "compute",
            "computes",
            "calculate",
            "calculates",
            "count",
            "counts",
            "sum",
            "sums",
            "result",
            "output",
        ]

        found_keywords = [kw for kw in return_keywords if kw in combined_text]
        print(f"\nFound return keywords: {found_keywords}")

        # Check for explicit "return" in effects
        has_explicit_return = "return" in effects_text
        print(f"Has explicit 'return' in effects: {has_explicit_return}")

        # Run actual detection
        constraints = detector.detect_constraints(ir)
        print(f"\n✅ Detected constraints: {len(constraints)}")
        for constraint in constraints:
            print(f"  - {constraint.type.value}: {constraint.description}")

        if not constraints:
            print("\n❌ NO CONSTRAINTS DETECTED!")
            if has_explicit_return:
                print("   Reason: 'return' found in effects, detector skipped ReturnConstraint")
                print("   This is the bug - should create constraint anyway!")


if __name__ == "__main__":
    asyncio.run(test_constraint_detection())
