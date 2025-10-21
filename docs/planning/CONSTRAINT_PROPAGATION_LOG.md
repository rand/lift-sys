# Constraint Propagation Log

**Date**: 2025-10-20
**Status**: ACTIVE
**Version**: 1.0

---

## Purpose

This document tracks constraint propagation events as holes are resolved. Each resolution may add new constraints to dependent holes, narrow their solution spaces, or discover previously unknown dependencies.

---

## Propagation Event Template

```markdown
## Event {N}: {Date}
**Hole Resolved**: H{N} - {HoleName}
**Resolution Summary**: {Brief description}

### Constraints Propagated

#### To H{M}: {DependentHole}
**New Constraint**: {Description}
**Reasoning**: {Why this constraint follows from the resolution}
**Impact**: {How this narrows the solution space}

#### To H{K}: {AnotherDependentHole}
**New Constraint**: {Description}
**Reasoning**: {Why this constraint follows from the resolution}
**Impact**: {How this narrows the solution space}

### Discovered Dependencies
- {HoleID}: {Newly discovered dependency}

### Updated Solution Spaces
| Hole | Before | After | Reduction |
|------|--------|-------|-----------|
| H{M} | {N possibilities} | {M possibilities} | {%} |
```

---

## Event Log

### Event 0: Initial State (2025-10-20)
**Hole Resolved**: NONE (baseline)
**Resolution Summary**: Cataloged all 19 holes with initial constraints

**Initial Constraint Set**:
- All implementations must preserve XGrammar functionality
- All interfaces must be type-safe (mypy --strict)
- All must fit within Modal resource limits
- All must maintain backward compatibility during migration

**Next Events**: Will be added as holes are resolved

---

## Propagation Rules

### Rule 1: Interface Resolution → Type Constraints
When an interface hole is resolved with concrete types, propagate type requirements to all consumers.

**Example**:
```
Resolve H6: NodeSignatureInterface
  → Type: BaseNode with async run(RunContext) -> NextNode | End
Propagates to:
  → H4: Parallel execution must handle Union[NextNode, End]
  → H5: Error recovery must handle End nodes
  → H1: Provider must support async calls
```

### Rule 2: Implementation Resolution → Performance Constraints
When an implementation hole is resolved with specific resource usage, propagate resource limits to dependent holes.

**Example**:
```
Resolve H4: Parallelization with max_concurrent=3
  → Resource: 3 concurrent LLM calls maximum
Propagates to:
  → H16: Rate limit = provider_limit / 3
  → H14: Memory budget = 3 * single_node_memory
  → H3: Cache must handle 3 concurrent writes
```

### Rule 3: Validation Resolution → Test Requirements
When a validation hole is resolved with test requirements, propagate data requirements to upstream holes.

**Example**:
```
Resolve H17: Optimization needs 50 test examples
  → Data: Collect 50 labeled (prompt, IR, code) examples
Propagates to:
  → H10: Metrics must support batch evaluation
  → H8: Optimization API must accept example batches
```

### Rule 4: Constraint Resolution → Limits Propagation
When a constraint hole is resolved with specific limits, propagate to all affected holes.

**Example**:
```
Resolve H14: ResourceLimits (max_memory=2GB, max_concurrent=3)
Propagates to:
  → H16: ConcurrencyModel ≤ 3
  → H4: Parallelization ≤ 3 nodes
  → H3: Cache size ≤ 500MB (leaves 1.5GB for execution)
```

---

## Constraint Composition

When multiple constraints apply to the same hole:

### Conjunction (AND)
```
H1: ProviderAdapter
  ← From H6: Must support async
  ← From H10: Must preserve XGrammar
  ← From H14: Must fit in memory budget

Combined: Must support async AND preserve XGrammar AND fit in memory
```

### Implication (THEN)
```
If H6 resolves to "BaseNode with signature field"
Then H1 must "initialize DSPy with signature"
Then H2 must "serialize signature metadata"
```

### Conflict Detection
```
If H4 requires "max_concurrent ≥ 5"
And H14 limits "max_concurrent ≤ 3"
Then CONFLICT → Must resolve (adjust H4 or H14)
```

---

## Example Propagation Chain

### Scenario: Resolving H6 (NodeSignatureInterface)

**Resolution**:
```python
class BaseNode(Generic[StateT]):
    signature: Type[dspy.Signature]

    async def run(self, ctx: RunContext[StateT]) -> NextNode | End:
        result = await dspy.ChainOfThought(self.signature)(
            **self.extract_inputs(ctx.state)
        )
        self.update_state(ctx.state, result)
        return self.next_node(ctx.state)
```

**Propagation Tree**:
```
H6 Resolution
  ├── Type Constraint: "signature: Type[dspy.Signature]"
  │   ├→ H1: Must initialize DSPy with signature types
  │   ├→ H2: Must serialize Type[dspy.Signature] to JSONB
  │   └→ H10: Metrics must handle signature outputs
  │
  ├── Async Constraint: "async def run(...)"
  │   ├→ H1: Provider must support async calls
  │   ├→ H4: Parallel executor must use asyncio
  │   └→ H5: Error handler must be async-aware
  │
  ├── Generic Constraint: "Generic[StateT]"
  │   ├→ H2: Must serialize generic types
  │   └→ H4: Parallel executor must preserve generics
  │
  └── Return Type Constraint: "NextNode | End"
      ├→ H4: Parallel executor must handle Union types
      └→ H5: Error handler must understand End nodes
```

**Quantified Impact**:
| Dependent Hole | Solution Space Before | Solution Space After | Reduction |
|----------------|----------------------|---------------------|-----------|
| H1 | Any provider wrapper | Must support async DSPy | 60% |
| H2 | Any serialization | Must handle Type[Signature] | 40% |
| H4 | Any parallel model | Must use asyncio.gather | 70% |
| H5 | Any error handling | Must handle Union[NextNode, End] | 50% |

---

## Monitoring Propagation Quality

### Metrics

**Constraint Coverage**:
```
Coverage = (Holes with added constraints) / (Total dependent holes)
Target: >80%
```

**Solution Space Reduction**:
```
Reduction = Average % reduction in solution space across all holes
Target: >50% by end of Phase 3
```

**Conflict Rate**:
```
Conflicts = (Contradictory constraints) / (Total constraints)
Target: <5%
```

### Alerts

**High Constraint Density**: If a single hole adds >5 constraints, review for over-specification

**Low Propagation**: If resolving a hole propagates <2 constraints, check for missing dependencies

**Circular Constraints**: If A → B → C → A, detect and break cycle

---

## Next Steps

As each hole is resolved:

1. **Document the resolution** in this log
2. **Identify all dependent holes**
3. **Compute new constraints** using propagation rules
4. **Update HOLE_INVENTORY.md** with new constraints
5. **Check for conflicts** and resolve if found
6. **Measure solution space reduction**

---

**Document Status**: ACTIVE - Update after each hole resolution
**Owner**: Architecture team
**Last Updated**: 2025-10-20
