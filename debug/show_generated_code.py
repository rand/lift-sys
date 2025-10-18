"""Quick diagnostic to see actual generated code."""

import asyncio

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    # Setup
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    translator = XGrammarIRTranslator(provider)
    generator = XGrammarCodeGenerator(provider)

    # Simple test case
    prompt = "Create a function that returns a new list containing only the even numbers from the input list"

    # Generate
    ir = await translator.translate(prompt, language="python")
    result = await generator.generate(ir, temperature=0.3, max_retries=1)

    # Show the code with visible whitespace
    print("=" * 80)
    print("GENERATED CODE (with repr to show whitespace):")
    print("=" * 80)
    lines = result.source_code.split("\n")
    for i, line in enumerate(lines[:10], 1):  # First 10 lines
        print(f"Line {i}: {repr(line)}")

    print()
    print("=" * 80)
    print("ACTUAL CODE:")
    print("=" * 80)
    print(result.source_code[:500])  # First 500 chars


if __name__ == "__main__":
    asyncio.run(main())
