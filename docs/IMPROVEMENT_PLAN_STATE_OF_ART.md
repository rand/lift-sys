# Lift-Sys Improvement Plan: Breaking the 80% Barrier
## State-of-the-Art Research Synthesis and Implementation Roadmap

**Date**: 2025-10-15
**Current Status**: 8/10 tests passing (80%)
**Goal**: Achieve 95%+ success rate through improved IR generation and code synthesis

---

## Research Summary: Key Findings

### 1. Semantic IR Design (IRCoder, 2024)

**Finding**: Compiler intermediate representations shared across languages significantly improve code generation robustness.

**IRCoder Results**:
- Trained on 4M parallel dataset of source code + compiler IR
- Showed "sizeable and consistent gains" across multilingual completion, understanding, instruction following
- Key insight: IR constructs align across programming languages, providing language-agnostic semantic understanding

**Application to Lift-Sys**: Our current IR is semantic but text-based. We can enhance it by:
- Adding compiler-like control flow representations (CFG, dominance analysis)
- Including concrete code templates/patterns in IR
- Structuring effects as executable pseudocode rather than descriptions

### 2. Verification-Guided Synthesis (2024-2025)

**Finding**: LLM + SMT solver integration achieves near-perfect results through generate-and-verify loops.

**Key Results**:
- **100% coverage** (133/133) on Code2Inv benchmark using O1/O3-mini + Z3
- Type-constrained decoding reduces compilation errors by **>50%**
- Correctness-guaranteed code generation via context-sensitive parser constraints

**Application to Lift-Sys**:
- Integrate Z3 SMT solver for formal verification of generated code
- Use SMT to verify control flow properties (e.g., "return only after loop completes")
- Generate verification conditions from IR assertions

### 3. Example-Driven Synthesis (2024)

**Finding**: Strategic few-shot examples dramatically improve generation quality.

**PERC Framework (2024)**:
- Uses algorithmic plans (pseudocode) to retrieve effective examples
- Converting code → pseudocode captures algorithmic patterns better than raw code
- Self-planning approach: plan → implement shows **25.4% relative improvement**

**CODEEXEMPLAR (Dec 2024)**:
- Model-free and model-based example selection methods
- Significantly improves CodeLlama on HumanEval+ benchmark
- Key: selecting examples whose algorithmic patterns match target behavior

**Application to Lift-Sys**:
- Build example library for each common pattern (loops, searches, filters)
- IR should include algorithmic plan + 1-2 exemplar implementations
- Use plan-based retrieval to select relevant examples

### 4. Execution-Guided Refinement (2024)

**Finding**: Generate → Execute → Refine loops with test oracles significantly improve correctness.

**AlphaCode Approach**:
- Generate 1M candidates → filter 99% via example tests → cluster + rank
- Achieved top 54.3% in competitive programming
- Key: massive sampling + empirical testing

**Oracle-Guided Synthesis**:
- CEGIS (Counter-Example Guided Inductive Synthesis) loop
- Algo framework: LLM generates oracle verifiers to guide synthesis
- OpenCodeInterpreter: integrated execution + iterative refinement

**Application to Lift-Sys**:
- Already have multishot (3 attempts) - increase to 5-10 for hard cases
- Implement CEGIS loop: test → counterexample → refine IR → regenerate
- Build oracle library for common patterns (search, filter, reduce)

### 5. AST-Based Repair (2024-2025)

**Finding**: Direct AST manipulation can fix control flow bugs that LLMs struggle with.

**Key Techniques**:
- Syntax-guided synthesis (SyGuS) for constraint-based repair
- Control flow reachability analysis
- Automated mutation of AST nodes guided by test failures

**Application to Lift-Sys**:
- When validation detects control flow bug, apply AST transformation
- Example: detect "return -1 inside loop" → move return after loop
- Build library of AST repair patterns for common bugs

---

## The Lift-Sys 80% Barrier: Root Cause Analysis

### Current System Architecture

```
Natural Language → IR Generation → Code Generation → Validation → (Retry)
                      │                    │              │
                      v                    v              v
                 Text Effects        XGrammar       AST Check
                 (vague)          (constrained)    (detect only)
```

### Identified Weaknesses

1. **IR Effects Too Vague**
   - Current: "After the loop ends (not inside it), return -1"
   - Problem: LLM interprets this in Python syntax but misses indentation semantics
   - Solution: Include concrete control flow structure + example

2. **No Formal Verification**
   - Current: AST validation detects bugs but can't verify correctness
   - Problem: No way to prove "return executes after loop"
   - Solution: SMT-based verification of control flow properties

3. **Limited Example Guidance**
   - Current: Only text descriptions in IR
   - Problem: LLM lacks concrete patterns to match
   - Solution: Include 1-2 exemplar implementations per pattern

4. **No Repair Mechanism**
   - Current: Validation detects, retry regenerates, but often fails again
   - Problem: Text feedback insufficient for control flow fixes
   - Solution: AST-based automatic repair for known patterns

---

## Improvement Plan: Four-Phase Roadmap

### **Phase 4: Enhanced IR with Concrete Examples** (Week 1)
**Goal**: Add concrete code patterns to IR to guide LLM generation

#### Implementation Steps

**4.1. Create Example Library** (`lift_sys/patterns/examples.py`)
```python
PATTERN_EXAMPLES = {
    "list_search_with_fallback": [
        {
            "description": "Find index of value in list, return -1 if not found",
            "pseudocode": """
                for each (index, item) in list:
                    if item == target:
                        return index
                # After loop completes:
                return -1
            """,
            "implementation": """
                def find_index(lst, value):
                    for index, item in enumerate(lst):
                        if item == value:
                            return index
                    return -1  # AFTER loop
            """,
            "control_flow": {
                "type": "search_loop",
                "success_return": "inside_loop",
                "fallback_return": "after_loop"
            }
        }
    ]
}
```

**4.2. Enhance IR Generation** (`lift_sys/ir/generator.py`)
- When generating IR for "find value in list", retrieve matching pattern
- Add `examples` field to IR with 1-2 concrete implementations
- Add `control_flow_pattern` field specifying structure

**4.3. Update Code Generation Prompts** (`lift_sys/codegen/code_schema.py`)
```python
def get_prompt_for_code_generation(..., examples=None):
    prompt = f"""Generate implementation matching this structure:

{examples[0]['pseudocode']}

Example implementation:
{examples[0]['implementation']}

IMPORTANT: Follow the same control flow structure:
- {examples[0]['control_flow']['success_return']}
- {examples[0]['control_flow']['fallback_return']}
"""
```

**Expected Impact**: 80% → 85% (examples guide LLM to correct patterns)

**Testing**: Re-run Phase 2 tests with enhanced IR

---

### **Phase 5: SMT-Based Verification** (Week 2)
**Goal**: Verify control flow properties using Z3 SMT solver

#### Implementation Steps

**5.1. Install Z3**
```bash
uv add z3-solver
```

**5.2. Create Verification Module** (`lift_sys/verification/smt_verifier.py`)
```python
from z3 import *

class ControlFlowVerifier:
    """Verify control flow properties using Z3."""

    def verify_return_after_loop(self, code: str, function_name: str) -> bool:
        """Verify that fallback return executes only after loop."""
        tree = ast.parse(code)

        # Find for loop and return statements
        for_node, return_nodes = self._extract_control_flow(tree)

        # Create Z3 variables for program points
        inside_loop = Bool('inside_loop')
        loop_completed = Bool('loop_completed')
        fallback_executed = Bool('fallback_executed')

        # Constraints
        solver = Solver()

        # Constraint: fallback return only if loop completed
        solver.add(Implies(fallback_executed, loop_completed))

        # Constraint: can't be inside loop when fallback executes
        solver.add(Implies(fallback_executed, Not(inside_loop)))

        # Check if constraints are satisfiable
        return solver.check() == sat

    def verify_all_paths_return(self, code: str) -> bool:
        """Verify all control paths have explicit returns."""
        # Use Z3 to model all branches and verify returns
        pass
```

**5.3. Integrate with Validation** (`lift_sys/codegen/validation.py`)
```python
def validate(self, code: str, function_name: str, context: dict) -> list[ValidationIssue]:
    issues = []

    # Existing AST validation
    issues.extend(self._validate_loop_return_placement(code))

    # NEW: SMT verification
    verifier = ControlFlowVerifier()
    if "find" in function_name or "search" in function_name:
        if not verifier.verify_return_after_loop(code, function_name):
            issues.append(ValidationIssue(
                severity="error",
                category="control_flow_verification_failed",
                message="SMT verification: fallback return may execute inside loop",
                suggestion="Move return -1 to after loop completion"
            ))

    return issues
```

**Expected Impact**: 85% → 90% (formal verification catches subtle bugs)

**Testing**: Verify on synthetic control flow bugs

---

### **Phase 6: AST-Based Auto-Repair** (Week 3)
**Goal**: Automatically fix detected control flow bugs via AST transformation

#### Implementation Steps

**6.1. Create Repair Module** (`lift_sys/repair/ast_repair.py`)
```python
class ASTRepairEngine:
    """Automatically repair common control flow bugs."""

    def repair_loop_return_placement(self, code: str) -> tuple[str, bool]:
        """
        Detect and fix return statements inside loops that should be after.

        Pattern:
            for ...:
                if condition:
                    return value
                return fallback  # BUG: inside loop

        Fix:
            for ...:
                if condition:
                    return value
            return fallback  # FIXED: after loop
        """
        tree = ast.parse(code)
        modified = False

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Find return statements at same level as if
                returns_to_move = []

                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.If):
                        # Check if next statement is return
                        if i + 1 < len(node.body) and isinstance(node.body[i + 1], ast.Return):
                            returns_to_move.append((i + 1, node.body[i + 1]))

                if returns_to_move:
                    # Remove return from loop body
                    for idx, ret_stmt in reversed(returns_to_move):
                        node.body.pop(idx)

                    # Add return after loop (need to modify parent)
                    # This requires parent tracking...
                    modified = True

        if modified:
            return ast.unparse(tree), True
        return code, False

    def repair_missing_fallback(self, code: str, return_value: str = "-1") -> str:
        """Add missing fallback return after loop."""
        # Similar AST transformation
        pass
```

**6.2. Integrate with Generation Loop** (`lift_sys/codegen/xgrammar_generator.py`)
```python
# In generate() method, after validation fails:

if validation_issues:
    # Try AST-based repair before retry
    repaired_code, was_repaired = self.repair_engine.repair_loop_return_placement(complete_code)

    if was_repaired:
        # Validate repaired code
        repaired_issues = self.validator.validate(repaired_code, ir.signature.name, context)

        if not repaired_issues:
            # Repair succeeded!
            return GeneratedCode(
                source_code=repaired_code,
                language="python",
                metadata={"repaired": True, "original_issues": len(validation_issues)},
                warnings=["Code was automatically repaired"]
            )
```

**Expected Impact**: 90% → 93% (auto-fix common patterns instead of retry)

**Testing**: Test on all previously failing cases

---

### **Phase 7: Advanced Multishot with CEGIS** (Week 4)
**Goal**: Implement Counter-Example Guided Inductive Synthesis

#### Implementation Steps

**7.1. Enhanced Multishot** (`lift_sys/codegen/multishot.py`)
```python
class CEGISMultishotGenerator:
    """Multi-shot with counterexample-guided refinement."""

    async def generate_with_cegis(
        self,
        generator,
        ir: IntermediateRepresentation,
        test_cases: list,
        max_iterations: int = 5
    ) -> GenerationCandidate:
        """
        CEGIS loop:
        1. Generate multiple candidates
        2. Test against test cases
        3. Collect counterexamples from failures
        4. Refine IR with counterexample guidance
        5. Repeat until success or max iterations
        """

        for iteration in range(max_iterations):
            # Generate candidates with varying temperatures
            candidates = await self._generate_candidates(generator, ir, n=5)

            # Test all candidates
            best = max(candidates, key=lambda c: c.score)

            if best.score == 1.0:
                return best  # Perfect solution

            # Collect counterexamples
            counterexamples = self._extract_counterexamples(best, test_cases)

            # Refine IR with counterexample insights
            ir = await self._refine_ir_with_counterexamples(ir, counterexamples)

            # Continue loop with refined IR

        # Return best attempt
        return best

    def _extract_counterexamples(self, candidate, test_cases):
        """Extract failing test cases as counterexamples."""
        failures = []
        for test_name, (inputs, expected) in test_cases:
            try:
                actual = self._run_code(candidate.code, inputs)
                if actual != expected:
                    failures.append({
                        "inputs": inputs,
                        "expected": expected,
                        "actual": actual,
                        "test_name": test_name
                    })
            except Exception as e:
                failures.append({
                    "inputs": inputs,
                    "expected": expected,
                    "actual": None,
                    "error": str(e),
                    "test_name": test_name
                })
        return failures

    async def _refine_ir_with_counterexamples(self, ir, counterexamples):
        """
        Use LLM to refine IR based on what went wrong.

        Example: if counterexample shows return -1 when expecting 1,
        and the test is "find value at index 1", we can infer the
        code is returning early (inside loop).
        """
        refinement_prompt = f"""
The current implementation fails on these cases:
{json.dumps(counterexamples, indent=2)}

Current effects:
{[e.description for e in ir.effects]}

Suggest more precise effects that would avoid these failures.
Focus on control flow and edge case handling.
"""

        # Use LLM to suggest refined effects
        # (This is meta-programming: using LLM to improve IR for better code generation)
        refined_effects = await self._generate_refined_effects(refinement_prompt)

        # Update IR
        ir.effects = refined_effects
        return ir
```

**Expected Impact**: 93% → 95%+ (iterative refinement catches edge cases)

---

## Implementation Timeline

### Week 1: Enhanced IR with Examples
- **Days 1-2**: Build pattern example library (5-10 common patterns)
- **Days 3-4**: Enhance IR generation to include examples
- **Days 5-7**: Update code generation prompts, test on Phase 2 suite

**Deliverable**: IR with concrete examples, expect 85% success rate

### Week 2: SMT Verification
- **Days 1-2**: Implement Z3-based control flow verifier
- **Days 3-4**: Integrate with validation pipeline
- **Days 5-7**: Test verification on synthetic bugs + Phase 2 suite

**Deliverable**: Formal verification of control flow, expect 90% success rate

### Week 3: AST Auto-Repair
- **Days 1-3**: Implement AST repair for 3-5 common patterns
- **Days 4-5**: Integrate with generation loop
- **Days 6-7**: Test repair on failing cases

**Deliverable**: Automatic repair of common bugs, expect 93% success rate

### Week 4: CEGIS Multishot
- **Days 1-3**: Implement CEGIS loop with IR refinement
- **Days 4-5**: Test on hard cases (find_index, get_type_name)
- **Days 6-7**: Full evaluation on expanded test suite

**Deliverable**: CEGIS-enhanced multishot, expect 95%+ success rate

---

## Expected Results by Phase

| Phase | Technique | Expected Success Rate | Key Improvement |
|-------|-----------|----------------------|-----------------|
| **Current** | Multishot + Validation | 80% | Baseline |
| **Phase 4** | + Concrete Examples | 85% | LLM has patterns to follow |
| **Phase 5** | + SMT Verification | 90% | Formal proofs catch subtle bugs |
| **Phase 6** | + AST Auto-Repair | 93% | Fix instead of retry |
| **Phase 7** | + CEGIS Loop | 95%+ | Iterative refinement from failures |

---

## Technical Dependencies

### New Libraries
```toml
# pyproject.toml additions
[dependencies]
z3-solver = "^4.12.0"  # SMT solver for verification
```

### New Modules
```
lift_sys/
├── patterns/
│   ├── __init__.py
│   ├── examples.py          # Pattern example library
│   └── retrieval.py         # Example retrieval logic
├── verification/
│   ├── __init__.py
│   ├── smt_verifier.py      # Z3-based verification
│   └── properties.py        # Control flow properties
└── repair/
    ├── __init__.py
    ├── ast_repair.py        # AST transformation repairs
    └── repair_patterns.py   # Library of repair patterns
```

---

## Alternative Approaches (Considered but Deferred)

### 1. Fine-tuning on IR→Code Dataset (IRCoder approach)
**Why Deferred**: Requires large parallel dataset (4M+ examples) and compute for fine-tuning. Our constrained generation approach is more practical.

**Future Consideration**: Could fine-tune smaller model (1-3B params) on lift-sys specific patterns.

### 2. Type System Integration (Type-Constrained Decoding)
**Why Deferred**: Python's gradual typing makes this complex. Focus on control flow first.

**Future Consideration**: Could add type constraints for statically-typed target languages (Rust, Go).

### 3. AlphaCode-style Massive Sampling
**Why Deferred**: 1M candidates requires significant compute ($$$).

**Future Consideration**: Scale up multishot from 3→10→50 based on problem difficulty.

---

## Metrics and Evaluation

### Success Criteria
- **Primary**: >95% test case passing rate on Phase 2 suite
- **Secondary**: <3 retry attempts on average per function
- **Tertiary**: Generated code matches reference implementation control flow 90%+ of time

### Evaluation Suite Expansion
Add 20 more tests covering:
- Complex control flow (nested loops, early returns)
- Edge cases (empty lists, None values, type mismatches)
- Multi-step algorithms (sort, merge, reduce)

### Continuous Monitoring
- Track success rate by pattern type
- Monitor which phases contribute most to success
- Measure repair success rate vs. retry success rate

---

## Risk Mitigation

### Risk 1: SMT Solver Overhead
**Mitigation**: Cache verification results, only verify complex patterns

### Risk 2: AST Repair Introduces New Bugs
**Mitigation**: Repair only if validation passes on repaired code, otherwise fall back to retry

### Risk 3: CEGIS Doesn't Converge
**Mitigation**: Cap iterations at 5, fall back to best candidate

### Risk 4: Examples Don't Match Novel Problems
**Mitigation**: Build diverse example library, use semantic similarity for retrieval

---

## Long-Term Vision (Beyond 95%)

### Towards 99% Success Rate
1. **Formal Specification Language**: Users write lightweight formal specs (pre/post conditions)
2. **Proof-Carrying Code**: Generate code with correctness proofs
3. **Learned Repair Policies**: Train model on successful repairs to guide future repairs
4. **Interactive Refinement**: User provides feedback on failures to guide synthesis

### Integration with Semantic IR Research
- Track "Can LLMs Understand IRs" research line (ICML 2025)
- Collaborate with IRCoder team on compiler IR integration
- Contribute findings back to program synthesis community

---

## Summary

**Current State**: 80% success rate limited by vague IR specifications and lack of verification

**Root Cause**: Text descriptions insufficient for LLMs to understand precise control flow semantics

**Solution**: Four-phase enhancement:
1. Add concrete examples to IR
2. Verify with SMT solver
3. Auto-repair with AST transformations
4. Refine iteratively with CEGIS

**Expected Outcome**: 95%+ success rate through formal verification and example-guided synthesis

**Timeline**: 4 weeks to full implementation

**Research Foundation**: Builds on IRCoder (2024), LLM-SMT integration (2024-2025), CEGIS techniques, and AST-based repair

---

**Next Steps**:
1. Review and approve this plan
2. Begin Phase 4 implementation (example library)
3. Set up evaluation framework for tracking improvements
