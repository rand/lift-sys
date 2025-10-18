# Research Report: Conjecturing in Formal Reasoning
## Applicability to lift-sys

**Paper**: [arXiv:2510.11986](https://arxiv.org/abs/2510.11986) - "Conjecturing: An Overlooked Step in Formal Mathematical Reasoning"

**Authors**: Jasivan Alex Sivakumar, Philipp Borchert, Ronald Cardenas, Gerasimos Lampouras

**Date**: October 17, 2025

**Assessment Status**: Research analysis complete, implementation plan proposed

---

## Executive Summary

**Core Finding**: The paper identifies that autoformalisation (converting informal mathematical statements to formal language) requires an explicit **conjecturing step** where the system must generate missing conclusions before formalisation can proceed.

**Applicability to lift-sys**: ⭐⭐⭐⭐⭐ **HIGHLY RELEVANT**

**Why it matters**: lift-sys already has the infrastructure (typed holes, constraints) but treats them as implementation details rather than a fundamental two-phase process. The paper's insights suggest **separating conjecture generation from translation** could improve success rates and resolve the current 3-failure bottleneck.

**Recommended action**: Implement a **two-phase IR generation** approach inspired by the conjecturing framework, which could address current diagnostic issues more systematically than additional constraint types.

---

## Part 1: Paper Summary

### 1.1 The Conjecturing Problem

**Traditional View** (incorrect):
```
Informal Math → [Direct Translation] → Formal Math
```

**Actual Process** (correct):
```
Informal Math → [Conjecture Generation] → [Formalisation] → Formal Math
              ↑                          ↑
         Missing step!            Overestimated success
```

**Example from paper**:

**Informal**: "Find the sum of all primes less than 1000"

**Requires conjecturing**:
- What is the answer? (Need explicit bound/value)
- What form should the proof take?
- What intermediate results are needed?

**Only after conjecturing** can you formalise the statement in Lean/Coq.

### 1.2 Key Contributions

1. **ConjectureBench**: Benchmark dataset for evaluating conjecturing capabilities
2. **Separated evaluation**: Treat conjecturing as independent task, not bundled with formalisation
3. **Lean-FIRe method**: Framework for improving conjecturing + autoformalisation
4. **Empirical findings**:
   - LLMs **can** generate accurate conjectures
   - Autoformalisation success is **substantially overestimated** when conjecture step is ignored
   - First end-to-end autoformalisation: 13 problems (GPT-4), 7 problems (DeepSeek-V3)

### 1.3 Core Insight

> "Conjecturing should be treated as an independent task and carefully integrated into the autoformalisation process."

**Translation to lift-sys context**:
> "Typed hole resolution should be treated as an independent task and carefully integrated into the IR generation process."

---

## Part 2: Direct Parallels to lift-sys

### 2.1 The Typed Hole ≈ Missing Conjecture Parallel

| Mathematical Reasoning | lift-sys IR Generation |
|----------------------|----------------------|
| **Informal statement** | **Natural language prompt** |
| ↓ | ↓ |
| **Missing conjecture** (explicit answer/bound) | **Typed hole** (`<?hole_1: function_name?>`) |
| ↓ | ↓ |
| **Conjecture generation** | **Hole resolution** |
| ↓ | ↓ |
| **Formalisation** (Lean/Coq) | **IR → Code** translation |

**Example**:

**lift-sys current approach** (bundled):
```python
Prompt: "Find the first index of value in list"
    ↓
[Single LLM call generates IR with holes filled]
    ↓
IR: {name: "find_index", ...}  # Holes implicitly resolved
```

**Conjecturing-inspired approach** (separated):
```python
Prompt: "Find the first index of value in list"
    ↓
[Phase 1: Generate IR skeleton with explicit holes]
    ↓
IR: {
    name: "<?hole_1: function_name?>",
    parameters: [{type: "<?hole_2: param_type?>"}],
    return: "<?hole_3: return_type?>",
    constraints: [LoopBehaviorConstraint(FIRST_MATCH, EARLY_RETURN)]
}
    ↓
[Phase 2: Conjecture resolution - explicitly fill holes]
    ↓
Conjectures:
    hole_1 = "find_index"
    hole_2 = "list[Any]"
    hole_3 = "int"
    ↓
[Phase 3: Validate conjectures satisfy constraints]
    ↓
Complete IR → Code generation
```

### 2.2 The "Overestimated Success" Problem

**Paper's finding**:
- Autoformalisation appears successful when conjecture is **given**
- Performance drops significantly when conjecture must be **generated**
- Problem: Bundling both tasks obscures where failure occurs

**lift-sys parallel**:
From `STRATEGIC_ASSESSMENT_2025-10-17.md`:
> "Phase 7 (IR-level constraints) completed with excellent architecture but **zero real-world impact** on success rate. We remain at **83.3%**."

**Root cause analysis** (through conjecturing lens):

Current lift-sys approach bundles:
1. IR skeleton generation
2. Hole filling (implicit conjecturing)
3. Constraint detection
4. Code generation

**Where's the failure?** We can't tell because it's bundled!

Possibilities:
- ❌ Bad conjectures (wrong hole values) → wrong IR → wrong code
- ❌ Good conjectures but constraints not honored during codegen
- ❌ Good IR but AST repair patterns don't match LLM variations
- ✅ **All three mixed together** (most likely)

### 2.3 Current lift-sys Evidence

**Evidence from existing diagnostics** (`STRATEGIC_ASSESSMENT_2025-10-17.md`):

1. **count_words**: Returns None (missing return)
   - **Conjecture**: Function should compute and return count
   - **Constraint**: ReturnConstraint(value_name="count")
   - **Status**: Constraint exists but doesn't prevent failure
   - **Analysis**: Conjecture (IR) may be correct, but codegen doesn't honor it

2. **find_index**: Returns last instead of first
   - **Conjecture**: Loop should use early return for first match
   - **Constraint**: LoopBehaviorConstraint(FIRST_MATCH, EARLY_RETURN)
   - **Status**: Constraint exists but doesn't prevent failure
   - **Analysis**: Conjecture correct, codegen produces accumulation pattern instead

3. **is_valid_email**: Accepts invalid adjacency
   - **Conjecture**: @ and . must not be adjacent
   - **Constraint**: PositionConstraint(NOT_ADJACENT)
   - **Status**: Constraint exists but doesn't prevent failure
   - **Analysis**: Conjecture correct, codegen doesn't implement position check

**Pattern**: Good conjectures (IR + constraints), but **codegen doesn't honor them**.

This is **exactly analogous** to the paper's finding: the "formalisation" step (IR→Code) fails even when "conjecturing" step (IR constraints) succeeds.

---

## Part 3: Applicable Concepts

### 3.1 Explicit Two-Phase Process

**From paper**: Separate conjecturing from formalisation

**Application to lift-sys**:

**Phase 1: IR Skeleton + Constraint Detection** (Conjecturing)
- Generate IR with explicit typed holes
- Detect constraints from natural language
- Output: IR with holes and constraints

**Phase 2: Hole Resolution** (Conjecture Refinement)
- For each typed hole:
  - Generate candidates using LLM
  - Filter by constraints
  - Select best candidate
- Validate complete IR satisfies all constraints
- Output: Complete IR (no holes)

**Phase 3: Code Generation** (Formalisation)
- Use complete IR + constraints to generate code
- Validate code honors constraints
- Retry with feedback if violations occur

**Benefit**: Each phase has clear success criteria and can be debugged independently.

### 3.2 Conjecture Evaluation as Independent Task

**From paper**: Measure conjecture quality separately

**Application to lift-sys**:

Current metrics:
- ✅ E2E success rate (83.3%)
- ❌ IR quality (not measured)
- ❌ Constraint satisfaction in IR (not measured)
- ❌ Constraint satisfaction in code (measured but not isolated)

**New metrics** (conjecturing-inspired):

1. **IR Conjecture Accuracy**: Do holes get filled correctly?
   - Measure: % of IRs where hole values are semantically correct
   - Example: `hole_function_name = "find_index"` (correct) vs `"search_list"` (vague)

2. **Constraint Completeness**: Are all necessary constraints detected?
   - Measure: % of IRs where constraints match requirements
   - Example: "find first" → LoopBehaviorConstraint(FIRST_MATCH) detected

3. **Constraint Preservation**: Does generated code honor IR constraints?
   - Measure: % of code that satisfies IR constraints
   - Example: IR has EARLY_RETURN → code uses `return` in loop

**Benefit**: Isolate where pipeline breaks (conjecture vs formalisation).

### 3.3 Iterative Refinement with Feedback

**From paper**: Lean-FIRe method for improving conjectures

**Application to lift-sys**:

**Current approach**:
```python
Prompt → IR (single shot) → Code (with retries if validation fails)
```

**Conjecturing-inspired approach**:
```python
Prompt → IR Skeleton (with holes)
    ↓
[Iterate on conjecture quality]
    ↓
For each hole:
    Generate candidates
    Validate against constraints
    If invalid: regenerate with feedback
    If valid: commit
    ↓
Complete IR → Code (fewer retries needed)
```

**Example** (find_index failure):

**Current**:
```
Prompt: "Find first index"
→ IR: {..., constraints: [LoopBehaviorConstraint(FIRST_MATCH)]}
→ Code: [LLM generates accumulation pattern]
→ Validate: ❌ Violation detected
→ Retry: [LLM generates same pattern again]
→ Retry: [LLM generates same pattern again]
→ Fail: 3 attempts exhausted
```

**Conjecturing-inspired**:
```
Prompt: "Find first index"
→ IR Skeleton: {
    name: "<?hole_name?>",
    loop_pattern: "<?hole_loop?>",
    constraints: [LoopBehaviorConstraint(FIRST_MATCH, EARLY_RETURN)]
}
→ Conjecture for hole_loop:
    Candidates: ["accumulate", "early_return", "iterate_all"]
    Constraint check:
        "accumulate" → ❌ violates EARLY_RETURN
        "early_return" → ✅ satisfies EARLY_RETURN
        "iterate_all" → ❌ violates EARLY_RETURN
    Selected: "early_return"
→ Complete IR: {loop_pattern: "early_return", ...}
→ Code generation with explicit pattern → Higher success rate
```

### 3.4 Constraint-Guided Generation

**From paper**: Use constraints to guide conjecture generation

**Application to lift-sys**:

**Current**: Constraints guide codegen but not IR generation

**Proposal**: Constraints guide **both** IR conjecturing **and** codegen

**Implementation**:

```python
class ConjecturingIRTranslator:
    """Two-phase IR translator inspired by conjecturing framework."""

    async def translate(self, prompt: str) -> IntermediateRepresentation:
        # Phase 1: Generate skeleton with holes
        skeleton = await self._generate_skeleton(prompt)

        # Phase 2: Detect constraints
        constraints = self.constraint_detector.detect(skeleton, prompt)
        skeleton.constraints = constraints

        # Phase 3: Resolve holes using constraints
        complete_ir = await self._resolve_holes(skeleton, constraints)

        # Phase 4: Validate complete IR
        if not self._validate_ir(complete_ir, constraints):
            raise ValueError("IR conjectures violate constraints")

        return complete_ir

    async def _resolve_holes(
        self,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> IntermediateRepresentation:
        """Resolve typed holes using constraint-guided generation."""
        for hole in skeleton.typed_holes():
            # Generate candidates for this hole
            candidates = await self._generate_conjecture_candidates(
                hole, skeleton, constraints
            )

            # Filter by constraints
            valid = [
                c for c in candidates
                if self._conjecture_satisfies_constraints(c, hole, constraints)
            ]

            if not valid:
                raise ValueError(f"No valid conjecture for {hole.identifier}")

            # Select best candidate (first valid for now)
            skeleton = self._fill_hole(skeleton, hole, valid[0])

        return skeleton
```

---

## Part 4: Specific Recommendations for lift-sys

### 4.1 Immediate Application (1-2 weeks)

**Goal**: Use conjecturing framework to diagnose current 3 failures

**Tasks**:

1. **Separate conjecture evaluation**:
   ```python
   # For each of 3 failing tests
   for test in ["count_words", "find_index", "is_valid_email"]:
       # Generate 10 IR samples
       irs = [await translator.translate(test.prompt) for _ in range(10)]

       # Evaluate conjecture quality (manual for now)
       for ir in irs:
           print(f"Constraints detected: {ir.constraints}")
           print(f"Holes filled: {ir.typed_holes()}")
           # Question: Are constraints correct?
           # Question: Would different hole values help?
   ```

2. **Measure constraint preservation**:
   ```python
   # For each generated code sample
   for code in generated_codes:
       violations = constraint_validator.validate(code, ir.constraints)
       if violations:
           print(f"Codegen failed to honor: {violations}")
           # Insight: Is this IR→Code issue or IR quality issue?
   ```

3. **Diagnostic report**:
   - Are conjectures (IR + constraints) correct?
   - If yes → Problem is in formalisation (IR→Code)
   - If no → Problem is in conjecturing (Prompt→IR)
   - Data-driven decision on whether to improve conjecture or formalisation

**Benefit**: Aligns with current diagnostic investigation (lift-sys-229) but adds theoretical framework.

### 4.2 Short-term Enhancement (2-3 weeks)

**Goal**: Implement explicit two-phase IR generation

**Architecture**:

```python
class ConjecturingIRGenerator:
    """
    IR generation with explicit conjecturing phase.

    Inspired by arXiv:2510.11986 conjecturing framework.
    """

    async def generate(self, prompt: str) -> IntermediateRepresentation:
        # Phase 1: Generate skeleton with explicit holes
        skeleton = await self._generate_skeleton(prompt)

        # Phase 2: Detect constraints from prompt
        constraints = await self._detect_constraints(prompt, skeleton)

        # Phase 3: Generate conjectures for holes (constraint-guided)
        conjectures = await self._generate_conjectures(skeleton, constraints)

        # Phase 4: Validate conjectures
        validated = self._validate_conjectures(conjectures, constraints)

        # Phase 5: Fill holes with validated conjectures
        complete_ir = self._apply_conjectures(skeleton, validated)

        return complete_ir

    async def _generate_conjectures(
        self,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> dict[str, Any]:
        """Generate conjectures for each typed hole."""
        conjectures = {}

        for hole in skeleton.typed_holes():
            # Build conjecture prompt
            prompt = self._build_conjecture_prompt(hole, skeleton, constraints)

            # Generate candidates (beam search or best-of-N)
            candidates = await self.provider.generate_candidates(
                prompt=prompt,
                num_candidates=5,
                temperature=0.7
            )

            # Filter by constraints
            valid = self._filter_by_constraints(candidates, hole, constraints)

            # Select best
            conjectures[hole.identifier] = valid[0] if valid else None

        return conjectures
```

**Integration**:
- Replace `XGrammarIRTranslator` single-phase approach
- Use existing constraint detection (Phase 7)
- Add conjecture validation layer
- Measure conjecture accuracy separately from codegen accuracy

**Expected outcome**:
- Better insight into failure modes
- Higher IR quality (validated conjectures)
- Potentially higher codegen success (better starting point)

### 4.3 Medium-term Integration (4-6 weeks)

**Goal**: Full conjecturing-aware pipeline with CSP integration

**Combines**:
- Conjecturing framework (this paper)
- CSP approach (`CONSTRAINT_PROPAGATION_TYPED_HOLES.md`)
- Existing constraint system (Phase 7)

**Architecture**:

```python
class ConjecturingCSPTranslator:
    """
    IR generation combining conjecturing + CSP.

    Phase 1: Generate IR skeleton (conjecturing)
    Phase 2: Build CSP from holes + constraints
    Phase 3: Solve CSP (generates conjectures)
    Phase 4: Validate solution
    Phase 5: Complete IR → Code
    """

    async def translate(self, prompt: str) -> IntermediateRepresentation:
        # Conjecturing Phase 1: Skeleton
        skeleton = await self._generate_skeleton(prompt)

        # Conjecturing Phase 2: Constraints
        constraints = await self._detect_constraints(prompt, skeleton)

        # CSP Phase 1: Build problem
        csp = self._build_csp(skeleton, constraints)

        # CSP Phase 2: Solve with constraint propagation
        conjectures = await self._solve_csp(csp)

        # Conjecturing Phase 3: Validate
        if not self._validate_conjectures(conjectures, constraints):
            raise ValueError("CSP solution violates constraints")

        # Fill IR
        complete_ir = self._apply_conjectures(skeleton, conjectures)

        return complete_ir
```

**Benefits**:
- Systematic conjecture generation (CSP)
- Constraint awareness (conjecturing framework)
- Backtracking if conjectures invalid
- Clear separation of concerns

**Effort**: 4-6 weeks (combines two research directions)

### 4.4 Evaluation Framework

**New metrics** (conjecturing-inspired):

| Metric | Current | Proposed | Purpose |
|--------|---------|----------|---------|
| E2E Success | 83.3% | Keep | Overall system quality |
| IR Conjecture Accuracy | ❌ Not measured | ✅ Add | Measure conjecture quality |
| Constraint Completeness | ❌ Not measured | ✅ Add | Measure constraint detection |
| Constraint Preservation | Partial | ✅ Enhance | Measure codegen fidelity |
| Hole Resolution Success | ❌ Not measured | ✅ Add | Measure typed hole handling |

**Implementation**:

```python
class ConjecturingMetrics:
    """Metrics for evaluating conjecturing-based IR generation."""

    def evaluate_conjecture_accuracy(
        self,
        ir: IntermediateRepresentation,
        ground_truth: dict[str, Any]
    ) -> float:
        """Measure how many hole values are semantically correct."""
        holes_filled = {h.identifier: h.value for h in ir.resolved_holes()}
        correct = sum(
            1 for k, v in holes_filled.items()
            if self._semantically_equivalent(v, ground_truth.get(k))
        )
        return correct / len(holes_filled) if holes_filled else 0.0

    def evaluate_constraint_completeness(
        self,
        ir: IntermediateRepresentation,
        expected_constraints: list[Constraint]
    ) -> float:
        """Measure how many necessary constraints were detected."""
        detected = set(c.type for c in ir.constraints)
        expected = set(c.type for c in expected_constraints)
        if not expected:
            return 1.0
        return len(detected & expected) / len(expected)

    def evaluate_constraint_preservation(
        self,
        code: str,
        constraints: list[Constraint]
    ) -> float:
        """Measure how many IR constraints are honored in code."""
        violations = self.validator.validate(code, constraints)
        return 1.0 - (len(violations) / len(constraints))
```

---

## Part 5: Risk Assessment & Trade-offs

### 5.1 Benefits

1. **Theoretical grounding**: Conjecturing framework provides principled approach
2. **Better diagnostics**: Separate metrics for IR vs codegen quality
3. **Modular failures**: Can identify and fix specific phase failures
4. **Aligned with existing work**: Builds on Phase 7 constraints + CSP exploration
5. **Addresses bottleneck**: May resolve 3-failure problem by improving IR quality

### 5.2 Risks

1. **Increased complexity**: Two-phase approach adds components
2. **Latency overhead**: Separate conjecture phase may add latency
3. **Cost increase**: More LLM calls for conjecture generation
4. **Unproven for code**: Paper focuses on mathematics, not code generation
5. **May not solve failures**: 3 failures might be codegen issue, not IR issue

### 5.3 Cost Analysis

**Current approach**:
- 1 LLM call: Prompt → IR (single phase)
- N LLM calls: IR → Code (retries)
- Total: 1 + N calls

**Conjecturing approach** (lightweight):
- 1 LLM call: Prompt → IR Skeleton
- M LLM calls: Resolve M typed holes (can be parallelized)
- N LLM calls: IR → Code (potentially fewer retries)
- Total: 1 + M + N calls

**Example** (3 holes):
- Current: 1 + 3 = 4 calls (1 IR, 3 code retries)
- Conjecturing: 1 + 3 + 1 = 5 calls (1 skeleton, 3 holes, 1 code)
- **Overhead**: +25% calls, but potentially better quality

**Mitigation**: Parallel hole resolution reduces latency impact.

### 5.4 Alternative: Lightweight Diagnostic First

**Recommendation**: Start with diagnostic application (4.1) before full implementation

**Rationale**:
- Current investigation (lift-sys-229) already underway
- Conjecturing framework provides lens for analysis
- Can measure conjecture accuracy without implementing full system
- Data-driven decision on whether full system needed

**Decision tree**:
```
Week 1 Diagnostic (with conjecturing lens)
    ↓
Are IR conjectures correct?
    ↓
YES → Problem is codegen (IR→Code)
    → Solution: Semantic validation (Option 2) or LLM repair (Option 4)
    → Conjecturing framework less applicable
    ↓
NO → Problem is conjecturing (Prompt→IR)
    → Solution: Two-phase conjecturing approach (this proposal)
    → Conjecturing framework highly applicable
    ↓
MIXED → Both phases have issues
    → Solution: Conjecturing framework + semantic validation
    → Full system recommended
```

---

## Part 6: Concrete Action Plan

### Option A: Diagnostic Application (RECOMMENDED - 1 week)

**Aligned with current investigation** (lift-sys-229)

**Tasks**:
1. Add conjecture evaluation to diagnostic script:
   ```python
   # In debug/collect_failure_samples.py
   def evaluate_conjectures(ir: IntermediateRepresentation) -> dict:
       return {
           "constraints_detected": len(ir.constraints),
           "holes_present": len(ir.typed_holes()),
           "constraints_correct": manual_evaluation(ir.constraints),
           "constraint_types": [c.type.value for c in ir.constraints]
       }
   ```

2. Measure constraint preservation in generated code:
   ```python
   def evaluate_constraint_preservation(code: str, ir: IR) -> float:
       violations = constraint_validator.validate(code, ir.constraints)
       return {
           "total_constraints": len(ir.constraints),
           "violations": len(violations),
           "preservation_rate": 1.0 - (len(violations) / len(ir.constraints)),
           "violation_details": violations
       }
   ```

3. Analyze results through conjecturing lens:
   - IR conjecture quality: Are constraints complete and correct?
   - Constraint preservation: Does codegen honor IR?
   - Bottleneck identification: Conjecture vs formalisation?

**Deliverable**: `DIAGNOSTIC_REPORT_3_FAILURES_WITH_CONJECTURING.md`

**Success criteria**: Clear answer to "Is our problem bad conjectures (IR) or bad formalisation (code)?"

### Option B: Two-Phase Prototype (2 weeks)

**If diagnostic shows IR quality issues**

**Tasks**:
1. Implement `ConjecturingIRTranslator` (lightweight version)
2. Separate skeleton generation from hole resolution
3. Add conjecture validation layer
4. Measure conjecture accuracy vs current approach

**Deliverable**: Working two-phase IR generator with metrics

**Success criteria**: Higher IR quality OR better diagnostic visibility

### Option C: Full CSP Integration (4-6 weeks)

**If diagnostic shows systemic issues**

**Tasks**:
1. Combine conjecturing framework + CSP approach
2. Implement full `ConjecturingCSPTranslator`
3. Build comprehensive evaluation framework
4. Benchmark against current system

**Deliverable**: Production-ready conjecturing-aware system

**Success criteria**: Measurably higher E2E success rate (>90%)

---

## Part 7: Relationship to Existing Work

### 7.1 Complements Phase 7 (IR Constraints)

**Phase 7** (current):
- Detects constraints from natural language
- Validates code against constraints
- Provides error messages

**Conjecturing framework** (proposed):
- Uses constraints to **guide IR generation** (not just validation)
- Separates conjecture quality from codegen quality
- Treats hole resolution as explicit phase

**Integration**: Conjecturing framework builds on Phase 7, adds upstream application.

### 7.2 Complements CSP Exploration

**CSP document** (`CONSTRAINT_PROPAGATION_TYPED_HOLES.md`):
- Treats typed holes as CSP variables
- Proposes constraint propagation for hole resolution
- Systematic approach to dependencies

**Conjecturing framework** (this paper):
- Provides theoretical grounding (conjecturing as independent task)
- Adds evaluation framework (measure conjecture quality)
- Suggests iterative refinement

**Integration**: CSP provides **mechanism**, conjecturing provides **framework**.

### 7.3 Addresses Current Bottleneck

**Current situation** (`STRATEGIC_ASSESSMENT_2025-10-17.md`):
- 83.3% success rate
- 3 persistent failures
- Phase 7 had zero impact
- Investigation needed

**Conjecturing framework contribution**:
- Provides diagnostic lens (conjecture vs formalisation)
- Suggests separation of concerns
- Offers alternative approach if IR quality is issue

**Alignment**: Perfect timing - investigation underway, framework provides structure.

---

## Part 8: Conclusion & Recommendation

### 8.1 Core Insights

1. **Typed holes = Missing conjectures**: Exact parallel to paper's framework
2. **Two-phase process**: Separate conjecture (IR) from formalisation (code)
3. **Overestimated success**: Bundling obscures where failure occurs
4. **Constraint-guided generation**: Use constraints upstream, not just downstream

### 8.2 Applicability Assessment

**Relevance**: ⭐⭐⭐⭐⭐ (5/5)

**Rationale**:
- Direct conceptual parallel (holes ↔ conjectures)
- Addresses current problem (diagnostic needed)
- Complements existing work (Phase 7, CSP)
- Provides theoretical grounding
- Actionable implementation path

### 8.3 Recommended Path Forward

**Immediate** (Week 1 - IN PROGRESS):
✅ Use conjecturing framework to structure diagnostic investigation
- Evaluate IR conjecture quality (constraints correct?)
- Measure constraint preservation (codegen honors IR?)
- Identify bottleneck (conjecture vs formalisation)

**Short-term** (Weeks 2-3 - IF APPLICABLE):
⚠️ Implement lightweight two-phase IR generation
- Separate skeleton from hole resolution
- Add conjecture validation
- Measure improvement

**Medium-term** (Weeks 4-9 - IF WARRANTED):
⏸️ Full conjecturing + CSP integration
- Complete framework implementation
- Comprehensive evaluation
- Production deployment

**Decision point**: After Week 1 diagnostic
- If IR quality good → Focus on codegen (semantic validation)
- If IR quality poor → Implement conjecturing framework
- If mixed → Hybrid approach

### 8.4 Expected Outcomes

**Best case**:
- Diagnostic identifies IR quality as bottleneck
- Two-phase approach improves IR quality
- E2E success rate increases to 90%+
- 3 failures resolved

**Realistic case**:
- Better diagnostic visibility (separate metrics)
- Marginal improvement in success rate
- Clearer understanding of failure modes
- Foundation for future improvements

**Worst case**:
- Conjecturing framework doesn't apply to code (only math)
- Added complexity without benefit
- Bottleneck remains in codegen
- Pivot to semantic validation (Option 2)

### 8.5 Final Recommendation

**START WITH OPTION A**: Use conjecturing framework as diagnostic lens during current investigation.

**Rationale**:
1. ✅ Low risk (just adds structure to planned work)
2. ✅ High value (better diagnostic framework)
3. ✅ Reversible (can pivot if not applicable)
4. ✅ Aligned (fits with lift-sys-229 investigation)
5. ✅ Theoretically grounded (peer-reviewed research)

**Success metric**: Clear data-driven decision on whether full conjecturing framework needed.

---

## Appendix A: Key Quotes from Paper

> "Autoformalisation, the task of expressing informal mathematical statements in formal language, is often viewed as a direct translation process. This, however, disregards a critical preceding step: conjecturing."

**Relevance**: IR generation also viewed as direct translation (NL→IR), but may need explicit conjecturing phase (skeleton→complete).

> "Since Large Language Models (LLMs) already struggle with autoformalisation, and the evaluation of their conjecturing ability is limited and often entangled within autoformalisation or proof, it is particularly challenging to understand its effect."

**Relevance**: lift-sys struggles with E2E success (83.3%), and evaluation of IR quality (conjecturing) is entangled with codegen (formalisation).

> "The paper introduces ConjectureBench to address this gap and measure the conjecturing capabilities of LLMs."

**Relevance**: We need similar benchmark for IR conjecture quality (typed hole resolution accuracy).

---

## Appendix B: Comparison Table

| Aspect | Mathematical Reasoning (Paper) | lift-sys Code Generation |
|--------|-------------------------------|--------------------------|
| **Input** | Informal mathematical statement | Natural language prompt |
| **Missing info** | Explicit answer/bound/form | Function name, types, patterns |
| **Conjecture** | Generate hypothesis/conclusion | Fill typed holes with values |
| **Formalisation** | Convert to Lean/Coq | Convert IR to executable code |
| **Current issue** | Bundled process, unclear failures | Bundled process, 83.3% success |
| **Solution** | Separate conjecturing evaluation | Separate IR quality evaluation |
| **Framework** | ConjectureBench + Lean-FIRe | ConjecturingIRGenerator (proposed) |
| **Metrics** | Conjecture accuracy vs E2E | IR quality vs codegen quality |

---

## Appendix C: References

**Primary Paper**:
- [arXiv:2510.11986](https://arxiv.org/abs/2510.11986) - Conjecturing: An Overlooked Step in Formal Mathematical Reasoning

**Related lift-sys Documents**:
- `STRATEGIC_ASSESSMENT_2025-10-17.md` - Current diagnostic status
- `docs/CONSTRAINT_PROPAGATION_TYPED_HOLES.md` - CSP approach
- `docs/USER_GUIDE_CONSTRAINTS.md` - Phase 7 constraints
- `docs/PHASE_7_ARCHITECTURE.md` - Constraint implementation

**Related Research**:
- arXiv 2504.09246 - Type-Constrained Code Generation (cited in CSP doc)
- arXiv 2407.13490 - GenCP: LLM + Constraint Programming (cited in CSP doc)

---

**Status**: Research report complete, awaiting decision on diagnostic integration

**Next step**: Integrate conjecturing evaluation into `debug/collect_failure_samples.py` (Option A)

**Timeline**: 1 week for diagnostic, then decision point on full implementation
