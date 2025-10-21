"""
Resource Limits (H14)

Defines and enforces resource limits for graph execution.

This module provides:
- ResourceLimits configuration for memory, time, tokens, and concurrency
- ResourceUsage tracking throughout execution
- ResourceEnforcer for limit validation
- Integration with RunContext for usage tracking

Design Principles:
1. Explicit Limits: All resource constraints are explicitly defined
2. Tracking: Resource usage is tracked throughout execution
3. Enforcement: Limits can be checked at any point in execution
4. Extensibility: Easy to add new resource types

Resolution for Hole H14: ResourceLimits
Status: Implementation
Phase: 1 (Week 1)
Constraints from H6: Must integrate with RunContext
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class ResourceType(str, Enum):
    """Types of resources that can be limited."""

    MEMORY = "memory"  # Bytes
    TIME = "time"  # Seconds
    TOKENS = "tokens"  # LLM tokens (input + output)
    CONCURRENCY = "concurrency"  # Concurrent nodes
    LLM_CALLS = "llm_calls"  # Number of LLM API calls


class LimitStatus(str, Enum):
    """Status of resource limit check."""

    OK = "ok"  # Within limits
    WARNING = "warning"  # Approaching limits (>80%)
    EXCEEDED = "exceeded"  # Limit exceeded


@dataclass
class ResourceLimits:
    """
    Configuration for resource limits.

    Defines hard limits for various resource types. None means unlimited.

    Example:
        limits = ResourceLimits(
            max_memory_bytes=2_000_000_000,  # 2GB
            max_time_seconds=300.0,  # 5 minutes
            max_tokens=100_000,
            max_concurrent_nodes=3
        )
    """

    max_memory_bytes: int | None = None
    max_time_seconds: float | None = None
    max_tokens: int | None = None
    max_concurrent_nodes: int | None = None
    max_llm_calls: int | None = None

    # Warning thresholds (fraction of limit)
    warning_threshold: float = 0.8

    def get_limit(self, resource_type: ResourceType) -> int | float | None:
        """Get the limit for a specific resource type."""
        mapping = {
            ResourceType.MEMORY: self.max_memory_bytes,
            ResourceType.TIME: self.max_time_seconds,
            ResourceType.TOKENS: self.max_tokens,
            ResourceType.CONCURRENCY: self.max_concurrent_nodes,
            ResourceType.LLM_CALLS: self.max_llm_calls,
        }
        return mapping.get(resource_type)


@dataclass
class ResourceUsage:
    """
    Tracks actual resource usage during execution.

    Updated throughout graph execution to monitor resource consumption.
    """

    memory_bytes: int = 0
    time_seconds: float = 0.0
    tokens: int = 0
    concurrent_nodes: int = 0
    llm_calls: int = 0

    # Execution timing
    start_time: float | None = None
    end_time: float | None = None

    def start(self) -> None:
        """Mark execution start time."""
        self.start_time = time.perf_counter()

    def end(self) -> None:
        """Mark execution end time and update elapsed time."""
        if self.start_time is None:
            raise ValueError("Cannot end before starting")
        self.end_time = time.perf_counter()
        self.time_seconds = self.end_time - self.start_time

    def get_usage(self, resource_type: ResourceType) -> int | float:
        """Get current usage for a specific resource type."""
        mapping = {
            ResourceType.MEMORY: self.memory_bytes,
            ResourceType.TIME: self.time_seconds,
            ResourceType.TOKENS: self.tokens,
            ResourceType.CONCURRENCY: self.concurrent_nodes,
            ResourceType.LLM_CALLS: self.llm_calls,
        }
        return mapping[resource_type]

    def add_tokens(self, count: int) -> None:
        """Add token usage."""
        self.tokens += count

    def add_llm_call(self) -> None:
        """Increment LLM call count."""
        self.llm_calls += 1

    def set_concurrent_nodes(self, count: int) -> None:
        """Update concurrent node count."""
        self.concurrent_nodes = count

    def update_memory(self, bytes_used: int) -> None:
        """Update memory usage."""
        self.memory_bytes = bytes_used

    def update_time(self) -> None:
        """Update elapsed time from start."""
        if self.start_time is not None:
            self.time_seconds = time.perf_counter() - self.start_time


@dataclass
class LimitCheckResult:
    """Result of checking resource limits."""

    resource_type: ResourceType
    status: LimitStatus
    current: int | float
    limit: int | float | None
    percentage: float | None = None  # Percentage of limit used
    message: str = ""

    @property
    def is_ok(self) -> bool:
        """Check if resource usage is OK."""
        return self.status == LimitStatus.OK

    @property
    def is_warning(self) -> bool:
        """Check if resource usage is in warning range."""
        return self.status == LimitStatus.WARNING

    @property
    def is_exceeded(self) -> bool:
        """Check if resource limit is exceeded."""
        return self.status == LimitStatus.EXCEEDED

    def __str__(self) -> str:
        """String representation for logging."""
        if self.limit is None:
            return f"[{self.status.value.upper()}] {self.resource_type.value}: {self.current} (unlimited)"
        pct = f"{self.percentage:.1f}%" if self.percentage is not None else "N/A"
        return f"[{self.status.value.upper()}] {self.resource_type.value}: {self.current}/{self.limit} ({pct})"


class ResourceEnforcer:
    """
    Enforces resource limits during graph execution.

    Checks current usage against configured limits and returns
    status for each resource type.

    Example:
        limits = ResourceLimits(max_tokens=1000, max_time_seconds=60.0)
        usage = ResourceUsage(tokens=950, time_seconds=55.0)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)
        if result.is_warning:
            logger.warning(f"Token usage approaching limit: {result}")
    """

    def __init__(self, limits: ResourceLimits) -> None:
        """
        Initialize enforcer with resource limits.

        Args:
            limits: Resource limit configuration
        """
        self.limits = limits

    def check(self, resource_type: ResourceType, usage: ResourceUsage) -> LimitCheckResult:
        """
        Check if resource usage is within limits.

        Args:
            resource_type: Type of resource to check
            usage: Current resource usage

        Returns:
            LimitCheckResult with status and details
        """
        limit = self.limits.get_limit(resource_type)
        current = usage.get_usage(resource_type)

        # If no limit, always OK
        if limit is None:
            return LimitCheckResult(
                resource_type=resource_type,
                status=LimitStatus.OK,
                current=current,
                limit=None,
                message=f"{resource_type.value} usage: {current} (no limit)",
            )

        # Calculate percentage
        percentage = (current / limit) * 100

        # Determine status
        if current > limit:
            status = LimitStatus.EXCEEDED
            message = f"{resource_type.value} limit exceeded: {current} > {limit}"
        elif current / limit >= self.limits.warning_threshold:
            status = LimitStatus.WARNING
            message = (
                f"{resource_type.value} approaching limit: {current}/{limit} ({percentage:.1f}%)"
            )
        else:
            status = LimitStatus.OK
            message = f"{resource_type.value} usage OK: {current}/{limit} ({percentage:.1f}%)"

        return LimitCheckResult(
            resource_type=resource_type,
            status=status,
            current=current,
            limit=limit,
            percentage=percentage,
            message=message,
        )

    def check_all(self, usage: ResourceUsage) -> dict[ResourceType, LimitCheckResult]:
        """
        Check all resource types.

        Args:
            usage: Current resource usage

        Returns:
            Dict mapping resource types to check results
        """
        results = {}
        for resource_type in ResourceType:
            # Only check if limit is set
            if self.limits.get_limit(resource_type) is not None:
                results[resource_type] = self.check(resource_type, usage)
        return results

    def any_exceeded(self, usage: ResourceUsage) -> bool:
        """
        Check if any resource limit is exceeded.

        Args:
            usage: Current resource usage

        Returns:
            True if any limit is exceeded
        """
        results = self.check_all(usage)
        return any(r.is_exceeded for r in results.values())

    def any_warning(self, usage: ResourceUsage) -> bool:
        """
        Check if any resource is in warning range.

        Args:
            usage: Current resource usage

        Returns:
            True if any resource is in warning range
        """
        results = self.check_all(usage)
        return any(r.is_warning for r in results.values())

    def summary(self, usage: ResourceUsage) -> str:
        """
        Generate a summary of all resource checks.

        Args:
            usage: Current resource usage

        Returns:
            Human-readable summary
        """
        results = self.check_all(usage)
        if not results:
            return "No resource limits configured"

        lines = ["Resource usage summary:"]
        for result in results.values():
            lines.append(f"  {result}")

        if any(r.is_exceeded for r in results.values()):
            lines.append("⚠️  Some limits exceeded!")
        elif any(r.is_warning for r in results.values()):
            lines.append("⚠️  Approaching limits")
        else:
            lines.append("✓ All limits OK")

        return "\n".join(lines)


# Default limits for Modal.com environment
MODAL_DEFAULT_LIMITS = ResourceLimits(
    max_memory_bytes=2_000_000_000,  # 2GB (conservative for Modal container)
    max_time_seconds=600.0,  # 10 minutes (Modal function timeout)
    max_tokens=200_000,  # Conservative token limit
    max_concurrent_nodes=3,  # Balance between parallelism and resource usage
    max_llm_calls=20,  # Prevent runaway LLM call loops
    warning_threshold=0.8,  # Warn at 80% usage
)


# Preset configurations for different scenarios
class ResourcePresets:
    """Preset resource limit configurations."""

    @staticmethod
    def development() -> ResourceLimits:
        """Development/testing limits (permissive)."""
        return ResourceLimits(
            max_memory_bytes=1_000_000_000,  # 1GB
            max_time_seconds=120.0,  # 2 minutes
            max_tokens=50_000,
            max_concurrent_nodes=2,
            max_llm_calls=10,
        )

    @staticmethod
    def production() -> ResourceLimits:
        """Production limits (aligned with Modal defaults)."""
        return MODAL_DEFAULT_LIMITS

    @staticmethod
    def strict() -> ResourceLimits:
        """Strict limits for cost control."""
        return ResourceLimits(
            max_memory_bytes=500_000_000,  # 500MB
            max_time_seconds=60.0,  # 1 minute
            max_tokens=20_000,
            max_concurrent_nodes=1,  # Sequential execution only
            max_llm_calls=5,
            warning_threshold=0.7,  # Warn earlier
        )

    @staticmethod
    def unlimited() -> ResourceLimits:
        """No limits (use with caution!)."""
        return ResourceLimits()  # All None = unlimited
