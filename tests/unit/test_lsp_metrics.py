"""Tests for LSP metrics collection."""

from __future__ import annotations

import time

import pytest

from lift_sys.codegen.lsp_metrics import LSPMetrics, LSPMetricsCollector


class TestLSPMetrics:
    """Tests for LSPMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating metrics."""
        metrics = LSPMetrics()

        assert metrics.queries_total == 0
        assert metrics.queries_success == 0
        assert metrics.queries_error == 0
        assert metrics.queries_cached == 0
        assert metrics.latency_sum == 0.0
        assert metrics.latency_count == 0
        assert metrics.symbols_retrieved == 0
        assert metrics.files_queried == 0
        assert metrics.errors == {}

    def test_query_success_rate_zero_queries(self):
        """Test success rate with zero queries."""
        metrics = LSPMetrics()

        assert metrics.query_success_rate == 0.0

    def test_query_success_rate(self):
        """Test success rate calculation."""
        metrics = LSPMetrics(queries_total=10, queries_success=8)

        assert metrics.query_success_rate == 80.0

    def test_cache_hit_rate_zero_queries(self):
        """Test cache hit rate with zero queries."""
        metrics = LSPMetrics()

        assert metrics.cache_hit_rate == 0.0

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = LSPMetrics(queries_total=10, queries_cached=6)

        assert metrics.cache_hit_rate == 60.0

    def test_avg_latency_ms_zero_queries(self):
        """Test average latency with zero queries."""
        metrics = LSPMetrics()

        assert metrics.avg_latency_ms == 0.0

    def test_avg_latency_ms(self):
        """Test average latency calculation."""
        # 300ms total / 3 queries = 100ms average
        metrics = LSPMetrics(latency_sum=0.3, latency_count=3)

        # Use approximate comparison due to floating point precision
        assert abs(metrics.avg_latency_ms - 100.0) < 0.01

    def test_avg_symbols_per_query_zero_success(self):
        """Test average symbols with zero successful queries."""
        metrics = LSPMetrics()

        assert metrics.avg_symbols_per_query == 0.0

    def test_avg_symbols_per_query(self):
        """Test average symbols calculation."""
        metrics = LSPMetrics(symbols_retrieved=50, queries_success=10)

        assert metrics.avg_symbols_per_query == 5.0

    def test_to_dict(self):
        """Test metrics export to dictionary."""
        metrics = LSPMetrics(
            queries_total=10,
            queries_success=8,
            queries_error=2,
            queries_cached=6,
            latency_sum=1.0,
            latency_count=10,
            symbols_retrieved=40,
            files_queried=4,
        )
        metrics.errors["TimeoutError"] = 1
        metrics.errors["ConnectionError"] = 1

        result = metrics.to_dict()

        # Check structure
        assert "queries" in result
        assert "rates" in result
        assert "performance" in result
        assert "errors" in result

        # Check query counts
        assert result["queries"]["total"] == 10
        assert result["queries"]["success"] == 8
        assert result["queries"]["error"] == 2
        assert result["queries"]["cached"] == 6

        # Check rates
        assert result["rates"]["success_rate"] == "80.0%"
        assert result["rates"]["cache_hit_rate"] == "60.0%"

        # Check performance
        assert result["performance"]["avg_latency_ms"] == "100.0"
        assert result["performance"]["avg_symbols_per_query"] == "5.0"
        assert result["performance"]["total_symbols"] == 40
        assert result["performance"]["files_queried"] == 4

        # Check errors
        assert result["errors"]["TimeoutError"] == 1
        assert result["errors"]["ConnectionError"] == 1

    def test_to_dict_empty_errors(self):
        """Test to_dict with no errors."""
        metrics = LSPMetrics()

        result = metrics.to_dict()

        assert result["errors"] == {}


class TestLSPMetricsCollector:
    """Tests for LSPMetricsCollector."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = LSPMetricsCollector()

        metrics = collector.get_metrics()
        assert metrics.queries_total == 0

    def test_record_successful_query(self):
        """Test recording a successful query."""
        collector = LSPMetricsCollector()

        collector.record_query(
            success=True,
            cached=False,
            latency=0.1,
            symbols_count=5,
        )

        metrics = collector.get_metrics()
        assert metrics.queries_total == 1
        assert metrics.queries_success == 1
        assert metrics.queries_error == 0
        assert metrics.queries_cached == 0
        assert metrics.latency_sum == 0.1
        assert metrics.latency_count == 1
        assert metrics.symbols_retrieved == 5
        assert metrics.files_queried == 1

    def test_record_cached_query(self):
        """Test recording a cached query."""
        collector = LSPMetricsCollector()

        collector.record_query(
            success=True,
            cached=True,
            latency=0.001,  # Cache hits are fast
            symbols_count=5,
        )

        metrics = collector.get_metrics()
        assert metrics.queries_total == 1
        assert metrics.queries_success == 1
        assert metrics.queries_cached == 1
        assert metrics.files_queried == 0  # Cached queries don't query files

    def test_record_failed_query(self):
        """Test recording a failed query."""
        collector = LSPMetricsCollector()

        collector.record_query(
            success=False,
            cached=False,
            latency=0.5,
            symbols_count=0,
            error_type="TimeoutError",
        )

        metrics = collector.get_metrics()
        assert metrics.queries_total == 1
        assert metrics.queries_success == 0
        assert metrics.queries_error == 1
        assert metrics.errors["TimeoutError"] == 1

    def test_record_multiple_queries(self):
        """Test recording multiple queries."""
        collector = LSPMetricsCollector()

        # Record various queries
        collector.record_query(True, False, 0.1, 5)  # Success, not cached
        collector.record_query(True, True, 0.001, 5)  # Success, cached
        collector.record_query(False, False, 0.5, 0, "TimeoutError")  # Failed
        collector.record_query(True, False, 0.2, 10)  # Success, not cached

        metrics = collector.get_metrics()
        assert metrics.queries_total == 4
        assert metrics.queries_success == 3
        assert metrics.queries_error == 1
        assert metrics.queries_cached == 1
        assert metrics.files_queried == 3  # Non-cached queries (including failed one)
        assert metrics.symbols_retrieved == 20  # 5 + 5 + 0 + 10

    def test_record_context_retrieval(self):
        """Test recording context retrieval."""
        collector = LSPMetricsCollector()

        collector.record_context_retrieval(
            files_queried=3,
            types_found=10,
            functions_found=15,
            latency=0.3,
        )

        metrics = collector.get_metrics()
        # Context retrieval adds symbols but doesn't increment query count
        assert metrics.queries_total == 0
        assert metrics.symbols_retrieved == 25  # 10 + 15

    def test_reset_metrics(self):
        """Test resetting metrics."""
        collector = LSPMetricsCollector()

        # Record some queries
        collector.record_query(True, False, 0.1, 5)
        collector.record_query(True, False, 0.2, 10)

        # Get metrics before reset
        metrics_before = collector.get_metrics()
        assert metrics_before.queries_total == 2

        # Reset
        old_metrics = collector.reset()

        # Old metrics should have the data
        assert old_metrics.queries_total == 2
        assert old_metrics.symbols_retrieved == 15

        # New metrics should be empty
        metrics_after = collector.get_metrics()
        assert metrics_after.queries_total == 0
        assert metrics_after.symbols_retrieved == 0

    def test_should_log_metrics_no_queries(self):
        """Test should_log_metrics with no queries."""
        collector = LSPMetricsCollector()

        # No queries yet
        assert not collector.should_log_metrics(interval_seconds=1.0)

    def test_should_log_metrics_before_interval(self):
        """Test should_log_metrics before interval elapsed."""
        collector = LSPMetricsCollector()

        # Record a query
        collector.record_query(True, False, 0.1, 5)

        # Check immediately (interval not elapsed)
        assert not collector.should_log_metrics(interval_seconds=60.0)

    def test_should_log_metrics_after_interval(self):
        """Test should_log_metrics after interval elapsed."""
        collector = LSPMetricsCollector()

        # Record a query
        collector.record_query(True, False, 0.1, 5)

        # Simulate time passing
        collector._last_log_time = time.time() - 61.0  # 61 seconds ago

        # Should log now
        assert collector.should_log_metrics(interval_seconds=60.0)

    def test_mark_logged(self):
        """Test mark_logged resets tracking."""
        collector = LSPMetricsCollector()

        # Record queries
        collector.record_query(True, False, 0.1, 5)
        collector.record_query(True, False, 0.2, 10)

        # Mark as logged
        collector.mark_logged()

        # Queries since last log should be reset
        assert collector._queries_since_last_log == 0

    def test_error_types_tracked(self):
        """Test that different error types are tracked separately."""
        collector = LSPMetricsCollector()

        collector.record_query(False, False, 0.1, 0, "TimeoutError")
        collector.record_query(False, False, 0.2, 0, "ConnectionError")
        collector.record_query(False, False, 0.3, 0, "TimeoutError")

        metrics = collector.get_metrics()
        assert metrics.errors["TimeoutError"] == 2
        assert metrics.errors["ConnectionError"] == 1


class TestMetricsIntegration:
    """Integration tests for metrics in LSP context provider."""

    @pytest.mark.asyncio
    async def test_metrics_collected_on_query(self):
        """Test that metrics are collected during LSP queries."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider

        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create test file
        test_file = repo_path / "test.py"
        test_file.write_text("def foo(): pass")

        config = LSPConfig(
            repository_path=repo_path,
            language="python",
            cache_enabled=False,
            metrics_enabled=True,
        )
        provider = LSPSemanticContextProvider(config)

        # Directly record metrics as if a query happened
        # (We can't test the actual LSP integration without starting a server)
        if provider._metrics:
            provider._metrics.record_query(
                success=True,
                cached=False,
                latency=0.1,
                symbols_count=5,
            )

        # Check metrics were recorded
        metrics_dict = provider.get_metrics()
        assert metrics_dict["queries"]["total"] == 1
        assert metrics_dict["queries"]["success"] == 1

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_metrics_track_cache_hits(self):
        """Test that cache hits are tracked in metrics."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider

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

        # Simulate a cache hit by directly recording it
        # (We can't test the actual cache integration without starting LSP)
        if provider._metrics:
            provider._metrics.record_query(
                success=True,
                cached=True,
                latency=0.001,
                symbols_count=1,
            )

        # Check metrics
        metrics_dict = provider.get_metrics()
        assert metrics_dict["queries"]["cached"] == 1
        assert metrics_dict["rates"]["cache_hit_rate"] == "100.0%"

        temp_dir.cleanup()

    def test_get_metrics_disabled(self):
        """Test get_metrics when metrics are disabled."""
        from pathlib import Path

        from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider

        config = LSPConfig(
            repository_path=Path("/tmp"),
            language="python",
            metrics_enabled=False,
        )
        provider = LSPSemanticContextProvider(config)

        metrics = provider.get_metrics()
        assert metrics == {"enabled": False}
