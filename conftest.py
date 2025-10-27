"""Root pytest configuration for lift-sys.

This file provides global pytest configuration and plugin loading.
All pytest_plugins declarations must be in this top-level file.
"""

# Load causal test fixtures plugin
# Moved from tests/causal/conftest.py to comply with pytest deprecation warning
pytest_plugins = ["tests.causal.fixtures.scm_test_fixtures"]
