# SpecificationLifter Causal Integration Design

**Date**: 2025-10-26
**Status**: Design Phase
**Purpose**: Integrate Week 4 CausalEnhancer into SpecificationLifter.lift()

---

## Overview

This document outlines the design for integrating CausalEnhancer and EnhancedIR into the existing `SpecificationLifter.lift()` method, enabling causal analysis of lifted code specifications.

**Goal**: Enable `lifter.lift(file, include_causal=True)` to return `EnhancedIR` with causal query capabilities.

---

## Current State Analysis

### SpecificationLifter.lift() (lift_sys/reverse_mode/lifter.py:333)

**Current Signature**:
```python
def lift(self, target_module: str) -> IntermediateRepresentation:
```

**Current Flow**:
```
1. Check repository loaded
2. Run CodeQL analyzer (if enabled)
3. Run Daikon analyzer (if enabled)
4. Run Stack Graphs analyzer (if enabled)
5. Bundle evidence
6. Build IR components (intent, signature, effects, assertions)
7. Return IntermediateRepresentation
```

**Key Components**:
- Uses `self.repo` (GitPython Repo object)
- Runs 3 analyzers (CodeQL, Daikon, Stack Graphs)
- Creates `IntermediateRepresentation` from findings
- No AST currently extracted or stored

### Week 4 CausalEnhancer Requirements

**Input Requirements**:
- `ir`: IntermediateRepresentation (base IR)
- `ast_tree`: ast.Module (Python AST)
- `call_graph`: nx.DiGraph (optional, from stack graphs)
- `traces`: pd.DataFrame (optional, for dynamic mode)
- `mode`: "static" | "dynamic" | "auto"
- `source_code`: dict[str, str] (optional, for static mode)

**Output**:
- Dict with `ir`, `causal_graph`, `scm`, `intervention_engine`, `mode`, `metadata`
- Wrapped in `EnhancedIR` for user-facing API

---

## Integration Design

### API Changes

#### LifterConfig (lift_sys/reverse_mode/lifter.py:85)

**Add Causal Configuration**:
```python
@dataclass
class LifterConfig:
    # ... existing fields ...

    # Causal analysis configuration (Week 4 integration)
    run_causal: bool = False  # Enable causal analysis
    causal_mode: str = "auto"  # "static", "dynamic", or "auto"
    causal_collect_traces: bool = False  # Collect execution traces for dynamic mode
    causal_num_traces: int = 200  # Number of traces to collect
    causal_enable_circuit_breaker: bool = True  # Enable circuit breaker
    causal_circuit_breaker_threshold: int = 3  # Failure threshold
```

**Rationale**: Configuration-based approach allows users to control causal analysis at initialization time.

#### SpecificationLifter.__init__() (lift_sys/reverse_mode/lifter.py:110)

**Add CausalEnhancer**:
```python
from lift_sys.causal import CausalEnhancer

class SpecificationLifter:
    def __init__(self, config: LifterConfig, repo: Repo | None = None) -> None:
        self.config = config
        self.repo = repo
        self.codeql = CodeQLAnalyzer()
        self.daikon = DaikonAnalyzer()
        self.stack_graphs = StackGraphAnalyzer()
        self.progress_log: list[str] = []

        # Week 4: Causal analysis integration
        if self.config.run_causal:
            self.causal_enhancer = CausalEnhancer(
                enable_circuit_breaker=self.config.causal_enable_circuit_breaker,
                circuit_breaker_threshold=self.config.causal_circuit_breaker_threshold,
            )
        else:
            self.causal_enhancer = None
```

#### SpecificationLifter.lift() (lift_sys/reverse_mode/lifter.py:333)

**Modified Signature** (optional parameter approach):
```python
def lift(
    self,
    target_module: str,
    include_causal: bool | None = None,  # Override config.run_causal
) -> IntermediateRepresentation:  # Returns base IR or EnhancedIR
```

**Rationale**:
- `include_causal=None`: Use `self.config.run_causal`
- `include_causal=True`: Force causal analysis (override config)
- `include_causal=False`: Skip causal analysis (override config)
- Return type remains `IntermediateRepresentation` (EnhancedIR is compatible)

**Modified Flow**:
```
1. Check repository loaded
2. Run existing analyzers (CodeQL, Daikon, Stack Graphs)
3. Bundle evidence
4. Build base IR components
5. Create base IntermediateRepresentation

   [NEW] 6. If causal analysis enabled:
   [NEW]    a. Parse target_module to AST
   [NEW]    b. Extract call graph (from Stack Graphs if available)
   [NEW]    c. Collect traces (if dynamic mode)
   [NEW]    d. Call CausalEnhancer.enhance()
   [NEW]    e. Wrap result in EnhancedIR
   [NEW]    f. Return EnhancedIR

   [EXISTING] 7. Return IntermediateRepresentation (if causal disabled)
```

---

## Implementation Plan

### Phase 1: Minimal Integration (Static Mode Only)

**Goal**: Enable `include_causal=True` with static mode (no traces).

**Changes**:
```python
def lift(
    self,
    target_module: str,
    include_causal: bool | None = None,
) -> IntermediateRepresentation:
    """Lift a specification from a single module.

    Args:
        target_module: Path to the Python module to analyze.
        include_causal: Enable causal analysis (overrides config.run_causal).
                       None = use config, True = force enable, False = force disable.

    Returns:
        IntermediateRepresentation (or EnhancedIR if causal enabled).
    """
    if not self.repo:
        raise RepositoryNotLoadedError("Repository must be loaded before analysis")

    self.progress_log = []
    self._record_progress("reverse:start")

    repo_path = str(Path(self.repo.working_tree_dir))

    # [EXISTING CODE: Run analyzers]
    codeql_findings: list[Finding] = []
    if self.config.run_codeql and self.config.codeql_queries:
        self._record_progress("analysis:codeql:start")
        codeql_findings = self.codeql.run(repo_path, self.config.codeql_queries)
        self._record_progress("analysis:codeql:complete")

    daikon_findings: list[Finding] = []
    if self.config.run_daikon:
        self._record_progress("analysis:daikon:start")
        daikon_findings = self.daikon.run(repo_path, self.config.daikon_entrypoint)
        self._record_progress("analysis:daikon:complete")

    stack_findings: list[Finding] = []
    call_graph = None  # Will extract from stack graphs
    if self.config.run_stack_graphs and self.config.stack_index_path:
        self.stack_graphs.set_index_root(self.config.stack_index_path)
        self._record_progress("analysis:stack_graph:start")
        stack_findings = self.stack_graphs.run(target_module)
        self._record_progress("analysis:stack_graph:complete")

        # Extract call graph from stack findings (if available)
        call_graph = self._extract_call_graph(stack_findings)

    # [EXISTING CODE: Build base IR]
    evidence, evidence_lookup = self._bundle_evidence(
        codeql_findings, daikon_findings, stack_findings
    )
    intent = self._build_intent(codeql_findings, evidence_lookup)
    signature = SigClause(...)  # existing code
    effects = self._build_effects(stack_findings, evidence_lookup)
    assertions = self._build_assertions(daikon_findings, evidence_lookup)
    metadata = Metadata(...)  # existing code

    self._record_progress("reverse:ir-assembled")

    base_ir = IntermediateRepresentation(
        intent=intent,
        signature=signature,
        effects=effects,
        assertions=assertions,
        metadata=metadata,
    )

    # [NEW: Causal analysis integration]
    should_run_causal = (
        include_causal if include_causal is not None else self.config.run_causal
    )

    if should_run_causal and self.causal_enhancer is not None:
        self._record_progress("causal:start")

        try:
            # Parse AST from target module
            module_path = Path(repo_path) / target_module
            with open(module_path, "r") as f:
                code_text = f.read()
            ast_tree = ast.parse(code_text)

            # Enhance with causal capabilities (static mode for Phase 1)
            result = self.causal_enhancer.enhance(
                ir=base_ir,
                ast_tree=ast_tree,
                call_graph=call_graph,
                mode=self.config.causal_mode,  # "auto" or "static"
            )

            self._record_progress("causal:complete")

            # Return EnhancedIR
            from lift_sys.causal import EnhancedIR
            return EnhancedIR.from_enhancement_result(result)

        except Exception as e:
            # Log error but don't fail - graceful degradation
            self._record_progress(f"causal:error:{type(e).__name__}")
            # Return base IR on causal failure
            return base_ir

    # Return base IR if causal disabled
    return base_ir
```

**New Helper Method**:
```python
def _extract_call_graph(self, stack_findings: list[Finding]) -> nx.DiGraph | None:
    """Extract call graph from stack graph findings.

    Args:
        stack_findings: Stack graph analysis results

    Returns:
        NetworkX DiGraph representing call relationships, or None if unavailable
    """
    # TODO: Implement based on Stack Graphs output format
    # For Phase 1, can return None (CausalGraphBuilder will use AST only)
    return None
```

### Phase 2: Dynamic Mode Support (Optional)

**Goal**: Enable trace collection for dynamic mode.

**Requires**:
- Execution environment for target module
- Test input generation or trace recording
- Integration with `lift_sys.causal.trace_collector`

**Complexity**: High (requires code execution infrastructure)

**Priority**: P2 (static mode sufficient for most use cases)

**Future Work**: Deferred post-Week 4

---

## Testing Strategy

### Unit Tests (tests/reverse_mode/test_lifter_causal.py)

**Test Cases**:
1. **test_lift_with_causal_disabled**: Verify base IR returned when `include_causal=False`
2. **test_lift_with_causal_static_mode**: Verify EnhancedIR returned with static mode
3. **test_lift_causal_graceful_degradation**: Verify base IR returned on causal error
4. **test_lift_causal_config_override**: Verify `include_causal` param overrides config
5. **test_lift_causal_circuit_breaker**: Verify circuit breaker prevents repeated failures
6. **test_lift_causal_progress_log**: Verify progress logged ("causal:start", "causal:complete")

**Coverage**:
- All code paths (causal enabled/disabled)
- Error handling (AST parse errors, enhancement failures)
- Configuration options (config vs parameter override)
- Performance (causal shouldn't significantly slow lift())

### Integration Tests (tests/reverse_mode/test_lifter_causal_integration.py)

**Test Cases**:
1. **test_lifter_e2e_with_causal**: Full pipeline from repo → lift → causal queries
2. **test_lifter_causal_impact_query**: Lift → EnhancedIR → causal_impact()
3. **test_lifter_multiple_files_with_causal**: lift_all() with causal analysis
4. **test_lifter_causal_no_dowhy**: Verify graceful degradation when DoWhy unavailable

**Scenarios**:
- Real repositories (test fixtures)
- Multiple file analysis
- Various code structures (simple, complex, edge cases)

---

## Migration Path

### Backward Compatibility

**Goal**: No breaking changes for existing users.

**Guarantees**:
1. **Default Behavior**: `config.run_causal=False` by default (no change to existing behavior)
2. **Return Type**: `EnhancedIR` is compatible with `IntermediateRepresentation` (delegates all base methods)
3. **API**: `lift()` signature unchanged (new parameter is optional)
4. **Performance**: No overhead when `run_causal=False` (causal_enhancer=None)

### Opt-In Usage

**Existing Users** (no code changes needed):
```python
# Existing code continues to work unchanged
lifter = SpecificationLifter(LifterConfig())
ir = lifter.lift("main.py")  # Returns base IR as before
```

**New Users** (opt-in to causal):
```python
# Option 1: Configuration-based
config = LifterConfig(run_causal=True, causal_mode="static")
lifter = SpecificationLifter(config)
ir = lifter.lift("main.py")  # Returns EnhancedIR

if ir.has_causal_capabilities:
    impact = ir.causal_impact("function_name")

# Option 2: Parameter-based (override config)
config = LifterConfig(run_causal=False)
lifter = SpecificationLifter(config)
ir = lifter.lift("main.py", include_causal=True)  # Force enable, returns EnhancedIR
```

---

## Performance Considerations

### Static Mode Performance

**Baseline** (existing lift()):
- CodeQL: ~10-30s (database build)
- Daikon: ~5-15s (dynamic analysis)
- Stack Graphs: ~1-5s (graph extraction)
- **Total**: ~15-50s typical

**With Causal** (static mode):
- Existing analyzers: ~15-50s (unchanged)
- AST parsing: <0.1s
- Causal enhancement (static): <1s (validated in Week 4)
- **Total**: ~16-51s (2-3% overhead)

**Impact**: Minimal (<5% slowdown)

### Dynamic Mode Performance

**If Implemented** (Phase 2):
- Trace collection: ~5-30s (depends on coverage)
- Causal enhancement (dynamic): <10s for 1000 traces (validated in Week 2)
- **Total**: ~5-40s additional (10-50% overhead)

**Mitigation**: Dynamic mode is opt-in, users control when to enable

---

## Error Handling Strategy

### Causal Enhancement Failures

**Principle**: Causal analysis failures never block core lift-sys functionality.

**Error Categories**:

1. **AST Parse Errors**:
   - **Cause**: Syntax errors, unsupported Python version
   - **Handling**: Log warning, return base IR
   - **User Impact**: None (base IR still usable)

2. **DoWhy Subprocess Unavailable**:
   - **Cause**: `.venv-dowhy` missing, Python 3.11 not available
   - **Handling**: Circuit breaker opens, return base IR
   - **User Impact**: Causal features unavailable, core features work

3. **Enhancement Timeout**:
   - **Cause**: Very large graphs, complex SCM fitting
   - **Handling**: Timeout after configurable threshold, return base IR
   - **User Impact**: Causal unavailable for this file

4. **Circuit Breaker Open**:
   - **Cause**: Repeated DoWhy failures (threshold exceeded)
   - **Handling**: Skip causal enhancement immediately
   - **User Impact**: Causal disabled to prevent repeated failures

**Logging**:
```python
import logging

logger = logging.getLogger(__name__)

# In lift():
try:
    result = self.causal_enhancer.enhance(...)
except Exception as e:
    logger.warning(
        f"Causal enhancement failed for {target_module}: {e}. "
        f"Returning base IR without causal capabilities."
    )
    self._record_progress(f"causal:error:{type(e).__name__}")
    return base_ir
```

---

## Documentation Requirements

### API Documentation Updates

**Files to Update**:
1. `lift_sys/reverse_mode/lifter.py`: Docstrings for `lift()`, `LifterConfig`
2. `docs/reverse_mode/LIFTER_API.md`: API reference (if exists)
3. `README.md`: Add causal analysis section

**Example Docstring**:
```python
def lift(
    self,
    target_module: str,
    include_causal: bool | None = None,
) -> IntermediateRepresentation:
    """Lift a specification from a single module.

    Args:
        target_module: Path to the Python module to analyze.
        include_causal: Enable causal analysis (overrides config.run_causal).
                       - None: Use config.run_causal setting (default)
                       - True: Force enable causal analysis
                       - False: Force disable causal analysis

    Returns:
        IntermediateRepresentation: Base IR if causal disabled.
        EnhancedIR: IR with causal query methods if causal enabled.

        EnhancedIR is compatible with IntermediateRepresentation and
        delegates all base IR properties/methods.

    Raises:
        RepositoryNotLoadedError: If repository is not loaded.
        AnalysisError: If core analysis fails (causal errors are caught).

    Causal Analysis:
        When enabled, adds causal analysis capabilities to the lifted IR.
        Use `ir.has_causal_capabilities` to check availability.

        Available methods (when causal enabled):
        - ir.causal_impact(node): Calculate downstream impact
        - ir.causal_intervention(changes): Execute what-if queries
        - ir.causal_paths(source, target): Find causal paths

        See docs/causal/CAUSAL_ANALYSIS_GUIDE.md for details.

    Example:
        >>> config = LifterConfig(run_causal=True, causal_mode="static")
        >>> lifter = SpecificationLifter(config)
        >>> lifter.load_repository("my_project/")
        >>> ir = lifter.lift("main.py")
        >>> if ir.has_causal_capabilities:
        ...     impact = ir.causal_impact("validate_input")
        ...     print(f"Downstream impact: {impact}")
    """
```

### User Guide Updates

**New Section**: "Using Causal Analysis with Reverse Mode"

**Topics**:
- Enabling causal analysis (configuration vs parameter)
- Static vs dynamic mode selection
- Querying causal impact, interventions, paths
- Performance considerations
- Troubleshooting (DoWhy unavailable, circuit breaker)

---

## Implementation Checklist

### Phase 1: Static Mode Integration

- [ ] Update `LifterConfig` with causal options
- [ ] Add `self.causal_enhancer` to `SpecificationLifter.__init__()`
- [ ] Modify `lift()` method to call `CausalEnhancer.enhance()`
- [ ] Add `_extract_call_graph()` helper (stub for Phase 1)
- [ ] Handle AST parsing errors gracefully
- [ ] Add progress logging ("causal:start", "causal:complete", "causal:error")
- [ ] Write unit tests (tests/reverse_mode/test_lifter_causal.py)
- [ ] Write integration tests (tests/reverse_mode/test_lifter_causal_integration.py)
- [ ] Update docstrings
- [ ] Update user documentation

**Estimated Effort**: 4-6 hours

**Dependencies**: Week 4 complete (CausalEnhancer, EnhancedIR tested)

### Phase 2: Dynamic Mode (Future)

- [ ] Implement trace collection integration
- [ ] Add execution environment for target modules
- [ ] Update tests for dynamic mode
- [ ] Performance benchmarking

**Estimated Effort**: 10-15 hours

**Priority**: P2 (deferred)

---

## Risks and Mitigations

### Risk 1: Performance Impact

**Risk**: Causal analysis slows down lift() significantly.

**Likelihood**: Low (static mode <1s validated)

**Mitigation**:
- Static mode by default (<5% overhead)
- Dynamic mode is opt-in
- Circuit breaker prevents repeated slow operations
- Progress logging allows performance monitoring

### Risk 2: DoWhy Dependency Issues

**Risk**: DoWhy subprocess unavailable, breaks lift().

**Likelihood**: Medium (Python 3.11 requirement)

**Mitigation**:
- Graceful degradation (return base IR)
- Circuit breaker prevents repeated failures
- Clear error messages with installation docs
- `run_causal=False` by default (no impact on existing users)

### Risk 3: AST Parsing Failures

**Risk**: AST parsing fails for valid Python code.

**Likelihood**: Low (Python 3.13 ast.parse is robust)

**Mitigation**:
- Try/except around ast.parse()
- Return base IR on parse failure
- Log specific error for debugging
- No impact on core lift() functionality

### Risk 4: Integration Complexity

**Risk**: Integration introduces bugs in existing lift() logic.

**Likelihood**: Low (changes are additive)

**Mitigation**:
- Causal code is isolated (runs after base IR created)
- Existing tests continue to pass (no behavior change when disabled)
- Comprehensive new tests for causal path
- Code review before merge

---

## Success Criteria

### Functional Requirements

- [ ] `lift(file, include_causal=True)` returns EnhancedIR
- [ ] `ir.has_causal_capabilities` correctly indicates availability
- [ ] `ir.causal_impact()`, `ir.causal_intervention()`, `ir.causal_paths()` work
- [ ] Graceful degradation on causal failures (returns base IR)
- [ ] Circuit breaker prevents repeated DoWhy failures
- [ ] Existing tests pass (no breaking changes)

### Performance Requirements

- [ ] Static mode adds <5% overhead to lift()
- [ ] Causal enhancement completes in <1s for typical modules
- [ ] No performance impact when `run_causal=False`

### Quality Requirements

- [ ] 100% test coverage for new causal code paths
- [ ] All error paths tested (AST errors, DoWhy failures)
- [ ] Documentation complete (API docs, user guide)
- [ ] Code review approved

---

## Conclusion

This design integrates Week 4 CausalEnhancer into SpecificationLifter with:
- **Minimal changes**: Additive integration, no breaking changes
- **Graceful degradation**: Core functionality never blocked
- **Configuration-driven**: Users opt-in to causal analysis
- **Performance-aware**: <5% overhead in static mode
- **Well-tested**: Comprehensive unit and integration tests

**Status**: Ready for implementation (Week 4 foundation complete)

**Next Step**: Implement Phase 1 (Static Mode Integration)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-26
**Author**: Claude (with human oversight)
**Review Status**: Design complete, pending implementation
