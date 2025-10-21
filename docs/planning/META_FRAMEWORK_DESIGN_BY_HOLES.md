# Meta-Framework: Design by Typed Holes

**Date**: 2025-10-20
**Status**: ACTIVE
**Version**: 1.0

---

## Executive Summary

This document describes the **meta-framework** for iteratively refining the DSPy + Pydantic AI architecture proposal using the same typed holes and constraint propagation system that we're designing.

**Core Insight**: Treat the architecture proposal itself as an Intermediate Representation (IR) with typed holes, then systematically resolve those holes while propagating constraints.

---

## The Proposal as an IR

### Viewing the Architecture Through the IR Lens

```python
ProposalIR = {
    "intent": {
        "summary": "Re-architect lift-sys with DSPy + Pydantic AI",
        "success_criteria": [
            "85% forward mode success rate",
            "Optimizable pipelines via MIPROv2",
            "Parallel execution with graphs",
            "Type-safe end-to-end"
        ]
    },
    "signature": {
        "components": [
            "DSPy Signature Layer",
            "Pydantic AI Graph Layer",
            "IR Core",
            "Execution Layer"
        ],
        "interfaces": [
            "?NodeSignatureInterface",  # HOLE
            "?GraphStateProtocol",      # HOLE
            "?OptimizationAPI"          # HOLE
        ]
    },
    "typed_holes": [
        # See HOLE_INVENTORY.md for complete catalog
        "?H1 - ?H19"
    ],
    "constraints": [
        "Must preserve XGrammar functionality",
        "Must maintain backward compatibility",
        "Must fit within Modal resource limits",
        "Must be type-safe end-to-end"
    ]
}
```

---

## Hole-Driven Development Process

### Phase Structure

Each phase follows this pattern:

```
1. Select Holes (based on dependency graph)
   ↓
2. For each hole:
   a. Generate candidate resolutions
   b. Evaluate against constraints
   c. Prototype best candidate
   d. Validate with tests
   ↓
3. Propagate Constraints
   - Update dependent hole contexts
   - Narrow solution spaces
   - Discover new constraints
   ↓
4. Gate Validation
   - Check phase completion criteria
   - Run integration tests
   - Document resolutions
   ↓
5. Proceed to Next Phase (or backtrack if validation fails)
```

### Constraint Propagation Rules

#### Rule 1: Interface Resolution → Type Constraints
```
When: Interface hole resolved with concrete types
Then: Propagate type requirements to all consumers

Example:
  Resolve H6: NodeSignatureInterface
    → Type: BaseNode with async run(RunContext) -> NextNode | End
  Propagates to:
    → H4: Parallel execution must handle Union[NextNode, End]
    → H5: Error recovery must handle End nodes
```

#### Rule 2: Implementation Resolution → Performance Constraints
```
When: Implementation hole resolved with resource usage
Then: Propagate resource limits to dependent holes

Example:
  Resolve H4: Parallelization with max_concurrent=3
    → Resource: 3 concurrent LLM calls maximum
  Propagates to:
    → H16: Rate limit = provider_limit / 3
    → H14: Memory budget = 3 * single_node_memory
    → H3: Cache must handle 3 concurrent writes
```

#### Rule 3: Validation Resolution → Test Requirements
```
When: Validation hole resolved with test requirements
Then: Propagate data requirements to upstream holes

Example:
  Resolve H17: Optimization needs 50 test examples
    → Data: Collect 50 labeled (prompt, IR, code) examples
  Propagates to:
    → H10: Metrics must support batch evaluation
    → H8: Optimization API must accept example batches
```

---

## Iterative Refinement Timeline

### Phase 0: Hole Detection (Complete)
- ✅ Catalog all holes
- ✅ Establish dependencies
- ✅ Identify critical path
- **Deliverable**: Hole inventory (see `HOLE_INVENTORY.md`)

### Phase 1: Foundation Holes (Week 1)
**Focus**: Blocking interface holes

**Holes to Resolve**:
- H6: NodeSignatureInterface
- H9: ValidationHooks
- H14: ResourceLimits

**Validation Gate**:
- [ ] Prototype node executes with DSPy signature
- [ ] Type checker validates interface
- [ ] Resource limits documented

**Beads**: `lift-sys-300`, `lift-sys-301`, `lift-sys-302`

### Phase 2: Execution Holes (Week 2)
**Focus**: Provider integration and persistence

**Holes to Resolve**:
- H1: ProviderAdapter
- H2: StatePersistence
- H11: ExecutionHistorySchema

**Validation Gate**:
- [ ] Graph executes end-to-end
- [ ] State persists and resumes
- [ ] XGrammar preserved through DSPy

**Beads**: `lift-sys-303`, `lift-sys-304`, `lift-sys-305`

### Phase 3: Optimization Holes (Week 3)
**Focus**: Metrics and optimization API

**Holes to Resolve**:
- H10: OptimizationMetrics
- H8: OptimizationAPI
- H12: ConfidenceCalibration

**Validation Gate**:
- [ ] Metrics computed on 20 examples
- [ ] MIPROv2 runs successfully
- [ ] Optimization improves scores

**Beads**: `lift-sys-306`, `lift-sys-307`, `lift-sys-308`

### Phase 4: Parallelization Holes (Week 4)
**Focus**: Concurrent execution

**Holes to Resolve**:
- H4: ParallelizationImpl
- H16: ConcurrencyModel
- H18: ConcurrencyValidation

**Validation Gate**:
- [ ] Parallel nodes execute correctly
- [ ] No race conditions (100 test runs)
- [ ] Speedup ≥2x measured

**Beads**: `lift-sys-309`, `lift-sys-310`, `lift-sys-311`

### Phase 5: Caching and Performance (Week 5)
**Focus**: Optimization

**Holes to Resolve**:
- H3: CachingStrategy
- H7: TraceVisualizationProtocol

**Validation Gate**:
- [ ] Cache hit rate >60%
- [ ] Deterministic cache invalidation
- [ ] Trace data accessible to UI

**Beads**: `lift-sys-312`, `lift-sys-313`

### Phase 6: Migration and Validation (Week 6)
**Focus**: Production readiness

**Holes to Resolve**:
- H15: MigrationConstraints
- H13: FeatureFlagSchema
- H19: BackwardCompatTest

**Validation Gate**:
- [ ] 100 sessions migrated successfully
- [ ] Feature flags operational
- [ ] Rollback tested

**Beads**: `lift-sys-314`, `lift-sys-315`, `lift-sys-316`

### Phase 7: Final Validation (Week 7)
**Focus**: Closing remaining holes

**Holes to Resolve**:
- H17: OptimizationValidation
- H5: ErrorRecovery

**Validation Gate**:
- [ ] Statistical significance (p < 0.05)
- [ ] Error recovery tested
- [ ] All gates passed

**Beads**: `lift-sys-317`, `lift-sys-318`

---

## Design Completeness Criteria

### Formal Completeness Check

A design is **complete** when:

```python
def design_is_complete(proposal_ir: ProposalIR) -> bool:
    checks = {
        "no_unresolved_holes": all(
            hole.status == "resolved"
            for hole in proposal_ir.typed_holes
        ),
        "constraints_satisfied": all(
            constraint.satisfiable
            for constraint in proposal_ir.constraints
        ),
        "interfaces_implemented": all(
            iface.implementation is not None
            for iface in proposal_ir.interfaces
        ),
        "critical_path_validated": all(
            hole.validated
            for hole in proposal_ir.dependency_graph.critical_path()
        ),
        "integration_tests_pass": proposal_ir.integration_tests.all_passing(),
        "gates_passed": all(
            phase.gate_passed
            for phase in proposal_ir.phases
        )
    }

    return all(checks.values())
```

### Measurable Gates

| Gate | Criteria | Status |
|------|----------|--------|
| Gate 1: Interface Completeness | All 9 interface holes resolved, type checker passes | ⏳ Pending |
| Gate 2: Execution Completeness | Full graph executes, state persists | ⏳ Pending |
| Gate 3: Optimization Completeness | Metrics validated, MIPROv2 runs | ⏳ Pending |
| Gate 4: Production Completeness | Migration tested, feature flags working | ⏳ Pending |

---

## Tracking and Tools

### Documents
- **This file**: Meta-framework overview
- `HOLE_INVENTORY.md`: Complete hole catalog with types and dependencies
- `CONSTRAINT_PROPAGATION_LOG.md`: Living log of constraint propagation events
- `PHASE_GATES_VALIDATION.md`: Detailed validation criteria per phase

### Scripts
- `scripts/planning/track_holes.py`: Manage hole status and dependencies
- `scripts/planning/validate_resolution.py`: Test if resolution satisfies constraints
- `scripts/planning/propagate_constraints.py`: Compute constraint propagation
- `scripts/planning/check_completeness.py`: Verify design completeness

### Beads
- Phase beads: `lift-sys-300` through `lift-sys-306` (one per phase)
- Hole beads: `lift-sys-307` through `lift-sys-325` (one per hole)

---

## Usage Guide

### Starting a Phase

```bash
# 1. Check which holes are ready to resolve
python scripts/planning/track_holes.py ready --phase 1

# 2. Review hole details
python scripts/planning/track_holes.py show H6

# 3. Claim hole in beads
bd update lift-sys-300 --status in_progress

# 4. Work on resolution...

# 5. Validate resolution
python scripts/planning/validate_resolution.py H6 \
  --prototype lift_sys/dspy_signatures/node_interface.py

# 6. If valid, propagate constraints
python scripts/planning/propagate_constraints.py H6 \
  --resolution "BaseNode with async run() -> NextNode | End"

# 7. Mark hole resolved
python scripts/planning/track_holes.py resolve H6 \
  --resolution-path lift_sys/dspy_signatures/node_interface.py

# 8. Close bead
bd close lift-sys-300 --reason "H6 resolved and validated"
```

### Checking Progress

```bash
# Overall completeness
python scripts/planning/check_completeness.py

# Phase status
python scripts/planning/track_holes.py phase-status 1

# Dependency graph visualization
python scripts/planning/track_holes.py visualize --output docs/planning/dependency_graph.png
```

---

## Key Principles

### 1. No Untyped Holes
Every hole must have:
- **Type annotation**: What kind of thing fills this hole?
- **Constraints**: What must be true of any resolution?
- **Dependencies**: What other holes does this depend on?
- **Blocking**: What does this hole block?

### 2. Validate Before Proceeding
Never move to the next hole without validating the current resolution:
- Write a prototype
- Run tests
- Check constraints
- Document decision

### 3. Propagate Immediately
When a hole is resolved:
- Update all dependent holes
- Narrow their solution spaces
- Discover new constraints
- Document propagation

### 4. Track Everything
Maintain audit trail:
- Why was this resolution chosen?
- What alternatives were considered?
- What constraints were propagated?
- What tests validated it?

### 5. Backtrack When Needed
If validation fails:
- Don't force it
- Try alternative resolution
- If no alternatives work, revisit dependencies
- Update constraints if needed

---

## Success Indicators

### Weekly Progress
Each week should show:
- ✅ 2-4 holes resolved
- ✅ Constraints propagated to dependent holes
- ✅ Phase gate criteria met
- ✅ Working prototype code
- ✅ Tests passing

### Red Flags
Stop and reassess if:
- ❌ Hole can't be resolved within constraints
- ❌ Validation fails repeatedly
- ❌ Constraints contradict each other
- ❌ Dependencies cycle
- ❌ No progress for >3 days

---

## Meta-Consistency

This framework practices what we preach:

| lift-sys Feature | Meta-Framework Application |
|------------------|---------------------------|
| Typed Holes | Architecture unknowns cataloged with types |
| Constraint Propagation | Design constraints flow through dependency graph |
| Iterative Refinement | Weekly resolution cycles |
| Validation | Gate criteria at each phase |
| Provenance | Track why each decision was made |
| SMT Checking | Constraint satisfaction validation |

**We're using the system to design the system.**

---

## Next Steps

1. **Review hole inventory**: `HOLE_INVENTORY.md`
2. **Start Phase 1**: Resolve H6, H9, H14
3. **Track progress**: Use scripts to monitor
4. **Validate gates**: Check phase completion
5. **Iterate**: Resolve → Validate → Propagate → Repeat

---

**Document Status**: ACTIVE - Updated as phases complete
**Owner**: Architecture team
**Last Updated**: 2025-10-20
