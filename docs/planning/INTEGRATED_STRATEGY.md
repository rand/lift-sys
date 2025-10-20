# Lift-Sys: Integrated IR + DSPy Strategy

**Date**: 2025-10-20
**Status**: Strategic Planning
**Related Documents**:
- [IR Adoption Plan](IR_ADOPTION_PLAN.md) - 20-month plan for IR 0.9
- [DSPy Migration Plan](DSPY_MIGRATION_PLAN.md) - 14-month plan for AI optimization
- [IR Specification v0.9](../IR_SPECIFICATION.md)
- [Semantic IR Roadmap](../../SEMANTIC_IR_ROADMAP.md)

---

## Executive Summary

This document outlines the **integrated strategy** for simultaneously adopting:
1. **IR 0.9 Specification**: Advanced semantic IR with dependent types, refinements, solvers, and hole closures
2. **DSPy Framework**: Systematic AI optimization replacing manual prompt engineering

**Why Both?**
- **IR 0.9** provides the **semantic foundation** for representing programs formally
- **DSPy** provides the **AI optimization infrastructure** for generating and refining that IR

Together, they enable the **codelift.space vision**: A bidirectional translation system with formal verification, interactive refinement, and continuous AI improvement.

**Timeline**: 20 months total (some parallelism)
**Investment**: ~6-8 FTE, ~$90K infrastructure
**Risk**: Medium - Large scope, but phased approach with clear go/no-go points

---

## The Vision

### What We're Building

**codelift.space**: A revolutionary code translation system with:

1. **Forward Mode**: Natural Language → IR → Verified Code
   - User writes intent in plain language or Spec-IR
   - AI generates formal IR with typed holes for ambiguities
   - Solver verifies constraints before code generation
   - User fills holes interactively with AI suggestions

2. **Reverse Mode**: Code → IR → Understanding
   - AI extracts semantic intent from existing code
   - Generates formal specifications with provenance
   - Detects ambiguities and missing constraints
   - Enables safe refactoring via IR transformations

3. **Interactive Refinement**: Holes + Partial Evaluation + AI Suggestions
   - Execute programs with holes to see what flows through
   - AI suggests fills based on context and traces
   - Systematic optimization improves suggestions over time
   - Provenance tracks all decisions

4. **Production Safety**: Verification + Manifests + Telemetry
   - SMT solver verifies contracts before deployment
   - Safety manifests enforce policies (SBOM, SLSA, OPA)
   - OpenTelemetry traces all IR operations
   - Intent ledger provides full audit trail

### The Gap Today

**Current State (October 2025)**:
- ✅ Basic IR (intent, signature, effects, assertions)
- ✅ Simple typed holes
- ✅ Code generation working (100% success, 38s latency)
- ✅ XGrammar-constrained generation
- ✅ Modal deployment + Supabase storage

**Missing for Vision**:
- ❌ No dependent types or refinements
- ❌ No solver integration (CSP/SAT/SMT)
- ❌ No hole closures / partial evaluation
- ❌ No surface syntax (Spec-IR)
- ❌ No intent/func alignment or provenance
- ❌ AI components use brittle manual prompts
- ❌ No systematic AI optimization
- ❌ No continuous learning from feedback

**These plans close the gap.**

---

## The Two Tracks

### Track 1: IR Adoption (Bottom-Up)

**What**: Implement IR 0.9 specification features
**Approach**: Data models → Solvers → Evaluation → Syntax → Provenance → Production
**Duration**: 20 months
**Phases**:
1. **Months 1-3**: Core types & refinements
2. **Months 4-6**: Solver integration (SMT/SAT/CSP)
3. **Months 7-10**: Hole closures & partial evaluation
4. **Months 11-14**: Surface syntax & parsing (Spec-IR)
5. **Months 15-18**: Alignment & provenance tracking
6. **Months 19-20**: Safety manifests & production

**Key Deliverables**:
- Dependent types: `Π(x:T).U`
- Refinement types: `{x:T | φ}`
- Enhanced holes (6 kinds: term, type, spec, entity, function, module)
- SMT/SAT/CSP solver integration with Z3
- Partial evaluator with hole closures
- Spec-IR surface syntax + parser + LSP
- IntentSpec ↔ FuncSpec alignment with drift detection
- Intent ledger + provenance chains
- Safety manifests (SBOM, SLSA, OPA)

### Track 2: DSPy Migration (Top-Down)

**What**: Migrate all AI components to DSPy
**Approach**: Forward mode → Reverse mode → Ambiguity → Entity → Continuous learning
**Duration**: 14 months (starts Month 4 after IR stabilizes)
**Phases**:
1. **Months 4-6**: DSPy setup + Forward mode (NL → IR)
2. **Months 7-9**: Reverse mode (Code → IR with AI)
3. **Months 10-12**: Ambiguity detection + hole suggestions
4. **Months 13-15**: Entity resolution + intent extraction
5. **Months 16-17**: Continuous learning + production

**Key Deliverables**:
- DSPy signatures for all AI tasks
- Forward mode: `PromptToIR`, `RefineIR`, `ExtractIntent`
- Reverse mode: `ExtractIntentFromCode`, `InferTypeFromUsage`
- Ambiguity: `DetectSemanticAmbiguities`, `SuggestHoleFill`
- Semantic: `ResolveEntities`, `ClassifyIntent`, `ExtractRelationships`
- Optimizers: BootstrapFewShot, MIPROv2
- Continuous learning pipeline
- Model versioning & registry

---

## Integration Points (Where Tracks Meet)

### 1. Month 4: IR Types → DSPy Signatures

**IR Side**: Core types & refinements complete
**DSPy Side**: Start Forward mode migration

**Integration**:
```python
# DSPy signatures now generate new IR format
class PromptToIR(dspy.Signature):
    """Generate IR 0.9 with refinement types and holes."""

    prompt: str = dspy.InputField(...)

    ir_json: str = dspy.OutputField(
        desc="Valid IR 0.9 JSON with refinement types {x:T | φ}"
    )

# Generated IR now includes refinements
{
  "signature": {
    "parameters": [{
      "name": "x",
      "type": {"kind": "refinement", "base": "int", "predicate": "x >= 0"}
    }]
  }
}
```

**Benefit**: DSPy generates richer IR from day 1

---

### 2. Month 7: Solvers → DSPy Training

**IR Side**: SMT/SAT/CSP solvers working
**DSPy Side**: Reverse mode migration starting

**Integration**:
```python
# Solver counterexamples become training data
def collect_solver_feedback():
    """Use solver counterexamples to improve IR generation."""
    examples = []

    for session in failed_validations:
        # Solver found unsatisfiable constraint
        counterexample = solver.get_counterexample()

        # Create training example: "Don't generate this pattern"
        examples.append(
            dspy.Example(
                prompt=session.prompt,
                bad_ir=session.generated_ir,  # Failed validation
                solver_error=counterexample.explanation,
                expected_ir=session.corrected_ir  # After user fix
            )
        )

    # Re-optimize with negative examples
    optimizer.compile(ir_generator, trainset=examples, negative_examples=True)
```

**Benefit**: Solver failures improve AI quality over time

---

### 3. Month 10: Hole Closures → DSPy Suggestions

**IR Side**: Hole closures & partial evaluation working
**DSPy Side**: Hole suggestion module starting

**Integration**:
```python
# Hole traces inform AI suggestions
class HoleSuggester(dspy.Module):
    def forward(self, hole: Hole, ir: IR):
        # Use hole closure traces as context
        trace = get_hole_trace(hole.identifier)

        # Extract value flows through hole
        value_examples = trace.values_in[:5]  # Top 5 values

        # Ask AI to generalize from examples
        result = self.suggest(
            hole_type=hole.type_annotation,
            value_examples=json.dumps(value_examples),
            context=json.dumps(trace.contexts)
        )

        return result.suggestions

# Example: Hole saw values [1, 2, 5, 10] flow through
# AI suggests: "positive integer" or "{x:Int | x > 0}"
```

**Benefit**: Partial evaluation evidence makes suggestions context-aware

---

### 4. Month 14: Surface Syntax → DSPy Parsing

**IR Side**: Spec-IR surface syntax + parser working
**DSPy Side**: Entity resolution module starting

**Integration**:
```python
# DSPy can now work with Spec-IR text
class SpecIRGenerator(dspy.Module):
    """Generate Spec-IR surface syntax (not just JSON)."""

    def forward(self, prompt: str):
        result = self.generate(
            prompt=prompt,
            output_format="spec-ir"  # Surface syntax
        )

        # Returns human-friendly Spec-IR:
        # intent "Summarize document":
        #   inputs: doc:Str, N:Nat
        #   outputs: bullets:List Str
        #   goals:
        #     - length(bullets) = N
        #
        # def summarize(doc:Str, N:Nat) :
        #   {bullets:List Str | length(bullets)=N} =
        #   ?impl:term

        return result.spec_ir_text
```

**Benefit**: AI generates human-readable specs, not just JSON

---

### 5. Month 18: Provenance → DSPy Optimization History

**IR Side**: Intent ledger + provenance tracking complete
**DSPy Side**: Continuous learning pipeline complete

**Integration**:
```python
# Provenance tracks DSPy optimization decisions
class ProvenanceTracker:
    def record_dspy_optimization(self, event: OptimizationEvent):
        """Record DSPy optimization in intent ledger."""
        self.ledger.record(LedgerEvent(
            kind="AIOptimized",
            targets=[event.module_name],
            diff={
                "model_version": f"v{event.old_version} → v{event.new_version}",
                "metric_improvement": f"{event.old_score:.3f} → {event.new_score:.3f}",
                "training_examples": len(event.trainset)
            },
            effects={
                "ir_generations": event.affected_sessions,
                "optimized_prompts": event.updated_prompts
            },
            justification=f"Optimized from {len(event.trainset)} user feedback examples"
        ))

# Query: "Why did the IR generation change for prompt X?"
# Answer: "AI model v5 → v6 optimized on 2025-10-15 with 127 examples,
#          improving intent extraction accuracy from 0.78 to 0.85"
```

**Benefit**: Full audit trail of AI improvements

---

## Timeline (Integrated View)

```
Month   IR Adoption Track                DSPy Migration Track           Integration
───────────────────────────────────────────────────────────────────────────────────────
1-3     Phase 1: Types & Refinements     (Prep: install DSPy)
                                         (Collect training data)

4-6     Phase 2: Solver Integration      Phase 1: Forward Mode          ✅ DSPy generates
                                         - Setup infrastructure            new IR format
                                         - NL → IR with DSPy            ✅ Solver feedback
                                         - Optimization pipeline           → training data

7-10    Phase 3: Hole Closures           Phase 2: Reverse Mode          ✅ Hole traces
        - Partial evaluator              - Code → IR with AI               inform AI
        - Trace collection               - Intent extraction               suggestions
        - Fill-and-resume                - Type inference

11-14   Phase 4: Surface Syntax          Phase 3: Hole Suggestions      ✅ AI generates
        - Spec-IR grammar + parser       - Ambiguity detection             Spec-IR syntax
        - LSP server                     - AI-powered suggestions       ✅ Entity resolution
        - Diagnostics                    - Feedback loop                   for parsing

15-18   Phase 5: Alignment               Phase 4: Entity Resolution     ✅ Provenance tracks
        - IntentSpec ↔ FuncSpec          - Entity resolution               DSPy optimizations
        - Intent ledger                  - Intent classification        ✅ Alignment uses
        - Provenance tracking            - Relationship extraction         AI classification

19-20   Phase 6: Production              Phase 5: Continuous Learning   ✅ Full integration
        - Safety manifests               - Optimization pipeline        ✅ Production ready
        - Policy gates                   - Model versioning
        - Telemetry                      - Monitoring
```

**Total Duration**: 20 months
**Parallel Work**: DSPy starts Month 4, runs concurrently with IR
**Critical Path**: IR adoption (DSPy depends on IR stability)

---

## Resource Allocation

### Team Composition

| Role | Allocation | Work On |
|------|-----------|---------|
| **Tech Lead** | Full-time (20 months) | Architecture, integration, reviews |
| **Senior Eng #1** | Full-time (20 months) | IR adoption (all phases) |
| **Senior Eng #2** | Full-time (17 months) | DSPy migration (Month 4-20) |
| **ML Engineer** | Full-time (14 months) | DSPy optimization, training (Month 4-17) |
| **PL Specialist** | 6 months | IR evaluator + hole closures (Month 7-12) |
| **Solver Specialist** | 3 months | SMT/SAT/CSP integration (Month 4-6) |
| **NLP Specialist** | 3 months | Entity resolution (Month 13-15) |
| **Frontend Eng** | 5 months | Surface syntax LSP + UI (Month 11-15) |
| **DevOps** | Part-time | Infrastructure, deployment |
| **Tech Writer** | Part-time | Documentation (Month 19-20) |

**Peak Team Size**: 6-7 FTE (Months 11-15)
**Average Team Size**: 4-5 FTE
**Total Effort**: ~80 engineer-months

### Budget

**Infrastructure** (20 months):
- Modal.com: $2K/month × 20 = $40K
- Supabase Pro: $500/month × 20 = $10K
- DSPy/LLM compute: $1.5K/month × 17 = $25.5K
- CI/CD: $200/month × 20 = $4K
- Monitoring: $200/month × 20 = $4K
- **Total Infrastructure**: ~$83.5K

**Personnel** (assuming $150K avg loaded cost):
- ~80 engineer-months × $12.5K/month = ~$1M

**Total Program Cost**: ~$1.08M

---

## Risk Management

### Critical Risks

#### 1. IR Complexity Overwhelming Users
**Risk**: New IR too complex, users don't adopt

**Mitigation**:
- **Progressive disclosure**: Simple types work without refinements
- **Excellent diagnostics**: Ariadne-style errors with suggestions
- **Surface syntax**: Human-friendly, not JSON
- **Examples & templates**: Ship 50+ curated examples
- **User testing**: Beta program with 20 users (Month 18)

**Go/No-Go**: Month 14 (after surface syntax)
- If users struggle, simplify before proceeding

---

#### 2. Solver Performance Unacceptable
**Risk**: SMT queries too slow for interactive use

**Mitigation**:
- **Tiered approach**: CSP → SAT → SMT (fastest first)
- **Caching**: Cache solver results
- **Incremental**: Use Z3's incremental solving
- **Timeouts**: 5s budget, fallback to heuristics
- **Optimization**: Profile and optimize queries

**Go/No-Go**: Month 6 (after solver integration)
- If >10% queries timeout, redesign approach

---

#### 3. DSPy Doesn't Outperform Manual Prompts
**Risk**: DSPy optimization worse than current prompts

**Mitigation**:
- **A/B testing**: Compare before switching
- **Extensive training data**: 100+ examples per task
- **Multiple optimizers**: Try Bootstrap, MIPRO, BayesOpt
- **Feature flags**: Easy rollback
- **Incremental**: One component at a time

**Go/No-Go**: Month 6 (after first DSPy migration)
- If DSPy worse, continue with manual prompts

---

#### 4. Timeline Slippage
**Risk**: 20 months stretches to 30+

**Mitigation**:
- **Phased approach**: Clear milestones
- **Go/no-go points**: Stop/pivot if needed
- **Parallel work**: IR and DSPy concurrent
- **Scope cuts**: Defer nice-to-haves
- **Monthly reviews**: Track progress

**Contingency**:
- Can cut Phase 4 (surface syntax) and use JSON longer
- Can cut Phase 5 continuous learning and optimize manually

---

### Medium Risks

#### 5. Training Data Quality
**Mitigation**: Manual curation + synthetic generation + user feedback

#### 6. Integration Bugs
**Mitigation**: Extensive testing, staged rollout, monitoring

#### 7. Team Turnover
**Mitigation**: Documentation, knowledge sharing, pair programming

---

## Success Metrics

### Technical Milestones (Go/No-Go Decision Points)

**Month 3 (IR Phase 1)**:
- ✅ Type system works for all IR 0.9 examples
- ✅ Backward compatibility ≥95%
- ✅ Team confident in approach

**Month 6 (IR Phase 2 + DSPy Phase 1)**:
- ✅ SMT solver detects 90%+ unsatisfiable specs
- ✅ Solver time <5s for 90% queries
- ✅ DSPy forward mode ≥10% better than baseline

**Month 10 (IR Phase 3 + DSPy Phase 2)**:
- ✅ Partial evaluation works
- ✅ Hole traces useful (user study >7/10)
- ✅ AI-extracted intent preferred over generic

**Month 14 (IR Phase 4 + DSPy Phase 3)**:
- ✅ Users can author Spec-IR
- ✅ LSP hover/completion works
- ✅ Hole suggestions 60%+ acceptance rate

**Month 18 (IR Phase 5 + DSPy Phase 4)**:
- ✅ Alignment detects drift 90%+ accuracy
- ✅ Entity resolution 90%+ accuracy
- ✅ System stable, ready for beta

**Month 20 (Production)**:
- ✅ Beta user satisfaction >8/10
- ✅ No critical bugs
- ✅ All safety gates pass

### Product Metrics (End State)

**Quality**:
- Spec-to-code success rate: >90% (up from 60% today)
- Code-to-spec fidelity: >85%
- Ambiguity detection: 70%+ precision/recall
- Hole suggestion acceptance: 60%+

**Performance**:
- IR generation: <5s (maintained)
- Solver queries: <5s for 90%
- Hole suggestions: <2s

**Adoption**:
- 50+ active users by Month 12
- 200+ active users by Month 18
- 1000+ specs created by Month 20

**Satisfaction**:
- User satisfaction: >8/10
- "Would recommend": >80%
- User retention: >70%

---

## Comparison: Old vs New System

| Aspect | Current (Oct 2025) | After IR + DSPy (2027) |
|--------|-------------------|----------------------|
| **IR** | Simple JSON | Dependent types, refinements, holes (6 kinds) |
| **Types** | Basic (str, int) | Refinement types `{x:T \| φ}` |
| **Verification** | None | SMT/SAT/CSP solver checks |
| **Execution** | Code generation only | Partial evaluation with hole closures |
| **Syntax** | JSON only | Spec-IR (human-friendly) + JSON |
| **AI** | Manual prompts | DSPy signatures + optimizers |
| **Learning** | None | Continuous optimization from feedback |
| **Ambiguity** | Rule-based (low quality) | AI semantic detection (high quality) |
| **Suggestions** | None | AI-powered, context-aware |
| **Provenance** | None | Full intent ledger + provenance chains |
| **Safety** | None | Manifests, SBOM, SLSA, OPA policies |
| **Forward Mode** | NL → IR → Code | NL/Spec-IR → IR → Solver → Code |
| **Reverse Mode** | Code → IR (heuristics) | Code → IR (AI-powered) |
| **Quality** | 60% real success | 90% success with verification |

**It's a complete transformation.**

---

## Communication Strategy

### Internal (Team)

**Weekly Standups**:
- Progress on IR and DSPy tracks
- Integration blockers
- Risk updates

**Monthly Reviews**:
- Demo new capabilities
- Metrics review
- Go/no-go decisions

**Docs**:
- Update README with progress
- Architecture docs in `docs/`
- API docs auto-generated

### External (Users/Stakeholders)

**Monthly Updates** (Blog/Newsletter):
- "Month 3: Type System Complete"
- "Month 6: Solvers Integrated, DSPy Live"
- "Month 10: Partial Evaluation Demo"
- "Month 14: Spec-IR Syntax Released"
- "Month 18: Beta Program Launch"

**Beta Program** (Month 18-20):
- 20 selected users
- Weekly office hours
- Feedback surveys
- Feature requests tracked

**Launch** (Month 20):
- Public announcement
- Documentation site
- Tutorial videos
- Conference talk

---

## Next Steps

### This Week
1. ✅ **Plans Complete**: IR Adoption + DSPy Migration + Integration Strategy
2. ⬜ **Team Review**: Schedule 2-hour review meeting
3. ⬜ **Stakeholder Buy-In**: Present to leadership
4. ⬜ **Budget Approval**: Get funding commitment
5. ⬜ **Hiring Plan**: Identify if we need to hire (PL specialist, ML eng, etc.)

### Next 2 Weeks
1. ⬜ **Kickoff**: Team kickoff meeting
2. ⬜ **Setup**: Install dependencies (DSPy, Z3, etc.)
3. ⬜ **Beads**: Create Phase 1 beads for both tracks
4. ⬜ **Training Data**: Start collecting DSPy training examples
5. ⬜ **IR Phase 1.1**: Begin Type System Foundation (Week 1-2 of 20-month plan)

### Month 1
1. ⬜ **IR**: Complete Type System + Predicate System
2. ⬜ **DSPy**: Collect 50+ training examples for Forward Mode
3. ⬜ **Monitoring**: Set up metrics tracking
4. ⬜ **Docs**: Update architecture docs

---

## Conclusion

This integrated strategy transforms lift-sys from a promising prototype into the **codelift.space production system**:

### What We're Building
- **Formal IR** with dependent types, refinements, solvers (IR 0.9 spec)
- **Interactive refinement** with hole closures and partial evaluation
- **AI optimization** with DSPy (no more prompt hacking)
- **Provenance tracking** with intent ledger and alignment maps
- **Production safety** with solver verification and policy gates

### Why It Matters
- **Users write intent**, system ensures correctness
- **Code becomes understandable** via reverse mode
- **AI gets better over time** via continuous learning
- **Full audit trail** for regulatory compliance
- **Safe refactoring** via verified IR transformations

### The Path
- **20 months** to full vision
- **6 phases** with clear go/no-go points
- **2 tracks** (IR + DSPy) converge at integration points
- **~$1.1M** investment (mostly personnel)
- **Phased rollout** with beta testing before launch

### The Result
A system that finally delivers on the promise:
> "Stop writing code. Describe what you want. We'll make it correct."

---

**Status**: Ready for team review and approval
**Next Action**: Schedule review meeting with full team
**Owners**: Tech Lead + Engineering Manager + Product Lead

**Let's build this.**
