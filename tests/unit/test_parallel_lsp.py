"""Tests for parallel LSP queries."""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider


class TestParallelSymbolQueries:
    """Tests for parallel file querying."""

    @pytest.mark.asyncio
    async def test_get_symbols_from_files_parallel(self):
        """Test that multiple files are queried in parallel."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create test files
        files = {
            "file1.py": "",
            "file2.py": "",
            "file3.py": "",
        }
        for name, content in files.items():
            (repo_path / name).write_text(content)

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        # Mock LSP to track call order
        call_times = []

        async def mock_get_symbols(file_path):
            call_times.append((file_path.name, asyncio.get_event_loop().time()))
            await asyncio.sleep(0.1)  # Simulate LSP query
            return [[{"name": f"Symbol_{file_path.stem}", "kind": 5}]]

        with patch.object(provider, "_get_document_symbols", side_effect=mock_get_symbols):
            file_paths = [repo_path / name for name in files.keys()]
            results = await provider._get_symbols_from_files(file_paths)

            # Should return results for all files
            assert len(results) == 3

            # Check that queries started nearly simultaneously (parallel)
            if len(call_times) >= 2:
                time_diff = call_times[1][1] - call_times[0][1]
                # Should start within 50ms of each other (parallel)
                assert time_diff < 0.05

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_get_symbols_from_files_handles_exceptions(self):
        """Test that exceptions in one query don't fail the entire operation."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create test files
        files = ["file1.py", "file2.py", "file3.py"]
        for name in files:
            (repo_path / name).write_text("")

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        # Mock LSP to fail on second file
        async def mock_get_symbols(file_path):
            if "file2" in file_path.name:
                raise RuntimeError("Simulated LSP error")
            return [[{"name": f"Symbol_{file_path.stem}", "kind": 5}]]

        with patch.object(provider, "_get_document_symbols", side_effect=mock_get_symbols):
            file_paths = [repo_path / name for name in files]
            results = await provider._get_symbols_from_files(file_paths)

            # Should return results for file1 and file3, empty for file2
            assert len(results) == 3

            # Check that we got symbols from file1 and file3
            result_files = [fp.name for fp, _ in results]
            assert "file1.py" in result_files
            assert "file3.py" in result_files

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_get_symbols_from_files_respects_timeout(self):
        """Test that timeout is enforced for each query."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create test file
        (repo_path / "slow_file.py").write_text("")

        config = LSPConfig(repository_path=repo_path, language="python", timeout=0.1)
        provider = LSPSemanticContextProvider(config)

        # Mock LSP to be slow
        async def mock_slow_query(file_path):
            await asyncio.sleep(0.5)  # Longer than timeout
            return [[{"name": "Symbol", "kind": 5}]]

        with patch.object(provider, "_get_document_symbols", side_effect=mock_slow_query):
            file_paths = [repo_path / "slow_file.py"]
            results = await provider._get_symbols_from_files(file_paths)

            # Should return empty result due to timeout
            assert len(results) == 1
            assert results[0][1] == []  # Empty symbols

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_get_symbols_from_files_empty_list(self):
        """Test handling of empty file list."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        results = await provider._get_symbols_from_files([])

        assert results == []

        temp_dir.cleanup()


class TestSymbolExtraction:
    """Tests for symbol extraction from LSP responses."""

    def test_extract_symbols_from_response_types_and_functions(self):
        """Test extracting both types and functions."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)
        file_path = repo_path / "test.py"

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        # Mock LSP response with types and functions
        symbols = [
            [
                {"name": "MyClass", "kind": 5, "detail": "class MyClass"},
                {"name": "my_function", "kind": 12, "detail": "def my_function()"},
                {"name": "MyInterface", "kind": 11, "detail": "interface"},
                {"name": "my_method", "kind": 6, "detail": "def my_method(self)"},
            ]
        ]

        types, functions = provider._extract_symbols_from_response(symbols, file_path)

        # Should extract 2 types and 2 functions
        assert len(types) == 2
        assert len(functions) == 2

        # Check types
        type_names = [t.name for t in types]
        assert "MyClass" in type_names
        assert "MyInterface" in type_names

        # Check functions
        func_names = [f.name for f in functions]
        assert "my_function" in func_names
        assert "my_method" in func_names

        temp_dir.cleanup()

    def test_extract_symbols_from_response_nested_list(self):
        """Test handling of nested list structure from multilspy."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)
        file_path = repo_path / "test.py"

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        # multilspy returns nested lists: [[{symbol}], None]
        symbols = [
            [{"name": "MyClass", "kind": 5}],
            None,
            [{"name": "my_function", "kind": 12}],
        ]

        types, functions = provider._extract_symbols_from_response(symbols, file_path)

        # Should correctly flatten and extract
        assert len(types) == 1
        assert len(functions) == 1

        temp_dir.cleanup()

    def test_extract_symbols_from_response_empty(self):
        """Test handling of empty symbol response."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)
        file_path = repo_path / "test.py"

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        symbols = []

        types, functions = provider._extract_symbols_from_response(symbols, file_path)

        assert types == []
        assert functions == []

        temp_dir.cleanup()

    def test_extract_symbols_preserves_file_path(self):
        """Test that extracted symbols reference correct file path."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)
        file_path = repo_path / "lib" / "utils.py"
        file_path.parent.mkdir(parents=True)

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        symbols = [[{"name": "helper_func", "kind": 12}]]

        types, functions = provider._extract_symbols_from_response(symbols, file_path)

        # Should reference lib/utils.py
        assert "lib/utils.py" in functions[0].module

        temp_dir.cleanup()

    def test_extract_symbols_with_signatures(self):
        """Test extraction of function signatures from detail field."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)
        file_path = repo_path / "test.py"

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        symbols = [
            [
                {
                    "name": "add",
                    "kind": 12,
                    "detail": "def add(x: int, y: int) -> int",
                },
                {
                    "name": "process",
                    "kind": 12,
                    "detail": "",  # No detail
                },
            ]
        ]

        types, functions = provider._extract_symbols_from_response(symbols, file_path)

        # Should extract signatures
        assert functions[0].signature == "def add(x: int, y: int) -> int"
        assert functions[1].signature == "process(...)"  # Fallback

        temp_dir.cleanup()


class TestParallelIntegration:
    """Integration tests for parallel queries in full context flow."""

    @pytest.mark.asyncio
    async def test_get_lsp_context_queries_multiple_files(self):
        """Test that get_context_for_intent queries multiple relevant files."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create multiple relevant files
        (repo_path / "api").mkdir()
        (repo_path / "api" / "server.py").write_text("")
        (repo_path / "api" / "routes.py").write_text("")
        (repo_path / "models").mkdir()
        (repo_path / "models" / "user.py").write_text("")

        config = LSPConfig(repository_path=repo_path, language="python")
        provider = LSPSemanticContextProvider(config)

        # Track which files were queried
        queried_files = []

        async def mock_get_symbols(file_path):
            queried_files.append(file_path.name)
            return [[{"name": f"Symbol_{file_path.stem}", "kind": 5}]]

        await provider.start()
        try:
            with patch.object(provider, "_get_document_symbols", side_effect=mock_get_symbols):
                context = await provider.get_context_for_intent(
                    "Create API endpoint for user management"
                )

                # Should have queried multiple files (up to 3)
                assert len(queried_files) >= 1

                # Should have found some types
                assert len(context.available_types) > 0

        finally:
            await provider.stop()

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_parallel_faster_than_sequential(self):
        """Test that parallel queries are faster than sequential."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create multiple files
        for i in range(3):
            (repo_path / f"file{i}.py").write_text("")

        config = LSPConfig(repository_path=repo_path, language="python", timeout=1.0)
        provider = LSPSemanticContextProvider(config)

        # Mock LSP with 100ms delay per query
        async def mock_query_with_delay(file_path):
            await asyncio.sleep(0.1)
            return [[{"name": f"Symbol_{file_path.stem}", "kind": 5}]]

        with patch.object(provider, "_get_document_symbols", side_effect=mock_query_with_delay):
            file_paths = [repo_path / f"file{i}.py" for i in range(3)]

            # Time parallel execution
            import time

            start = time.time()
            await provider._get_symbols_from_files(file_paths)
            parallel_time = time.time() - start

            # Parallel should be ~100ms (all at once)
            # Sequential would be ~300ms (one after another)
            # Allow some overhead, but should be < 200ms
            assert parallel_time < 0.2, f"Parallel took {parallel_time}s, expected <0.2s"

        temp_dir.cleanup()
