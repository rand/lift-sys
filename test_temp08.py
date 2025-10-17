#!/usr/bin/env python3
"""Quick test of temperature=0.8 Best-of-N on a single test case."""

import asyncio

from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    """Test a single IR generation with temperature=0.8."""

    print("="*70)
    print("Testing Best-of-N with temperature=0.8")
    print("="*70)

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    print("\n✓ Provider initialized")

    # Create Best-of-N translator with temp=0.8
    translator = BestOfNIRTranslator(
        provider=provider,
        n_candidates=3,
        temperature=0.8
    )
    print(f"✓ Best-of-N translator created (n=3, temp=0.8)")

    # Simple test prompt
    prompt = "Create a function that takes a list and a value, uses enumerate to find the value, and returns its index or -1 if not found"

    print(f"\n[Testing prompt]")
    print(f"{prompt}")
    print("-"*70)

    # Generate IR
    ir = await translator.translate(prompt)

    print("\n[Result]")
    print(f"Function: {ir.signature.name}")
    print(f"Parameters: {[(p.name, p.type_hint) for p in ir.signature.parameters]}")
    print(f"Returns: {ir.signature.returns}")
    print(f"\nEffects ({len(ir.effects)}):")
    for i, effect in enumerate(ir.effects, 1):
        print(f"  {i}. {effect.description}")

    print("\n"+ "="*70)
    print("Test complete!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
