# DSPy Architecture Track Status

**Last Updated**: 2025-10-27
**Track Priority**: P0 (Foundational architecture)
**Current Phase**: Phase 3 of 7 (Optimization & Execution) - 80% complete

---

## For New Claude Code Session

**Quick Context** (30 seconds):
- **10/19 holes resolved** (53% complete)
- Current: Phase 3 (Optimization & Execution) - 80% done
- Next holes: H4 (ParallelExecutor), H5 (ErrorRecovery), H15 (ConstraintTracking)
- Methodology: Typed holes with constraint propagation

**Start Work**:
```bash
# Read current state
cat docs/planning/SESSION_STATE.md | head -100

# Check hole status
python3 scripts/planning/track_holes.py ready --phase 3

# View next hole
python3 scripts/planning/track_holes.py show H4
```

---

## Current Status (2025-10-27)

### ✅ Holes Resolved: 10/19 (53%)

**Phase 1** (Interface Completeness - 1/3):
- H6: NodeSignatureInterface ✅ (async design)

**Phase 2** (Core Implementation - 4/6):
- H9: BasicProvider ✅
- H14: ResourceLimits ✅
- H1: ProviderAdapter ✅ (dual routing)
- H2: CallPattern ✅

**Phase 3** (Optimization & Execution - 5/10):
- H11: BasicGraphExecutor ✅
- H10: DependencyResolver ✅
- H8: SimpleOptimizer ✅
- H17: ValidationCache ✅
- H12: ExecutionContext ✅

### 🔄 Next Holes (Phase 3 remaining)

**H4: ParallelExecutor** (Week 2):
- Enable concurrent node execution
- Blocked by: H6 ✅, H10 ✅
- Effort: 3-4 days

**H5: ErrorRecovery** (Week 2):
- Retry logic and fallbacks
- Blocked by: H1 ✅, H4 (after implementation)
- Effort: 2-3 days

**H15: ConstraintTracking** (Week 6):
- Provenance and debugging support
- Blocked by: H8 ✅
- Effort: 2-3 days

---

## Architecture Overview

### DSPy + Pydantic AI Integration

**Goal**: Replace hardcoded prompts with declarative DSPy signatures and Pydantic AI graphs

**Benefits**:
- Automatic prompt optimization (MIPROv2, COPRO)
- Type-safe LLM interactions
- Graph-based workflow orchestration
- Resource tracking and optimization
- Systematic testing and validation

### Key Components

```
DSPy Signatures (lift_sys/dspy_signatures/)
├── node_interface.py       # H6: Node interface (async)
├── provider_adapter.py     # H1: Provider routing
├── graph_executor.py       # H11, H4: Execution engines
├── error_recovery.py       # H5: Retry and fallbacks
├── optimizer.py            # H8: Graph optimization
└── validation_cache.py     # H17: Cache layer
```

### Data Flow

```
User Prompt
  ↓
NLP → IR Translation (DSPy Signature)
  ↓
IR Validation (cached via H17)
  ↓
Pydantic AI Graph (nodes = H6)
  ↓
Graph Optimization (H8)
  ↓
Dependency Resolution (H10)
  ↓
Parallel Execution (H4 - pending)
  ↓
Error Recovery (H5 - pending)
  ↓
Generated Code
```

---

## Hole-Driven Development Methodology

### How It Works

**Architecture as IR with Typed Holes**:
```python
# Example: H4 ParallelExecutor
class ParallelExecutor:
    """
    Type: Executor
    Signature: async execute(graph: DAG, context: ExecutionContext) -> Results
    Constraints:
      - MUST use asyncio.gather() for parallel execution
      - MUST respect dependency order from H10
      - MUST propagate errors via H5
    """
    pass  # ← Typed hole to fill
```

**Constraint Propagation**:
When H6 was resolved with async design:
- Propagated to H1: ProviderAdapter MUST support async calls
- Propagated to H4: ParallelExecutor MUST use asyncio.gather()
- Propagated to H5: ErrorRecovery MUST handle async exceptions

**Documentation**:
- `CONSTRAINT_PROPAGATION_LOG.md` - Event log of all constraint propagations
- `HOLE_INVENTORY.md` - All 19 holes with dependencies
- `SESSION_STATE.md` - Current work context

### Workflow

**For each hole**:
1. **Read** hole spec from HOLE_INVENTORY.md
2. **Implement** following acceptance criteria
3. **Commit** before testing
4. **Test** implementation
5. **Document** constraint propagation
6. **Update** SESSION_STATE.md
7. **Commit** documentation

**Critical Rules**:
- ❌ NEVER start hole without reading SESSION_STATE.md
- ❌ NEVER skip constraint propagation documentation
- ❌ NEVER implement out of dependency order
- ✅ ALWAYS follow hole specification exactly

---

## Phase Progress

### Phase 1: Interface Completeness (1/3 complete, 33%)

**Resolved**:
- H6: NodeSignatureInterface ✅

**Pending**:
- H9: BasicProvider (moved to Phase 2)
- H14: ResourceLimits (moved to Phase 2)

**Gate 1 Criteria** (4/14 satisfied, 28%):
- ✅ H6 async interface defined
- ✅ Basic provider working (H9 moved but functional)
- ✅ Resource tracking present (H14 moved but functional)
- ✅ Initial tests passing
- ⏳ 10 other criteria pending

### Phase 2: Core Implementation (4/6 complete, 67%)

**Resolved**:
- H9: BasicProvider ✅
- H14: ResourceLimits ✅
- H1: ProviderAdapter ✅
- H2: CallPattern ✅

**Pending**:
- H3: IRBuilder (Week 2)
- H7: GraphOptimizer (Week 3)

### Phase 3: Optimization & Execution (5/10 complete, 50%)

**Resolved**:
- H11: BasicGraphExecutor ✅
- H10: DependencyResolver ✅
- H8: SimpleOptimizer ✅
- H17: ValidationCache ✅
- H12: ExecutionContext ✅

**Pending** (5 holes):
- H4: ParallelExecutor (Week 2)
- H5: ErrorRecovery (Week 2)
- H15: ConstraintTracking (Week 6)
- H13: ResourceManager (Week 4)
- H16: MetricsCollector (Week 5)

### Phases 4-7 (9 holes remaining)

**Phase 4: Validation** (3 holes)
- H18: TypeValidator
- H19: SemanticValidator
- H20: ConstraintChecker

**Phase 5: Deployment** (2 holes)
- H21: ProductionConfig
- H22: MonitoringSetup

**Phase 6: Scale** (2 holes)
- H23: CachingStrategy
- H24: LoadBalancing

**Phase 7: Governance** (2 holes)
- H25: SecurityAudit
- H26: ComplianceChecks

---

## Key Implementations

### H6: NodeSignatureInterface (Async Design)

```python
class NodeSignatureInterface(Protocol):
    """Async node interface for Pydantic AI graph nodes."""

    async def __call__(
        self,
        context: RunContext,
        deps: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute node with dependencies."""
        ...
```

**Design Decision**: Async-first for LLM calls
**Constraint Propagation**: All executors MUST be async

### H1: ProviderAdapter (Dual Routing)

```python
class ProviderAdapter:
    """Routes to Modal (XGrammar) when available, best provider otherwise."""

    async def __call__(
        self,
        prompt: str,
        schema: dict | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.3,
    ) -> dspy.Prediction:
        if schema and self.provider.capabilities.structured_output:
            # Route to Modal (XGrammar)
            return await self.provider.generate_structured(prompt, schema)
        else:
            # Route to best available
            return await self.provider.generate(prompt)
```

**Design Decision**: Dual routing enables gradual migration
**Constraint Propagation**: All LLM calls go through adapter

### H17: ValidationCache

```python
class ValidationCache:
    """Cache validation results to avoid redundant checks."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[bool, list[str]]] = {}
        self._ttl = ttl_seconds

    def get(self, ir_hash: str) -> tuple[bool, list[str]] | None:
        """Get cached validation result."""
        if ir_hash in self._cache:
            result, timestamp = self._cache[ir_hash]
            if time.time() - timestamp < self._ttl:
                return result
        return None

    def set(self, ir_hash: str, result: tuple[bool, list[str]]) -> None:
        """Cache validation result."""
        self._cache[ir_hash] = (result, time.time())
```

**Design Decision**: Simple in-memory cache with TTL
**Constraint Propagation**: Validators MUST compute deterministic hashes

---

## Testing

### Test Coverage by Hole

```
Hole    Tests   Status
──────────────────────────
H6      15/15   ✅ All passing
H1      12/12   ✅ All passing
H2      10/10   ✅ All passing
H8       8/8    ✅ All passing
H9      17/17   ✅ All passing (with today's fixes)
H10      6/6    ✅ All passing
H11      8/8    ✅ All passing
H12      9/9    ✅ All passing
H14      5/5    ✅ All passing
H17      6/6    ✅ All passing
──────────────────────────
Total   96/96   ✅ 100%
```

### Test Strategy

**Unit Tests** (lift_sys/dspy_signatures/):
- Each hole has dedicated test file
- Mock external dependencies (LLMs, DB)
- Type safety verified with mypy --strict

**Integration Tests**:
- Full DSPy → Pydantic AI pipeline
- Real Modal.com provider calls
- Validation caching end-to-end

**Performance Tests**:
- Benchmark optimization impact (H8)
- Cache hit rate measurement (H17)
- Parallel execution speedup (H4 - pending)

---

## Known Issues

### Active Issues

**None** - All implemented holes working correctly

### Resolved Issues (Today!)

✅ **H9 MockProvider** (17 tests) - Fixed `structured_output` capability
✅ **H1 Prediction Conversion** (2 tests) - Fixed dict extraction from dspy.Prediction

---

## Roadmap

### Q4 2025 (Current)

**October** (Week 1-2):
- Complete Phase 3: H4, H5, H15
- Gate 3 validation
- Documentation updates

**November** (Week 3-6):
- Phase 4: Validation (H18, H19, H20)
- Phase 5: Deployment (H21, H22)
- Gate 4 & 5 validation

**December** (Week 7):
- Phase 6: Scale (H23, H24)
- Phase 7: Governance (H25, H26)
- Final gate validation
- Production readiness review

### Q1 2026

**Migration**:
- Replace hardcoded prompts with DSPy signatures
- Deploy to production with feature flags
- Monitor performance and quality
- Iterate based on feedback

---

## Resources

### Documentation

- **SESSION_STATE.md**: Current work context and next hole
- **HOLE_INVENTORY.md**: All 19 holes with dependencies
- **CONSTRAINT_PROPAGATION_LOG.md**: Constraint propagation events
- **REIFICATION_SUMMARY.md**: Methodology explanation
- **SESSION_BOOTSTRAP.md**: 5-minute quick start guide

### Tools

- **track_holes.py**: Hole management CLI
  - `ready`: Show ready holes
  - `show H4`: View hole details
  - `resolve H4`: Mark hole complete
  - `phase-status 3`: Check phase progress

### External References

- **DSPy**: https://github.com/stanfordnlp/dspy
- **Pydantic AI**: https://ai.pydantic.dev
- **MIPROv2**: DSPy optimization algorithm

---

## Quick Commands

```bash
# Read current state
cat docs/planning/SESSION_STATE.md | head -100

# Check ready holes
python3 scripts/planning/track_holes.py ready --phase 3

# View hole details
python3 scripts/planning/track_holes.py show H4

# Implement hole (example: H4)
# 1. Read spec
cat docs/planning/HOLE_INVENTORY.md | grep -A 50 "H4:"

# 2. Implement
vim lift_sys/dspy_signatures/graph_executor.py

# 3. Test (AFTER committing!)
git add . && git commit -m "Implement H4: ParallelExecutor"
uv run pytest tests/unit/dspy_signatures/test_graph_executor.py

# 4. Document constraint propagation
vim docs/planning/CONSTRAINT_PROPAGATION_LOG.md

# 5. Update state
vim docs/planning/SESSION_STATE.md

# 6. Commit
git add docs/planning/*.md && git commit -m "Document H4 constraint propagation"
```

---

**End of DSPy Track Status**

**For next session**: Continue with H4 (ParallelExecutor) or check SESSION_STATE.md for current work.
