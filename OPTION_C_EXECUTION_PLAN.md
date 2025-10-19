# Option C: Core Features Execution Plan

**Status**: ACTIVE - Executing Now
**Timeline**: 6 months (Months 1-6)
**Vision Reference**: SEMANTIC_IR_ROADMAP.md, SEMANTIC_IR_SPECIFICATION.md, SEMANTIC_IR_DETAILED_EXECUTION_PLAN.md

---

## The Plan: Build Core Features, Defer Polish

### Included in Option C (6 months):
- ✅ **Phase 1: Foundation** (Months 1-2) - Enhanced IR, Entity Resolution, Typed Holes
- ✅ **Phase 3: Interactive Refinement** (Months 3-4) - AI suggestions, real-time updates
- ✅ **Phase 5: Reverse Mode** (Months 5-6) - Code→IR, split-view

### Deferred (Add Later if Needed):
- ⏸️ **Phase 2: NLP & Ambiguity Detection** - Full semantic analysis, contradiction detection
- ⏸️ **Phase 4: Visualization & Navigation** - Relationship graphs, fancy hover states

---

## Current Status: Phase 1 Starting

**Epic**: lift-sys-258 - Semantic IR Phase 1: Foundation
**Current Task**: lift-sys-70 - Enhanced IR Data Models
**Status**: In Progress

---

## Phase 1: Foundation (Months 1-2)

**Goal**: Core semantic data models, entity resolution, typed holes, basic UI

### Week 1-2: Data Models & Infrastructure

**lift-sys-70**: Enhanced IR Data Models (5 days) - **IN PROGRESS**
- Implement Entity, TypedHole, Ambiguity, Intent, SemanticMetadata classes
- JSON serialization (to_dict/from_dict)
- 100% test coverage
- Files: `lift_sys/ir/semantic_models.py` (~800 lines)

**lift-sys-71**: Database Schema (3 days)
- Tables for semantic_metadata, entities, relationships, typed_holes, ambiguities
- Migration with alembic
- Files: `alembic/versions/xxx_add_semantic_ir.py`

**lift-sys-72**: API Endpoints (3 days)
- POST /analyze, GET /semantic, POST /resolve-hole
- Pydantic schemas, authentication
- Files: `lift_sys/api/server.py` updates

### Week 3-4: NLP Pipeline - Entity Resolution

**lift-sys-73**: NLP Infrastructure (2 days)
- spaCy setup, Redis caching
- Files: `lift_sys/nlp/pipeline.py`

**lift-sys-74**: Tokenization and POS Tagging (2 days)
- Token class with spans, POS tags, lemmas
- Files: `lift_sys/nlp/tokenizer.py`

**lift-sys-75**: Noun Phrase Extraction (2 days)
- Extract entities from noun phrases
- Files: `lift_sys/nlp/entity_extractor.py`

**lift-sys-76**: Coreference Resolution (4 days)
- Resolve pronouns (it, they, them)
- Handle definite articles ("the X")
- Files: `lift_sys/nlp/coreference.py`

**lift-sys-77**: Entity Graph Builder (2 days)
- Build entity relationship graph
- Files: `lift_sys/nlp/entity_graph.py`

**lift-sys-78**: Entity Resolver Integration (2 days)
- Integrate all entity resolution components
- End-to-end pipeline working

### Week 5-6: Typed Holes System

**lift-sys-79**: Typed Hole Detection (3 days)
- Detect unknowns in IR
- Files: `lift_sys/ir/hole_detector.py`

**lift-sys-80**: Context-Based Suggestion Generator (3 days)
- Generate suggestions for holes
- Files: `lift_sys/refinement/suggestions.py`

**lift-sys-81**: Hole Resolution Logic (2 days)
- Apply user selections, update IR
- Files: `lift_sys/refinement/hole_resolver.py`

**lift-sys-82**: Hole Manager Integration (2 days)
- Integrate hole system into pipeline

### Week 7-8: Basic UI Components

**lift-sys-83**: Annotation Generation (2 days)
- Generate highlighting metadata from IR
- Files: `lift_sys/ui/annotations.py`

**lift-sys-84**: Frontend Prompt Highlighter (3 days)
- Highlight entities in prompt text
- Files: `frontend/src/components/PromptHighlighter.tsx`

**lift-sys-85**: Enhanced IR Viewer (3 days)
- Display semantic metadata in UI
- Files: `frontend/src/components/EnhancedIRViewer.tsx`

**lift-sys-86**: Phase 1 Integration Testing (2 days)
- End-to-end tests for all Phase 1 features
- Files: `tests/e2e/test_phase1_complete.py`

**Phase 1 Deliverables**:
- ✅ Semantic IR data models working
- ✅ Entity resolution 90%+ accuracy
- ✅ Typed holes detected and visible
- ✅ Basic UI showing entities and holes

---

## Phase 3: Interactive Refinement (Months 3-4)

**Goal**: Users can interactively resolve holes with AI assistance

### Skipping from Full Plan:
- Full ambiguity detection (Phase 2)
- Advanced suggestion ranking
- Complex consistency checking

### Building:
- lift-sys-104: Refinement panel UI
- lift-sys-105: Suggestion display
- lift-sys-107: State management
- lift-sys-108: LLM suggestion prompts
- lift-sys-109: LLM integration
- lift-sys-112: IR update propagation
- lift-sys-113-115: Real-time updates (WebSocket)
- lift-sys-116: UX optimization
- lift-sys-118: Integration testing

**Phase 3 Deliverables**:
- ✅ Interactive hole resolution working
- ✅ AI-powered suggestions
- ✅ Real-time IR updates
- ✅ Refinement progress tracking

---

## Phase 5: Reverse Mode (Months 5-6)

**Goal**: Code → IR with bidirectional navigation

### Skipping from Full Plan:
- Advanced relationship graphs (Phase 4)
- Fancy provenance visualization
- Complex hover tooltips

### Building:
- lift-sys-131: AST-based entity extraction
- lift-sys-132: Intent inference from code
- lift-sys-133: Relationship extraction
- lift-sys-134: EnhancedIR builder from code
- lift-sys-136: Code syntax highlighter
- lift-sys-138: Bidirectional navigation
- lift-sys-139: Split-view layout
- lift-sys-140: Synchronized highlighting
- lift-sys-143-145: Refinement, validation, testing

**Phase 5 Deliverables**:
- ✅ Code → IR working
- ✅ Split-view UI (code | IR)
- ✅ Bidirectional navigation
- ✅ Round-trip fidelity >90%

---

## Month 6 Deliverable: Core Vision Working

**What Users Get**:
1. **Forward Mode**: Natural Language → Semantic IR → Code
   - Entity resolution working
   - Typed holes identified
   - Interactive refinement with AI suggestions

2. **Reverse Mode**: Code → Semantic IR
   - Extract entities and intent from code
   - Same semantic IR structure as forward mode
   - Understand existing code

3. **Interactive Experience**:
   - Split-view (prompt/code | IR)
   - Real-time updates
   - AI-assisted hole resolution

**What's Deferred** (Add if Users Request):
- Advanced ambiguity detection (contradictions, vague terms)
- Relationship graphs and fancy visualizations
- Complex provenance tracking
- Full Phase 2 and Phase 4 features

---

## Success Metrics

**Month 2 (Phase 1)**:
- Entity resolution: 90%+ accuracy on "it" references
- Typed holes: 80%+ detection rate
- UI: Entities highlighted, holes visible

**Month 4 (Phase 3)**:
- Refinement: Users complete in <5 minutes
- Suggestions: 80%+ helpful
- Updates: Real-time (<500ms)

**Month 6 (Phase 5)**:
- Reverse mode: Code→IR working
- Round-trip: 90%+ semantic preservation
- UX: Smooth 60fps split-view

---

## Deferred Features (Full Vision Reference)

### Phase 2: NLP & Ambiguity Detection (Deferred)

**Beads**: lift-sys-87 to 103 (marked priority 2, labels: "deferred-phase2")

**Features**:
- Clause analysis and dependency graphs
- Contradiction detector
- Vague term detector
- Missing constraint detector
- Inference rule library
- Intent taxonomy (50+ categories)
- Full intent classifier

**When to Build**: If users report confusion from contradictory prompts or missing information

---

### Phase 4: Visualization & Navigation (Deferred)

**Beads**: lift-sys-119 to 130 (marked priority 2, labels: "deferred-phase4")

**Features**:
- Rich hover tooltip engine
- Provenance tracking and visualization
- Relationship graph with D3.js
- Interactive graph controls
- Advanced navigation
- Performance optimization

**When to Build**: If users request better visualization of relationships and provenance

---

## Full Vision Documentation (Preserved)

All planning documents remain available for reference:

1. **SEMANTIC_IR_ROADMAP.md** - This file (strategic overview, 3 options)
2. **SEMANTIC_IR_SPECIFICATION.md** - Complete technical specification
3. **SEMANTIC_IR_DETAILED_EXECUTION_PLAN.md** - Task-level detail for all 6 phases
4. **OPTION_C_EXECUTION_PLAN.md** - This document (current execution)
5. **FULL_PLAN_OVERVIEW.md** - Beads analysis and strategic decision

**Beads**: All 257 beads preserved
- Phase 1 tasks: Priority 0, active
- Phase 3 tasks: Priority 0, queued
- Phase 5 tasks: Priority 0, queued
- Phase 2 tasks: Priority 2, deferred
- Phase 4 tasks: Priority 2, deferred

---

## Next Actions (This Week)

1. **Complete lift-sys-70**: Enhanced IR Data Models
   - Implement all semantic metadata classes
   - JSON serialization working
   - 100% test coverage
   - Estimate: 5 days

2. **Start lift-sys-71**: Database Schema
   - Alembic migration for semantic tables
   - Can store/retrieve EnhancedIR
   - Estimate: 3 days

3. **Daily standup check**:
   - What was completed?
   - What's blocking?
   - Adjust timeline if needed

---

## Timeline Summary

```
Week 1-2:   Data models, database, API endpoints
Week 3-4:   NLP pipeline, entity resolution
Week 5-6:   Typed holes system
Week 7-8:   Basic UI, Phase 1 testing
            ↓
Month 3-4:  Interactive refinement (Phase 3)
            ↓
Month 5-6:  Reverse mode (Phase 5)
            ↓
Month 6:    DELIVERABLE - Core vision working
```

---

**Status**: Phase 1 in progress (lift-sys-70)
**Current Epic**: lift-sys-258
**Timeline**: 6 months to core vision
**Full Vision**: Preserved in docs and beads for future reference
