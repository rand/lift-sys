# H16: ConcurrencyModel - Preparation Document

**Date**: 2025-10-21
**Status**: Planning
**Phase**: 4 (Week 4)

---

## Overview

H16 (ConcurrencyModel) defines maximum concurrent operations based on provider rate limits, building on H14 (ResourceLimits) to calculate optimal concurrency values for different LLM providers.

## Goals

1. **Provider-Aware**: Different providers have different rate limits (requests/min, tokens/min)
2. **Calculated Limits**: Automatically compute max_concurrent_nodes from provider limits
3. **No Rate Limit Errors**: Stay within provider bounds (AC: no rate limit errors)
4. **Throughput Optimization**: Achieve ≥90% of theoretical maximum throughput
5. **Configurable**: Easy to adjust per provider and use case

## Context

### Dependencies

**Blocked By**:
- ✅ H14 (ResourceLimits) - **RESOLVED**: Provides ResourceLimits dataclass with max_concurrent_nodes, max_llm_calls

**Blocks**:
- H4 (ParallelizationImpl) - Already resolved, but H16 provides limits for ParallelExecutor

**Related**:
- H4 ParallelExecutor uses `max_concurrent` parameter (semaphore limiting)
- H14 ResourceLimits has fields but no provider-specific calculation

### Existing Components

From H14 (ResourceLimits):
```python
@dataclass
class ResourceLimits:
    max_memory_bytes: int | None = None
    max_time_seconds: float | None = None
    max_tokens: int | None = None
    max_concurrent_nodes: int | None = None  # What H16 calculates
    max_llm_calls: int | None = None          # What H16 calculates
    warning_threshold: float = 0.8

# Current Modal defaults (hardcoded, not calculated)
MODAL_DEFAULT_LIMITS = ResourceLimits(
    max_concurrent_nodes=3,  # Hardcoded
    max_llm_calls=20,        # Hardcoded
)
```

From H4 (ParallelExecutor):
```python
class ParallelExecutor(Generic[StateT]):
    def __init__(self, max_concurrent: int = 4):
        # Uses semaphore to limit concurrency
        self._semaphore = asyncio.Semaphore(max_concurrent)
```

## Design

### Core Abstraction: ConcurrencyModel

```python
from pydantic import BaseModel
from enum import Enum

class ProviderType(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"       # Claude via API
    OPENAI = "openai"             # GPT via API
    MODAL_INFERENCE = "modal"     # Modal-hosted inference
    BEST_AVAILABLE = "best_available"  # Route to best (from ADR 001)

@dataclass
class ProviderRateLimits:
    """
    Rate limits for a specific LLM provider.

    Sourced from provider documentation:
    - Anthropic: https://docs.anthropic.com/claude/reference/rate-limits
    - OpenAI: https://platform.openai.com/docs/guides/rate-limits
    - Modal: Based on GPU count and queue depth
    """
    provider: ProviderType

    # Rate limits
    requests_per_minute: int
    tokens_per_minute: int
    tokens_per_day: int | None = None

    # Typical request characteristics
    avg_tokens_per_request: int = 2000  # Conservative estimate (prompt + completion)
    avg_latency_seconds: float = 2.0   # Average request latency

    # Burst allowance
    max_concurrent_requests: int | None = None  # Provider-enforced concurrency limit

class ConcurrencyModel(BaseModel):
    """
    Calculates optimal concurrency limits from provider rate limits.

    Key calculations:
    1. max_parallel_llm_calls: Limited by requests/min and concurrent request cap
    2. max_parallel_nodes: Limited by expected nodes-per-graph and total parallelism budget
    3. Safety margin: Reduce by 10-20% to avoid hitting limits
    """

    provider_limits: ProviderRateLimits

    # Configuration
    expected_concurrent_graphs: int = 1  # How many graphs run in parallel
    safety_margin: float = 0.8           # Use 80% of theoretical max (safety buffer)

    # Computed limits (cached properties)
    @property
    def max_parallel_llm_calls(self) -> int:
        """
        Maximum parallel LLM calls without hitting rate limits.

        Calculation:
        - If provider has max_concurrent_requests: use that (with safety margin)
        - Otherwise: requests_per_minute / 60 * avg_latency_seconds

        Rationale: With latency L seconds and rate R req/min,
        max concurrent = R/60 * L (requests in flight during latency period)
        """
        ...

    @property
    def max_parallel_nodes(self) -> int:
        """
        Maximum parallel graph nodes.

        Calculation:
        - Assume each node makes 1 LLM call
        - Divide max_parallel_llm_calls by expected_concurrent_graphs
        - Apply safety margin
        """
        ...

    @property
    def max_throughput_requests_per_minute(self) -> float:
        """
        Theoretical maximum throughput.

        Calculation: min(
            requests_per_minute,
            tokens_per_minute / avg_tokens_per_request,
            max_concurrent_requests / avg_latency_seconds * 60
        )
        """
        ...

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
        model = get_concurrency_model(ProviderType.ANTHROPIC, expected_concurrent_graphs=2)
        limits = model.to_resource_limits()
        executor = ParallelExecutor(max_concurrent=limits.max_concurrent_nodes)
    """
    limits = PROVIDER_LIMITS_REGISTRY[provider]
    return ConcurrencyModel(
        provider_limits=limits,
        expected_concurrent_graphs=expected_concurrent_graphs,
        safety_margin=safety_margin,
    )
```

### Calculation Details

#### max_parallel_llm_calls

**Strategy 1: Concurrent Request Cap (if provider enforces)**
```python
if self.provider_limits.max_concurrent_requests is not None:
    return int(self.provider_limits.max_concurrent_requests * self.safety_margin)
```

**Strategy 2: Latency-Based Calculation**
```python
# Requests that can be in flight during avg latency period
# Rate: R req/min, Latency: L sec
# Max concurrent = R/60 * L (requests started but not finished)
rate_per_second = self.provider_limits.requests_per_minute / 60
max_in_flight = rate_per_second * self.provider_limits.avg_latency_seconds
return int(max_in_flight * self.safety_margin)
```

**Example (Anthropic Tier 1)**:
- requests_per_minute = 50
- avg_latency_seconds = 2.0
- max_concurrent_requests = 5 (enforced)
- Result: min(5, 50/60 * 2) * 0.8 = min(5, 1.67) * 0.8 = 1.33 * 0.8 = **1** concurrent LLM call

#### max_parallel_nodes

```python
# Divide available LLM call budget by expected concurrent graphs
per_graph_budget = self.max_parallel_llm_calls / self.expected_concurrent_graphs

# Assume each node makes 1 LLM call (conservative)
return max(1, int(per_graph_budget))
```

**Example (Anthropic, 1 concurrent graph)**:
- max_parallel_llm_calls = 1
- expected_concurrent_graphs = 1
- Result: 1 / 1 = **1** parallel node (sequential execution)

**Example (Modal, 1 concurrent graph)**:
- max_parallel_llm_calls = 4 * 0.8 = 3
- expected_concurrent_graphs = 1
- Result: 3 / 1 = **3** parallel nodes

#### max_throughput_requests_per_minute

```python
# Limited by three factors
request_limit = self.provider_limits.requests_per_minute
token_limit = self.provider_limits.tokens_per_minute / self.provider_limits.avg_tokens_per_request

if self.provider_limits.max_concurrent_requests:
    concurrency_limit = self.provider_limits.max_concurrent_requests / self.provider_limits.avg_latency_seconds * 60
else:
    concurrency_limit = float('inf')

return min(request_limit, token_limit, concurrency_limit) * self.safety_margin
```

## Acceptance Criteria

### AC1: Calculated from provider limits ✓
**Test**: Verify max_parallel_nodes computed from provider rate limits, not hardcoded
```python
def test_calculated_from_provider_limits():
    model = get_concurrency_model(ProviderType.ANTHROPIC)

    # Should be calculated, not hardcoded
    assert model.max_parallel_llm_calls > 0
    assert model.max_parallel_nodes > 0

    # Change provider limits, recalculate
    custom_limits = ProviderRateLimits(
        provider=ProviderType.ANTHROPIC,
        requests_per_minute=100,  # Double the rate
        tokens_per_minute=80_000,
        avg_tokens_per_request=2000,
        avg_latency_seconds=2.0,
        max_concurrent_requests=10,
    )
    custom_model = ConcurrencyModel(provider_limits=custom_limits)

    # Higher limits → higher concurrency
    assert custom_model.max_parallel_llm_calls > model.max_parallel_llm_calls
```

### AC2: No rate limit errors in testing ✓
**Test**: Simulate load, verify no rate limit errors
```python
async def test_no_rate_limit_errors():
    """Simulate realistic load and verify no 429 errors."""
    model = get_concurrency_model(ProviderType.ANTHROPIC)
    limits = model.to_resource_limits()

    # Simulate parallel execution within limits
    executor = ParallelExecutor(max_concurrent=limits.max_concurrent_nodes)

    # Create mock nodes that track request timing
    nodes = [MockLLMNode() for _ in range(limits.max_llm_calls)]
    ctx = RunContext(state=TestState(), execution_id="test")

    # Execute with timing
    results = await executor.execute_parallel(nodes, ctx)

    # Verify no rate limit errors (would be in result.error)
    rate_limit_errors = [r for r in results if isinstance(r.error, RateLimitError)]
    assert len(rate_limit_errors) == 0, f"Got {len(rate_limit_errors)} rate limit errors"
```

### AC3: Throughput within 90% of theoretical max ✓
**Test**: Measure actual throughput vs theoretical
```python
async def test_throughput_optimization():
    """Verify actual throughput ≥90% of theoretical max."""
    model = get_concurrency_model(ProviderType.MODAL_INFERENCE)

    # Theoretical max
    theoretical_max = model.max_throughput_requests_per_minute

    # Actual throughput test (1 minute load test)
    start_time = time.time()
    completed = 0

    executor = ParallelExecutor(max_concurrent=model.max_parallel_nodes)

    # Send requests for 1 minute
    while time.time() - start_time < 60:
        nodes = [MockLLMNode() for _ in range(model.max_parallel_nodes)]
        results = await executor.execute_parallel(nodes, ctx)
        completed += len([r for r in results if r.is_success])

    actual_throughput = completed  # Requests in 1 minute

    # Should achieve ≥90% of theoretical
    efficiency = actual_throughput / theoretical_max
    assert efficiency >= 0.9, f"Efficiency {efficiency:.1%} < 90%"
```

### AC4: Configurable per provider ✓
**Test**: Verify different providers have different limits
```python
def test_configurable_per_provider():
    """Verify different providers get different limits."""
    anthropic = get_concurrency_model(ProviderType.ANTHROPIC)
    openai = get_concurrency_model(ProviderType.OPENAI)
    modal = get_concurrency_model(ProviderType.MODAL_INFERENCE)

    # Different providers → different limits
    assert anthropic.max_parallel_llm_calls != openai.max_parallel_llm_calls
    assert openai.max_parallel_llm_calls != modal.max_parallel_llm_calls

    # Modal (local) should have highest concurrency
    assert modal.max_parallel_llm_calls > anthropic.max_parallel_llm_calls
```

## Implementation Plan

### Phase 1: Data Structures
1. Create `ProviderType` enum
2. Create `ProviderRateLimits` dataclass
3. Create provider limits registry (ANTHROPIC_TIER1_LIMITS, etc.)

### Phase 2: ConcurrencyModel
1. Implement `ConcurrencyModel` class with computed properties
2. Implement `max_parallel_llm_calls` calculation
3. Implement `max_parallel_nodes` calculation
4. Implement `max_throughput_requests_per_minute`
5. Implement `to_resource_limits()` conversion

### Phase 3: Integration
1. Create `get_concurrency_model()` helper
2. Update H4 ParallelExecutor usage examples
3. Integration with ADR 001 dual-provider routing

### Phase 4: Testing
1. Unit tests: Calculation logic, edge cases
2. Provider tests: Verify limits for each provider
3. Integration tests: Use with ParallelExecutor
4. Load tests: Verify no rate limit errors (AC2), throughput (AC3)

### Phase 5: Documentation
1. Update HOLE_INVENTORY.md
2. Add constraint propagation event
3. Update SESSION_STATE.md
4. Export from `lift_sys.dspy_signatures`

## Constraints Propagated

### To H4: ParallelizationImpl
**New Constraint**: SHOULD use ConcurrencyModel to set max_concurrent
**Reasoning**: H16 provides calculated limits, H4 should use them
**Impact**: ParallelExecutor examples should show integration

### To H3: CachingStrategy (future)
**New Constraint**: MUST respect max_llm_calls when cache misses occur
**Reasoning**: Cache misses trigger LLM calls, must stay within rate limits
**Impact**: Cache implementation needs rate limit awareness

## Alternative Designs Considered

### 1. Token Bucket Algorithm (Deferred)
**Pros**: Smooth rate limiting, handles bursts
**Cons**: Complex, requires state tracking across requests
**Decision**: Start with static limits, add token bucket in Phase 5 if needed

### 2. Dynamic Adjustment (Deferred)
**Pros**: Adapts to actual usage patterns
**Cons**: Requires telemetry, complex feedback loop
**Decision**: Static calculation first, dynamic adjustment later if needed

### 3. Per-Request Rate Limiting (Rejected)
**Pros**: Fine-grained control
**Cons**: High overhead, complex coordination
**Decision**: Use semaphore limiting at executor level (H4)

## Provider Rate Limit Sources

**Anthropic Claude API** (as of 2025):
- Tier 1: 50 RPM, 40K TPM, 5 concurrent requests
- Tier 2: 1000 RPM, 80K TPM, 5 concurrent requests
- Source: https://docs.anthropic.com/claude/reference/rate-limits

**OpenAI GPT API** (as of 2025):
- Tier 1: 500 RPM, 30K TPM
- Tier 2: 3500 RPM, 60K TPM
- Source: https://platform.openai.com/docs/guides/rate-limits

**Modal Inference** (deployment-specific):
- Based on GPU count (1 GPU = ~600 RPM)
- Queue depth typically 4-8
- Latency: 0.5-1.0s with GPU acceleration

## Future Enhancements

1. **Dynamic Limits**: Adjust based on actual error rates
2. **Token Bucket**: Smooth burst handling
3. **Multi-Tenant**: Different limits per user/organization
4. **Cost-Based**: Optimize for cost, not just throughput
5. **Adaptive**: Learn optimal concurrency from telemetry

---

**Status**: Ready for implementation
**Next Steps**: Implement ConcurrencyModel → Create tests → Integrate with H4
