# Integration Recommendations: DoWhy Causal Analysis in lift-sys

**Date**: 2025-10-26
**Context**: Specific recommendations for integrating DoWhy into lift-sys reverse mode
**Dependencies**: INTEGRATION_PATTERNS_RESEARCH.md

---

## Executive Summary

This document provides **actionable recommendations** for integrating DoWhy causal analysis into lift-sys, based on patterns research and existing architecture.

**Recommended Approach**: **Lazy + Graceful + Resilient**
1. Lazy evaluation (`@cached_property`) for zero overhead
2. Graceful degradation (fallbacks) for robustness
3. Circuit breaker + timeout for resilience

**Target User Experience**:
```python
# Users opt into causal analysis via parameter
ir = lifter.lift("file.py", include_causal=True)

# Lazy: causal graph only built when accessed
graph = ir.causal_graph  # Triggers computation

# Methods available on causal-enabled IR
impact = ir.causal_impact("function_name")
intervention = ir.causal_intervention({"var": new_value})
```

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [API Design Recommendations](#2-api-design-recommendations)
3. [IR Extension Strategy](#3-ir-extension-strategy)
4. [Subprocess Integration Pattern](#4-subprocess-integration-pattern)
5. [Configuration Management](#5-configuration-management)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────┐
│ User API                                        │
│ ─────────────────────────────────────────────── │
│ lifter.lift("file.py", include_causal=True)     │
└─────────────────┬───────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────┐
│ SpecificationLifter                             │
│ ─────────────────────────────────────────────── │
│ 1. Extract AST (existing)                       │
│ 2. Build IR (existing)                          │
│ 3. If include_causal: attach CausalAnalyzer     │
└─────────────────┬───────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────┐
│ IntermediateRepresentation (IR)                 │
│ ─────────────────────────────────────────────── │
│ Properties (lazy, cached):                      │
│   @cached_property causal_graph                 │
│   @cached_property causal_model                 │
│                                                 │
│ Methods:                                        │
│   causal_impact(target) -> List[str]            │
│   causal_intervention(intervention) -> Result   │
└─────────────────┬───────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────┐
│ CausalAnalyzer (Bridge to DoWhy)                │
│ ─────────────────────────────────────────────── │
│ - Circuit breaker for subprocess calls          │
│ - Timeout management                            │
│ - Error handling + fallbacks                    │
└─────────────────┬───────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────┐
│ DoWhy Subprocess (Python 3.11)                  │
│ ─────────────────────────────────────────────── │
│ scripts/dowhy/fit_scm.py                        │
│ scripts/dowhy/query_scm.py                      │
└─────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Zero Overhead When Disabled**: Users who don't use causal features pay no cost
2. **Graceful Degradation**: Core lift-sys works even if DoWhy unavailable
3. **Lazy Evaluation**: Expensive computations deferred until needed
4. **Fail-Fast**: Timeouts and circuit breakers prevent hanging
5. **Clear Errors**: Users understand why causal analysis failed

---

## 2. API Design Recommendations

### 2.1 Recommended: `include_causal` Parameter

**Pattern**: Optional boolean parameter to enable causal analysis

**Rationale**:
- Simple, discoverable API
- Backward compatible (defaults to False)
- Clear user intent

**Implementation**:
```python
# In SpecificationLifter
class SpecificationLifter:
    def lift(
        self,
        target_module: str,
        include_causal: bool = False
    ) -> IntermediateRepresentation:
        """Lift specification from module.

        Args:
            target_module: Path to Python module
            include_causal: If True, attach causal analysis capabilities

        Returns:
            IR with optional causal features
        """
        # Existing IR extraction
        ir = self._extract_ir(target_module)

        # Conditionally attach causal analyzer
        if include_causal:
            ir._causal_analyzer = CausalAnalyzer(
                ast=ir.metadata.get("ast"),
                config=self.config.causal_config
            )

        return ir
```

**User Experience**:
```python
# Without causal analysis (fast, lightweight)
ir = lifter.lift("file.py")
# ir.causal_graph -> AttributeError (not attached)

# With causal analysis (opt-in)
ir = lifter.lift("file.py", include_causal=True)
# ir.causal_graph -> Lazy computation
```

---

### 2.2 Alternative Considered: Separate Method

**Pattern**: Dedicated method for causal lifting

```python
# Alternative API (NOT recommended)
ir_basic = lifter.lift("file.py")
ir_causal = lifter.lift_with_causal("file.py")
```

**Pros**: Very explicit separation

**Cons**:
- API proliferation (lift, lift_all, lift_with_causal, lift_all_with_causal, ...)
- Harder to discover
- Users may not realize causal features exist

**Verdict**: **Reject** (prefer single `lift()` with `include_causal` parameter)

---

### 2.3 Alternative Considered: Builder Pattern

**Pattern**: Fluent configuration API

```python
# Alternative API (MAYBE for advanced config)
ir = lifter
    .with_causal(quality="GOOD", timeout=30)
    .lift("file.py")
```

**Pros**: Very flexible for complex configuration

**Cons**:
- More complex API
- Overkill for single boolean flag

**Verdict**: **Consider for Phase 2** (advanced causal configuration)

**Recommendation**: Start with simple `include_causal=True`, add builder later if needed

---

## 3. IR Extension Strategy

### 3.1 Recommended: Attach `_causal_analyzer` to Existing IR

**Pattern**: Add causal capabilities to existing IR class without subclassing

**Rationale**:
- No type splitting (single IR class)
- Backward compatible (existing code unaffected)
- Lazy properties naturally indicate availability

**Implementation**:
```python
from functools import cached_property
from typing import Optional

class IntermediateRepresentation:
    """Existing IR class (in lift_sys/ir/models.py)."""

    def __init__(self, intent, signature, effects, assertions, metadata):
        self.intent = intent
        self.signature = signature
        self.effects = effects
        self.assertions = assertions
        self.metadata = metadata

        # Causal analysis (optional, attached by lifter)
        self._causal_analyzer: Optional[CausalAnalyzer] = None

    # --- Causal Properties (Lazy) ---

    @cached_property
    def causal_graph(self) -> Optional[CausalGraph]:
        """Get causal graph (lazy, cached).

        Returns:
            CausalGraph if causal analysis enabled, else None

        Raises:
            RuntimeError: If causal analysis failed
        """
        if self._causal_analyzer is None:
            return None  # Feature not enabled

        return self._causal_analyzer.build_graph()

    @cached_property
    def causal_model(self) -> Optional[StructuralCausalModel]:
        """Get fitted SCM (lazy, cached).

        Returns:
            SCM if causal analysis enabled and graph available, else None
        """
        if self.causal_graph is None:
            return None

        return self._causal_analyzer.fit_model(self.causal_graph)

    # --- Causal Methods (Convenience) ---

    def causal_impact(self, target: str) -> Optional[List[str]]:
        """Get downstream effects of target node.

        Args:
            target: Function/variable name

        Returns:
            List of affected nodes, or None if causal analysis unavailable
        """
        if self.causal_graph is None:
            return None

        return self.causal_graph.downstream_effects(target)

    def causal_intervention(
        self,
        intervention: Dict[str, Any]
    ) -> Optional[InterventionResult]:
        """Estimate impact of intervention.

        Args:
            intervention: {node: new_value} mapping

        Returns:
            InterventionResult with impact estimates, or None if unavailable
        """
        if self.causal_model is None:
            return None

        return self._causal_analyzer.intervene(
            self.causal_model,
            intervention
        )
```

**Benefits**:
- Single IR type (no CausalIR vs BaseIR confusion)
- Type checkers happy (Optional[X] for causal properties)
- Lazy evaluation (properties only computed when accessed)
- Graceful degradation (returns None if unavailable)

**Drawbacks**:
- IR class larger (but logically cohesive)
- Private `_causal_analyzer` attribute (implementation detail)

**Verdict**: **Recommended** (best balance of simplicity and functionality)

---

### 3.2 Alternative Considered: Subclassing

**Pattern**: Create `CausalIR(IntermediateRepresentation)`

```python
class CausalIR(IntermediateRepresentation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._causal_analyzer = CausalAnalyzer(...)

    @cached_property
    def causal_graph(self):
        return self._causal_analyzer.build_graph()
```

**Pros**: Clear separation of concerns

**Cons**:
- Type splitting (`CausalIR` vs `IntermediateRepresentation`)
- Functions must accept `Union[IR, CausalIR]` or `IR` (lose causal methods)
- Harder to add more optional features (SecurityIR? PerformanceIR?)

**Verdict**: **Reject** (composition over inheritance)

---

## 4. Subprocess Integration Pattern

### 4.1 Recommended: Circuit Breaker + Timeout Wrapper

**Pattern**: Wrap DoWhy subprocess calls with resilience patterns

**Implementation**:
```python
# In lift_sys/causal/dowhy_client.py

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class DoWhyCircuitBreaker:
    """Circuit breaker for DoWhy subprocess calls."""

    def __init__(
        self,
        failure_threshold: int = 3,
        timeout: float = 60.0,
        call_timeout: float = 30.0
    ):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # Cooldown period
        self.call_timeout = call_timeout  # Per-call timeout
        self.last_failure_time: Optional[float] = None

    def call(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call DoWhy subprocess with circuit breaker protection.

        Args:
            input_data: JSON-serializable data for DoWhy

        Returns:
            DoWhy output dict, or None if failed/unavailable
        """
        import time

        # Check circuit state
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - (self.last_failure_time or 0)
            if elapsed > self.timeout:
                # Try recovery
                self.state = CircuitState.HALF_OPEN
                logging.info("Circuit breaker HALF_OPEN, attempting recovery")
            else:
                # Still in cooldown
                logging.warning(
                    f"Circuit breaker OPEN, cooldown remaining: "
                    f"{self.timeout - elapsed:.1f}s"
                )
                return None

        # Attempt call
        try:
            result = self._call_dowhy_subprocess(input_data)

            # Success: reset circuit
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logging.info("Circuit breaker CLOSED, service recovered")

            return result

        except Exception as e:
            # Failure: increment counter
            self.failure_count += 1
            self.last_failure_time = time.time()

            logging.error(
                f"DoWhy subprocess failed ({self.failure_count}/"
                f"{self.failure_threshold}): {e}"
            )

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logging.error(
                    f"Circuit breaker OPEN after {self.failure_count} failures"
                )

            return None

    def _call_dowhy_subprocess(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Raw subprocess call (raises on error)."""

        # Locate DoWhy venv
        venv_python = Path(".venv-dowhy/bin/python")
        if not venv_python.exists():
            raise FileNotFoundError(
                "DoWhy venv not found (.venv-dowhy/bin/python). "
                "Run: uv venv --python 3.11 .venv-dowhy && "
                "source .venv-dowhy/bin/activate && "
                "uv pip install dowhy pandas numpy"
            )

        # Determine script based on operation
        script_path = Path("scripts/dowhy/fit_scm.py")

        # Call subprocess with timeout
        result = subprocess.run(
            [str(venv_python), str(script_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=self.call_timeout
        )

        # Check exit code
        if result.returncode != 0:
            raise RuntimeError(
                f"DoWhy subprocess failed (exit {result.returncode}): "
                f"{result.stderr}"
            )

        # Parse output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"DoWhy returned invalid JSON: {result.stdout[:200]}"
            ) from e

        # Check status field
        if output.get("status") == "error":
            raise RuntimeError(
                f"DoWhy error: {output.get('error', 'Unknown error')}"
            )

        return output


# Global circuit breaker instance
_dowhy_breaker = DoWhyCircuitBreaker(
    failure_threshold=3,
    timeout=60.0,  # 1 minute cooldown
    call_timeout=30.0  # 30s per call
)


def call_dowhy(input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Public API: Call DoWhy with circuit breaker protection.

    Args:
        input_data: JSON-serializable input for DoWhy

    Returns:
        DoWhy output dict, or None if unavailable/failed
    """
    return _dowhy_breaker.call(input_data)
```

**Benefits**:
- Prevents repeated failures from overwhelming system
- Fast failure when DoWhy degraded (no waiting)
- Automatic recovery after cooldown
- Clear logging for debugging

**User Experience**:
```python
# First 3 calls fail (DoWhy crashes)
result = call_dowhy({...})  # None, logs error
result = call_dowhy({...})  # None, logs error
result = call_dowhy({...})  # None, logs error + "Circuit breaker OPEN"

# Next calls fail fast (no subprocess spawned)
result = call_dowhy({...})  # None, logs "Circuit breaker OPEN"

# After 60s cooldown, circuit breaker tries recovery
result = call_dowhy({...})  # Attempts call (HALF_OPEN)
# If succeeds: CLOSED (normal operation)
# If fails: OPEN again (another 60s cooldown)
```

---

### 4.2 Error Handling Hierarchy

**Recommendation**: Return `None` for expected failures, raise exceptions for programmer errors

```python
def build_causal_graph(ast) -> Optional[CausalGraph]:
    """Build causal graph from AST.

    Returns:
        CausalGraph if successful, None if DoWhy unavailable/failed

    Raises:
        ValueError: If AST is malformed (programmer error)
    """
    # Validate input (programmer error)
    if ast is None:
        raise ValueError("AST cannot be None")

    # Call DoWhy (expected to possibly fail)
    result = call_dowhy({"graph": ast_to_graph(ast)})

    if result is None:
        # DoWhy unavailable/failed: graceful degradation
        logging.warning("Causal graph unavailable (DoWhy failed)")
        return None

    return CausalGraph.from_dict(result["graph"])
```

**Error Categories**:
1. **Programmer Errors** (raise exception): Invalid inputs, logic bugs
2. **Expected Failures** (return None + log): DoWhy unavailable, timeout, subprocess crash
3. **Data Issues** (return partial result + warning): Noisy data, low R², insufficient samples

---

## 5. Configuration Management

### 5.1 Recommended: Configuration Dataclass

**Pattern**: Use dataclass for causal analysis configuration

**Implementation**:
```python
# In lift_sys/causal/config.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class CausalConfig:
    """Configuration for causal analysis."""

    # Quality vs speed tradeoff
    quality: Literal["GOOD", "BETTER", "BEST"] = "GOOD"

    # Timeouts
    call_timeout: float = 30.0  # Per DoWhy call (seconds)
    total_timeout: float = 300.0  # Total causal analysis (seconds)

    # Circuit breaker
    failure_threshold: int = 3  # Failures before circuit opens
    cooldown_period: float = 60.0  # Cooldown after circuit opens (seconds)

    # Validation
    validate_r2: bool = True  # Enforce R² threshold
    r2_threshold: float = 0.7  # Minimum R² for SCM

    # Caching (future)
    cache_graphs: bool = False
    cache_ttl: float = 3600.0  # 1 hour

    @classmethod
    def default(cls) -> "CausalConfig":
        """Get default configuration."""
        return cls()

    @classmethod
    def fast(cls) -> "CausalConfig":
        """Fast configuration (low quality, short timeouts)."""
        return cls(
            quality="GOOD",
            call_timeout=10.0,
            total_timeout=60.0,
            validate_r2=False
        )

    @classmethod
    def accurate(cls) -> "CausalConfig":
        """Accurate configuration (high quality, long timeouts)."""
        return cls(
            quality="BEST",
            call_timeout=60.0,
            total_timeout=600.0,
            validate_r2=True,
            r2_threshold=0.8
        )
```

**Usage**:
```python
# Default configuration
ir = lifter.lift("file.py", include_causal=True)

# Custom configuration
ir = lifter.lift(
    "file.py",
    include_causal=True,
    causal_config=CausalConfig.accurate()
)

# Very custom configuration
ir = lifter.lift(
    "file.py",
    include_causal=True,
    causal_config=CausalConfig(
        quality="BETTER",
        call_timeout=45.0,
        r2_threshold=0.75
    )
)
```

**Benefits**:
- Type-safe configuration (dataclass validation)
- Discoverable options (IDE autocomplete)
- Presets for common use cases (default, fast, accurate)
- Extensible (add fields without breaking API)

---

### 5.2 Integration with LifterConfig

**Recommendation**: Add `causal_config` to existing `LifterConfig`

```python
# In lift_sys/reverse_mode/lifter.py

@dataclass
class LifterConfig:
    """Existing lifter configuration."""

    # Existing fields
    codeql_queries: Iterable[str] = field(default_factory=lambda: ["security/default"])
    daikon_entrypoint: str = "main"
    run_codeql: bool = True
    run_daikon: bool = True
    # ... other fields ...

    # NEW: Causal analysis configuration
    causal_config: CausalConfig = field(default_factory=CausalConfig.default)
```

**Usage**:
```python
# Lifter with custom causal config
config = LifterConfig(
    run_codeql=True,
    causal_config=CausalConfig.accurate()
)
lifter = SpecificationLifter(config)

# Per-file override
ir = lifter.lift(
    "file.py",
    include_causal=True,
    causal_config=CausalConfig.fast()  # Override lifter's config
)
```

---

## 6. Implementation Roadmap

### 6.1 Phase 1: Core Integration (Week 1-2)

**Goal**: Basic causal analysis available via `ir.causal_graph`

**Tasks**:
1. Add `_causal_analyzer` field to `IntermediateRepresentation`
2. Implement `@cached_property causal_graph`
3. Create `DoWhyCircuitBreaker` and `call_dowhy()` wrapper
4. Add `include_causal` parameter to `SpecificationLifter.lift()`
5. Write unit tests for circuit breaker, timeout handling

**Deliverables**:
- `lift_sys/causal/dowhy_client.py` (circuit breaker + subprocess wrapper)
- `lift_sys/ir/models.py` (updated with causal properties)
- `tests/causal/test_dowhy_client.py` (circuit breaker tests)
- `tests/integration/test_causal_integration.py` (end-to-end)

**Exit Criteria**:
- Users can call `lifter.lift("file.py", include_causal=True)`
- `ir.causal_graph` returns `CausalGraph` or `None` (if unavailable)
- Circuit breaker prevents repeated failures
- Tests pass: 95%+ coverage on new code

---

### 6.2 Phase 2: Convenience Methods (Week 3)

**Goal**: User-friendly methods for common causal queries

**Tasks**:
1. Implement `ir.causal_impact(target)`
2. Implement `ir.causal_intervention(intervention)`
3. Implement `@cached_property causal_model` (fitted SCM)
4. Add `CausalConfig` dataclass with presets
5. Write integration tests with real codebases

**Deliverables**:
- `lift_sys/ir/models.py` (causal methods)
- `lift_sys/causal/config.py` (configuration)
- `tests/integration/test_causal_queries.py` (query tests)
- `docs/user_guide/CAUSAL_ANALYSIS.md` (user documentation)

**Exit Criteria**:
- Users can query `ir.causal_impact("function_name")`
- Users can run `ir.causal_intervention({"var": value})`
- Configuration presets work (default, fast, accurate)
- Documentation complete with examples

---

### 6.3 Phase 3: Error Handling & Polish (Week 4)

**Goal**: Production-ready error handling and user experience

**Tasks**:
1. Add detailed error messages (why causal analysis failed)
2. Implement fallback to cached results (if available)
3. Add telemetry (how often causal analysis succeeds/fails)
4. Performance benchmarks (overhead measurement)
5. User acceptance testing with sample codebases

**Deliverables**:
- `lift_sys/causal/errors.py` (custom exceptions)
- `lift_sys/causal/cache.py` (optional caching layer)
- `docs/benchmarks/CAUSAL_ANALYSIS_PERFORMANCE.md` (benchmarks)
- `docs/troubleshooting/CAUSAL_ANALYSIS.md` (debugging guide)

**Exit Criteria**:
- Clear error messages for all failure modes
- Performance overhead <5% when `include_causal=False`
- Benchmarks show acceptable latency (<30s for 100-file codebase)
- No known bugs or edge cases

---

### 6.4 Phase 4: Advanced Features (Future)

**Goal**: Advanced causal analysis capabilities

**Tasks** (Future Work):
- Counterfactual queries ("What if I hadn't added this feature?")
- Causal test generation (generate tests based on causal graph)
- Interactive causal graph visualization
- Caching layer for frequently-analyzed codebases
- Support for alternative causal backends (CausalNex, gCastle)

**Not Prioritized**: Wait for user feedback before implementing

---

## 7. Code Examples

### 7.1 Full Integration Example

**User Code**:
```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
from lift_sys.causal import CausalConfig

# Configure lifter with causal analysis
config = LifterConfig(
    run_codeql=True,
    run_daikon=False,
    causal_config=CausalConfig.default()
)

# Load repository
lifter = SpecificationLifter(config)
lifter.load_repository("https://github.com/user/repo")

# Lift with causal analysis
ir = lifter.lift("src/app.py", include_causal=True)

# Access causal graph (lazy, cached)
if ir.causal_graph is not None:
    print(f"Nodes: {ir.causal_graph.nodes}")
    print(f"Edges: {ir.causal_graph.edges}")

    # Query downstream effects
    affected = ir.causal_impact("validate_input")
    print(f"Changing validate_input affects: {affected}")

    # Run intervention
    result = ir.causal_intervention({"validate_input": True})
    if result is not None:
        print(f"Intervention impact: {result.summary}")
else:
    print("Causal analysis unavailable (DoWhy failed or not installed)")
```

**Expected Output** (Success):
```
Nodes: ['validate_input', 'process_data', 'generate_output', 'save_results']
Edges: [('validate_input', 'process_data'), ('process_data', 'generate_output'), ...]
Changing validate_input affects: ['process_data', 'generate_output', 'save_results']
Intervention impact: Setting validate_input=True increases generate_output by 23% (95% CI: [18%, 28%])
```

**Expected Output** (Failure):
```
WARNING: DoWhy subprocess failed (exit 1): ModuleNotFoundError: No module named 'dowhy'
WARNING: Causal graph unavailable (DoWhy failed)
Causal analysis unavailable (DoWhy failed or not installed)
```

---

### 7.2 Batch Analysis Example

**User Code**:
```python
# Analyze entire repository with causal analysis
irs = lifter.lift_all(max_files=100)

# Count how many have causal graphs
causal_available = sum(1 for ir in irs if ir.causal_graph is not None)
print(f"Causal graphs available: {causal_available}/{len(irs)}")

# Find most impactful functions
for ir in irs:
    if ir.causal_graph is not None:
        # Functions with most downstream effects
        impacts = {
            node: len(ir.causal_impact(node) or [])
            for node in ir.causal_graph.nodes
        }
        top_impact = max(impacts.items(), key=lambda x: x[1])
        print(f"{ir.metadata.source_path}: Most impactful function: {top_impact}")
```

---

## 8. Success Metrics

### 8.1 Technical Metrics

**Performance**:
- Overhead when `include_causal=False`: <1% (target: 0%)
- Causal graph construction: <5s per file (target: <3s)
- SCM fitting: <10s per file (target: <5s)
- Total analysis (100 files): <300s (target: <180s)

**Reliability**:
- Success rate: >90% (when DoWhy installed)
- Circuit breaker activation: <10% of runs
- Timeout rate: <5% of calls

**Accuracy**:
- Causal graph precision: >85% (verified against manual annotation)
- Causal graph recall: >75% (capture most causal relationships)
- SCM R²: >0.7 (when execution traces available)

### 8.2 User Experience Metrics

**Usability**:
- Time to first causal query: <5 minutes (including setup)
- Documentation completeness: 100% (all APIs documented)
- Error message clarity: >4/5 user rating

**Adoption**:
- Percentage of users enabling `include_causal`: Track via telemetry
- Feature usage: % of IRs with `.causal_graph` accessed
- Feedback: Net Promoter Score (NPS) for causal features

---

## 9. Risk Mitigation

### 9.1 Risk: DoWhy Subprocess Unavailable

**Likelihood**: HIGH (users may not install DoWhy, Python 3.11 missing)

**Impact**: MEDIUM (causal features unavailable, but core lift-sys works)

**Mitigation**:
1. Graceful degradation (return `None`, log warning)
2. Clear error message with setup instructions
3. Automated setup script (`scripts/setup/install_dowhy.sh`)
4. Documentation: troubleshooting guide

**Acceptance**: This is expected behavior (optional feature)

---

### 9.2 Risk: Subprocess Performance Overhead

**Likelihood**: MEDIUM (subprocess startup ~100ms, JSON serialization overhead)

**Impact**: MEDIUM (slow causal analysis, users frustrated)

**Mitigation**:
1. Lazy evaluation (only compute when accessed)
2. Caching (cache graphs keyed by AST hash)
3. Future: persistent worker process (avoid startup overhead)
4. Configuration presets (fast mode for quick analysis)

**Acceptance**: Trade-off for Python 3.11 compatibility

---

### 9.3 Risk: Circuit Breaker False Positives

**Likelihood**: LOW (circuit breaker well-tuned)

**Impact**: LOW (causal analysis unnecessarily disabled)

**Mitigation**:
1. Conservative failure threshold (3 failures before opening)
2. Reasonable cooldown period (60s)
3. Configurable parameters (users can adjust)
4. Telemetry to detect false positives

**Acceptance**: Fail-safe is better than hanging

---

## 10. Conclusion

**Recommended Integration Strategy**:

1. **Extend existing IR** with `_causal_analyzer` (composition, not inheritance)
2. **Lazy properties** (`@cached_property`) for zero overhead
3. **Circuit breaker + timeout** for robust subprocess integration
4. **Graceful degradation** (return `None` when unavailable)
5. **Simple API** (`include_causal=True`) with optional advanced config

**Implementation Timeline**: 3-4 weeks

**Success Criteria**:
- Users can opt into causal analysis with single parameter
- Zero overhead when disabled
- Robust error handling (no crashes from DoWhy failures)
- Clear documentation and examples

**Next Steps**: See ERROR_HANDLING_STRATEGY.md for detailed error handling approach

---

## References

- [INTEGRATION_PATTERNS_RESEARCH.md](./INTEGRATION_PATTERNS_RESEARCH.md) - Pattern analysis
- [DoWhy Integration Spec](./DOWHY_INTEGRATION_SPEC.md) - High-level design
- [Existing Lifter Code](../../lift_sys/reverse_mode/lifter.py) - Current implementation
- [Existing IR Code](../../lift_sys/ir/models.py) - IR data structures

**Last Updated**: 2025-10-26
