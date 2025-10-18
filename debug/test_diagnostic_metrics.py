"""
Quick test of diagnostic metrics to verify they work before full collection.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from debug.collect_failure_samples import (
    evaluate_conjecture_quality,
    evaluate_constraint_preservation,
)
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def test_metrics():
    """Test the diagnostic metrics on a single sample."""
    print("Testing diagnostic metrics...")

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create translator and generator
    translator = XGrammarIRTranslator(provider)
    generator = XGrammarCodeGenerator(provider)

    # Test prompt
    prompt = "Create a function that counts the number of words in a string"

    # Generate IR
    print("\nGenerating IR...")
    ir = await translator.translate(prompt, language="python")
    print(f"✓ IR generated: {ir.signature.name}")
    print(f"  Constraints: {len(ir.constraints)}")

    # Evaluate conjecture quality
    print("\nEvaluating conjecture quality...")
    completeness = evaluate_conjecture_quality(ir, "count_words")
    print(f"✓ Completeness: {completeness:.1%}")

    # Generate code
    print("\nGenerating code...")
    result = await generator.generate(ir, temperature=0.5)
    print("✓ Code generated")
    print(f"  Code:\n{result.source_code}")

    # Evaluate constraint preservation
    print("\nEvaluating constraint preservation...")
    preservation = evaluate_constraint_preservation(ir, result.source_code, "count_words")
    print(f"✓ Preservation: {preservation:.1%}")

    print("\n✓ All metrics working correctly!")


if __name__ == "__main__":
    asyncio.run(test_metrics())
