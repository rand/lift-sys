#!/usr/bin/env python3
"""Debug count_words syntax error by capturing generated code before validation."""

import asyncio

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation, TypedHole
from lift_sys.ir.schema import IR_JSON_SCHEMA
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Generate IR
    prompt = "Create a function that counts the number of words in a string, where words are separated by spaces"
    ir_json = await provider.generate_structured(
        prompt=prompt,
        schema=IR_JSON_SCHEMA,
        max_tokens=3000,
        temperature=0.3,
    )
    ir = IntermediateRepresentation.from_dict(ir_json)

    print("IR Generated successfully")
    print(f"Function name: {ir.signature.name}")

    # Clear holes
    holes = ir.typed_holes()
    if holes:
        print(f"Clearing {len(holes)} holes...")
        ir.intent.holes = []
        ir.signature.holes = []
        for effect in ir.effects:
            effect.holes = []
        for assertion in ir.assertions:
            assertion.holes = []
        ir.signature.parameters = [
            p for p in ir.signature.parameters if not isinstance(p, TypedHole)
        ]

    # Generate code
    generator = XGrammarCodeGenerator(provider=provider)

    try:
        # Get structural code first
        structural_code = generator.structural_generator.generate(ir)
        structure = generator._parse_structural_code(structural_code.source_code)

        # Generate implementation
        impl_json = await generator._generate_implementation(ir, structure, 0)

        # Combine (this is where syntax error happens)
        combined_code = generator._combine_structure_and_implementation(structure, impl_json)

        print("\n📝 Generated code (before AST validation):")
        print("=" * 70)
        for i, line in enumerate(combined_code.split("\n"), 1):
            print(f"{i:3d} | {line}")

        # Try to parse
        import ast

        try:
            ast.parse(combined_code)
            print("\n✅ Code is valid!")
        except SyntaxError as e:
            print(f"\n❌ Syntax error: {e}")
            print(f"   Line {e.lineno}: {e.text}")
            print("   " + " " * (e.offset - 1) + "^")

    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
