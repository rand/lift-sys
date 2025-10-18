"""
Diagnose the IndentationError by capturing actual generated code.
"""

import asyncio

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    translator = XGrammarIRTranslator(provider)
    generator = XGrammarCodeGenerator(provider)

    prompt = "Create a function that returns a new list containing only the even numbers from the input list"
    print(f"Prompt: {prompt}")
    print()

    ir = await translator.translate(prompt, language="python")
    print(f"IR Function: {ir.signature.name}")
    print()

    result = await generator.generate(ir, temperature=0.3, max_retries=1)

    print("=" * 80)
    print("Generated code (repr):")
    print("=" * 80)
    print(repr(result.source_code))
    print()

    print("=" * 80)
    print("Generated code (actual):")
    print("=" * 80)
    print(result.source_code)
    print("=" * 80)
    print()

    # Show line-by-line with visible indentation
    print("=" * 80)
    print("Line-by-line analysis:")
    print("=" * 80)
    for i, line in enumerate(result.source_code.split("\n"), 1):
        print(f"Line {i:2d} [{len(line):3d} chars]: {repr(line)}")
    print()

    # Try to compile
    print("Compilation test:")
    try:
        compile(result.source_code, "<string>", "exec")
        print("✓ Code compiles successfully!")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        print(f"  Line {e.lineno}: {repr(e.text)}")
        print(f"  Offset: {e.offset}")


if __name__ == "__main__":
    asyncio.run(main())
