"""LSP performance and health metrics.

This module provides comprehensive metrics collection for LSP operations,
including query counts, latency tracking, cache hit rates, and error tracking.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LSPMetrics:
    """Aggregate LSP performance metrics.

    Attributes:
        queries_total: Total number of LSP queries attempted
        queries_success: Number of successful queries
        queries_error: Number of failed queries
        queries_cached: Number of queries served from cache
        latency_sum: Sum of all query latencies (seconds)
        latency_count: Number of latency measurements
        symbols_retrieved: Total number of symbols retrieved
        files_queried: Number of unique files queried
        errors: Error type counts
    """

    queries_total: int = 0
    queries_success: int = 0
    queries_error: int = 0
    queries_cached: int = 0

    latency_sum: float = 0.0
    latency_count: int = 0

    symbols_retrieved: int = 0
    files_queried: int = 0

    errors: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def query_success_rate(self) -> float:
        """Success rate as percentage (0-100)."""
        if self.queries_total == 0:
            return 0.0
        return (self.queries_success / self.queries_total) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage (0-100)."""
        if self.queries_total == 0:
            return 0.0
        return (self.queries_cached / self.queries_total) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Average query latency in milliseconds."""
        if self.latency_count == 0:
            return 0.0
        return (self.latency_sum / self.latency_count) * 1000

    @property
    def avg_symbols_per_query(self) -> float:
        """Average number of symbols retrieved per successful query."""
        if self.queries_success == 0:
            return 0.0
        return self.symbols_retrieved / self.queries_success

    def to_dict(self) -> dict[str, Any]:
        """Export metrics as dictionary.

        Returns:
            Dictionary with organized metrics sections
        """
        return {
            "queries": {
                "total": self.queries_total,
                "success": self.queries_success,
                "error": self.queries_error,
                "cached": self.queries_cached,
            },
            "rates": {
                "success_rate": f"{self.query_success_rate:.1f}%",
                "cache_hit_rate": f"{self.cache_hit_rate:.1f}%",
            },
            "performance": {
                "avg_latency_ms": f"{self.avg_latency_ms:.1f}",
                "avg_symbols_per_query": f"{self.avg_symbols_per_query:.1f}",
                "total_symbols": self.symbols_retrieved,
                "files_queried": self.files_queried,
            },
            "errors": dict(self.errors) if self.errors else {},
        }


class LSPMetricsCollector:
    """Collect and aggregate LSP metrics.

    This collector tracks all LSP operations and provides aggregated metrics
    for monitoring and debugging purposes.

    Example:
        >>> collector = LSPMetricsCollector()
        >>> # Record a query
        >>> collector.record_query(
        ...     success=True,
        ...     cached=False,
        ...     latency=0.123,
        ...     symbols_count=5
        ... )
        >>> # Get metrics
        >>> metrics = collector.get_metrics()
        >>> print(f"Success rate: {metrics.query_success_rate:.1f}%")
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = LSPMetrics()
        self._last_log_time = time.time()
        self._queries_since_last_log = 0

    def record_query(
        self,
        success: bool,
        cached: bool,
        latency: float,
        symbols_count: int = 0,
        error_type: str | None = None,
    ) -> None:
        """Record a single LSP query.

        Args:
            success: Whether the query succeeded
            cached: Whether the query was served from cache
            latency: Query latency in seconds
            symbols_count: Number of symbols retrieved
            error_type: Type of error if query failed
        """
        self.metrics.queries_total += 1
        self._queries_since_last_log += 1

        if success:
            self.metrics.queries_success += 1
        else:
            self.metrics.queries_error += 1
            if error_type:
                self.metrics.errors[error_type] += 1

        if cached:
            self.metrics.queries_cached += 1

        self.metrics.latency_sum += latency
        self.metrics.latency_count += 1
        self.metrics.symbols_retrieved += symbols_count

        if not cached:
            self.metrics.files_queried += 1

    def record_context_retrieval(
        self,
        files_queried: int,
        types_found: int,
        functions_found: int,
        latency: float,
    ) -> None:
        """Record a context retrieval operation.

        This tracks high-level context gathering that may involve
        multiple underlying LSP queries.

        Args:
            files_queried: Number of files queried
            types_found: Number of types discovered
            functions_found: Number of functions discovered
            latency: Total latency for context retrieval
        """
        # This is tracked at a higher level than individual queries
        # We don't increment queries_total here since that's for LSP calls
        self.metrics.symbols_retrieved += types_found + functions_found

    def get_metrics(self) -> LSPMetrics:
        """Get current metrics snapshot.

        Returns:
            Current metrics
        """
        return self.metrics

    def reset(self) -> LSPMetrics:
        """Reset metrics and return the old values.

        Returns:
            Metrics before reset
        """
        old_metrics = self.metrics
        self.metrics = LSPMetrics()
        self._last_log_time = time.time()
        self._queries_since_last_log = 0
        return old_metrics

    def should_log_metrics(self, interval_seconds: float = 60.0) -> bool:
        """Check if metrics should be logged based on time interval.

        Args:
            interval_seconds: Time interval for logging (default 60s)

        Returns:
            True if metrics should be logged
        """
        elapsed = time.time() - self._last_log_time
        return elapsed >= interval_seconds and self._queries_since_last_log > 0

    def mark_logged(self) -> None:
        """Mark that metrics have been logged."""
        self._last_log_time = time.time()
        self._queries_since_last_log = 0


__all__ = ["LSPMetrics", "LSPMetricsCollector"]
