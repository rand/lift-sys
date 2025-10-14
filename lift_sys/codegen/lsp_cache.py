"""LSP response caching layer.

This module provides a thread-safe cache for LSP responses with TTL-based
expiration and file modification tracking for intelligent invalidation.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """Cached LSP response with metadata.

    Attributes:
        value: The cached response value
        timestamp: Unix timestamp when entry was created
        file_path: Path to the file this entry is for
        hits: Number of times this entry was accessed
        file_mtime: File modification time for invalidation (optional)
    """

    value: Any
    timestamp: float
    file_path: Path
    hits: int = 0
    file_mtime: float | None = None


class LSPCache:
    """Thread-safe cache for LSP responses with TTL and LRU eviction.

    This cache stores LSP query results to reduce duplicate queries and
    improve performance. It supports:
    - TTL-based expiration (default 5 minutes)
    - File modification-based invalidation
    - LRU eviction when at capacity
    - Thread-safe concurrent access

    Example:
        >>> cache = LSPCache(ttl=300, max_size=1000)
        >>> # Check cache
        >>> result = await cache.get(file_path, "document_symbols")
        >>> if result is None:
        ...     result = await lsp.request_document_symbols(file_path)
        ...     await cache.put(file_path, "document_symbols", result)
    """

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default 5 minutes)
            max_size: Maximum cache entries before LRU eviction
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, file_path: Path, operation: str, **params) -> str:
        """Generate cache key from operation parameters.

        Args:
            file_path: File being queried
            operation: LSP operation name (e.g., "document_symbols")
            **params: Additional operation parameters

        Returns:
            MD5 hash of the composite key
        """
        # Hash file path + operation + params for consistent key
        key_data = f"{file_path}:{operation}:{sorted(params.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, file_path: Path, operation: str, **params) -> Any | None:
        """Get cached response if valid.

        Args:
            file_path: File being queried
            operation: LSP operation name
            **params: Additional operation parameters

        Returns:
            Cached value if valid, None otherwise
        """
        key = self._make_key(file_path, operation, **params)

        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check TTL expiration
            if time.time() - entry.timestamp > self.ttl:
                del self._cache[key]
                return None

            # Check file modification (invalidate if file changed)
            if entry.file_mtime and file_path.exists():
                current_mtime = file_path.stat().st_mtime
                if current_mtime > entry.file_mtime:
                    del self._cache[key]
                    return None

            # Valid cache hit
            entry.hits += 1
            return entry.value

    async def put(self, file_path: Path, operation: str, value: Any, **params) -> None:
        """Store response in cache.

        Args:
            file_path: File being queried
            operation: LSP operation name
            value: Response value to cache
            **params: Additional operation parameters
        """
        key = self._make_key(file_path, operation, **params)

        file_mtime = file_path.stat().st_mtime if file_path.exists() else None

        async with self._lock:
            # LRU eviction if at capacity
            if len(self._cache) >= self.max_size:
                # Remove least recently used (lowest hits, oldest timestamp)
                lru_key = min(self._cache.items(), key=lambda x: (x[1].hits, x[1].timestamp))[0]
                del self._cache[lru_key]

            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                file_path=file_path,
                file_mtime=file_mtime,
            )

    async def invalidate(self, file_path: Path) -> int:
        """Invalidate all cache entries for a file.

        Args:
            file_path: File whose cache entries should be invalidated

        Returns:
            Number of entries invalidated
        """
        count = 0
        async with self._lock:
            # Find all entries for this file by checking stored file_path
            keys_to_delete = [k for k, entry in self._cache.items() if entry.file_path == file_path]

            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        return count

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics:
            - size: Current number of entries
            - max_size: Maximum capacity
            - total_hits: Sum of all hit counts
            - ttl: Time-to-live setting
        """
        total_hits = sum(e.hits for e in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "ttl": self.ttl,
        }


__all__ = ["LSPCache", "CacheEntry"]
