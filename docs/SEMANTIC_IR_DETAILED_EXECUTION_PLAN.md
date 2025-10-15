# Semantic IR: Detailed Execution Plan

**Status**: Approved - Full Scope
**Created**: 2025-10-15
**Timeline**: 12 months (52 weeks)
**Team**: 3.5 FTE (2 eng, 0.5 ML, 0.5 design, 0.5 QA)

---

## Overview

This document provides **task-level detail** for implementing the complete Semantic IR system. Every task includes:

- **Task ID** (for Beads tracking)
- **Detailed description** with acceptance criteria
- **Time estimate** (in days)
- **Dependencies** (which tasks must complete first)
- **Owner** (role assignment)
- **Test requirements**
- **Risk assessment**

**No corners cut** - this is the full implementation of the specification.

---

## Phase 1: Foundation (Weeks 1-8)

**Goal**: Core data models, entity resolution, typed holes, basic UI

### Sprint 1 (Weeks 1-2): Data Model & Infrastructure

#### Task 1.1.1: Enhanced IR Data Models

**Bead ID**: `lift-sys-100`
**Owner**: Backend Engineer
**Estimate**: 5 days
**Dependencies**: None

**Description**:
Implement all semantic metadata classes in `lift_sys/ir/semantic_models.py`:
- `Entity`, `EntityType`, `SemanticType`
- `Span`, `Relationship`
- `TypedHole`, `Ambiguity`, `ImplicitTerm`
- `Intent` (with hierarchy support)
- `SemanticMetadata` (container)
- `AnnotationLayer`
- `RefinementState`, `RefinementStep`
- `EnhancedIR` (wrapper combining all layers)

**Acceptance Criteria**:
- [ ] All classes have complete docstrings (Google style)
- [ ] All classes have type hints (mypy --strict passes)
- [ ] JSON serialization works (to_dict/from_dict)
- [ ] No data loss in serialize→deserialize cycle
- [ ] Unit tests cover all classes (100% coverage)
- [ ] Example EnhancedIR object can be created and serialized

**Tests**:
- `tests/unit/test_semantic_models.py` (15+ test cases)
- Test serialization with nested structures
- Test edge cases (empty lists, None values)

**Deliverables**:
- `lift_sys/ir/semantic_models.py` (~800 lines)
- `tests/unit/test_semantic_models.py` (~400 lines)

---

#### Task 1.1.2: Database Schema for Semantic IR

**Bead ID**: `lift-sys-101`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.1.1

**Description**:
Create database schema to store EnhancedIR with all metadata:
- Create migration: `alembic revision` for new tables
- Tables: `semantic_metadata`, `entities`, `relationships`, `typed_holes`, `ambiguities`, `refinement_history`
- Indexes for fast retrieval by session_id, entity_id
- JSON columns for flexible metadata storage

**Acceptance Criteria**:
- [ ] Migration applies cleanly
- [ ] Can store and retrieve EnhancedIR
- [ ] Queries are efficient (<100ms for retrieval)
- [ ] Supports concurrent writes (session isolation)
- [ ] Rollback works

**Tests**:
- `tests/integration/test_semantic_ir_persistence.py`
- Test CRUD operations
- Test concurrent access
- Test large IRs (100+ entities)

**Deliverables**:
- `alembic/versions/xxx_add_semantic_ir.py` (~200 lines)
- Update `lift_sys/db/models.py` (~150 lines)

---

#### Task 1.1.3: API Endpoints for Semantic IR

**Bead ID**: `lift-sys-102`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.1.2

**Description**:
Add API endpoints for semantic IR operations:
- `POST /api/sessions/{id}/analyze` - Run semantic analysis
- `GET /api/sessions/{id}/semantic` - Get semantic metadata
- `POST /api/sessions/{id}/resolve-hole` - Resolve typed hole
- `POST /api/sessions/{id}/resolve-ambiguity` - Resolve ambiguity
- `GET /api/sessions/{id}/annotations` - Get UI annotations

**Acceptance Criteria**:
- [ ] All endpoints documented in OpenAPI
- [ ] Request/response models use Pydantic
- [ ] Error handling returns useful messages
- [ ] Endpoints are authenticated
- [ ] Rate limiting applied

**Tests**:
- `tests/integration/test_semantic_api.py`
- Test all endpoints
- Test error cases
- Test pagination (for large entity lists)

**Deliverables**:
- Update `lift_sys/api/server.py` (~300 lines)
- `lift_sys/api/schemas.py` additions (~200 lines)

---

### Sprint 2 (Weeks 3-4): NLP Pipeline - Entity Resolution

#### Task 1.2.1: NLP Infrastructure Setup

**Bead ID**: `lift-sys-103`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: None (can run parallel to 1.1.x)

**Description**:
Set up NLP processing infrastructure:
- Install spaCy: `uv add spacy`
- Download model: `python -m spacy download en_core_web_sm`
- Create `NLPPipeline` class (wrapper around spaCy)
- Implement caching for parsed documents (Redis)
- Set up performance monitoring (track parse time)

**Acceptance Criteria**:
- [ ] spaCy pipeline initializes correctly
- [ ] Can parse text and extract POS tags
- [ ] Caching reduces repeated parsing time by 90%+
- [ ] Monitoring tracks parse time per prompt

**Tests**:
- `tests/unit/test_nlp_pipeline.py`
- Test initialization
- Test caching behavior
- Test parse output format

**Deliverables**:
- `lift_sys/nlp/__init__.py`
- `lift_sys/nlp/pipeline.py` (~150 lines)
- Add spaCy to `pyproject.toml`

---

#### Task 1.2.2: Tokenization and POS Tagging

**Bead ID**: `lift-sys-104`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.2.1

**Description**:
Implement tokenization with metadata tracking:
- Create `Token` class with span, POS tag, lemma
- Create `TokenizedPrompt` class (list of tokens + metadata)
- Track character offsets for highlighting
- Handle edge cases (punctuation, special characters)

**Acceptance Criteria**:
- [ ] Tokenizes prompts accurately
- [ ] Preserves character offsets
- [ ] POS tags are correct (95%+ accuracy)
- [ ] Handles Unicode and special characters

**Tests**:
- `tests/unit/test_tokenization.py`
- Test various prompt styles
- Test edge cases (emojis, URLs, code snippets)

**Deliverables**:
- `lift_sys/nlp/tokenizer.py` (~200 lines)

---

#### Task 1.2.3: Noun Phrase Extraction

**Bead ID**: `lift-sys-105`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.2.2

**Description**:
Extract entities from noun phrases:
- Use spaCy's noun chunk detection
- Filter by relevance (remove determiners)
- Create `Entity` objects for each noun phrase
- Assign initial semantic types (using POS patterns)

**Acceptance Criteria**:
- [ ] Extracts all major noun phrases
- [ ] Filters out irrelevant phrases (e.g., "a", "the")
- [ ] Creates Entity objects with correct spans
- [ ] Initial type assignment is reasonable

**Tests**:
- `tests/unit/test_noun_extraction.py`
- Test simple prompts ("Create a report")
- Test complex prompts ("Create a user authentication system")

**Deliverables**:
- `lift_sys/nlp/entity_extractor.py` (~250 lines)

---

#### Task 1.2.4: Coreference Resolution

**Bead ID**: `lift-sys-106`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.2.3

**Description**:
Resolve pronouns and references:
- Try NeuralCoref integration (if compatible with spaCy 3.7)
- Fallback: Implement rule-based coreference
  - Track pronouns (it, they, them, its, their)
  - Find nearest noun antecedent
  - Handle definite articles ("the report" → previously mentioned report)
- Update Entity objects with coreference links

**Acceptance Criteria**:
- [ ] Resolves "it" correctly in "Create X and process it" (90%+ accuracy)
- [ ] Handles definite articles correctly
- [ ] Updates Entity.references list
- [ ] Fallback works if NeuralCoref unavailable

**Tests**:
- `tests/unit/test_coreference.py`
- Test pronouns: it, they, them
- Test definite articles: the, that, this
- Test ambiguous cases (should flag ambiguity, not guess)

**Deliverables**:
- `lift_sys/nlp/coreference_resolver.py` (~300 lines)
- Test set with 50 labeled examples

---

#### Task 1.2.5: Entity Graph Builder

**Bead ID**: `lift-sys-107`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.2.4

**Description**:
Build complete entity graph from resolved entities:
- Create `EntityGraph` class (dict of Entity objects)
- Link entities via relationships (coreference, modification)
- Assign semantic types using heuristics
- Calculate confidence scores

**Acceptance Criteria**:
- [ ] Builds complete graph with all entities
- [ ] Coreferences correctly linked
- [ ] Semantic types assigned (80%+ correct)
- [ ] Confidence scores correlate with accuracy

**Tests**:
- `tests/integration/test_entity_graph.py`
- End-to-end test: prompt → entity graph
- Validate graph structure
- Validate semantic types

**Deliverables**:
- `lift_sys/nlp/entity_graph.py` (~200 lines)
- Integration test suite

---

#### Task 1.2.6: Entity Resolver Integration

**Bead ID**: `lift-sys-108`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.2.5

**Description**:
Integrate entity resolution into main pipeline:
- Create `EntityResolver` class (facade)
- Wire up all components (tokenizer → extractor → coreference → graph)
- Add error handling and logging
- Optimize performance (target <500ms for 100-token prompt)

**Acceptance Criteria**:
- [ ] Complete pipeline works end-to-end
- [ ] Performance meets target (<500ms)
- [ ] Error messages are actionable
- [ ] Logs include timing breakdowns

**Tests**:
- `tests/integration/test_entity_resolver.py`
- Test 20 diverse prompts
- Measure performance
- Test error cases

**Deliverables**:
- `lift_sys/nlp/entity_resolver.py` (~250 lines)

---

### Sprint 3 (Weeks 5-6): Typed Holes & Suggestions

#### Task 1.3.1: Typed Hole Detection

**Bead ID**: `lift-sys-109`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.1.1, Task 1.2.6

**Description**:
Detect unresolved elements in entity graph and IR:
- Check all entities for missing semantic types
- Check signature parameters for missing types
- Check return type specification
- Create TypedHole objects for each missing element
- Classify hole types (type_specification, missing_parameter, etc.)

**Acceptance Criteria**:
- [ ] Detects all missing types
- [ ] Creates TypedHole with correct metadata
- [ ] Hole locations map back to prompt
- [ ] No false positives (don't flag resolved elements)

**Tests**:
- `tests/unit/test_hole_detection.py`
- Test various incomplete IRs
- Test edge cases (partially specified types)

**Deliverables**:
- `lift_sys/refinement/hole_detector.py` (~200 lines)

---

#### Task 1.3.2: Context-Based Suggestion Generator

**Bead ID**: `lift-sys-110`
**Owner**: ML Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.3.1

**Description**:
Generate suggestions for hole resolution from context:
- Index existing types in connected codebase (if any)
- Use semantic similarity to find relevant types
- Query common type patterns from dataset
- Rank suggestions by relevance
- Use LLM for custom suggestions (Claude/GPT API)

**Acceptance Criteria**:
- [ ] Generates 3-5 suggestions per hole
- [ ] Top suggestion is correct 60%+ of the time
- [ ] Suggestions are ranked by relevance
- [ ] LLM suggestions are coherent and relevant

**Tests**:
- `tests/unit/test_suggestion_generator.py`
- Test with codebase context
- Test without context (cold start)
- Test suggestion ranking

**Deliverables**:
- `lift_sys/refinement/suggestion_generator.py` (~300 lines)
- Prompt templates for LLM suggestions

---

#### Task 1.3.3: Hole Resolution Logic

**Bead ID**: `lift-sys-111`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.3.2

**Description**:
Implement hole resolution and propagation:
- Apply user's choice to IR
- Update entity types
- Propagate changes to related entities
- Mark hole as resolved
- Record in refinement history

**Acceptance Criteria**:
- [ ] Resolution updates IR correctly
- [ ] Changes propagate to dependent elements
- [ ] Refinement history tracks all changes
- [ ] Can undo resolution (if needed)

**Tests**:
- `tests/unit/test_hole_resolution.py`
- Test simple resolution
- Test propagation
- Test undo functionality

**Deliverables**:
- `lift_sys/refinement/hole_resolver.py` (~200 lines)

---

#### Task 1.3.4: Hole Manager Integration

**Bead ID**: `lift-sys-112`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.3.3

**Description**:
Integrate hole management into API:
- Add hole detection to analysis pipeline
- Expose suggestions via API
- Handle resolution requests
- Update session state

**Acceptance Criteria**:
- [ ] Holes detected automatically on analysis
- [ ] Suggestions returned with holes
- [ ] Resolution endpoint works correctly
- [ ] Session state persists

**Tests**:
- `tests/integration/test_hole_manager.py`
- Test full hole lifecycle
- Test API integration

**Deliverables**:
- `lift_sys/refinement/hole_manager.py` (~150 lines)
- API endpoint updates

---

### Sprint 4 (Weeks 7-8): UI Highlighting & Visualization

#### Task 1.4.1: Annotation Generation

**Bead ID**: `lift-sys-113`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.2.6

**Description**:
Generate UI annotations from semantic metadata:
- Create `AnnotationGenerator` class
- Map entities to highlight spans
- Assign colors based on entity types
- Generate tooltip content
- Create bidirectional links (prompt ↔ IR)

**Acceptance Criteria**:
- [ ] Generates highlights for all entities
- [ ] Colors match specification
- [ ] Tooltips include relevant info
- [ ] Links are bidirectional

**Tests**:
- `tests/unit/test_annotation_generator.py`
- Test annotation generation
- Test tooltip content
- Test link creation

**Deliverables**:
- `lift_sys/visualization/annotation_generator.py` (~250 lines)

---

#### Task 1.4.2: Frontend Prompt Highlighter Component

**Bead ID**: `lift-sys-114`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.4.1

**Description**:
Build React component for prompt highlighting:
- Create `PromptHighlighter.tsx` component
- Apply highlights based on annotation data
- Implement hover states
- Add click handlers for navigation
- Ensure performance (60fps rendering)

**Acceptance Criteria**:
- [ ] Highlights render correctly
- [ ] Hover shows tooltips
- [ ] Click navigates to IR element
- [ ] No performance issues (60fps)
- [ ] Works on long prompts (500+ tokens)

**Tests**:
- `tests/frontend/PromptHighlighter.test.tsx`
- Test rendering
- Test interaction
- Test performance

**Deliverables**:
- `frontend/src/components/PromptHighlighter.tsx` (~400 lines)
- `frontend/src/styles/semantic-highlighting.css` (~150 lines)

---

#### Task 1.4.3: Enhanced IR Viewer Component

**Bead ID**: `lift-sys-115`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.4.1

**Description**:
Enhance existing IR viewer with semantic annotations:
- Add syntax highlighting to IR view
- Show hover tooltips with provenance
- Add click navigation back to prompt
- Display confidence scores
- Show refinement state

**Acceptance Criteria**:
- [ ] IR renders with highlights
- [ ] Hover shows source in prompt
- [ ] Click navigates to prompt token
- [ ] Confidence scores visible
- [ ] Refinement state displayed

**Tests**:
- `tests/frontend/IRViewer.test.tsx`
- Test enhanced features
- Test navigation

**Deliverables**:
- Update `frontend/src/components/IRViewer.tsx` (~300 lines added)

---

#### Task 1.4.4: Phase 1 Integration Testing

**Bead ID**: `lift-sys-116`
**Owner**: QA Engineer
**Estimate**: 3 days
**Dependencies**: All Phase 1 tasks

**Description**:
Comprehensive end-to-end testing of Phase 1:
- Test complete pipeline: prompt → analysis → highlighting
- Test hole detection and suggestion
- Test UI interactions
- Performance testing
- User acceptance testing (internal)

**Acceptance Criteria**:
- [ ] All Phase 1 features work end-to-end
- [ ] Performance meets targets
- [ ] No critical bugs
- [ ] User feedback is positive (internal team)

**Tests**:
- `tests/e2e/test_phase1_complete.py`
- 20 diverse test scenarios
- Performance benchmarks

**Deliverables**:
- Test report
- Bug list with priorities
- Performance metrics

---

## Phase 2: Deep Analysis (Weeks 9-16)

**Goal**: Clause analysis, ambiguity detection, implicit terms, intent classification

### Sprint 5 (Weeks 9-10): Clause Analysis

#### Task 2.1.1: Clause Extraction

**Bead ID**: `lift-sys-117`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.2.6

**Description**:
Extract clauses from spaCy dependency parse:
- Identify main clauses
- Identify subordinate clauses
- Extract verb phrases for each clause
- Classify clause types (declarative, conditional, relative)

**Acceptance Criteria**:
- [ ] Identifies all clauses in prompt
- [ ] Classifies clause types correctly (90%+)
- [ ] Extracts verbs and objects
- [ ] Handles complex nested clauses

**Tests**:
- `tests/unit/test_clause_extraction.py`
- Test simple sentences
- Test complex multi-clause prompts

**Deliverables**:
- `lift_sys/nlp/clause_extractor.py` (~300 lines)

---

#### Task 2.1.2: Dependency Graph Builder

**Bead ID**: `lift-sys-118`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.1.1

**Description**:
Build clause dependency graph:
- Create `ClauseDependencyGraph` class
- Link clauses via coordinators (and, or, but)
- Link clauses via subordinators (if, when, because)
- Identify main vs. dependent clauses

**Acceptance Criteria**:
- [ ] Builds correct dependency structure
- [ ] Identifies main clause
- [ ] Links related clauses
- [ ] Handles complex dependencies

**Tests**:
- `tests/unit/test_clause_graph.py`
- Test various clause patterns

**Deliverables**:
- `lift_sys/nlp/clause_graph.py` (~250 lines)

---

#### Task 2.1.3: Conditional and Temporal Extraction

**Bead ID**: `lift-sys-119`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.1.2

**Description**:
Extract conditions and temporal relationships:
- Identify conditional clauses (if, unless, when)
- Extract condition predicates
- Identify temporal relationships (before, after, during)
- Link conditions to affected clauses

**Acceptance Criteria**:
- [ ] Identifies all conditional clauses
- [ ] Extracts condition predicates
- [ ] Identifies temporal order
- [ ] Links conditions to actions

**Tests**:
- `tests/unit/test_conditional_extraction.py`
- Test if/then/else patterns
- Test temporal patterns

**Deliverables**:
- `lift_sys/nlp/conditional_extractor.py` (~200 lines)

---

#### Task 2.1.4: Clause Analyzer Integration

**Bead ID**: `lift-sys-120`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 2.1.3

**Description**:
Integrate clause analysis into pipeline:
- Create `ClauseAnalyzer` facade
- Wire up all clause components
- Add to main analysis pipeline
- Optimize performance

**Acceptance Criteria**:
- [ ] Complete clause analysis works
- [ ] Performance <1s for typical prompts
- [ ] Integrates with entity resolution

**Tests**:
- `tests/integration/test_clause_analyzer.py`

**Deliverables**:
- `lift_sys/nlp/clause_analyzer.py` (~200 lines)

---

### Sprint 6 (Weeks 11-12): Ambiguity Detection

#### Task 2.2.1: Contradiction Detector

**Bead ID**: `lift-sys-121`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.1.4

**Description**:
Detect contradictory statements:
- Check for conflicting assertions
- Identify mutually exclusive conditions
- Flag inconsistent requirements
- Rank by severity

**Acceptance Criteria**:
- [ ] Detects obvious contradictions (90%+)
- [ ] Flags likely contradictions (70%+)
- [ ] Provides clear explanation
- [ ] Low false positive rate (<10%)

**Tests**:
- `tests/unit/test_contradiction_detector.py`
- Test obvious contradictions
- Test subtle conflicts

**Deliverables**:
- `lift_sys/refinement/contradiction_detector.py` (~250 lines)

---

#### Task 2.2.2: Vague Term Detector

**Bead ID**: `lift-sys-122`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.1.4

**Description**:
Detect overly general or vague terms:
- Maintain dictionary of vague terms
- Check entities and verbs against dictionary
- Consider context (some terms OK in context)
- Generate clarifying questions

**Acceptance Criteria**:
- [ ] Flags vague terms (70%+ recall)
- [ ] Considers context appropriately
- [ ] Generates useful questions
- [ ] Not overly sensitive (precision 80%+)

**Tests**:
- `tests/unit/test_vague_term_detector.py`

**Deliverables**:
- `lift_sys/refinement/vague_term_detector.py` (~200 lines)
- Dictionary of vague terms (~100 entries)

---

#### Task 2.2.3: Missing Constraint Detector

**Bead ID**: `lift-sys-123`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.3.1

**Description**:
Detect missing constraints and specifications:
- Check for untyped parameters
- Check for missing preconditions
- Check for missing validations
- Flag based on domain knowledge

**Acceptance Criteria**:
- [ ] Finds missing types (95%+)
- [ ] Suggests likely constraints
- [ ] Prioritizes by importance

**Tests**:
- `tests/unit/test_missing_constraint_detector.py`

**Deliverables**:
- `lift_sys/refinement/constraint_detector.py` (~200 lines)

---

#### Task 2.2.4: Inconsistent Usage Detector

**Bead ID**: `lift-sys-124`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 1.2.6

**Description**:
Detect inconsistent use of terms:
- Track usage of each term across prompt
- Identify shifts in meaning
- Flag potential confusion
- Suggest consistent terminology

**Acceptance Criteria**:
- [ ] Detects usage shifts
- [ ] Provides examples of inconsistency
- [ ] Suggests unified terminology

**Tests**:
- `tests/unit/test_inconsistent_usage_detector.py`

**Deliverables**:
- `lift_sys/refinement/usage_detector.py` (~150 lines)

---

#### Task 2.2.5: Ambiguity Ranker and Integrator

**Bead ID**: `lift-sys-125`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Tasks 2.2.1-2.2.4

**Description**:
Integrate all ambiguity detectors and rank findings:
- Create `AmbiguityDetector` facade
- Combine results from all detectors
- Rank by severity and impact
- Generate user-friendly descriptions
- Add to analysis pipeline

**Acceptance Criteria**:
- [ ] All detectors integrated
- [ ] Ranking is sensible
- [ ] Descriptions are clear
- [ ] Performance <1s

**Tests**:
- `tests/integration/test_ambiguity_detector.py`

**Deliverables**:
- `lift_sys/refinement/ambiguity_detector.py` (~250 lines)

---

### Sprint 7 (Weeks 13-14): Implicit Term Finding

#### Task 2.3.1: Rule Library for Common Patterns

**Bead ID**: `lift-sys-126`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: Task 2.1.4

**Description**:
Build library of inference rules:
- "Delete X" → "X must exist" (precondition)
- "Create X" → "X doesn't exist yet" (precondition)
- "Send notification" → "recipient needed" (missing parameter)
- "Update X" → "X must exist" (precondition)
- "Authenticate user" → "credentials needed" (missing parameter)
- ...100+ rules covering common patterns

**Acceptance Criteria**:
- [ ] 100+ rules implemented
- [ ] Rules are accurate (90%+ precision)
- [ ] Rules cover common scenarios
- [ ] Easy to add new rules

**Tests**:
- `tests/unit/test_inference_rules.py`
- Test each rule category

**Deliverables**:
- `lift_sys/refinement/inference_rules.py` (~400 lines)
- Rule documentation

---

#### Task 2.3.2: Precondition Inference Engine

**Bead ID**: `lift-sys-127`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.3.1

**Description**:
Infer preconditions from clauses:
- Apply inference rules to clauses
- Generate precondition statements
- Assign confidence scores
- Link to source clauses

**Acceptance Criteria**:
- [ ] Infers obvious preconditions (95%+)
- [ ] Confidence scores are calibrated
- [ ] Links back to source

**Tests**:
- `tests/unit/test_precondition_inference.py`

**Deliverables**:
- `lift_sys/refinement/precondition_inferencer.py` (~250 lines)

---

#### Task 2.3.3: Missing Parameter Detection

**Bead ID**: `lift-sys-128`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.3.1

**Description**:
Detect likely missing parameters:
- Apply inference rules to identify gaps
- Check for implicit subjects ("send email" → to whom?)
- Suggest parameter names and types
- Rank by likelihood

**Acceptance Criteria**:
- [ ] Finds 60%+ of missing parameters
- [ ] Suggestions are reasonable
- [ ] Low false positive rate

**Tests**:
- `tests/unit/test_missing_parameter_detection.py`

**Deliverables**:
- `lift_sys/refinement/parameter_inferencer.py` (~200 lines)

---

#### Task 2.3.4: Implicit Term Finder Integration

**Bead ID**: `lift-sys-129`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Tasks 2.3.2-2.3.3

**Description**:
Integrate implicit term finding into pipeline:
- Create `ImplicitTermFinder` facade
- Combine all inference engines
- Generate user-friendly descriptions
- Add to analysis pipeline

**Acceptance Criteria**:
- [ ] All inference engines integrated
- [ ] Results are actionable
- [ ] Performance <1s

**Tests**:
- `tests/integration/test_implicit_term_finder.py`

**Deliverables**:
- `lift_sys/refinement/implicit_term_finder.py` (~150 lines)

---

### Sprint 8 (Weeks 15-16): Intent Classification

#### Task 2.4.1: Intent Taxonomy Definition

**Bead ID**: `lift-sys-130`
**Owner**: ML Engineer
**Estimate**: 2 days
**Dependencies**: None

**Description**:
Define complete intent taxonomy:
- CRUD operations: CREATE, READ, UPDATE, DELETE
- Transformations: TRANSFORM, CONVERT, FILTER, AGGREGATE
- Validations: VALIDATE, CHECK, VERIFY
- Communications: SEND, NOTIFY, LOG
- Control flow: IF, LOOP, TRY
- ...50+ intent categories

**Acceptance Criteria**:
- [ ] Taxonomy is comprehensive
- [ ] Categories are mutually exclusive
- [ ] Hierarchical structure makes sense
- [ ] Documented with examples

**Tests**:
- Manual review by team

**Deliverables**:
- `lift_sys/nlp/intent_taxonomy.py` (~200 lines)
- Documentation: `docs/INTENT_TAXONOMY.md`

---

#### Task 2.4.2: Rule-Based Intent Classifier

**Bead ID**: `lift-sys-131`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 2.4.1

**Description**:
Implement rule-based intent classification:
- Map verbs to intent categories
- Consider clause context
- Handle multi-intent prompts
- Build intent hierarchy

**Acceptance Criteria**:
- [ ] Classifies simple prompts correctly (90%+)
- [ ] Handles complex prompts (70%+)
- [ ] Builds sensible hierarchy
- [ ] Fast (<100ms)

**Tests**:
- `tests/unit/test_intent_classifier.py`
- Test 50+ diverse prompts

**Deliverables**:
- `lift_sys/nlp/intent_classifier.py` (~300 lines)

---

#### Task 2.4.3: Intent Signature Generator

**Bead ID**: `lift-sys-132`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: Task 2.4.2

**Description**:
Generate canonical intent signatures:
- Format: Operation<Target>
- Example: "CreateAndConfigure<Report>"
- Handle compound intents
- Include constraints in signature

**Acceptance Criteria**:
- [ ] Signatures are consistent
- [ ] Signatures are parseable
- [ ] Unique for different intents

**Tests**:
- `tests/unit/test_signature_generator.py`

**Deliverables**:
- `lift_sys/nlp/signature_generator.py` (~150 lines)

---

#### Task 2.4.4: Phase 2 Integration Testing

**Bead ID**: `lift-sys-133`
**Owner**: QA Engineer
**Estimate**: 4 days
**Dependencies**: All Phase 2 tasks

**Description**:
Comprehensive testing of Phase 2:
- Test complete analysis pipeline
- Test ambiguity detection accuracy
- Test implicit term finding
- Test intent classification
- Performance testing
- User acceptance testing

**Acceptance Criteria**:
- [ ] All Phase 2 features work end-to-end
- [ ] Ambiguity detection: 80% precision, 70% recall
- [ ] Intent classification: 80% accuracy
- [ ] Performance: <2s for complete analysis

**Tests**:
- `tests/e2e/test_phase2_complete.py`
- 30 diverse test scenarios

**Deliverables**:
- Test report
- Accuracy metrics
- Bug list

---

## Phase 3: Interactive Refinement (Weeks 17-24)

**Goal**: Full refinement UI with LLM-powered suggestions

### Sprint 9 (Weeks 17-18): Refinement UI Components

#### Task 3.1.1: Refinement Panel Component

**Bead ID**: `lift-sys-134`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.4.2

**Description**:
Build main refinement panel:
- Side panel that shows current issue
- Context display (surrounding prompt)
- Suggestion list
- Custom input field
- Accept/Reject buttons

**Acceptance Criteria**:
- [ ] Panel renders correctly
- [ ] Shows context clearly
- [ ] Suggestions are readable
- [ ] Interactions are smooth

**Tests**:
- `tests/frontend/RefinementPanel.test.tsx`

**Deliverables**:
- `frontend/src/components/RefinementPanel.tsx` (~500 lines)

---

#### Task 3.1.2: Suggestion Display Component

**Bead ID**: `lift-sys-135`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.1.1

**Description**:
Build suggestion display:
- Radio button list of suggestions
- Show rationale for each suggestion
- Show confidence scores
- Highlight selected suggestion
- Support custom input

**Acceptance Criteria**:
- [ ] Renders suggestion list
- [ ] Radio buttons work
- [ ] Custom input works
- [ ] Accessible (keyboard navigation)

**Tests**:
- `tests/frontend/SuggestionList.test.tsx`

**Deliverables**:
- `frontend/src/components/SuggestionList.tsx` (~300 lines)

---

#### Task 3.1.3: Progress Tracker Component

**Bead ID**: `lift-sys-136`
**Owner**: Frontend Engineer
**Estimate**: 2 days
**Dependencies**: Task 3.1.1

**Description**:
Build refinement progress tracker:
- Show total issues (holes + ambiguities)
- Show resolved vs. unresolved
- Progress bar
- Jump to next issue button

**Acceptance Criteria**:
- [ ] Shows accurate counts
- [ ] Progress bar updates
- [ ] Navigation works

**Tests**:
- `tests/frontend/ProgressTracker.test.tsx`

**Deliverables**:
- `frontend/src/components/ProgressTracker.tsx` (~200 lines)

---

#### Task 3.1.4: Refinement State Management

**Bead ID**: `lift-sys-137`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.1.3

**Description**:
Implement frontend state management for refinement:
- Track current issue being refined
- Track refinement history
- Handle optimistic updates
- Sync with backend

**Acceptance Criteria**:
- [ ] State updates correctly
- [ ] History is tracked
- [ ] Optimistic updates work
- [ ] Backend sync is reliable

**Tests**:
- `tests/frontend/refinementStore.test.ts`

**Deliverables**:
- `frontend/src/stores/refinementStore.ts` (~300 lines)

---

### Sprint 10 (Weeks 19-20): LLM-Powered Suggestions

#### Task 3.2.1: LLM Suggestion Prompt Engineering

**Bead ID**: `lift-sys-138`
**Owner**: ML Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.3.2

**Description**:
Design prompts for LLM suggestion generation:
- Prompt for type suggestions
- Prompt for parameter name suggestions
- Prompt for implementation suggestions
- Include context in prompts
- Optimize for quality and cost

**Acceptance Criteria**:
- [ ] Prompts generate relevant suggestions
- [ ] Suggestions are accurate (80%+)
- [ ] Cost is reasonable (<$0.01 per suggestion)
- [ ] Latency is acceptable (<2s)

**Tests**:
- Manual evaluation of 100 suggestions

**Deliverables**:
- `lift_sys/refinement/llm_prompts.py` (~200 lines)
- Prompt template documentation

---

#### Task 3.2.2: LLM Integration Layer

**Bead ID**: `lift-sys-139`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.2.1

**Description**:
Integrate LLM for suggestion generation:
- Use existing provider abstraction (Anthropic/OpenAI)
- Implement caching (avoid repeat calls)
- Handle rate limiting
- Fallback to heuristics if LLM unavailable

**Acceptance Criteria**:
- [ ] LLM suggestions work
- [ ] Caching reduces costs
- [ ] Rate limiting prevents errors
- [ ] Fallback is transparent

**Tests**:
- `tests/integration/test_llm_suggestions.py`

**Deliverables**:
- `lift_sys/refinement/llm_suggester.py` (~250 lines)

---

#### Task 3.2.3: Suggestion Ranking Algorithm

**Bead ID**: `lift-sys-140`
**Owner**: ML Engineer
**Estimate**: 4 days
**Dependencies**: Task 3.2.2

**Description**:
Rank suggestions by relevance:
- Combine heuristic and LLM suggestions
- Score by context match
- Score by type compatibility
- Score by user history (if available)
- Final ranking

**Acceptance Criteria**:
- [ ] Top suggestion is correct 70%+ of time
- [ ] Ranking is consistent
- [ ] Fast (<100ms)

**Tests**:
- `tests/unit/test_suggestion_ranking.py`
- Evaluate on test set

**Deliverables**:
- `lift_sys/refinement/suggestion_ranker.py` (~200 lines)

---

#### Task 3.2.4: Contextual Suggestion Enhancement

**Bead ID**: `lift-sys-141`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.2.3

**Description**:
Enhance suggestions with context:
- Extract relevant context from codebase
- Include existing types and patterns
- Show usage examples
- Link to documentation

**Acceptance Criteria**:
- [ ] Context is relevant
- [ ] Examples are helpful
- [ ] Documentation links work

**Tests**:
- Manual evaluation

**Deliverables**:
- `lift_sys/refinement/context_enhancer.py` (~200 lines)

---

### Sprint 11 (Weeks 21-22): Real-Time IR Updates

#### Task 3.3.1: IR Update Propagation Engine

**Bead ID**: `lift-sys-142`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.3.3

**Description**:
Implement change propagation:
- When hole resolved, update related elements
- When type changed, validate consistency
- Re-run analysis if needed
- Update all dependent metadata

**Acceptance Criteria**:
- [ ] Changes propagate correctly
- [ ] Consistency maintained
- [ ] Performance is good (<500ms)
- [ ] No infinite loops

**Tests**:
- `tests/unit/test_ir_propagation.py`
- Test various propagation scenarios

**Deliverables**:
- `lift_sys/refinement/propagation_engine.py` (~300 lines)

---

#### Task 3.3.2: Consistency Checker

**Bead ID**: `lift-sys-143`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.3.1

**Description**:
Check IR consistency after updates:
- Type compatibility checks
- Constraint satisfaction checks
- Reference validity checks
- Flag new ambiguities

**Acceptance Criteria**:
- [ ] Catches type mismatches
- [ ] Validates all constraints
- [ ] Identifies broken references

**Tests**:
- `tests/unit/test_consistency_checker.py`

**Deliverables**:
- `lift_sys/refinement/consistency_checker.py` (~250 lines)

---

#### Task 3.3.3: Real-Time Update WebSocket

**Bead ID**: `lift-sys-144`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.3.2

**Description**:
Implement WebSocket for real-time updates:
- Send IR updates to connected clients
- Send new ambiguities found
- Send progress updates
- Handle reconnection

**Acceptance Criteria**:
- [ ] Updates sent in real-time
- [ ] Reconnection works
- [ ] Multiple clients supported

**Tests**:
- `tests/integration/test_websocket_updates.py`

**Deliverables**:
- Update `lift_sys/api/websocket.py` (~200 lines)

---

#### Task 3.3.4: Frontend Real-Time Update Handler

**Bead ID**: `lift-sys-145`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 3.3.3

**Description**:
Handle real-time updates in frontend:
- Listen to WebSocket messages
- Update IR view
- Update highlights
- Show notifications for new issues

**Acceptance Criteria**:
- [ ] Updates reflected immediately
- [ ] UI doesn't flicker
- [ ] Notifications are clear

**Tests**:
- `tests/frontend/realtimeUpdates.test.ts`

**Deliverables**:
- `frontend/src/hooks/useRealtimeUpdates.ts` (~200 lines)

---

### Sprint 12 (Weeks 23-24): Phase 3 Polish & Testing

#### Task 3.4.1: Refinement Flow Optimization

**Bead ID**: `lift-sys-146`
**Owner**: Product Designer + Frontend Engineer
**Estimate**: 4 days
**Dependencies**: All Phase 3 tasks

**Description**:
Optimize refinement UX:
- Streamline issue navigation
- Improve keyboard shortcuts
- Add undo/redo
- Polish animations and transitions

**Acceptance Criteria**:
- [ ] Flow is intuitive
- [ ] Keyboard shortcuts work
- [ ] Undo/redo reliable
- [ ] Smooth animations

**Tests**:
- User testing with 5 participants

**Deliverables**:
- UX improvements across components

---

#### Task 3.4.2: Error Handling and Edge Cases

**Bead ID**: `lift-sys-147`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: All Phase 3 backend tasks

**Description**:
Handle error cases:
- LLM API failures
- WebSocket disconnections
- Invalid user input
- Concurrent modifications

**Acceptance Criteria**:
- [ ] Errors handled gracefully
- [ ] User sees helpful messages
- [ ] System recovers automatically

**Tests**:
- `tests/integration/test_error_handling.py`

**Deliverables**:
- Error handling improvements

---

#### Task 3.4.3: Phase 3 Integration Testing

**Bead ID**: `lift-sys-148`
**Owner**: QA Engineer
**Estimate**: 5 days
**Dependencies**: All Phase 3 tasks

**Description**:
Comprehensive Phase 3 testing:
- Test complete refinement flow
- Test with real users (5 alpha testers)
- Performance testing
- Stress testing (concurrent users)

**Acceptance Criteria**:
- [ ] Refinement flow works end-to-end
- [ ] Users can complete IR in <5 minutes
- [ ] User satisfaction >7/10
- [ ] No critical bugs

**Tests**:
- `tests/e2e/test_phase3_complete.py`
- User study report

**Deliverables**:
- Test report
- User study findings
- Bug list

---

## Phase 4: Visual Intelligence (Weeks 25-32)

**Goal**: Rich hover states, relationship visualization, provenance tracking

### Sprint 13 (Weeks 25-26): Advanced Hover System

#### Task 4.1.1: Hover Tooltip Engine

**Bead ID**: `lift-sys-149`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.4.2

**Description**:
Build rich tooltip system:
- Multi-section tooltips (type, relationships, provenance)
- Dynamic content loading
- Smart positioning (avoid screen edges)
- Keyboard accessible

**Acceptance Criteria**:
- [ ] Tooltips show rich content
- [ ] Positioning is smart
- [ ] Loading is fast (<100ms)
- [ ] Keyboard navigation works

**Tests**:
- `tests/frontend/TooltipEngine.test.tsx`

**Deliverables**:
- `frontend/src/components/TooltipEngine.tsx` (~400 lines)

---

#### Task 4.1.2: Provenance Tracking Backend

**Bead ID**: `lift-sys-150`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 1.4.1

**Description**:
Track provenance for all IR elements:
- Record where each element came from
- Track inference chain (X was inferred from Y because Z)
- Store confidence scores at each step
- Link to source tokens in prompt

**Acceptance Criteria**:
- [ ] Provenance recorded for all elements
- [ ] Chain is complete
- [ ] Links are bidirectional

**Tests**:
- `tests/unit/test_provenance_tracker.py`

**Deliverables**:
- `lift_sys/visualization/provenance_tracker.py` (~250 lines)

---

#### Task 4.1.3: Hover Content Generator

**Bead ID**: `lift-sys-151`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 4.1.2

**Description**:
Generate hover content from metadata:
- Type information section
- Relationship section (what's connected)
- Provenance section (where it came from)
- Confidence scores
- Navigation links

**Acceptance Criteria**:
- [ ] Content is comprehensive
- [ ] Content is well-formatted
- [ ] Links are functional

**Tests**:
- `tests/unit/test_hover_content_generator.py`

**Deliverables**:
- `lift_sys/visualization/hover_content_generator.py` (~200 lines)

---

#### Task 4.1.4: Hover Integration

**Bead ID**: `lift-sys-152`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Tasks 4.1.1, 4.1.3

**Description**:
Integrate hover system:
- Connect backend content to frontend tooltips
- Add to prompt highlighter
- Add to IR viewer
- Performance optimization

**Acceptance Criteria**:
- [ ] Hover works on prompt and IR
- [ ] Content loads quickly
- [ ] No performance issues

**Tests**:
- `tests/integration/test_hover_system.py`

**Deliverables**:
- Integration code (~150 lines)

---

### Sprint 14 (Weeks 27-28): Relationship Visualization

#### Task 4.2.1: Graph Layout Algorithm

**Bead ID**: `lift-sys-153`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.2.5

**Description**:
Implement graph layout:
- Use force-directed layout (D3.js)
- Position entities logically
- Handle large graphs (100+ nodes)
- Support zoom and pan

**Acceptance Criteria**:
- [ ] Graph is readable
- [ ] Layout is stable
- [ ] Performance good for large graphs

**Tests**:
- Manual testing with various graphs

**Deliverables**:
- `frontend/src/components/RelationshipGraph.tsx` (~500 lines)

---

#### Task 4.2.2: Interactive Graph Controls

**Bead ID**: `lift-sys-154`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 4.2.1

**Description**:
Add graph interactivity:
- Click node → highlight in prompt/IR
- Hover node → show tooltip
- Filter by relationship type
- Search nodes

**Acceptance Criteria**:
- [ ] Click navigation works
- [ ] Hover shows info
- [ ] Filters work
- [ ] Search works

**Tests**:
- `tests/frontend/RelationshipGraph.test.tsx`

**Deliverables**:
- Graph controls (~300 lines)

---

#### Task 4.2.3: Graph Side Panel

**Bead ID**: `lift-sys-155`
**Owner**: Frontend Engineer
**Estimate**: 2 days
**Dependencies**: Task 4.2.2

**Description**:
Build side panel for graph view:
- Toggle visibility
- Resize panel
- Legend for relationship types
- Statistics (node count, etc.)

**Acceptance Criteria**:
- [ ] Panel toggles smoothly
- [ ] Resizing works
- [ ] Legend is clear

**Tests**:
- Manual testing

**Deliverables**:
- `frontend/src/components/GraphPanel.tsx` (~200 lines)

---

#### Task 4.2.4: Graph Integration

**Bead ID**: `lift-sys-156`
**Owner**: Frontend Engineer
**Estimate**: 2 days
**Dependencies**: Task 4.2.3

**Description**:
Integrate graph into main UI:
- Add to IR viewer
- Sync with other views
- Preserve state on navigation

**Acceptance Criteria**:
- [ ] Graph integrates cleanly
- [ ] State synchronization works

**Tests**:
- Integration testing

**Deliverables**:
- Integration code

---

### Sprint 15-16 (Weeks 29-32): Bidirectional Navigation & Phase 4 Polish

#### Task 4.3.1: Navigation Link System

**Bead ID**: `lift-sys-157`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: Task 1.4.3

**Description**:
Implement bidirectional navigation:
- Click prompt token → jump to IR element
- Click IR element → jump to prompt token
- Scroll into view
- Highlight target

**Acceptance Criteria**:
- [ ] Both directions work
- [ ] Smooth scrolling
- [ ] Clear highlighting

**Tests**:
- `tests/frontend/navigation.test.tsx`

**Deliverables**:
- `frontend/src/utils/navigation.ts` (~200 lines)

---

#### Task 4.3.2: Provenance Visualization

**Bead ID**: `lift-sys-158`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 4.1.2

**Description**:
Visualize provenance chains:
- Show inference path (X → Y → Z)
- Display in hover tooltip
- Optional: Full provenance panel

**Acceptance Criteria**:
- [ ] Provenance is clear
- [ ] Path is complete
- [ ] Visual is intuitive

**Tests**:
- Manual testing

**Deliverables**:
- `frontend/src/components/ProvenanceView.tsx` (~300 lines)

---

#### Task 4.3.3: Performance Optimization

**Bead ID**: `lift-sys-159`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: All Phase 4 UI tasks

**Description**:
Optimize visual performance:
- Virtualize long lists
- Lazy load tooltips
- Optimize graph rendering
- Reduce re-renders

**Acceptance Criteria**:
- [ ] 60fps on all views
- [ ] Fast initial load (<2s)
- [ ] Smooth interactions

**Tests**:
- Performance benchmarks

**Deliverables**:
- Performance improvements

---

#### Task 4.3.4: Phase 4 Integration Testing

**Bead ID**: `lift-sys-160`
**Owner**: QA Engineer
**Estimate**: 5 days
**Dependencies**: All Phase 4 tasks

**Description**:
Comprehensive Phase 4 testing:
- Test all visual features
- Test navigation
- Test graph visualization
- Performance testing
- User acceptance testing

**Acceptance Criteria**:
- [ ] All features work
- [ ] User feedback positive
- [ ] Performance meets targets

**Tests**:
- `tests/e2e/test_phase4_complete.py`
- User study

**Deliverables**:
- Test report
- User study findings

---

## Phase 5: Reverse Mode Integration (Weeks 33-40)

**Goal**: Same visual experience for code → IR

### Sprint 17 (Weeks 33-34): Code Analysis Pipeline

#### Task 5.1.1: AST-Based Entity Extraction

**Bead ID**: `lift-sys-161`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: None

**Description**:
Extract entities from code AST:
- Extract classes, functions, variables
- Extract types from type hints
- Create Entity objects from code
- Link to source code locations

**Acceptance Criteria**:
- [ ] Extracts all entities
- [ ] Types are accurate
- [ ] Links are correct

**Tests**:
- `tests/unit/test_ast_entity_extraction.py`

**Deliverables**:
- `lift_sys/reverse_mode/ast_extractor.py` (~300 lines)

---

#### Task 5.1.2: Code Intent Inference

**Bead ID**: `lift-sys-162`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: Task 5.1.1

**Description**:
Infer intent from code:
- Extract from docstrings
- Infer from function name
- Infer from operations in body
- Build intent hierarchy

**Acceptance Criteria**:
- [ ] Intent extraction works
- [ ] Accuracy is reasonable (70%+)

**Tests**:
- `tests/unit/test_code_intent_inference.py`

**Deliverables**:
- `lift_sys/reverse_mode/intent_inferencer.py` (~250 lines)

---

#### Task 5.1.3: Code Relationship Extraction

**Bead ID**: `lift-sys-163`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.1.1

**Description**:
Extract relationships from code:
- Function calls
- Class inheritance
- Variable references
- Parameter passing

**Acceptance Criteria**:
- [ ] Relationships extracted
- [ ] Graph is complete

**Tests**:
- `tests/unit/test_code_relationship_extraction.py`

**Deliverables**:
- `lift_sys/reverse_mode/relationship_extractor.py` (~200 lines)

---

#### Task 5.1.4: Code-to-EnhancedIR Builder

**Bead ID**: `lift-sys-164`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: Tasks 5.1.1-5.1.3

**Description**:
Build EnhancedIR from code:
- Convert entities to semantic metadata
- Build relationships
- Infer intent
- Create annotations

**Acceptance Criteria**:
- [ ] Produces EnhancedIR
- [ ] Structure matches forward mode
- [ ] Links back to code

**Tests**:
- `tests/integration/test_code_to_ir.py`

**Deliverables**:
- `lift_sys/reverse_mode/enhanced_ir_builder.py` (~300 lines)

---

### Sprint 18 (Weeks 35-36): Code ↔ IR Linking

#### Task 5.2.1: Code Annotation System

**Bead ID**: `lift-sys-165`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.1.4

**Description**:
Create annotations linking code to IR:
- Map code spans to IR elements
- Map IR elements to code spans
- Generate highlights for code view

**Acceptance Criteria**:
- [ ] Links are bidirectional
- [ ] Spans are accurate

**Tests**:
- `tests/unit/test_code_annotations.py`

**Deliverables**:
- `lift_sys/reverse_mode/code_annotator.py` (~200 lines)

---

#### Task 5.2.2: Code Syntax Highlighter

**Bead ID**: `lift-sys-166`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: Task 5.2.1

**Description**:
Build code highlighter with semantic annotations:
- Use Monaco Editor or CodeMirror
- Apply semantic highlights (beyond syntax)
- Show entities, relationships
- Link to IR

**Acceptance Criteria**:
- [ ] Code renders with highlights
- [ ] Semantic highlights are clear
- [ ] Performance is good

**Tests**:
- Manual testing

**Deliverables**:
- `frontend/src/components/CodeHighlighter.tsx` (~400 lines)

---

#### Task 5.2.3: Code Hover Tooltips

**Bead ID**: `lift-sys-167`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.2.2

**Description**:
Add hover tooltips to code view:
- Show IR element on hover
- Show type information
- Show relationships
- Link to IR view

**Acceptance Criteria**:
- [ ] Hover shows relevant info
- [ ] Links work

**Tests**:
- Manual testing

**Deliverables**:
- Code hover integration (~200 lines)

---

#### Task 5.2.4: Bidirectional Navigation (Code ↔ IR)

**Bead ID**: `lift-sys-168`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Tasks 5.2.2, 5.2.3

**Description**:
Implement navigation between code and IR:
- Click code → jump to IR element
- Click IR → jump to code location
- Scroll into view
- Highlight target

**Acceptance Criteria**:
- [ ] Both directions work
- [ ] Smooth navigation

**Tests**:
- Integration testing

**Deliverables**:
- Navigation code (~150 lines)

---

### Sprint 19 (Weeks 37-38): Split-View UI

#### Task 5.3.1: Split-View Layout

**Bead ID**: `lift-sys-169`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.2.2

**Description**:
Build split-view layout:
- Code on left, IR on right (or configurable)
- Resizable panels
- Toggle views
- Sync scrolling (optional)

**Acceptance Criteria**:
- [ ] Layout is responsive
- [ ] Resizing works smoothly
- [ ] Toggle is instant

**Tests**:
- Manual testing

**Deliverables**:
- `frontend/src/components/SplitView.tsx` (~300 lines)

---

#### Task 5.3.2: Synchronized Highlighting

**Bead ID**: `lift-sys-170`
**Owner**: Frontend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.3.1

**Description**:
Synchronize highlights across views:
- Hover in code → highlight IR
- Hover in IR → highlight code
- Click in one → highlight in both

**Acceptance Criteria**:
- [ ] Highlights synchronize
- [ ] No performance lag

**Tests**:
- Integration testing

**Deliverables**:
- Sync logic (~200 lines)

---

#### Task 5.3.3: View State Persistence

**Bead ID**: `lift-sys-171`
**Owner**: Frontend Engineer
**Estimate**: 2 days
**Dependencies**: Task 5.3.1

**Description**:
Persist view state:
- Remember panel sizes
- Remember scroll positions
- Remember expanded/collapsed sections

**Acceptance Criteria**:
- [ ] State persists across sessions
- [ ] Restore works reliably

**Tests**:
- Manual testing

**Deliverables**:
- State persistence (~100 lines)

---

#### Task 5.3.4: Split-View Polish

**Bead ID**: `lift-sys-172`
**Owner**: Frontend Engineer
**Estimate**: 2 days
**Dependencies**: All Sprint 19 tasks

**Description**:
Polish split-view experience:
- Smooth animations
- Keyboard shortcuts
- Accessibility
- Mobile considerations

**Acceptance Criteria**:
- [ ] UX is smooth
- [ ] Keyboard shortcuts work
- [ ] Accessible

**Tests**:
- Accessibility audit

**Deliverables**:
- Polish improvements

---

### Sprint 20 (Weeks 39-40): Reverse Mode Refinement & Testing

#### Task 5.4.1: Reverse Mode Refinement

**Bead ID**: `lift-sys-173`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.1.4

**Description**:
Enable refinement on lifted IR:
- Detect ambiguities in lifted IR
- Allow hole resolution
- Allow intent refinement
- Update code annotations

**Acceptance Criteria**:
- [ ] Can refine lifted IR
- [ ] Changes update annotations

**Tests**:
- `tests/integration/test_reverse_refinement.py`

**Deliverables**:
- Refinement integration (~200 lines)

---

#### Task 5.4.2: Round-Trip Validation

**Bead ID**: `lift-sys-174`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 5.4.1

**Description**:
Validate round-trip fidelity:
- Code → IR → Code
- Compare original vs. generated
- Measure semantic equivalence
- Report differences

**Acceptance Criteria**:
- [ ] Round-trip works
- [ ] Semantic equivalence measured
- [ ] Differences are explainable

**Tests**:
- `tests/integration/test_round_trip.py`

**Deliverables**:
- `lift_sys/validation/round_trip_validator.py` (~250 lines)

---

#### Task 5.4.3: Phase 5 Integration Testing

**Bead ID**: `lift-sys-175`
**Owner**: QA Engineer
**Estimate**: 5 days
**Dependencies**: All Phase 5 tasks

**Description**:
Comprehensive Phase 5 testing:
- Test code analysis
- Test split-view
- Test refinement
- Test round-trip
- User acceptance testing

**Acceptance Criteria**:
- [ ] All features work
- [ ] Round-trip fidelity is good
- [ ] User feedback positive

**Tests**:
- `tests/e2e/test_phase5_complete.py`
- User study

**Deliverables**:
- Test report
- User study findings

---

## Phase 6: Polish & Deployment (Weeks 41-52)

**Goal**: Production-ready system

### Sprint 21-22 (Weeks 41-44): Performance Optimization

#### Task 6.1.1: Backend Performance Profiling

**Bead ID**: `lift-sys-176`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: All backend tasks

**Description**:
Profile and optimize backend:
- Profile analysis pipeline
- Identify bottlenecks
- Optimize slow queries
- Add caching where needed

**Acceptance Criteria**:
- [ ] Analysis <2s for typical prompts
- [ ] API responses <500ms
- [ ] DB queries optimized

**Tests**:
- Performance benchmarks

**Deliverables**:
- Performance report
- Optimizations

---

#### Task 6.1.2: Frontend Performance Optimization

**Bead ID**: `lift-sys-177`
**Owner**: Frontend Engineer
**Estimate**: 4 days
**Dependencies**: All frontend tasks

**Description**:
Optimize frontend performance:
- Bundle size optimization
- Code splitting
- Lazy loading
- React rendering optimization

**Acceptance Criteria**:
- [ ] Initial load <2s
- [ ] 60fps interactions
- [ ] Bundle size <500KB (gzipped)

**Tests**:
- Lighthouse audit
- Performance benchmarks

**Deliverables**:
- Performance improvements

---

#### Task 6.1.3: Database Optimization

**Bead ID**: `lift-sys-178`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 6.1.1

**Description**:
Optimize database:
- Add missing indexes
- Optimize queries
- Set up connection pooling
- Configure caching

**Acceptance Criteria**:
- [ ] Queries <100ms
- [ ] No N+1 queries
- [ ] Connection pooling works

**Tests**:
- Query analysis

**Deliverables**:
- Database optimizations

---

#### Task 6.1.4: Caching Strategy

**Bead ID**: `lift-sys-179`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Task 6.1.3

**Description**:
Implement comprehensive caching:
- Redis for session data
- Cache parsed documents
- Cache LLM suggestions
- Cache entity graphs

**Acceptance Criteria**:
- [ ] Caching reduces latency 50%+
- [ ] Cache invalidation works
- [ ] Memory usage is reasonable

**Tests**:
- Cache behavior tests

**Deliverables**:
- Caching layer (~300 lines)

---

### Sprint 23 (Weeks 45-46): Comprehensive Testing

#### Task 6.2.1: Unit Test Coverage

**Bead ID**: `lift-sys-180`
**Owner**: QA Engineer
**Estimate**: 5 days
**Dependencies**: All implementation tasks

**Description**:
Achieve 90%+ test coverage:
- Add missing unit tests
- Add edge case tests
- Add error path tests
- Generate coverage report

**Acceptance Criteria**:
- [ ] 90%+ coverage overall
- [ ] 95%+ coverage for critical paths
- [ ] All edge cases tested

**Tests**:
- All unit tests

**Deliverables**:
- Test suite completion
- Coverage report

---

#### Task 6.2.2: Integration Test Suite

**Bead ID**: `lift-sys-181`
**Owner**: QA Engineer
**Estimate**: 4 days
**Dependencies**: Task 6.2.1

**Description**:
Comprehensive integration tests:
- End-to-end workflows
- Cross-component tests
- API integration tests
- Database integration tests

**Acceptance Criteria**:
- [ ] 50+ integration tests
- [ ] All workflows covered
- [ ] Tests are reliable (no flakiness)

**Tests**:
- Integration test suite

**Deliverables**:
- Integration tests

---

#### Task 6.2.3: E2E Test Suite

**Bead ID**: `lift-sys-182`
**Owner**: QA Engineer
**Estimate**: 4 days
**Dependencies**: Task 6.2.2

**Description**:
End-to-end test suite:
- User workflow tests
- Browser automation (Playwright)
- Test all major features
- Test error scenarios

**Acceptance Criteria**:
- [ ] 30+ E2E tests
- [ ] Tests run reliably
- [ ] CI/CD integration

**Tests**:
- E2E test suite

**Deliverables**:
- E2E tests

---

#### Task 6.2.4: Load and Stress Testing

**Bead ID**: `lift-sys-183`
**Owner**: QA Engineer
**Estimate**: 3 days
**Dependencies**: Task 6.1.4

**Description**:
Performance and load testing:
- Test with 100+ concurrent users
- Test with large prompts (1000+ tokens)
- Test with large codebases (10,000+ files)
- Identify breaking points

**Acceptance Criteria**:
- [ ] Handles 100+ concurrent users
- [ ] No degradation under load
- [ ] Breaking points documented

**Tests**:
- Load tests

**Deliverables**:
- Load test report

---

### Sprint 24 (Weeks 47-48): Documentation

#### Task 6.3.1: User Documentation

**Bead ID**: `lift-sys-184`
**Owner**: Technical Writer (or Frontend Engineer)
**Estimate**: 5 days
**Dependencies**: All implementation

**Description**:
Complete user documentation:
- Getting started guide
- Feature documentation
- Tutorial videos
- FAQ
- Troubleshooting guide

**Acceptance Criteria**:
- [ ] Comprehensive documentation
- [ ] Clear examples
- [ ] Screenshots/videos
- [ ] Searchable

**Tests**:
- User feedback on docs

**Deliverables**:
- `docs/USER_GUIDE.md` (~5000 lines)
- Tutorial videos (3-5)

---

#### Task 6.3.2: API Documentation

**Bead ID**: `lift-sys-185`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: All API endpoints

**Description**:
Complete API documentation:
- OpenAPI spec
- Endpoint descriptions
- Request/response examples
- Error codes
- Rate limiting docs

**Acceptance Criteria**:
- [ ] All endpoints documented
- [ ] Examples work
- [ ] Interactive docs (Swagger)

**Tests**:
- Manual review

**Deliverables**:
- API documentation

---

#### Task 6.3.3: Developer Documentation

**Bead ID**: `lift-sys-186`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: All implementation

**Description**:
Documentation for developers:
- Architecture overview
- Component documentation
- Extension guides
- Contributing guide

**Acceptance Criteria**:
- [ ] Architecture is clear
- [ ] Components are documented
- [ ] Extension points explained

**Tests**:
- Manual review

**Deliverables**:
- `docs/DEVELOPER_GUIDE.md` (~3000 lines)

---

#### Task 6.3.4: Deployment Documentation

**Bead ID**: `lift-sys-187`
**Owner**: Backend Engineer
**Estimate**: 2 days
**Dependencies**: None

**Description**:
Deployment documentation:
- Infrastructure requirements
- Deployment steps
- Configuration guide
- Monitoring setup
- Troubleshooting

**Acceptance Criteria**:
- [ ] Step-by-step deployment guide
- [ ] Configuration is documented
- [ ] Monitoring setup is clear

**Tests**:
- Deploy to staging following guide

**Deliverables**:
- `docs/DEPLOYMENT.md` (~2000 lines)

---

### Sprint 25-26 (Weeks 49-52): Beta Testing & Production Deployment

#### Task 6.4.1: Beta Program

**Bead ID**: `lift-sys-188`
**Owner**: Product Manager (or team lead)
**Estimate**: 10 days
**Dependencies**: All previous tasks

**Description**:
Run beta program:
- Recruit 20 beta testers
- Provide training/onboarding
- Collect feedback
- Track metrics
- Fix critical issues

**Acceptance Criteria**:
- [ ] 20 beta testers onboarded
- [ ] Feedback collected
- [ ] Critical bugs fixed
- [ ] User satisfaction >8/10

**Tests**:
- Beta testing

**Deliverables**:
- Beta test report
- Bug fixes

---

#### Task 6.4.2: Production Infrastructure Setup

**Bead ID**: `lift-sys-189`
**Owner**: Backend Engineer
**Estimate**: 4 days
**Dependencies**: Task 6.3.4

**Description**:
Set up production infrastructure:
- Production database
- Redis cluster
- Load balancer
- CDN for frontend
- Monitoring (Datadog/Grafana)
- Logging (ELK/Cloudwatch)

**Acceptance Criteria**:
- [ ] Infrastructure is scalable
- [ ] Monitoring is comprehensive
- [ ] Logging is centralized
- [ ] Backups are automated

**Tests**:
- Infrastructure validation

**Deliverables**:
- Production infrastructure

---

#### Task 6.4.3: Security Audit

**Bead ID**: `lift-sys-190`
**Owner**: Security Engineer (or external auditor)
**Estimate**: 5 days
**Dependencies**: All implementation

**Description**:
Security audit:
- Code review for vulnerabilities
- Penetration testing
- Authentication/authorization review
- Data privacy review
- Fix critical issues

**Acceptance Criteria**:
- [ ] No critical vulnerabilities
- [ ] Authentication is secure
- [ ] Data is encrypted
- [ ] Privacy compliant (GDPR, etc.)

**Tests**:
- Security tests

**Deliverables**:
- Security audit report
- Security fixes

---

#### Task 6.4.4: Production Deployment

**Bead ID**: `lift-sys-191`
**Owner**: Backend Engineer
**Estimate**: 3 days
**Dependencies**: Tasks 6.4.1-6.4.3

**Description**:
Deploy to production:
- Deploy backend
- Deploy frontend
- Configure monitoring
- Set up alerts
- Create runbook

**Acceptance Criteria**:
- [ ] Deployment succeeds
- [ ] All features work
- [ ] Monitoring is active
- [ ] Alerts are configured

**Tests**:
- Smoke tests in production

**Deliverables**:
- Production deployment
- Runbook

---

#### Task 6.4.5: Post-Launch Support

**Bead ID**: `lift-sys-192`
**Owner**: Entire Team
**Estimate**: Ongoing
**Dependencies**: Task 6.4.4

**Description**:
Post-launch activities:
- Monitor production
- Fix bugs
- Respond to user feedback
- Iterate on features

**Acceptance Criteria**:
- [ ] System is stable
- [ ] Bugs are fixed quickly
- [ ] User feedback is addressed

**Tests**:
- Ongoing monitoring

**Deliverables**:
- Support and maintenance

---

## Summary Statistics

### Total Tasks: 92

**By Phase:**
- Phase 1 (Foundation): 16 tasks, 8 weeks
- Phase 2 (Deep Analysis): 17 tasks, 8 weeks
- Phase 3 (Interactive Refinement): 15 tasks, 8 weeks
- Phase 4 (Visual Intelligence): 12 tasks, 8 weeks
- Phase 5 (Reverse Mode): 15 tasks, 8 weeks
- Phase 6 (Polish & Deployment): 17 tasks, 12 weeks

**By Role:**
- Backend Engineer: ~40 tasks
- Frontend Engineer: ~25 tasks
- ML Engineer: ~8 tasks
- QA Engineer: ~10 tasks
- Product Designer: ~5 tasks
- Other: ~4 tasks

### Total Effort: ~460 person-days = 92 person-weeks = 1.77 person-years

**With team of 3.5 FTE:** 92 weeks ÷ 3.5 = ~26 weeks = ~6 months **if perfectly parallelized**

**Realistic timeline with dependencies:** 52 weeks = 12 months

---

## Next Step: Create Beads Items

Now I'll create all 92 tasks as Beads items...

**Document Version**: 1.0
**Last Updated**: 2025-10-15
