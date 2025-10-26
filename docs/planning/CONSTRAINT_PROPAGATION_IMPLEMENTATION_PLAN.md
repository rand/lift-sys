# Constraint Propagation for Typed Holes: Implementation Plan

**Created**: October 16, 2025
**Status**: 📋 **READY TO START**
**Owner**: Rand Arete
**Timeline**: 6-8 weeks (phased approach)

---

## Executive Summary

This plan details the implementation of a Constraint Satisfaction Problem (CSP) solver for typed holes in lift-sys, enabling systematic, constraint-aware hole filling with parallel generation capabilities.

**Vision**: Transform IR generation from ad-hoc text generation into structured constraint solving, treating typed holes like sudoku cells with coordinated dependencies.

**Approach**: Phased implementation starting with lightweight dependency-aware filling, evolving to full CSP with backtracking and parallel generation.

---

## Phase 0: Foundation and Setup (Week 1)

**Goal**: Establish infrastructure and validate approach

### 0.1 Research Validation
- [x] Research constraint propagation techniques
- [x] Validate llguidance integration with Modal
- [x] Document architecture and approach
- [ ] Review and approve design with stakeholders

### 0.2 Development Environment
- [ ] Create feature branch: `feature/constraint-propagation-holes`
- [ ] Set up development structure:
  ```
  lift_sys/
    constraint_solver/        # New module
      __init__.py
      hole_csp.py              # CSP data structures
      propagation.py           # Constraint propagation algorithms
      solver.py                # Main solver
      strategies.py            # Solving strategies
    forward_mode/
      constrained_ir_translator.py  # Enhanced translator
  tests/
    unit/
      test_hole_csp.py
      test_propagation.py
      test_solver.py
    integration/
      test_constrained_translator.py
  ```

### 0.3 Dependencies
- [ ] Add networkx to dependencies (for constraint graphs)
- [ ] Verify llguidance available in Modal environment
- [ ] Update pyproject.toml with new dependencies

**Deliverable**: Clean development environment with approved design

**Effort**: 3-4 days

---

## Phase 1: Core Data Structures (Week 2)

**Goal**: Implement CSP data structures for typed holes

### 1.1 Constraint Modeling

**File**: `lift_sys/constraint_solver/hole_csp.py`

**Classes to implement**:

```python
@dataclass
class Constraint:
    """Constraint between typed holes."""
    source: str              # Source hole identifier
    target: str              # Target hole identifier
    predicate: str           # Constraint expression
    constraint_type: str     # Type: "depends_on", "type_match", "value_constraint"
    metadata: dict[str, Any]

    def check(self, source_value: Any, target_value: Any) -> bool:
        """Validate constraint satisfaction."""

    def to_dict(self) -> dict:
        """Serialize constraint."""

    @classmethod
    def from_typed_hole(cls, hole: TypedHole) -> list[Constraint]:
        """Extract constraints from TypedHole.constraints dict."""
```

**Implementation tasks**:
- [ ] Implement Constraint class with validation logic
- [ ] Support common constraint types:
  - [ ] `depends_on`: X depends on Y
  - [ ] `type_match`: X type must match Y type
  - [ ] `value_constraint`: X value must satisfy predicate
  - [ ] `domain_constraint`: X value must be in domain
- [ ] Add constraint parsing from TypedHole.constraints dict
- [ ] Unit tests for constraint checking

### 1.2 Hole Variables

```python
@dataclass
class HoleVariable:
    """CSP variable for a typed hole."""
    hole: TypedHole
    domain: list[Any]          # Possible values
    assignment: Any | None     # Current assignment
    metadata: dict[str, Any]   # Generation metadata

    @property
    def is_assigned(self) -> bool:
        """Check if variable has assignment."""

    def assign(self, value: Any) -> None:
        """Assign value to variable."""

    def unassign(self) -> None:
        """Clear assignment (for backtracking)."""

    def restrict_domain(self, new_domain: list[Any]) -> None:
        """Restrict domain (for constraint propagation)."""
```

**Implementation tasks**:
- [ ] Implement HoleVariable class
- [ ] Add domain management methods
- [ ] Add assignment tracking
- [ ] Unit tests for HoleVariable operations

### 1.3 Constraint Graph

```python
class HoleCSP:
    """Constraint Satisfaction Problem for typed holes."""

    def __init__(self, ir: IntermediateRepresentation):
        """Build CSP from IR with typed holes."""

    def _build_variables(self) -> None:
        """Extract typed holes as CSP variables."""

    def _build_constraints(self) -> None:
        """Extract constraints from hole metadata."""

    def _build_constraint_graph(self) -> nx.DiGraph:
        """Build directed graph of dependencies."""

    def get_independent_holes(self) -> list[str]:
        """Return holes with no dependencies (for parallel generation)."""

    def get_generation_order(self) -> list[str]:
        """Return topological order for hole generation."""

    def get_dependent_holes(self, hole_id: str) -> list[str]:
        """Return holes that depend on given hole."""

    def validate_solution(self, assignment: dict[str, Any]) -> bool:
        """Check if assignment satisfies all constraints."""
```

**Implementation tasks**:
- [ ] Implement HoleCSP class
- [ ] Build constraint graph from IR
- [ ] Implement topological sorting for generation order
- [ ] Detect cycles in constraint graph
- [ ] Add solution validation
- [ ] Unit tests for CSP construction and queries

**Deliverable**: Working CSP representation of typed holes with constraint graph

**Effort**: 5-7 days

---

## Phase 2: Basic Constraint Propagation (Week 3)

**Goal**: Implement forward checking and basic propagation

### 2.1 Forward Checking

**File**: `lift_sys/constraint_solver/propagation.py`

```python
def forward_check(
    csp: HoleCSP,
    assigned_hole: str,
    assigned_value: Any
) -> tuple[bool, dict[str, list[Any]]]:
    """
    Propagate assignment to dependent holes.

    Returns:
        (feasible, domain_changes):
            - feasible: True if no domain wipeout
            - domain_changes: Dict of holes -> removed values (for backtracking)
    """
```

**Implementation tasks**:
- [ ] Implement forward checking algorithm
- [ ] Track domain changes for backtracking
- [ ] Detect domain wipeout (no valid values left)
- [ ] Handle multiple constraints per hole
- [ ] Unit tests with various constraint patterns

### 2.2 Arc Consistency (AC-3)

```python
def arc_consistency_3(csp: HoleCSP) -> bool:
    """
    Enforce arc consistency on CSP.

    Returns:
        True if CSP is arc-consistent, False if inconsistent
    """

def revise(
    csp: HoleCSP,
    X: HoleVariable,
    Y: HoleVariable
) -> bool:
    """
    Remove values from X.domain that violate constraint with Y.

    Returns:
        True if domain was revised, False otherwise
    """
```

**Implementation tasks**:
- [ ] Implement AC-3 algorithm
- [ ] Implement revise function for constraint checking
- [ ] Add queue management for efficient propagation
- [ ] Unit tests for arc consistency
- [ ] Performance tests (should be fast for small graphs)

### 2.3 Constraint Propagation Strategies

**File**: `lift_sys/constraint_solver/strategies.py`

```python
class PropagationStrategy(ABC):
    """Base class for constraint propagation strategies."""

    @abstractmethod
    def propagate(
        self,
        csp: HoleCSP,
        assignment: dict[str, Any]
    ) -> tuple[bool, dict[str, list[Any]]]:
        """Propagate constraints given current assignment."""

class ForwardCheckingStrategy(PropagationStrategy):
    """Simple forward checking."""

class AC3Strategy(PropagationStrategy):
    """Full arc consistency."""

class NoStrategy(PropagationStrategy):
    """No propagation (baseline)."""
```

**Implementation tasks**:
- [ ] Define strategy interface
- [ ] Implement ForwardCheckingStrategy
- [ ] Implement AC3Strategy
- [ ] Implement NoStrategy (for comparison)
- [ ] Add strategy selection to solver
- [ ] Unit tests for each strategy

**Deliverable**: Working constraint propagation with multiple strategies

**Effort**: 5-7 days

---

## Phase 3: Domain Generation with LLM (Week 4)

**Goal**: Generate hole domains using LLM with llguidance

### 3.1 llguidance Integration

**File**: `lift_sys/providers/modal_provider.py` (enhance existing)

**New methods**:
```python
async def generate_with_grammar(
    self,
    prompt: str,
    grammar: str | dict,
    max_tokens: int = 200,
    temperature: float = 0.7,
    num_candidates: int = 1
) -> list[str]:
    """
    Generate text constrained by context-free grammar.

    Uses llguidance for fast constrained decoding.
    """
```

**Implementation tasks**:
- [ ] Research llguidance API for Modal/vLLM
- [ ] Add llguidance grammar specification support
- [ ] Implement grammar-constrained generation
- [ ] Test with simple grammars (JSON, regex)
- [ ] Add error handling and fallbacks
- [ ] Integration tests with Modal endpoint

### 3.2 Grammar Generation from TypedHole

**File**: `lift_sys/constraint_solver/grammar.py` (new)

```python
class GrammarBuilder:
    """Build llguidance grammars from TypedHole specifications."""

    def build_grammar_for_hole(self, hole: TypedHole) -> dict:
        """
        Convert TypedHole type_hint and constraints to llguidance grammar.

        Example:
            hole.type_hint = "str"
            hole.constraints = {"pattern": "[a-z_][a-z0-9_]*"}
            → Grammar: regex pattern for valid Python identifiers
        """

    def build_json_schema(self, hole: TypedHole) -> dict:
        """Build JSON schema for structured holes."""

    def build_regex_pattern(self, hole: TypedHole) -> str:
        """Build regex pattern for string holes."""
```

**Implementation tasks**:
- [ ] Implement GrammarBuilder class
- [ ] Map Python type hints to grammars:
  - [ ] `str` → string grammar with optional pattern
  - [ ] `int` → integer grammar with optional range
  - [ ] `float` → number grammar
  - [ ] `bool` → boolean grammar
  - [ ] `list[T]` → array grammar
  - [ ] `dict` → object grammar
- [ ] Handle constraint specifications:
  - [ ] `pattern`: Regex pattern
  - [ ] `enum`: Explicit value list
  - [ ] `minimum/maximum`: Numeric bounds
  - [ ] `domain`: Explicit domain constraint
- [ ] Unit tests for grammar generation
- [ ] Validate generated grammars

### 3.3 Domain Generation

**File**: `lift_sys/constraint_solver/domain_generator.py` (new)

```python
class DomainGenerator:
    """Generate domains for typed holes using LLM."""

    def __init__(self, provider: BaseProvider):
        self.provider = provider
        self.grammar_builder = GrammarBuilder()

    async def generate_domain(
        self,
        hole: TypedHole,
        context: dict[str, Any],
        num_candidates: int = 10,
        temperature: float = 0.7
    ) -> list[Any]:
        """
        Generate domain values for hole using LLM + llguidance.

        Args:
            hole: Typed hole to generate values for
            context: Current assignments and metadata
            num_candidates: Number of candidates to generate
            temperature: Sampling temperature

        Returns:
            List of candidate values satisfying hole constraints
        """

    def _build_generation_prompt(
        self,
        hole: TypedHole,
        context: dict[str, Any]
    ) -> str:
        """Build prompt for domain generation."""

    def _parse_generated_values(
        self,
        response: str | dict,
        hole: TypedHole
    ) -> list[Any]:
        """Parse LLM response into domain values."""
```

**Implementation tasks**:
- [ ] Implement DomainGenerator class
- [ ] Build prompts for domain generation
- [ ] Integrate llguidance grammar constraints
- [ ] Parse and validate generated values
- [ ] Handle explicit domain constraints (skip LLM)
- [ ] Add caching for repeated hole types
- [ ] Unit tests for domain generation
- [ ] Integration tests with Modal provider

**Deliverable**: LLM-based domain generation with llguidance constraints

**Effort**: 6-8 days

---

## Phase 4: Solver Implementation (Week 5)

**Goal**: Implement complete CSP solver with backtracking

### 4.1 Basic Solver

**File**: `lift_sys/constraint_solver/solver.py`

```python
class HoleSolver:
    """Base solver for typed holes."""

    def __init__(
        self,
        provider: BaseProvider,
        strategy: PropagationStrategy = None
    ):
        self.provider = provider
        self.domain_generator = DomainGenerator(provider)
        self.strategy = strategy or ForwardCheckingStrategy()

    async def solve(
        self,
        csp: HoleCSP,
        timeout: float = 60.0
    ) -> dict[str, Any] | None:
        """
        Solve CSP, returning assignment if successful.

        Returns:
            Assignment dict (hole_id -> value) or None if no solution
        """
```

**Implementation tasks**:
- [ ] Implement HoleSolver base class
- [ ] Add timeout handling
- [ ] Add logging and metrics
- [ ] Implement simple sequential solver (baseline)
- [ ] Unit tests for solver initialization
- [ ] Integration tests with simple CSPs

### 4.2 Backtracking Search

```python
async def backtrack_solve(
    self,
    csp: HoleCSP,
    assignment: dict[str, Any] | None = None,
    depth: int = 0
) -> dict[str, Any] | None:
    """
    Backtracking search with constraint propagation.

    Algorithm:
    1. If assignment complete, return it
    2. Select next unassigned variable (MCV heuristic)
    3. Generate domain for variable
    4. For each domain value:
        a. Assign value
        b. Propagate constraints
        c. If feasible, recurse
        d. If solution found, return it
        e. Backtrack (undo assignment)
    5. Return None (no solution)
    """
```

**Implementation tasks**:
- [ ] Implement backtracking algorithm
- [ ] Add variable selection heuristics:
  - [ ] Most Constrained Variable (MCV)
  - [ ] Most Constraining Variable
  - [ ] Minimum Remaining Values (MRV)
- [ ] Add value ordering heuristics:
  - [ ] Least Constraining Value (LCV)
  - [ ] Random ordering
- [ ] Track search statistics (nodes explored, backtracks)
- [ ] Add depth limiting for safety
- [ ] Unit tests for backtracking
- [ ] Test with unsolvable CSPs

### 4.3 Solution Validation

```python
def validate_solution(
    self,
    csp: HoleCSP,
    assignment: dict[str, Any]
) -> tuple[bool, list[str]]:
    """
    Validate complete assignment.

    Returns:
        (is_valid, errors): Validation result and error messages
    """
```

**Implementation tasks**:
- [ ] Implement solution validation
- [ ] Check all constraints satisfied
- [ ] Verify type consistency
- [ ] Check hole coverage (all holes assigned)
- [ ] Add detailed error reporting
- [ ] Unit tests for validation

**Deliverable**: Complete CSP solver with backtracking and validation

**Effort**: 6-8 days

---

## Phase 5: Parallel Generation (Week 6)

**Goal**: Enable parallel domain generation for independent holes

### 5.1 Parallel Domain Generation

**File**: `lift_sys/constraint_solver/parallel_solver.py` (new)

```python
class ParallelHoleSolver(HoleSolver):
    """Solver with parallel domain generation for independent holes."""

    async def solve_parallel(
        self,
        csp: HoleCSP,
        max_parallel: int = 5
    ) -> dict[str, Any] | None:
        """
        Solve CSP with parallel generation for independent holes.

        Strategy:
        1. Identify independent holes (no incoming edges)
        2. Generate domains in parallel (asyncio.gather)
        3. For each independent hole, assign best value
        4. Propagate constraints to dependent holes
        5. Continue with dependent holes (may be parallel if independent)
        6. Backtrack if needed
        """
```

**Implementation tasks**:
- [ ] Implement ParallelHoleSolver
- [ ] Identify independent hole sets at each level
- [ ] Use asyncio.gather for parallel domain generation
- [ ] Coordinate assignments across parallel holes
- [ ] Handle failures in parallel branches
- [ ] Add concurrency limits (max_parallel)
- [ ] Benchmark parallel vs sequential
- [ ] Unit tests for parallel solving

### 5.2 Batch Domain Generation

```python
async def generate_domains_batch(
    self,
    holes: list[TypedHole],
    context: dict[str, Any]
) -> dict[str, list[Any]]:
    """
    Generate domains for multiple holes in parallel.

    Uses provider batching if available.
    """
```

**Implementation tasks**:
- [ ] Implement batch domain generation
- [ ] Use provider batching if supported
- [ ] Handle partial failures gracefully
- [ ] Add retry logic for failed generations
- [ ] Measure speedup vs sequential
- [ ] Integration tests with Modal provider

**Deliverable**: Parallel solver with significant speedup for independent holes

**Effort**: 5-7 days

---

## Phase 6: Integration with lift-sys (Week 7)

**Goal**: Integrate solver with existing IR translation pipeline

### 6.1 Enhanced IR Translator

**File**: `lift_sys/forward_mode/constrained_ir_translator.py`

```python
class ConstrainedIRTranslator(XGrammarIRTranslator):
    """
    IR translator with constraint-aware hole solving.

    Extends XGrammarIRTranslator to automatically solve typed holes
    using CSP approach when present in generated IR.
    """

    def __init__(
        self,
        provider: BaseProvider,
        solver_strategy: str = "forward_checking",
        enable_parallel: bool = True
    ):
        super().__init__(provider)
        self.hole_solver = self._create_solver(solver_strategy, enable_parallel)

    async def translate(
        self,
        prompt: str,
        language: str = "python",
        max_retries: int = 3
    ) -> IntermediateRepresentation:
        """
        Translate with automatic hole solving.

        Process:
        1. Generate initial IR (may contain typed holes)
        2. If holes present, build CSP
        3. Solve CSP using constraint propagation
        4. Apply assignments to IR
        5. Validate complete IR
        6. Return solved IR
        """
```

**Implementation tasks**:
- [ ] Implement ConstrainedIRTranslator
- [ ] Add solver configuration options
- [ ] Integrate with existing translation pipeline
- [ ] Add fallback to hole clearing if solving fails
- [ ] Add metrics and logging
- [ ] Handle edge cases (no holes, unsolvable CSP)
- [ ] Unit tests for translator
- [ ] Integration tests with real prompts

### 6.2 IR Application Logic

```python
def _apply_solution_to_ir(
    self,
    ir: IntermediateRepresentation,
    assignment: dict[str, Any]
) -> IntermediateRepresentation:
    """
    Apply hole assignments to IR, replacing holes with values.

    This requires sophisticated logic to locate holes in IR structure
    and replace them with assigned values while maintaining IR validity.
    """
```

**Implementation tasks**:
- [ ] Implement hole replacement in IR
- [ ] Handle holes in different IR locations:
  - [ ] IntentClause
  - [ ] SigClause (parameters, return type)
  - [ ] EffectClause
  - [ ] AssertClause
- [ ] Preserve IR structure and metadata
- [ ] Validate modified IR
- [ ] Unit tests for IR application

### 6.3 Configuration and Options

**File**: `lift_sys/constraint_solver/__init__.py`

```python
@dataclass
class SolverConfig:
    """Configuration for constraint solver."""

    strategy: str = "forward_checking"  # forward_checking, ac3, none
    enable_parallel: bool = True
    max_parallel_holes: int = 5
    domain_size: int = 10
    temperature: float = 0.7
    timeout: float = 60.0
    enable_caching: bool = True
    backtrack_limit: int = 100
```

**Implementation tasks**:
- [ ] Define SolverConfig dataclass
- [ ] Add configuration validation
- [ ] Support environment variables
- [ ] Add config serialization
- [ ] Document configuration options

**Deliverable**: Full integration with lift-sys IR translation

**Effort**: 6-8 days

---

## Phase 7: Testing and Validation (Week 8)

**Goal**: Comprehensive testing and performance validation

### 7.1 Unit Tests

**Coverage goals**: >90% for new modules

**Test files**:
- [ ] `tests/unit/test_hole_csp.py`: CSP data structures
- [ ] `tests/unit/test_propagation.py`: Constraint propagation
- [ ] `tests/unit/test_solver.py`: Solver algorithms
- [ ] `tests/unit/test_domain_generator.py`: Domain generation
- [ ] `tests/unit/test_grammar.py`: Grammar building
- [ ] `tests/unit/test_parallel_solver.py`: Parallel solving

**Implementation tasks**:
- [ ] Write comprehensive unit tests
- [ ] Test edge cases and error conditions
- [ ] Test with malformed inputs
- [ ] Achieve >90% code coverage
- [ ] Fix any bugs found

### 7.2 Integration Tests

**Test scenarios**:
- [ ] Simple IR with 1-2 typed holes
- [ ] Complex IR with 5+ typed holes and dependencies
- [ ] IR with cyclic dependencies (should fail gracefully)
- [ ] IR with unsolvable constraints
- [ ] IR with parallel-solvable holes
- [ ] Real-world prompts from benchmarks

**Test files**:
- [ ] `tests/integration/test_constrained_translator.py`
- [ ] `tests/integration/test_end_to_end_solving.py`

**Implementation tasks**:
- [ ] Create integration test suite
- [ ] Test with real Modal provider
- [ ] Test with mocked provider (for CI)
- [ ] Measure success rate on benchmark prompts
- [ ] Compare against baseline (hole clearing)

### 7.3 Performance Benchmarks

**Metrics to measure**:
- Solving time vs number of holes
- Solving time vs constraint complexity
- Parallel speedup factor
- Success rate (solvable CSPs)
- LLM API calls per solution

**Implementation tasks**:
- [ ] Create benchmark suite
- [ ] Benchmark sequential solver
- [ ] Benchmark parallel solver
- [ ] Benchmark different strategies
- [ ] Compare against baseline
- [ ] Generate performance report

### 7.4 Example Scenarios

**Create examples demonstrating**:
- [ ] Type-dependent function generation
- [ ] Parameter validation with constraints
- [ ] Return type inference from parameters
- [ ] Complex multi-hole coordination

**Deliverable**: Fully tested and validated constraint solver

**Effort**: 8-10 days

---

## Phase 8: Documentation and Refinement (Ongoing)

**Goal**: Production-ready documentation and polish

### 8.1 API Documentation

**Files to document**:
- [ ] `constraint_solver/` module docstrings
- [ ] API reference for public classes
- [ ] Usage examples for common scenarios
- [ ] Configuration guide

### 8.2 User Guide

**File**: `docs/CONSTRAINT_SOLVER_USER_GUIDE.md`

**Sections**:
- [ ] Introduction and motivation
- [ ] Quick start guide
- [ ] Configuration options
- [ ] Advanced usage (custom constraints, strategies)
- [ ] Troubleshooting
- [ ] Performance tuning
- [ ] Limitations and future work

### 8.3 Developer Guide

**File**: `docs/CONSTRAINT_SOLVER_ARCHITECTURE.md`

**Sections**:
- [ ] System architecture
- [ ] Key algorithms
- [ ] Extension points
- [ ] Testing guide
- [ ] Contributing guidelines

### 8.4 Migration Guide

**File**: `docs/MIGRATING_TO_CONSTRAINT_SOLVER.md`

**Sections**:
- [ ] Comparison with old approach
- [ ] When to use constraint solver
- [ ] Migration steps
- [ ] Compatibility notes

**Deliverable**: Complete documentation suite

**Effort**: 5-7 days (distributed)

---

## Risk Management

### Technical Risks

**Risk 1: llguidance integration complexity**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Start with simple fallback (text generation), add llguidance incrementally
- **Contingency**: Use XGrammar structured output as alternative

**Risk 2: CSP solving too slow**
- **Probability**: Low-Medium
- **Impact**: Medium
- **Mitigation**: Implement parallel solving early, add caching
- **Contingency**: Use simpler strategy (no backtracking) or lightweight approach

**Risk 3: Constraint specification too complex**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Start with simple constraints, add complexity gradually
- **Contingency**: Provide constraint templates and builder helpers

**Risk 4: Unsolvable CSPs common**
- **Probability**: Medium
- **Impact**: Low
- **Mitigation**: Graceful fallback to hole clearing
- **Contingency**: Add constraint relaxation mechanism

### Schedule Risks

**Risk 5: llguidance learning curve**
- **Probability**: Medium
- **Impact**: Low-Medium
- **Mitigation**: Allocate extra time in Phase 3, consult documentation early
- **Contingency**: Use alternative constraint mechanism (XGrammar only)

**Risk 6: Integration complications**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Continuous integration testing, incremental rollout
- **Contingency**: Feature flag for enabling/disabling solver

---

## Success Metrics

### Quantitative Metrics

1. **Solving success rate**: >85% of IRs with typed holes successfully solved
2. **Performance**: <5s additional latency for holes with <10 variables
3. **Parallel speedup**: >2x for IRs with 5+ independent holes
4. **Code coverage**: >90% for constraint_solver module
5. **Integration success**: Zero regressions in existing IR translation tests

### Qualitative Metrics

1. **Code quality**: Clean architecture, well-documented, maintainable
2. **Usability**: Simple API, good defaults, easy configuration
3. **Reliability**: Graceful error handling, helpful error messages
4. **Extensibility**: Easy to add new constraint types and strategies

---

## Rollout Plan

### Phase 1: Internal Testing (Week 9)
- [ ] Deploy to development environment
- [ ] Test with representative workloads
- [ ] Gather performance metrics
- [ ] Fix critical bugs

### Phase 2: Limited Rollout (Week 10)
- [ ] Enable for 10% of IR translations (feature flag)
- [ ] Monitor error rates and performance
- [ ] Collect user feedback
- [ ] Adjust configuration based on data

### Phase 3: Full Rollout (Week 11)
- [ ] Enable for 50% of translations
- [ ] Continue monitoring
- [ ] Week 12: Enable for 100% if metrics good
- [ ] Make constraint solver default

### Phase 4: Optimization (Week 12+)
- [ ] Analyze bottlenecks
- [ ] Optimize hot paths
- [ ] Add caching layers
- [ ] Tune configuration defaults

---

## Alternative: Lightweight Approach

If full CSP proves too complex or slow, pivot to **lightweight approach**:

**Simplified implementation** (2-3 weeks):
1. Build dependency graph only (no full CSP)
2. Topological sort for generation order
3. Simple forward checking (no backtracking)
4. Generate values sequentially with llguidance
5. Fail fast if constraint violated

**Pros**: Faster to implement, simpler, lower overhead
**Cons**: Less robust, can't handle complex constraints, no parallel generation

**Decision point**: End of Phase 4 (Week 5)
- If backtracking solver working well → continue with full approach
- If struggling with complexity → pivot to lightweight approach

---

## Dependencies and Blockers

### External Dependencies
- llguidance availability in Modal environment
- vLLM version with llguidance support
- networkx for constraint graphs

### Internal Dependencies
- Stable XGrammarIRTranslator (current baseline)
- Modal provider with structured output support
- TypedHole constraints specification format

### Potential Blockers
- llguidance integration issues → Use XGrammar fallback
- Modal provider limitations → Test with local provider first
- Performance issues → Optimize or use lightweight approach

---

## Team and Resources

### Required Skills
- Python async programming (asyncio)
- Constraint satisfaction algorithms
- Graph algorithms (networkx)
- LLM integration and prompting
- Testing and benchmarking

### Time Allocation
- Development: 70% (architecture, implementation, testing)
- Research: 10% (llguidance, algorithms)
- Documentation: 10% (user guide, API docs)
- Testing/Debugging: 10% (bug fixes, performance)

### Infrastructure
- Modal account with GPU access
- Development environment with Python 3.12+
- CI/CD pipeline for testing
- Benchmarking infrastructure

---

## Conclusion

This implementation plan provides a structured, phased approach to implementing constraint propagation for typed holes in lift-sys. The plan:

1. **Starts simple**: Foundation → Data structures → Basic algorithms
2. **Adds sophistication**: Propagation → LLM integration → Backtracking
3. **Optimizes**: Parallel generation → Performance tuning
4. **Validates**: Comprehensive testing → Documentation

**Timeline**: 8-12 weeks for full implementation
**Effort**: ~120-160 hours total
**Risk**: Medium (manageable with phased approach and contingencies)
**Reward**: High (systematic, constraint-aware hole solving)

The phased approach allows for early validation and pivoting to lightweight approach if needed, while maintaining a clear path to the full vision of CSP-based hole solving.

**Next step**: Review plan, create Beads work items, start Phase 0.
