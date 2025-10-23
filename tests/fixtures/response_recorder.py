"""
Response recording system for fast, deterministic integration tests.

Records Modal API responses on first run, replays them on subsequent runs.
This enables integration tests to run in seconds instead of minutes.

Usage:
    # In conftest.py
    @pytest.fixture
    def modal_recorder():
        record_mode = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
        return ResponseRecorder(
            fixture_file=Path("tests/fixtures/modal_responses.json"),
            record_mode=record_mode
        )

    # In tests
    async def test_with_recording(modal_recorder):
        ir = await modal_recorder.get_or_record(
            key="find_index_prompt",
            generator_fn=lambda: translator.translate(FIND_INDEX_PROMPT)
        )

Environment Variables:
    RECORD_FIXTURES=true  - Record new responses (overwrites existing)
    RECORD_FIXTURES=false - Use recorded responses (default)
"""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


class ResponseRecorder:
    """
    Records and replays API responses for deterministic testing.

    First run (RECORD_FIXTURES=true):
    - Calls actual API
    - Saves response to fixture file
    - Returns response

    Subsequent runs (RECORD_FIXTURES=false):
    - Loads response from fixture file
    - Returns cached response instantly
    - No API calls

    This approach:
    - Makes tests deterministic
    - Runs in milliseconds instead of seconds/minutes
    - Can update fixtures when API changes
    - Works offline
    """

    def __init__(self, fixture_file: Path, record_mode: bool = False, auto_save: bool = True):
        """
        Initialize response recorder.

        Args:
            fixture_file: Path to JSON file storing responses
            record_mode: If True, call APIs and record responses
                        If False, use cached responses
            auto_save: If True, save after each recording
                      If False, must call save() manually
        """
        self.fixture_file = Path(fixture_file)
        self.record_mode = record_mode
        self.auto_save = auto_save
        self.responses: dict[str, Any] = self._load_fixtures()
        self.cache_hits = 0
        self.cache_misses = 0

    def _load_fixtures(self) -> dict[str, Any]:
        """Load existing fixtures from file."""
        if self.fixture_file.exists():
            try:
                content = self.fixture_file.read_text()
                if not content.strip():
                    return {}
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Warning: Could not load fixtures from {self.fixture_file}: {e}")
                return {}
        return {}

    def _save_fixtures(self) -> None:
        """Save fixtures to file."""
        self.fixture_file.parent.mkdir(parents=True, exist_ok=True)
        self.fixture_file.write_text(json.dumps(self.responses, indent=2, sort_keys=True))

    def _make_key(self, key: str) -> str:
        """
        Normalize key for consistent lookup.

        For long keys (e.g., entire prompts), creates a hash.
        For short keys, uses as-is.
        """
        if len(key) > 100:
            # Hash long keys for readability
            key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
            return f"hash_{key_hash}"
        return key

    async def get_or_record(
        self, key: str, generator_fn: Callable[[], Any], metadata: dict[str, Any] | None = None
    ) -> Any:
        """
        Get cached response or call generator and record.

        Args:
            key: Unique identifier for this response
            generator_fn: Async function to call if not cached
            metadata: Optional metadata to store with response

        Returns:
            Response (from cache or generator)

        Example:
            response = await recorder.get_or_record(
                key="test_prompt_1",
                generator_fn=lambda: translator.translate(prompt),
                metadata={"test": "find_index", "version": "1.0"}
            )
        """
        normalized_key = self._make_key(key)

        # Check cache first
        if not self.record_mode and normalized_key in self.responses:
            self.cache_hits += 1
            entry = self.responses[normalized_key]
            # Return just the response, not metadata
            if isinstance(entry, dict) and "response" in entry:
                return entry["response"]
            return entry

        # Cache miss - call generator
        self.cache_misses += 1

        # Call the generator function
        if asyncio.iscoroutinefunction(generator_fn):
            response = await generator_fn()
        else:
            response = generator_fn()
            # Check if the result is a coroutine (e.g., from a lambda that returns async call)
            if asyncio.iscoroutine(response):
                response = await response

        # Record if in record mode
        if self.record_mode:
            # Store with metadata
            entry = {"response": response, "original_key": key, "metadata": metadata or {}}
            self.responses[normalized_key] = entry

            if self.auto_save:
                self._save_fixtures()

        return response

    def save(self) -> None:
        """Manually save fixtures (if auto_save=False)."""
        self._save_fixtures()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": total,
            "hit_rate": hit_rate,
            "num_cached_responses": len(self.responses),
            "record_mode": self.record_mode,
        }

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self.responses = {}
        if self.fixture_file.exists():
            self.fixture_file.unlink()


# Import asyncio for iscoroutinefunction
import asyncio


class SerializableResponseRecorder(ResponseRecorder):
    """
    Enhanced recorder that handles serialization of complex objects.

    Useful when API responses contain custom objects that need
    conversion to/from JSON.
    """

    def __init__(
        self,
        fixture_file: Path,
        record_mode: bool = False,
        auto_save: bool = True,
        serializer: Callable[[Any], Any] | None = None,
        deserializer: Callable[[Any], Any] | None = None,
    ):
        """
        Initialize with custom serialization.

        Args:
            fixture_file: Path to fixture file
            record_mode: Whether to record or replay
            auto_save: Auto-save after recording
            serializer: Function to convert response to JSON-serializable form
            deserializer: Function to convert JSON back to response object
        """
        super().__init__(fixture_file, record_mode, auto_save)
        self.serializer = serializer or (lambda x: x)
        self.deserializer = deserializer or (lambda x: x)

    async def get_or_record(
        self, key: str, generator_fn: Callable[[], Any], metadata: dict[str, Any] | None = None
    ) -> Any:
        """Get or record with serialization support."""
        normalized_key = self._make_key(key)

        # Check cache
        if not self.record_mode and normalized_key in self.responses:
            self.cache_hits += 1
            entry = self.responses[normalized_key]
            serialized = (
                entry["response"] if isinstance(entry, dict) and "response" in entry else entry
            )
            # Deserialize on retrieval
            return self.deserializer(serialized)

        # Cache miss
        self.cache_misses += 1

        # Call generator
        if asyncio.iscoroutinefunction(generator_fn):
            response = await generator_fn()
        else:
            response = generator_fn()
            # Check if the result is a coroutine (e.g., from a lambda that returns async call)
            if asyncio.iscoroutine(response):
                response = await response

        # Record with serialization
        if self.record_mode:
            serialized = self.serializer(response)
            entry = {"response": serialized, "original_key": key, "metadata": metadata or {}}
            self.responses[normalized_key] = entry

            if self.auto_save:
                self._save_fixtures()

        return response
