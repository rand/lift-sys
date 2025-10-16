#!/usr/bin/env python3
"""
Simplified E2E test with simpler prompts (no control flow nesting).

Tests the COMPLETE forward mode workflow:
1. Natural language → IR
2. IR → Python code
3. Validate + execute code

This uses simpler functions to avoid indentation complexity.
