# Constraint Propagation for Typed Holes: A Sudoku-Like Approach

**Created**: October 16, 2025
**Status**: 📋 **RESEARCH COMPLETE** - Ready for design phase
**Vision**: Parallel constrained decoding across typed holes with coordinated constraint propagation

---

## Executive Summary

This document explores treating IR generation with typed holes as a **Constraint Satisfaction Problem (CSP)** where:

1. **Typed holes** = CSP variables (like sudoku cells)
2. **Type hints + domain constraints** = CSP domains (possible values)
3. **Cross-hole dependencies** = CSP constraints (coordinating rules)
4. **Parallel constrained decoding** = Solving multiple variables simultaneously
5. **Final validation** = Checking global constraint satisfaction

**Key Insight**: Your sudoku analogy is exactly right! Typed holes with coordinated constraints can be solved using CSP techniques combined with LLM-based generation.

---

## Part 1: The Current State (lift-sys)

### Typed Holes in lift-sys

From `lift_sys/ir/models.py:113-135`:

```python
@dataclass(slots=True)
class TypedHole:
    """Explicit representation of an unknown value in the IR."""

    identifier: str          # Unique name (e.g., "param_type", "return_value")
    type_hint: str          # Expected type (e.g., "str", "int", "List[str]")
    description: str        # Human-readable description
    constraints: dict[str, str]  # Domain-specific constraints
    kind: HoleKind          # INTENT, SIGNATURE, EFFECT, ASSERTION, IMPLEMENTATION
```

**Example typed holes in IR**:
```json
{
  "signature": {
    "name": "<?hole_1: function_name?>",
    "parameters": [
      {
        "name": "value",
        "type_hint": "<?hole_2: parameter_type?>",
        "description": "Input to process"
      }
    ],
    "returns": "<?hole_3: return_type?>",
    "holes": [
      {
        "identifier": "hole_1",
        "type_hint": "str",
        "constraints": {"pattern": "[a-z_][a-z0-9_]*"},
        "kind": "signature"
      },
      {
        "identifier": "hole_2",
        "type_hint": "str",
        "constraints": {"valid_types": ["int", "str", "list", "dict"]},
        "kind": "signature"
      },
      {
        "identifier": "hole_3",
        "type_hint": "str",
        "constraints": {
          "depends_on": "hole_2",
          "rule": "if hole_2 == 'int' then hole_3 in ['int', 'str', 'bool']"
        },
        "kind": "signature"
      }
    ]
  }
}
```

### Current Hole Handling

**Current approach** (from `xgrammar_generator.py:88-110`):
```python
# Clear any unresolved holes (e.g., from IR deserialization)
holes = ir.typed_holes()
if holes:
    # Clear hole lists from all locations
    ir.intent.holes = []
    ir.signature.holes = []
    for effect in ir.effects:
        effect.holes = []
    for assertion in ir.assertions:
        assertion.holes = []
```

**Problem**: Holes are simply cleared, not systematically filled with constraint awareness.

---

## Part 2: The Vision (Sudoku-Like Constraint Propagation)

### Sudoku Analogy

**Sudoku cell**:
- Has a position (row, column)
- Has possible values (1-9)
- Constrained by row/column/box rules
- Value choice affects other cells

**Typed hole**:
- Has an identifier (`hole_1`)
- Has possible values (domain: `["int", "str", "list"]`)
- Constrained by type system + domain logic
- Value choice affects dependent holes

### Example: Type-Dependent Return Value

**Problem**: Generate function that validates input type and returns appropriate message.

**Typed holes with constraints**:
```python
# Hole 1: Parameter type
hole_1 = TypedHole(
    identifier="param_type",
    type_hint="str",
    constraints={
        "domain": ["int", "str", "list", "dict"],
        "affects": ["return_type", "validation_logic"]
    },
    kind=HoleKind.SIGNATURE
)

# Hole 2: Return type (depends on hole_1)
hole_2 = TypedHole(
    identifier="return_type",
    type_hint="str",
    constraints={
        "depends_on": ["param_type"],
        "rule": "if param_type == 'int' then return_type == 'bool' else return_type == 'str'"
    },
    kind=HoleKind.SIGNATURE
)

# Hole 3: Validation logic (depends on both)
hole_3 = TypedHole(
    identifier="validation_logic",
    type_hint="str",  # Code snippet
    constraints={
        "depends_on": ["param_type", "return_type"],
        "template": "isinstance(value, {param_type}) and return {return_type}"
    },
    kind=HoleKind.IMPLEMENTATION
)
```

**Constraint graph** (like sudoku constraints):
```
param_type (hole_1)
    ↓
    ├─→ return_type (hole_2)
    │      ↓
    └───→ validation_logic (hole_3)
```

**Solving process** (parallel):
1. Generate domain for `param_type`: `["int", "str", "list", "dict"]`
2. For each candidate in `param_type`, propagate constraints:
   - If `param_type = "int"` → constrain `return_type = "bool"`
   - If `param_type = "str"` → constrain `return_type = "str"`
3. Generate `validation_logic` using constrained decoding with both values fixed
4. Validate complete solution

---

## Part 3: Research Foundations

### 3.1 Type-Constrained Code Generation (arXiv 2504.09246)

**Key Innovation**: Prefix automata + search over inhabitable types

**Approach**:
1. Build automaton that accepts only well-typed code prefixes
2. At each generation step, mask tokens that would violate type constraints
3. Search over possible type inhabitations (ways to fill typed holes)

**Results**:
- 50%+ reduction in compilation errors
- Significant improvement in functional correctness
- Works across synthesis, translation, repair tasks

**Relevance to lift-sys**: This is almost exactly our typed holes concept! They're enforcing type constraints during decoding.

**How it works**:
```
Current state: "def validate("
Type context: {expecting: parameter with type annotation}
Valid next tokens: [identifier tokens] ∪ [type annotation tokens]
Invalid tokens: [return, if, while, ...] (syntax errors)

After "def validate(value: "
Type context: {expecting: type expression}
Valid tokens: [int, str, list, dict, ...]
Invalid tokens: [123, "hello", ...] (not types)
```

### 3.2 GenCP: LLM + Constraint Programming (arXiv 2407.13490)

**Key Innovation**: Dynamic CSP where LLM generates variable domains

**Three core procedures**:

**GenV (Generate Variable)**:
```python
def gen_v(problem: CSP, var_name: str) -> Variable:
    """Create new CSP variable with empty domain."""
    var = Variable(name=var_name, domain=[])
    problem.add_variable(var)
    return var
```

**GenD (Generate Domain)** ⭐ Most relevant:
```python
async def gen_d(
    llm: LLM,
    var: Variable,
    context: Context,
    constraints: List[Constraint]
) -> Domain:
    """Use LLM to generate variable domain, filtered by constraints."""
    # Get LLM predictions for this variable
    candidates = await llm.generate_candidates(
        prompt=context.to_prompt(),
        num_candidates=10,
        temperature=0.7
    )

    # Filter candidates through constraints
    valid_candidates = [
        c for c in candidates
        if all(constraint.check(c) for constraint in constraints)
    ]

    var.domain = valid_candidates
    return var.domain
```

**GenC (Generate Constraints)**:
```python
def gen_c(problem: CSP, var: Variable, spec: ConstraintSpec) -> Constraint:
    """Create constraint from specification."""
    constraint = Constraint(
        variables=[var] + spec.dependent_vars,
        predicate=spec.predicate,
        relation=spec.relation
    )
    problem.add_constraint(constraint)
    return constraint
```

**GenCP Results**:
- 100% constraint satisfaction (vs. 80-90% for beam search)
- Faster time to valid solution
- Natural integration of LLM flexibility + CP guarantees

**Mapping to lift-sys typed holes**:

| GenCP Concept | lift-sys Equivalent |
|---------------|---------------------|
| CSP Variable | TypedHole |
| Variable Domain | Constrained LLM generations for hole |
| Constraint | `TypedHole.constraints` dict |
| GenV | Create new TypedHole |
| GenD | Generate candidates for hole with llguidance |
| GenC | Define dependency between holes |
| Problem | IntermediateRepresentation with holes |

### 3.3 llguidance: Fast Constraint Enforcement

**Architecture**:
```
llguidance
├── Context-free grammar (CFG) definition
├── Earley parser (handles ambiguity, left recursion)
├── Regex-derivative lexer (fast token classification)
└── Token mask computation (50μs per token)
```

**Core algorithm**:
```python
def compute_token_mask(
    grammar: Grammar,
    token_prefix: List[Token],
    tokenizer: Tokenizer
) -> TokenMask:
    """
    Compute valid next tokens given grammar and current prefix.

    Returns:
        TokenMask: Binary mask over tokenizer vocabulary
                   1 = valid, 0 = invalid
    """
    # Parse current prefix to get parser state
    parser_state = earley_parse(grammar, token_prefix)

    # For each token in vocabulary
    mask = np.zeros(len(tokenizer.vocab), dtype=bool)
    for token_id, token in enumerate(tokenizer.vocab):
        # Check if adding this token keeps parse valid
        if can_continue_parse(parser_state, token):
            mask[token_id] = True

    return mask
```

**Performance**:
- 50μs/token (128k vocab tokenizer)
- Handles batch sizes up to 3200 (16 cores)
- Negligible startup cost
- Scales to parallel generation

**Integration with vLLM/SGLang**: Already supported, can use with Modal provider!

---

## Part 4: Constraint Propagation Techniques

### 4.1 Arc Consistency (AC-3 Algorithm)

**Classic CSP technique** for constraint propagation.

**Algorithm**:
```python
def arc_consistency_3(problem: CSP) -> CSP:
    """
    Enforce arc consistency on CSP.

    For each pair of variables (X, Y) with constraint C(X, Y):
    Remove values from domain(X) that have no supporting value in domain(Y)
    """
    queue = problem.get_all_arcs()  # All constraint pairs

    while queue:
        (X, Y) = queue.pop()

        # Check if we need to revise X's domain
        if revise(problem, X, Y):
            if len(X.domain) == 0:
                return None  # No solution

            # Add all arcs (Z, X) back to queue where Z ≠ Y
            for Z in problem.neighbors(X):
                if Z != Y:
                    queue.append((Z, X))

    return problem


def revise(problem: CSP, X: Variable, Y: Variable) -> bool:
    """Remove values from X.domain that violate constraint with Y."""
    revised = False
    constraint = problem.get_constraint(X, Y)

    for x_val in X.domain[:]:  # Copy to allow modification
        # Check if any value in Y.domain satisfies constraint
        if not any(constraint.check(x_val, y_val) for y_val in Y.domain):
            X.domain.remove(x_val)
            revised = True

    return revised
```

**Example for typed holes**:
```python
# Hole 1: parameter type
param_type.domain = ["int", "str", "list"]

# Hole 2: return type (must be compatible with param_type)
return_type.domain = ["int", "str", "bool"]

# Constraint: if param_type == "list", return_type must be "bool" or "str"
constraint = lambda p, r: (p != "list") or (r in ["bool", "str"])

# Apply arc consistency
# Check param_type = "list"
# → return_type can only be ["bool", "str"]
# → remove "int" from return_type.domain
# Result: return_type.domain = ["bool", "str"]
```

### 4.2 Forward Checking

**Simpler but effective** constraint propagation.

**Algorithm**:
```python
def forward_check(
    problem: CSP,
    assigned_var: Variable,
    assigned_value: Any
) -> bool:
    """
    After assigning value to var, propagate constraints to unassigned neighbors.

    Returns:
        True if still feasible, False if domain wipeout detected
    """
    for neighbor in problem.neighbors(assigned_var):
        if neighbor.is_assigned:
            continue

        constraint = problem.get_constraint(assigned_var, neighbor)

        # Remove values from neighbor that conflict with assigned_value
        for neighbor_val in neighbor.domain[:]:
            if not constraint.check(assigned_value, neighbor_val):
                neighbor.domain.remove(neighbor_val)

        # Check for domain wipeout (no valid values left)
        if len(neighbor.domain) == 0:
            return False  # No solution with this assignment

    return True
```

**Example**:
```python
# Assign param_type = "int"
param_type.assign("int")

# Forward check to return_type
constraint = "if param_type == 'int' then return_type in ['int', 'bool']"
return_type.domain = ["int", "str", "bool"]

# Apply constraint
return_type.domain = [v for v in return_type.domain if constraint.check("int", v)]
# Result: return_type.domain = ["int", "bool"]
```

### 4.3 Backtracking with Constraint Propagation

**Complete search** with intelligent pruning.

```python
async def backtrack_search(
    problem: CSP,
    llm: LLM,
    assignment: Assignment = None
) -> Assignment | None:
    """
    Backtracking search with constraint propagation.

    Uses:
    - Most constrained variable (MCV) heuristic
    - Least constraining value (LCV) heuristic
    - Forward checking for early failure detection
    """
    if assignment is None:
        assignment = Assignment()

    # Base case: all variables assigned
    if assignment.is_complete(problem):
        return assignment

    # Select next variable (most constrained first)
    var = select_unassigned_variable(problem, assignment)

    # Generate domain for this variable using LLM + constraints
    domain = await gen_d(llm, var, assignment.context(), problem.constraints_for(var))

    # Try each value in domain
    for value in domain:
        # Check if value consistent with assignment
        if is_consistent(value, assignment, problem):
            # Make assignment
            assignment.assign(var, value)

            # Propagate constraints (forward check)
            if forward_check(problem, var, value):
                # Recurse
                result = await backtrack_search(problem, llm, assignment)
                if result is not None:
                    return result

            # Backtrack
            assignment.unassign(var)

    return None  # No solution found


def select_unassigned_variable(
    problem: CSP,
    assignment: Assignment
) -> Variable:
    """Select variable with smallest remaining domain (MCV heuristic)."""
    unassigned = [v for v in problem.variables if not v.is_assigned]
    return min(unassigned, key=lambda v: len(v.domain))
```

---

## Part 5: Parallel Constrained Decoding Architecture

### 5.1 High-Level Design

**Goal**: Fill multiple typed holes in parallel while respecting cross-hole constraints.

**Architecture**:
```
┌─────────────────────────────────────────────────────┐
│         IntermediateRepresentation (IR)             │
│  ┌─────────────────────────────────────────────┐   │
│  │ Typed Holes: [hole_1, hole_2, ..., hole_n] │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│       Constraint Graph Builder                      │
│  - Extract holes and dependencies                   │
│  - Build directed graph of constraints              │
│  - Identify independent vs dependent holes          │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│       Hole Dependency Analyzer                      │
│  - Topological sort (if acyclic)                    │
│  - Detect strongly connected components (cycles)    │
│  - Determine generation order                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│    Parallel Constrained Generator (GenCP-style)     │
│  ┌───────────────────────────────────────────┐     │
│  │  For each independent hole (parallel):     │     │
│  │    1. GenD: Generate domain with LLM      │     │
│  │    2. Filter by hole constraints          │     │
│  │    3. Return candidates                   │     │
│  └───────────────────────────────────────────┘     │
│  ┌───────────────────────────────────────────┐     │
│  │  For each dependent hole (sequential):     │     │
│  │    1. Get assignments from dependencies   │     │
│  │    2. Propagate constraints (AC-3)        │     │
│  │    3. GenD with updated constraints       │     │
│  │    4. Forward check remaining holes       │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│         Solution Validator                          │
│  - Check all constraints satisfied                  │
│  - Verify type consistency                          │
│  - Run assertions if applicable                     │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│      Complete IR (all holes filled)                 │
└─────────────────────────────────────────────────────┘
```

### 5.2 Implementation Components

**File**: `lift_sys/constraint_solver/hole_csp.py`

```python
"""Constraint satisfaction solver for typed holes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from ..ir.models import IntermediateRepresentation, TypedHole
from ..providers.base import BaseProvider


@dataclass
class Constraint:
    """Constraint between typed holes."""

    source: str  # Source hole identifier
    target: str  # Target hole identifier
    predicate: str  # Constraint expression
    metadata: dict[str, Any] = field(default_factory=dict)

    def check(self, source_value: Any, target_value: Any) -> bool:
        """Check if values satisfy constraint."""
        # Eval constraint predicate with values
        # e.g., "source == 'int' implies target in ['int', 'bool']"
        namespace = {
            'source': source_value,
            'target': target_value,
            **self.metadata
        }
        try:
            return eval(self.predicate, namespace)
        except:
            return False


@dataclass
class HoleVariable:
    """CSP variable for a typed hole."""

    hole: TypedHole
    domain: list[Any] = field(default_factory=list)
    assignment: Any | None = None

    @property
    def is_assigned(self) -> bool:
        return self.assignment is not None

    def assign(self, value: Any) -> None:
        self.assignment = value

    def unassign(self) -> None:
        self.assignment = None


class HoleCSP:
    """Constraint Satisfaction Problem for typed holes."""

    def __init__(self, ir: IntermediateRepresentation):
        self.ir = ir
        self.variables: dict[str, HoleVariable] = {}
        self.constraints: list[Constraint] = []
        self.constraint_graph = nx.DiGraph()

        # Build CSP from IR
        self._build_variables()
        self._build_constraints()

    def _build_variables(self) -> None:
        """Create CSP variable for each typed hole."""
        for hole in self.ir.typed_holes():
            var = HoleVariable(hole=hole)
            self.variables[hole.identifier] = var
            self.constraint_graph.add_node(hole.identifier)

    def _build_constraints(self) -> None:
        """Extract constraints from hole metadata."""
        for hole in self.ir.typed_holes():
            # Check for dependency constraints
            if "depends_on" in hole.constraints:
                deps = hole.constraints["depends_on"]
                if isinstance(deps, str):
                    deps = [deps]

                for dep in deps:
                    constraint = Constraint(
                        source=dep,
                        target=hole.identifier,
                        predicate=hole.constraints.get("rule", "True"),
                        metadata=hole.constraints
                    )
                    self.constraints.append(constraint)
                    self.constraint_graph.add_edge(dep, hole.identifier)

    def get_independent_holes(self) -> list[str]:
        """Return holes with no dependencies (can be generated in parallel)."""
        return [
            node for node in self.constraint_graph.nodes()
            if self.constraint_graph.in_degree(node) == 0
        ]

    def get_generation_order(self) -> list[str]:
        """Return topological order for hole generation."""
        try:
            return list(nx.topological_sort(self.constraint_graph))
        except nx.NetworkXError:
            # Graph has cycles - use approximation
            return list(self.constraint_graph.nodes())

    def get_dependent_holes(self, hole_id: str) -> list[str]:
        """Return holes that depend on given hole."""
        return list(self.constraint_graph.successors(hole_id))

    def forward_check(
        self,
        assigned_hole: str,
        assigned_value: Any
    ) -> bool:
        """
        Propagate assignment to dependent holes.

        Returns:
            True if still feasible, False if domain wipeout
        """
        for dep_hole_id in self.get_dependent_holes(assigned_hole):
            dep_var = self.variables[dep_hole_id]

            # Find constraints between assigned_hole and dep_hole
            relevant_constraints = [
                c for c in self.constraints
                if c.source == assigned_hole and c.target == dep_hole_id
            ]

            # Filter domain
            new_domain = []
            for value in dep_var.domain:
                if all(c.check(assigned_value, value) for c in relevant_constraints):
                    new_domain.append(value)

            dep_var.domain = new_domain

            # Check for domain wipeout
            if len(dep_var.domain) == 0:
                return False

        return True


class ParallelHoleSolver:
    """Solves typed holes using parallel constrained generation."""

    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def solve(
        self,
        ir: IntermediateRepresentation
    ) -> IntermediateRepresentation:
        """
        Fill all typed holes in IR using constraint propagation.

        Args:
            ir: IR with typed holes

        Returns:
            IR with all holes filled
        """
        # Build CSP
        csp = HoleCSP(ir)

        # Get generation order
        gen_order = csp.get_generation_order()

        # Solve using backtracking with constraint propagation
        assignment = await self._backtrack_solve(csp, gen_order)

        if assignment is None:
            raise ValueError("No solution found for typed holes")

        # Apply assignments to IR
        return self._apply_assignment(ir, assignment)

    async def _backtrack_solve(
        self,
        csp: HoleCSP,
        gen_order: list[str],
        assignment: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Backtracking search with constraint propagation."""
        if assignment is None:
            assignment = {}

        # Base case: all holes assigned
        if len(assignment) == len(csp.variables):
            return assignment

        # Get next unassigned hole (follow generation order)
        current_hole_id = None
        for hole_id in gen_order:
            if hole_id not in assignment:
                current_hole_id = hole_id
                break

        if current_hole_id is None:
            return assignment

        hole_var = csp.variables[current_hole_id]

        # Generate domain for this hole
        domain = await self._generate_domain(hole_var, assignment, csp)

        # Try each value
        for value in domain:
            # Assign value
            assignment[current_hole_id] = value
            hole_var.assign(value)

            # Forward check
            if csp.forward_check(current_hole_id, value):
                # Recurse
                result = await self._backtrack_solve(csp, gen_order, assignment)
                if result is not None:
                    return result

            # Backtrack
            del assignment[current_hole_id]
            hole_var.unassign()

        return None

    async def _generate_domain(
        self,
        hole_var: HoleVariable,
        assignment: dict[str, Any],
        csp: HoleCSP
    ) -> list[Any]:
        """
        Generate domain for hole using LLM with constrained decoding.

        This is the GenD procedure from GenCP.
        """
        hole = hole_var.hole

        # Build context from current assignment
        context = self._build_context(hole, assignment, csp)

        # Check if hole has explicit domain constraint
        if "domain" in hole.constraints:
            return hole.constraints["domain"]

        # Use LLM to generate candidates
        # If provider supports structured output (llguidance), use it
        if hasattr(self.provider, 'generate_structured'):
            # Build grammar from type_hint and constraints
            grammar = self._build_grammar(hole)

            candidates = await self.provider.generate_structured(
                prompt=context,
                schema=grammar,
                max_tokens=100,
                temperature=0.7
            )
        else:
            # Fallback: generate text and parse
            response = await self.provider.generate_text(
                prompt=context,
                max_tokens=100,
                temperature=0.7
            )
            candidates = self._parse_candidates(response, hole.type_hint)

        return candidates[:10]  # Return top 10 candidates

    def _build_context(
        self,
        hole: TypedHole,
        assignment: dict[str, Any],
        csp: HoleCSP
    ) -> str:
        """Build prompt context for hole generation."""
        context_parts = [
            f"Generate value for typed hole: {hole.identifier}",
            f"Type: {hole.type_hint}",
            f"Description: {hole.description}",
        ]

        # Add constraint information
        if hole.constraints:
            context_parts.append("Constraints:")
            for key, value in hole.constraints.items():
                if key not in ["depends_on", "domain", "rule"]:
                    context_parts.append(f"  - {key}: {value}")

        # Add current assignments for dependent holes
        for dep_id in hole.constraints.get("depends_on", []):
            if dep_id in assignment:
                context_parts.append(f"Given: {dep_id} = {assignment[dep_id]}")

        return "\n".join(context_parts)

    def _build_grammar(self, hole: TypedHole) -> dict:
        """Build JSON schema grammar for hole based on type_hint."""
        # Map Python type hints to JSON schema
        type_map = {
            "str": {"type": "string"},
            "int": {"type": "integer"},
            "float": {"type": "number"},
            "bool": {"type": "boolean"},
            "list": {"type": "array"},
            "dict": {"type": "object"},
        }

        base_type = hole.type_hint
        if base_type in type_map:
            schema = type_map[base_type]
        else:
            schema = {"type": "string"}  # Default

        # Add additional constraints from hole.constraints
        if "pattern" in hole.constraints:
            schema["pattern"] = hole.constraints["pattern"]
        if "enum" in hole.constraints:
            schema["enum"] = hole.constraints["enum"]
        if "minimum" in hole.constraints:
            schema["minimum"] = hole.constraints["minimum"]
        if "maximum" in hole.constraints:
            schema["maximum"] = hole.constraints["maximum"]

        return schema

    def _parse_candidates(
        self,
        response: str,
        type_hint: str
    ) -> list[Any]:
        """Parse LLM response into candidate values."""
        # Simple parsing - would need more sophistication in practice
        lines = response.strip().split("\n")
        candidates = []

        for line in lines[:10]:  # Top 10
            line = line.strip()
            if not line:
                continue

            # Try to parse based on type_hint
            try:
                if type_hint == "int":
                    candidates.append(int(line))
                elif type_hint == "float":
                    candidates.append(float(line))
                elif type_hint == "bool":
                    candidates.append(line.lower() in ["true", "yes", "1"])
                else:
                    candidates.append(line)
            except:
                continue

        return candidates

    def _apply_assignment(
        self,
        ir: IntermediateRepresentation,
        assignment: dict[str, Any]
    ) -> IntermediateRepresentation:
        """Apply hole assignments to IR."""
        # This would need sophisticated logic to replace holes
        # with assigned values throughout the IR structure

        # For now, just clear holes and assume values are used
        ir.intent.holes = []
        ir.signature.holes = []
        for effect in ir.effects:
            effect.holes = []
        for assertion in ir.assertions:
            assertion.holes = []

        return ir


__all__ = ["HoleCSP", "ParallelHoleSolver", "Constraint", "HoleVariable"]
```

---

## Part 6: Integration with lift-sys

### 6.1 Enhanced IR Translator

**File**: `lift_sys/forward_mode/constrained_ir_translator.py`

```python
"""IR translator with constraint-aware hole solving."""

from __future__ import annotations

from ..constraint_solver.hole_csp import ParallelHoleSolver
from ..ir.models import IntermediateRepresentation
from ..providers.base import BaseProvider
from .xgrammar_ir_translator import XGrammarIRTranslator


class ConstrainedIRTranslator(XGrammarIRTranslator):
    """
    IR translator that uses constraint propagation for typed holes.

    Extends XGrammarIRTranslator with CSP-based hole solving.
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(provider)
        self.hole_solver = ParallelHoleSolver(provider)

    async def translate(
        self,
        prompt: str,
        language: str = "python",
        max_retries: int = 3
    ) -> IntermediateRepresentation:
        """
        Translate natural language to IR with constraint-aware hole solving.

        Process:
        1. Generate initial IR (may contain typed holes)
        2. If holes present, solve using CSP approach
        3. Validate complete IR
        4. Return filled IR
        """
        # Generate initial IR (may have holes)
        ir = await super().translate(prompt, language, max_retries)

        # Check for typed holes
        holes = ir.typed_holes()
        if not holes:
            return ir  # No holes to solve

        print(f"\n🧩 Found {len(holes)} typed holes, solving with CSP...")

        # Solve holes using constraint propagation
        try:
            solved_ir = await self.hole_solver.solve(ir)
            print(f"✓ Successfully filled all typed holes")
            return solved_ir
        except ValueError as e:
            print(f"✗ Failed to solve typed holes: {e}")
            # Fall back to clearing holes (current behavior)
            ir.intent.holes = []
            ir.signature.holes = []
            for effect in ir.effects:
                effect.holes = []
            for assertion in ir.assertions:
                assertion.holes = []
            return ir


__all__ = ["ConstrainedIRTranslator"]
```

### 6.2 Usage Example

```python
from lift_sys.providers.modal_provider import ModalProvider
from lift_sys.forward_mode.constrained_ir_translator import ConstrainedIRTranslator

# Initialize provider with llguidance support
provider = ModalProvider(
    endpoint_url="https://rand--generate.modal.run",
    capabilities={"structured_output": True}  # Enable llguidance
)
await provider.initialize({})

# Create translator with CSP hole solver
translator = ConstrainedIRTranslator(provider)

# Translate with typed holes
prompt = """
Create a function that validates user input.
The function should check if the input is of the expected type.
If valid, return a success message. If invalid, return an error.
"""

ir = await translator.translate(prompt)

# Result: IR with all typed holes filled via constraint propagation
print(ir.to_dict())
```

---

## Part 7: Benefits and Trade-offs

### Benefits

1. **Systematic hole filling**: No more manual hole clearing
2. **Constraint awareness**: Holes filled with respect to dependencies
3. **Parallel generation**: Independent holes generated simultaneously
4. **Type safety**: Constraints enforced during generation
5. **Backtracking**: Can explore multiple solutions if first fails
6. **Extensible**: Easy to add new constraint types

### Trade-offs

1. **Complexity**: More sophisticated than current approach
2. **Latency**: CSP solving adds overhead (though parallelism helps)
3. **LLM calls**: More API calls for domain generation
4. **Memory**: Maintaining constraint graph and domains
5. **Debugging**: Harder to debug constraint propagation failures

### Cost Analysis

**Current approach** (clearing holes):
- 1 LLM call per IR generation
- Fast (no constraint solving)
- But: Holes not systematically filled

**CSP approach** (this proposal):
- 1 LLM call for initial IR
- N LLM calls for hole domain generation (N = number of holes)
- Parallel: Can batch independent holes
- Cost multiplier: ~2-3x (depending on holes per IR)

**Example**:
- IR with 3 typed holes
- 2 independent (parallel batch call)
- 1 dependent (sequential call)
- Total calls: 1 (IR) + 1 (batch) + 1 (dep) = 3 calls
- Latency: ~2x (vs clearing holes)
- Cost: ~3x (vs clearing holes)

**ROI**: Worth it if systematic hole filling improves downstream quality

---

## Part 8: Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Tasks**:
- [ ] Implement `HoleCSP` class
- [ ] Implement constraint graph builder
- [ ] Implement `forward_check()` and basic constraint propagation
- [ ] Unit tests for constraint checking

**Deliverable**: Working CSP representation of typed holes

### Phase 2: Domain Generation (Week 2)

**Tasks**:
- [ ] Integrate llguidance with Modal provider
- [ ] Implement `_generate_domain()` with LLM
- [ ] Implement grammar building from `TypedHole`
- [ ] Test domain generation for various hole types

**Deliverable**: LLM-based domain generation with llguidance

### Phase 3: Solver (Week 3)

**Tasks**:
- [ ] Implement `ParallelHoleSolver`
- [ ] Implement backtracking search
- [ ] Add parallel generation for independent holes
- [ ] Integration tests with real IRs

**Deliverable**: End-to-end hole solver

### Phase 4: Integration (Week 4)

**Tasks**:
- [ ] Create `ConstrainedIRTranslator`
- [ ] Update Modal provider for llguidance support
- [ ] Benchmark against current approach
- [ ] Documentation and examples

**Deliverable**: Production-ready constraint-aware IR translator

### Phase 5: Optimization (Week 5)

**Tasks**:
- [ ] Profile and optimize hot paths
- [ ] Implement caching for repeated holes
- [ ] Add heuristics for hole ordering
- [ ] A/B test against baseline

**Deliverable**: Optimized system with performance metrics

**Total effort**: 4-6 weeks (part-time)

---

## Part 9: Alternative: Lightweight Approach

If full CSP is too complex, consider a **lightweight constraint propagation**:

### Simplified Design

```python
class SimpleHoleFiller:
    """Lightweight hole filler with basic constraint awareness."""

    async def fill_holes(
        self,
        ir: IntermediateRepresentation
    ) -> IntermediateRepresentation:
        """Fill holes using simple topological ordering."""
        holes = ir.typed_holes()

        # Build dependency graph (no CSP)
        dep_graph = self._build_dependency_graph(holes)

        # Topological sort
        order = nx.topological_sort(dep_graph)

        # Fill in order (no backtracking)
        assignments = {}
        for hole in order:
            # Generate value with context from previous assignments
            value = await self._generate_value(hole, assignments)
            assignments[hole.identifier] = value

        # Apply assignments
        return self._apply_assignments(ir, assignments)
```

**Pros**:
- Simple to implement (~1 week)
- Still handles dependencies
- Lower overhead

**Cons**:
- No backtracking (may fail on hard constraints)
- No parallel generation
- Less robust than full CSP

**Recommendation**: Start with this, upgrade to full CSP if needed

---

## Conclusion

Your sudoku analogy is **spot on**! Typed holes with constraints are exactly like CSP variables, and the research shows this is a viable approach:

1. **Type-constrained code generation** (arXiv 2504.09246): Proves typed holes + constraint enforcement works
2. **GenCP** (arXiv 2407.13490): Shows how to combine LLM + CSP for 100% constraint satisfaction
3. **llguidance**: Provides fast infrastructure for constraint enforcement

**Recommended path**:
1. Start with **lightweight approach** (simple topological fill)
2. If successful, upgrade to **full CSP with backtracking**
3. Use **llguidance for fast constrained decoding**
4. Enable **parallel generation for independent holes**

**Expected outcome**: Systematic, constraint-aware hole filling that treats IR generation as a structured CSP rather than ad-hoc text generation.

This aligns perfectly with lift-sys's vision of formal, verifiable IR!

---

**Next steps**: Review this design, discuss trade-offs, and decide whether to prototype the lightweight or full CSP approach first.
