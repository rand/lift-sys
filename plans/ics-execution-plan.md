# ICS Execution Plan

**Version**: 1.0
**Date**: 2025-10-25
**Status**: Phase 3 - Execution Plan
**Parent**: Phase 2 specifications (7 files, 5,902 lines)

---

## Document Purpose

This execution plan breaks down the complete ICS implementation into atomic, executable steps with:
- Clear dependencies (what must complete before each step)
- Complexity estimates (S/M/L/XL)
- Risk levels (Low/Medium/High)
- Parallelization opportunities
- Critical path identification
- Sequencing for optimal execution

**Goal**: Enable systematic, resumable implementation across multiple sessions.

---

## Table of Contents

1. [Execution Overview](#1-execution-overview)
2. [Critical Path](#2-critical-path)
3. [Implementation Steps](#3-implementation-steps)
4. [Parallelization Zones](#4-parallelization-zones)
5. [Risk Mitigation](#5-risk-mitigation)
6. [Sequencing](#6-sequencing)

---

## 1. Execution Overview

### 1.1 Summary

**Total Steps**: 32
**Estimated Duration**: 2-3 weeks (Phase 1 MVP)
**Critical Path**: 8 steps (H2 → Tests → Validation)

**By Complexity**:
- S (Small): 12 steps (< 2 hours each)
- M (Medium): 14 steps (2-4 hours each)
- L (Large): 5 steps (4-8 hours each)
- XL (Extra Large): 1 step (8+ hours)

**By Risk**:
- Low: 18 steps
- Medium: 12 steps
- High: 2 steps

**Parallelization**:
- 4 parallel zones (8 steps can run concurrently)
- 24 sequential steps (dependencies)

### 1.2 Phase Breakdown

**Phase 1 (MVP)**: 22 steps, 2 weeks
- Fix critical blockers (H2, H5)
- Complete unit tests
- Get 22/22 E2E tests passing
- Performance validation

**Phase 2 (Advanced)**: 10 steps, 1 week
- Implement hole dependency graph
- Implement constraint propagation
- Add AI assistant integration

---

## 2. Critical Path

**Definition**: Minimum steps required to get MVP working (22/22 tests passing).

```
CRITICAL PATH (8 steps, ~40 hours):

STEP-03: Fix H2 (DecorationApplication)         [L, High, 6h]
   ↓
STEP-08: Update SemanticEditor                    [M, Medium, 3h]
   ↓
STEP-09: Fix autocomplete popup (H5)              [M, Medium, 3h]
   ↓
STEP-15: Run full E2E suite                       [S, Low, 1h]
   ↓
STEP-16: Debug failing tests                      [L, Medium, 6h]
   ↓
STEP-17: Verify 22/22 passing                     [S, Low, 1h]
   ↓
STEP-29: Performance validation                   [M, Medium, 4h]
   ↓
STEP-32: Phase 1 completion verification          [M, Low, 2h]
```

**Total Critical Path**: ~26 hours (3-4 days)

**Blockers**:
- STEP-03 blocks STEP-08, STEP-15, STEP-16 (9 failing tests depend on H2)
- STEP-09 blocks STEP-15 (1 failing test depends on H5)

---

## 3. Implementation Steps

### ZONE 1: Critical Fixes (Sequential)

#### STEP-01: Backend Test Validation
**Goal**: Verify backend NLP pipeline works before blaming frontend

**Tasks**:
- Start backend: `uv run uvicorn lift_sys.api.server:app --reload`
- Test health endpoint: `curl http://localhost:8000/ics/health`
- Test analyze endpoint with sample text
- Verify response matches SemanticAnalysis type
- Document backend status

**Dependencies**: None
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Backend status report (pass/fail)
**Acceptance**: Backend returns valid SemanticAnalysis OR documented as unavailable

---

#### STEP-02: Mock Analysis Validation
**Goal**: Verify mock fallback works correctly

**Tasks**:
- Review `frontend/src/lib/ics/mockSemanticAnalysis.ts`
- Write unit tests for mock analysis (10 tests)
  - Entity detection from patterns
  - Modal operator detection
  - Typed hole detection (??? syntax)
  - Ambiguity detection (probabilistic)
  - Empty text handling
- Verify mock returns correct structure
- Verify positions (from/to) are accurate

**Dependencies**: None (parallel with STEP-01)
**Complexity**: M (3 hours)
**Risk**: Low
**Deliverable**: 10 unit tests passing
**Acceptance**: Mock generates entities, modals, holes correctly

---

#### STEP-03: Fix H2 (DecorationApplication) 🔴 CRITICAL
**Goal**: Fix decoration application to unblock 9 failing tests

**Tasks**:
1. Update `SemanticEditor.tsx`:
   ```typescript
   useEffect(() => {
     if (!editorView || !semanticAnalysis) return;

     const tr = editorView.state.tr;
     tr.setMeta('semanticAnalysis', semanticAnalysis);
     editorView.dispatch(tr);
   }, [editorView, semanticAnalysis]);
   ```

2. Update `decorations.ts`:
   - Modify `createDecorationsPlugin()` to read transaction metadata
   - Create decorations from `tr.getMeta('semanticAnalysis')`
   - Map old decorations on document changes
   - Return DecorationSet with all semantic highlights

3. Test decoration application:
   - Manually type text, verify highlights appear
   - Check DOM for `.entity`, `.modal`, `.hole`, `.constraint` classes
   - Verify data attributes (`data-entity-id`, etc.)

**Dependencies**: STEP-01 (backend status known), STEP-02 (mock works)
**Complexity**: L (6 hours)
**Risk**: High (critical blocker, complex ProseMirror integration)
**Deliverable**: Decorations apply when analysis updates
**Acceptance**:
- Highlights appear in editor after typing
- DOM contains semantic CSS classes
- 9 failing tests now pass (entities, modals, holes, constraints, tooltips)

---

#### STEP-04: Write Decorations Unit Tests
**Goal**: Ensure decorations creation is well-tested

**Tasks**:
- Test `createEntityDecoration()`
- Test `createModalDecoration()`
- Test `createConstraintDecoration()`
- Test `createAmbiguityDecoration()`
- Test `createHoleWidget()`
- Test decoration positioning (from/to accuracy)
- Test data attribute inclusion

**Dependencies**: STEP-03 (decorations working)
**Complexity**: M (3 hours)
**Risk**: Low
**Deliverable**: 10 unit tests for decorations
**Acceptance**: 10/10 tests passing, 85% coverage of decorations.ts

---

#### STEP-05: Write Store Unit Tests
**Goal**: Test Zustand store actions

**Tasks**:
- Test `setSemanticAnalysis()`
- Test `resolveHole()`
- Test `propagateConstraints()` (Phase 1 stub)
- Test `addHole()`, `updateHole()`, `removeHole()`
- Test `addConstraint()`, `updateConstraint()`, `removeConstraint()`
- Test `setLayout()`, `togglePanel()`
- Test persistence (localStorage)

**Dependencies**: None (parallel with STEP-04)
**Complexity**: M (3 hours)
**Risk**: Low
**Deliverable**: 10 unit tests for store
**Acceptance**: 10/10 tests passing, 80% coverage of store.ts

---

#### STEP-06: Write API Client Integration Tests
**Goal**: Test API client + mock fallback integration

**Tasks**:
- Use MSW to mock backend
- Test backend available → uses NLP analysis
- Test backend unavailable → uses mock
- Test backend timeout → falls back to mock
- Test error handling → graceful degradation
- Test health check

**Dependencies**: STEP-01 (backend behavior known), STEP-02 (mock works)
**Complexity**: M (3 hours)
**Risk**: Medium (MSW setup complexity)
**Deliverable**: 5 integration tests
**Acceptance**: 5/5 tests passing, backend/mock fallback verified

---

#### STEP-07: Write Editor + Store Integration Tests
**Goal**: Test SemanticEditor + Zustand integration

**Tasks**:
- Test typing updates store (`specificationText`)
- Test analysis update triggers decorations
- Test debounce behavior (500ms)
- Test empty text handling
- Test long text handling

**Dependencies**: STEP-03 (decorations working), STEP-05 (store tested)
**Complexity**: M (4 hours)
**Risk**: Medium (React Testing Library + ProseMirror complexity)
**Deliverable**: 5 integration tests
**Acceptance**: 5/5 tests passing, editor ↔ store integration verified

---

#### STEP-08: Update SemanticEditor for Optimization
**Goal**: Optimize editor state sync (H1 improvement)

**Tasks**:
- Review current `onEditorChange` implementation
- Optimize text extraction (avoid unnecessary updates)
- Add transaction batching for performance
- Prevent circular updates (editor → store → editor)
- Add performance timing logs

**Dependencies**: STEP-03 (H2 fixed)
**Complexity**: M (3 hours)
**Risk**: Medium (performance optimization trade-offs)
**Deliverable**: Optimized editor state sync
**Acceptance**:
- No circular updates
- Text extraction < 16ms
- Character count updates in real-time

---

### ZONE 2: Autocomplete & Tooltips (Sequential after STEP-03)

#### STEP-09: Fix Autocomplete Popup (H5) 🔴 CRITICAL
**Goal**: Fix autocomplete popup appearance (blocks 1 test)

**Tasks**:
- Review `AutocompletePopup.tsx` rendering
- Debug why `.autocomplete-popup` not appearing in DOM
- Check CSS positioning (below cursor)
- Verify popup mounts to document body
- Test keyboard navigation (↓↑ Enter Escape)
- Test results filtering

**Dependencies**: STEP-03 (decorations fixed, editor stable)
**Complexity**: M (3 hours)
**Risk**: Medium (CSS/positioning issues)
**Deliverable**: Autocomplete popup visible in tests
**Acceptance**:
- `.autocomplete-popup` appears in DOM
- Results filter as user types
- Keyboard navigation works
- 1 failing test now passes

---

#### STEP-10: Write Autocomplete Unit Tests
**Goal**: Test autocomplete logic

**Tasks**:
- Test file search (# trigger)
- Test symbol search (@ trigger)
- Test fuzzy filtering
- Test result sorting
- Test keyboard navigation state

**Dependencies**: STEP-09 (autocomplete working)
**Complexity**: S (2 hours)
**Risk**: Low
**Deliverable**: 5 unit tests
**Acceptance**: 5/5 tests passing, autocomplete logic covered

---

#### STEP-11: Fix Tooltip Positioning (H11)
**Goal**: Ensure tooltips appear correctly on hover

**Tasks**:
- Implement `calculateTooltipPosition()`
- Handle viewport clipping (show above if no room below)
- Test 300ms hover delay
- Test immediate hide on mouse out
- Test tooltip content for each element type (entity, modal, hole, constraint)

**Dependencies**: STEP-03 (semantic elements exist to hover)
**Complexity**: M (2 hours)
**Risk**: Low (blocked by H2, now unblocked)
**Deliverable**: Tooltips appear on hover
**Acceptance**:
- 4 tooltip tests pass
- Tooltips position correctly
- Content matches element type

---

### ZONE 3: Testing & Validation (Sequential after STEP-09, STEP-11)

#### STEP-12: Run Unit Test Suite
**Goal**: Verify all unit tests pass

**Tasks**:
- Run `npm run test` (all unit tests)
- Review coverage report
- Fix any failing tests
- Document coverage metrics

**Dependencies**: STEP-02, STEP-04, STEP-05, STEP-10
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Unit test results
**Acceptance**:
- 50/50 unit tests passing (target)
- 80% coverage achieved

---

#### STEP-13: Run Integration Test Suite
**Goal**: Verify all integration tests pass

**Tasks**:
- Run `npm run test:integration`
- Review results
- Fix any integration failures
- Document integration coverage

**Dependencies**: STEP-06, STEP-07
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Integration test results
**Acceptance**:
- 20/20 integration tests passing (target)
- 70% coverage achieved

---

#### STEP-14: Pre-E2E Preparation
**Goal**: Ensure environment ready for E2E tests

**Tasks**:
- Build frontend: `npm run build`
- Start dev server: `npm run dev`
- Verify app loads without errors
- Clear Playwright cache
- Regenerate auth state if needed

**Dependencies**: STEP-03, STEP-09, STEP-11 (all fixes complete)
**Complexity**: S (30 min)
**Risk**: Low
**Deliverable**: Dev server running
**Acceptance**:
- Frontend builds successfully
- Dev server running at http://localhost:5173
- No console errors

---

#### STEP-15: Run Full E2E Suite 🔴 CRITICAL
**Goal**: Execute all 22 Playwright tests

**Tasks**:
- Run `npm run test:e2e`
- Capture test results
- Identify any remaining failures
- Save screenshots/videos of failures

**Dependencies**: STEP-14 (environment ready)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: E2E test results
**Acceptance**:
- Test suite completes without crashes
- Results documented (pass/fail count)

---

#### STEP-16: Debug Failing E2E Tests 🔴 CRITICAL
**Goal**: Fix any remaining E2E failures

**Tasks**:
- Analyze failure screenshots/videos
- Debug specific failing tests
- Fix issues (could be timing, selectors, logic)
- Re-run failed tests
- Repeat until all pass

**Dependencies**: STEP-15 (test results available)
**Complexity**: L (6 hours - assumes 0-2 remaining failures)
**Risk**: Medium (unknown issues may arise)
**Deliverable**: All E2E tests passing
**Acceptance**:
- 22/22 E2E tests passing
- No flaky tests

---

#### STEP-17: Verify 22/22 E2E Tests Passing 🔴 CRITICAL
**Goal**: Confirm Phase 1 E2E acceptance criteria met

**Tasks**:
- Run E2E suite 3 times (ensure not flaky)
- Verify all 22 tests pass each time
- Document final test status
- Save passing test report

**Dependencies**: STEP-16 (all tests fixed)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: E2E test report (3 runs, 100% pass rate)
**Acceptance**:
- 22/22 tests pass in all 3 runs
- No flaky tests detected

---

### ZONE 4: Code Quality & Validation (Parallel with ZONE 3)

#### STEP-18: Type Checking
**Goal**: Verify TypeScript strict mode compliance

**Tasks**:
- Run `npm run type-check`
- Fix any type errors
- Verify no `any` types (exceptions allowed in tests)
- Document type coverage

**Dependencies**: STEP-03, STEP-08, STEP-09 (code changes complete)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Zero type errors
**Acceptance**:
- `npm run type-check` passes
- No `any` types in production code (TC2)

---

#### STEP-19: Linting
**Goal**: Verify code quality standards

**Tasks**:
- Run `npm run lint`
- Fix any linting errors
- Review and fix any warnings
- Document code quality metrics

**Dependencies**: STEP-03, STEP-08, STEP-09 (code changes complete)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Zero lint errors
**Acceptance**:
- `npm run lint` passes
- All warnings addressed or documented

---

#### STEP-20: Build Verification
**Goal**: Ensure production build succeeds

**Tasks**:
- Run `npm run build`
- Verify build output
- Check bundle sizes
- Test production build locally

**Dependencies**: STEP-18, STEP-19 (code quality verified)
**Complexity**: S (30 min)
**Risk**: Low
**Deliverable**: Production build
**Acceptance**:
- `npm run build` succeeds
- No build errors or warnings
- Bundle size reasonable (< 500KB per chunk)

---

#### STEP-21: Browser Console Check
**Goal**: Verify no runtime errors

**Tasks**:
- Load app in browser
- Navigate through all ICS features
- Check console for errors
- Test all user workflows
- Document any console warnings

**Dependencies**: STEP-14 (dev server running)
**Complexity**: M (2 hours)
**Risk**: Low
**Deliverable**: Console log report
**Acceptance**:
- Zero console errors during normal operation (BC2)
- Warnings documented and acceptable

---

### ZONE 5: Performance & Validation (Sequential after STEP-17)

#### STEP-22: Manual OODA Loop Timing
**Goal**: Verify OODA cycle performance constraints

**Tasks**:
- Measure Semantic Analysis OODA loop:
  - Typing → Debounce → Analysis → Highlights visible
  - Target: < 2s
- Measure Hole Inspection OODA loop:
  - Click hole → Inspector open → Read → Decide → Act
  - Target: < 10s
- Measure Autocomplete OODA loop:
  - Trigger → Results → Select → Insert
  - Target: < 1s
- Document timings with Chrome DevTools Performance

**Dependencies**: STEP-17 (all tests passing)
**Complexity**: M (3 hours)
**Risk**: Low
**Deliverable**: Performance timing report
**Acceptance**:
- Semantic Analysis < 2s (PC1)
- Hole Inspection < 10s
- Autocomplete < 1s

---

#### STEP-23: Keystroke Latency Test
**Goal**: Verify editor responsiveness

**Tasks**:
- Measure keystroke latency with Chrome DevTools
- Test typing in editor (rapid input)
- Verify < 16ms response time
- Test with long documents (1000+ chars)

**Dependencies**: STEP-17 (all tests passing)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Keystroke latency measurements
**Acceptance**:
- Keystroke latency < 16ms (PC2, 60 FPS)
- No lag during typing

---

#### STEP-24: Store Update Performance
**Goal**: Verify store operations are fast

**Tasks**:
- Add performance timing to store actions
- Measure `setSemanticAnalysis()` time
- Measure `resolveHole()` time
- Measure `propagateConstraints()` time
- Verify all < 16ms

**Dependencies**: STEP-05 (store tested)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Store performance report
**Acceptance**:
- All store updates < 16ms (PC3)

---

#### STEP-25: Decoration Calculation Performance
**Goal**: Verify decoration creation is fast

**Tasks**:
- Add timing to `createDecorationsPlugin`
- Measure with 100 entities
- Measure with 50 modals + 50 constraints
- Verify < 100ms

**Dependencies**: STEP-03 (decorations working)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Decoration performance report
**Acceptance**:
- Decoration calculation < 100ms (PC4)
- Scales to 100+ elements

---

#### STEP-26: API Timeout Test
**Goal**: Verify backend timeout and fallback

**Tasks**:
- Mock slow backend (> 5s response)
- Verify timeout triggers
- Verify fallback to mock
- Verify toast notification shown
- Test user not blocked

**Dependencies**: STEP-06 (API client tested)
**Complexity**: S (1 hour)
**Risk**: Low
**Deliverable**: Timeout test report
**Acceptance**:
- 5s timeout works (PC5)
- Fallback to mock (BC1)
- User sees notification

---

#### STEP-27: State Machine Compliance Check
**Goal**: Verify all components follow state machines

**Tasks**:
- Review SemanticEditor states (idle, typing, analyzing, success, error)
- Review SymbolsPanel states (empty, loading, populated)
- Review HoleInspector states (empty, loading, populated, resolving)
- Verify transitions match specifications
- Test error states
- Test empty states
- Test loading states

**Dependencies**: STEP-17 (all features working)
**Complexity**: M (2 hours)
**Risk**: Low
**Deliverable**: State machine compliance report
**Acceptance**:
- All components follow state machines (BC3)
- All empty states shown (BC4)
- All error states shown (BC5)
- All loading states shown (BC6)

---

#### STEP-28: Accessibility Quick Check
**Goal**: Basic WCAG 2.1 AA check (full audit in Phase 2)

**Tasks**:
- Test keyboard navigation
- Verify focus indicators visible
- Check color contrast (text > 4.5:1)
- Test with screen reader (basic)
- Verify ARIA labels on icons

**Dependencies**: STEP-17 (all features working)
**Complexity**: M (2 hours)
**Risk**: Low
**Deliverable**: Accessibility checklist
**Acceptance**:
- All features keyboard accessible (UX2)
- Focus indicators visible
- Basic screen reader support

---

#### STEP-29: Performance Validation Summary 🔴 CRITICAL
**Goal**: Verify all performance constraints met

**Tasks**:
- Compile results from STEP-22 through STEP-26
- Create performance summary table
- Identify any constraint violations
- Document mitigations for violations
- Mark constraints as met/partial/failed

**Dependencies**: STEP-22, STEP-23, STEP-24, STEP-25, STEP-26
**Complexity**: M (2 hours)
**Risk**: Low
**Deliverable**: Performance validation report
**Acceptance**:
- All 8 performance constraints documented
- Critical constraints met (PC1-PC3)
- Any violations have mitigation plans

---

### ZONE 6: Documentation & Completion (Sequential after STEP-29)

#### STEP-30: Update Documentation
**Goal**: Document implementation status

**Tasks**:
- Update `typed-holes.md` with resolution status
- Update `constraints.md` with validation results
- Update `test-plan.md` with actual coverage
- Document any deviations from specs
- Add troubleshooting guide

**Dependencies**: STEP-29 (all validation complete)
**Complexity**: M (3 hours)
**Risk**: Low
**Deliverable**: Updated specs with actual results
**Acceptance**:
- All specs reflect implementation status
- Coverage actual vs target documented
- Known issues documented

---

#### STEP-31: Code Review Preparation
**Goal**: Prepare for code review

**Tasks**:
- Review all changed files
- Add comments where needed
- Document non-obvious decisions
- Clean up console.logs
- Remove dead code
- Format code

**Dependencies**: STEP-30 (docs updated)
**Complexity**: M (2 hours)
**Risk**: Low
**Deliverable**: Clean, reviewable code
**Acceptance**:
- Code formatted
- Comments added
- No debug code

---

#### STEP-32: Phase 1 Completion Verification 🔴 CRITICAL
**Goal**: Verify all Phase 1 acceptance criteria met

**Tasks**:
- Review Phase 1 acceptance criteria (ics-spec-v1.md §8)
- Verify functional requirements (FR1-FR14)
- Verify state handling requirements (SH1-SH9)
- Verify OODA loop requirements (OODA1-OODA5)
- Verify technical requirements (TECH1-TECH10)
- Verify code quality requirements (CQ1-CQ8)
- Create completion report

**Dependencies**: STEP-29, STEP-30, STEP-31 (all work complete)
**Complexity**: M (2 hours)
**Risk**: Low
**Deliverable**: Phase 1 completion report
**Acceptance**:
- All acceptance criteria met or documented exceptions
- Completion report signed off

---

## 4. Parallelization Zones

### Zone A: Initial Validation (Parallel)
**When**: After Phase 3 plan approved
**Steps**: STEP-01, STEP-02 (2 parallel)
**Duration**: ~3 hours total (max of individual durations)
**Goal**: Validate backend and mock independently

---

### Zone B: Unit Testing (Parallel)
**When**: After STEP-03 (H2 fixed)
**Steps**: STEP-04, STEP-05 (2 parallel)
**Duration**: ~3 hours total
**Goal**: Unit test decorations and store simultaneously

---

### Zone C: Integration Testing (Parallel)
**When**: After STEP-05 (store tested), STEP-02 (mock validated)
**Steps**: STEP-06, STEP-07 (2 parallel)
**Duration**: ~4 hours total
**Goal**: Integration test API and editor simultaneously

---

### Zone D: Code Quality (Parallel with Testing)
**When**: After STEP-09 (all code changes done), during STEP-12-STEP-17
**Steps**: STEP-18, STEP-19, STEP-20 (3 parallel)
**Duration**: ~1 hour total
**Goal**: Run type checking, linting, build in parallel while E2E tests run

---

### Parallelization Summary
**Total Parallel Time Saved**: ~6 hours
- Zone A: 1 hour saved (3h instead of 4h)
- Zone B: 0 hours (both 3h)
- Zone C: 3 hours saved (4h instead of 7h)
- Zone D: 2 hours saved (1h instead of 2.5h)

---

## 5. Risk Mitigation

### High-Risk Steps

#### STEP-03: Fix H2 (DecorationApplication)
**Risk**: ProseMirror plugin complexity, critical blocker
**Mitigation**:
- Review ProseMirror docs thoroughly
- Test incrementally (small changes, test often)
- Have rollback plan (git commit before changes)
- Allocate extra time (6h + 2h buffer)
- Seek help if blocked after 4h

#### STEP-16: Debug Failing E2E Tests
**Risk**: Unknown issues may arise
**Mitigation**:
- Capture detailed screenshots/videos
- Use Playwright debug mode
- Test with headed browser to see what's happening
- Isolate failing tests
- Allocate buffer time (6h + 4h buffer)

---

### Medium-Risk Steps

#### STEP-06: API Client Integration Tests
**Risk**: MSW (Mock Service Worker) setup complexity
**Mitigation**:
- Review MSW docs
- Start with simple mock (health check)
- Build up to complex scenarios
- Have fallback (skip MSW, test with real backend)

#### STEP-07: Editor + Store Integration Tests
**Risk**: React Testing Library + ProseMirror interaction complexity
**Mitigation**:
- Review RTL best practices
- Test simple interactions first
- Use `screen.debug()` liberally
- Have fallback (manual testing if automated fails)

#### STEP-08: Optimize Editor State Sync
**Risk**: Performance optimization may introduce bugs
**Mitigation**:
- Profile before optimizing
- Change one thing at a time
- Test after each change
- Keep performance logs

#### STEP-09: Fix Autocomplete Popup
**Risk**: CSS/positioning issues can be tricky
**Mitigation**:
- Inspect DOM carefully (DevTools)
- Test positioning calculations with console.log
- Use fixed positioning as fallback
- Check z-index stacking

---

## 6. Sequencing

### Week 1: Critical Path (Days 1-5)

**Day 1** (8 hours):
- STEP-01: Backend validation (1h)
- STEP-02: Mock validation (3h) [parallel with STEP-01]
- STEP-03: Fix H2 (6h) [CRITICAL]

**Day 2** (8 hours):
- STEP-04: Decorations unit tests (3h)
- STEP-05: Store unit tests (3h) [parallel with STEP-04]
- STEP-06: API integration tests (3h, start in afternoon)

**Day 3** (8 hours):
- STEP-07: Editor integration tests (4h)
- STEP-08: Optimize editor sync (3h)
- STEP-09: Fix autocomplete (3h, start in afternoon) [CRITICAL]

**Day 4** (8 hours):
- STEP-10: Autocomplete unit tests (2h)
- STEP-11: Fix tooltips (2h)
- STEP-12: Run unit tests (1h)
- STEP-13: Run integration tests (1h)
- STEP-14: Pre-E2E prep (0.5h)
- STEP-15: Run E2E suite (1h) [CRITICAL]
- STEP-16: Debug E2E failures (BUFFER TIME) [CRITICAL]

**Day 5** (8 hours):
- STEP-16: Continue debugging E2E (if needed)
- STEP-17: Verify 22/22 passing (1h) [CRITICAL]
- STEP-18: Type checking (1h) [parallel with STEP-19, STEP-20]
- STEP-19: Linting (1h)
- STEP-20: Build verification (0.5h)
- STEP-21: Console check (2h)
- STEP-22: OODA loop timing (3h, start)

---

### Week 2: Validation & Polish (Days 6-10)

**Day 6** (8 hours):
- STEP-22: Complete OODA timing (1h)
- STEP-23: Keystroke latency (1h)
- STEP-24: Store performance (1h)
- STEP-25: Decoration performance (1h)
- STEP-26: API timeout test (1h)
- STEP-27: State machine compliance (2h)
- STEP-28: Accessibility check (2h, start)

**Day 7** (4 hours):
- STEP-28: Complete accessibility (1h)
- STEP-29: Performance validation summary (2h) [CRITICAL]
- STEP-30: Update documentation (3h, start)

**Day 8** (8 hours):
- STEP-30: Complete documentation (2h)
- STEP-31: Code review prep (2h)
- STEP-32: Phase 1 completion verification (2h) [CRITICAL]
- Buffer time (4h for any issues)

---

### Timeline Summary

**Estimated Duration**: 8-10 days (1.5-2 weeks)
- Week 1: Implementation (Days 1-5)
- Week 2: Validation & Polish (Days 6-8)
- Buffer: Days 9-10

**Critical Path**: Days 1, 3, 4 (STEP-03, STEP-09, STEP-15-17, STEP-29, STEP-32)

**Milestones**:
- End of Day 1: H2 fixed, decorations applying
- End of Day 3: All code changes complete
- End of Day 4: 22/22 tests passing
- End of Day 7: All validation complete
- End of Day 8: Phase 1 MVP complete

---

## 7. Success Criteria

**Phase 1 MVP Complete When**:
- ✅ All 32 steps completed
- ✅ 22/22 E2E tests passing (100%)
- ✅ 50 unit tests passing (80% coverage)
- ✅ 20 integration tests passing (70% coverage)
- ✅ All 8 performance constraints met
- ✅ All 12 behavioral constraints met
- ✅ All 10 type constraints met
- ✅ 0 console errors
- ✅ TypeScript strict mode passing
- ✅ All acceptance criteria met (ics-spec-v1.md §8)

**Ready for Phase 2 When**:
- Phase 1 complete
- Code reviewed and merged
- Documentation updated
- Known issues documented with Beads

---

**End of Execution Plan**

**Status**: Ready for Phase 4 (Artifact Generation - Beads Issues)

**Next**: Create Beads issues for each step, establish dependencies, begin execution
