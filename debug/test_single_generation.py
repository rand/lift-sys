"""
Minimal reproduction to see actual generated code with constraint detection fixes.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    # Initialize
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    translator = XGrammarIRTranslator(provider)
    generator = XGrammarCodeGenerator(provider)

    # Simple test case
    prompt = "Create a function that counts the number of words in a string"

    print("=" * 80)
    print("Generating IR...")
    ir = await translator.translate(prompt, language="python")
    print(f"Function: {ir.signature.name}")
    print(f"Return type: {ir.signature.returns}")
    print(f"Constraints detected: {len(ir.constraints)}")
    for c in ir.constraints:
        print(f"  - {c.type.value}: {c.description}")

    print("\n" + "=" * 80)
    print("Generating code...")
    result = await generator.generate(ir, temperature=0.3, max_retries=1)

    print("\n" + "=" * 80)
    print("Generated code:")
    print("=" * 80)
    print(result.source_code)
    print("=" * 80)

    # Try to execute it
    print("\nTrying to compile...")
    try:
        compile(result.source_code, "<string>", "exec")
        print("✓ Code compiles successfully!")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        print(f"  Line {e.lineno}: {e.text}")


if __name__ == "__main__":
    asyncio.run(main())
