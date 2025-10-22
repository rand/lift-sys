"""
Parallelization Implementation (H4)

Concurrent execution of independent graph nodes.

This module provides async-based parallel execution for graph nodes, enabling
performance improvements while maintaining determinism and safety through
copy-on-execute state isolation.

Design Principles:
1. Async-First: Use asyncio.gather for concurrent I/O-bound LLM calls
2. State Isolation: Copy-on-execute prevents race conditions
3. Resource Management: Semaphore limiting respects concurrency bounds
4. Determinism: Same inputs → same outputs (validated by tests)

Resolution for Hole H4: ParallelizationImpl
Status: Implementation
Phase: 4 (Week 4)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .node_interface import BaseNode, End, RunContext

# Type variables
StateT = TypeVar("StateT", bound=BaseModel)


@dataclass
class NodeResult(Generic[StateT]):
    """
    Result of a single node execution.

    Captures execution metadata:
    - Node that was executed
    - Next node to execute (or End)
    - Updated context (with modified state)
    - Execution timing
    - Error information (if failed)
    """

    node: BaseNode[StateT]
    next_node: BaseNode[StateT] | End
    context: RunContext[StateT]
    execution_time_ms: float
    error: Exception | None = None

    @property
    def is_success(self) -> bool:
        """Check if execution succeeded."""
        return self.error is None

    @property
    def is_end(self) -> bool:
        """Check if next node is termination."""
        return isinstance(self.next_node, End)


class MergeStrategy(Enum):
    """Strategy for merging parallel execution results."""

    FIRST_SUCCESS = "first_success"  # Use first successful result
    ALL_SUCCESS = "all_success"  # Require all succeed, merge provenance
    MAJORITY = "majority"  # Most common output (for determinism validation)


@dataclass
class ParallelExecutionError(Exception):
    """Error during parallel execution."""

    message: str
    failed_nodes: list[tuple[BaseNode, Exception]] = field(default_factory=list)
    partial_results: list[NodeResult] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation of parallel execution error."""
        failures = len(self.failed_nodes)
        return f"{self.message} ({failures} nodes failed)"


class ParallelExecutor(Generic[StateT]):
    """
    Executes independent graph nodes concurrently.

    Features:
    - asyncio.gather for concurrent I/O-bound execution
    - asyncio.Semaphore for resource limiting (respects provider limits)
    - Copy-on-execute for state isolation (prevents race conditions)
    - Configurable merge strategies for result combination
    - Error capture and propagation

    Example:
        executor = ParallelExecutor(max_concurrent=4)
        results = await executor.execute_parallel(nodes, ctx)
        merged_ctx = executor.merge_states(results, MergeStrategy.FIRST_SUCCESS)
    """

    def __init__(self, max_concurrent: int = 4):
        """
        Initialize parallel executor.

        Args:
            max_concurrent: Maximum concurrent node executions
                           (limited by provider rate limits, see H16)
        """
        if max_concurrent < 1:
            raise ValueError(f"max_concurrent must be ≥1, got {max_concurrent}")

        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_parallel(
        self,
        nodes: list[BaseNode[StateT]],
        ctx: RunContext[StateT],
    ) -> list[NodeResult[StateT]]:
        """
        Execute nodes in parallel with state isolation.

        Strategy:
        1. Create isolated context per node (copy state)
        2. Execute nodes concurrently with semaphore limiting
        3. Collect results with timing and error info
        4. Return all results for merging

        Args:
            nodes: List of independent nodes to execute in parallel
            ctx: Shared execution context (state will be copied per node)

        Returns:
            List of NodeResult with execution metadata (one per node)

        Note:
            - Does not raise on individual node failures
            - Check result.error to detect failures
            - Use merge_states() to combine results
        """
        if not nodes:
            return []

        # Execute all nodes concurrently with isolation
        tasks = [self.execute_single_with_isolation(node, ctx) for node in nodes]
        results = await asyncio.gather(*tasks)

        return list(results)

    async def execute_single_with_isolation(
        self,
        node: BaseNode[StateT],
        ctx: RunContext[StateT],
    ) -> NodeResult[StateT]:
        """
        Execute single node with isolated state copy.

        Implementation:
        1. Deep copy RunContext (isolate state)
        2. Acquire semaphore slot (limit concurrency)
        3. Execute node.run(isolated_ctx)
        4. Measure execution time
        5. Handle exceptions gracefully
        6. Return NodeResult with all metadata

        Args:
            node: Node to execute
            ctx: Context to copy and execute with

        Returns:
            NodeResult with execution metadata and updated context
        """
        # Acquire semaphore before copying (limit concurrent copies too)
        async with self._semaphore:
            # Create isolated context (prevents race conditions)
            isolated_ctx = self._copy_context(ctx)

            # Execute with timing
            start_time = time.perf_counter()
            try:
                next_node = await node.run(isolated_ctx)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                return NodeResult(
                    node=node,
                    next_node=next_node,
                    context=isolated_ctx,
                    execution_time_ms=elapsed_ms,
                    error=None,
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                return NodeResult(
                    node=node,
                    next_node=End(),  # Terminate on error
                    context=isolated_ctx,
                    execution_time_ms=elapsed_ms,
                    error=e,
                )

    def merge_states(
        self,
        results: list[NodeResult[StateT]],
        strategy: MergeStrategy = MergeStrategy.FIRST_SUCCESS,
    ) -> RunContext[StateT]:
        """
        Merge execution results into single context.

        Strategies:
        - FIRST_SUCCESS: Use first successful result (default)
        - ALL_SUCCESS: Require all to succeed, merge provenance
        - MAJORITY: Use most common output (for determinism validation)

        Args:
            results: List of node execution results
            strategy: How to merge multiple results

        Returns:
            Merged RunContext with combined state and provenance

        Raises:
            ParallelExecutionError: If merge fails (e.g., no successes)
        """
        if not results:
            raise ParallelExecutionError(
                message="Cannot merge empty results list",
                failed_nodes=[],
                partial_results=[],
            )

        if strategy == MergeStrategy.FIRST_SUCCESS:
            return self._merge_first_success(results)
        elif strategy == MergeStrategy.ALL_SUCCESS:
            return self._merge_all_success(results)
        elif strategy == MergeStrategy.MAJORITY:
            return self._merge_majority(results)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")

    def _merge_first_success(self, results: list[NodeResult[StateT]]) -> RunContext[StateT]:
        """
        Use first successful result.

        Use case: Alternative paths (try multiple strategies, use first that works)
        """
        for result in results:
            if result.is_success:
                return result.context

        # All failed
        failed = [(r.node, r.error) for r in results if r.error is not None]
        raise ParallelExecutionError(
            message="All parallel nodes failed",
            failed_nodes=failed,
            partial_results=results,
        )

    def _merge_all_success(self, results: list[NodeResult[StateT]]) -> RunContext[StateT]:
        """
        Require all to succeed, merge provenance.

        Use case: Fan-out/fan-in (process multiple items, need all results)
        """
        # Check all succeeded
        failures = [(r.node, r.error) for r in results if not r.is_success]
        if failures:
            raise ParallelExecutionError(
                message=f"{len(failures)} of {len(results)} nodes failed (ALL_SUCCESS requires all)",
                failed_nodes=failures,
                partial_results=results,
            )

        # Merge provenance from all results
        # Use first result as base, append provenance from others
        merged_ctx = self._copy_context(results[0].context)

        for result in results[1:]:
            # Append provenance entries
            merged_ctx.provenance.extend(result.context.provenance)

            # Merge metadata (simple dict update, later results overwrite)
            merged_ctx.metadata.update(result.context.metadata)

        return merged_ctx

    def _merge_majority(self, results: list[NodeResult[StateT]]) -> RunContext[StateT]:
        """
        Use most common output (for determinism validation).

        Use case: Determinism validation (run same node N times, verify same output)
        """
        # Hash state snapshots to find most common
        state_hashes: dict[str, list[NodeResult[StateT]]] = {}

        for result in results:
            if result.is_success:
                # Hash state for comparison
                state_json = result.context.state.model_dump_json(sort_keys=True)
                state_hash = hash(state_json)
                state_key = str(state_hash)

                if state_key not in state_hashes:
                    state_hashes[state_key] = []
                state_hashes[state_key].append(result)

        if not state_hashes:
            failed = [(r.node, r.error) for r in results if not r.is_success]
            raise ParallelExecutionError(
                message="All parallel nodes failed (no successful results to merge)",
                failed_nodes=failed,
                partial_results=results,
            )

        # Find most common state
        most_common_key = max(state_hashes.keys(), key=lambda k: len(state_hashes[k]))
        most_common_results = state_hashes[most_common_key]

        # Use first result with most common state
        return most_common_results[0].context

    def _copy_context(self, ctx: RunContext[StateT]) -> RunContext[StateT]:
        """
        Create deep copy of RunContext for state isolation.

        Uses:
        - Pydantic model_copy(deep=True) for state
        - dict/list copies for metadata/provenance
        """
        return RunContext(
            state=ctx.state.model_copy(deep=True),
            execution_id=ctx.execution_id,
            user_id=ctx.user_id,
            metadata=ctx.metadata.copy(),
            provenance=ctx.provenance.copy(),  # Shallow copy of list (entries are dicts)
        )

    def get_statistics(self, results: list[NodeResult[StateT]]) -> dict[str, Any]:
        """
        Compute execution statistics from results.

        Returns:
            Dictionary with timing, success/failure counts, errors
        """
        successes = [r for r in results if r.is_success]
        failures = [r for r in results if not r.is_success]

        timings = [r.execution_time_ms for r in results]

        return {
            "total_nodes": len(results),
            "successes": len(successes),
            "failures": len(failures),
            "success_rate": len(successes) / len(results) if results else 0.0,
            "avg_time_ms": sum(timings) / len(timings) if timings else 0.0,
            "min_time_ms": min(timings) if timings else 0.0,
            "max_time_ms": max(timings) if timings else 0.0,
            "total_time_ms": sum(timings),
            "errors": [str(r.error) for r in failures],
        }


__all__ = [
    "NodeResult",
    "MergeStrategy",
    "ParallelExecutionError",
    "ParallelExecutor",
]
