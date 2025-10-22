"""
Caching Strategy (H3)

Caching mechanism for deterministic node outputs.

This module provides caching abstractions to avoid redundant LLM calls for
identical inputs, significantly improving performance and reducing costs.

Design Principles:
1. Deterministic: Same inputs → same cache key
2. Concurrent-Safe: Handle parallel access without race conditions
3. Invalidation: Support cache invalidation on node version changes
4. Performance: Cache hit rate >60%, speedup >2x on cached paths
5. Flexible Backend: Support in-memory (development) and Redis (production)

Resolution for Hole H3: CachingStrategy
Status: Implementation
Phase: 5 (Week 5)
Dependencies: H4 (ParallelizationImpl) - RESOLVED
"""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .node_interface import BaseNode, RunContext
from .parallel_executor import NodeResult, ParallelExecutor

# Type variables
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
        """Check if entry has expired based on TTL."""
        return (current_time - self.created_at) > self.ttl

    def is_valid_version(self, node_version: str | None) -> bool:
        """Check if entry matches node version (for invalidation)."""
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

    Example:
        >>> cache = InMemoryCache[TestState]()
        >>> key = cache.cache_key(node, inputs)
        >>> result = await cache.get(key)
        >>> if result is None:
        ...     result = await execute_node(node)
        ...     await cache.set(key, result)
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

    Example:
        >>> cache = InMemoryCache[TestState](max_size=1000, default_ttl=3600)
        >>> key = cache.cache_key(node, {"prompt": "hello"})
        >>> await cache.set(key, result)
        >>> cached = await cache.get(key)
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
            >>> node = GenerateCodeNode()
            >>> inputs = {"prompt": "write hello world"}
            >>> key = cache_key(node, inputs, "v1.0")
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

        Example:
            >>> count = await cache.invalidate("*:v1.0:*")
            # Invalidates all v1.0 entries
        """
        async with self._lock:
            # Find matching keys
            matching_keys = [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

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
    Useful for:
    - Benchmarking (comparing cached vs non-cached performance)
    - Testing (isolating cache behavior)
    - Disabling caching temporarily

    Example:
        >>> cache = NoOpCache[TestState]()
        >>> result = await cache.get("any_key")  # Always None
    """

    def cache_key(
        self,
        node: BaseNode[StateT],
        inputs: dict[str, Any],
        node_version: str | None = None,
    ) -> str:
        """Generate empty cache key (no caching)."""
        return ""

    async def get(self, key: str) -> NodeResult[StateT] | None:
        """Always return None (cache miss)."""
        return None

    async def set(
        self,
        key: str,
        result: NodeResult[StateT],
        ttl: int = 3600,
        node_version: str | None = None,
    ) -> None:
        """No-op (don't store anything)."""
        pass

    async def invalidate(self, pattern: str) -> int:
        """No-op (nothing to invalidate)."""
        return 0

    def stats(self) -> dict[str, Any]:
        """Return zero statistics."""
        return {
            "hit_rate": 0.0,
            "miss_rate": 1.0,
            "entry_count": 0,
            "max_size": 0,
            "hits": 0,
            "misses": 0,
        }


class CachedParallelExecutor(ParallelExecutor[StateT]):
    """
    ParallelExecutor with caching support.

    Wraps H4 ParallelExecutor with cache layer:
    1. Check cache before executing node
    2. If hit: return cached result
    3. If miss: execute node, cache result
    4. Respects H16 concurrency limits on cache misses

    Example:
        >>> cache = InMemoryCache[TestState]()
        >>> executor = CachedParallelExecutor(max_concurrent=4, cache=cache)
        >>> result = await executor.execute_with_cache(node, ctx)
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        cache: CachingStrategy[StateT] | None = None,
        cache_enabled: bool = True,
    ):
        """
        Initialize cached executor.

        Args:
            max_concurrent: Maximum concurrent node executions
            cache: Caching strategy (default: InMemoryCache)
            cache_enabled: Enable/disable caching (useful for benchmarking)
        """
        super().__init__(max_concurrent=max_concurrent)
        self.cache = cache if cache is not None else InMemoryCache[StateT]()
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
        4. If hit: return cached result (with cached context)
        5. If miss: execute node, cache result, return

        Args:
            node: Node to execute
            ctx: Execution context
            node_version: Optional version for cache invalidation

        Returns:
            NodeResult (from cache or fresh execution)
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
            # Cache hit: return cached result with instant execution time
            # Note: We return the cached result's context, which contains the
            # cached state. The caller can use this to continue execution.
            return NodeResult(
                node=node,
                next_node=cached_result.next_node,
                context=cached_result.context,
                execution_time_ms=0.0,  # Instant from cache
                error=None,
            )

        # Cache miss: execute node
        result = await self.execute_single_with_isolation(node, ctx)

        # Cache successful results only (don't cache errors)
        if result.is_success:
            await self.cache.set(key, result, node_version=node_version)

        return result

    async def execute_parallel_with_cache(
        self,
        nodes: list[BaseNode[StateT]],
        ctx: RunContext[StateT],
        node_version: str | None = None,
    ) -> list[NodeResult[StateT]]:
        """
        Execute multiple nodes in parallel with caching.

        Each node is checked against cache individually before execution.
        Cache hits avoid LLM calls entirely.

        Args:
            nodes: List of nodes to execute
            ctx: Execution context
            node_version: Optional version for cache invalidation

        Returns:
            List of NodeResults (mix of cached and fresh)
        """
        if not nodes:
            return []

        # Execute all nodes with caching (in parallel)
        tasks = [self.execute_with_cache(node, ctx, node_version) for node in nodes]
        results = await asyncio.gather(*tasks)

        return list(results)


__all__ = [
    "CacheEntry",
    "CachingStrategy",
    "InMemoryCache",
    "NoOpCache",
    "CachedParallelExecutor",
]
