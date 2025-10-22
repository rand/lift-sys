# H4: ParallelizationImpl - Preparation Document

**Date**: 2025-10-21
**Status**: Planning
**Phase**: 4 (Week 4)

---

## Overview

H4 (ParallelizationImpl) provides concurrent execution of independent graph nodes, enabling parallel processing paths in the DSPy + Pydantic AI graph execution system.

## Goals

1. **Parallelization**: Execute independent nodes concurrently using asyncio
2. **Determinism**: Same inputs → same outputs (100 runs produce identical results)
3. **Safety**: Avoid race conditions through copy-on-execute pattern
4. **Resource Management**: Respect concurrency limits (H16)
5. **Performance**: Achieve ≥2x speedup on parallel paths

## Context

### Dependencies

**Blocked By**:
- ✅ H6 (NodeSignatureInterface) - **RESOLVED**: Provides BaseNode protocol

**Blocks**:
- H3 (CachingStrategy) - Will use ParallelExecutor for cache invalidation
- H16 (ConcurrencyModel) - Will define max_concurrent limits
- H18 (ConcurrencyValidation) - Will validate determinism

### Existing Components

From H6 (NodeSignatureInterface):
```python
class BaseNode(Protocol, Generic[StateT]):
    signature: Any  # DSPy signature

    def extract_inputs(self, state: StateT) -> dict[str, Any]: ...
    def update_state(self, state: StateT, result: dspy.Prediction) -> None: ...
    async def run(self, ctx: RunContext[StateT]) -> BaseNode[StateT] | End: ...

@dataclass
class RunContext(Generic[StateT]):
    state: StateT
    execution_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: list[dict[str, Any]] = field(default_factory=list)
```

From H2 (StatePersistence):
```python
class GraphState(BaseModel):
    execution_id: str
    state_snapshot: dict[str, Any]
    state_type: str
    provenance: list[dict[str, Any]]
    metadata: dict[str, Any]
    user_id: str | None
    created_at: str
    updated_at: str
```

## Design

### Core Abstraction: ParallelExecutor

```python
from dataclasses import dataclass
from typing import Generic, TypeVar
import asyncio

StateT = TypeVar("StateT", bound=BaseModel)

@dataclass
class NodeResult(Generic[StateT]):
    """
    Result of a single node execution.

    Captures:
    - Node that was executed
    - Next node to execute (or End)
    - Updated context (with modified state)
    - Execution metadata (timing, errors)
    """
    node: BaseNode[StateT]
    next_node: BaseNode[StateT] | End
    context: RunContext[StateT]
    execution_time_ms: float
    error: Exception | None = None

class ParallelExecutor(Generic[StateT]):
    """
    Executes independent graph nodes concurrently.

    Key features:
    - asyncio.gather for concurrent execution
    - asyncio.Semaphore for resource limiting
    - Copy-on-execute for state isolation
    - Error propagation with context
    """

    def __init__(self, max_concurrent: int = 4):
        """
        Initialize parallel executor.

        Args:
            max_concurrent: Maximum concurrent node executions
        """
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
            nodes: List of independent nodes to execute
            ctx: Shared execution context (state will be copied per node)

        Returns:
            List of NodeResult with execution metadata

        Raises:
            ParallelExecutionError: If all nodes fail or critical error occurs
        """
        ...

    def merge_states(
        self,
        results: list[NodeResult[StateT]],
        strategy: MergeStrategy = MergeStrategy.FIRST_SUCCESS,
    ) -> RunContext[StateT]:
        """
        Merge execution results into single context.

        Strategies:
        - FIRST_SUCCESS: Use first successful result
        - ALL_SUCCESS: Require all to succeed, merge provenance
        - MAJORITY: Use most common output (for determinism validation)

        Args:
            results: List of node execution results
            strategy: How to merge multiple results

        Returns:
            Merged RunContext with combined state and provenance

        Raises:
            MergeError: If merge fails (e.g., no successes with FIRST_SUCCESS)
        """
        ...

    async def execute_single_with_isolation(
        self,
        node: BaseNode[StateT],
        ctx: RunContext[StateT],
    ) -> NodeResult[StateT]:
        """
        Execute single node with isolated state copy.

        Implementation:
        1. Deep copy RunContext (isolate state)
        2. Acquire semaphore slot
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
        ...

class MergeStrategy(Enum):
    """Strategy for merging parallel execution results."""
    FIRST_SUCCESS = "first_success"  # Use first successful result
    ALL_SUCCESS = "all_success"      # Require all succeed, merge provenance
    MAJORITY = "majority"            # Most common output (for validation)

@dataclass
class ParallelExecutionError(Exception):
    """Error during parallel execution."""
    failed_nodes: list[tuple[BaseNode, Exception]]
    partial_results: list[NodeResult]
```

### State Isolation Strategy

**Problem**: Multiple nodes modifying shared state → race conditions

**Solution**: Copy-on-Execute
1. Deep copy RunContext before each node execution
2. Each node operates on isolated state copy
3. Merge strategy determines final state
4. No shared mutable state during execution

**Implementation**:
```python
def _copy_context(ctx: RunContext[StateT]) -> RunContext[StateT]:
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
        provenance=ctx.provenance.copy(),  # Shallow copy of list, entries are immutable dicts
    )
```

### Resource Management

**Semaphore Pattern**:
```python
async def execute_single_with_isolation(self, node, ctx):
    async with self._semaphore:  # Limit concurrent executions
        isolated_ctx = self._copy_context(ctx)
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
```

### Merge Strategies

**1. FIRST_SUCCESS** (Default):
- Use case: Alternative paths (try multiple strategies, use first that works)
- Logic: Return first result with error=None
- Provenance: Only from successful path

**2. ALL_SUCCESS**:
- Use case: Fan-out/fan-in (process multiple items, need all results)
- Logic: Require all results to succeed, merge provenance from all
- State: Merge by combining lists/appending fields (task-specific)

**3. MAJORITY**:
- Use case: Determinism validation (run same node N times, verify same output)
- Logic: Hash state outputs, find most common
- Validation: Assert all outputs identical (for AC: 100 runs identical)

## Acceptance Criteria

### AC1: Speedup ≥2x on parallel paths ✓

**Test Setup**:
- Create 4 independent nodes (each takes ~100ms)
- Sequential execution: ~400ms
- Parallel execution (max_concurrent=4): ~100ms
- Speedup: 4x (exceeds 2x requirement)

**Validation**:
```python
async def test_speedup_parallel_paths():
    nodes = [SlowNode(delay_ms=100) for _ in range(4)]
    ctx = RunContext(state=TestState())

    # Sequential
    start = time.perf_counter()
    for node in nodes:
        await node.run(ctx)
    sequential_time = time.perf_counter() - start

    # Parallel
    executor = ParallelExecutor(max_concurrent=4)
    start = time.perf_counter()
    results = await executor.execute_parallel(nodes, ctx)
    parallel_time = time.perf_counter() - start

    speedup = sequential_time / parallel_time
    assert speedup >= 2.0, f"Speedup {speedup:.2f}x < 2.0x required"
```

### AC2: 100 test runs produce identical results ✓

**Determinism Validation**:
```python
async def test_deterministic_100_runs():
    node = TestNode()  # Deterministic node
    ctx = RunContext(state=TestState(value=42))
    executor = ParallelExecutor(max_concurrent=4)

    # Run 100 times
    outputs = []
    for _ in range(100):
        results = await executor.execute_parallel([node], ctx)
        output_hash = hash(results[0].context.state.model_dump_json())
        outputs.append(output_hash)

    # All outputs identical
    assert len(set(outputs)) == 1, "Outputs varied across runs (non-deterministic)"
```

### AC3: No deadlocks or race conditions ✓

**Race Condition Test**:
```python
async def test_no_race_conditions():
    # Create nodes that would race if state not isolated
    nodes = [IncrementNode() for _ in range(10)]
    ctx = RunContext(state=TestState(counter=0))

    executor = ParallelExecutor(max_concurrent=10)
    results = await executor.execute_parallel(nodes, ctx)

    # If state isolated: each sees counter=0, increments to 1
    # If race condition: undefined behavior
    for result in results:
        assert result.context.state.counter == 1, "State not properly isolated"
```

**Deadlock Test**:
```python
async def test_no_deadlocks():
    # Create many nodes to stress semaphore
    nodes = [QuickNode() for _ in range(100)]
    ctx = RunContext(state=TestState())

    executor = ParallelExecutor(max_concurrent=4)

    # Should complete without hanging
    with asyncio.timeout(5.0):  # 5 second timeout
        results = await executor.execute_parallel(nodes, ctx)

    assert len(results) == 100
```

### AC4: Proper error propagation ✓

**Error Handling Test**:
```python
async def test_error_propagation():
    nodes = [
        SuccessNode(),
        FailNode(ValueError("Test error")),
        SuccessNode(),
    ]
    ctx = RunContext(state=TestState())
    executor = ParallelExecutor(max_concurrent=3)

    results = await executor.execute_parallel(nodes, ctx)

    # All results returned (no exception thrown)
    assert len(results) == 3

    # Failed node has error
    assert results[1].error is not None
    assert isinstance(results[1].error, ValueError)

    # Successful nodes have no error
    assert results[0].error is None
    assert results[2].error is None
```

## Implementation Plan

### Phase 1: Core Data Structures
1. Create `NodeResult[StateT]` dataclass
2. Create `MergeStrategy` enum
3. Create `ParallelExecutionError` exception

### Phase 2: ParallelExecutor Implementation
1. Implement `__init__` with semaphore setup
2. Implement `_copy_context` for state isolation
3. Implement `execute_single_with_isolation` with timing and error handling
4. Implement `execute_parallel` with asyncio.gather
5. Implement `merge_states` with strategy support

### Phase 3: Testing
1. Unit tests: State isolation, context copying, merge strategies
2. Performance tests: Speedup validation (AC1)
3. Determinism tests: 100 runs identical (AC2)
4. Safety tests: No race conditions, no deadlocks (AC3)
5. Error tests: Proper propagation and recovery (AC4)

### Phase 4: Documentation & Integration
1. Update HOLE_INVENTORY.md
2. Add constraint propagation event
3. Update SESSION_STATE.md
4. Export from `lift_sys.dspy_signatures`

## Constraints Propagated

### To H16: ConcurrencyModel
**New Constraint**: MUST define max_concurrent parameter for ParallelExecutor
**Reasoning**: H4 uses semaphore-based limiting, needs concurrency bounds
**Impact**: H16 must specify provider-specific limits (e.g., OpenAI 100/min, Modal GPU count)

### To H3: CachingStrategy
**New Constraint**: SHOULD support parallel cache lookups
**Reasoning**: H4 enables parallel node execution, cache should not be bottleneck
**Impact**: Cache implementation must be thread-safe or use async locks

### To H18: ConcurrencyValidation
**New Constraint**: MUST validate determinism using MAJORITY merge strategy
**Reasoning**: H4 provides MAJORITY strategy specifically for validation
**Impact**: H18 can use execute_parallel with MAJORITY to verify outputs

## Alternative Designs Considered

### 1. ProcessPoolExecutor (Rejected)
**Pros**: True parallelism (not limited by GIL)
**Cons**:
- Overhead of pickling/unpickling state
- DSPy signatures may not be picklable
- Async/await doesn't work with ProcessPoolExecutor
**Decision**: Use asyncio.gather (I/O-bound workload, LLM calls)

### 2. ThreadPoolExecutor (Rejected)
**Pros**: Can use with sync code
**Cons**:
- GIL limits parallelism
- DSPy async signatures preferred
- Thread safety harder than asyncio
**Decision**: Use asyncio.gather (async-first architecture)

### 3. Custom Scheduler with Priority Queue (Deferred)
**Pros**: Fine-grained control, priority scheduling
**Cons**: Complex, premature optimization
**Decision**: Start with asyncio.gather, add scheduler later if needed (Phase 5+)

## Performance Targets

- **Parallel Speedup**: ≥2x for N independent nodes (AC1)
- **Overhead**: <10ms per node for context copying
- **Determinism**: 100% identical outputs across runs (AC2)
- **Error Overhead**: <1ms for error capture and wrapping

## Future Enhancements

1. **Dynamic Concurrency**: Adjust max_concurrent based on provider rate limits
2. **Priority Scheduling**: High-priority nodes execute first
3. **Partial Merge**: Merge partial results before all nodes complete (streaming)
4. **Retry Logic**: Automatic retry for failed nodes with exponential backoff
5. **Dependency Graph**: Auto-detect dependencies, maximize parallelism

---

**Status**: Ready for implementation
**Next Steps**: Implement ParallelExecutor → Create tests → Update documentation
