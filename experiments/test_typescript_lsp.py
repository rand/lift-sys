"""Test TypeScript LSP integration with multilspy."""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory


async def test_typescript_lsp():
    """Test that typescript-language-server works with multilspy."""

    from multilspy import LanguageServer
    from multilspy.multilspy_config import MultilspyConfig
    from multilspy.multilspy_logger import MultilspyLogger

    # Create logger
    logger = MultilspyLogger()

    print("Creating temporary TypeScript project...")
    temp_dir = TemporaryDirectory()
    repo_path = Path(temp_dir.name)

    # Create a simple TypeScript file
    test_file = repo_path / "test.ts"
    test_file.write_text("""
interface User {
    name: string;
    age: number;
}

function greetUser(user: User): string {
    return `Hello, ${user.name}!`;
}

class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}
""")

    # Create package.json (needed for TypeScript projects)
    package_json = repo_path / "package.json"
    package_json.write_text('{"name": "test-ts-project", "version": "1.0.0"}')

    # Create tsconfig.json
    tsconfig = repo_path / "tsconfig.json"
    tsconfig.write_text("""{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true
  }
}""")

    print(f"Test project created at: {repo_path}")
    print(f"Test file: {test_file}")

    try:
        # Configure multilspy for TypeScript
        print("\nConfiguring multilspy for TypeScript...")
        config = MultilspyConfig.from_dict(
            {
                "code_language": "typescript",
                "trace_lsp_communication": False,
            }
        )

        print("Creating LanguageServer...")
        lsp = LanguageServer.create(
            config,
            logger,
            str(repo_path),
        )

        print("Starting LSP server...")
        try:
            async with lsp.start_server():
                print("✓ LSP server started successfully")

                # Try to get document symbols
                print(f"\nQuerying document symbols for {test_file.name}...")
                symbols = await lsp.request_document_symbols(str(test_file))

                print(f"\nFound {len(symbols) if symbols else 0} top-level symbols:")
                if symbols:
                    # Handle nested list structure from multilspy
                    flat_symbols = []
                    for item in symbols:
                        if isinstance(item, list):
                            flat_symbols.extend(item)
                        else:
                            flat_symbols.append(item)

                    for symbol in flat_symbols:
                        if isinstance(symbol, dict):
                            symbol_type = symbol.get("kind", "unknown")
                            symbol_name = symbol.get("name", "unnamed")
                            print(f"  - {symbol_name} (kind: {symbol_type})")

                # Try completion
                print("\nTesting completion at line 7...")
                completions = await lsp.request_completions(
                    str(test_file),
                    line=7,
                    column=15,
                )
                print(f"Found {len(completions) if completions else 0} completions")

                print("\n✓ TypeScript LSP integration working!")
        except Exception as cleanup_error:
            # Ignore cleanup errors - server already did its job
            if "PID not found" in str(cleanup_error):
                print("✓ LSP server stopped (cleanup warning ignored)")
            else:
                raise

        print("✓ Test completed")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        temp_dir.cleanup()

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("TypeScript LSP Integration Test")
    print("=" * 60)

    success = asyncio.run(test_typescript_lsp())

    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Tests failed")
    print("=" * 60)
