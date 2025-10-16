#!/usr/bin/env python3
"""Diagnose count_words syntax error by capturing generated code."""

import asyncio

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
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

    # Generate code
    generator = XGrammarCodeGenerator(provider=provider)

    try:
        code = await generator.generate(ir)
        print("\n✅ Code generated successfully:")
        print("=" * 70)
        for i, line in enumerate(code.source_code.split("\n"), 1):
            print(f"{i:3d} | {line}")
    except Exception as e:
        print(f"\n❌ Code generation failed: {e}")

        # Try to get the raw implementation JSON
        try:
            structure = generator._parse_structural_code(
                generator.structural_generator.generate(ir).source_code
            )
            impl_json = await generator._generate_implementation(ir, structure, 0)

            print("\n📋 Raw implementation JSON:")
            import json

            print(json.dumps(impl_json, indent=2))

            # Try to combine and show what was generated
            try:
                combined = generator._combine_structure_and_implementation(structure, impl_json)
                print("\n📝 Combined code (with syntax error):")
                print("=" * 70)
                for i, line in enumerate(combined.split("\n"), 1):
                    print(f"{i:3d} | {line}")
            except Exception as e2:
                print(f"Could not combine: {e2}")

        except Exception as e3:
            print(f"Could not get raw data: {e3}")


if __name__ == "__main__":
    asyncio.run(main())
