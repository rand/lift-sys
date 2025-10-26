# Phase 7: IR-Level Constraints for Code Generation Quality

**Date**: October 17, 2025
**Status**: PLANNING
**Prerequisites**: Phase 6 complete at 83.3% (15/18 tests)
**Target**: 95%+ success rate with principled constraint approach
**Estimated Timeline**: 2-3 weeks

---

## Executive Summary

Phase 6 achieved 83.3% success rate using hybrid LLM + AST repair, but identified **pattern matching brittleness** as the root cause of remaining failures. Phase 7 moves to a principled approach: **IR-level constraints** that prevent bugs before code generation, rather than fixing them afterward.

### Key Insight from Phase 6

The 3 persistent failures (count_words, find_index, is_valid_email) result from:
- **LLM inconsistency**: Same prompt produces different code structures
- **Pattern brittleness**: AST repair requires exact structure matches
- **Lack of constraints**: IR doesn't explicitly constrain generation behavior

### Phase 7 Approach

Instead of chasing AST patterns, **add explicit constraints to IR** that:
1. Prevent bugs during generation (not after)
2. Work for ANY code structure (not specific patterns)
3. Scale maintainably (one constraint covers all variations)
4. Guide LLM generation with clear requirements

---

## Problem Analysis

### The 3 Persistent Failures

From Phase 6 analysis:

**1. count_words (missing return)**
- **Symptom**: Returns `None` instead of count value
- **IR Issue**: Effect describes "Count the number of elements" but doesn't require explicit return
- **Root Cause**: No constraint ensuring computed values are returned

**2. find_index (off-by-one / accumulation)**
- **Symptom**: Returns last match instead of first match
- **IR Issue**: Effect says "Find the first index" but doesn't constrain loop behavior
- **Root Cause**: No constraint requiring early return on first match

**3. is_valid_email (adjacency validation)**
- **Symptom**: Accepts `test@.com` (dot immediately after @)
- **IR Issue**: Effect validates @ and . exist but doesn't constrain their positions
- **Root Cause**: No constraint specifying "dot must NOT be immediately adjacent to @"

### Why AST Repair Failed

Phase 6 AST repair had 100% unit test pass rate, but failed in integration because:

```python
# Pass 6 expected this pattern:
if email.index('@') > email.rindex('.'):
    return False

# But LLM generated this instead:
at_index = email.index('@')
if '.' not in email[at_index + 1:]:
    return False
```

Both implement same logic, but different AST structures → pattern doesn't match.

**Lesson**: We can't match all possible code structures. Need to specify requirements at IR level.

---

## Phase 7 Architecture

### Constraint Types

Add three new IR constraint types:

#### 1. **Return Constraints** (count_words)

```python
{
  "type": "return_constraint",
  "value_name": "count",
  "requirement": "MUST_RETURN",
  "description": "Function must return the computed count value"
}
```

**Effect**: Ensures LLM generates explicit return statement for computed values.

#### 2. **Loop Behavior Constraints** (find_index)

```python
{
  "type": "loop_constraint",
  "search_type": "FIRST_MATCH",
  "requirement": "EARLY_RETURN",
  "description": "Loop must return immediately on first match (not continue to last)"
}
```

**Effect**: Guides LLM to generate early return pattern, not accumulation.

#### 3. **Position Constraints** (is_valid_email)

```python
{
  "type": "position_constraint",
  "elements": ["@", "."],
  "requirement": "NOT_ADJACENT",
  "min_distance": 1,
  "description": "Dot must be at least 2 characters after @"
}
```

**Effect**: Explicitly constrains relative positions of validation elements.

### IR Schema Extension

Extend `IntermediateRepresentation` model:

```python
@dataclass
class IntermediateRepresentation:
    # ... existing fields ...

    constraints: list[Constraint] = field(default_factory=list)
    """Explicit constraints on code generation behavior"""
```

```python
@dataclass
class Constraint:
    """Base constraint type"""
    type: str  # "return", "loop_behavior", "position", etc.
    severity: str = "error"  # "error", "warning"
    description: str = ""
```

```python
@dataclass
class ReturnConstraint(Constraint):
    type: str = "return_constraint"
    value_name: str  # Name of value that must be returned
    requirement: str = "MUST_RETURN"  # or "OPTIONAL_RETURN"
```

```python
@dataclass
class LoopBehaviorConstraint(Constraint):
    type: str = "loop_constraint"
    search_type: str  # "FIRST_MATCH", "LAST_MATCH", "ALL_MATCHES"
    requirement: str = "EARLY_RETURN"  # or "ACCUMULATE", "TRANSFORM"
```

```python
@dataclass
class PositionConstraint(Constraint):
    type: str = "position_constraint"
    elements: list[str]  # Elements to constrain (e.g., ["@", "."])
    requirement: str  # "NOT_ADJACENT", "ORDERED", "MIN_DISTANCE"
    min_distance: int = 0  # Minimum character distance
    max_distance: int | None = None  # Maximum character distance
```

---

## Implementation Plan

### Week 1: Constraint Infrastructure (5-7 days)

#### Day 1-2: Schema & Data Models

**Tasks**:
1. Extend IR schema with `constraints` field
2. Define `Constraint` base class and subclasses
3. Add constraint validation to IR validator
4. Update JSON schema for constraints

**Files**:
- `lift_sys/ir/models.py` - Add constraint classes
- `lift_sys/ir/schema.py` - Update JSON schema
- `tests/ir/test_constraints.py` - Unit tests (15+ tests)

**Success Criteria**:
- IR can be created with constraints
- Constraints validate correctly
- JSON serialization works
- 100% unit test coverage

#### Day 3-4: Constraint Detector

Create system to analyze IR and automatically add constraints:

```python
class ConstraintDetector:
    """Analyzes IR and adds appropriate constraints."""

    def detect_return_constraints(self, ir: IR) -> list[ReturnConstraint]:
        """Detect values that should be returned."""
        # If effect produces a value and signature has return type,
        # add MUST_RETURN constraint

    def detect_loop_constraints(self, ir: IR) -> list[LoopBehaviorConstraint]:
        """Detect loop behaviors from effect descriptions."""
        # If effect says "find first", add EARLY_RETURN constraint

    def detect_position_constraints(self, ir: IR) -> list[PositionConstraint]:
        """Detect position requirements from assertions."""
        # If assertion mentions adjacency/distance, add constraint
```

**Files**:
- `lift_sys/validation/constraint_detector.py` (300+ lines)
- `tests/validation/test_constraint_detector.py` (200+ lines)

**Success Criteria**:
- Detector identifies missing return constraints
- Detector recognizes "first match" patterns
- Detector extracts position requirements from assertions
- 90%+ accuracy on Phase 3 test cases

#### Day 5: Integration with IR Generator

Modify `XGrammarIRTranslator` to run constraint detection:

```python
class XGrammarIRTranslator:
    def __init__(self, ..., enable_constraints: bool = True):
        self.constraint_detector = ConstraintDetector() if enable_constraints else None

    async def translate(self, ...):
        ir = await self._generate_ir(...)

        # Add constraints
        if self.constraint_detector:
            constraints = self.constraint_detector.detect_all(ir)
            ir.constraints.extend(constraints)

        return ir
```

**Files**:
- `lift_sys/forward_mode/xgrammar_translator.py` - Add constraint detection
- `tests/integration/test_ir_with_constraints.py` - Integration tests

**Success Criteria**:
- IR generation produces IRs with constraints
- Constraints logged for debugging
- No performance regression (<100ms overhead)

#### Day 6-7: Constraint-Aware Prompt Engineering

Enhance code generation prompt to respect constraints:

**Current prompt** (simplified):
```
Generate Python code implementing this IR:
{ir_json}
```

**New prompt with constraints**:
```
Generate Python code implementing this IR with these REQUIRED constraints:

IR Specification:
{ir_json}

CONSTRAINTS (MUST be respected):
{format_constraints_for_prompt(ir.constraints)}

Examples of correct implementations:
{generate_constraint_examples(ir.constraints)}
```

**Constraint Formatting**:
```python
def format_constraints_for_prompt(constraints: list[Constraint]) -> str:
    """Format constraints as explicit requirements for LLM."""
    lines = []

    for c in constraints:
        if isinstance(c, ReturnConstraint):
            lines.append(f"- MUST return '{c.value_name}' value explicitly")
            lines.append(f"  Example: return {c.value_name}")

        elif isinstance(c, LoopBehaviorConstraint):
            if c.search_type == "FIRST_MATCH":
                lines.append(f"- MUST return immediately on FIRST match (not continue loop)")
                lines.append(f"  Example: for ...: if condition: return value")

        elif isinstance(c, PositionConstraint):
            lines.append(f"- Elements {c.elements} must be {c.requirement}")
            if c.requirement == "NOT_ADJACENT":
                lines.append(f"  Example: Check distance > {c.min_distance}")

    return "\n".join(lines)
```

**Files**:
- `lift_sys/codegen/xgrammar_generator.py` - Update prompt with constraints
- `lift_sys/codegen/constraint_formatter.py` - Format constraints for prompt
- `tests/codegen/test_constraint_prompts.py` - Test prompt generation

**Success Criteria**:
- Constraints clearly communicated in prompt
- Examples provided for each constraint type
- Prompt remains under token limit
- LLM understands and follows constraints

---

### Week 2: Testing & Validation (5-7 days)

#### Day 8-9: Constraint Validation

Create post-generation validator to check if constraints were respected:

```python
class ConstraintValidator:
    """Validates generated code against IR constraints."""

    def validate(self, code: str, ir: IR) -> ConstraintViolationReport:
        """Check if generated code respects all constraints."""
        ast_tree = ast.parse(code)
        violations = []

        for constraint in ir.constraints:
            if isinstance(constraint, ReturnConstraint):
                if not self._has_explicit_return(ast_tree, constraint.value_name):
                    violations.append(...)

            elif isinstance(constraint, LoopBehaviorConstraint):
                if not self._has_early_return_pattern(ast_tree):
                    violations.append(...)

            elif isinstance(constraint, PositionConstraint):
                if not self._validates_position(ast_tree, constraint):
                    violations.append(...)

        return ConstraintViolationReport(violations)
```

**Files**:
- `lift_sys/validation/constraint_validator.py` (400+ lines)
- `tests/validation/test_constraint_validator.py` (250+ lines)

**Success Criteria**:
- Detects missing return statements
- Detects accumulation instead of early return
- Detects missing position validation
- 95%+ accuracy on known violations

#### Day 10-11: Integration with ValidatedCodeGenerator

Extend `ValidatedCodeGenerator` to use constraints:

```python
class ValidatedCodeGenerator:
    def __init__(self, ...):
        self.constraint_validator = ConstraintValidator()

    async def generate_with_validation(self, ir: IR, ...) -> ValidatedCode:
        # ... existing test generation ...

        for attempt in range(max_attempts):
            code = await self._generate_code(ir)

            # 1. Check constraints
            constraint_report = self.constraint_validator.validate(code, ir)
            if constraint_report.has_violations():
                error_msg = self._format_constraint_violations(constraint_report)
                # Provide feedback for next attempt
                continue

            # 2. Run tests (existing logic)
            test_results = await self._run_tests(code, test_cases)
            if test_results.passed:
                return ValidatedCode(code=code, ...)

        return best_attempt_with_warnings(...)
```

**Files**:
- `lift_sys/codegen/validated_generator.py` - Add constraint validation
- `tests/codegen/test_validated_generator_with_constraints.py`

**Success Criteria**:
- Constraint violations trigger regeneration
- Error feedback includes constraint violations
- Falls back to best attempt if all fail
- No infinite loops

#### Day 12-13: Phase 3 Re-Testing

Run full Phase 3 test suite with constraints enabled:

```bash
uv run python debug/run_phase3_with_constraints.py --best-of-n
```

**Expected Results**:
- **count_words**: Fixed by ReturnConstraint (✅ 5/5 tests pass)
- **find_index**: Fixed by LoopBehaviorConstraint (✅ 5/5 tests pass)
- **is_valid_email**: Fixed by PositionConstraint (✅ 5/5 tests pass)
- **Overall**: 18/18 passing (100%)

**Analysis**:
- Compare before/after for each test
- Measure constraint detection accuracy
- Document cases where constraints helped
- Identify any new failures

**Files**:
- `debug/run_phase3_with_constraints.py` - Test runner
- `logs/phase3_with_constraints.log` - Results
- `docs/PHASE_7_TEST_RESULTS.md` - Analysis

#### Day 14: Performance & Cost Analysis

Measure overhead of constraint system:

**Metrics**:
1. **IR Generation Time**:
   - Baseline: ~11s
   - With constraint detection: ~11.1s (+100ms acceptable)

2. **Code Generation Time**:
   - Baseline: ~10.7s
   - With constraint prompts: ~11.5s (+800ms acceptable for clarity)

3. **Cost per IR**:
   - Baseline: $0.0056
   - With constraints: ~$0.0062 (+10% for longer prompts acceptable)

4. **Success Rate Improvement**:
   - Baseline: 83.3% (15/18)
   - With constraints: Target 95%+ (17-18/18)
   - Cost per success: Should DECREASE despite higher per-IR cost

**Files**:
- `debug/benchmark_constraints_overhead.py`
- `docs/PHASE_7_PERFORMANCE_ANALYSIS.md`

---

### Week 3: Polish & Documentation (3-5 days)

#### Day 15-16: Error Messages & Logging

Improve user-facing messages:

```python
# Before
"Code generation failed: test execution failed"

# After
"Code generation failed: Constraint violation detected
 - Missing return for 'count' value (MUST_RETURN constraint)
 - Generated code does not explicitly return computed value
 - Suggestion: Add 'return count' statement after computation"
```

**Files**:
- `lift_sys/validation/constraint_messages.py` - User-friendly messages
- `lift_sys/codegen/xgrammar_generator.py` - Enhanced logging

#### Day 17-18: Documentation

**User-Facing Docs**:
- `docs/USER_GUIDE_CONSTRAINTS.md` - How constraints work
- `docs/CONSTRAINT_REFERENCE.md` - All constraint types
- `docs/TROUBLESHOOTING_CONSTRAINTS.md` - Common issues

**Developer Docs**:
- `docs/PHASE_7_ARCHITECTURE.md` - System design
- `docs/ADDING_NEW_CONSTRAINTS.md` - Extension guide
- `docs/CONSTRAINT_DETECTOR_INTERNALS.md` - How detection works

#### Day 19: Phase 7 Completion Summary

Write comprehensive completion document:

**Contents**:
- What was built (constraint types, detector, validator)
- Test results (before/after Phase 3)
- Performance metrics
- Lessons learned
- Future work (additional constraint types)

**Files**:
- `PHASE_7_COMPLETE.md` (similar to PHASE_6_COMPLETE.md)

---

## Success Criteria

### Must Have (Phase 7 Completion)

1. **Infrastructure**:
   - ✅ IR schema extended with constraints
   - ✅ ConstraintDetector implemented and tested
   - ✅ ConstraintValidator implemented and tested
   - ✅ Integration with IR generation pipeline
   - ✅ Integration with code generation pipeline

2. **Constraint Types**:
   - ✅ ReturnConstraint (count_words fix)
   - ✅ LoopBehaviorConstraint (find_index fix)
   - ✅ PositionConstraint (is_valid_email fix)

3. **Testing**:
   - ✅ 100% unit test coverage for new components
   - ✅ Integration tests with Phase 3 suite
   - ✅ Performance benchmarks

4. **Quality**:
   - ✅ Phase 3 success rate: **≥95% (17-18/18 tests)**
   - ✅ Constraint detection accuracy: **≥90%**
   - ✅ No performance regression: **<1s overhead per IR**
   - ✅ Cost increase acceptable: **<20% per IR**

5. **Documentation**:
   - ✅ User guide for constraints
   - ✅ Developer guide for extending
   - ✅ Phase 7 completion summary

### Nice to Have (Future Work)

1. **Additional Constraint Types**:
   - `RangeConstraint`: Off-by-one prevention (e.g., "use <= not <")
   - `OrderConstraint`: Operation ordering (e.g., "validate before use")
   - `NullCheckConstraint`: Null safety requirements

2. **Advanced Features**:
   - Constraint auto-discovery from test failures
   - Constraint relaxation if too restrictive
   - Constraint explanations in generated code comments

3. **Integration**:
   - Constraint visualization in IR viewer
   - IDE hints based on constraints
   - Constraint templates for common patterns

---

## Risk Mitigation

### Risk: Constraint detection accuracy insufficient

**Symptoms**: Detector misses constraints or adds incorrect ones

**Mitigation**:
- Start with simple heuristics (keyword matching)
- Iteratively improve based on test failures
- Manual constraint override API for edge cases

**Fallback**: Disable auto-detection, require manual constraint specification

### Risk: LLM doesn't follow constraints

**Symptoms**: Code violates constraints despite clear prompt

**Mitigation**:
- Provide concrete examples in prompt
- Use multi-attempt generation with constraint feedback
- Fall back to AST repair for known violations

**Fallback**: Keep Phase 6 AST repair as safety net

### Risk: Constraint overhead too high

**Symptoms**: Generation time or cost increases significantly

**Mitigation**:
- Cache constraint detection results
- Optimize prompt formatting (concise but clear)
- Make constraints optional per-IR

**Fallback**: Disable constraints for simple cases (100% success category)

### Risk: Phase 3 improvement insufficient

**Symptoms**: Success rate doesn't reach 95%+

**Mitigation**:
- Analyze specific failures case-by-case
- Add targeted constraints for new failure patterns
- Combine with Phase 6 AST repair (hybrid approach)

**Fallback**: Accept 90%+ as respectable, move to other improvements

---

## Comparison to Phase 6 AST Repair

| Aspect | Phase 6 (AST Repair) | Phase 7 (IR Constraints) |
|--------|----------------------|--------------------------|
| **Approach** | Fix code after generation | Prevent bugs before generation |
| **Brittleness** | High (pattern-specific) | Low (behavior-agnostic) |
| **Maintainability** | Low (new patterns per bug) | High (one constraint per bug type) |
| **Success Rate** | 83.3% (15/18) | Target 95%+ (17-18/18) |
| **Scalability** | Doesn't scale (pattern explosion) | Scales (constraint library) |
| **LLM Independence** | Works with any LLM output | Guides LLM to correct output |
| **Sustainability** | Low (breaks with LLM changes) | High (specification-level) |

**Hybrid Strategy**: Keep Phase 6 AST repair as fallback for constraint violations.

---

## Alignment with Strategic Vision

### From PRINCIPLED_PATH_FORWARD.md

**Stage 3: Research-Backed Enhancement**
> **Path A: IR-Level Constraint Enhancement** (recommended for Phase 7)
> - Rationale: Systematic handling without brittle patterns
> - Expected gain: 5-10% through upstream validation
> - When to choose: After hitting 80% (✅ We're at 83.3%)
> - Sustainability: High - one constraint covers all code structures

**Phase 7 aligns perfectly** with this recommendation.

### From PHASE_6_COMPLETE.md

**Future Work - Option 1: IR-Level Constraint Enhancement**
> - Add explicit constraints to IR before generation
> - Example: "Dot must NOT be immediately after @"
> - Grammar-constrained generation respects constraints
> - **Pros**: Prevents bugs before code generation
> - **Effort**: 4-6 hours per constraint type
> - **Sustainability**: High - one constraint covers all code structures

**Phase 7 implements this vision**.

---

## Files to Create/Modify

### New Files (~2,500 lines)

**Models & Schema**:
- `lift_sys/ir/constraints.py` (200 lines) - Constraint classes
- `lift_sys/ir/schema_constraints.json` (100 lines) - JSON schema extension

**Detection & Validation**:
- `lift_sys/validation/constraint_detector.py` (350 lines)
- `lift_sys/validation/constraint_validator.py` (400 lines)
- `lift_sys/validation/constraint_messages.py` (150 lines)

**Code Generation**:
- `lift_sys/codegen/constraint_formatter.py` (200 lines)

**Testing**:
- `tests/ir/test_constraints.py` (250 lines)
- `tests/validation/test_constraint_detector.py` (200 lines)
- `tests/validation/test_constraint_validator.py` (250 lines)
- `tests/codegen/test_constraint_prompts.py` (150 lines)
- `tests/integration/test_ir_with_constraints.py` (200 lines)
- `debug/run_phase3_with_constraints.py` (100 lines)
- `debug/benchmark_constraints_overhead.py` (150 lines)

**Documentation**:
- `docs/USER_GUIDE_CONSTRAINTS.md`
- `docs/CONSTRAINT_REFERENCE.md`
- `docs/PHASE_7_ARCHITECTURE.md`
- `docs/PHASE_7_TEST_RESULTS.md`
- `docs/PHASE_7_PERFORMANCE_ANALYSIS.md`
- `PHASE_7_COMPLETE.md`

### Modified Files

**Core Pipeline**:
- `lift_sys/ir/models.py` - Add `constraints` field to IR
- `lift_sys/forward_mode/xgrammar_translator.py` - Run constraint detection
- `lift_sys/codegen/xgrammar_generator.py` - Use constraints in prompt
- `lift_sys/codegen/validated_generator.py` - Validate constraints

**Supporting**:
- `tests/integration/test_xgrammar_translator.py` - Test with constraints
- `tests/integration/test_xgrammar_code_generator.py` - Test constraint validation

---

## Timeline Summary

| Week | Focus | Deliverables | Success Metric |
|------|-------|--------------|----------------|
| **Week 1** | Infrastructure | Schema, detector, integration | Constraints in IR, 100% unit tests |
| **Week 2** | Validation & Testing | Validator, Phase 3 re-test | 95%+ Phase 3 success rate |
| **Week 3** | Polish & Docs | Logging, docs, completion | Production-ready, documented |

**Total**: 2-3 weeks, ~2,500 new lines of code

---

## Decision Points

### End of Week 1

**Question**: Is constraint detection accurate enough?

**Metrics**:
- Constraint detection recall: ≥90% (detects 90% of needed constraints)
- Constraint detection precision: ≥80% (80% of detected constraints are correct)

**Decisions**:
- **If yes**: Proceed to Week 2 (validation & testing)
- **If no**: Iterate on detection heuristics, add manual override API

### End of Week 2

**Question**: Does Phase 3 reach 95%+ with constraints?

**Metrics**:
- Phase 3 success rate: Target 17-18/18 (95-100%)
- Specific fixes: count_words (5/5), find_index (5/5), is_valid_email (5/5)

**Decisions**:
- **If yes**: Proceed to Week 3 (polish & documentation), declare success
- **If 90-94%**: Acceptable, document limitations, proceed to Week 3
- **If <90%**: Analyze failures, add targeted constraints, extend Week 2

### End of Week 3

**Question**: Is Phase 7 production-ready?

**Metrics**:
- Code quality: 100% unit tests passing
- Documentation: User guide + developer guide complete
- Performance: <20% overhead acceptable
- Stability: No regressions on Phase 3

**Decisions**:
- **If yes**: Declare Phase 7 COMPLETE, plan Phase 8
- **If no**: Extend polish phase, address specific issues

---

## Next Steps After Phase 7

Assuming Phase 7 achieves 95%+ success rate:

### Option A: Push to 100% (Phase 8)

Focus on remaining edge cases with additional constraint types:
- RangeConstraint for off-by-one prevention
- OrderConstraint for operation sequencing
- ErrorHandlingConstraint for exception safety

**Timeline**: 1-2 weeks
**Expected gain**: 95% → 100%

### Option B: Multi-Language Support (Phase 8)

Extend to TypeScript/JavaScript:
- Language-agnostic IR constraints
- TypeScript-specific constraint formatters
- TypeScript code generator with constraints

**Timeline**: 3-4 weeks
**Expected gain**: Python-only → Multi-language

### Option C: Production Deployment (Phase 8)

Stabilize for production use:
- Error recovery and retry logic
- Monitoring and metrics
- Performance optimization
- User beta testing

**Timeline**: 2-3 weeks
**Expected gain**: Prototype → Production-ready

**Recommendation**: Choose based on priorities (quality vs scope vs deployment).

---

## Conclusion

Phase 7 represents a **principled evolution** from Phase 6's pattern-based approach to a specification-based approach. By adding explicit constraints to the IR, we:

1. **Move validation upstream**: Prevent bugs before generation, not after
2. **Eliminate brittleness**: Constraints work for ANY code structure
3. **Scale maintainably**: One constraint per bug type, not pattern per variation
4. **Guide LLM generation**: Clear requirements in prompts
5. **Achieve sustainability**: Constraints survive LLM version changes

**Expected Outcome**: 95%+ success rate (17-18/18 tests) with principled, maintainable solution.

**Key Principle**: Specify requirements at the right abstraction level (IR), not implementation details (AST).

---

**Phase 7 Status**: PLANNING COMPLETE
**Next Action**: Begin Week 1 implementation (schema & constraint models)
**Target Completion**: November 7, 2025
