# ICS Constraints Catalog

**Version**: 1.0
**Date**: 2025-10-25
**Status**: Phase 2 Constraints Catalog
**Parent**: `ics-master-spec.md` §6

---

## Document Purpose

This document catalogs all **constraints** that govern the ICS implementation. Constraints define boundaries, invariants, and requirements that must be satisfied for correct operation.

**Constraint Categories**:
1. Type Constraints (TypeScript, Pydantic)
2. Performance Constraints (OODA loops, latency)
3. Behavioral Constraints (state transitions, error handling)
4. UI/UX Constraints (accessibility, keyboard nav)

---

## Table of Contents

1. [Constraint Inventory](#1-constraint-inventory)
2. [Type Constraints](#2-type-constraints)
3. [Performance Constraints](#3-performance-constraints)
4. [Behavioral Constraints](#4-behavioral-constraints)
5. [UI/UX Constraints](#5-uiux-constraints)
6. [Validation Strategy](#6-validation-strategy)

---

## 1. Constraint Inventory

**Total Constraints**: 34

| Category | Count | Priority |
|----------|-------|----------|
| Type Constraints | 10 | P0 |
| Performance Constraints | 8 | P0 |
| Behavioral Constraints | 12 | P0 |
| UI/UX Constraints | 4 | P1 |

**Validation**:
- **Automated**: 28 constraints (tests, type checker, linter)
- **Manual**: 6 constraints (code review, accessibility audit)

---

## 2. Type Constraints

### TC1: TypeScript Strict Mode

**Requirement**: All TypeScript code MUST compile with strict mode enabled.

**Configuration**: `tsconfig.json`
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictPropertyInitialization": true
  }
}
```

**Validation**: `npm run type-check`

**Impact**: Code quality, type safety

---

### TC2: No Any Types

**Requirement**: No `any` types in production code (tests exempt).

**Validation**: ESLint rule `@typescript-eslint/no-explicit-any`

**Exceptions**: Test mocks, third-party library wrappers (with comment)

---

### TC3: Pydantic Validation (Backend)

**Requirement**: All API request/response schemas MUST use Pydantic models.

**Example**:
```python
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    options: dict[str, Any] = Field(default_factory=dict)
```

**Validation**: Pydantic raises `ValidationError` on invalid data

---

### TC4: Immutable State Updates

**Requirement**: Zustand store updates MUST create new objects (not mutate).

**Pattern**:
```typescript
// ✅ Correct
set({ holes: new Map(get().holes) });

// ❌ Wrong
get().holes.set(id, hole);  // Mutation!
```

**Validation**: Manual code review, integration tests

---

### TC5: SemanticAnalysis Type Completeness

**Requirement**: `SemanticAnalysis` interface MUST match backend response exactly.

**Fields**: All 10 fields required (empty arrays if no data):
- entities, relationships, modalOperators, constraints
- effects, assertions, ambiguities, contradictions
- typedHoles, confidenceScores

**Validation**: API integration tests

---

### TC6: Position Accuracy

**Requirement**: All `from`/`to` positions MUST be exact character offsets in original text.

**Example**:
```typescript
text = "The system must authenticate";
//      012345678901234567890123456789
// "system" = {from: 4, to: 10}
// "must" = {from: 11, to: 15}
```

**Validation**: Unit tests for position calculation

---

### TC7: Non-Nullable Store State

**Requirement**: Store state MUST have defined initial values (no undefined).

**Pattern**:
```typescript
// ✅ Correct
semanticAnalysis: SemanticAnalysis | null = null;  // Explicitly null

// ❌ Wrong
semanticAnalysis: SemanticAnalysis | undefined;  // Ambiguous
```

---

### TC8: ProseMirror Schema Validity

**Requirement**: Document schema MUST be valid ProseMirror schema.

**Validation**: ProseMirror runtime error if invalid

**File**: `frontend/src/lib/ics/schema.ts`

---

### TC9: Unique IDs

**Requirement**: All entity/modal/hole/constraint IDs MUST be unique within analysis.

**Pattern**: `${type}-${index}` or `${type}-${timestamp}-${random}`

**Validation**: Unit tests check uniqueness

---

### TC10: Enum Exhaustiveness

**Requirement**: All enum switches MUST be exhaustive (TypeScript compiler enforced).

**Pattern**:
```typescript
function handleStatus(status: HoleStatus) {
  switch (status) {
    case 'unresolved': return ...;
    case 'in_progress': return ...;
    case 'resolved': return ...;
    default:
      const _exhaustive: never = status;  // Compile error if missing case
      throw new Error(`Unhandled status: ${_exhaustive}`);
  }
}
```

---

## 3. Performance Constraints

### PC1: OODA Cycle < 2s (Primary)

**Requirement**: Semantic analysis OODA loop MUST complete in < 2s.

**Breakdown**:
- Typing → Debounce: 500ms
- API call: < 1s (backend) or < 200ms (mock)
- Decoration apply: < 100ms
- **Total**: < 1.6s target

**Measurement**: Manual timing with Chrome DevTools Performance

**Priority**: P0 (user requirement)

---

### PC2: Keystroke Latency < 16ms

**Requirement**: Editor MUST respond to keystrokes in < 16ms (60 FPS).

**Measurement**: Chrome DevTools Performance (Input Latency)

**Impact**: User experience (typing feels laggy if > 16ms)

---

### PC3: Store Update < 16ms

**Requirement**: Zustand store updates MUST complete in < 16ms.

**Pattern**: No heavy computation in actions (use async for slow operations)

---

### PC4: Decoration Calculation < 100ms

**Requirement**: Creating decorations from analysis MUST take < 100ms.

**Measurement**: Performance.now() timing in decorations plugin

**Optimization**: Batch decoration creation, use Map for O(1) lookup

---

### PC5: API Timeout 5s

**Requirement**: Backend API calls MUST timeout after 5s and fallback to mock.

**Implementation**:
```typescript
const response = await fetch(url, {
  signal: AbortSignal.timeout(5000)
});
```

---

### PC6: Health Check < 100ms

**Requirement**: Backend health check MUST respond in < 100ms.

**Implementation**: Simple endpoint, no heavy computation

---

### PC7: Mock Analysis < 200ms

**Requirement**: Mock semantic analysis MUST complete in < 200ms.

**Measurement**: Performance.now() timing

---

### PC8: Autocomplete Filter < 100ms

**Requirement**: Autocomplete results filtering MUST take < 100ms for 1000 items.

**Optimization**: Use efficient string search (fuzzy search library)

---

## 4. Behavioral Constraints

### BC1: Graceful Degradation

**Requirement**: Frontend MUST work without backend (using mock analysis).

**Flow**:
```
Health check fails → Toast notification → Use mock analysis → Continue
```

**Validation**: E2E test with backend stopped

---

### BC2: No Uncaught Errors

**Requirement**: All errors MUST be caught and handled (no console errors in production).

**Pattern**:
```typescript
try {
  // ...
} catch (error) {
  logger.error('Description', error);
  setAnalysisError(error.message);
  // Fallback behavior
}
```

**Validation**: Browser console check during manual testing

---

### BC3: State Machine Compliance

**Requirement**: All components MUST follow their state machines (defined in `ics-spec-v1.md` §3).

**Example**: SemanticEditor states: idle → typing → analyzing → success/error

**Validation**: Integration tests verify state transitions

---

### BC4: Empty State Handling

**Requirement**: All components MUST show meaningful empty states (no blank screens).

**Examples**:
- Editor: "Start writing your specification..."
- SymbolsPanel: "No elements detected. Start writing to see entities..."
- HoleInspector: "Select a hole from the Symbols panel..."

**Validation**: Manual checklist, screenshot tests (Phase 2)

---

### BC5: Error State Handling

**Requirement**: All components MUST show meaningful error states with recovery actions.

**Pattern**: Error message + Retry button

**Validation**: Manual error injection, E2E tests

---

### BC6: Loading State Handling

**Requirement**: All async operations MUST show loading indicators.

**Examples**:
- Analyzing: Spinner + "Analyzing..."
- Loading tree: Skeleton loaders

**Validation**: Manual testing, E2E tests

---

### BC7: Idempotent Actions

**Requirement**: Store actions SHOULD be idempotent where possible.

**Example**: `setSemanticAnalysis(analysis)` can be called multiple times with same value (no side effects)

---

### BC8: Transactional Updates

**Requirement**: Related state updates SHOULD be atomic (single set() call).

**Pattern**:
```typescript
// ✅ Atomic
set({
  semanticAnalysis: analysis,
  isAnalyzing: false,
  analysisError: null,
});

// ❌ Non-atomic
set({ semanticAnalysis: analysis });
set({ isAnalyzing: false });
set({ analysisError: null });
```

---

### BC9: Debounce Analysis Calls

**Requirement**: Analysis API calls MUST be debounced (500ms).

**Rationale**: Avoid flooding backend, wait for user to stop typing

**Implementation**: `useDebounce` hook or `setTimeout`

---

### BC10: Prevent Circular Updates

**Requirement**: Editor → Store → Editor updates MUST NOT create infinite loops.

**Pattern**: Check if value changed before dispatching transaction

---

### BC11: Preserve Undo/Redo

**Requirement**: ProseMirror undo/redo MUST work correctly (history plugin).

**Validation**: Manual testing (Ctrl+Z, Ctrl+Shift+Z)

---

### BC12: Persist UI Preferences

**Requirement**: Layout, theme, panel visibility MUST persist across sessions.

**Implementation**: Zustand persist middleware + localStorage

**Validation**: Refresh browser, check if preferences restored

---

## 5. UI/UX Constraints

### UX1: WCAG 2.1 AA Compliance

**Requirement**: Interface MUST meet WCAG 2.1 AA accessibility standards.

**Key Requirements**:
- Color contrast ≥ 4.5:1 (text)
- Color contrast ≥ 3:1 (interactive elements)
- All interactive elements keyboard accessible
- Focus indicators visible
- ARIA labels on icons
- Semantic HTML

**Validation**: axe-core (Phase 2), manual audit

---

### UX2: Keyboard Navigation

**Requirement**: All features MUST be accessible via keyboard.

**Shortcuts** (defined):
```
Ctrl+B: Toggle file explorer
Ctrl+Shift+F: Focus search
Ctrl+/: Toggle AI chat
Ctrl+Shift+I: Toggle hole inspector
↓↑: Navigate autocomplete
Enter: Select autocomplete item
Escape: Dismiss autocomplete/tooltip
```

**Validation**: Manual keyboard-only testing

---

### UX3: Responsive Layout

**Requirement**: Layout MUST work at viewport widths 1024px+.

**Breakpoints**:
- 1024px: Minimum (3-panel layout)
- 1280px: Comfortable (4-panel layout)
- 1920px+: Spacious (all panels expanded)

**Validation**: Manual resize testing, responsive tests (Phase 2)

---

### UX4: Visual Feedback

**Requirement**: All user actions MUST have immediate visual feedback (< 100ms).

**Examples**:
- Button click: Visual press state
- Hover: Highlight / tooltip
- Focus: Focus ring
- Loading: Spinner / skeleton
- Success: Toast / checkmark
- Error: Toast / error message

**Validation**: Manual testing, interaction tests

---

## 6. Validation Strategy

### 6.1 Automated Validation

| Constraint | Tool | When |
|------------|------|------|
| TC1-TC2 | TypeScript compiler | Pre-commit, CI |
| TC3 | Pydantic | Runtime (backend) |
| TC4-TC10 | Jest/Vitest unit tests | Pre-commit, CI |
| PC1-PC8 | Performance tests (manual Phase 1, automated Phase 2) | Pre-release |
| BC1-BC12 | Integration + E2E tests | Pre-commit, CI |
| UX2 | Keyboard E2E tests | CI |

### 6.2 Manual Validation

| Constraint | Process | When |
|------------|---------|------|
| UX1 | Accessibility audit (axe-core) | Pre-release |
| UX3 | Responsive testing | Pre-release |
| UX4 | Manual interaction testing | Weekly |
| BC2 | Browser console check | Pre-release |
| BC4-BC6 | State checklist | Weekly |

### 6.3 Constraint Violation Handling

**Severity Levels**:
- **P0 (Critical)**: Blocks release (TC1, PC1, BC1, BC2)
- **P1 (High)**: Must fix before next release (TC2-TC10, PC2-PC8, BC3-BC12)
- **P2 (Medium)**: Should fix (UX1-UX4)

**Process**:
1. Constraint violation detected (test failure, lint error, code review)
2. Create Beads issue with constraint ID
3. Prioritize based on severity
4. Fix and verify
5. Update validation if needed

---

## Summary

**By Phase**:
- **Phase 1**: 28 constraints (all P0 + P1)
- **Phase 2**: +6 constraints (advanced features)

**By Validation**:
- **Automated**: 28 constraints (82%)
- **Manual**: 6 constraints (18%)

**Current Status**:
- ✅ Met: 22 constraints
- ⚠️ Partial: 8 constraints (performance not measured yet)
- ❌ Failing: 4 constraints (tests failing due to H2)

**Next Steps**:
1. Fix H2 (DecorationApplication) → Unblocks BC3, BC4, PC4
2. Run performance measurements → Verify PC1-PC8
3. Run full E2E suite → Verify BC1-BC12
4. Accessibility audit → Verify UX1

---

**End of Constraints Catalog**

**Next**: `test-plan.md` (Comprehensive testing strategy)
