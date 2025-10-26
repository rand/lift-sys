# ICS Implementation - Resume Guide

**Date**: 2025-10-26
**Status**: Ready to begin Phase 1 implementation
**Branch**: main (just merged feature/phase2-ics-nlp)

## Context: What Just Happened

### Merge Complete ✅

Just merged `feature/phase2-ics-nlp` to main with:
- **Robustness improvements**: 29.4% → 50% pass rate
  - Effect ordering: 0% → 100% robustness
  - Stylistic paraphrases: 100% robustness
  - AST-based semantic equivalence
  - Semantic filtering with sentence embeddings
- **DoWhy causal analysis integration**: Complete with comprehensive tests
- **Modal cost optimization**: Dev/demo modes implemented
- **NLP relationship extraction**: Enhanced capabilities

**Documentation**: See `docs/fixes/ROBUSTNESS_TEST_IMPROVEMENTS_20251026.md` for details.

---

## ICS Implementation Overview

### What is ICS?

**Integrated Context Studio** - Interactive specification editor with real-time semantic analysis. This is the PRIMARY user interface for lift-sys (not just a diagnostic tool).

### Goal

**Phase 1 MVP**: 22/22 E2E tests passing in 8-10 days

### Current Status

- ✅ **Phase 4**: Artifacts complete (specs, execution plan, 32 atomic steps)
- 🎯 **Phase 1**: Ready to begin implementation
- ❌ **Blockers**:
  - H2: DecorationApplication bug (9 tests failing)
  - H5: Autocomplete popup implementation

---

## First 3 Steps (Starting Point)

### STEP-01: Backend Test Validation (1 hour) ⚡

**Issue**: `lift-sys-308`
**Status**: Open (P3)
**Dependencies**: None
**Can start**: Immediately

**Tasks**:
1. Start backend: `uv run uvicorn lift_sys.api.server:app --reload`
2. Test health endpoint: `curl http://localhost:8000/ics/health`
3. Test analyze endpoint with sample text
4. Verify response matches `SemanticAnalysis` type
5. Document backend status

**Acceptance**: Backend returns valid `SemanticAnalysis` OR documented as unavailable

**Files**: Backend API server, NLP pipeline

---

### STEP-02: Mock Analysis Validation (3 hours) 🔧

**Issue**: `lift-sys-309`
**Status**: Open (P2)
**Dependencies**: None (parallel with STEP-01)
**Can start**: Immediately

**Tasks**:
1. Review `frontend/src/lib/ics/mockSemanticAnalysis.ts`
2. Write 10 unit tests for mock analysis:
   - Entity detection from patterns
   - Modal operator detection
   - Typed hole detection (??? syntax)
   - Ambiguity detection (probabilistic)
   - Empty text handling
3. Verify mock returns correct structure
4. Verify positions (from/to) are accurate

**Acceptance**: 10 unit tests passing, mock generates entities/modals/holes correctly

**Files**:
- `frontend/src/lib/ics/mockSemanticAnalysis.ts`
- `frontend/src/lib/ics/mockSemanticAnalysis.test.ts` (create)

---

### STEP-03: Fix H2 (DecorationApplication) - CRITICAL (6 hours) 🚨

**Issue**: `lift-sys-310`
**Status**: Open (P1)
**Dependencies**: STEP-01 (backend status known), STEP-02 (mock works)
**Can start**: After STEP-01 and STEP-02 complete

**Why Critical**: Blocks 9 failing tests and 9 downstream steps

**Implementation**:

1. **Update `SemanticEditor.tsx`**:
   ```typescript
   useEffect(() => {
     if (editorView && semanticAnalysis) {
       const tr = editorView.state.tr;
       tr.setMeta('semanticAnalysis', semanticAnalysis);
       editorView.dispatch(tr);
     }
   }, [editorView, semanticAnalysis]);
   ```

2. **Update `decorations.ts`**:
   ```typescript
   createDecorationsPlugin() {
     return new Plugin({
       state: {
         init(_, state) {
           // Initialize with empty DecorationSet
         },
         apply(tr, decorationSet, oldState, newState) {
           // Read semantic analysis from transaction
           const analysis = tr.getMeta('semanticAnalysis');

           if (analysis) {
             // Create new decorations from analysis
             const decorations = [
               ...createEntityDecorations(analysis.entities),
               ...createModalDecorations(analysis.modals),
               ...createHoleDecorations(analysis.holes),
               ...createConstraintDecorations(analysis.constraints)
             ];
             return DecorationSet.create(newState.doc, decorations);
           }

           // Map old decorations on document changes
           return decorationSet.map(tr.mapping, newState.doc);
         }
       },
       props: {
         decorations(state) { return this.getState(state); }
       }
     });
   }
   ```

3. **Test decoration application**:
   - Manually type text, verify highlights appear
   - Check DOM for `.entity`, `.modal`, `.hole`, `.constraint` classes
   - Verify data attributes (`data-entity-id`, etc.)

**Acceptance**:
- Highlights appear in editor after typing
- DOM contains semantic CSS classes
- 9 failing tests now pass (entities, modals, holes, constraints, tooltips)

**Files**:
- `frontend/src/components/ics/SemanticEditor.tsx`
- `frontend/src/lib/ics/decorations.ts`

---

## Recommended Workflow

### Parallel Track (Start Together)

**Day 1 Morning**:
```bash
# Track A: Backend validation (1 hour)
cd /Users/rand/src/lift-sys
uv run uvicorn lift_sys.api.server:app --reload &
# Test endpoints, document status
bd update lift-sys-308 --status in_progress

# Track B: Mock validation (3 hours)
cd frontend
npm test -- mockSemanticAnalysis.test.ts --watch
# Write tests, verify mock behavior
bd update lift-sys-309 --status in_progress
```

**Day 1 Afternoon**:
```bash
# Close STEP-01 and STEP-02
bd close lift-sys-308 --reason "Backend validated"
bd close lift-sys-309 --reason "Mock tests passing"

# Start STEP-03 (critical blocker)
bd update lift-sys-310 --status in_progress
# Implement decoration fix (6 hours)
```

**Day 2**:
```bash
# Finish STEP-03
# Verify 9 tests now pass
bd close lift-sys-310 --reason "Decorations working, tests passing"

# Continue with STEP-04 and beyond
```

---

## Development Environment Setup

### Backend (Terminal 1)

```bash
cd /Users/rand/src/lift-sys
uv run uvicorn lift_sys.api.server:app --reload --port 8000
```

**Endpoints**:
- Health: `http://localhost:8000/ics/health`
- Analyze: `http://localhost:8000/ics/analyze`

### Frontend (Terminal 2)

```bash
cd /Users/rand/src/lift-sys/frontend
npm run dev
```

**App**: `http://localhost:5173`

### Tests (Terminal 3)

```bash
cd /Users/rand/src/lift-sys/frontend
npm test -- --watch
```

---

## Key Files to Review Before Starting

### Specifications (Read First)

1. **`specs/ics-master-spec.md`** - Complete ICS specification (2,000+ lines)
2. **`plans/ics-execution-plan.md`** - 32 atomic steps with dependencies
3. **`docs/planning/SESSION_BOOTSTRAP.md`** - 5-minute quick start (if available)

### Frontend Code (Current State)

1. **`frontend/src/components/ics/SemanticEditor.tsx`** - Main editor component
2. **`frontend/src/lib/ics/decorations.ts`** - Decoration plugin (needs fix)
3. **`frontend/src/lib/ics/mockSemanticAnalysis.ts`** - Mock fallback
4. **`frontend/src/lib/ics/store.ts`** - Zustand state management

### Backend Code (Current State)

1. **`lift_sys/api/endpoints/ics.py`** - ICS API endpoints
2. **`lift_sys/nlp/pipeline.py`** - NLP pipeline
3. **`lift_sys/nlp/relationship_extractor.py`** - Relationship extraction (just merged)

---

## Success Criteria (Phase 1 MVP)

### Behavioral Completeness (BC)

- [ ] BC1: All components render without errors
- [ ] BC2: No console errors during normal operation
- [ ] BC3: All components follow state machines (idle, loading, success, error)
- [ ] BC4: Empty states shown when appropriate
- [ ] BC5: Error states shown and recoverable
- [ ] BC6: Loading states shown during async operations

### User Experience (UX)

- [ ] UX1: 300ms debounce on typing → analysis
- [ ] UX2: Keyboard navigation works (Tab, Arrow keys, Escape)
- [ ] UX3: Focus management correct (modal → editor)
- [ ] UX4: Visual feedback for all user actions

### Functional (F)

- [ ] F1: Semantic highlights appear in editor
- [ ] F2: Tooltips show on hover
- [ ] F3: Symbols panel shows entities
- [ ] F4: Click entity → editor jumps to position
- [ ] F5: Holes clickable → inspector panel
- [ ] F6: Autocomplete popup works (H5)

### E2E Tests

- [ ] 22/22 E2E tests passing (see `frontend/playwright/ics.spec.ts`)

---

## Beads Workflow During ICS Implementation

### Starting a Task

```bash
bd update lift-sys-308 --status in_progress --json
# Work on task
```

### Completing a Task

```bash
bd close lift-sys-308 --reason "Backend endpoints validated, returning correct types" --json
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -m "beads: Complete lift-sys-308 (ICS STEP-01)"
```

### Discovering New Work

```bash
bd create "Fix TypeScript error in decorations.ts" \
  -t bug -p P1 --label ics-implementation --json
bd dep add lift-sys-310 <new-id> --type blocks
```

### Checking Progress

```bash
# See all ICS work
bd list --json | jq '[.[] | select(.title | contains("ICS"))]'

# See ready work
bd ready --json --limit 10

# See specific step
bd show lift-sys-310
```

---

## Common Issues & Solutions

### Issue: Backend not starting

**Symptom**: `uvicorn` command fails
**Solution**:
```bash
cd /Users/rand/src/lift-sys
uv sync  # Reinstall dependencies
uv run uvicorn lift_sys.api.server:app --reload
```

### Issue: Frontend tests failing

**Symptom**: Mock tests don't pass
**Solution**:
```bash
cd frontend
npm install  # Update dependencies
npm test -- mockSemanticAnalysis.test.ts --run
```

### Issue: Decorations not appearing

**Symptom**: Text typed but no highlights
**Solution**:
1. Check browser console for errors
2. Verify `semanticAnalysis` prop passed to `SemanticEditor`
3. Verify `useEffect` dispatching transaction
4. Verify plugin reading `tr.getMeta('semanticAnalysis')`
5. Check CSS classes in DOM inspector

### Issue: Cannot find ICS specs

**Solution**:
```bash
ls specs/ics-master-spec.md
ls plans/ics-execution-plan.md
```

---

## Next Steps After STEP-03

Once H2 is fixed and 9 tests are passing, continue with:

1. **STEP-04**: Write Decorations Unit Tests (3 hours) - `lift-sys-311`
2. **STEP-05**: Write HoleInspector Unit Tests (3 hours) - `lift-sys-312`
3. **STEP-06**: Write API Client Integration Tests (4 hours) - `lift-sys-313`
4. **STEP-07**: Write Editor + Store Integration Tests (4 hours) - `lift-sys-314`
5. **STEP-08**: Update SemanticEditor for Optimization (3 hours) - `lift-sys-315`

See `plans/ics-execution-plan.md` for complete 32-step sequence.

---

## Timeline Estimate

| Phase | Days | Status |
|-------|------|--------|
| STEP-01, STEP-02 (parallel) | 0.5 | Ready to start |
| STEP-03 (H2 fix) | 1 | Critical blocker |
| STEP-04 to STEP-08 | 2.5 | After H2 fixed |
| STEP-09 (H5 autocomplete) | 1 | Second critical blocker |
| STEP-10 to STEP-22 | 3 | Unit tests, integration tests |
| STEP-23 to STEP-32 | 2 | E2E tests, polish |
| **Total** | **10 days** | MVP target |

---

## Reference Documents

### Planning & Specs
- `specs/ics-master-spec.md` - Complete ICS specification
- `plans/ics-execution-plan.md` - 32 atomic steps with dependencies
- `docs/planning/ICS_PHASE4_ARTIFACTS_COMPLETE.md` - Phase 4 summary

### Architecture
- `docs/PRDs and RFCs/RFC_LIFT_ARCHITECTURE.md` - Overall lift-sys architecture
- `docs/IR_SPECIFICATION.md` - IR design specification

### Current State
- `CURRENT_STATE.md` - Project status snapshot
- `docs/issues/BACKEND_STATUS.md` - Backend pipeline detailed status

### Recent Work
- `docs/fixes/ROBUSTNESS_TEST_IMPROVEMENTS_20251026.md` - Just completed
- `docs/causal/README.md` - DoWhy integration just merged

---

## Quick Start Commands

```bash
# 1. Start backend (Terminal 1)
cd /Users/rand/src/lift-sys
uv run uvicorn lift_sys.api.server:app --reload --port 8000

# 2. Start frontend (Terminal 2)
cd /Users/rand/src/lift-sys/frontend
npm run dev

# 3. Run tests (Terminal 3)
cd /Users/rand/src/lift-sys/frontend
npm test -- --watch

# 4. Claim first task
bd update lift-sys-308 --status in_progress
```

---

**Ready to begin ICS Phase 1 implementation!** 🚀

Start with STEP-01 (backend validation) and STEP-02 (mock validation) in parallel, then tackle STEP-03 (H2 critical blocker).
