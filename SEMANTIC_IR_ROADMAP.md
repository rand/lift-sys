# Semantic IR Implementation Roadmap

**Vision**: https://codelift.space - Bidirectional translation system with formal IR
**Last Updated**: 2025-10-25
**Status**: **ICS (Primary UI) Active**, Backend Partially Working, Semantic Enhancement Queued

**📌 For up-to-date status, see [CURRENT_STATE.md](CURRENT_STATE.md)**

---

## The Vision (from codelift.space)

**Core Innovation**: A bidirectional translation system centered on a **semantically rich Intermediate Representation** that:

1. **Forward Mode**: Natural Language → IR → Code
2. **Reverse Mode**: Existing Code → IR → Understanding
3. **Interactive Refinement**: AI-assisted resolution of ambiguities through "typed holes"
4. **Visual Artifacts**: IDE-style highlighting, hover states, relationship graphs

**Key Technical Innovations**:
- **Constraint Propagation**: Makes ambiguity explicit, resolves systematically
- **Context Engineering**: Preserves context across iterations
- **Semantic IR**: Transforms IR into visual, interactive artifacts

---

## Current State Assessment (October 25, 2025)

### 🎯 Active Work: ICS (Integrated Context Studio)

**PRIMARY FOCUS** - Interactive specification editor with real-time semantic analysis

**Status**:
- ✅ Phase 4 complete: 32 Beads issues created (lift-sys-308 to 339)
- 🔄 Phase 1 implementation starting (STEP-01, STEP-02)
- 🎯 Timeline: 8-10 days to MVP (22/22 E2E tests passing)
- 🚧 Blockers: H2 (DecorationApplication), H5 (Autocomplete popup)

**Why ICS First**: Provides the primary user interface AND serves as diagnostic tool to identify backend issues systematically.

---

### ⚠️ What's Built: Foundation Layer (PARTIALLY WORKING)

**Forward Mode Pipeline**: **80% Functional**
- ✅ **Compilation**: 100% success (IR → syntactically valid Python)
- ✅ **Execution**: 80% success (8/10 tests pass)
- ❌ **Known Failures**: 3 persistent (find_index, get_type_name, is_valid_email)
- ⚠️ **XGrammar**: Status uncertain, llguidance migration in progress
- ⚠️ **132 Known Gaps**: Backend issues labeled `backend-gap` (incomplete features)

**Working Components**:
- ✅ **Phase 4**: AST-Level Repair (tests passing)
- ✅ **Phase 5**: Assertion Checking (tests passing)
- ✅ **Phase 7**: IR-Level Constraints (97.8% tests passing, 87/89)

**Infrastructure**:
- ✅ **Modal.com**: Operational (LLM inference, some latency issues)
- ⏸️ **Supabase**: Schema designed, deployment pending (lift-sys-71)
- ⏸️ **Honeycomb**: Observability planned, not started

### ❌ What's Missing: Semantic Enhancement

**The gap between current state and codelift.space vision:**

**Current IR** (JSON schema):
```python
{
  "intent": "Create a function...",
  "signature": {...},
  "effects": [...],
  "assertions": [...],
  "constraints": [...]
}
```

**Target IR** (Semantic IR from spec):
```python
EnhancedIR {
  core_ir: {...},  # Current IR
  semantic_metadata: {
    entities: [Entity("report", type=Document, span=(3,9))],
    relationships: [calls("validate_report", "report")],
    typed_holes: [Hole("validation_rule", type=Function)],
    ambiguities: [Ambiguity("shareable", candidates=["public", "permissioned"])]
  },
  annotation_layer: {
    highlights: [...],  # For IDE-style visualization
    hover_content: [...],  # Tooltips with provenance
    navigation_links: [...]  # Bidirectional linking
  },
  refinement_state: {
    unresolved_holes: 3,
    pending_ambiguities: 1,
    history: [...]
  }
}
```

**Missing capabilities:**
1. ❌ Entity resolution (pronouns, references, definite/indefinite articles)
2. ❌ Typed holes for unknowns
3. ❌ Ambiguity detection (contradictions, vague terms)
4. ❌ Interactive refinement UI
5. ❌ Visual annotations (highlighting, hover states)
6. ❌ Relationship graphs
7. ❌ Reverse mode (code → IR)
8. ❌ Bidirectional navigation

---

## Revised Timeline (Updated October 25, 2025)

**Phase 0: ICS (Primary UI) - ACTIVE** (8-10 days)
- Week 1: ICS Phase 1 implementation (22/22 E2E tests passing)
- Provides primary user interface for lift-sys
- Serves as diagnostic tool for backend issues
- **Status**: Phase 4 complete, Phase 1 starting

**Phase 1: Backend Stabilization - HIGH PRIORITY** (2-3 weeks)
- Fix 3 persistent test failures (find_index, get_type_name, is_valid_email)
- Investigate XGrammar status (migrate to llguidance if needed)
- Systematic review and prioritization of 132 backend-gap issues
- Deploy Supabase (lift-sys-71)

**Phase 2: Enhancements - QUEUED** (timing TBD)
- DSPy Architecture (H1-H19): Systematic LLM orchestration
- ACE Enhancement (3 issues): Advanced code evolution
- MUSLR Enhancement (4 issues): Multi-stage reasoning
- Honeycomb observability integration

**Phase 3-8: Semantic Enhancement - QUEUED** (12 months, post-stabilization)
- See "The 6-Phase Plan" below for detailed breakdown
- Entity resolution, typed holes, ambiguity detection
- Interactive refinement UI, visualization, reverse mode
- **Timing**: Begins after ICS + backend stabilization complete

**Total Revised Timeline**:
- Near-term (1-2 months): ICS + Backend stabilization
- Medium-term (3-6 months): Enhancements (DSPy, ACE, MUSLR)
- Long-term (12 months): Full semantic enhancement (6 phases)

---

## The 6-Phase Plan (from SEMANTIC_IR_DETAILED_EXECUTION_PLAN.md)

> **⚠️ NOTE**: This plan is QUEUED pending ICS completion and backend stabilization.
> See "Revised Timeline" above for actual priorities.

### Phase 1: Foundation (Weeks 1-8) ← **START HERE**

**Goal**: Core semantic data models, entity resolution, typed holes, basic UI

**Critical Tasks** (lift-sys-70 to 86):
1. **Enhanced IR Data Models** (lift-sys-70) - 5 days
   - Entity, TypedHole, Ambiguity, Intent, SemanticMetadata
   - JSON serialization
   - 100% test coverage

2. **Database Schema** (lift-sys-71) - 3 days
   - Store semantic metadata
   - Efficient queries (<100ms)

3. **API Endpoints** (lift-sys-72) - 3 days
   - POST /analyze, GET /semantic, POST /resolve-hole

4. **NLP Infrastructure** (lift-sys-73) - 2 days
   - spaCy setup
   - Redis caching
   - Parse time monitoring

5. **Entity Resolution Pipeline** (lift-sys-74-78) - 10 days
   - Tokenization, POS tagging
   - Noun phrase extraction
   - Coreference resolution
   - Entity graph building

6. **Typed Holes System** (lift-sys-79-82) - 8 days
   - Hole detection
   - Resolution logic
   - Context-based suggestions
   - UI integration

7. **Basic UI Components** (lift-sys-83-86) - 10 days
   - Annotation generation
   - Prompt highlighter
   - Enhanced IR viewer
   - Integration testing

**Deliverables**:
- Semantic IR data models working end-to-end
- Entity resolution 90%+ accuracy
- Typed holes visible in UI
- Forward mode: Prompt → Enhanced IR (with holes)

**Success Metrics**:
- Can resolve "it" in "Create X and process it" (90%+)
- Typed holes detected for unknowns (80%+)
- UI shows highlighted entities
- Database round-trip preserves all metadata

**Estimated Effort**: 8 weeks (with current team)

---

### Phase 2: NLP & Ambiguity Detection (Weeks 9-16)

**Goal**: Deep semantic analysis, ambiguity detection, intent classification

**Critical Tasks** (lift-sys-87 to 103):
1. Clause analysis and dependency graphs
2. Contradiction detector
3. Vague term detector
4. Missing constraint detector
5. Inference rule library
6. Intent taxonomy (50+ categories)
7. Intent classifier

**Deliverables**:
- Ambiguity detection working
- Intent signatures generated
- Contradiction warnings
- Missing parameter detection

**Success Metrics**:
- 80% precision, 70% recall on ambiguity detection
- 80% intent classification accuracy
- <2s analysis time

**Estimated Effort**: 8 weeks

---

### Phase 3: Interactive Refinement UI (Weeks 17-24)

**Goal**: User can interactively resolve holes and ambiguities with AI suggestions

**Critical Tasks** (lift-sys-104 to 118):
1. Refinement panel component
2. Suggestion display
3. LLM-powered suggestion generation
4. Real-time IR update propagation
5. WebSocket for live updates
6. Consistency checking
7. Error handling

**Deliverables**:
- Interactive refinement working
- AI suggestions for holes
- Real-time IR updates
- Refinement progress tracking

**Success Metrics**:
- Users complete IR refinement in <5 minutes
- Suggestion quality 80%+ helpful
- No infinite loops in propagation
- Satisfaction >7/10

**Estimated Effort**: 8 weeks

---

### Phase 4: Visualization & Navigation (Weeks 25-32)

**Goal**: IDE-style visual experience with rich tooltips and relationship graphs

**Critical Tasks** (lift-sys-119 to 130):
1. Hover tooltip engine
2. Provenance tracking
3. Relationship graph (D3.js)
4. Interactive graph controls
5. Bidirectional navigation (prompt ↔ IR)
6. Performance optimization

**Deliverables**:
- Rich hover tooltips working
- Relationship graph visualization
- Click navigation between prompt and IR
- Provenance chains visible

**Success Metrics**:
- Tooltip load <100ms
- Graph handles 100+ nodes smoothly
- Navigation instant
- 60fps interactions

**Estimated Effort**: 8 weeks

---

### Phase 5: Reverse Mode Enhancement (Weeks 33-40)

**Goal**: Code → IR with same quality as forward mode

**Critical Tasks** (lift-sys-131 to 145):
1. AST-based entity extraction
2. Code intent inference
3. Relationship extraction
4. EnhancedIR builder from code
5. Split-view layout (code | IR)
6. Bidirectional navigation (code ↔ IR)
7. Round-trip validation

**Deliverables**:
- Reverse mode generates EnhancedIR
- Split-view working
- Synchronized highlighting
- Round-trip fidelity >90%

**Success Metrics**:
- Code→IR→Code preserves semantics (90%+)
- Split-view smooth (60fps)
- Entity extraction accuracy 85%+

**Estimated Effort**: 8 weeks

---

### Phase 6: Production Readiness (Weeks 41-52)

**Goal**: Deployed, documented, tested system with real users

**Critical Tasks** (lift-sys-146 to 162):
1. Performance profiling and optimization
2. 90%+ test coverage
3. User documentation
4. Beta program (20 testers)
5. Security audit
6. Production deployment

**Deliverables**:
- Production deployment live
- Comprehensive documentation
- Security audit passed
- Beta user feedback incorporated

**Success Metrics**:
- <2s analysis, <500ms API responses
- 90%+ test coverage
- Beta user satisfaction >8/10
- No critical security issues

**Estimated Effort**: 12 weeks

---

## Total Timeline: 12 months (52 weeks)

```
Months 1-2:  Phase 1 - Foundation (semantic data models, entity resolution)
Months 3-4:  Phase 2 - NLP & Ambiguity Detection
Months 5-6:  Phase 3 - Interactive Refinement UI
Months 7-8:  Phase 4 - Visualization & Navigation
Months 9-10: Phase 5 - Reverse Mode Enhancement
Months 11-12: Phase 6 - Production Readiness
```

---

## What We've Actually Built (Reconciliation)

The recent work (Phases 3, 5, 7 in old numbering) focused on **code generation quality** rather than **semantic IR enhancement**. This was valuable foundation work but orthogonal to the semantic IR vision.

**Foundation work complete**:
- ✅ IR generation pipeline working
- ✅ Constraint-based code generation
- ✅ Quality optimization (100% success rate)
- ✅ Performance optimization (44% latency reduction)

**This foundation enables semantic IR work** because:
1. IR schema is stable and working
2. Code generation quality is proven
3. Performance is acceptable
4. Testing infrastructure exists

**Now we can build the semantic layer on top.**

---

## Recommended Path Forward

### Option A: Full Semantic IR Vision (12 months)

**Execute the 6-phase plan as designed.**

**Pros**:
- ✅ Achieves complete codelift.space vision
- ✅ All features from website
- ✅ Comprehensive, polished product

**Cons**:
- ❌ 12 months before users see semantic features
- ❌ High complexity
- ❌ No revenue/feedback for a year

**When to choose**: If you have funding/runway for 12 months, or if this is a research project.

---

### Option B: Phased Rollout (3-6 months to first value)

**Build Phase 1 only, then get users.**

**Phase 1 deliverable** (2 months):
- Semantic IR data models
- Entity resolution working
- Typed holes visible in UI
- Basic refinement (manual hole filling)

**Value to users**:
- See what entities/types the system detected
- Manually clarify ambiguities
- Better understanding of IR

**Then iterate based on feedback**:
- Month 3: If users need it, add ambiguity detection (Phase 2)
- Month 4: If users need it, add AI suggestions (Phase 3)
- Month 5+: Build requested features

**Pros**:
- ✅ User feedback in 2 months
- ✅ Revenue potential sooner
- ✅ Validates assumptions

**Cons**:
- ❌ Incomplete vision
- ❌ May need rework

---

### Option C: Hybrid - Core Features First (6 months)

**Build the "must-have" semantic IR features, defer nice-to-haves.**

**Months 1-2**: Phase 1 (Foundation)
- Enhanced IR data models
- Entity resolution
- Typed holes
- Basic UI

**Months 3-4**: Phase 3 (Interactive Refinement) - SKIP Phase 2
- AI-powered suggestions
- Real-time updates
- Interactive hole resolution
- Skip: Full ambiguity detection (add later if needed)

**Months 5-6**: Phase 5 (Reverse Mode) - SKIP Phase 4
- Code → IR
- Split-view
- Skip: Fancy graphs, provenance viz (add later)

**Result after 6 months**:
- ✅ Bidirectional translation (forward + reverse)
- ✅ Interactive refinement with AI
- ✅ Typed holes
- ✅ Entity resolution
- ⏸️ Defer: Full ambiguity detection, relationship graphs, provenance viz

**Pros**:
- ✅ Core vision delivered in 6 months
- ✅ Bidirectional working
- ✅ Interactive refinement working
- ✅ Faster to market

**Cons**:
- ❌ Missing some polish features
- ❌ May need to add Phase 2/4 later

---

## My Recommendation: **Option C (Hybrid)**

**Why**:
1. **Core vision achieved**: Bidirectional translation + interactive refinement
2. **Faster to value**: 6 months vs 12 months
3. **Validate early**: Users see working system sooner
4. **Defer complexity**: Ambiguity detection and graphs can be added if needed

**Execution**:
1. **Month 1-2**: Phase 1 (Foundation)
   - Start with lift-sys-70: Enhanced IR data models
   - Focus on entity resolution and typed holes
2. **Month 3-4**: Phase 3 (Interactive Refinement)
   - Skip full Phase 2 ambiguity detection for now
   - Focus on AI-powered suggestions and real-time updates
3. **Month 5-6**: Phase 5 (Reverse Mode)
   - Skip Phase 4 visualization complexity
   - Focus on code → IR working
4. **Month 7+**: Production deployment + iterate based on feedback

---

## Immediate Next Steps (This Week)

### 1. Close out current work
```bash
bd close lift-sys-178 --reason "IR Interpreter complete"
bd close lift-sys-252 --reason "Phase 3 optimization complete"
bd close lift-sys-232 --reason "Parallel benchmarks working, aggregation deferred"
```

### 2. Mark Phase 1 as current focus
```bash
bd update lift-sys-70 --status in_progress
bd update lift-sys-71 --status open
bd update lift-sys-72 --status open
bd update lift-sys-73 --status open
```

### 3. Start implementing lift-sys-70: Enhanced IR Data Models

**Task**: Implement semantic metadata classes in `lift_sys/ir/semantic_models.py`

**Classes to implement**:
- Entity, EntityType, SemanticType
- Span, Relationship
- TypedHole, Ambiguity, ImplicitTerm
- Intent (with hierarchy)
- SemanticMetadata (container)
- AnnotationLayer
- RefinementState, RefinementStep
- EnhancedIR (wrapper combining all layers)

**Acceptance criteria**:
- All classes with docstrings and type hints
- JSON serialization (to_dict/from_dict)
- No data loss in round-trip
- 100% test coverage

**Estimate**: 5 days

**Files**:
- `lift_sys/ir/semantic_models.py` (~800 lines)
- `tests/unit/test_semantic_models.py` (~400 lines)

---

## Success Metrics (6-month plan)

**After 2 months (Phase 1)**:
- Enhanced IR data models working
- Entity resolution 90%+ accuracy
- Typed holes detected and visible in UI

**After 4 months (Phase 1 + 3)**:
- Interactive refinement working
- AI suggestions for hole resolution
- Real-time IR updates

**After 6 months (Phase 1 + 3 + 5)**:
- Bidirectional translation working (NL→IR→Code AND Code→IR)
- Split-view UI functional
- Round-trip fidelity >90%

**Deliverable**: A working codelift.space system with the core vision:
- ✅ Bidirectional translation
- ✅ Interactive refinement
- ✅ Typed holes
- ✅ Entity resolution
- ⏸️ Defer: Full ambiguity detection, fancy visualizations (add if users request)

---

**Status**: Ready to start Phase 1, Task 1 (lift-sys-70)
**Timeline**: 6 months to core vision
**Next Action**: Implement Enhanced IR data models
