# ICS Phase 2 Planning Document

**Date**: 2025-10-26
**Version**: 1.0
**Status**: Planning
**Phase**: Phase 2 (Constraint Propagation & Intelligence)
**Predecessor**: Phase 1 Complete (see `docs/planning/PHASE_1_COMPLETION_REPORT.md`)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 1 Learnings](#phase-1-learnings)
3. [Deferred Features from Phase 1](#deferred-features-from-phase-1)
4. [Phase 2 Scope Definition](#phase-2-scope-definition)
5. [Architecture Decisions](#architecture-decisions)
6. [Implementation Plan](#implementation-plan)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Risk Assessment](#risk-assessment)
9. [Timeline & Resources](#timeline--resources)
10. [Dependencies & Prerequisites](#dependencies--prerequisites)

---

## Executive Summary

### Phase 2 Goals

**ICS Phase 2** builds on Phase 1's proven semantic editor foundation by adding **intelligence and constraint flow**:

1. **Constraint Propagation & Hole Resolution** - Complete the typed-hole workflow with real constraint solving
2. **Dependency Graph Visualization** - Visual understanding of hole dependencies and critical path
3. **AI Chat Integration** - Conversational specification refinement via LLM
4. **Backend NLP Deployment** - Production-ready semantic analysis API

### Key Deliverables

- **Constraint Solver Integration**: Z3 or MiniZinc backend for solution space narrowing
- **Interactive Dependency Graph**: D3.js or Cytoscape.js visualization with critical path
- **AI Chat Assistant**: Claude/OpenAI integration with `/refine`, `/analyze` commands
- **Production Backend**: Modal.com deployment with spaCy + HuggingFace NER
- **Enhanced NLP**: Relationships, effects, assertions detection

### Timeline Estimate

**8 weeks** (2 months)
- Week 1-2: Architecture setup (constraint solver, graph library, AI backend)
- Week 3-4: Constraint propagation implementation
- Week 5-6: Dependency graph visualization + AI chat
- Week 7: Backend deployment + integration
- Week 8: Testing, polish, documentation

### Success Metrics

**User Can**:
- Resolve a typed hole and see constraints propagate to dependent holes
- View dependency graph showing which holes block others
- Chat with AI to refine specifications or resolve ambiguities
- Get real semantic analysis from backend (not just mock patterns)

**Technical**:
- All Phase 2 acceptance criteria pass (80+ new tests)
- Constraint propagation correctly narrows solution spaces
- Dependency graph renders in <1s for 100+ holes
- AI chat responds in <3s with contextual suggestions
- Backend handles 100 concurrent analysis requests

---

## Phase 1 Learnings

### What Worked Well

1. **Test-Driven Development** - 192 passing tests gave confidence throughout
2. **Incremental STEPs** - Breaking work into 32 STEPs made progress manageable
3. **State Machine Specification** - Clear component states prevented confusion
4. **Mock-First Approach** - Mock analysis allowed frontend development before backend
5. **OODA Loop Focus** - Performance budgets kept UX snappy (<2s cycles)

### What to Improve in Phase 2

1. **Earlier Integration Testing** - Delay in backend integration caused initial test failures
2. **More Explicit Dependencies** - Some features assumed others were complete
3. **Design Decisions Documentation** - Option C pattern worked well, use for Phase 2
4. **Frontend-Backend Contract** - Define API schemas upfront with OpenAPI spec
5. **Performance Benchmarking** - Add metrics from start, not end

### Technical Debt from Phase 1

**Priority 1 (Fix in Phase 2)**:
- 17 non-ICS test failures (PromptWorkbench, Auth, IDE, IR, VersionHistory)
- No React ErrorBoundary components (resilience gap)
- No environment-conditional logging (clutters console)

**Priority 2 (Nice-to-have)**:
- Loading skeletons in SymbolsPanel (optional, updates are fast)
- Tooltip content validation in E2E tests (test quality)
- Multi-browser E2E testing (currently Chromium only)

**Priority 3 (Defer to Phase 3+)**:
- Visual regression testing (Chromatic/Percy)
- Automated accessibility testing (axe-core)

---

## Deferred Features from Phase 1

### From specs/ics-spec-v1.md Section 9

**Backend TODOs** (from `lift_sys/nlp/pipeline.py`):

1. **Relationship Extraction** (Line 232)
   - **Why Deferred**: Requires additional UI, not critical for MVP
   - **Phase 2 Plan**: Use spaCy dependency parsing for subject-verb-object triples
   - **Frontend Impact**: Add "Relationships" tab to SymbolsPanel

2. **Effects Detection** (Line 133)
   - **Why Deferred**: Requires semantic understanding beyond NER
   - **Phase 2 Plan**: Pattern matching + DSPy for I/O operations (write, read, modify)
   - **Frontend Impact**: Add "Effects" tab to SymbolsPanel

3. **Assertions Detection** (Line 134)
   - **Why Deferred**: Advanced logical reasoning needed
   - **Phase 2 Plan**: Pattern matching for preconditions, postconditions, invariants
   - **Frontend Impact**: Add "Assertions" tab to SymbolsPanel

4. **Contradiction Detection** (Line 318)
   - **Why Deferred**: Deep semantic understanding required, likely Phase 3
   - **Phase 2 Status**: Keep deferred, focus on constraint propagation first
   - **Phase 3 Plan**: DSPy signatures + textual entailment models

**Frontend TODOs** (from `frontend/src/store/useICSStore.ts`):

5. **Constraint Validation** (Line 158)
   - **Why Deferred**: Requires constraint solver
   - **Phase 2 Plan**: Integrate Z3 or MiniZinc for validation
   - **Acceptance**: Refinement rejected if conflicts with existing constraints

6. **Solution Space Recalculation** (Line 204)
   - **Why Deferred**: Requires constraint satisfaction logic
   - **Phase 2 Plan**: Calculate percentage reduction when constraints applied
   - **Acceptance**: HoleInspector shows "Solution space: 87% → 23% (5 constraints)"

**UI Features**:

7. **Dependency Graph Visualization**
   - **Why Deferred**: Not critical for basic editor functionality
   - **Phase 2 Plan**: Interactive graph with zoom, pan, critical path highlighting
   - **Library Decision**: D3.js vs Cytoscape.js (see Architecture Decisions)

8. **AI Chat Integration**
   - **Why Deferred**: Backend infrastructure not ready
   - **Phase 2 Plan**: Claude/OpenAI API with conversational refinement
   - **Acceptance**: `/refine H1` generates suggestions, `/analyze` finds issues

---

## Phase 2 Scope Definition

### Must Have (Phase 2 Acceptance Criteria)

**Constraint Propagation**:
- ✅ User can resolve a typed hole by providing refinement
- ✅ System validates refinement against existing constraints
- ✅ System detects conflicts and rejects invalid refinements
- ✅ Resolving a hole propagates constraints to dependent holes (via `blocks` relationships)
- ✅ HoleInspector shows solution space narrowing (before/after percentages)
- ✅ SymbolsPanel updates to show newly constrained holes

**Dependency Graph Visualization**:
- ✅ User can view dependency graph of all holes
- ✅ Graph shows nodes (holes) and edges (blocks/blockedBy relationships)
- ✅ Critical path highlighted (holes that block the most downstream work)
- ✅ Graph interactive: zoom, pan, click node → select hole
- ✅ Graph renders in <1s for 100 holes, <5s for 1000 holes

**AI Chat Assistant**:
- ✅ User can open chat panel and send messages
- ✅ AI responds with contextual suggestions based on current specification
- ✅ Commands: `/refine H1`, `/analyze`, `/suggest`, `/clarify`
- ✅ Chat history persisted in session
- ✅ AI suggestions can be applied directly to specification (insert text)
- ✅ Chat response time <3s for simple queries, <10s for complex analysis

**Backend NLP Deployment**:
- ✅ Backend deployed to Modal.com with GPU workers
- ✅ `/ics/analyze` endpoint returns enhanced analysis (entities, modals, constraints, holes, relationships, effects, assertions)
- ✅ Backend handles 100 concurrent requests without degradation
- ✅ Health check endpoint monitors backend status
- ✅ Frontend uses backend by default, falls back to mock on failure
- ✅ Backend confidence scores guide UI (highlight low-confidence elements differently)

**Enhanced NLP**:
- ✅ Relationship extraction working (subject-verb-object triples)
- ✅ Effects detection working (I/O operations, state changes)
- ✅ Assertions detection working (preconditions, postconditions, invariants)
- ✅ Frontend displays relationships, effects, assertions in SymbolsPanel tabs

### Should Have (High Priority Enhancements)

**Improved UX**:
- ✅ Undo/redo for hole resolutions
- ✅ Bulk operations (resolve multiple holes, apply constraint to many)
- ✅ Export specification to Markdown with annotations
- ✅ Import existing specifications and analyze

**Error Handling**:
- ✅ React ErrorBoundary components around ICS panels
- ✅ Better error messages (user-friendly, actionable)
- ✅ Retry logic for backend API calls (exponential backoff)

**Performance**:
- ✅ Lazy loading for dependency graph (render only visible nodes)
- ✅ Debounce constraint validation (500ms after user stops typing)
- ✅ Cache backend responses (1-hour TTL for same input text)

### Could Have (Nice-to-Have)

**Polish**:
- ✅ Loading skeletons in SymbolsPanel during analysis
- ✅ Dark mode support for all ICS components
- ✅ Keyboard shortcuts for common actions (resolve hole: Cmd+R, chat: Cmd+K)

**Developer Experience**:
- ✅ OpenAPI spec for backend API
- ✅ Storybook for ICS components
- ✅ Visual regression tests for critical UI

### Won't Have (Explicitly Deferred to Phase 3+)

**Phase 3 Features**:
- ❌ Semantic search across specifications
- ❌ Contradiction detection (requires deep semantic reasoning)
- ❌ Multi-user real-time collaboration

**Phase 4 Features**:
- ❌ Git integration (commit, push, diff from ICS)
- ❌ Code generation from resolved specifications
- ❌ Version control for specifications

**Phase 5 Features**:
- ❌ Team workflows and review processes
- ❌ Specification templates library
- ❌ Analytics dashboard

---

## Architecture Decisions

### AD1: Constraint Solver Selection

**Options Considered**:

1. **Z3 (Microsoft Research)**
   - Pros: Powerful SMT solver, Python bindings (z3-solver)
   - Cons: Complex API, overkill for simple constraints
   - Best for: Complex logical constraints, type systems

2. **MiniZinc**
   - Pros: High-level constraint modeling language, fast
   - Cons: Requires MiniZinc runtime, less Pythonic
   - Best for: Optimization problems, scheduling

3. **python-constraint**
   - Pros: Pure Python, simple API, lightweight
   - Cons: Not as powerful as Z3, slower for large problems
   - Best for: Simple CSPs, rapid prototyping

**Decision**: **Z3** for Phase 2

**Rationale**:
- ICS constraints are semantic (type constraints, value constraints, temporal)
- Z3's SMT capabilities handle mixed constraint types well
- Python bindings mature and well-documented
- Can model constraint propagation as logical implications
- Performance acceptable for 100-1000 holes (tested in prototypes)

**Implementation Plan**:
- Install: `uv add z3-solver`
- Create `lift_sys/constraint_solver/z3_backend.py`
- Model holes as Z3 variables, constraints as Z3 assertions
- Solve on refinement, check SAT/UNSAT
- Calculate solution space reduction by counting models

**Alternatives Considered**: Keep simple python-constraint as fallback if Z3 proves too complex

---

### AD2: Dependency Graph Library Selection

**Options Considered**:

1. **D3.js (Force-Directed Graph)**
   - Pros: Extremely flexible, beautiful visualizations, rich ecosystem
   - Cons: Steep learning curve, manual layout tuning
   - Best for: Custom graph layouts, animations

2. **Cytoscape.js**
   - Pros: Graph-focused API, built-in layouts (dagre, cose), extensible
   - Cons: Larger bundle size (~500KB), less "flashy" than D3
   - Best for: DAG visualization, network analysis

3. **React Flow**
   - Pros: React-native, easy node/edge customization, good docs
   - Cons: Horizontal layout bias, less mature than D3/Cytoscape
   - Best for: Flowcharts, pipelines

4. **vis.js Network**
   - Pros: Simple API, physics simulation, good defaults
   - Cons: Less actively maintained, limited customization
   - Best for: Quick prototypes

**Decision**: **Cytoscape.js** for Phase 2

**Rationale**:
- ICS dependency graph is a **DAG** (Directed Acyclic Graph) - Cytoscape optimized for this
- Built-in **dagre** layout perfect for top-to-bottom dependency flow
- Critical path highlighting easy with Cytoscape selectors (`:selected`, CSS classes)
- React wrapper available: `react-cytoscapejs`
- Used in production tools (e.g., Netflix, Uber dashboards)
- Bundle size acceptable (<500KB, code-split in ICSView chunk)

**Implementation Plan**:
- Install: `npm install cytoscape react-cytoscapejs`
- Create `frontend/src/components/ics/DependencyGraph.tsx`
- Data model: Nodes = holes, Edges = `blocks` relationships
- Layout: dagre (hierarchical top-to-bottom)
- Interactivity: Click node → select hole, hover → tooltip
- Critical path: BFS from unresolved holes with most dependents

**Alternatives Considered**: If performance issues arise, fallback to vis.js or simple React Flow

---

### AD3: AI Chat Backend Selection

**Options Considered**:

1. **Claude API (Anthropic)**
   - Pros: Best for long context, excellent reasoning, function calling
   - Cons: Cost ($15/M tokens for Claude 3.5 Sonnet), rate limits
   - Best for: Complex analysis, multi-turn conversations

2. **OpenAI GPT-4**
   - Pros: Widely used, strong code understanding, cheaper ($10/M tokens)
   - Cons: Context length limits, less reasoning than Claude
   - Best for: General-purpose chat, summarization

3. **OpenAI GPT-3.5-turbo**
   - Pros: Very cheap ($0.50/M tokens), fast (<1s latency)
   - Cons: Less accurate, struggles with complex reasoning
   - Best for: Simple refinement, autocomplete

4. **Local LLM (Llama 3.1 70B via Ollama)**
   - Pros: No API costs, full control, privacy
   - Cons: Requires GPU, slower, less capable than Claude/GPT-4
   - Best for: On-prem deployments, sensitive data

**Decision**: **Claude 3.5 Sonnet** for Phase 2

**Rationale**:
- ICS specifications are **long context** (10k+ tokens) - Claude excels here
- Reasoning about constraints, dependencies requires **strong reasoning** - Claude best-in-class
- Function calling enables structured output (e.g., `/refine H1` returns typed suggestions)
- Cost acceptable for beta testing (~$50/month for 100 users @ 10 chats/day)
- Anthropic API well-documented, Python SDK mature

**Implementation Plan**:
- Install: `uv add anthropic`
- Create `lift_sys/ai/claude_client.py`
- System prompt: "You are an AI assistant for ICS (Integrated Context Studio), helping users refine natural language specifications..."
- Commands: Parse user message, extract `/refine H1` → fetch hole details → generate suggestions
- Frontend: Chat component sends message to `/ics/chat` endpoint → streams response
- Caching: Cache responses for identical messages (1-hour TTL)

**Cost Mitigation**:
- Use **caching** for repeated queries
- Use **cheaper model** (Claude 3 Haiku at $0.25/M tokens) for simple commands like `/clarify`
- Offer **OpenAI fallback** if cost becomes issue (configurable via env var)

**Alternatives Considered**: Switch to GPT-4 Turbo if cost exceeds budget, or add local Llama for on-prem

---

### AD4: Backend Deployment Platform

**Options Considered**:

1. **Modal.com (Serverless GPU)**
   - Pros: Already using for lift-sys, GPU access, auto-scaling, Python-native
   - Cons: Vendor lock-in, cold start latency (~30s for GPU)
   - Best for: ML workloads, bursty traffic

2. **AWS Lambda + API Gateway**
   - Pros: Industry standard, mature, granular pricing
   - Cons: No GPU, complex setup (VPC, IAM), cold starts
   - Best for: General APIs, high availability

3. **Google Cloud Run**
   - Pros: Containerized, auto-scaling, cheap
   - Cons: No GPU in serverless, cold starts
   - Best for: Stateless APIs, microservices

4. **Dedicated Server (Hetzner, DigitalOcean)**
   - Pros: No cold starts, full control, cheap for steady load
   - Cons: No auto-scaling, manual DevOps, uptime responsibility
   - Best for: Predictable traffic, cost optimization

**Decision**: **Modal.com** for Phase 2

**Rationale**:
- **Already integrated** with lift-sys project (Modal secrets configured)
- **GPU support** for HuggingFace NER model (dslim/bert-large-NER)
- **Auto-scaling** handles burst traffic (100 users analyzing simultaneously)
- **Python-native** - no containerization overhead
- **Fast iteration** - deploy with `modal deploy`
- **Cost-effective** for development (pay-per-use, no idle costs)

**Implementation Plan**:
- Reuse `lift_sys/api/server.py` with Modal decorators
- Deploy endpoint: `modal deploy lift_sys/api/server.py`
- Use L40S GPU for NER model loading (cost/perf balance)
- Set timeout: 30s (most analyses <5s)
- Health check: Ping every 5 minutes to keep warm (avoid cold starts)
- Frontend: Update API URL to `https://rand--lift-sys-api.modal.run/ics/analyze`

**Migration Path**: If cost becomes issue in production, migrate to Google Cloud Run (CPU-only, smaller model)

---

### AD5: Frontend-Backend API Contract

**Decision**: Define OpenAPI 3.1 spec upfront, generate TypeScript types

**Rationale**:
- Phase 1 had **type mismatches** (snake_case backend, camelCase frontend)
- OpenAPI spec ensures **contract-first development**
- TypeScript types auto-generated from spec (via `openapi-typescript`)
- Backend validates requests/responses against spec (via Pydantic)
- API documentation auto-generated (via Redoc or Swagger UI)

**Implementation Plan**:

1. **Create OpenAPI Spec**: `specs/ics-api-v2.yaml`
   ```yaml
   openapi: 3.1.0
   info:
     title: ICS Semantic Analysis API
     version: 2.0.0
   paths:
     /ics/analyze:
       post:
         summary: Analyze specification text
         requestBody:
           content:
             application/json:
               schema:
                 $ref: '#/components/schemas/AnalyzeRequest'
         responses:
           200:
             content:
               application/json:
                 schema:
                   $ref: '#/components/schemas/SemanticAnalysis'
   components:
     schemas:
       AnalyzeRequest:
         type: object
         required: [text]
         properties:
           text: {type: string, maxLength: 50000}
           options:
             type: object
             properties:
               includeConfidence: {type: boolean}
               detectRelationships: {type: boolean}
       SemanticAnalysis:
         type: object
         properties:
           entities: {type: array, items: {$ref: '#/components/schemas/Entity'}}
           relationships: {type: array, items: {$ref: '#/components/schemas/Relationship'}}
           # ... (full schema)
   ```

2. **Generate TypeScript Types**:
   ```bash
   npm install -D openapi-typescript
   npx openapi-typescript specs/ics-api-v2.yaml -o frontend/src/types/ics/api.generated.ts
   ```

3. **Backend Validation**:
   - Use Pydantic models generated from OpenAPI spec (via `datamodel-code-generator`)
   - FastAPI auto-validates requests/responses
   - Return 422 for schema violations

4. **Frontend Usage**:
   ```typescript
   import type { components } from '@/types/ics/api.generated';

   type AnalyzeRequest = components['schemas']['AnalyzeRequest'];
   type SemanticAnalysis = components['schemas']['SemanticAnalysis'];
   ```

**Benefit**: No more type mismatches, frontend-backend contract explicit and versioned

---

## Implementation Plan

### STEP-by-STEP Breakdown (Similar to Phase 1)

**Total Steps**: ~30 STEPs over 8 weeks

---

### Week 1-2: Architecture Setup & Backend Enhancement

#### STEP-1: OpenAPI Specification
**Goal**: Define ICS API v2 contract
**Tasks**:
- Create `specs/ics-api-v2.yaml` with all endpoints (`/analyze`, `/chat`, `/health`)
- Generate TypeScript types: `frontend/src/types/ics/api.generated.ts`
- Generate Pydantic models: `lift_sys/api/models_generated.py`
**Acceptance**: OpenAPI spec valid, types generated, no compilation errors
**Estimate**: 1 day

#### STEP-2: Backend - Relationship Extraction
**Goal**: Implement relationship detection using spaCy dependencies
**Tasks**:
- Implement `_extract_relationships()` in `lift_sys/nlp/pipeline.py`
- Use spaCy dependency parsing (subject-verb-object triples)
- Add relationship types: `calls`, `extends`, `contains`, `requires`
- Write 20 unit tests (various sentence structures)
**Acceptance**: Relationships detected with 70%+ accuracy on test corpus
**Estimate**: 2 days

#### STEP-3: Backend - Effects Detection
**Goal**: Detect I/O operations and side effects
**Tasks**:
- Implement `_detect_effects()` in `lift_sys/nlp/pipeline.py`
- Pattern matching for keywords: write, read, modify, delete, create, fetch, send
- Classify effects: `io_read`, `io_write`, `state_change`, `network_call`
- Write 15 unit tests
**Acceptance**: Effects detected with 60%+ accuracy
**Estimate**: 2 days

#### STEP-4: Backend - Assertions Detection
**Goal**: Detect pre/postconditions and invariants
**Tasks**:
- Implement `_detect_assertions()` in `lift_sys/nlp/pipeline.py`
- Pattern matching for: precondition, postcondition, invariant, assert, require, ensure
- Classify assertions: `precondition`, `postcondition`, `invariant`
- Write 15 unit tests
**Acceptance**: Assertions detected with 60%+ accuracy
**Estimate**: 2 days

#### STEP-5: Backend Deployment to Modal
**Goal**: Deploy enhanced backend to production
**Tasks**:
- Update `lift_sys/api/server.py` with Modal decorators
- Configure GPU (L40S) for HuggingFace model
- Set timeout: 30s, concurrency: 100
- Health check endpoint: `/ics/health` (ping every 5min)
- Deploy: `modal deploy lift_sys/api/server.py`
- Test endpoint: `curl https://rand--lift-sys-api.modal.run/ics/analyze`
**Acceptance**: Backend responds in <5s, handles 100 concurrent requests
**Estimate**: 1 day

#### STEP-6: Frontend - Enhanced NLP Display
**Goal**: Show relationships, effects, assertions in UI
**Tasks**:
- Add "Relationships" tab to SymbolsPanel
- Add "Effects" tab to SymbolsPanel
- Add "Assertions" tab to SymbolsPanel
- Update store: `semanticAnalysis` includes new fields
- Update decorations: Highlight relationships (purple), effects (orange), assertions (teal)
**Acceptance**: All 3 new semantic elements visible in UI
**Estimate**: 2 days

---

### Week 3-4: Constraint Propagation

#### STEP-7: Z3 Constraint Solver Integration
**Goal**: Set up Z3 for constraint satisfaction
**Tasks**:
- Install: `uv add z3-solver`
- Create `lift_sys/constraint_solver/z3_backend.py`
- Model holes as Z3 variables (type: String, Int, Bool based on hint)
- Model constraints as Z3 assertions (temporal → Implies, type → custom sorts)
- Implement `solve()` → returns SAT/UNSAT
- Write 20 unit tests (simple constraints: type, value, temporal)
**Acceptance**: Z3 solver correctly identifies conflicts, suggests valid refinements
**Estimate**: 3 days

#### STEP-8: Constraint Validation
**Goal**: Validate hole refinements against constraints
**Tasks**:
- Implement `validateRefinement(holeId, refinement)` in store
- Call Z3 solver to check if refinement satisfies constraints
- Return error if UNSAT, success if SAT
- Show validation errors in HoleInspector
- Write 15 integration tests (valid/invalid refinements)
**Acceptance**: Invalid refinements rejected with clear error message
**Estimate**: 2 days

#### STEP-9: Constraint Propagation Logic
**Goal**: Propagate constraints when hole resolved
**Tasks**:
- Implement `propagateConstraints(holeId, refinement)` in store
- Traverse dependency graph (BFS over `blocks` edges)
- Add new constraints to dependent holes (e.g., if H1 → "OAuth", H3 constrained to "support OAuth tokens")
- Update hole metadata: `appliedConstraints`, `solutionSpaceReduction`
- Write 20 integration tests (simple 2-3 hole chains)
**Acceptance**: Resolving H1 correctly constrains H3, H5, etc.
**Estimate**: 3 days

#### STEP-10: Solution Space Calculation
**Goal**: Calculate solution space narrowing percentage
**Tasks**:
- Implement `calculateSolutionSpace(holeId)` in store
- Before constraints: Count Z3 models (sample 1000 solutions)
- After constraints: Count Z3 models (should be fewer)
- Reduction = `(before - after) / before * 100%`
- Display in HoleInspector: "Solution space: 100% → 23% (5 constraints)"
**Acceptance**: Percentage accurate within ±10% (sampling variance)
**Estimate**: 2 days

#### STEP-11: Hole Resolution UI
**Goal**: Implement "Resolve" button workflow
**Tasks**:
- HoleInspector: Add refinement input field
- Button: "Resolve" → calls `validateRefinement()` → `propagateConstraints()`
- Show success toast: "Hole H1 resolved, 3 dependent holes constrained"
- Update SymbolsPanel: Newly constrained holes highlighted
- Add undo/redo support (store action history)
**Acceptance**: User can resolve hole, see propagation visually
**Estimate**: 2 days

#### STEP-12: Constraint Propagation Tests
**Goal**: Comprehensive E2E tests for propagation
**Tasks**:
- Write 10 E2E tests:
  - Simple 2-hole chain (H1 → H2)
  - Complex 5-hole DAG
  - Circular dependency rejection
  - Invalid refinement rejection
  - Undo/redo propagation
- Run full test suite
**Acceptance**: All propagation tests pass
**Estimate**: 2 days

---

### Week 5-6: Dependency Graph & AI Chat

#### STEP-13: Dependency Graph Component
**Goal**: Create interactive Cytoscape.js graph
**Tasks**:
- Install: `npm install cytoscape react-cytoscapejs`
- Create `frontend/src/components/ics/DependencyGraph.tsx`
- Data: Nodes = holes, Edges = `blocks` relationships
- Layout: dagre (top-to-bottom)
- Styling: Unresolved holes (red), resolved (green), constrained (amber)
- Interactivity: Click node → select hole in HoleInspector
**Acceptance**: Graph renders 100 holes in <1s
**Estimate**: 3 days

#### STEP-14: Critical Path Highlighting
**Goal**: Highlight holes blocking most downstream work
**Tasks**:
- Implement BFS: Start from unresolved holes, traverse `blocks` edges
- Count downstream dependencies for each hole
- Highlight top 10% as critical path (bold border, red glow)
- Tooltip: "H1 blocks 5 downstream holes"
**Acceptance**: Critical path visually distinct, accurate
**Estimate**: 1 day

#### STEP-15: Graph Performance Optimization
**Goal**: Handle large graphs (1000+ holes)
**Tasks**:
- Lazy loading: Render only visible nodes (viewport culling)
- Pagination: Load graph in chunks (100 nodes at a time)
- Debounce updates: Only re-render after 500ms of no changes
- Benchmark: 1000-hole graph rendering time
**Acceptance**: 1000-hole graph renders in <5s
**Estimate**: 2 days

#### STEP-16: AI Chat Backend Setup
**Goal**: Claude API integration
**Tasks**:
- Install: `uv add anthropic`
- Create `lift_sys/ai/claude_client.py`
- System prompt: "You are an AI assistant for ICS..."
- Endpoint: `/ics/chat` (POST with message, returns response)
- Commands: Parse `/refine H1`, `/analyze`, `/suggest`, `/clarify`
- Write 10 integration tests (mock Claude responses)
**Acceptance**: Backend returns structured suggestions for commands
**Estimate**: 2 days

#### STEP-17: AI Chat Frontend Component
**Goal**: Chat UI with message history
**Tasks**:
- Create `frontend/src/components/ics/AIChat.tsx`
- UI: Message list (user/AI bubbles), input field, send button
- State: Chat history in store (persist to localStorage)
- Streaming: Use SSE or polling for AI responses
- Apply suggestions: Insert button next to AI message → insert text into editor
**Acceptance**: User can chat, see history, apply suggestions
**Estimate**: 3 days

#### STEP-18: AI Chat Commands Implementation
**Goal**: Implement `/refine`, `/analyze`, etc.
**Tasks**:
- `/refine H1`: Fetch hole details, generate 3 refinement suggestions with rationale
- `/analyze`: Analyze entire spec for ambiguities, missing constraints, contradictions
- `/suggest`: Suggest next holes to resolve (based on critical path)
- `/clarify`: Ask clarifying questions about ambiguous sections
- Write 15 E2E tests (one per command)
**Acceptance**: All commands return contextual, helpful responses
**Estimate**: 3 days

#### STEP-19: AI Chat Performance & Caching
**Goal**: <3s response time for simple queries
**Tasks**:
- Cache identical messages (Redis or in-memory TTL cache)
- Use cheaper model (Claude 3 Haiku) for simple commands
- Timeout: 10s, show "AI is thinking..." spinner
- Error handling: Show "AI unavailable" if timeout or API error
**Acceptance**: 90% of queries <3s, cache hit rate >50%
**Estimate**: 1 day

---

### Week 7: Integration & Polish

#### STEP-20: Frontend-Backend Integration
**Goal**: Wire up all Phase 2 features
**Tasks**:
- Update API client: New endpoints for `/chat`, enhanced `/analyze`
- Update store: Handle new semantic elements (relationships, effects, assertions)
- Update decorations: New highlight colors
- Integration tests: Backend → Frontend flow for all features
**Acceptance**: All features work end-to-end
**Estimate**: 2 days

#### STEP-21: Error Handling Improvements
**Goal**: React ErrorBoundary + better error UX
**Tasks**:
- Create `frontend/src/components/ErrorBoundary.tsx`
- Wrap each ICS panel in ErrorBoundary
- Better error messages: User-friendly, actionable (e.g., "Constraint conflict: H1 requires OAuth but H2 requires basic auth. Resolve H2 first.")
- Retry logic: Exponential backoff for backend API calls (3 retries, 1s, 2s, 4s)
**Acceptance**: No uncaught errors, all errors handled gracefully
**Estimate**: 2 days

#### STEP-22: Performance Benchmarking
**Goal**: Measure OODA loops, backend latency
**Tasks**:
- Instrument code: Add timing metrics (console.time/timeEnd)
- Benchmark OODA loops: Semantic analysis, hole resolution, graph render, AI chat
- Backend latency: Measure p50, p95, p99 for `/analyze` and `/chat`
- Document results: `docs/benchmarks/PHASE_2_PERFORMANCE.md`
**Acceptance**: All OODA loops meet targets (Phase 2 spec)
**Estimate**: 1 day

#### STEP-23: Phase 2 E2E Test Suite
**Goal**: Comprehensive E2E tests for all Phase 2 features
**Tasks**:
- Write 30 new E2E tests:
  - Constraint propagation (10 tests)
  - Dependency graph (5 tests)
  - AI chat (10 tests)
  - Backend integration (5 tests)
- Run full suite (Phase 1 + Phase 2): 52 total tests
**Acceptance**: All 52 tests pass
**Estimate**: 3 days

---

### Week 8: Testing, Documentation, Deployment

#### STEP-24: Unit Test Coverage
**Goal**: 90%+ coverage for new code
**Tasks**:
- Write unit tests for:
  - Z3 backend (constraint_solver/)
  - AI chat backend (ai/)
  - Frontend constraint store logic
  - Dependency graph logic
- Run coverage: `uv run pytest --cov`
**Acceptance**: Coverage >90% for Phase 2 code
**Estimate**: 2 days

#### STEP-25: Bug Fixing Pass
**Goal**: Fix all known issues from testing
**Tasks**:
- Review failing tests, fix root causes
- Manual testing: Click through all workflows
- Fix non-ICS test failures from Phase 1 (17 tests)
- Update `.beads/issues.jsonl` with resolved bugs
**Acceptance**: Zero failing tests, clean CI/CD
**Estimate**: 2 days

#### STEP-26: Documentation
**Goal**: Update all specs and guides
**Tasks**:
- Update `specs/ics-spec-v1.md` → v2 (Phase 2 features)
- Write `docs/planning/PHASE_2_COMPLETION_REPORT.md`
- Update README with Phase 2 screenshots
- API documentation: Redoc from OpenAPI spec
- User guide: How to use constraint propagation, dependency graph, AI chat
**Acceptance**: All documentation current and accurate
**Estimate**: 2 days

#### STEP-27: Production Deployment
**Goal**: Deploy to production
**Tasks**:
- Frontend: `npm run build` → deploy to Vercel/Cloudflare
- Backend: `modal deploy` → production endpoint
- Secrets: Configure API keys (Claude, Supabase)
- Monitoring: Set up health checks, alerts
- Smoke test: Full user workflow in production
**Acceptance**: Production deployment successful, all features working
**Estimate**: 1 day

#### STEP-28: Phase 2 Completion Verification
**Goal**: Sign-off on Phase 2
**Tasks**:
- Review all acceptance criteria (60+ criteria)
- Verify all STEPs complete
- Performance benchmarks documented
- Create completion report (this document)
- Merge PR to main
**Acceptance**: Phase 2 complete, ready for Phase 3 planning
**Estimate**: 1 day

---

## Acceptance Criteria

### AC1: Constraint Propagation (15 criteria)

| ID | Criterion | Target |
|----|-----------|--------|
| CP1 | User can resolve hole by providing refinement | ✅ Working in UI |
| CP2 | System validates refinement against constraints | ✅ Z3 solver validates |
| CP3 | Invalid refinements rejected with error message | ✅ Error shown in HoleInspector |
| CP4 | Resolving hole propagates constraints to dependents | ✅ BFS traversal works |
| CP5 | HoleInspector shows solution space before/after | ✅ Percentage displayed |
| CP6 | Solution space calculation accurate within ±10% | ✅ Sampling variance acceptable |
| CP7 | SymbolsPanel updates to show newly constrained holes | ✅ Real-time UI update |
| CP8 | Undo/redo for hole resolutions | ✅ Action history works |
| CP9 | Bulk resolve multiple holes | ✅ UI supports multi-select |
| CP10 | Circular dependency detection | ✅ Rejected with error |
| CP11 | Constraint conflict detection | ✅ Z3 returns UNSAT |
| CP12 | Z3 solver handles 100 holes in <1s | ✅ Performance acceptable |
| CP13 | Propagation updates 50 dependent holes in <2s | ✅ BFS fast enough |
| CP14 | Unit tests: 20 passing for Z3 backend | ✅ 100% pass rate |
| CP15 | E2E tests: 10 passing for propagation | ✅ 100% pass rate |

### AC2: Dependency Graph (10 criteria)

| ID | Criterion | Target |
|----|-----------|--------|
| DG1 | Graph renders 100 holes in <1s | ✅ Cytoscape performance |
| DG2 | Graph renders 1000 holes in <5s | ✅ Lazy loading works |
| DG3 | Critical path highlighted visually | ✅ Red glow on top 10% |
| DG4 | Click node → select hole in HoleInspector | ✅ Interactivity works |
| DG5 | Zoom, pan, reset view | ✅ Cytoscape built-in |
| DG6 | Tooltip on hover shows hole details | ✅ Rich tooltip |
| DG7 | Graph updates in real-time when hole resolved | ✅ Node color changes |
| DG8 | Graph layout correct (top-to-bottom DAG) | ✅ dagre layout |
| DG9 | No graph rendering errors in console | ✅ Error-free |
| DG10 | E2E tests: 5 passing for graph | ✅ 100% pass rate |

### AC3: AI Chat (15 criteria)

| ID | Criterion | Target |
|----|-----------|--------|
| AI1 | User can open chat panel and send messages | ✅ UI working |
| AI2 | AI responds in <3s for simple queries | ✅ 90th percentile |
| AI3 | AI responds in <10s for complex queries | ✅ 95th percentile |
| AI4 | `/refine H1` generates 3 suggestions with rationale | ✅ Structured output |
| AI5 | `/analyze` finds ambiguities, missing constraints | ✅ Full spec analysis |
| AI6 | `/suggest` recommends next holes to resolve | ✅ Critical path aware |
| AI7 | `/clarify` asks clarifying questions | ✅ Interactive refinement |
| AI8 | Chat history persisted across sessions | ✅ localStorage works |
| AI9 | AI suggestions can be applied to editor | ✅ Insert button works |
| AI10 | Cache hit rate >50% for repeated queries | ✅ TTL cache effective |
| AI11 | Error handling: "AI unavailable" on timeout | ✅ Fallback UI |
| AI12 | Retry logic: 3 retries with exponential backoff | ✅ Resilient |
| AI13 | Cost tracking: <$100/month for 100 beta users | ✅ Budget acceptable |
| AI14 | Integration tests: 10 passing for chat backend | ✅ 100% pass rate |
| AI15 | E2E tests: 10 passing for chat UI | ✅ 100% pass rate |

### AC4: Backend NLP (10 criteria)

| ID | Criterion | Target |
|----|-----------|--------|
| BE1 | Backend deployed to Modal.com | ✅ Production URL live |
| BE2 | `/ics/analyze` returns relationships, effects, assertions | ✅ Enhanced schema |
| BE3 | Backend handles 100 concurrent requests | ✅ Auto-scaling works |
| BE4 | Health check endpoint returns 200 OK | ✅ Monitoring green |
| BE5 | Backend latency: p50 <2s, p95 <5s | ✅ Performance acceptable |
| BE6 | Frontend uses backend by default | ✅ API client updated |
| BE7 | Frontend falls back to mock on backend failure | ✅ Graceful degradation |
| BE8 | Confidence scores shown in UI (badge color) | ✅ Low confidence = amber |
| BE9 | Relationship detection accuracy >70% | ✅ Test corpus validation |
| BE10 | Effects/Assertions detection accuracy >60% | ✅ Test corpus validation |

### AC5: Code Quality (10 criteria)

| ID | Criterion | Target |
|----|-----------|--------|
| CQ1 | All 52 E2E tests pass (Phase 1 + Phase 2) | ✅ 100% pass rate |
| CQ2 | Unit test coverage >90% for Phase 2 code | ✅ Coverage report |
| CQ3 | Zero console errors during normal operation | ✅ Browser console clean |
| CQ4 | OpenAPI spec valid and documented | ✅ Redoc generated |
| CQ5 | TypeScript strict mode, no `any` types | ✅ tsc passes |
| CQ6 | All TODOs resolved or deferred with plan | ✅ No blocking TODOs |
| CQ7 | Phase 2 scope clearly documented | ✅ This document |
| CQ8 | Phase 3 features clearly deferred | ✅ See Won't Have |
| CQ9 | React ErrorBoundary around all ICS panels | ✅ Resilience improved |
| CQ10 | Non-ICS test failures fixed (17 from Phase 1) | ✅ Clean CI/CD |

**Total Acceptance Criteria**: **60 criteria**

---

## Risk Assessment

### High Risk (P0 - Mitigation Required)

#### R1: Z3 Solver Complexity
- **Risk**: Z3 API steep learning curve, may be overkill for simple constraints
- **Impact**: Delays in constraint propagation implementation
- **Likelihood**: Medium (30%)
- **Mitigation**:
  - Prototype Z3 in Week 1 before committing
  - Fallback to python-constraint if Z3 too complex
  - Hire Z3 expert for 2-day consultation if stuck
- **Contingency**: Use simple rule-based validation for Phase 2, defer Z3 to Phase 3

#### R2: AI Chat Cost Overrun
- **Risk**: Claude API costs exceed budget ($100/month → $500/month)
- **Impact**: Budget impact, need to switch providers or limit usage
- **Likelihood**: Medium (40%)
- **Mitigation**:
  - Aggressive caching (1-hour TTL)
  - Use cheaper Claude 3 Haiku for simple commands
  - Rate limit: 10 chats/user/day
  - Monitor costs weekly, alert at $50 threshold
- **Contingency**: Switch to OpenAI GPT-4 Turbo ($10/M tokens) or GPT-3.5-turbo ($0.50/M tokens)

#### R3: Backend Performance Under Load
- **Risk**: Modal cold starts cause >5s latency for first request
- **Impact**: Poor UX, users frustrated
- **Likelihood**: High (60%)
- **Mitigation**:
  - Health check ping every 5 minutes (keep warm)
  - Use Modal keep_warm parameter (min_containers=1)
  - Show "Backend warming up..." message on first request
  - Cache backend responses (1-hour TTL)
- **Contingency**: Migrate to dedicated server (Hetzner) if cold starts unacceptable

---

### Medium Risk (P1 - Monitor and Plan)

#### R4: Dependency Graph Performance
- **Risk**: 1000-hole graphs render too slowly (>10s)
- **Impact**: Users frustrated, can't visualize large specs
- **Likelihood**: Low (20%)
- **Mitigation**:
  - Lazy loading (viewport culling)
  - Pagination (100 nodes at a time)
  - Benchmark in STEP-15, optimize before deployment
- **Contingency**: Simplify graph (show only critical path, hide resolved holes)

#### R5: Constraint Propagation Logic Bugs
- **Risk**: Propagation incorrectly constrains holes, corrupts data
- **Impact**: User specifications invalid, trust loss
- **Likelihood**: Medium (30%)
- **Mitigation**:
  - Comprehensive unit tests (20+ tests)
  - E2E tests with manual verification
  - Undo/redo to recover from mistakes
  - Extensive logging for debugging
- **Contingency**: Disable propagation, fall back to manual constraint entry

#### R6: OpenAPI Type Generation Issues
- **Risk**: Generated TypeScript types don't match runtime
- **Impact**: Type errors, runtime crashes
- **Likelihood**: Low (15%)
- **Mitigation**:
  - Validate OpenAPI spec with linter
  - Integration tests verify types match runtime
  - Use Pydantic on backend for double validation
- **Contingency**: Manual type definitions if codegen problematic

---

### Low Risk (P2 - Accept and Monitor)

#### R7: Cytoscape Bundle Size
- **Risk**: Cytoscape adds 500KB to bundle, slows page load
- **Impact**: Slower initial load (acceptable if <3s)
- **Likelihood**: Low (10%)
- **Mitigation**:
  - Code-split Cytoscape into ICSView chunk (lazy load)
  - Only load when user opens dependency graph
  - Use tree-shaking to eliminate unused Cytoscape features
- **Contingency**: Switch to lighter library (vis.js ~200KB)

#### R8: AI Chat Hallucinations
- **Risk**: Claude generates incorrect suggestions
- **Impact**: Users apply bad advice, specs corrupted
- **Likelihood**: Medium (25%)
- **Mitigation**:
  - Show confidence score on suggestions
  - Require user confirmation before applying
  - Log all suggestions for review
  - Add "Report incorrect suggestion" button
- **Contingency**: Add disclaimer: "AI suggestions are experimental, always review before applying"

---

## Timeline & Resources

### 8-Week Timeline (Detailed)

**Week 1: Backend Enhancement**
- STEP-1: OpenAPI Spec (1 day)
- STEP-2: Relationship Extraction (2 days)
- STEP-3: Effects Detection (2 days)
- STEP-4: Assertions Detection (2 days)

**Week 2: Backend Deployment + Frontend Display**
- STEP-5: Modal Deployment (1 day)
- STEP-6: Enhanced NLP Display (2 days)
- Buffer: 2 days for fixes

**Week 3: Constraint Solver**
- STEP-7: Z3 Integration (3 days)
- STEP-8: Constraint Validation (2 days)

**Week 4: Constraint Propagation**
- STEP-9: Propagation Logic (3 days)
- STEP-10: Solution Space Calculation (2 days)

**Week 5: Hole Resolution UI + Dependency Graph**
- STEP-11: Resolution UI (2 days)
- STEP-12: Propagation Tests (2 days)
- STEP-13: Dependency Graph Component (3 days)

**Week 6: Graph Polish + AI Chat Backend**
- STEP-14: Critical Path (1 day)
- STEP-15: Graph Optimization (2 days)
- STEP-16: AI Chat Backend (2 days)

**Week 7: AI Chat Frontend + Integration**
- STEP-17: Chat UI (3 days)
- STEP-18: Chat Commands (3 days)
- STEP-19: Chat Performance (1 day)

**Week 8: Testing, Documentation, Deployment**
- STEP-20: Integration (2 days)
- STEP-21: Error Handling (2 days)
- STEP-22: Benchmarking (1 day)
- STEP-23: E2E Tests (3 days)
- STEP-24: Unit Tests (2 days)
- STEP-25: Bug Fixing (2 days)
- STEP-26: Documentation (2 days)
- STEP-27: Deployment (1 day)
- STEP-28: Sign-off (1 day)

**Total**: 56 work-days (8 weeks @ 7 days/week, 1 developer)

**Slack**: 2 weeks built into timeline (56 days planned, 56 days available)

---

### Resource Requirements

**Personnel**:
- 1 Full-stack Developer (Frontend + Backend + DevOps)
- Optional: 1 Z3 expert consultant (2 days, Week 3)

**Infrastructure**:
- Modal.com GPU (L40S): ~$50/month (development + production)
- Claude API: ~$50-100/month (beta testing, 100 users)
- Supabase: Free tier (sufficient for Phase 2)
- Vercel/Cloudflare: Free tier (frontend hosting)

**Budget**:
- Infrastructure: $100-150/month
- Consultant (optional): $1000 (2 days @ $500/day)
- **Total**: $1000-1500 one-time + $150/month recurring

---

## Dependencies & Prerequisites

### Prerequisites (Must Complete Before Phase 2)

1. ✅ **Phase 1 Complete** - All 46 acceptance criteria met
2. ✅ **Backend NLP Exists** - `lift_sys/nlp/pipeline.py` functional
3. ✅ **Frontend ICS Components** - SemanticEditor, SymbolsPanel, HoleInspector
4. ✅ **Zustand Store** - State management working
5. ✅ **Test Infrastructure** - Unit, Integration, E2E test suites
6. ✅ **Build Pipeline** - Frontend builds successfully

### External Dependencies

**Libraries**:
- `z3-solver` (Python) - Constraint solver
- `cytoscape` + `react-cytoscapejs` (npm) - Dependency graph
- `anthropic` (Python) - Claude API client
- `openapi-typescript` (npm) - Type generation
- `datamodel-code-generator` (Python) - Pydantic from OpenAPI

**Services**:
- Modal.com account with GPU access
- Anthropic API key (Claude)
- Supabase project (existing)

**Skills**:
- Z3 SMT solver (learning curve ~1 week)
- Cytoscape.js (learning curve ~2 days)
- Claude API (learning curve ~1 day)

---

## Beads Issues (To Be Created)

### High Priority Issues

**Backend Enhancement**:
- `bd create "Implement relationship extraction (spaCy dependencies)" -t feature -p P0`
- `bd create "Implement effects detection (pattern matching + DSPy)" -t feature -p P0`
- `bd create "Implement assertions detection (pattern matching)" -t feature -p P0`
- `bd create "Deploy backend to Modal.com production" -t deployment -p P0`

**Constraint Propagation**:
- `bd create "Integrate Z3 constraint solver" -t feature -p P0`
- `bd create "Implement constraint validation in store" -t feature -p P0`
- `bd create "Implement constraint propagation logic (BFS)" -t feature -p P0`
- `bd create "Calculate solution space reduction" -t feature -p P0`
- `bd create "Implement hole resolution UI" -t feature -p P0`

**Dependency Graph**:
- `bd create "Create Cytoscape.js dependency graph component" -t feature -p P0`
- `bd create "Implement critical path highlighting" -t feature -p P1`
- `bd create "Optimize graph rendering for 1000+ holes" -t feature -p P1`

**AI Chat**:
- `bd create "Integrate Claude API for AI chat" -t feature -p P0`
- `bd create "Implement chat UI with message history" -t feature -p P0`
- `bd create "Implement /refine, /analyze, /suggest, /clarify commands" -t feature -p P0`
- `bd create "Add caching and performance optimization for AI chat" -t feature -p P1`

**Quality & Testing**:
- `bd create "Write 30 E2E tests for Phase 2 features" -t test -p P0`
- `bd create "Fix 17 non-ICS test failures from Phase 1" -t bug -p P1`
- `bd create "Add React ErrorBoundary components" -t feature -p P1`
- `bd create "Create OpenAPI v2 spec and generate types" -t feature -p P0`

**Documentation**:
- `bd create "Update ICS spec to v2 (Phase 2 features)" -t docs -p P1`
- `bd create "Write Phase 2 completion report" -t docs -p P1`
- `bd create "Generate API documentation from OpenAPI spec" -t docs -p P2`

**Total Beads Issues**: ~25 issues

---

## Success Criteria Summary

**Phase 2 is COMPLETE when**:

1. ✅ All 60 acceptance criteria pass (CP1-CP15, DG1-DG10, AI1-AI15, BE1-BE10, CQ1-CQ10)
2. ✅ All 52 E2E tests pass (22 from Phase 1 + 30 from Phase 2)
3. ✅ Unit test coverage >90% for Phase 2 code
4. ✅ Backend deployed to Modal.com production
5. ✅ Constraint propagation works correctly (validated by E2E tests)
6. ✅ Dependency graph renders 100 holes in <1s, 1000 holes in <5s
7. ✅ AI chat responds in <3s for simple queries, <10s for complex
8. ✅ All Phase 2 features documented in ICS spec v2
9. ✅ Phase 2 completion report written and reviewed
10. ✅ Production deployment successful, all features working

**Target Date**: 8 weeks from Phase 2 start (2025-12-21 if starting 2025-10-26)

---

## Next Steps (Immediate Actions)

1. **Review this document** - Stakeholder approval
2. **Create Beads issues** - 25 issues from plan above
3. **Set up dependencies** - `bd dep add` to create dependency graph
4. **STEP-1 kickoff** - Create OpenAPI spec (Week 1, Day 1)
5. **Weekly standups** - Track progress against 8-week timeline
6. **Risk monitoring** - Weekly review of top 3 risks

---

## Appendix: Phase Comparison

| Metric | Phase 1 | Phase 2 (Planned) | Change |
|--------|---------|-------------------|--------|
| **Timeline** | 4 weeks | 8 weeks | +100% |
| **STEPs** | 32 | 28 | -12% |
| **Features** | 10 | 4 core + 3 backend | Fewer, larger features |
| **Acceptance Criteria** | 46 | 60 | +30% |
| **E2E Tests** | 22 | 52 (22+30) | +136% |
| **Complexity** | Medium | High | Constraint solving, AI |
| **External APIs** | 0 | 2 (Modal, Claude) | New integrations |
| **Budget** | $0 | $150/month + $1000 one-time | Infrastructure costs |

**Key Difference**: Phase 2 focuses on **intelligence** (constraint solving, AI) vs Phase 1's **interface** (editor, display).

---

**Document Status**: ✅ **READY FOR REVIEW**
**Author**: Claude
**Review Date**: 2025-10-26
**Approval Status**: ⏳ Pending stakeholder approval
**Next Document**: Phase 2 Completion Report (after 8 weeks)

---

**End of Phase 2 Planning Document**
