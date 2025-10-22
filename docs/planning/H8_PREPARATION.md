# H8: OptimizationAPI - Implementation Preparation

**Date**: 2025-10-21
**Status**: Ready to Start (Unblocked by H10)
**Phase**: 3 (Week 3)
**Priority**: High (blocks H17, critical for optimization capability)

---

## Overview

H8 provides the interface between lift-sys pipelines and DSPy optimizers (MIPROv2, COPRO), with route-aware optimization support per ADR 001.

**Key Goal**: Enable automated pipeline optimization using H10 metrics with intelligent provider route selection.

---

## Dependencies

### Resolved (Ready)
- ✅ **H10**: OptimizationMetrics - Provides metric functions for optimization objectives
- ✅ **H1**: ProviderAdapter - Provides LLM execution with route support (ADR 001)
- ✅ **H6**: NodeSignatureInterface - Provides async execution patterns
- ✅ **H11**: ExecutionHistorySchema - Provides execution tracking

### Blocks
- **H17**: OptimizationValidation (can't validate optimizations without optimization capability)
- **Phase 3 Gate**: Requires H8 + H10 + H12 complete

---

## Type Signature (from HOLE_INVENTORY.md)

```python
class OptimizationAPI(Protocol):
    def optimize(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
        metric: Callable,  # From H10!
        route_strategy: ProviderRoute | None = None,  # ADR 001
        **kwargs
    ) -> OptimizedPipeline: ...

    def suggest_route_changes(
        self,
        metrics: OptimizationMetrics  # From H10!
    ) -> dict[str, ProviderRoute]: ...  # ADR 001
```

---

## Constraints (from Propagation)

### From H10 (Event 8)
**New Constraint**: MUST use H10 metrics as optimization objectives
**Requirements**:
- Use `end_to_end()` or `aggregate_metric()` as default objective
- Support custom metric composition from H10 primitives
- Track route used per ADR 001 via `route_quality()`
- Enable route migration suggestions via `suggest_route_migration()`

### From H1 (Routing)
**Constraint**: MUST support route switching as optimization strategy (ADR 001)
**Requirements**:
- Allow manual route override for experimentation
- Validate route migrations (ensure Modal-only features not used on Best Available)

### From H11 (Execution History)
**Constraint**: MUST track optimization runs in execution history
**Requirements**:
- Store optimizer configuration (MIPROv2 vs COPRO)
- Track before/after metrics
- Enable optimization replay

---

## Acceptance Criteria

From HOLE_INVENTORY.md:
- [ ] MIPROv2 runs successfully
- [ ] Custom metrics accepted (from H10)
- [ ] Optimized pipeline demonstrates improvement
- [ ] Integration test with 20 examples
- [ ] Route switching recommendations work (ADR 001)
- [ ] Manual route override supported (ADR 001)
- [ ] Route migration validation prevents errors (ADR 001)

---

## Implementation Strategy

### Option 1: Direct DSPy Integration (RECOMMENDED)
Wrap DSPy's `MIPROv2` and `COPRO` optimizers with lift-sys-specific configuration.

**Pros**:
- Leverages battle-tested DSPy optimization
- Minimal code to maintain
- Clear separation of concerns

**Cons**:
- Tied to DSPy optimization API

### Option 2: Custom Optimizer Wrapper
Build abstraction layer around optimizers for maximum flexibility.

**Pros**:
- Can swap optimizers easily
- Custom optimization strategies

**Cons**:
- More code to maintain
- Risk of reimplementing DSPy features

**RECOMMENDATION**: Start with Option 1, add abstraction if needed.

---

## Key DSPy APIs to Use

### MIPROv2 (Recommended for Phase 3)
```python
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2(
    metric=end_to_end_metric,  # From H10
    num_candidates=3,
    init_temperature=1.4,
)

optimized_pipeline = optimizer.compile(
    student=pipeline,
    trainset=examples,
    num_trials=10,
)
```

### COPRO (Alternative)
```python
from dspy.teleprompt import COPRO

optimizer = COPRO(
    metric=end_to_end_metric,  # From H10
    breadth=10,
    depth=3,
)

optimized_pipeline = optimizer.compile(
    student=pipeline,
    trainset=examples,
)
```

---

## Route-Aware Optimization (ADR 001)

### Strategy 1: Route as Hyperparameter
Treat provider route as optimization dimension.

**Implementation**:
```python
def optimize_with_routes(pipeline, examples, metric):
    results = {}
    for route in [ProviderRoute.BEST_AVAILABLE, ProviderRoute.MODAL_INFERENCE]:
        # Configure provider adapter with route
        set_route(route)

        # Run optimization
        optimized = optimizer.compile(pipeline, examples)

        # Evaluate with route-aware metrics
        quality = evaluate(optimized, examples, metric)
        cost = route_cost(route, ...)

        results[route] = (optimized, quality, cost)

    # Return best route based on quality/cost tradeoff
    return select_best_route(results)
```

### Strategy 2: Dynamic Route Switching
Allow optimizer to switch routes during optimization.

**Implementation**:
```python
def optimize_with_dynamic_routing(pipeline, examples, metric):
    for trial in range(num_trials):
        # Run trial
        result = trial_run(pipeline, examples)

        # Check if route migration would help
        suggestion = suggest_route_migration(current_route, metrics)

        if suggestion:
            switch_to_route(suggestion)
            continue_optimization()
```

**RECOMMENDATION**: Start with Strategy 1 (simpler), add Strategy 2 if needed.

---

## Implementation Plan

### Step 1: Core Optimizer Wrapper (2-3 hours)
**File**: `lift_sys/optimization/optimizer.py`

```python
class DSPyOptimizer:
    """Wrapper around DSPy optimizers with lift-sys integration."""

    def __init__(
        self,
        optimizer_type: str = "mipro",  # "mipro" or "copro"
        metric: Callable = None,  # From H10
        **optimizer_kwargs
    ):
        self.optimizer_type = optimizer_type
        self.metric = metric or self._default_metric()
        self.optimizer_kwargs = optimizer_kwargs

    def optimize(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
        route_strategy: ProviderRoute | None = None,
    ) -> OptimizedPipeline:
        """Run optimization and return optimized pipeline."""
        # Initialize DSPy optimizer
        # Run optimization
        # Track in execution history (H11)
        # Return results with metrics

    def _default_metric(self) -> Callable:
        """Default to H10 aggregate_metric."""
        from lift_sys.optimization.metrics import aggregate_metric
        return aggregate_metric
```

### Step 2: Route-Aware Optimization (2-3 hours)
**File**: `lift_sys/optimization/route_optimizer.py`

```python
class RouteAwareOptimizer:
    """Optimizer with route switching support (ADR 001)."""

    def optimize_with_routes(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
        routes: list[ProviderRoute] = None,
    ) -> dict[ProviderRoute, OptimizedPipeline]:
        """Optimize pipeline for each route, return best."""
        # For each route:
        #   - Configure provider adapter
        #   - Run optimization
        #   - Evaluate with route_quality()
        #   - Track cost with route_cost()
        # Return results per route

    def suggest_route_changes(
        self,
        metrics: dict[str, float]
    ) -> dict[str, ProviderRoute]:
        """Suggest route migrations based on metrics."""
        # Use H10 suggest_route_migration()
        # Return recommendations
```

### Step 3: Integration & Testing (2-3 hours)
**File**: `tests/unit/optimization/test_optimizer.py`

- Test MIPROv2 integration
- Test COPRO integration
- Test custom metrics from H10
- Test route-aware optimization
- Test with 20+ examples
- Integration test end-to-end

### Step 4: Documentation (1 hour)
- Update HOLE_INVENTORY.md status
- Add usage examples
- Document route optimization strategies

---

## Expected Outputs

### Implementation Files
1. `lift_sys/optimization/optimizer.py` (~300 lines)
2. `lift_sys/optimization/route_optimizer.py` (~200 lines)
3. `lift_sys/optimization/__init__.py` (updated exports)

### Test Files
1. `tests/unit/optimization/test_optimizer.py` (~400 lines)
2. `tests/integration/test_optimization_e2e.py` (~200 lines)

### Documentation
1. Updated `HOLE_INVENTORY.md` (H8 status → RESOLVED)
2. `CONSTRAINT_PROPAGATION_LOG.md` Event 9
3. `SESSION_STATE.md` update

---

## Risks & Mitigations

**Risk**: DSPy optimizer API changes
**Mitigation**: Pin DSPy version, wrap tightly, add tests

**Risk**: Route optimization slow (2x optimization runs)
**Mitigation**: Start with single route, add multi-route as enhancement

**Risk**: Metrics don't improve pipeline
**Mitigation**: Use H10 validation dataset, tune optimizer hyperparameters

---

## Success Criteria

✅ **Complete when**:
1. MIPROv2 successfully optimizes a pipeline
2. Optimized pipeline shows measurable improvement on H10 metrics
3. Route-aware optimization works for both Best Available and Modal routes
4. All acceptance criteria passing
5. Integration test with 20 examples passing
6. Documentation complete

---

## Next Steps After H8

1. **H17**: OptimizationValidation (validates H8 actually improves pipelines)
2. **H12**: ConfidenceCalibration (uses optimization metrics for calibration)
3. **Phase 3 Gate**: Validate all optimization capability complete

---

**Status**: READY TO START
**Estimated Time**: 6-8 hours total
**Critical Path**: YES (blocks H17, Phase 3 completion)
