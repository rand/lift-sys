# Integration Patterns Research: Adding Analysis Capabilities to Existing Systems

**Date**: 2025-10-26
**Context**: DoWhy causal analysis integration into lift-sys reverse mode
**Research Focus**: Best practices for extending systems with optional analysis features

---

## Executive Summary

This document surveys integration patterns from ML model deployment, static analysis tools, profilers, and distributed systems to inform how lift-sys should integrate DoWhy causal analysis capabilities.

**Key Findings**:
1. **Decorator Pattern** - Most flexible for adding optional features
2. **Lazy Evaluation** - Critical for performance with expensive analysis
3. **Graceful Degradation** - Essential for subprocess/external tool integration
4. **Builder Pattern** - Clean API for complex configuration
5. **Circuit Breaker** - Prevents cascading failures from analysis components

**Recommendation**: Combine **decorator + lazy evaluation + circuit breaker** for robust, performant integration.

---

## Table of Contents

1. [ML Model Integration Patterns](#1-ml-model-integration-patterns)
2. [Static Analysis Tool Patterns](#2-static-analysis-tool-patterns)
3. [Profiler Integration Patterns](#3-profiler-integration-patterns)
4. [Distributed Systems Patterns](#4-distributed-systems-patterns)
5. [Synthesis: Recommended Patterns](#5-synthesis-recommended-patterns)

---

## 1. ML Model Integration Patterns

### 1.1 Lazy Evaluation with `@cached_property`

**Source**: MLX Framework, Python functools

**Pattern**: Defer expensive computation until first access, cache result

**Example**:
```python
from functools import cached_property

class IntermediateRepresentation:
    def __init__(self, ast, code):
        self.ast = ast
        self.code = code
        # DON'T compute causal analysis here!

    @cached_property
    def causal_graph(self):
        """Lazy: only computed when accessed."""
        return CausalGraphBuilder().build(self.ast)

    @cached_property
    def causal_model(self):
        """Lazy: depends on causal_graph."""
        return SCMFitter().fit(self.causal_graph)
```

**Benefits**:
- Zero overhead when feature not used
- Automatic memoization (computed once)
- Clear dependency chain (causal_model requires causal_graph)

**Applicability to lift-sys**: **HIGH**
- Perfect for `ir.causal_graph`, `ir.causal_model`
- Users only pay cost when they use causal features
- Fits existing IR immutability model (properties, not methods)

**References**:
- [MLX Lazy Evaluation Docs](https://ml-explore.github.io/mlx/build/html/usage/lazy_evaluation.html)
- [Python @cached_property](https://docs.python.org/3/library/functools.html#functools.cached_property)

---

### 1.2 Decorator Pattern for Feature Flags

**Source**: ML model deployment, feature toggles

**Pattern**: Wrap objects with optional capabilities without modifying core

**Example**:
```python
class BaseIR:
    """Core IR without causal analysis."""
    def __init__(self, ast, code):
        self.ast = ast
        self.code = code

class CausalIR(BaseIR):
    """IR decorated with causal capabilities."""
    @cached_property
    def causal_graph(self):
        return CausalGraphBuilder().build(self.ast)

    def causal_impact(self, target):
        return self.causal_graph.downstream_effects(target)

# Factory method decides which to return
def create_ir(ast, code, include_causal=False):
    if include_causal:
        return CausalIR(ast, code)
    else:
        return BaseIR(ast, code)
```

**Benefits**:
- Clear separation of concerns
- No performance penalty for non-causal users
- Easier testing (test BaseIR independently)

**Drawbacks**:
- Requires two classes (more maintenance)
- Type checkers may struggle (CausalIR vs BaseIR)

**Applicability to lift-sys**: **MEDIUM**
- Good if causal features are extensive
- May be overkill for lift-sys (prefer single class + lazy properties)

---

### 1.3 Configuration-Based Caching

**Source**: ML model deployments, LLM apps

**Pattern**: Cache expensive computations with configurable invalidation

**Example**:
```python
from functools import lru_cache
import hashlib

class IRWithCaching:
    def __init__(self, ast, code):
        self.ast = ast
        self.code = code
        self._ast_hash = hashlib.sha256(str(ast).encode()).hexdigest()

    @lru_cache(maxsize=128)
    def _compute_causal_graph(self, ast_hash):
        """Cache keyed by AST hash."""
        return CausalGraphBuilder().build(self.ast)

    @property
    def causal_graph(self):
        return self._compute_causal_graph(self._ast_hash)
```

**Benefits**:
- Cross-instance caching (multiple IRs with same AST)
- Configurable cache size (memory vs speed tradeoff)
- Automatic LRU eviction

**Drawbacks**:
- Cache key design critical (hash collisions?)
- Memory leaks if cache grows unbounded

**Applicability to lift-sys**: **LOW**
- lift-sys IRs are unique per file (unlikely to benefit from cross-instance caching)
- `@cached_property` sufficient for single-instance caching

**References**:
- [Python LRU Cache](https://realpython.com/lru-cache-python/)
- [Caching for ML Models](https://www.tekhnoal.com/caching-for-ml-models.html)

---

## 2. Static Analysis Tool Patterns

### 2.1 AST Analyzer Integration

**Source**: Static analysis tools (Pylint, mypy, CodeQL)

**Pattern**: Extend AST visitors with optional analysis passes

**Example**:
```python
class BaseASTAnalyzer(ast.NodeVisitor):
    """Core structural analysis."""
    def visit_FunctionDef(self, node):
        # Extract signature, docstring, etc.
        pass

class CausalASTAnalyzer(BaseASTAnalyzer):
    """Adds causal edge detection."""
    def visit_Assign(self, node):
        # Detect causal edges (X = f(Y))
        super().visit_Assign(node)  # Run base analysis first
        self._add_causal_edge(node.target, node.value)

# Configurable pipeline
def analyze(ast_tree, include_causal=False):
    if include_causal:
        analyzer = CausalASTAnalyzer()
    else:
        analyzer = BaseASTAnalyzer()
    analyzer.visit(ast_tree)
    return analyzer.results
```

**Benefits**:
- Clean separation: base vs extended analysis
- Easy to add more optional analyzers (security, performance, etc.)
- Standard AST visitor pattern (familiar to developers)

**Applicability to lift-sys**: **MEDIUM**
- lift-sys already has AST analysis in reverse mode
- Could extend with CausalASTAnalyzer pass
- Prefer composition over inheritance (pass results between analyzers)

**References**:
- [Static Analysis using ASTs](https://medium.com/hootsuite-engineering/static-analysis-using-asts-ebcd170c955e)
- [Python AST Visitors](https://docs.python.org/3/library/ast.html#ast.NodeVisitor)

---

### 2.2 Plugin Architecture with Registry

**Source**: Static analysis frameworks, extensible compilers

**Pattern**: Register optional analyzers dynamically

**Example**:
```python
class AnalyzerRegistry:
    _analyzers = {}

    @classmethod
    def register(cls, name):
        def decorator(analyzer_class):
            cls._analyzers[name] = analyzer_class
            return analyzer_class
        return decorator

    @classmethod
    def get_analyzer(cls, name):
        return cls._analyzers.get(name)

# Register analyzers
@AnalyzerRegistry.register("causal")
class CausalAnalyzer:
    def analyze(self, ir):
        return {"causal_graph": ...}

@AnalyzerRegistry.register("security")
class SecurityAnalyzer:
    def analyze(self, ir):
        return {"vulnerabilities": ...}

# Use dynamically
def analyze_with_plugins(ir, plugins=None):
    results = {}
    for plugin_name in (plugins or []):
        analyzer = AnalyzerRegistry.get_analyzer(plugin_name)()
        results[plugin_name] = analyzer.analyze(ir)
    return results
```

**Benefits**:
- Extremely flexible (add analyzers without touching core)
- Users can provide custom analyzers
- Clear extension point

**Drawbacks**:
- More complex (registry, discovery, loading)
- Overkill for single optional feature (DoWhy)

**Applicability to lift-sys**: **LOW**
- Future-proof for multiple analysis backends
- Current need (DoWhy) doesn't justify complexity
- Revisit if adding 3+ optional analyzers

---

### 2.3 Progressive Enhancement with Fallbacks

**Source**: Web development, graceful degradation systems

**Pattern**: Try advanced feature, fall back to basic if unavailable

**Example**:
```python
def analyze_code(source_code, include_causal=False):
    """Analyze with progressive enhancement."""
    # Base analysis (always works)
    ir = extract_ir(source_code)

    # Try causal analysis if requested
    if include_causal:
        try:
            causal_graph = CausalGraphBuilder().build(ir.ast)
            ir.metadata["causal_graph"] = causal_graph
        except (ImportError, ToolNotFoundError) as e:
            # Fallback: add placeholder + warning
            ir.metadata["causal_graph"] = None
            ir.warnings.append(f"Causal analysis unavailable: {e}")

    return ir
```

**Benefits**:
- Robust: core functionality never fails due to optional feature
- User-friendly: clear warnings when features unavailable
- Works in degraded environments (DoWhy not installed)

**Applicability to lift-sys**: **HIGH**
- Essential for subprocess integration (DoWhy in Python 3.11)
- Users shouldn't fail if .venv-dowhy missing
- Aligns with graceful degradation best practices

**References**:
- [Graceful Degradation Guide](https://blog.logrocket.com/guide-graceful-degradation-web-development/)
- [New Relic: Design for Graceful Degradation](https://newrelic.com/blog/best-practices/design-software-for-graceful-degradation)

---

## 3. Profiler Integration Patterns

### 3.1 Context Manager for Optional Profiling

**Source**: cProfile, line_profiler, memory_profiler

**Pattern**: Use context managers to opt into expensive analysis

**Example**:
```python
class ProfilingContext:
    """Context manager for optional profiling."""
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.profiler = None

    def __enter__(self):
        if self.enabled:
            import cProfile
            self.profiler = cProfile.Profile()
            self.profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.profiler:
            self.profiler.disable()
            self.profiler.print_stats()

# Usage
def analyze_code(source, profile=False):
    with ProfilingContext(enabled=profile):
        # Analysis happens inside context
        ir = extract_ir(source)
        # Profiling data collected automatically
        return ir
```

**Benefits**:
- Clean syntax (with statement)
- Automatic cleanup (profiler disabled on exit)
- Zero overhead when disabled

**Applicability to lift-sys**: **MEDIUM**
- Good for optional causal tracing during development
- Less relevant for production API (`ir.causal_graph` better)
- Useful for debugging/benchmarking causal analysis itself

---

### 3.2 Decorator-Based Instrumentation

**Source**: profiling-decorator, performance monitoring tools

**Pattern**: Add optional metrics collection via decorators

**Example**:
```python
from functools import wraps
import time

def with_causal_analysis(func):
    """Decorator to add causal analysis to IR extraction."""
    @wraps(func)
    def wrapper(*args, include_causal=False, **kwargs):
        ir = func(*args, **kwargs)

        if include_causal:
            start = time.time()
            ir._causal_graph = CausalGraphBuilder().build(ir.ast)
            ir._causal_time_ms = (time.time() - start) * 1000

        return ir
    return wrapper

@with_causal_analysis
def extract_ir(source_code):
    """Extract IR (optionally with causal analysis)."""
    ast_tree = ast.parse(source_code)
    return IR(ast=ast_tree, code=source_code)
```

**Benefits**:
- Non-invasive (decorator wraps existing function)
- Easy to enable/disable (remove decorator)
- Metrics collection built-in (timing, etc.)

**Drawbacks**:
- Mixed responsibility (IR extraction + causal analysis)
- Harder to test causal analysis independently

**Applicability to lift-sys**: **LOW**
- Prefer explicit API (`include_causal` parameter)
- Decorator pattern better for cross-cutting concerns (logging, auth)
- Causal analysis is domain-specific, not cross-cutting

---

## 4. Distributed Systems Patterns

### 4.1 Circuit Breaker Pattern

**Source**: Resilient API design, microservices

**Pattern**: Prevent cascading failures by "opening circuit" after repeated failures

**Example**:
```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=3, timeout=60):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            # Check if timeout expired (try recovery)
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise RuntimeError("Circuit breaker OPEN")

        try:
            result = func(*args, **kwargs)
            # Success: reset failure count
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise

# Usage
causal_breaker = CircuitBreaker(failure_threshold=3, timeout=60)

def build_causal_graph(ast):
    return causal_breaker.call(CausalGraphBuilder().build, ast)
```

**Benefits**:
- Prevents repeated failures from overwhelming system
- Automatic recovery after timeout
- Fail-fast when external service degraded

**Applicability to lift-sys**: **HIGH**
- Critical for subprocess integration (DoWhy might fail)
- Prevents hanging on repeated DoWhy crashes
- Users get fast error instead of repeated timeouts

**References**:
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [API Resilience Patterns](https://api7.ai/blog/10-common-api-resilience-design-patterns)

---

### 4.2 Fallback Pattern with Caching

**Source**: API gateways, distributed caches

**Pattern**: Serve cached/default response when primary service fails

**Example**:
```python
class CausalAnalysisWithFallback:
    def __init__(self):
        self.cache = {}  # {ast_hash: causal_graph}

    def get_causal_graph(self, ast):
        ast_hash = hash(str(ast))

        try:
            # Try fresh analysis
            graph = CausalGraphBuilder().build(ast)
            self.cache[ast_hash] = graph  # Update cache
            return graph
        except Exception as e:
            # Fallback: return cached version (if available)
            if ast_hash in self.cache:
                logging.warning(f"Using cached causal graph due to: {e}")
                return self.cache[ast_hash]
            else:
                # No cache: return minimal graph
                logging.error(f"Causal analysis failed, no cache: {e}")
                return EmptyCausalGraph()
```

**Benefits**:
- Resilient to transient failures
- Better UX (stale data > no data)
- Useful for expensive operations (causal analysis)

**Drawbacks**:
- Stale data risk (cache invalidation hard)
- Memory overhead (cache storage)

**Applicability to lift-sys**: **MEDIUM**
- Useful if causal analysis flaky (subprocess failures)
- AST changes frequently (code edits) → cache often invalid
- Better for production systems with stable code

---

### 4.3 Timeout with Graceful Failure

**Source**: Subprocess management, external API calls

**Pattern**: Set timeout for external operations, handle TimeoutExpired cleanly

**Example**:
```python
import subprocess
import json

def call_dowhy_subprocess(graph_data, timeout=30):
    """Call DoWhy subprocess with timeout and error handling."""
    try:
        result = subprocess.run(
            [".venv-dowhy/bin/python", "scripts/dowhy/fit_scm.py"],
            input=json.dumps(graph_data),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"DoWhy failed: {result.stderr}")

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        # Graceful failure: return None + log warning
        logging.warning(f"DoWhy subprocess timed out after {timeout}s")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"DoWhy returned invalid JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected DoWhy error: {e}")
        return None
```

**Benefits**:
- Prevents indefinite hangs
- Clear error handling (timeout vs failure vs success)
- Users get fast feedback ("this is taking too long")

**Applicability to lift-sys**: **CRITICAL**
- DoWhy runs in subprocess (must have timeout)
- Complex graphs may take minutes (need configurable timeout)
- Users shouldn't wait indefinitely for causal analysis

**References**:
- [Python Subprocess Timeout](https://stackoverflow.com/questions/1191374/using-module-subprocess-with-timeout)
- [Python Timeout Best Practices](https://coderivers.org/blog/python-timeout/)

---

## 5. Synthesis: Recommended Patterns

Based on the research, here are the patterns **most applicable to lift-sys DoWhy integration**:

### 5.1 Primary Patterns (MUST USE)

#### Pattern 1: Lazy Evaluation with `@cached_property`
**Use for**: `ir.causal_graph`, `ir.causal_model` properties

**Rationale**:
- Zero overhead when not used
- Automatic caching (computed once)
- Fits Python idioms

**Implementation**:
```python
from functools import cached_property

class IntermediateRepresentation:
    @cached_property
    def causal_graph(self):
        """Lazy: only built when accessed."""
        if not self._causal_available():
            raise RuntimeError("Causal analysis not available")
        return self._build_causal_graph()

    @cached_property
    def causal_model(self):
        """Lazy: depends on causal_graph."""
        return self._fit_causal_model(self.causal_graph)
```

---

#### Pattern 2: Graceful Degradation with Fallbacks
**Use for**: Handling DoWhy subprocess unavailability

**Rationale**:
- Subprocess may fail (DoWhy not installed, Python 3.11 missing, etc.)
- Core lift-sys functionality must not break
- Clear error messages for users

**Implementation**:
```python
def _build_causal_graph(self):
    try:
        return call_dowhy_subprocess(self.ast)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        # DoWhy unavailable: return None + warning
        logging.warning(f"Causal analysis unavailable: {e}")
        return None
```

---

#### Pattern 3: Timeout + Circuit Breaker
**Use for**: DoWhy subprocess calls

**Rationale**:
- Prevent hanging on slow/failing DoWhy processes
- Fail-fast after repeated failures
- Automatic recovery after timeout

**Implementation**:
```python
causal_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout=60  # 1 minute cooldown
)

def call_dowhy_subprocess(graph_data):
    return causal_circuit_breaker.call(
        _raw_dowhy_call,
        graph_data,
        timeout=30  # 30s per call
    )
```

---

### 5.2 Secondary Patterns (CONSIDER)

#### Pattern 4: Builder Pattern for Configuration
**Use for**: Configuring causal analysis options

**Rationale**:
- Many config options (quality, timeout, validation thresholds)
- Builder provides clean API
- Optional parameters without constructor bloat

**Implementation**:
```python
# User API
ir = lifter.lift(
    "file.py",
    causal_config=CausalConfig()
        .with_quality("GOOD")
        .with_timeout(30)
        .with_validation(r2_threshold=0.7)
)
```

---

#### Pattern 5: Plugin Registry (Future-Proofing)
**Use for**: Supporting multiple analysis backends (not just DoWhy)

**Rationale**:
- May want alternative causal libraries (CausalNex, gCastle)
- Plugin pattern enables experimentation
- Users can provide custom analyzers

**Implementation**: Deferred (YAGNI for now)

---

### 5.3 Anti-Patterns (AVOID)

#### Anti-Pattern 1: Eager Computation
**Problem**: Computing causal graph in `__init__` wastes resources

```python
# ❌ BAD: Always computes, even if never used
class IR:
    def __init__(self, ast, include_causal=False):
        if include_causal:
            self.causal_graph = CausalGraphBuilder().build(ast)  # EAGER!
```

**Solution**: Use `@cached_property` (lazy)

---

#### Anti-Pattern 2: Silent Failures
**Problem**: Causal analysis fails silently, user unaware

```python
# ❌ BAD: Swallows exceptions, no warning
def build_causal_graph(ast):
    try:
        return CausalGraphBuilder().build(ast)
    except Exception:
        return None  # User doesn't know it failed!
```

**Solution**: Log warnings, raise clear exceptions

---

#### Anti-Pattern 3: No Timeout on Subprocess
**Problem**: User waits indefinitely for DoWhy

```python
# ❌ BAD: No timeout, hangs forever
result = subprocess.run(
    [".venv-dowhy/bin/python", "..."],
    # Missing timeout parameter!
)
```

**Solution**: Always set timeout, handle TimeoutExpired

---

## 6. Conclusion

The research reveals **five critical patterns** for integrating DoWhy into lift-sys:

1. **Lazy Evaluation** (`@cached_property`) - Zero overhead when unused
2. **Graceful Degradation** (fallbacks, warnings) - Core system resilient
3. **Timeout + Circuit Breaker** - Fast failure, automatic recovery
4. **Builder Pattern** (optional) - Clean configuration API
5. **Plugin Registry** (future) - Multi-backend support

These patterns are battle-tested in:
- ML frameworks (MLX, HuggingFace)
- Static analyzers (Pylint, CodeQL)
- Profilers (cProfile, py-spy)
- Distributed systems (API gateways, microservices)

**Next Steps**: Apply these patterns to lift-sys architecture (see INTEGRATION_RECOMMENDATIONS.md)

---

## References

### Academic & Industry
- [Graceful Degradation Patterns (Springer)](https://link.springer.com/chapter/10.1007/978-3-642-10832-7_3)
- [API Resilience Patterns (API7)](https://api7.ai/blog/10-common-api-resilience-design-patterns)
- [Static Analysis using ASTs (Hootsuite)](https://medium.com/hootsuite-engineering/static-analysis-using-asts-ebcd170c955e)

### Python Documentation
- [functools.cached_property](https://docs.python.org/3/library/functools.html#functools.cached_property)
- [subprocess.run() timeout](https://docs.python.org/3/library/subprocess.html#subprocess.run)
- [Python AST](https://docs.python.org/3/library/ast.html)

### Tools & Frameworks
- [MLX Lazy Evaluation](https://ml-explore.github.io/mlx/build/html/usage/lazy_evaluation.html)
- [DoWhy Documentation](https://www.pywhy.org/dowhy/)
- [Python Profilers](https://docs.python.org/3/library/profile.html)

**Last Updated**: 2025-10-26
