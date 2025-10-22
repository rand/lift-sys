# H3: CachingStrategy - Preparation Document

**Date**: 2025-10-21
**Status**: Planning
**Phase**: 5 (Week 5)

---

## Overview

H3 (CachingStrategy) defines a caching mechanism for deterministic node outputs, enabling significant performance improvements by avoiding redundant LLM calls for identical inputs.

## Goals

1. **Deterministic**: Same inputs → same cache key
2. **Concurrent-Safe**: Handle parallel access without race conditions
3. **Invalidation**: Support cache invalidation on node version changes
4. **Performance**: Cache hit rate >60%, speedup >2x on cached paths
5. **Flexible Backend**: Support in-memory (development) and Redis (production)

## Context

### Dependencies

**Blocked By**:
- ✅ H4 (ParallelizationImpl) - **RESOLVED**: Provides concurrent execution model

**Blocks**:
- Performance optimization
- Cost reduction (fewer LLM API calls)

**Related**:
- H4 ParallelExecutor: Concurrent node execution requires thread-safe caching
- H6 BaseNode: Nodes provide inputs for cache key generation
- H16 ConcurrencyModel: Cache misses trigger LLM calls → must respect rate limits

### Existing Components

From H4 (ParallelExecutor):
```python
@dataclass
class NodeResult(Generic[StateT]):
    node: BaseNode[StateT]
    next_node: BaseNode[StateT] | End
    context: RunContext[StateT]
    execution_time_ms: float
    error: Exception | None = None
```

From H6 (BaseNode):
```python
class BaseNode(Protocol, Generic[StateT]):
    signature: Any
    def extract_inputs(self, state: StateT) -> dict[str, Any]: ...
    def update_state(self, state: StateT, result: Any) -> None: ...
    async def run(self, ctx: RunContext[StateT]) -> BaseNode[StateT] | End: ...
```

## Design

### Core Abstraction: CachingStrategy

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
import hashlib
import json
from dataclasses import dataclass

StateT = TypeVar("StateT", bound=BaseModel)

@dataclass
class CacheEntry(Generic[StateT]):
    """
    Cached node result with metadata.

    Attributes:
        key: Cache key (SHA256 hash)
        result: Cached NodeResult
        created_at: Unix timestamp when cached
        ttl: Time-to-live in seconds
        hit_count: Number of cache hits
        node_version: Node version for invalidation
    """
    key: str
    result: NodeResult[StateT]
    created_at: float
    ttl: int
    hit_count: int = 0
    node_version: str | None = None

    def is_expired(self, current_time: float) -> bool:
        """Check if entry has expired."""
        return (current_time - self.created_at) > self.ttl

    def is_valid_version(self, node_version: str | None) -> bool:
        """Check if entry matches node version."""
        return self.node_version == node_version


class CachingStrategy(ABC, Generic[StateT]):
    """
    Abstract caching strategy for node execution results.

    Implementations must provide:
    - cache_key(): Deterministic key generation
    - get(): Async cache retrieval
    - set(): Async cache storage
    - invalidate(): Pattern-based invalidation
    - stats(): Cache statistics
    """

    @abstractmethod
    def cache_key(
        self,
        node: BaseNode[StateT],
        inputs: dict[str, Any],
        node_version: str | None = None,
    ) -> str:
        """
        Generate deterministic cache key.

        Key components:
        1. Node type (class name or identifier)
        2. Input hash (SHA256 of sorted JSON)
        3. Node version (optional, for invalidation)

        Args:
            node: Node being executed
            inputs: Extracted inputs from node.extract_inputs()
            node_version: Optional version identifier for invalidation

        Returns:
            SHA256 hex digest as cache key
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> NodeResult[StateT] | None:
        """
        Retrieve cached result.

        Args:
            key: Cache key from cache_key()

        Returns:
            Cached NodeResult if found and valid, None otherwise
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        result: NodeResult[StateT],
        ttl: int = 3600,
        node_version: str | None = None,
    ) -> None:
        """
        Store result in cache.

        Args:
            key: Cache key from cache_key()
            result: NodeResult to cache
            ttl: Time-to-live in seconds (default 1 hour)
            node_version: Optional version for invalidation
        """
        pass

    @abstractmethod
    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Glob-style pattern for keys to invalidate

        Returns:
            Number of entries invalidated
        """
        pass

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit_rate, miss_rate, entry_count, etc.
        """
        pass


class InMemoryCache(CachingStrategy[StateT]):
    """
    In-memory LRU cache with TTL support.

    Features:
    - Thread-safe (asyncio.Lock for concurrent access)
    - LRU eviction when max_size exceeded
    - TTL-based expiration
    - Pattern-based invalidation
    - Hit/miss statistics

    Use cases:
    - Development and testing
    - Single-process deployments
    - Small-scale production (no distributed caching needed)

    Limitations:
    - Not distributed (single process only)
    - Lost on process restart
    - Memory constrained by max_size
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries (LRU eviction)
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl

        # Cache storage
        self._cache: dict[str, CacheEntry[StateT]] = {}

        # Access order for LRU
        self._access_order: list[str] = []

        # Statistics
        self._hits = 0
        self._misses = 0

        # Thread safety
        self._lock = asyncio.Lock()

    def cache_key(
        self,
        node: BaseNode[StateT],
        inputs: dict[str, Any],
        node_version: str | None = None,
    ) -> str:
        """
        Generate cache key from node and inputs.

        Implementation:
        1. Get node identifier (class name)
        2. Sort inputs by key for determinism
        3. JSON serialize inputs
        4. Create composite: node_id:version:input_hash
        5. SHA256 hash the composite

        Example:
            node = GenerateCodeNode()
            inputs = {"prompt": "write hello world"}
            key = cache_key(node, inputs, "v1.0")
            # Returns: "a3f5b8c9..." (64-char hex)
        """
        # Node identifier
        node_id = type(node).__name__

        # Sort and serialize inputs for determinism
        sorted_inputs = json.dumps(inputs, sort_keys=True)

        # Create composite key
        composite = f"{node_id}:{node_version or 'none'}:{sorted_inputs}"

        # SHA256 hash
        return hashlib.sha256(composite.encode()).hexdigest()

    async def get(self, key: str) -> NodeResult[StateT] | None:
        """
        Retrieve from cache with LRU update.

        Implementation:
        1. Acquire lock (thread safety)
        2. Check if key exists
        3. Check if entry expired
        4. If valid: update LRU order, increment hit count, return result
        5. If invalid: remove entry, return None
        """
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired(time.time()):
                del self._cache[key]
                self._access_order.remove(key)
                self._misses += 1
                return None

            # Cache hit: update LRU
            self._access_order.remove(key)
            self._access_order.append(key)
            entry.hit_count += 1
            self._hits += 1

            return entry.result

    async def set(
        self,
        key: str,
        result: NodeResult[StateT],
        ttl: int | None = None,
        node_version: str | None = None,
    ) -> None:
        """
        Store in cache with LRU eviction if needed.

        Implementation:
        1. Acquire lock
        2. If cache full: evict LRU entry
        3. Create CacheEntry
        4. Store entry
        5. Update access order
        """
        async with self._lock:
            # Evict LRU if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                lru_key = self._access_order.pop(0)
                del self._cache[lru_key]

            # Create entry
            entry = CacheEntry(
                key=key,
                result=result,
                created_at=time.time(),
                ttl=ttl or self.default_ttl,
                node_version=node_version,
            )

            # Store and update access order
            self._cache[key] = entry
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate entries matching glob pattern.

        Implementation:
        1. Acquire lock
        2. Find matching keys (fnmatch)
        3. Delete entries
        4. Update access order
        5. Return count

        Patterns:
            "*" - all entries
            "GenerateCodeNode:*" - all GenerateCodeNode entries
            "*:v1.0:*" - all v1.0 entries
        """
        import fnmatch

        async with self._lock:
            # Find matching keys
            matching_keys = [
                k for k in self._cache.keys()
                if fnmatch.fnmatch(k, pattern)
            ]

            # Delete entries
            for key in matching_keys:
                del self._cache[key]
                self._access_order.remove(key)

            return len(matching_keys)

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            - hit_rate: Percentage of cache hits
            - miss_rate: Percentage of cache misses
            - entry_count: Current number of entries
            - max_size: Maximum capacity
            - hits: Total hits
            - misses: Total misses
        """
        total = self._hits + self._misses
        return {
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "miss_rate": self._misses / total if total > 0 else 0.0,
            "entry_count": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
        }


class NoOpCache(CachingStrategy[StateT]):
    """
    No-op cache for testing or disabling caching.

    Always returns None on get(), does nothing on set().
    Useful for benchmarking or comparing cached vs non-cached performance.
    """

    def cache_key(self, node: BaseNode[StateT], inputs: dict[str, Any], node_version: str | None = None) -> str:
        return ""

    async def get(self, key: str) -> NodeResult[StateT] | None:
        return None

    async def set(self, key: str, result: NodeResult[StateT], ttl: int = 3600, node_version: str | None = None) -> None:
        pass

    async def invalidate(self, pattern: str) -> int:
        return 0

    def stats(self) -> dict[str, Any]:
        return {"hit_rate": 0.0, "miss_rate": 1.0, "entry_count": 0}
```

### Integration with ParallelExecutor

```python
class CachedParallelExecutor(ParallelExecutor[StateT]):
    """
    ParallelExecutor with caching support.

    Wraps H4 ParallelExecutor with cache layer:
    1. Check cache before executing node
    2. If hit: return cached result
    3. If miss: execute node, cache result
    4. Respects H16 concurrency limits on cache misses
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        cache: CachingStrategy[StateT] | None = None,
        cache_enabled: bool = True,
    ):
        super().__init__(max_concurrent=max_concurrent)
        self.cache = cache or InMemoryCache[StateT]()
        self.cache_enabled = cache_enabled

    async def execute_with_cache(
        self,
        node: BaseNode[StateT],
        ctx: RunContext[StateT],
        node_version: str | None = None,
    ) -> NodeResult[StateT]:
        """
        Execute node with caching.

        Flow:
        1. Extract inputs from state
        2. Generate cache key
        3. Check cache (if enabled)
        4. If hit: return cached result (update context)
        5. If miss: execute node, cache result, return
        """
        if not self.cache_enabled:
            return await self.execute_single_with_isolation(node, ctx)

        # Extract inputs for cache key
        inputs = node.extract_inputs(ctx.state)

        # Generate cache key
        key = self.cache.cache_key(node, inputs, node_version)

        # Check cache
        cached_result = await self.cache.get(key)
        if cached_result is not None:
            # Cache hit: update context with cached state
            return NodeResult(
                node=node,
                next_node=cached_result.next_node,
                context=cached_result.context,
                execution_time_ms=0.0,  # Instant from cache
                error=None,
            )

        # Cache miss: execute node
        result = await self.execute_single_with_isolation(node, ctx)

        # Cache successful results only
        if result.is_success:
            await self.cache.set(key, result, node_version=node_version)

        return result
```

## Acceptance Criteria

### AC1: Cache hit rate >60% on repeated prompts ✓

**Test**: Simulate repeated prompts with identical inputs
```python
async def test_ac1_cache_hit_rate():
    """
    AC1: Cache hit rate >60% on repeated prompts.

    Test:
    1. Execute same node 10 times with identical inputs
    2. First execution: cache miss
    3. Next 9 executions: cache hits
    4. Hit rate = 9/10 = 90% > 60%
    """
    cache = InMemoryCache[TestState]()
    executor = CachedParallelExecutor(cache=cache)

    node = MockLLMNode()
    ctx = RunContext(state=TestState(value=42), execution_id="test")

    # Execute 10 times
    for _ in range(10):
        await executor.execute_with_cache(node, ctx)

    stats = cache.stats()
    assert stats["hit_rate"] > 0.6, f"Hit rate {stats['hit_rate']:.1%} < 60%"
    assert stats["hits"] == 9
    assert stats["misses"] == 1
```

### AC2: No race conditions in 1000 parallel tests ✓

**Test**: Concurrent access to cache from multiple tasks
```python
async def test_ac2_no_race_conditions():
    """
    AC2: No race conditions in 1000 parallel tests.

    Test:
    1. Create 1000 tasks accessing cache concurrently
    2. Mix of get/set operations
    3. Verify no data corruption
    4. Verify consistent state
    """
    cache = InMemoryCache[TestState]()

    async def access_cache(i: int):
        key = f"key_{i % 100}"  # 100 unique keys, 10 concurrent per key

        # Read
        result = await cache.get(key)

        # Write
        if result is None:
            await cache.set(
                key,
                NodeResult(
                    node=MockLLMNode(),
                    next_node=End(),
                    context=RunContext(state=TestState(value=i), execution_id=f"test-{i}"),
                    execution_time_ms=0.0,
                ),
            )

    # 1000 concurrent accesses
    await asyncio.gather(*[access_cache(i) for i in range(1000)])

    # Verify consistent state
    stats = cache.stats()
    assert stats["entry_count"] == 100  # 100 unique keys
    assert stats["entry_count"] <= cache.max_size
```

### AC3: Invalidation works correctly on node updates ✓

**Test**: Cache invalidation with patterns
```python
async def test_ac3_invalidation_on_node_updates():
    """
    AC3: Invalidation works correctly on node updates.

    Test:
    1. Cache results for multiple nodes with version "v1.0"
    2. Invalidate pattern "*:v1.0:*"
    3. Verify all v1.0 entries removed
    4. Verify other versions unaffected
    """
    cache = InMemoryCache[TestState]()

    # Cache v1.0 entries
    for i in range(5):
        key = cache.cache_key(MockLLMNode(), {"value": i}, "v1.0")
        await cache.set(
            key,
            NodeResult(...),
            node_version="v1.0",
        )

    # Cache v2.0 entries
    for i in range(5):
        key = cache.cache_key(MockLLMNode(), {"value": i}, "v2.0")
        await cache.set(
            key,
            NodeResult(...),
            node_version="v2.0",
        )

    # Invalidate v1.0
    count = await cache.invalidate("*:v1.0:*")
    assert count == 5

    # Verify v2.0 unaffected
    stats = cache.stats()
    assert stats["entry_count"] == 5
```

### AC4: Speedup >2x on cached paths ✓

**Test**: Compare execution time with/without cache
```python
async def test_ac4_speedup_on_cached_paths():
    """
    AC4: Speedup >2x on cached paths.

    Test:
    1. Execute slow node (100ms) 10 times without cache
    2. Execute same node 10 times with cache (first miss, rest hits)
    3. Verify cached execution ≥2x faster
    """
    # Without cache
    no_cache_executor = CachedParallelExecutor(cache_enabled=False)
    node = SlowMockNode(delay_ms=100)
    ctx = RunContext(state=TestState(), execution_id="test")

    start = time.time()
    for _ in range(10):
        await no_cache_executor.execute_with_cache(node, ctx)
    no_cache_time = time.time() - start

    # With cache
    cached_executor = CachedParallelExecutor(cache=InMemoryCache[TestState]())

    start = time.time()
    for _ in range(10):
        await cached_executor.execute_with_cache(node, ctx)
    cached_time = time.time() - start

    speedup = no_cache_time / cached_time
    assert speedup > 2.0, f"Speedup {speedup:.1f}x < 2x"
```

## Implementation Plan

### Phase 1: Core Abstractions
1. Create `CachingStrategy` protocol
2. Create `CacheEntry` dataclass
3. Create `cache_key()` implementation

### Phase 2: InMemoryCache
1. Implement `InMemoryCache` with LRU eviction
2. Add thread safety (asyncio.Lock)
3. Implement TTL-based expiration
4. Add statistics tracking

### Phase 3: Integration
1. Create `CachedParallelExecutor` wrapping H4
2. Implement `execute_with_cache()` method
3. Add cache hit/miss metrics

### Phase 4: Testing
1. Unit tests: Cache key generation, LRU eviction, TTL expiration
2. Concurrency tests: Race conditions, parallel access
3. Integration tests: CachedParallelExecutor with H4
4. Performance tests: All acceptance criteria

### Phase 5: Documentation
1. Update HOLE_INVENTORY.md
2. Create H3_COMPLETION_SUMMARY.md
3. Export from `lift_sys.dspy_signatures`

## Constraints Propagated

### From H16: ConcurrencyModel

**Constraint**: MUST respect max_llm_calls when cache misses occur

**Reasoning**: Cache misses trigger LLM calls → must stay within rate limits

**Impact**: CachedParallelExecutor must use H4's semaphore limiting

### To Future: Redis Integration

**Constraint**: SHOULD support distributed caching via Redis

**Reasoning**: Production deployments need shared cache across processes

**Impact**: CachingStrategy abstraction allows swapping InMemoryCache for RedisCache

## Alternative Designs Considered

### 1. Redis-First (Deferred)
**Pros**: Production-ready, distributed
**Cons**: Requires Redis deployment, more complex
**Decision**: Start with InMemoryCache, add RedisCache in Phase 6

### 2. Cache-Aside vs Write-Through
**Pros (Cache-Aside)**: Simpler, cache only on demand
**Cons (Write-Through)**: More complex, proactive caching
**Decision**: Use cache-aside pattern (check cache, execute on miss, cache result)

### 3. Serialization Format
**Options**: JSON, Pickle, MessagePack
**Decision**: Use Pydantic model_dump() for NodeResult serialization (JSON-compatible, safe)

## Future Enhancements

1. **Redis Backend**: Distributed caching for multi-process deployments
2. **Cache Warming**: Preload cache with common prompts
3. **Adaptive TTL**: Adjust TTL based on hit patterns
4. **Compression**: Compress large results to save memory
5. **Metrics Integration**: Export cache metrics to observability (H7)

---

**Status**: Ready for implementation
**Next Steps**: Implement CachingStrategy → Create InMemoryCache → Test with H4 → Integrate
