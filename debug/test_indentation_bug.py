#!/usr/bin/env python3
"""
Investigate indentation bug with max_of_two function.

This test generates the max_of_two function and examines:
1. The IR structure
2. The generated code
3. Where indentation fails
"""

import asyncio
import json
from pathlib import Path

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.providers.modal_provider import ModalProvider


async def main():
    """Investigate max_of_two indentation bug."""

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    prompt = "Create a function that returns the maximum of two numbers"

    print("\n" + "=" * 60)
    print("INDENTATION BUG INVESTIGATION")
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print("=" * 60)

    # Step 1: Generate IR
    print("\n[Step 1/2] Generating IR from natural language...")

    from lift_sys.ir.schema import IR_JSON_SCHEMA

    try:
        ir_data = await provider.generate_structured(
            prompt=f"Convert this natural language description to an intermediate representation: {prompt}",
            schema=IR_JSON_SCHEMA,
            temperature=0.7,
        )
    except Exception as e:
        print(f"❌ IR generation failed: {e}")
        return
    print("✅ IR generated successfully")

    # Save IR for inspection
    ir_file = Path("debug_max_of_two_ir.json")
    with open(ir_file, "w") as f:
        json.dump(ir_data, f, indent=2)
    print(f"   Saved IR to: {ir_file}")

    # Parse IR
    try:
        ir = IntermediateRepresentation.from_dict(ir_data)
        print("   IR parsed successfully")
        print(f"   Function name: {ir.signature.name if hasattr(ir, 'signature') else 'N/A'}")
    except Exception as e:
        print(f"❌ IR parsing failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Step 2: Generate Code
    print("\n[Step 2/2] Generating code from IR...")

    generator = XGrammarCodeGenerator(provider=provider)

    try:
        gen_result = await generator.generate(ir)

        # GeneratedCode object is returned directly, no success attribute
        code = gen_result.source_code
        print("✅ Code generated")

        # Save code for inspection
        code_file = Path("debug_max_of_two_code.py")
        with open(code_file, "w") as f:
            f.write(code)
        print(f"   Saved code to: {code_file}")

        # Display code with line numbers
        print("\n" + "=" * 60)
        print("GENERATED CODE (with line numbers)")
        print("=" * 60)
        for i, line in enumerate(code.split("\n"), 1):
            print(f"{i:3d} | {line}")
        print("=" * 60)

        # Try to compile
        print("\n[Validation] Attempting to compile...")
        try:
            compile(code, "<generated>", "exec")
            print("✅ Code compiled successfully!")
        except SyntaxError as e:
            print(f"❌ Compilation failed: {e}")
            print(f"   Line {e.lineno}: {e.text}")
            print(f"   {' ' * (e.offset or 0)}^")
            print(f"\n   Error: {e.msg}")

            # Show context around error
            if e.lineno:
                lines = code.split("\n")
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                print(f"\n   Context (lines {start + 1}-{end}):")
                for i in range(start, end):
                    marker = ">>>" if i == e.lineno - 1 else "   "
                    print(f"   {marker} {i + 1:3d} | {lines[i]}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
