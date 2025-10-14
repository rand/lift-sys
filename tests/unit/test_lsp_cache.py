"""Tests for LSP response caching."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from lift_sys.codegen.lsp_cache import CacheEntry, LSPCache


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_cache_entry(self):
        """Test creating a cache entry."""
        file_path = Path("/test/file.py")
        entry = CacheEntry(value={"test": "data"}, timestamp=time.time(), file_path=file_path)

        assert entry.value == {"test": "data"}
        assert entry.file_path == file_path
        assert entry.hits == 0
        assert entry.file_mtime is None

    def test_cache_entry_with_mtime(self):
        """Test cache entry with file modification time."""
        file_path = Path("/test/file.py")
        entry = CacheEntry(
            value={"test": "data"},
            timestamp=time.time(),
            file_path=file_path,
            file_mtime=1234567890.0,
        )

        assert entry.file_path == file_path
        assert entry.file_mtime == 1234567890.0


class TestLSPCache:
    """Tests for LSPCache."""

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initialization."""
        cache = LSPCache(ttl=300, max_size=1000)

        assert cache.ttl == 300
        assert cache.max_size == 1000
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = LSPCache()
        file_path = Path("/test/file.py")

        result = await cache.get(file_path, "document_symbols")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit returns stored value."""
        cache = LSPCache()
        file_path = Path("/test/file.py")
        test_data = [{"name": "TestClass", "kind": 5}]

        # Store in cache
        await cache.put(file_path, "document_symbols", test_data)

        # Retrieve from cache
        result = await cache.get(file_path, "document_symbols")

        assert result == test_data

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL."""
        cache = LSPCache(ttl=1)  # 1 second TTL
        file_path = Path("/test/file.py")
        test_data = [{"name": "TestClass", "kind": 5}]

        # Store in cache
        await cache.put(file_path, "document_symbols", test_data)

        # Immediate hit works
        result = await cache.get(file_path, "document_symbols")
        assert result == test_data

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        result = await cache.get(file_path, "document_symbols")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_file_modification_invalidation(self):
        """Test cache invalidation when file is modified."""
        cache = LSPCache()

        # Create a temporary file
        with NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("# test")
            file_path = Path(f.name)

        try:
            test_data = [{"name": "TestClass", "kind": 5}]

            # Store in cache
            await cache.put(file_path, "document_symbols", test_data)

            # Should hit cache
            result = await cache.get(file_path, "document_symbols")
            assert result == test_data

            # Modify file
            await asyncio.sleep(0.1)  # Ensure different mtime
            with open(file_path, "a") as f:
                f.write("\n# modified")

            # Should miss cache (file modified)
            result = await cache.get(file_path, "document_symbols")
            assert result is None

        finally:
            file_path.unlink()

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LSPCache(max_size=3)  # Small cache for testing

        file1 = Path("/test/file1.py")
        file2 = Path("/test/file2.py")
        file3 = Path("/test/file3.py")
        file4 = Path("/test/file4.py")

        # Fill cache to capacity
        await cache.put(file1, "document_symbols", {"data": 1})
        await cache.put(file2, "document_symbols", {"data": 2})
        await cache.put(file3, "document_symbols", {"data": 3})

        # Access file2 to increase its hits
        await cache.get(file2, "document_symbols")

        # Add file4, should evict file1 (least hits, oldest)
        await cache.put(file4, "document_symbols", {"data": 4})

        # file1 should be evicted
        result = await cache.get(file1, "document_symbols")
        assert result is None

        # file2 should still be cached (had hits)
        result = await cache.get(file2, "document_symbols")
        assert result == {"data": 2}

        # file4 should be cached
        result = await cache.get(file4, "document_symbols")
        assert result == {"data": 4}

    @pytest.mark.asyncio
    async def test_cache_hit_increments_counter(self):
        """Test that cache hits increment the hit counter."""
        cache = LSPCache()
        file_path = Path("/test/file.py")
        test_data = [{"name": "TestClass", "kind": 5}]

        # Store in cache
        await cache.put(file_path, "document_symbols", test_data)

        # Get cache key and entry
        key = cache._make_key(file_path, "document_symbols")
        initial_hits = cache._cache[key].hits

        # Access multiple times
        for _ in range(5):
            await cache.get(file_path, "document_symbols")

        # Hits should have increased
        final_hits = cache._cache[key].hits
        assert final_hits == initial_hits + 5

    @pytest.mark.asyncio
    async def test_cache_invalidate_file(self):
        """Test invalidating all cache entries for a file."""
        cache = LSPCache()
        file_path = Path("/test/file.py")

        # Store multiple operations for same file
        await cache.put(file_path, "document_symbols", [{"data": 1}])
        await cache.put(file_path, "hover", {"content": "test"})

        # Invalidate file
        count = await cache.invalidate(file_path)

        # Should have invalidated both entries
        assert count == 2

        # Both should be cache misses now
        result1 = await cache.get(file_path, "document_symbols")
        result2 = await cache.get(file_path, "hover")
        assert result1 is None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = LSPCache()

        # Add multiple entries
        await cache.put(Path("/test/file1.py"), "document_symbols", [{"data": 1}])
        await cache.put(Path("/test/file2.py"), "document_symbols", [{"data": 2}])

        # Clear cache
        await cache.clear()

        # Cache should be empty
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = LSPCache(ttl=300, max_size=1000)

        # Initially empty
        stats = cache.stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 1000
        assert stats["total_hits"] == 0
        assert stats["ttl"] == 300

        # Add entries and access them
        await cache.put(Path("/test/file.py"), "document_symbols", [{"data": 1}])
        await cache.get(Path("/test/file.py"), "document_symbols")
        await cache.get(Path("/test/file.py"), "document_symbols")

        # Stats should update
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["total_hits"] == 2

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = LSPCache()
        file_path = Path("/test/file.py")

        key1 = cache._make_key(file_path, "document_symbols")
        key2 = cache._make_key(file_path, "document_symbols")

        # Same inputs should generate same key
        assert key1 == key2

        # Different operation should generate different key
        key3 = cache._make_key(file_path, "hover")
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_cache_parameters_affect_key(self):
        """Test that additional parameters affect cache key."""
        cache = LSPCache()
        file_path = Path("/test/file.py")

        # Store with different parameters
        await cache.put(file_path, "completion", [{"label": "test1"}], position=10)
        await cache.put(file_path, "completion", [{"label": "test2"}], position=20)

        # Should be separate cache entries
        result1 = await cache.get(file_path, "completion", position=10)
        result2 = await cache.get(file_path, "completion", position=20)

        assert result1 == [{"label": "test1"}]
        assert result2 == [{"label": "test2"}]

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self):
        """Test cache handles concurrent access correctly."""
        cache = LSPCache()
        file_path = Path("/test/file.py")

        # Concurrent puts
        tasks = [cache.put(file_path, f"operation_{i}", [{"data": i}]) for i in range(10)]
        await asyncio.gather(*tasks)

        # All should be cached
        results = await asyncio.gather(*[cache.get(file_path, f"operation_{i}") for i in range(10)])

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result == [{"data": i}]
