"""
DSPy signatures module for lift-sys.

This module provides the interface between Pydantic AI graph nodes and DSPy signatures,
enabling declarative LLM task specifications with automatic optimization.
"""

from lift_sys.dspy_signatures.node_interface import (
    BaseNode,
    End,
    NextNode,
    RunContext,
)

__all__ = [
    "BaseNode",
    "RunContext",
    "NextNode",
    "End",
]
