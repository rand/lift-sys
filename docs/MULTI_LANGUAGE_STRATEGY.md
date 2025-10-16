# Multi-Language Support Strategy

**Date**: October 16, 2025
**Status**: Strategic requirement for production
**Constraint**: Must maintain control and precision (no long-term Claude dependency)

---

## Production Requirement

**Goal**: Support Python, TypeScript, Rust, Go as first-class languages in production

**Rationale**:
- Different teams use different languages
- Code analysis must work across language boundaries
- IR should be truly language-agnostic

**Non-negotiable**: This is not optional—it's a production requirement.

---

## Phased Approach

### Phase 1: Python Excellence (Weeks 1-3)
**Goal**: Achieve 80%+ on Python with full control

**Why Python first**:
- Most test data and validation infrastructure
- Fastest iteration cycle
- Proves IR schema and approach work
- Establishes quality bar for other languages

**Deliverables**:
- ✅ Python IR generation at ≥80%
- ✅ Python code generation validated
- ✅ Test suite comprehensive
- ✅ Modal infrastructure optimized

**Success criteria**: Sustainable 80%+ on Phase 3 tests

### Phase 2: Language-Agnostic IR Design (Weeks 4-8)
**Goal**: Evolve IR schema to support multiple languages

**Approach**: Incremental enhancement, not rewrite

**Key changes**:
1. **Separate language-specific from language-agnostic**
   ```python
   # Language-agnostic (keep)
   - Control flow (loops, conditionals, returns)
   - Type system (generics, constraints)
   - Effects (semantic descriptions)

   # Language-specific (abstract)
   - Syntax details
   - Standard library calls
   - Language quirks
   ```

2. **Add language abstraction layer**
   ```python
   class LanguageAdapter:
       """Maps language-agnostic IR to language-specific code."""
       def generate_loop(self, ir_loop: LoopIR) -> str:
           # Python: "for x in range(n):"
           # Rust: "for x in 0..n {"
           # TypeScript: "for (let x = 0; x < n; x++) {"
   ```

3. **Compiler-inspired IR elements**
   - Control Flow Graph (CFG) representation
   - Basic blocks and dominance
   - Static Single Assignment (SSA) form
   - Type inference results

**Deliverables**:
- Enhanced IR schema (v2.0)
- Python adapter (maintains 80%+ quality)
- Design for TypeScript, Rust, Go adapters
- Migration path from v1.0 to v2.0

**Success criteria**: Python quality maintained or improved with new IR

### Phase 3: TypeScript Support (Weeks 9-12)
**Goal**: Second language proves language-agnostic IR works

**Why TypeScript**:
- Similar to Python (high-level, GC'd)
- Different enough (structural typing, async/await)
- Large user base and test data available

**Approach**:
1. Implement TypeScript language adapter
2. Port Phase 3 tests to TypeScript
3. Measure quality (target: ≥75% initial)
4. Iterate to match Python quality (≥80%)

**Deliverables**:
- TypeScript adapter implementation
- TypeScript test suite (18+ tests)
- TypeScript code generation at ≥80%
- Documentation for adding new languages

**Success criteria**: TypeScript ≥80% and Python still ≥80%

### Phase 4: Systems Languages (Weeks 13-20)
**Goal**: Add Rust and Go to prove approach works for systems languages

**Why Rust and Go**:
- Memory management complexity
- Different paradigms (ownership, goroutines)
- Production requirements

**Approach**:
1. **Rust adapter** (Weeks 13-16)
   - Handle ownership and borrowing in IR
   - Lifetime annotations
   - Result<T, E> vs exceptions
   - Target: ≥75% → ≥80%

2. **Go adapter** (Weeks 17-20)
   - Handle channels and goroutines
   - Error handling conventions
   - Interface satisfaction
   - Target: ≥75% → ≥80%

**Deliverables**:
- Rust adapter + test suite ≥80%
- Go adapter + test suite ≥80%
- Multi-language E2E tests
- Production readiness assessment

**Success criteria**: All 4 languages at ≥80%

---

## IR Evolution Strategy

### Current IR (v1.0) - Python-focused
```python
signature: "add(x: int, y: int) -> int"
effects: [
    "Adds x and y together",
    "Returns the sum"
]
assertions: [
    "x and y are integers",
    "Result is x + y"
]
```

### Enhanced IR (v2.0) - Language-agnostic
```python
signature: {
    "name": "add",
    "params": [
        {"name": "x", "type": {"kind": "integer", "bits": 32}},
        {"name": "y", "type": {"kind": "integer", "bits": 32}}
    ],
    "return": {"kind": "integer", "bits": 32}
}
control_flow: {
    "blocks": [
        {
            "id": "entry",
            "operations": [
                {"op": "binary_add", "lhs": "x", "rhs": "y", "result": "sum"}
            ],
            "terminator": {"kind": "return", "value": "sum"}
        }
    ]
}
semantics: {
    "effects": ["Adds x and y together"],
    "preconditions": ["x and y are valid integers"],
    "postconditions": ["Result equals x + y"]
}
```

### Migration Path
1. **Weeks 4-6**: Design v2.0 schema
2. **Weeks 6-8**: Implement v2.0 generation, maintain v1.0 compatibility
3. **Weeks 8-10**: Migrate Python to v2.0
4. **Weeks 10+**: Add languages using v2.0

---

## Control and Precision Requirements

### Model Strategy
**No Claude long-term** means:

1. **Fine-tune on Qwen family**
   - Week 4: Collect (prompt, IR) training data from Python success
   - Week 5: Fine-tune Qwen2.5-32B with LoRA
   - Week 6: Validate fine-tuned model ≥ baseline
   - Weeks 7-8: Deploy fine-tuned model on Modal

2. **Language-specific fine-tuning**
   - After each language reaches 80%, collect training data
   - Fine-tune language-specific adapters
   - Maintain single base model + adapters

3. **Deterministic components**
   - Use AST repair for known patterns
   - SMT verification for correctness guarantees
   - Constraint propagation for systematic hole filling

### Infrastructure Control
**Full Modal control**:
- Own GPU infrastructure (no API dependencies)
- Custom model serving (vLLM + XGrammar)
- Flexible scaling and cost optimization
- Complete telemetry and debugging

---

## Research Alignment

### Semantic IR (224 Beads)
**Now validated as essential**, not optional

**Revised timeline**:
- Phase 1 (Enhanced IR Data Models): Weeks 4-8
- Phase 2 (NLP & Ambiguity Detection): Weeks 9-12
- Phase 3 (Interactive Refinement UI): Weeks 13-16
- Phases 4-6: Weeks 17-24 (parallel with language rollout)

**Key adjustment**: Execute incrementally alongside language support

### Constraint Propagation (lift-sys-181)
**Becomes more important with multi-language**

**Why**: Language-agnostic constraint solving
- CFG constraints are language-independent
- Type constraints map across languages
- Control flow patterns universal

**Revised timeline**:
- Start after Python ≥80% (Week 4)
- Implement alongside Semantic IR Phase 1
- Deploy for all languages simultaneously

---

## Concrete Milestones

### Week 1 (Now)
- [ ] Temperature=0.8 Best-of-N test
- [ ] Python baseline ≥80% achieved
- [ ] Begin Semantic IR v2.0 design

### Week 4
- [ ] Semantic IR v2.0 schema complete
- [ ] Python maintains ≥80% with v2.0
- [ ] Start constraint propagation Phase 0

### Week 8
- [ ] Python at ≥85% with optimizations
- [ ] Semantic IR v2.0 deployed
- [ ] Constraint propagation Phase 2 complete

### Week 12
- [ ] TypeScript at ≥80%
- [ ] Fine-tuned model deployed
- [ ] Multi-language IR validated

### Week 20
- [ ] Python, TypeScript, Rust, Go all ≥80%
- [ ] Production deployment ready
- [ ] Documentation complete

---

## Risk Mitigation

### Risk: IR redesign breaks Python quality
**Mitigation**:
- Maintain v1.0 compatibility during transition
- Extensive regression testing
- Rollback plan to v1.0 if needed

### Risk: Language-specific quirks require separate IRs
**Mitigation**:
- Abstraction layers for language-specific details
- Shared semantic core, language-specific adapters
- Early prototyping with TypeScript to validate approach

### Risk: Fine-tuning doesn't match Claude quality
**Mitigation**:
- Use Claude-generated data for training if needed (synthetic data)
- Multi-stage fine-tuning (general → language-specific)
- Continuous improvement with production data

### Risk: 80% on Python but <70% on other languages
**Mitigation**:
- Invest more in language-specific training data
- Language experts review IR schema
- Iterate on adapter design before committing

---

## Success Metrics

### Short-term (Weeks 1-3)
- ✅ Python ≥80% sustained
- ✅ Cost per success <$0.02
- ✅ Infrastructure stable

### Medium-term (Weeks 4-12)
- ✅ Semantic IR v2.0 deployed
- ✅ TypeScript ≥80%
- ✅ Python maintained at ≥80%

### Long-term (Weeks 13-20)
- ✅ All 4 languages ≥80%
- ✅ Production deployment ready
- ✅ No external API dependencies

---

## Immediate Next Steps

1. **Today**: Temperature=0.8 Best-of-N experiment
2. **This week**: Reach Python ≥80% with existing infrastructure
3. **Next week**: Begin Semantic IR v2.0 design (parallel with Python optimization)
4. **Week 4**: Start implementation of language-agnostic components

**The strategy**: Prove Python works, then evolve IR for multi-language while maintaining Python quality.
