#!/usr/bin/env python3
"""Quick test of Modal IR generation."""

import asyncio

from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    """Test Modal provider with simple prompt."""
    print("Testing Modal provider...")

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    print("Provider created")

    await provider.initialize(credentials={})
    print("Provider initialized")

    # Create translator
    translator = XGrammarIRTranslator(provider)
    print("Translator created")

    # Test with simple prompt
    prompt = "Create a function called add that takes two integers a and b, and returns their sum"
    print(f"\nGenerating IR for: {prompt}")

    ir = await translator.translate(prompt)
    print("\n✅ SUCCESS! Generated IR:")
    print(f"   Function: {ir.signature.name}")
    print(f"   Parameters: {[p.name for p in ir.signature.parameters]}")
    print(f"   Returns: {ir.signature.returns}")


if __name__ == "__main__":
    asyncio.run(main())
