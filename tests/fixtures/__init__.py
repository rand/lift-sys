"""
Test fixtures and response recording infrastructure.

This package provides utilities for fast, deterministic testing:
- Response recording/replay for Modal API calls
- Pre-generated test data and sample IRs
- Reusable test fixtures
"""

from .response_recorder import ResponseRecorder, SerializableResponseRecorder

__all__ = [
    "ResponseRecorder",
    "SerializableResponseRecorder",
]
