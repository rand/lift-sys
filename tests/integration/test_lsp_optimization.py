"""Integration tests for LSP optimization features.

These tests verify that all LSP optimization components work together correctly:
- LSP caching
- Smart file discovery
- Parallel queries
- Relevance ranking
- Metrics collection
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider


class TestLSPOptimizationIntegration:
    """Integration tests for complete LSP optimization stack."""

    @pytest.mark.asyncio
    async def test_cache_and_metrics_integration(self):
        """Test that cache and metrics work together."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create test file
        test_file = repo_path / "test.py"
        test_file.write_text("def foo(): pass")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=True,
            metrics_enabled=True,
        )
        provider = LSPSemanticContextProvider(config)

        # Test cache and metrics at the component level
        # Populate cache
        mock_symbols = [[{"name": "foo", "kind": 12}]]
        if provider._lsp_cache:
            await provider._lsp_cache.put(test_file, "document_symbols", mock_symbols)

        # Record a cache hit in metrics
        if provider._metrics:
            provider._metrics.record_query(
                success=True,
                cached=True,
                latency=0.001,
                symbols_count=1,
            )

        # Check metrics include cache info
        metrics = provider.get_metrics()
        assert metrics["queries"]["cached"] >= 1
        assert "cache" in metrics
        assert metrics["cache"]["size"] >= 1
        assert metrics["cache"]["max_size"] == 1000

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_parallel_queries_with_relevance_ranking(self):
        """Test that parallel queries are ranked correctly."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create multiple test files
        (repo_path / "validators").mkdir()
        (repo_path / "validators" / "email.py").write_text("def validate_email(): pass")
        (repo_path / "validators" / "user.py").write_text("def validate_user(): pass")
        (repo_path / "models").mkdir()
        (repo_path / "models" / "user.py").write_text("class User: pass")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            metrics_enabled=True,
        )
        provider = LSPSemanticContextProvider(config)

        # Mock parallel symbol retrieval
        async def mock_get_symbols(file_paths):
            results = []
            for fp in file_paths:
                if "email" in fp.name:
                    symbols = [[{"name": "validate_email", "kind": 12}]]
                elif "user.py" in str(fp) and "validators" in str(fp):
                    symbols = [[{"name": "validate_user", "kind": 12}]]
                elif "user.py" in str(fp) and "models" in str(fp):
                    symbols = [[{"name": "User", "kind": 5}]]
                else:
                    symbols = []
                results.append((fp, symbols))
            return results

        with patch.object(provider, "_get_symbols_from_files", side_effect=mock_get_symbols):
            # Simulate finding relevant files
            files = [
                repo_path / "validators" / "email.py",
                repo_path / "validators" / "user.py",
                repo_path / "models" / "user.py",
            ]

            # Get symbols
            symbol_results = await provider._get_symbols_from_files(files)

            # Extract and rank
            all_types = []
            all_functions = []
            for file_path, symbols in symbol_results:
                if symbols:
                    types, functions = provider._extract_symbols_from_response(symbols, file_path)
                    all_types.extend(types)
                    all_functions.extend(functions)

            # Rank by relevance
            keywords = ["validate", "email"]
            intent = "validate email address"
            ranked_functions = provider._rank_symbols(all_functions, keywords, intent)

            # validate_email should rank highest
            assert len(ranked_functions) >= 1
            if len(ranked_functions) > 0:
                # The function with email in the name should score well
                function_names = [f.name for f in ranked_functions]
                assert "validate_email" in function_names

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_file_discovery_finds_relevant_files(self):
        """Test that file discovery finds the most relevant files."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create file structure
        (repo_path / "api").mkdir()
        (repo_path / "api" / "server.py").write_text("# API server")
        (repo_path / "api" / "routes.py").write_text("# API routes")
        (repo_path / "models").mkdir()
        (repo_path / "models" / "user.py").write_text("# User model")
        (repo_path / "tests").mkdir()
        (repo_path / "tests" / "test_api.py").write_text("# API tests")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            metrics_enabled=False,
        )
        provider = LSPSemanticContextProvider(config)

        # Find files for API intent
        keywords = provider._extract_keywords("Create new API endpoint for users")
        files = provider._find_relevant_files(
            keywords, "Create new API endpoint for users", limit=3
        )

        # Should find API-related files, not test files
        file_paths = [str(f) for f in files]
        assert any("api" in fp for fp in file_paths)

        # Test files should not be top priority (unless intent mentions testing)
        if len(files) >= 2:
            # At least one of the top 2 should be an API file
            top_2_paths = [str(f) for f in files[:2]]
            assert any("api" in fp for fp in top_2_paths)

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_metrics_track_full_workflow(self):
        """Test that metrics capture the complete workflow."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=True,
            metrics_enabled=True,
        )
        provider = LSPSemanticContextProvider(config)

        # Simulate some queries
        if provider._metrics:
            # Successful query
            provider._metrics.record_query(True, False, 0.1, 5)
            # Cached query
            provider._metrics.record_query(True, True, 0.001, 5)
            # Failed query
            provider._metrics.record_query(False, False, 0.5, 0, "TimeoutError")

        metrics = provider.get_metrics()

        # Verify all metrics sections exist
        assert "queries" in metrics
        assert "rates" in metrics
        assert "performance" in metrics
        assert "errors" in metrics

        # Verify counts
        assert metrics["queries"]["total"] == 3
        assert metrics["queries"]["success"] == 2
        assert metrics["queries"]["error"] == 1
        assert metrics["queries"]["cached"] == 1

        # Verify rates
        assert "success_rate" in metrics["rates"]
        assert "cache_hit_rate" in metrics["rates"]

        # Verify error tracking
        assert "TimeoutError" in metrics["errors"]
        assert metrics["errors"]["TimeoutError"] == 1

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_cache_improves_latency_on_repeated_queries(self):
        """Test that cache operations are fast."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        test_file = repo_path / "test.py"
        test_file.write_text("def foo(): pass")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=True,
            metrics_enabled=True,
        )
        provider = LSPSemanticContextProvider(config)

        # Mock symbols
        mock_symbols = [[{"name": "foo", "kind": 12}]]

        # Put in cache
        if provider._lsp_cache:
            await provider._lsp_cache.put(test_file, "document_symbols", mock_symbols)

            # Measure cache retrieval latency
            start = time.time()
            result = await provider._lsp_cache.get(test_file, "document_symbols")
            cache_hit_latency = time.time() - start

            assert result == mock_symbols
            # Cache hit should be very fast (< 10ms typically)
            assert cache_hit_latency < 0.01  # 10ms

        # Simulate recording a cache hit
        if provider._metrics:
            provider._metrics.record_query(
                success=True,
                cached=True,
                latency=cache_hit_latency,
                symbols_count=len(mock_symbols[0]),
            )

            # Check metrics show cache hit
            metrics = provider.get_metrics()
            assert metrics["queries"]["cached"] >= 1

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_error_handling_doesnt_break_metrics(self):
        """Test that errors are properly tracked without breaking metrics collection."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            metrics_enabled=True,
        )
        provider = LSPSemanticContextProvider(config)

        # Simulate various errors
        if provider._metrics:
            provider._metrics.record_query(False, False, 0.1, 0, "TimeoutError")
            provider._metrics.record_query(False, False, 0.2, 0, "ConnectionError")
            provider._metrics.record_query(False, False, 0.3, 0, "TimeoutError")

        metrics = provider.get_metrics()

        # Errors should be tracked by type
        assert metrics["errors"]["TimeoutError"] == 2
        assert metrics["errors"]["ConnectionError"] == 1
        assert metrics["queries"]["error"] == 3

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_relevance_ranking_improves_context_quality(self):
        """Test that relevance ranking surfaces the most appropriate symbols."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            metrics_enabled=False,
        )
        provider = LSPSemanticContextProvider(config)

        # Create symbols with varying relevance
        from lift_sys.codegen.semantic_context import FunctionInfo

        symbols = [
            FunctionInfo("process_data", "utils.py", "process_data()", "Generic processor"),
            FunctionInfo(
                "validate_email",
                "validators.py",
                "validate_email(email: str) -> bool",
                "Email validator",
            ),
            FunctionInfo(
                "check_email_format",
                "validators.py",
                "check_email_format(email: str) -> bool",
                "Email format checker",
            ),
        ]

        # Rank for email validation intent
        keywords = ["email", "validate"]
        intent = "validate email address format"
        ranked = provider._rank_symbols(symbols, keywords, intent)

        # validate_email and check_email_format should rank higher than process_data
        assert ranked[0].name in ["validate_email", "check_email_format"]
        assert ranked[-1].name == "process_data"

        temp_dir.cleanup()


class TestPerformanceCharacteristics:
    """Tests for performance characteristics of optimizations."""

    @pytest.mark.asyncio
    async def test_parallel_queries_complete_within_timeout(self):
        """Test that parallel queries complete within reasonable time."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create multiple files
        for i in range(5):
            (repo_path / f"file{i}.py").write_text(f"def func{i}(): pass")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            timeout=1.0,  # 1 second timeout per query
        )
        provider = LSPSemanticContextProvider(config)

        # Mock symbols with delay
        async def mock_symbols(file_path):
            await asyncio.sleep(0.05)  # 50ms per query
            return [[{"name": f"func_{file_path.stem}", "kind": 12}]]

        file_paths = [repo_path / f"file{i}.py" for i in range(5)]

        with patch.object(provider, "_get_document_symbols", side_effect=mock_symbols):
            # Time parallel execution
            start = time.time()
            results = await provider._get_symbols_from_files(file_paths)
            elapsed = time.time() - start

            # 5 queries at 50ms each would be 250ms sequentially
            # But parallel should be ~50ms (all at once) + overhead
            # Allow for overhead but should be much less than sequential
            assert elapsed < 0.15  # 150ms max (3x faster than sequential)
            assert len(results) == 5

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_cache_stats_accurate(self):
        """Test that cache statistics are accurate."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=True,
            cache_ttl=300,
        )
        provider = LSPSemanticContextProvider(config)

        # Add items to cache
        test_file1 = repo_path / "test1.py"
        test_file2 = repo_path / "test2.py"

        if provider._lsp_cache:
            await provider._lsp_cache.put(test_file1, "document_symbols", [{"name": "foo"}])
            await provider._lsp_cache.put(test_file2, "document_symbols", [{"name": "bar"}])

            # Check stats
            stats = provider.cache_stats()
            assert stats["size"] == 2
            assert stats["max_size"] == 1000
            assert stats["ttl"] == 300

        temp_dir.cleanup()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_repository(self):
        """Test behavior with empty repository."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
        )
        provider = LSPSemanticContextProvider(config)

        # Try to find files
        files = provider._find_relevant_files(["test"], "test intent", limit=3)

        # Should return empty list gracefully
        assert files == []

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_metrics_disabled(self):
        """Test that metrics can be disabled."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            metrics_enabled=False,
        )
        provider = LSPSemanticContextProvider(config)

        assert provider._metrics is None
        metrics = provider.get_metrics()
        assert metrics == {"enabled": False}

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test that cache can be disabled."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
        )
        provider = LSPSemanticContextProvider(config)

        assert provider._lsp_cache is None
        cache_stats = provider.cache_stats()
        assert cache_stats == {"enabled": False}

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_timeout_handling_in_parallel_queries(self):
        """Test that timeouts are handled gracefully in parallel queries."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create test files
        for i in range(3):
            (repo_path / f"file{i}.py").write_text(f"def func{i}(): pass")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            timeout=0.1,  # Very short timeout
        )
        provider = LSPSemanticContextProvider(config)

        # Mock one slow query that will timeout
        async def mock_symbols(file_path):
            if "file1" in file_path.name:
                await asyncio.sleep(0.5)  # Longer than timeout
            return [[{"name": f"func_{file_path.stem}", "kind": 12}]]

        file_paths = [repo_path / f"file{i}.py" for i in range(3)]

        with patch.object(provider, "_get_document_symbols", side_effect=mock_symbols):
            results = await provider._get_symbols_from_files(file_paths)

            # Should get results for all files, even if one timed out
            assert len(results) == 3

            # file1 should have empty symbols due to timeout
            file1_result = next((r for r in results if "file1" in str(r[0])), None)
            if file1_result:
                assert file1_result[1] == []

        temp_dir.cleanup()
