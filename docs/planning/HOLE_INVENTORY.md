# Hole Inventory - DSPy + Pydantic AI Architecture

**Date**: 2025-10-20
**Status**: TRACKING (19 holes, 0 resolved)
**Version**: 1.0

---

## Overview

This document catalogs all typed holes in the DSPy + Pydantic AI architecture proposal. Each hole represents an unknown or underspecified element that must be resolved during implementation.

**Total Holes**: 19
**Resolved**: 0
**In Progress**: 0
**Blocked**: 0
**Ready**: 3 (H6, H9, H14)

---

## Hole Classification

### By Type
- **Implementation** (5): H1, H2, H3, H4, H5
- **Interface** (4): H6, H7, H8, H9
- **Specification** (4): H10, H11, H12, H13
- **Constraint** (3): H14, H15, H16
- **Validation** (3): H17, H18, H19

### By Priority
- **Critical Path** (6): H6, H1, H10, H17, H4, H2
- **High Priority** (7): H8, H9, H11, H14, H15, H16, H18
- **Medium Priority** (6): H3, H5, H7, H12, H13, H19

---

## Hole Catalog

### H1: ProviderAdapter
**Type**: Implementation
**Kind**: `DSPyProvider`
**Status**: ✅ RESOLVED (2025-10-21)

**Description**: Dual-route integration layer between DSPy and LLM providers

**Architectural Decision**: ADR 001 - Dual-Provider Routing Strategy
- **Route 1**: Best Available (Anthropic/OpenAI/Google) for standard tasks
- **Route 2**: Modal Inference System for constrained generation (XGrammar/llguidance/aici)

**Type Signature**:
```python
from enum import Enum

class ProviderRoute(Enum):
    BEST_AVAILABLE = "best_available"
    MODAL_INFERENCE = "modal_inference"

class ProviderAdapter:
    def __init__(
        self,
        modal_provider: ModalProvider,
        best_available_provider: BestAvailableProvider | None = None,
        config: ProviderConfig | None = None,
    ) -> None: ...

    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        llguidance_grammar: str | None = None,
        **kwargs
    ) -> dspy.Prediction: ...

    def _determine_route(self, **kwargs) -> ProviderRoute: ...

    @property
    def supports_xgrammar(self) -> bool: ...
```

**Constraints**:
- MUST route to Modal when XGrammar/llguidance/aici required (ADR 001)
- MUST route to Best Available for standard tasks (ADR 001)
- MUST preserve XGrammar constraints on Modal route
- MUST support async execution on both routes
- MUST be compatible with DSPy.LM interface
- SHOULD maintain current performance (<16s p50 latency)
- MUST track which route was used (for H10 metrics)

**Routing Decision Criteria**:
- `schema` parameter present → Modal route (XGrammar)
- `llguidance_grammar` present → Modal route
- `aici_control` present → Modal route
- `speculative_decode=True` → Modal route
- Otherwise → Best Available route

**Dependencies**:
- **Blocks**: H8 (OptimizationAPI), H10 (OptimizationMetrics)
- **Blocked by**: H6 (NodeSignatureInterface - RESOLVED)

**Acceptance Criteria**:
- [x] Can execute DSPy signature through Modal endpoint
- [x] XGrammar schema passed through correctly
- [x] Async execution works
- [x] Latency within 10% of current baseline
- [x] Resource tracking integrated
- [ ] Best Available provider integration (Phase 3)
- [ ] Routing logic implements ADR 001
- [ ] Route tracking for metrics

**Current Implementation**: `lift_sys/dspy_signatures/provider_adapter.py` (277 lines)
- ✅ Modal provider integration complete
- ✅ Resource tracking complete
- ⏳ Best Available provider pending (Phase 3)
- ⏳ Routing logic update needed for ADR 001

**Resolution Notes**:
- Phase 2 implementation: Modal provider only
- Phase 3 update: Add Best Available provider and routing logic per ADR 001

**Assigned To**: Phase 2 team
**Resolved**: 2025-10-21
**Target Phase**: Phase 2 (Week 2) - Initial, Phase 3 (Week 3) - Full routing

---

### H2: StatePersistence
**Type**: Implementation
**Kind**: `GraphStateStore`
**Status**: ⏳ Blocked by H6

**Description**: Mechanism for persisting and restoring Pydantic AI graph state

**Type Signature**:
```python
class StatePersistence:
    async def save(self, execution_id: UUID, state: GraphState) -> None: ...
    async def load(self, execution_id: UUID) -> GraphState: ...
    async def update_node_output(self, execution_id: UUID, node: str, output: dict) -> None: ...
```

**Constraints**:
- MUST support round-trip serialization (no data loss)
- MUST handle Pydantic models (IR, TypedHoles, etc.)
- MUST be atomic (no partial states)
- SHOULD use existing Supabase infrastructure

**Dependencies**:
- **Blocks**: H11 (ExecutionHistorySchema)
- **Blocked by**: H6 (NodeSignatureInterface - needs to know what state looks like)

**Acceptance Criteria**:
- [ ] Save → Kill → Resume works correctly
- [ ] All Pydantic models serialize/deserialize
- [ ] Performance: <100ms for save/load
- [ ] Integration test: 100 consecutive save/load cycles

**Resolution Ideas**:
1. JSONB column in Supabase with Pydantic .model_dump()
2. Dedicated state table with versioning
3. Hybrid: Small states inline, large states in object storage

**Assigned To**: TBD
**Target Phase**: Phase 2 (Week 2)

---

### H3: CachingStrategy
**Type**: Implementation
**Kind**: `NodeCache`
**Status**: ⏳ Blocked by H4

**Description**: Caching mechanism for deterministic node outputs

**Type Signature**:
```python
class CachingStrategy:
    def cache_key(self, node: BaseNode, inputs: dict) -> str: ...
    async def get(self, key: str) -> NodeResult | None: ...
    async def set(self, key: str, result: NodeResult, ttl: int) -> None: ...
    async def invalidate(self, pattern: str) -> int: ...
```

**Constraints**:
- MUST be deterministic (same inputs → same key)
- MUST handle concurrent access (parallel execution)
- MUST support invalidation (node version changes)
- SHOULD integrate with Redis or similar

**Dependencies**:
- **Blocks**: Performance optimization
- **Blocked by**: H4 (ParallelizationImpl - needs concurrency model)

**Acceptance Criteria**:
- [ ] Cache hit rate >60% on repeated prompts
- [ ] No race conditions in 1000 parallel tests
- [ ] Invalidation works correctly on node updates
- [ ] Speedup >2x on cached paths

**Resolution Ideas**:
1. Redis with SHA256(node_id + input_hash) keys
2. LRU cache with size limits
3. Distributed cache with consistent hashing

**Assigned To**: TBD
**Target Phase**: Phase 5 (Week 5)

---

### H4: ParallelizationImpl
**Type**: Implementation
**Kind**: `ParallelExecutor`
**Status**: ⏳ Blocked by H6

**Description**: Concurrent execution of independent graph nodes

**Type Signature**:
```python
class ParallelizationImpl:
    async def execute_parallel(
        self,
        nodes: list[BaseNode],
        ctx: RunContext
    ) -> list[NodeResult]: ...
    def merge_states(self, states: list[GraphState]) -> GraphState: ...
```

**Constraints**:
- MUST avoid race conditions (copy-on-execute)
- MUST respect resource limits (max concurrent)
- MUST be deterministic (same inputs → same outputs)
- MUST handle failures gracefully

**Dependencies**:
- **Blocks**: H3 (CachingStrategy), H16 (ConcurrencyModel), H18 (ConcurrencyValidation)
- **Blocked by**: H6 (NodeSignatureInterface)

**Acceptance Criteria**:
- [ ] Speedup ≥2x on parallel paths
- [ ] 100 test runs produce identical results
- [ ] No deadlocks or race conditions
- [ ] Proper error propagation

**Resolution Ideas**:
1. asyncio.gather with semaphore limiting
2. ProcessPoolExecutor for CPU-bound nodes
3. Custom scheduler with priority queue

**Assigned To**: TBD
**Target Phase**: Phase 4 (Week 4)

---

### H5: ErrorRecovery
**Type**: Implementation
**Kind**: `ErrorHandler`
**Status**: ⏳ Blocked by H9

**Description**: Handling node failures and graph-level errors

**Type Signature**:
```python
class ErrorRecovery:
    async def handle_node_error(
        self,
        node: BaseNode,
        error: Exception,
        ctx: RunContext
    ) -> RecoveryAction: ...
    def should_retry(self, error: Exception, attempt: int) -> bool: ...
```

**Constraints**:
- MUST preserve graph state on failure
- MUST support retry with backoff
- MUST log errors for debugging
- SHOULD allow graceful degradation

**Dependencies**:
- **Blocks**: Production readiness
- **Blocked by**: H9 (ValidationHooks - needs validation framework)

**Acceptance Criteria**:
- [ ] Transient errors retry successfully
- [ ] Fatal errors terminate gracefully
- [ ] State preserved on all failure modes
- [ ] Error messages actionable

**Resolution Ideas**:
1. Retry decorator with exponential backoff
2. Circuit breaker pattern
3. Fallback to baseline on repeated failures

**Assigned To**: TBD
**Target Phase**: Phase 7 (Week 7)

---

### H6: NodeSignatureInterface
**Type**: Interface
**Kind**: `Protocol`
**Status**: ✅ READY (no blockers)

**Description**: Contract between graph nodes and DSPy signatures

**Type Signature**:
```python
class BaseNode(Protocol):
    signature: Type[dspy.Signature]

    async def run(self, ctx: RunContext[StateT]) -> NextNode | End: ...
    def extract_inputs(self, state: StateT) -> dict: ...
    def update_state(self, state: StateT, result: dspy.Prediction) -> None: ...
```

**Constraints**:
- MUST be type-safe (generic over StateT)
- MUST support async execution
- MUST compose with Pydantic AI Graph
- MUST preserve DSPy semantics

**Dependencies**:
- **Blocks**: H1 (ProviderAdapter), H2 (StatePersistence), H4 (ParallelizationImpl), H5 (ErrorRecovery)
- **Blocked by**: NONE (ready to start!)

**Acceptance Criteria**:
- [ ] Prototype node executes with DSPy signature
- [ ] Type checker validates (mypy --strict passes)
- [ ] Integrates with Pydantic AI Graph
- [ ] Example: ExtractIntentNode working end-to-end

**Resolution Ideas**:
1. **PREFERRED**: Generic BaseNode with signature composition
2. Mixin pattern with SignatureExecutor
3. Decorator pattern wrapping DSPy modules

**Assigned To**: TBD
**Target Phase**: Phase 1 (Week 1)
**Priority**: CRITICAL PATH

---

### H7: TraceVisualizationProtocol
**Type**: Interface
**Kind**: `Protocol`
**Status**: ⏳ Blocked by H11

**Description**: Interface for exposing graph execution traces to UI

**Type Signature**:
```python
class TraceVisualizationProtocol(Protocol):
    def get_trace(self, execution_id: UUID) -> ExecutionTrace: ...
    def get_node_timeline(self, execution_id: UUID) -> list[NodeEvent]: ...
    def get_state_history(self, execution_id: UUID) -> list[StateSnapshot]: ...
```

**Constraints**:
- MUST support real-time updates (WebSocket)
- MUST include node inputs/outputs
- MUST show timing information
- SHOULD support filtering and search

**Dependencies**:
- **Blocks**: UX features
- **Blocked by**: H11 (ExecutionHistorySchema - needs schema definition)

**Acceptance Criteria**:
- [ ] UI can display execution trace
- [ ] Real-time updates work via WebSocket
- [ ] Performance: <100ms query time
- [ ] Supports filtering by node type

**Resolution Ideas**:
1. REST API + WebSocket for updates
2. GraphQL with subscriptions
3. Server-sent events for streaming

**Assigned To**: TBD
**Target Phase**: Phase 5 (Week 5)

---

### H8: OptimizationAPI
**Type**: Interface
**Kind**: `Protocol`
**Status**: ⏳ Blocked by H10

**Description**: Interface between pipeline and MIPROv2 optimizer with route-aware optimization

**Architectural Constraint**: ADR 001 - Must support route switching as optimization strategy

**Type Signature**:
```python
class OptimizationAPI(Protocol):
    def optimize(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
        metric: Callable,
        route_strategy: ProviderRoute | None = None,  # ADR 001
        **kwargs
    ) -> OptimizedPipeline: ...

    def suggest_route_changes(
        self,
        metrics: OptimizationMetrics
    ) -> dict[str, ProviderRoute]: ...  # ADR 001
```

**Constraints**:
- MUST support MIPROv2 and COPRO optimizers
- MUST accept custom metrics
- MUST return optimized pipeline
- SHOULD support continuous optimization
- MUST support route switching as optimization strategy (ADR 001)
- MUST allow manual route override for experimentation (ADR 001)
- MUST validate route migrations (ensure Modal-only features not used on Best Available) (ADR 001)

**Dependencies**:
- **Blocks**: Optimization capability
- **Blocked by**: H10 (OptimizationMetrics - needs metric definition), H1 (ProviderAdapter - RESOLVED with routing pending)

**Acceptance Criteria**:
- [ ] MIPROv2 runs successfully
- [ ] Custom metrics accepted
- [ ] Optimized pipeline demonstrates improvement
- [ ] Integration test with 20 examples
- [ ] Route switching recommendations work (ADR 001)
- [ ] Manual route override supported (ADR 001)
- [ ] Route migration validation prevents errors (ADR 001)

**Resolution Ideas**:
1. Direct DSPy optimizer interface
2. Wrapper with lift-sys specific config
3. Async optimization with progress tracking

**Assigned To**: TBD
**Target Phase**: Phase 3 (Week 3)

---

### H9: ValidationHooks
**Type**: Interface
**Kind**: `Protocol`
**Status**: ✅ READY (no blockers)

**Description**: Pluggable validation at graph execution points

**Type Signature**:
```python
class ValidationHooks(Protocol):
    async def pre_node(self, node: BaseNode, ctx: RunContext) -> ValidationResult: ...
    async def post_node(self, node: BaseNode, result: NodeResult) -> ValidationResult: ...
    async def pre_graph(self, state: GraphState) -> ValidationResult: ...
```

**Constraints**:
- MUST be composable (multiple validators)
- MUST support async execution
- MUST provide actionable error messages
- SHOULD be opt-in (performance)

**Dependencies**:
- **Blocks**: H5 (ErrorRecovery)
- **Blocked by**: NONE (ready to start!)

**Acceptance Criteria**:
- [ ] Can register multiple validators
- [ ] Pre/post hooks execute correctly
- [ ] Validation errors propagate clearly
- [ ] Performance impact <5% when disabled

**Resolution Ideas**:
1. **PREFERRED**: List of validators with chain-of-responsibility
2. Event-driven hooks
3. Decorator pattern on nodes

**Assigned To**: TBD
**Target Phase**: Phase 1 (Week 1)

---

### H10: OptimizationMetrics
**Type**: Specification
**Kind**: `MetricDefinition`
**Status**: ⏳ Blocked by H1

**Description**: Route-aware metrics for evaluating pipeline quality and cost

**Architectural Constraint**: ADR 001 - Must track and optimize across both provider routes

**Type Signature**:
```python
from lift_sys.dspy_signatures.provider_adapter import ProviderRoute

def ir_quality(predicted: IR, expected: IR) -> float: ...
def code_quality(predicted: str, expected: str, tests: list) -> float: ...
def end_to_end(example: Example, prediction: Prediction) -> float: ...

# ADR 001: Route-aware metrics
def route_cost(
    route: ProviderRoute,
    tokens: int,
    duration_ms: float
) -> float: ...

def route_quality(
    route: ProviderRoute,
    task_type: str,
    metrics: dict[str, float]
) -> float: ...

def suggest_route_migration(
    current_route: ProviderRoute,
    task_metrics: dict[str, float]
) -> ProviderRoute | None: ...
```

**Constraints**:
- MUST be measurable (computable from examples)
- MUST be differentiable (or at least smooth)
- MUST correlate with user satisfaction
- SHOULD be composable (sub-metrics)
- MUST track provider_route per execution (ADR 001)
- MUST measure quality metrics per route (ADR 001)
- MUST measure cost metrics per route (API costs vs Modal compute) (ADR 001)
- MUST identify opportunities to migrate tasks between routes (ADR 001)

**Dependencies**:
- **Blocks**: H8 (OptimizationAPI), H17 (OptimizationValidation)
- **Blocked by**: H1 (ProviderAdapter - RESOLVED, routing pending)

**Acceptance Criteria**:
- [ ] Metrics defined mathematically
- [ ] Computed on 20 hand-labeled examples
- [ ] Inter-rater reliability >0.8
- [ ] Correlates with manual quality assessment
- [ ] Route tracking implemented (ADR 001)
- [ ] Cost metrics per route computed (ADR 001)
- [ ] Quality metrics per route computed (ADR 001)
- [ ] Route migration suggestions accurate (ADR 001)

**Resolution Ideas**:
1. **PREFERRED**: Weighted combination of intent, signature, code quality
2. Learned metric via preference model
3. Multi-objective optimization

**Assigned To**: TBD
**Target Phase**: Phase 3 (Week 3)
**Priority**: CRITICAL PATH

---

### H11: ExecutionHistorySchema
**Type**: Specification
**Kind**: `DatabaseSchema`
**Status**: ⏳ Blocked by H2

**Description**: Database schema for storing graph execution traces

**Type Signature**:
```sql
CREATE TABLE graph_executions (
    id UUID PRIMARY KEY,
    graph_type TEXT NOT NULL,
    state JSONB NOT NULL,
    -- ... (see resolution for full schema)
);
```

**Constraints**:
- MUST support replay (deterministic re-execution)
- MUST store node inputs/outputs
- MUST track timing information
- SHOULD support querying by state properties

**Dependencies**:
- **Blocks**: H7 (TraceVisualizationProtocol)
- **Blocked by**: H2 (StatePersistence - needs state structure)

**Acceptance Criteria**:
- [ ] Schema supports all graph types
- [ ] Can replay execution from history
- [ ] Query performance <100ms
- [ ] Supports pagination and filtering

**Resolution Ideas**:
1. **PREFERRED**: JSONB for flexibility + indexed columns for queries
2. Separate tables per graph type
3. Event sourcing with append-only log

**Assigned To**: TBD
**Target Phase**: Phase 2 (Week 2)

---

### H12: ConfidenceCalibration
**Type**: Specification
**Kind**: `ScoringFunction`
**Status**: ⏳ Blocked by H10

**Description**: Method for scoring hole suggestion confidence

**Type Signature**:
```python
def score_suggestion(
    hole: TypedHole,
    suggestion: str,
    context: dict
) -> float:  # 0.0-1.0, calibrated to match accuracy
    ...
```

**Constraints**:
- MUST correlate with actual accuracy
- MUST be calibrated (score 0.8 → 80% chance correct)
- SHOULD improve with feedback
- SHOULD consider multiple factors

**Dependencies**:
- **Blocks**: Suggestion quality
- **Blocked by**: H10 (OptimizationMetrics - uses similar scoring)

**Acceptance Criteria**:
- [ ] Calibration plot: predicted vs actual
- [ ] Brier score <0.2
- [ ] Improves with few-shot learning
- [ ] User study: confidence helpful

**Resolution Ideas**:
1. Logistic regression on features
2. Neural calibration network
3. Isotonic regression

**Assigned To**: TBD
**Target Phase**: Phase 3 (Week 3)

---

### H13: FeatureFlagSchema
**Type**: Specification
**Kind**: `ConfigurationSchema`
**Status**: ⏳ Blocked by H15

**Description**: Configuration for gradual rollout and A/B testing

**Type Signature**:
```python
class FeatureFlagSchema(BaseModel):
    flag_name: str
    enabled_for: list[str]  # User IDs
    rollout_percentage: float  # 0.0-1.0
    override_conditions: dict
```

**Constraints**:
- MUST support user-level flags
- MUST support percentage rollout
- MUST be queryable quickly (<10ms)
- SHOULD support complex conditions

**Dependencies**:
- **Blocks**: Migration strategy
- **Blocked by**: H15 (MigrationConstraints - needs to know what to flag)

**Acceptance Criteria**:
- [ ] Supports user-level overrides
- [ ] Percentage rollout works correctly
- [ ] Query time <10ms
- [ ] Integrates with existing config

**Resolution Ideas**:
1. Database table with caching
2. LaunchDarkly or similar service
3. Environment-based configuration

**Assigned To**: TBD
**Target Phase**: Phase 6 (Week 6)

---

### H14: ResourceLimits
**Type**: Constraint
**Kind**: `ResourceSpecification`
**Status**: ✅ READY (no blockers)

**Description**: Memory, CPU, and concurrency limits for graph execution

**Type Signature**:
```python
class ResourceLimits(BaseModel):
    max_memory_mb: int
    max_cpu_percent: int
    max_concurrent_nodes: int
    max_execution_time_sec: int
```

**Constraints**:
- MUST fit within Modal resource limits
- MUST leave headroom for system overhead
- SHOULD be measurable/enforceable
- SHOULD be configurable per graph type

**Dependencies**:
- **Blocks**: H16 (ConcurrencyModel)
- **Blocked by**: NONE (can measure current usage)

**Acceptance Criteria**:
- [ ] Measured current resource usage
- [ ] Documented limits per Modal tier
- [ ] Headroom calculated (80% rule)
- [ ] Monitoring alerts configured

**Resolution Ideas**:
1. **PREFERRED**: Empirical measurement + 80% safety margin
2. Conservative fixed limits
3. Dynamic limits based on load

**Assigned To**: TBD
**Target Phase**: Phase 1 (Week 1)

---

### H15: MigrationConstraints
**Type**: Constraint
**Kind**: `CompatibilityRequirement`
**Status**: ⏳ Blocked by H2

**Description**: Requirements for backward compatibility with existing sessions

**Type Signature**:
```python
def migrate_session(old: PromptSession) -> GraphExecution:
    """Convert old session format to new graph format."""
    ...
```

**Constraints**:
- MUST preserve all session data (no loss)
- MUST allow resuming old sessions
- MUST support rollback to old format
- SHOULD be idempotent (re-migration safe)

**Dependencies**:
- **Blocks**: H13 (FeatureFlagSchema), H19 (BackwardCompatTest)
- **Blocked by**: H2 (StatePersistence - needs new format)

**Acceptance Criteria**:
- [ ] All session fields mapped correctly
- [ ] 100 production sessions migrate successfully
- [ ] Can resume migrated sessions
- [ ] Rollback tested

**Resolution Ideas**:
1. **PREFERRED**: Explicit migration function with version tags
2. Dual-write during transition
3. Lazy migration on access

**Assigned To**: TBD
**Target Phase**: Phase 6 (Week 6)

---

### H16: ConcurrencyModel
**Type**: Constraint
**Kind**: `ConcurrencySpecification`
**Status**: ⏳ Blocked by H14

**Description**: Maximum concurrent operations given provider limits

**Type Signature**:
```python
class ConcurrencyModel(BaseModel):
    max_parallel_nodes: int
    max_parallel_llm_calls: int
    rate_limit_per_minute: int
```

**Constraints**:
- MUST respect provider rate limits
- MUST account for graph parallelization
- SHOULD maximize throughput
- SHOULD be configurable per provider

**Dependencies**:
- **Blocks**: H4 (ParallelizationImpl)
- **Blocked by**: H14 (ResourceLimits)

**Acceptance Criteria**:
- [ ] Calculated from provider limits
- [ ] No rate limit errors in testing
- [ ] Throughput within 90% of theoretical max
- [ ] Configurable per provider

**Resolution Ideas**:
1. provider_limit / expected_concurrent_graphs
2. Dynamic adjustment based on actual usage
3. Token bucket algorithm

**Assigned To**: TBD
**Target Phase**: Phase 4 (Week 4)

---

### H17: OptimizationValidation
**Type**: Validation
**Kind**: `StatisticalTest`
**Status**: ⏳ Blocked by H10

**Description**: Statistical validation that optimization improves performance

**Type Signature**:
```python
def validate_optimization(
    baseline: Pipeline,
    optimized: Pipeline,
    test_set: list[Example]
) -> ValidationResult:
    # Returns p-value, effect size, recommendation
    ...
```

**Constraints**:
- MUST use statistical significance (p < 0.05)
- MUST measure effect size (Cohen's d)
- SHOULD use held-out test set
- SHOULD account for variance

**Dependencies**:
- **Blocks**: Confidence in deployment
- **Blocked by**: H10 (OptimizationMetrics - needs metric definition)

**Acceptance Criteria**:
- [ ] Paired t-test implemented
- [ ] Effect size calculated
- [ ] Test on 50 held-out examples
- [ ] Documentation of methodology

**Resolution Ideas**:
1. **PREFERRED**: Paired t-test + Cohen's d
2. Bootstrap confidence intervals
3. Bayesian A/B test

**Assigned To**: TBD
**Target Phase**: Phase 7 (Week 7)
**Priority**: CRITICAL PATH

---

### H18: ConcurrencyValidation
**Type**: Validation
**Kind**: `DeterminismTest`
**Status**: ⏳ Blocked by H4

**Description**: Validation that parallel execution is deterministic and safe

**Type Signature**:
```python
def validate_concurrency(
    graph: Graph,
    test_cases: list[TestCase],
    iterations: int = 100
) -> ValidationResult:
    # Returns pass/fail, any non-determinism detected
    ...
```

**Constraints**:
- MUST run many iterations (≥100)
- MUST check for race conditions
- MUST verify determinism
- SHOULD measure performance variance

**Dependencies**:
- **Blocks**: Production deployment confidence
- **Blocked by**: H4 (ParallelizationImpl)

**Acceptance Criteria**:
- [ ] 100 iterations produce identical results
- [ ] No race conditions detected
- [ ] Performance variance <10%
- [ ] Integration test suite

**Resolution Ideas**:
1. **PREFERRED**: Property-based testing with Hypothesis
2. Stress testing with ThreadSanitizer
3. Formal verification of critical sections

**Assigned To**: TBD
**Target Phase**: Phase 4 (Week 4)

---

### H19: BackwardCompatTest
**Type**: Validation
**Kind**: `MigrationTest`
**Status**: ⏳ Blocked by H15

**Description**: Test suite validating session migration correctness

**Type Signature**:
```python
def test_backward_compatibility(
    old_sessions: list[PromptSession]
) -> ValidationResult:
    # Returns pass/fail, any data loss detected
    ...
```

**Constraints**:
- MUST test on real production sessions
- MUST verify no data loss
- MUST test resume functionality
- SHOULD test rollback

**Dependencies**:
- **Blocks**: Deployment confidence
- **Blocked by**: H15 (MigrationConstraints)

**Acceptance Criteria**:
- [ ] 100 production sessions tested
- [ ] 100% migration success
- [ ] All sessions resumable
- [ ] Rollback verified

**Resolution Ideas**:
1. Snapshot-based testing
2. Differential testing (old vs new)
3. Property-based migration tests

**Assigned To**: TBD
**Target Phase**: Phase 6 (Week 6)

---

## Dependency Graph Summary

### Critical Path (Must resolve in order)
```
H6 → H1 → H10 → H17
(NodeSignatureInterface → ProviderAdapter → OptimizationMetrics → OptimizationValidation)
```

**Timeline**: Weeks 1-3, 7

### Parallel Tracks

**Track 1: Execution**
```
H6 → H2 → H11 → H7
(Interface → Persistence → History → Visualization)
```

**Track 2: Performance**
```
H6 → H4 → H3
     ↓
    H16 → H18
(Interface → Parallelization → Caching)
         (ConcurrencyModel → Validation)
```

**Track 3: Production**
```
H2 → H15 → H13 → H19
(Persistence → Migration → FeatureFlags → Testing)
```

---

## Status Updates

### Format
Each hole resolution should update this section:

```markdown
### H{N}: {HoleName} - {Date}
**Status**: Resolved ✅
**Resolution**: {Brief description}
**Path**: {File path to implementation}
**Validated**: {Yes/No + test results}
**Propagated Constraints**:
- {Hole ID}: {New constraint added}
```

---

**Document Status**: ACTIVE TRACKING
**Last Updated**: 2025-10-20
**Next Review**: After each hole resolution
