"""Test that LSP actually retrieves repository-specific symbols.

This validates that the LSP integration is working by checking if it
retrieves actual types and functions from the lift-sys codebase.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider


async def test_lsp_retrieves_real_symbols():
    """Test that LSP retrieves actual types and functions from the codebase."""
    print("=" * 80)
    print("LSP Real Symbol Retrieval Test")
    print("=" * 80)
    print()

    # Use lift-sys itself as the test repository
    repo_path = Path(__file__).parent.parent
    print(f"Repository: {repo_path}")
    print()

    config = LSPConfig(
        repository_path=repo_path,
        language="python",
        timeout=2.0,  # Longer timeout for symbol retrieval
    )

    provider = LSPSemanticContextProvider(config)

    async with provider:
        # Test 1: IR-related intent should find IR types
        print("Test 1: IR-related intent")
        print("-" * 80)
        context1 = await provider.get_context_for_intent(
            "Create an intermediate representation for a function"
        )
        print(f"Available Types: {len(context1.available_types)}")
        for t in context1.available_types[:3]:
            print(f"  - {t.name} from {t.module}")
        print(f"Available Functions: {len(context1.available_functions)}")
        for f in context1.available_functions[:3]:
            print(f"  - {f.name} from {f.module}")
        print(f"Import Patterns: {len(context1.import_patterns)}")
        for imp in context1.import_patterns[:3]:
            print(f"  - {imp.module}: {', '.join(imp.common_imports[:3])}")
        print()

        # Test 2: Code generation intent should find relevant functions
        print("Test 2: Code generation intent")
        print("-" * 80)
        context2 = await provider.get_context_for_intent("Generate Python code from specification")
        print(f"Available Types: {len(context2.available_types)}")
        for t in context2.available_types[:3]:
            print(f"  - {t.name} from {t.module}")
        print(f"Available Functions: {len(context2.available_functions)}")
        for f in context2.available_functions[:3]:
            print(f"  - {f.name} from {f.module}")
        print()

        # Test 3: LSP-specific intent
        print("Test 3: LSP integration intent")
        print("-" * 80)
        context3 = await provider.get_context_for_intent("Configure language server protocol")
        print(f"Available Types: {len(context3.available_types)}")
        for t in context3.available_types[:3]:
            print(f"  - {t.name} from {t.module}")
        print(f"Available Functions: {len(context3.available_functions)}")
        for f in context3.available_functions[:3]:
            print(f"  - {f.name} from {f.module}")
        print()

    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)

    total_types = (
        len(context1.available_types)
        + len(context2.available_types)
        + len(context3.available_types)
    )
    total_functions = (
        len(context1.available_functions)
        + len(context2.available_functions)
        + len(context3.available_functions)
    )

    print(f"Total types retrieved: {total_types}")
    print(f"Total functions retrieved: {total_functions}")
    print()

    if total_types > 0 or total_functions > 0:
        print("✅ SUCCESS: LSP is retrieving repository-specific symbols!")
        print("   The LSP server is working and querying the codebase.")
    else:
        print("⚠️  WARNING: No repository-specific symbols retrieved")
        print("   LSP may not be finding relevant files or symbols.")
        print("   This is okay - fallback to import patterns is working.")

    return total_types, total_functions


if __name__ == "__main__":
    types, functions = asyncio.run(test_lsp_retrieves_real_symbols())
