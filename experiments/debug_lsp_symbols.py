"""Debug LSP symbol retrieval to understand what's happening."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from multilspy import LanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def debug_lsp_symbols():
    """Debug LSP symbol retrieval."""
    print("=" * 80)
    print("LSP Symbol Retrieval Debug")
    print("=" * 80)
    print()

    # Use lift-sys itself
    repo_path = Path(__file__).parent.parent
    print(f"Repository: {repo_path}")
    print(f"Repository exists: {repo_path.exists()}")
    print()

    # Find some Python files
    py_files = list(repo_path.glob("lift_sys/**/*.py"))[:5]
    print(f"Found {len(py_files)} Python files (showing first 5):")
    for f in py_files:
        print(f"  - {f.relative_to(repo_path)}")
    print()

    if not py_files:
        print("No Python files found!")
        return

    # Pick first file
    test_file = py_files[0]
    print(f"Testing with file: {test_file.relative_to(repo_path)}")
    print()

    # Create LSP server
    config = MultilspyConfig.from_dict(
        {
            "code_language": "python",
            "trace_lsp_communication": True,  # Enable tracing
        }
    )

    multilspy_logger = MultilspyLogger()
    lsp = LanguageServer.create(config, multilspy_logger, str(repo_path))

    print("Starting LSP server...")
    async with lsp.start_server():
        print("LSP server started successfully!")
        print()

        # Try to get symbols from the file
        print(f"Requesting symbols from: {test_file}")
        try:
            # Try with relative path
            relative_path = str(test_file.relative_to(repo_path))
            print(f"  Relative path: {relative_path}")

            with lsp.open_file(relative_path):
                print("  File opened successfully")
                symbols = await lsp.request_document_symbols(relative_path)
                print(f"  Symbols retrieved: {len(symbols) if symbols else 0}")

                if symbols:
                    print("\n  First 5 symbols:")
                    for i, symbol in enumerate(symbols[:5]):
                        print(f"    Symbol {i}: {type(symbol)}")
                        print(f"      {symbol}")
                        if hasattr(symbol, "kind"):
                            print(f"      Kind: {symbol.kind}, Name: {symbol.name}")
                        elif isinstance(symbol, dict):
                            print(f"      Kind: {symbol.get('kind')}, Name: {symbol.get('name')}")
                else:
                    print("  No symbols returned")

        except Exception as e:
            print(f"  Error: {e}")
            import traceback

            traceback.print_exc()

    print("\nLSP server stopped")


if __name__ == "__main__":
    asyncio.run(debug_lsp_symbols())
