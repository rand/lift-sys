# Conjecturing Framework Implementation Plan
## Based on arXiv:2510.11986 Research

**Status**: Proposal - Awaiting approval to proceed
**Priority**: P1 (aligns with active investigation lift-sys-229)
**Effort**: 1 week (diagnostic) → 2-3 weeks (implementation) → 4-6 weeks (full system)
**Risk**: Low (starts with diagnostic enhancement)

---

## Phase 1: Diagnostic Enhancement (RECOMMENDED START)

**Duration**: 1 week
**Effort**: 8-12 hours
**Risk**: Low
**Prerequisites**: None (uses existing infrastructure)

### Goals

1. Add conjecturing-based metrics to current diagnostic investigation
2. Separate IR quality (conjecture) from codegen quality (formalisation)
3. Identify whether 3 failures are IR issues or codegen issues

### Tasks

#### Task 1.1: Enhance Diagnostic Collection Script

**File**: `debug/collect_failure_samples.py`

**Add conjecture evaluation**:
```python
def evaluate_ir_conjecture_quality(
    ir: IntermediateRepresentation,
    test_name: str
) -> dict:
    """Evaluate IR as conjecture (independent of codegen)."""
    return {
        # Constraint detection
        "constraints_count": len(ir.constraints),
        "constraint_types": [c.type.value for c in ir.constraints],

        # Expected constraints (manual ground truth)
        "expected_constraints": EXPECTED_CONSTRAINTS.get(test_name, []),
        "constraint_completeness": compute_completeness(
            ir.constraints, EXPECTED_CONSTRAINTS.get(test_name, [])
        ),

        # Typed holes
        "holes_present": len(ir.typed_holes()),
        "holes_filled": all(h.is_filled for h in ir.typed_holes()),

        # Semantic correctness (manual evaluation helper)
        "ir_summary": {
            "function_name": ir.signature.name,
            "return_type": ir.signature.returns,
            "effects": [e.kind.value for e in ir.effects]
        }
    }

# Ground truth for 3 failing tests
EXPECTED_CONSTRAINTS = {
    "count_words": [
        {"type": "RETURN", "value_name": "count"}
    ],
    "find_index": [
        {"type": "LOOP_BEHAVIOR", "search_type": "FIRST_MATCH", "requirement": "EARLY_RETURN"}
    ],
    "is_valid_email": [
        {"type": "POSITION", "elements": ["@", "."], "requirement": "NOT_ADJACENT"}
    ]
}
```

#### Task 1.2: Add Constraint Preservation Measurement

**File**: `debug/collect_failure_samples.py`

**Measure how well codegen honors IR constraints**:
```python
def evaluate_constraint_preservation(
    code: str,
    ir: IntermediateRepresentation
) -> dict:
    """Measure constraint preservation in generated code."""
    from lift_sys.ir.constraint_validator import ConstraintValidator

    validator = ConstraintValidator()
    violations = validator.validate_code(code, ir.constraints)

    return {
        "total_constraints": len(ir.constraints),
        "violations": len(violations),
        "preservation_rate": 1.0 - (len(violations) / max(len(ir.constraints), 1)),
        "violation_details": [
            {
                "constraint_type": v.constraint.type.value,
                "description": v.message,
                "severity": v.severity.value
            }
            for v in violations
        ]
    }
```

#### Task 1.3: Generate Diagnostic Report

**File**: `DIAGNOSTIC_REPORT_CONJECTURING.md` (output)

**Structure**:
```markdown
# Diagnostic Report: Conjecturing vs Formalisation Analysis

## Summary
- Test: count_words
- Samples: 12 (temperature 0.8)

## Conjecture Quality (IR)
- Constraint Completeness: 10/12 (83%) had correct ReturnConstraint
- 2/12 missing constraint entirely
- All 12 had correct function signature

## Formalisation Quality (Codegen)
- Constraint Preservation: 3/12 (25%) honored ReturnConstraint
- 9/12 generated code without return statement
- IR was correct, codegen failed to honor it

## Bottleneck Identification
✅ Conjecture (IR): 83% quality
❌ Formalisation (Code): 25% preservation

**Conclusion**: Problem is in formalisation, not conjecturing.
**Recommendation**: Focus on semantic validation or LLM repair, not two-phase IR.
```

#### Task 1.4: Analyze Results

**Run diagnostic for all 3 tests**:
```bash
# Collect samples with conjecture evaluation
python debug/collect_failure_samples.py --with-conjecturing

# Analyze results
python debug/analyze_conjecturing_bottleneck.py
```

**Output**: Decision matrix
```
If constraint_completeness > 80% AND preservation_rate < 50%:
    → Bottleneck is FORMALISATION (codegen)
    → Recommendation: Semantic validation (Option 2) or LLM repair (Option 4)

If constraint_completeness < 50% AND preservation_rate > 80%:
    → Bottleneck is CONJECTURING (IR)
    → Recommendation: Two-phase IR generation (Phase 2)

If both < 50%:
    → Systemic issues
    → Recommendation: Full conjecturing framework (Phase 3)
```

### Deliverables

1. ✅ Enhanced diagnostic script with conjecture metrics
2. ✅ Diagnostic report with bottleneck identification
3. ✅ Data-driven recommendation for next phase
4. ✅ Updated `STRATEGIC_ASSESSMENT` with findings

### Success Criteria

- [x] Clear separation of IR quality vs codegen quality
- [x] Bottleneck identified (conjecture OR formalisation)
- [x] Recommendation backed by data (>12 samples per test)
- [x] Decision made on whether to proceed to Phase 2

---

## Phase 2: Two-Phase IR Generation (IF PHASE 1 RECOMMENDS)

**Duration**: 2-3 weeks
**Effort**: 40-60 hours
**Risk**: Medium
**Prerequisites**: Phase 1 shows IR quality is bottleneck

### Goals

1. Separate IR skeleton generation from hole resolution
2. Implement constraint-guided conjecture generation
3. Validate conjectures before code generation
4. Measure improvement in IR quality and E2E success

### Architecture

```python
class ConjecturingIRTranslator:
    """
    Two-phase IR translator inspired by conjecturing framework.

    Phase 1: Generate IR skeleton with explicit typed holes
    Phase 2: Resolve holes using constraint-guided generation
    """

    async def translate(
        self,
        prompt: str,
        language: str = "python"
    ) -> IntermediateRepresentation:
        # Phase 1: Skeleton generation
        skeleton = await self._generate_skeleton(prompt, language)

        # Phase 2: Constraint detection
        constraints = await self._detect_constraints(prompt, skeleton)
        skeleton.constraints = constraints

        # Phase 3: Conjecture generation (hole resolution)
        complete_ir = await self._resolve_holes_with_constraints(
            skeleton, constraints
        )

        # Phase 4: Validate complete IR
        if not self._validate_ir_conjectures(complete_ir):
            raise ValueError("IR conjectures violate constraints")

        return complete_ir
```

### Tasks

#### Task 2.1: Implement Skeleton Generator

**File**: `lift_sys/forward_mode/conjecturing_translator.py`

**Prompt engineering**:
```python
SKELETON_GENERATION_PROMPT = """
Generate an IR skeleton for the following prompt.
Include typed holes (<?hole_name: type?>) for unknown values.

Prompt: {prompt}

Return IR in JSON format with typed holes for:
- Function name (if ambiguous)
- Parameter types (if not specified)
- Return type (if not clear)
- Implementation patterns (if multiple valid approaches)

Example:
{{
  "signature": {{
    "name": "<?hole_function_name: str?>",
    "parameters": [
      {{"name": "text", "type_hint": "<?hole_param_type: str?>"}}
    ],
    "returns": "<?hole_return_type: str?>"
  }}
}}
"""
```

#### Task 2.2: Implement Constraint-Guided Hole Resolution

**File**: `lift_sys/forward_mode/conjecture_generator.py`

```python
class ConjectureGenerator:
    """Generates conjectures for typed holes using constraints."""

    async def generate_conjecture(
        self,
        hole: TypedHole,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> Any:
        """Generate single conjecture for hole."""
        # Build context from skeleton
        context = self._build_conjecture_context(hole, skeleton)

        # Filter constraints relevant to this hole
        relevant_constraints = self._filter_relevant_constraints(
            hole, constraints
        )

        # Generate candidates
        candidates = await self._generate_candidates(
            hole, context, relevant_constraints
        )

        # Validate candidates against constraints
        valid = [
            c for c in candidates
            if self._validate_candidate(c, hole, relevant_constraints)
        ]

        if not valid:
            raise ValueError(f"No valid conjecture for {hole.identifier}")

        return valid[0]  # Return best candidate

    def _build_conjecture_context(
        self,
        hole: TypedHole,
        skeleton: IntermediateRepresentation
    ) -> str:
        """Build prompt context for conjecture generation."""
        return f"""
Generate value for typed hole: {hole.identifier}

Type: {hole.type_hint}
Description: {hole.description}

Context:
Function intent: {skeleton.intent.summary}
Current signature: {skeleton.signature}

Requirements:
{hole.constraints}
        """.strip()
```

#### Task 2.3: Add Conjecture Validation

**File**: `lift_sys/forward_mode/conjecture_validator.py`

```python
class ConjectureValidator:
    """Validates conjectures satisfy constraints."""

    def validate(
        self,
        ir: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> list[ConstraintViolation]:
        """Validate all conjectures in IR."""
        violations = []

        # Check each constraint
        for constraint in constraints:
            if not self._check_constraint(ir, constraint):
                violations.append(
                    ConstraintViolation(
                        constraint=constraint,
                        message=f"IR conjecture violates {constraint.type}",
                        severity=constraint.severity
                    )
                )

        return violations

    def _check_constraint(
        self,
        ir: IntermediateRepresentation,
        constraint: Constraint
    ) -> bool:
        """Check if IR satisfies constraint."""
        if isinstance(constraint, ReturnConstraint):
            return self._check_return_constraint(ir, constraint)
        elif isinstance(constraint, LoopBehaviorConstraint):
            return self._check_loop_constraint(ir, constraint)
        # ... other constraint types
```

#### Task 2.4: Integration and Testing

**Files**: `tests/forward_mode/test_conjecturing_translator.py`

**Tests**:
1. Skeleton generation produces typed holes
2. Constraint detection from prompt works
3. Conjecture generation fills holes
4. Validation catches invalid conjectures
5. E2E: prompt → complete IR (no holes)

**Metrics**:
```python
class ConjecturingMetrics:
    """Metrics for conjecturing-based IR generation."""

    def measure_conjecture_accuracy(
        self,
        ir: IntermediateRepresentation,
        ground_truth: dict
    ) -> float:
        """Measure semantic correctness of conjectures."""
        # Compare filled holes against expected values
        # Return 0.0-1.0 accuracy score

    def measure_constraint_completeness(
        self,
        detected: list[Constraint],
        expected: list[Constraint]
    ) -> float:
        """Measure constraint detection accuracy."""
        # Return percentage of expected constraints detected

    def measure_e2e_improvement(
        self,
        baseline_success: float,
        conjecturing_success: float
    ) -> float:
        """Measure improvement over baseline."""
        return conjecturing_success - baseline_success
```

### Deliverables

1. ✅ Working `ConjecturingIRTranslator`
2. ✅ Test suite with >90% coverage
3. ✅ Benchmark results vs current approach
4. ✅ Documentation and examples
5. ✅ Integration with existing pipeline

### Success Criteria

- [x] IR conjecture accuracy > 90%
- [x] E2E success rate improvement > 5% (from 83.3% to 88%+)
- [x] No regression in latency (within 20% of baseline)
- [x] All existing tests still pass

---

## Phase 3: Full CSP Integration (OPTIONAL - IF NEEDED)

**Duration**: 4-6 weeks
**Effort**: 120-180 hours
**Risk**: High
**Prerequisites**: Phase 2 successful but needs more sophistication

### Goals

1. Combine conjecturing framework with CSP approach
2. Handle complex hole dependencies systematically
3. Support backtracking and constraint propagation
4. Achieve >95% success rate

### Architecture

See `CONSTRAINT_PROPAGATION_TYPED_HOLES.md` for detailed CSP design.

**Integration with conjecturing**:
```python
class ConjecturingCSPTranslator:
    """
    Full conjecturing + CSP integration.

    Combines:
    - Conjecturing framework (skeleton + validation)
    - CSP solver (constraint propagation)
    - Existing constraint system (Phase 7)
    """

    async def translate(self, prompt: str) -> IntermediateRepresentation:
        # Conjecturing Phase 1: Generate skeleton
        skeleton = await self.conjecture_gen.generate_skeleton(prompt)

        # Conjecturing Phase 2: Detect constraints
        constraints = await self.constraint_detector.detect(prompt, skeleton)

        # CSP Phase 1: Build constraint satisfaction problem
        csp = self.csp_builder.build(skeleton, constraints)

        # CSP Phase 2: Solve with backtracking + propagation
        solution = await self.csp_solver.solve(csp)

        # Conjecturing Phase 3: Validate solution
        if not self.validator.validate(solution, constraints):
            raise ValueError("CSP solution invalid")

        # Apply solution to skeleton
        complete_ir = self.applicator.apply(skeleton, solution)

        return complete_ir
```

### Tasks

See `CONSTRAINT_PROPAGATION_IMPLEMENTATION_PLAN.md` for detailed task breakdown.

**Additional conjecturing-specific tasks**:
1. Conjecture quality scoring (select best CSP solution)
2. Iterative refinement with feedback
3. Conjecture caching (reuse known-good solutions)
4. Meta-learning (learn which conjectures work best)

### Deliverables

1. ✅ Complete ConjecturingCSP system
2. ✅ Comprehensive evaluation framework
3. ✅ Production deployment
4. ✅ Research paper/blog post documenting approach

### Success Criteria

- [x] E2E success rate > 95%
- [x] Handles complex dependencies (cyclic constraints)
- [x] Scalable to large IRs (100+ holes)
- [x] Production-ready (latency, cost, reliability)

---

## Decision Tree

```
START: Phase 1 Diagnostic
    ↓
Bottleneck = CONJECTURING (IR)?
    ↓
    YES → Proceed to Phase 2
        ↓
        Phase 2 improves E2E > 5%?
            ↓
            YES → Deploy Phase 2, consider Phase 3
            NO → Investigate why (maybe codegen is still bottleneck)
    ↓
    NO (Bottleneck = FORMALISATION)
        ↓
        Stop conjecturing work
        Pivot to semantic validation (Option 2) or LLM repair (Option 4)
```

---

## Risk Mitigation

### Risk 1: Paper concepts don't transfer to code

**Mitigation**: Phase 1 diagnostic validates applicability before implementation

### Risk 2: Increased latency kills UX

**Mitigation**: Parallel hole resolution, measure latency at each phase

### Risk 3: Cost increase not justified by improvement

**Mitigation**: Cost tracking, ROI analysis, can abort after Phase 1 or 2

### Risk 4: Complexity makes system harder to debug

**Mitigation**: Separate metrics for each phase, clear logging, comprehensive tests

---

## Resources Required

### Phase 1
- **Time**: 1 week (8-12 hours)
- **People**: 1 engineer
- **Infrastructure**: Existing (no new services)
- **Cost**: $0 (uses existing LLM budget)

### Phase 2
- **Time**: 2-3 weeks (40-60 hours)
- **People**: 1 engineer + occasional review
- **Infrastructure**: Existing (Modal, current providers)
- **Cost**: +20-30% LLM budget for development/testing

### Phase 3
- **Time**: 4-6 weeks (120-180 hours)
- **People**: 1-2 engineers
- **Infrastructure**: May need CSP solver libraries
- **Cost**: +50% LLM budget for development/testing

---

## Success Metrics

| Phase | Metric | Target | Measurement |
|-------|--------|--------|-------------|
| 1 | Bottleneck identified | Clear answer | Manual analysis |
| 1 | Constraint completeness | >80% | Automated |
| 1 | Preservation rate | Measured | Automated |
| 2 | IR conjecture accuracy | >90% | Automated |
| 2 | E2E improvement | >5% (88%+) | Automated |
| 2 | Latency overhead | <20% | Automated |
| 3 | E2E success rate | >95% | Automated |
| 3 | Complex dependencies | Supported | Manual test |

---

## Timeline

### Week 1: Diagnostic (Phase 1)
- Mon-Tue: Implement conjecture evaluation
- Wed-Thu: Collect samples and analyze
- Fri: Decision point (proceed to Phase 2 or pivot?)

### Weeks 2-4: Two-Phase IR (Phase 2, if approved)
- Week 2: Skeleton generator + conjecture generator
- Week 3: Validation + integration
- Week 4: Testing + benchmarking

### Weeks 5-10: Full CSP (Phase 3, if needed)
- Weeks 5-6: CSP builder + solver
- Weeks 7-8: Integration + testing
- Weeks 9-10: Optimization + deployment

---

## Go/No-Go Criteria

### After Phase 1:
**GO to Phase 2 if**:
- IR constraint completeness < 80% (conjecturing is bottleneck)
- Clear evidence that better IR would improve E2E
- Team has capacity for 2-3 week implementation

**NO-GO (pivot) if**:
- IR constraint completeness > 80% AND preservation < 50% (codegen is bottleneck)
- Other higher-priority issues identified
- Resource constraints

### After Phase 2:
**GO to Phase 3 if**:
- E2E improvement > 5% (proves value)
- Complex dependencies identified that need CSP
- Goal is >95% success rate
- Budget supports 4-6 week effort

**NO-GO (deploy Phase 2) if**:
- Marginal improvement (<5%)
- Phase 2 sufficient for current needs
- Other priorities higher

---

## Next Steps

1. ✅ Review this plan
2. ⏳ Get approval for Phase 1 diagnostic enhancement
3. ⏳ Implement Phase 1 (1 week)
4. ⏳ Decision meeting after Phase 1 results
5. ⏳ If approved: Begin Phase 2
6. ⏳ If not: Document findings, pivot to alternative approach

---

**Status**: Awaiting approval to begin Phase 1

**Owner**: TBD

**Reviewer**: TBD

**Target Start**: After approval

**First Milestone**: Phase 1 diagnostic report (1 week from start)
