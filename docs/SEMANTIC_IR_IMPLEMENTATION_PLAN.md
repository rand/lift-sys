# Semantic IR Implementation Plan

**Status**: Planning
**Created**: 2025-10-15
**Specification**: See `SEMANTIC_IR_SPECIFICATION.md`
**Timeline**: 12 months (6 phases × 2 months each)

---

## Overview

This document provides a concrete, task-level implementation plan for the Semantic IR system described in `SEMANTIC_IR_SPECIFICATION.md`. Each phase includes:

- **Clear deliverables** with acceptance criteria
- **Task breakdown** with estimates
- **Dependencies** between tasks
- **Risk assessment** and mitigation strategies
- **Testing requirements**

---

## Phase 1: Foundation (Months 1-2)

**Goal**: Implement core data models and basic entity resolution

### Deliverables

1. ✅ Enhanced IR data model (all classes implemented)
2. ✅ Entity resolver (handles pronouns and definite articles)
3. ✅ Typed hole system (create, store, resolve)
4. ✅ Basic UI highlighting (syntax coloring for prompts)

### Task Breakdown

#### Task 1.1: Data Model Implementation (1 week)

**Files to create/modify**:
- `lift_sys/ir/semantic_models.py` (new)
- `lift_sys/ir/models.py` (extend existing)

**Subtasks**:
1. Implement `Entity`, `Relationship`, `TypedHole` classes (2 days)
2. Implement `SemanticMetadata` container (1 day)
3. Implement `AnnotationLayer` (1 day)
4. Implement `RefinementState` tracker (1 day)
5. Implement `EnhancedIR` wrapper (1 day)
6. Write serialization/deserialization (to_dict, from_dict) (1 day)

**Acceptance Criteria**:
- [ ] All classes have complete docstrings
- [ ] JSON serialization works (no data loss)
- [ ] Unit tests cover all data structures
- [ ] Type hints pass `mypy --strict`

**Dependencies**: None (can start immediately)

---

#### Task 1.2: Entity Resolution Engine (2 weeks)

**Files to create**:
- `lift_sys/nlp/entity_resolver.py` (new)
- `lift_sys/nlp/tokenizer.py` (new)

**Subtasks**:
1. Set up spaCy pipeline (1 day)
   - Install spaCy: `uv add spacy`
   - Download model: `python -m spacy download en_core_web_sm`
2. Implement tokenization and POS tagging (1 day)
3. Implement noun phrase extraction (1 day)
4. Implement coreference resolution (3 days)
   - Option A: Use NeuralCoref (if compatible with spaCy 3.7)
   - Option B: Rule-based fallback (look for pronouns, find nearest noun)
5. Implement entity linking (track mentions across prompt) (2 days)
6. Build entity graph from parse results (2 days)
7. Write comprehensive tests (2 days)

**Acceptance Criteria**:
- [ ] Correctly resolves "it" in "Create X and process it"
- [ ] Handles definite articles ("the report") correctly
- [ ] 90%+ accuracy on test set of 50 prompts
- [ ] Performance: <500ms for 100-token prompt

**Dependencies**: Task 1.1 (needs `Entity` class)

**Risks**:
- **Risk**: NeuralCoref may not work with latest spaCy
  - **Mitigation**: Implement rule-based fallback
- **Risk**: Complex prompts may have ambiguous references
  - **Mitigation**: Flag as ambiguity rather than failing

---

#### Task 1.3: Typed Hole System (1 week)

**Files to create**:
- `lift_sys/refinement/hole_manager.py` (new)

**Subtasks**:
1. Implement hole creation logic (1 day)
   - Detect missing types in signatures
   - Detect unresolved entities
2. Implement hole suggestion generator (2 days)
   - Extract suggestions from context (existing types in codebase)
   - Use simple heuristics (common types for common patterns)
3. Implement hole resolution (1 day)
   - Apply user's choice to IR
   - Propagate changes (update dependent elements)
4. Write tests (1 day)

**Acceptance Criteria**:
- [ ] Holes created for all missing types
- [ ] Suggestions ranked by relevance
- [ ] Resolution updates IR correctly
- [ ] Unit tests cover edge cases

**Dependencies**: Task 1.1 (needs `TypedHole` class)

---

#### Task 1.4: UI Highlighting (1 week)

**Files to create/modify**:
- `frontend/src/components/PromptHighlighter.tsx` (new)
- `frontend/src/components/IRViewer.tsx` (modify existing)
- `frontend/src/styles/semantic-highlighting.css` (new)

**Subtasks**:
1. Design color scheme for entity types (1 day)
2. Implement prompt tokenization in frontend (1 day)
3. Implement highlighting based on entity graph (2 days)
4. Add CSS styles for each entity type (1 day)
5. Test rendering performance (1 day)
6. Polish UX (animations, transitions) (1 day)

**Acceptance Criteria**:
- [ ] Entities highlighted with correct colors
- [ ] Highlights match spec color scheme
- [ ] No performance issues (60fps)
- [ ] Works on all supported browsers

**Dependencies**: Task 1.2 (needs entity graph)

---

### Phase 1 Testing

**Test files to create**:
- `tests/unit/test_semantic_models.py`
- `tests/unit/test_entity_resolver.py`
- `tests/unit/test_hole_manager.py`
- `tests/integration/test_phase1_pipeline.py`

**Integration test**:
```python
def test_phase1_end_to_end():
    """Test: prompt → entity graph → typed holes → UI highlights"""
    prompt = "Create a report and make it shareable"

    # 1. Tokenize and resolve entities
    entity_graph = entity_resolver.resolve(prompt)
    assert entity_graph["e1"].name == "report"
    assert entity_graph["e1"].references == ["it"]

    # 2. Create typed holes
    holes = hole_manager.detect_holes(entity_graph)
    assert len(holes) >= 1  # At least report type is unclear

    # 3. Generate highlights
    highlights = annotation_generator.generate(entity_graph, holes)
    assert len(highlights) > 0
```

---

### Phase 1 Milestones

| Milestone | Criteria | Date |
|-----------|----------|------|
| **M1.1: Data model complete** | All classes implemented, tests passing | End of Week 2 |
| **M1.2: Entity resolution working** | 90% accuracy on test set | End of Week 4 |
| **M1.3: Typed holes functional** | Can create and resolve holes | End of Week 6 |
| **M1.4: UI highlighting live** | Highlights render in UI | End of Week 8 |

---

## Phase 2: Deep Analysis (Months 3-4)

**Goal**: Clause analysis, ambiguity detection, intent classification

### Deliverables

1. ✅ Clause dependency graph
2. ✅ Ambiguity detector (precision 80%, recall 70%)
3. ✅ Implicit term finder
4. ✅ Intent classifier

### Task Breakdown

#### Task 2.1: Clause Dependency Parser (2 weeks)

**Files to create**:
- `lift_sys/nlp/clause_analyzer.py` (new)

**Subtasks**:
1. Extract clauses from spaCy dependency parse (2 days)
2. Identify main vs. subordinate clauses (2 days)
3. Build dependency graph (clause A depends on clause B) (3 days)
4. Extract conditions and temporal relationships (3 days)
5. Write tests (2 days)

**Acceptance Criteria**:
- [ ] Correctly identifies main and subordinate clauses
- [ ] Builds accurate dependency graph
- [ ] Handles conditionals ("if", "when", "unless")
- [ ] 85%+ accuracy on test set

**Dependencies**: Task 1.2 (needs entity graph)

---

#### Task 2.2: Ambiguity Detector (2 weeks)

**Files to create**:
- `lift_sys/refinement/ambiguity_detector.py` (new)

**Subtasks**:
1. Implement contradiction detector (2 days)
   - Check for conflicting statements
2. Implement vague term detector (2 days)
   - Flag overly general words ("process", "handle")
3. Implement missing constraint detector (2 days)
   - Check for parameters without types
4. Implement inconsistent usage detector (2 days)
   - Track term meanings across prompt
5. Rank ambiguities by severity (1 day)
6. Write tests (3 days)

**Acceptance Criteria**:
- [ ] Detects contradictions with 90%+ precision
- [ ] Flags vague terms with 70%+ recall
- [ ] Severity ranking makes sense to users
- [ ] False positive rate <20%

**Dependencies**: Tasks 1.2, 2.1 (needs entities and clauses)

---

#### Task 2.3: Implicit Term Finder (2 weeks)

**Files to create**:
- `lift_sys/refinement/implicit_term_finder.py` (new)

**Subtasks**:
1. Build rule library for common patterns (3 days)
   - "Delete X" → "X must exist"
   - "Send notification" → "recipient needed"
2. Implement precondition inference (2 days)
3. Implement missing parameter detection (2 days)
4. Assign confidence scores (1 day)
5. Generate human-readable descriptions (2 days)
6. Write tests (2 days)

**Acceptance Criteria**:
- [ ] Finds 60%+ of implicit terms (validated by users)
- [ ] Confidence scores correlate with user acceptance rate
- [ ] Descriptions are clear and actionable
- [ ] No false positives that confuse users

**Dependencies**: Task 2.1 (needs clause graph)

---

#### Task 2.4: Intent Classifier (1 week)

**Files to create**:
- `lift_sys/nlp/intent_classifier.py` (new)

**Subtasks**:
1. Define intent taxonomy (1 day)
   - CREATE, READ, UPDATE, DELETE, TRANSFORM, VALIDATE, etc.
2. Implement rule-based classifier (2 days)
   - Match verbs to intent categories
3. Build intent hierarchy (main → sub-intents) (1 day)
4. Generate intent signatures (1 day)
5. Write tests (2 days)

**Acceptance Criteria**:
- [ ] Correctly classifies 80%+ of prompts
- [ ] Intent hierarchy makes sense
- [ ] Signatures are consistent and parseable
- [ ] Handles multi-intent prompts

**Dependencies**: Task 2.1 (needs clause graph)

---

### Phase 2 Testing

**Integration test**:
```python
def test_phase2_end_to_end():
    """Test: prompt → full semantic analysis"""
    prompt = "Create a report and make it shareable if the user is authenticated"

    # 1. Entity resolution (from Phase 1)
    entity_graph = entity_resolver.resolve(prompt)

    # 2. Clause analysis
    clause_graph = clause_analyzer.analyze(prompt, entity_graph)
    assert len(clause_graph.clauses) == 3  # create, make, if
    assert clause_graph.clauses[2].type == "conditional"

    # 3. Ambiguity detection
    ambiguities = ambiguity_detector.detect(entity_graph, clause_graph)
    assert any(a.text == "shareable" for a in ambiguities)

    # 4. Implicit term finding
    implicit = implicit_term_finder.find(clause_graph)
    assert any("must be created" in t.term for t in implicit)

    # 5. Intent classification
    intent = intent_classifier.classify(clause_graph)
    assert intent.signature == "CreateAndConfigure<Report>"
```

---

### Phase 2 Milestones

| Milestone | Criteria | Date |
|-----------|----------|------|
| **M2.1: Clause analysis working** | Builds accurate clause graphs | End of Week 10 |
| **M2.2: Ambiguity detection validated** | 80% precision, 70% recall on test set | End of Week 12 |
| **M2.3: Intent signatures generated** | Correct for 80%+ of prompts | End of Week 14 |
| **M2.4: Implicit terms identified** | 60%+ user acceptance rate | End of Week 16 |

---

## Phase 3-6: High-Level Plan

**Phase 3 (Months 5-6)**: Interactive Refinement
- Refinement UI components
- Suggestion generation with LLM
- Real-time IR updates
- User testing and iteration

**Phase 4 (Months 7-8)**: Visual Intelligence
- Hover state system
- Relationship graph visualization
- Provenance tracking
- Bidirectional navigation

**Phase 5 (Months 9-10)**: Reverse Mode Integration
- Code analysis pipeline
- Code ↔ IR linking
- Split-view UI
- Reverse mode refinement

**Phase 6 (Months 11-12)**: Polish & Deployment
- Performance optimization
- Comprehensive testing
- Documentation
- Production deployment

---

## Dependencies & Critical Path

```
Phase 1: Foundation (no blockers - can start immediately)
    ↓
Phase 2: Deep Analysis (depends on Phase 1 entity resolution)
    ↓
Phase 3: Interactive Refinement (depends on Phase 2 ambiguity detection)
    ↓
Phase 4: Visual Intelligence (can partially overlap with Phase 3)
    ↓
Phase 5: Reverse Mode (depends on Phase 3 IR refinement)
    ↓
Phase 6: Polish (depends on all previous phases)
```

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 6

**Parallel Work**: Phase 4 (Visual Intelligence) can start during Phase 3 (UI components are independent of refinement logic)

---

## Resource Requirements

### Team Size (Recommended)

- **Full-stack engineer** (1x full-time): UI components, frontend integration
- **Backend/NLP engineer** (1x full-time): Semantic analysis, entity resolution
- **ML engineer** (0.5x part-time): Intent classification, suggestion generation
- **Product designer** (0.5x part-time): UI/UX for refinement flow
- **QA engineer** (0.5x part-time): Testing, user studies

**Total**: 3.5 FTE

### Infrastructure

- **Development**:
  - Modal for LLM inference (existing)
  - Elasticsearch for context search (new - ~$50/month)
  - PostgreSQL for IR storage (existing)

- **Production** (additional):
  - Elasticsearch cluster (3 nodes - ~$200/month)
  - Redis for session caching (~$30/month)
  - Monitoring (Datadog or similar - ~$100/month)

**Estimated Cloud Costs**: ~$400/month during development, ~$1000/month in production

---

## Risk Management

### High-Risk Items

| Risk | Impact | Mitigation | Owner |
|------|--------|------------|-------|
| **NLP accuracy insufficient** | High | Fallback to LLM-based analysis | ML Engineer |
| **UI performance issues** | Medium | Profile early, optimize rendering | Frontend Engineer |
| **User adoption low** | High | User studies in Phase 3, iterate on feedback | Product Designer |
| **LLM API costs too high** | Medium | Use LLM only for suggestions, not core analysis | Backend Engineer |
| **Scope creep** | High | Strict adherence to phase deliverables | Project Manager |

### Medium-Risk Items

| Risk | Impact | Mitigation |
|------|--------|------------|
| **spaCy model limitations** | Medium | Fine-tune or use alternative (Stanza) |
| **JSON serialization edge cases** | Low | Comprehensive unit tests |
| **Browser compatibility** | Low | Test on Chrome, Firefox, Safari early |
| **Context retrieval latency** | Medium | Pre-index codebase, use caching |

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 90%+

- All data models: 100% coverage
- Entity resolution: 95% coverage
- Ambiguity detection: 85% coverage
- UI components: 80% coverage

### Integration Tests

**Test Scenarios** (minimum 50):
- Simple prompts (10 scenarios)
- Complex multi-clause prompts (15 scenarios)
- Ambiguous prompts (10 scenarios)
- Prompts with context (10 scenarios)
- Error cases (5 scenarios)

### User Acceptance Testing

**Phases**:
1. **Phase 1**: Internal testing (team members)
2. **Phase 3**: Alpha testing (5 external users)
3. **Phase 5**: Beta testing (20 external users)
4. **Phase 6**: Production release (100+ users)

**Metrics**:
- Task completion rate: >90%
- User satisfaction: >8/10
- Time to complete IR: <5 minutes
- Error rate: <5%

---

## Success Criteria (Overall)

| Metric | Phase 2 Target | Phase 4 Target | Phase 6 Target |
|--------|---------------|----------------|----------------|
| **Entity resolution accuracy** | 85% | 90% | 95% |
| **Ambiguity detection recall** | 60% | 70% | 80% |
| **Ambiguity detection precision** | 70% | 80% | 85% |
| **User satisfaction** | 6/10 | 7/10 | 8/10 |
| **Time to complete IR** | <10 min | <7 min | <5 min |
| **IR → Code quality** | 80% valid | 90% valid | 95% valid |

---

## Next Actions (Week 1)

1. **Get approval on specification** (this document and `SEMANTIC_IR_SPECIFICATION.md`)
2. **Set up development environment**:
   ```bash
   uv add spacy
   python -m spacy download en_core_web_sm
   uv add pytest-cov  # For coverage reporting
   ```
3. **Create project structure**:
   ```bash
   mkdir -p lift_sys/nlp
   mkdir -p lift_sys/refinement
   mkdir -p tests/unit/nlp
   mkdir -p tests/integration/semantic_ir
   ```
4. **Start Task 1.1** (Data Model Implementation)
5. **Schedule Phase 1 kickoff meeting**

---

## Appendix: Detailed Task Estimates

### Phase 1 Tasks (Total: 40 days = 8 weeks)

| Task | Days | Confidence |
|------|------|------------|
| 1.1: Data Model | 5 | High (90%) |
| 1.2: Entity Resolution | 10 | Medium (70%) - NLP complexity |
| 1.3: Typed Holes | 5 | High (85%) |
| 1.4: UI Highlighting | 5 | High (90%) |
| Integration & Testing | 5 | Medium (75%) |
| Buffer (20%) | 10 | N/A |

### Phase 2 Tasks (Total: 40 days = 8 weeks)

| Task | Days | Confidence |
|------|------|------------|
| 2.1: Clause Parsing | 10 | Medium (70%) - NLP complexity |
| 2.2: Ambiguity Detection | 10 | Medium (65%) - Heuristics may need tuning |
| 2.3: Implicit Terms | 10 | Low (60%) - Hard to validate |
| 2.4: Intent Classification | 5 | High (80%) |
| Integration & Testing | 5 | Medium (70%) |
| Buffer (20%) | 10 | N/A |

**Total for Phases 1-2**: 16 weeks (4 months)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-15
**Next Review**: After Phase 1 completion
