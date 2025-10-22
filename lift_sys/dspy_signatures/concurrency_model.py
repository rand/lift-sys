"""
Concurrency Model (H16)

Provider-aware concurrency limits calculated from rate limits.

This module provides automatic computation of optimal concurrency values based on
LLM provider rate limits, building on H14 ResourceLimits to prevent rate limit
errors while maximizing throughput.

Design Principles:
1. Provider-Aware: Different providers have different rate limits
2. Calculated Limits: Compute max_concurrent_nodes from provider documentation
3. No Rate Limit Errors: Stay within provider bounds (AC: no 429 errors)
4. Throughput Optimization: Achieve ≥90% of theoretical maximum throughput
5. Configurable: Easy to adjust per provider and use case

Resolution for Hole H16: ConcurrencyModel
Status: Implementation
Phase: 4 (Week 4)
Dependencies: H14 (ResourceLimits) - RESOLVED
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from .resource_limits import ResourceLimits


class ProviderType(str, Enum):
    """Supported LLM providers.

    Each provider has different rate limits and concurrency constraints.
    Use the appropriate provider type to get correct concurrency calculations.
    """

    ANTHROPIC = "anthropic"  # Claude via API
    OPENAI = "openai"  # GPT via API
    MODAL_INFERENCE = "modal"  # Modal-hosted inference
    BEST_AVAILABLE = "best_available"  # Route to best (from ADR 001)


@dataclass
class ProviderRateLimits:
    """
    Rate limits for a specific LLM provider.

    Sourced from provider documentation:
    - Anthropic: https://docs.anthropic.com/claude/reference/rate-limits
    - OpenAI: https://platform.openai.com/docs/guides/rate-limits
    - Modal: Based on GPU count and queue depth

    Attributes:
        provider: Provider type
        requests_per_minute: Maximum requests per minute
        tokens_per_minute: Maximum tokens per minute
        tokens_per_day: Maximum tokens per day (None if no daily limit)
        avg_tokens_per_request: Conservative estimate of tokens per request
        avg_latency_seconds: Average request latency in seconds
        max_concurrent_requests: Provider-enforced concurrency limit (None if no limit)
    """

    provider: ProviderType

    # Rate limits
    requests_per_minute: int
    tokens_per_minute: int
    tokens_per_day: int | None = None

    # Typical request characteristics
    avg_tokens_per_request: int = 2000  # Conservative estimate (prompt + completion)
    avg_latency_seconds: float = 2.0  # Average request latency

    # Burst allowance
    max_concurrent_requests: int | None = None  # Provider-enforced concurrency limit


class ConcurrencyModel(BaseModel):
    """
    Calculates optimal concurrency limits from provider rate limits.

    Key calculations:
    1. max_parallel_llm_calls: Limited by requests/min and concurrent request cap
    2. max_parallel_nodes: Limited by expected nodes-per-graph and total parallelism budget
    3. Safety margin: Reduce by 10-20% to avoid hitting limits

    Example:
        >>> model = get_concurrency_model(ProviderType.ANTHROPIC)
        >>> limits = model.to_resource_limits()
        >>> executor = ParallelExecutor(max_concurrent=limits.max_concurrent_nodes)
    """

    provider_limits: ProviderRateLimits

    # Configuration
    expected_concurrent_graphs: int = 1  # How many graphs run in parallel
    safety_margin: float = 0.8  # Use 80% of theoretical max (safety buffer)

    @property
    def max_parallel_llm_calls(self) -> int:
        """
        Maximum parallel LLM calls without hitting rate limits.

        Calculation:
        - If provider has max_concurrent_requests: use that (with safety margin)
        - Otherwise: requests_per_minute / 60 * avg_latency_seconds

        Rationale: With latency L seconds and rate R req/min,
        max concurrent = R/60 * L (requests in flight during latency period)

        Returns:
            Maximum number of concurrent LLM calls
        """
        if self.provider_limits.max_concurrent_requests is not None:
            # Use provider-enforced limit
            return int(self.provider_limits.max_concurrent_requests * self.safety_margin)

        # Calculate from rate and latency
        rate_per_second = self.provider_limits.requests_per_minute / 60
        max_in_flight = rate_per_second * self.provider_limits.avg_latency_seconds
        return max(1, int(max_in_flight * self.safety_margin))

    @property
    def max_parallel_nodes(self) -> int:
        """
        Maximum parallel graph nodes.

        Calculation:
        - Assume each node makes 1 LLM call
        - Divide max_parallel_llm_calls by expected_concurrent_graphs
        - Apply safety margin (already applied in max_parallel_llm_calls)

        Returns:
            Maximum number of nodes to execute in parallel
        """
        # Divide available LLM call budget by expected concurrent graphs
        per_graph_budget = self.max_parallel_llm_calls / self.expected_concurrent_graphs

        # Assume each node makes 1 LLM call (conservative)
        return max(1, int(per_graph_budget))

    @property
    def max_throughput_requests_per_minute(self) -> float:
        """
        Theoretical maximum throughput.

        Calculation: min(
            requests_per_minute,
            tokens_per_minute / avg_tokens_per_request,
            max_concurrent_requests / avg_latency_seconds * 60
        )

        Returns:
            Maximum achievable requests per minute
        """
        # Limited by three factors
        request_limit = self.provider_limits.requests_per_minute
        token_limit = (
            self.provider_limits.tokens_per_minute / self.provider_limits.avg_tokens_per_request
        )

        if self.provider_limits.max_concurrent_requests:
            concurrency_limit = (
                self.provider_limits.max_concurrent_requests
                / self.provider_limits.avg_latency_seconds
                * 60
            )
        else:
            concurrency_limit = float("inf")

        return min(request_limit, token_limit, concurrency_limit) * self.safety_margin

    def to_resource_limits(self) -> ResourceLimits:
        """
        Convert to H14 ResourceLimits for integration.

        Returns:
            ResourceLimits with computed max_concurrent_nodes and max_llm_calls
        """
        return ResourceLimits(
            max_concurrent_nodes=self.max_parallel_nodes,
            max_llm_calls=self.max_parallel_llm_calls,
            max_tokens=self.provider_limits.tokens_per_minute // 4,  # Per-graph token budget
        )


# Provider-specific rate limits (from documentation)

ANTHROPIC_TIER1_LIMITS = ProviderRateLimits(
    provider=ProviderType.ANTHROPIC,
    requests_per_minute=50,
    tokens_per_minute=40_000,
    tokens_per_day=None,  # No daily limit for Tier 1
    avg_tokens_per_request=2000,
    avg_latency_seconds=2.0,
    max_concurrent_requests=5,  # Anthropic enforces this
)

OPENAI_TIER1_LIMITS = ProviderRateLimits(
    provider=ProviderType.OPENAI,
    requests_per_minute=500,
    tokens_per_minute=30_000,
    avg_tokens_per_request=2000,
    avg_latency_seconds=1.5,
    max_concurrent_requests=None,  # No hard limit, but rate-limited
)

MODAL_GPU_LIMITS = ProviderRateLimits(
    provider=ProviderType.MODAL_INFERENCE,
    requests_per_minute=600,  # Based on GPU count (assume 1 GPU)
    tokens_per_minute=100_000,  # High throughput with local inference
    avg_tokens_per_request=2000,
    avg_latency_seconds=0.5,  # Faster with local GPU
    max_concurrent_requests=4,  # Modal queue depth
)

# Registry of provider limits
PROVIDER_LIMITS_REGISTRY = {
    ProviderType.ANTHROPIC: ANTHROPIC_TIER1_LIMITS,
    ProviderType.OPENAI: OPENAI_TIER1_LIMITS,
    ProviderType.MODAL_INFERENCE: MODAL_GPU_LIMITS,
}


def get_concurrency_model(
    provider: ProviderType,
    expected_concurrent_graphs: int = 1,
    safety_margin: float = 0.8,
) -> ConcurrencyModel:
    """
    Get pre-configured concurrency model for a provider.

    Args:
        provider: LLM provider type
        expected_concurrent_graphs: How many graphs expected to run in parallel
        safety_margin: Safety buffer (0.8 = use 80% of theoretical max)

    Returns:
        ConcurrencyModel with calculated limits

    Example:
        >>> model = get_concurrency_model(ProviderType.ANTHROPIC, expected_concurrent_graphs=2)
        >>> limits = model.to_resource_limits()
        >>> executor = ParallelExecutor(max_concurrent=limits.max_concurrent_nodes)
    """
    limits = PROVIDER_LIMITS_REGISTRY[provider]
    return ConcurrencyModel(
        provider_limits=limits,
        expected_concurrent_graphs=expected_concurrent_graphs,
        safety_margin=safety_margin,
    )


__all__ = [
    "ProviderType",
    "ProviderRateLimits",
    "ConcurrencyModel",
    "ANTHROPIC_TIER1_LIMITS",
    "OPENAI_TIER1_LIMITS",
    "MODAL_GPU_LIMITS",
    "PROVIDER_LIMITS_REGISTRY",
    "get_concurrency_model",
]
