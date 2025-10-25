# ICS Comprehensive Test Plan

**Version**: 1.0
**Date**: 2025-10-25
**Status**: Phase 2 Test Strategy
**Parent**: `ics-master-spec.md` §7

---

## Document Purpose

This document defines the complete testing strategy for ICS, including:
- Test pyramid (unit, integration, E2E)
- Coverage targets
- Test scenarios
- Validation criteria
- Testing tools and infrastructure

---

## Table of Contents

1. [Test Strategy](#1-test-strategy)
2. [Unit Tests](#2-unit-tests)
3. [Integration Tests](#3-integration-tests)
4. [E2E Tests](#4-e2e-tests)
5. [Performance Tests](#5-performance-tests)
6. [Accessibility Tests](#6-accessibility-tests)
7. [Test Infrastructure](#7-test-infrastructure)
8. [Coverage Targets](#8-coverage-targets)

---

## 1. Test Strategy

### 1.1 Test Pyramid

```
         ┌────────────────┐
         │   E2E Tests    │  22 tests (user workflows)
         │  (Playwright)  │  Target: 100% pass
         └────────────────┘
              ▲
       ┌──────────────────┐
       │Integration Tests │  20 tests (component integration)
       │ (Vitest + MSW)   │  Target: 70% coverage
       └──────────────────┘
              ▲
    ┌──────────────────────────┐
    │      Unit Tests          │  50 tests (functions, utilities)
    │   (Vitest + RTL)         │  Target: 80% coverage
    └──────────────────────────┘
```

### 1.2 Testing Principles

1. **Test Behavior, Not Implementation**: Focus on what components do, not how they do it
2. **Integration Over Isolation**: Prefer integration tests for component interactions
3. **User-Centric E2E**: E2E tests follow real user workflows
4. **Fast Feedback**: Unit tests < 1ms, Integration < 100ms, E2E < 5s
5. **Deterministic**: No flaky tests allowed (fix or skip)

### 1.3 Test Tools

| Layer | Tool | Purpose |
|-------|------|---------|
| **Unit** | Vitest | Test runner, assertions |
| **Unit** | React Testing Library | Component testing |
| **Integration** | Vitest + MSW | API mocking, integration |
| **E2E** | Playwright | Browser automation |
| **Coverage** | Vitest (c8/istanbul) | Code coverage |
| **Performance** | Chrome DevTools | Performance profiling |
| **Accessibility** | axe-core (Phase 2) | WCAG compliance |

---

## 2. Unit Tests

### 2.1 Unit Test Scope

**Target**: 50 tests, 80% coverage

**What to Test**:
- Pure functions (text extraction, position mapping)
- Utilities (mock analysis, decorations creation)
- Store actions (state transitions)
- Hooks (useDebounce, useICSStore)
- Type guards (isEntity, isModal, etc.)

**What NOT to Test**:
- React component rendering (use integration tests)
- ProseMirror internals (trust the library)
- Third-party libraries

### 2.2 Unit Test Scenarios

#### Mock Analysis
**File**: `frontend/src/lib/ics/mockSemanticAnalysis.test.ts`

```typescript
describe('generateMockAnalysis', () => {
  it('detects entities from patterns', () => {
    const text = 'The system must authenticate users';
    const analysis = generateMockAnalysis(text);

    expect(analysis.entities).toHaveLength(2);
    expect(analysis.entities[0]).toMatchObject({
      type: 'TECHNICAL',
      text: 'system',
      from: 4,
      to: 10,
    });
  });

  it('detects modal operators', () => {
    const text = 'The system must authenticate';
    const analysis = generateMockAnalysis(text);

    expect(analysis.modalOperators).toHaveLength(1);
    expect(analysis.modalOperators[0]).toMatchObject({
      modality: 'necessity',
      text: 'must',
    });
  });

  it('detects typed holes', () => {
    const text = 'Use ???AuthProvider for authentication';
    const analysis = generateMockAnalysis(text);

    expect(analysis.typedHoles).toHaveLength(1);
    expect(analysis.typedHoles[0].identifier).toBe('AuthProvider');
  });

  it('returns empty arrays for empty text', () => {
    const analysis = generateMockAnalysis('');

    expect(analysis.entities).toEqual([]);
    expect(analysis.modalOperators).toEqual([]);
    expect(analysis.typedHoles).toEqual([]);
  });
});
```

---

#### Decorations Creation
**File**: `frontend/src/lib/ics/decorations.test.ts`

```typescript
import { schema } from 'prosemirror-schema-basic';
import { createEntityDecoration, createModalDecoration } from './decorations';

describe('createEntityDecoration', () => {
  it('creates decoration with correct class', () => {
    const entity = {
      id: 'entity-0',
      type: 'TECHNICAL',
      text: 'system',
      from: 0,
      to: 6,
      confidence: 0.9,
    };

    const decoration = createEntityDecoration(0, 6, entity);

    expect(decoration.type.attrs.class).toContain('entity');
    expect(decoration.type.attrs.class).toContain('entity-technical');
  });

  it('includes data attributes', () => {
    const entity = { id: 'e1', type: 'PERSON', text: 'Alice', from: 0, to: 5, confidence: 0.95 };
    const decoration = createEntityDecoration(0, 5, entity);

    expect(decoration.type.attrs['data-entity-id']).toBe('e1');
    expect(decoration.type.attrs['data-entity-type']).toBe('PERSON');
  });
});
```

---

#### Store Actions
**File**: `frontend/src/lib/ics/store.test.ts`

```typescript
import { useICSStore } from './store';

describe('ICSStore', () => {
  beforeEach(() => {
    useICSStore.setState({
      semanticAnalysis: null,
      isAnalyzing: false,
      holes: new Map(),
    });
  });

  it('setSemanticAnalysis updates state', () => {
    const analysis = { entities: [], modalOperators: [], /* ... */ };
    useICSStore.getState().setSemanticAnalysis(analysis);

    expect(useICSStore.getState().semanticAnalysis).toBe(analysis);
    expect(useICSStore.getState().isAnalyzing).toBe(false);
  });

  it('resolveHole updates hole status', () => {
    const hole: TypedHole = {
      id: 'h1',
      identifier: 'H1',
      kind: 'intent',
      status: 'unresolved',
      typeHint: 'Auth',
      dependencies: { blocks: [], blockedBy: [] },
    };

    useICSStore.setState({ holes: new Map([['h1', hole]]) });
    useICSStore.getState().resolveHole('h1', {
      source: 'user',
      description: 'Use OAuth2',
    });

    const updated = useICSStore.getState().holes.get('h1');
    expect(updated?.status).toBe('resolved');
  });

  it('propagateConstraints creates new constraints', () => {
    const hole1: TypedHole = {
      id: 'h1',
      identifier: 'H1',
      kind: 'intent',
      status: 'resolved',
      typeHint: 'Auth',
      dependencies: { blocks: ['h2'], blockedBy: [] },
      solutionSpace: { narrowed: true, refinements: [{ source: 'user', description: 'OAuth2' }] },
    };

    const hole2: TypedHole = {
      id: 'h2',
      identifier: 'H2',
      kind: 'signature',
      status: 'unresolved',
      typeHint: 'Function',
      dependencies: { blocks: [], blockedBy: ['h1'] },
    };

    useICSStore.setState({
      holes: new Map([['h1', hole1], ['h2', hole2]]),
      constraints: new Map(),
    });

    useICSStore.getState().propagateConstraints('h1', ['h2']);

    expect(useICSStore.getState().constraints.size).toBeGreaterThan(0);
  });
});
```

---

### 2.3 Unit Test Coverage Target

**Overall**: 80%

**By Module**:
| Module | Target | Priority |
|--------|--------|----------|
| mockSemanticAnalysis.ts | 90% | P0 |
| decorations.ts | 85% | P0 |
| store.ts | 80% | P0 |
| api.ts | 75% | P1 |
| autocomplete.ts | 70% | P1 |

---

## 3. Integration Tests

### 3.1 Integration Test Scope

**Target**: 20 tests, 70% coverage

**What to Test**:
- Component + Store integration
- Editor + Decorations plugin
- API Client + Backend (mocked)
- Store + Persistence

**Tools**:
- Vitest (test runner)
- React Testing Library (component rendering)
- MSW (Mock Service Worker - API mocking)

### 3.2 Integration Test Scenarios

#### SemanticEditor + Store
**File**: `frontend/src/components/ics/SemanticEditor.integration.test.tsx`

```typescript
import { render, screen, userEvent } from '@testing-library/react';
import { SemanticEditor } from './SemanticEditor';
import { useICSStore } from '@/lib/ics/store';

describe('SemanticEditor Integration', () => {
  it('updates store when user types', async () => {
    const user = userEvent.setup();
    render(<SemanticEditor />);

    const editor = screen.getByRole('textbox');
    await user.type(editor, 'The system must authenticate');

    expect(useICSStore.getState().specificationText).toContain('authenticate');
  });

  it('applies decorations when analysis updates', async () => {
    render(<SemanticEditor />);

    const analysis = {
      entities: [{ id: 'e1', type: 'TECHNICAL', text: 'system', from: 4, to: 10, confidence: 0.9 }],
      modalOperators: [],
      typedHoles: [],
      // ...
    };

    useICSStore.getState().setSemanticAnalysis(analysis);

    // Wait for decoration application
    await waitFor(() => {
      const entity = screen.getByText('system');
      expect(entity).toHaveClass('entity');
    });
  });
});
```

---

#### API Client + Mock Backend
**File**: `frontend/src/lib/ics/api.integration.test.ts`

```typescript
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { analyzeText, checkHealth } from './api';

const server = setupServer();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('API Client Integration', () => {
  it('uses backend when healthy', async () => {
    server.use(
      http.get('*/ics/health', () => HttpResponse.json({ status: 'healthy' })),
      http.post('*/ics/analyze', () => HttpResponse.json({
        entities: [{ id: 'e1', type: 'TECHNICAL', text: 'system', from: 0, to: 6, confidence: 0.9 }],
        modalOperators: [],
        // ...
      }))
    );

    const analysis = await analyzeText('system');

    expect(analysis.entities).toHaveLength(1);
  });

  it('falls back to mock when backend unavailable', async () => {
    server.use(
      http.get('*/ics/health', () => HttpResponse.json({ status: 'unhealthy' }))
    );

    const analysis = await analyzeText('system');

    // Mock should still return results
    expect(analysis).toBeDefined();
    expect(analysis.entities).toBeDefined();
  });

  it('handles backend timeout', async () => {
    server.use(
      http.post('*/ics/analyze', async () => {
        await new Promise(resolve => setTimeout(resolve, 6000)); // Longer than 5s timeout
        return HttpResponse.json({});
      })
    );

    const analysis = await analyzeText('system');

    // Should fall back to mock
    expect(analysis).toBeDefined();
  });
});
```

---

### 3.3 Integration Test Coverage Target

**Overall**: 70%

**Focus Areas**:
- Critical paths (editor → store → decorations)
- Error handling (API failures, timeouts)
- State transitions (analyzing → success/error)

---

## 4. E2E Tests

### 4.1 E2E Test Scope

**Current**: 22 tests (12 passing, 10 failing)
**Target**: 22 tests, 100% passing

**Tools**: Playwright

**File**: `frontend/e2e/ics-*.spec.ts`

### 4.2 Existing E2E Tests

#### Passing (12)
1. ✅ Authentication setup
2. ✅ Navigate to ICS section
3. ✅ Display all ICS panels
4. ✅ Show character count in toolbar
5. ✅ Allow typing in editor
6. ✅ Show loading state during analysis
7. ✅ Detect ambiguities (probabilistic)
8. ✅ Trigger file autocomplete with #
9. ✅ Trigger symbol autocomplete with @
10. ✅ Dismiss autocomplete on Escape
11. ✅ Handle empty text input
12. ✅ Handle long text input

#### Failing (10) - All require H2 fix
13. ❌ Detect entities
14. ❌ Detect modal operators
15. ❌ Detect typed holes
16. ❌ Detect constraints
17. ❌ Filter autocomplete results
18. ❌ Show tooltip on entity hover
19. ❌ Show tooltip on modal operator hover
20. ❌ Show tooltip on typed hole hover
21. ❌ Hide tooltip when mouse moves away
22. ❌ Use backend or mock analysis gracefully

### 4.3 E2E Test Scenarios (Key Workflows)

#### Workflow 1: Basic Semantic Editing
**File**: `frontend/e2e/ics-semantic-editor.spec.ts`

```typescript
test('semantic editing workflow', async ({ page }) => {
  await page.goto('/ics');

  // Type specification
  await page.getByRole('textbox').fill('The system must authenticate users');

  // Wait for analysis
  await page.waitForSelector('.entity', { timeout: 2000 });

  // Verify highlights
  const entities = await page.locator('.entity').count();
  expect(entities).toBeGreaterThan(0);

  const modals = await page.locator('.modal-operator').count();
  expect(modals).toBeGreaterThan(0);
});
```

---

#### Workflow 2: Hole Inspection
**File**: `frontend/e2e/ics-hole-inspector.spec.ts`

```typescript
test('hole inspection workflow', async ({ page }) => {
  await page.goto('/ics');

  // Type spec with hole
  await page.getByRole('textbox').fill('Use ???AuthProvider for authentication');

  // Wait for analysis
  await page.waitForSelector('.hole-badge', { timeout: 2000 });

  // Click hole in symbols panel
  await page.getByRole('tab', { name: 'Holes' }).click();
  await page.getByText('AuthProvider').click();

  // Verify inspector opens
  await expect(page.getByText('Hole Inspector')).toBeVisible();
  await expect(page.getByText('Type: ???AuthProvider')).toBeVisible();
});
```

---

#### Workflow 3: Autocomplete
**File**: `frontend/e2e/ics-autocomplete.spec.ts`

```typescript
test('autocomplete workflow', async ({ page }) => {
  await page.goto('/ics');

  const editor = page.getByRole('textbox');

  // Type #
  await editor.fill('See #');

  // Wait for popup
  await page.waitForSelector('.autocomplete-popup', { timeout: 1000 });

  // Verify results shown
  const results = await page.locator('.autocomplete-result').count();
  expect(results).toBeGreaterThan(0);

  // Type to filter
  await editor.press('d');
  await editor.press('o');
  await editor.press('c');

  // Verify filtered
  await expect(page.getByText('docs/')).toBeVisible();

  // Select with Enter
  await editor.press('ArrowDown');
  await editor.press('Enter');

  // Verify inserted
  await expect(editor).toContainText('#docs/');
});
```

---

### 4.4 E2E Test Infrastructure

**Setup**:
```typescript
// frontend/playwright.config.ts
export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    storageState: 'playwright/.auth/user.json',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
  ],
});
```

**Authentication**:
```typescript
// frontend/playwright/auth.setup.ts
setup('authenticate', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Continue with Google/i }).click();
  await page.waitForLoadState('networkidle');
  await page.context().storageState({ path: authFile });
});
```

---

## 5. Performance Tests

### 5.1 Performance Test Scope

**Target**: Verify all performance constraints (PC1-PC8)

**Method**: Manual measurement (Phase 1), automated (Phase 2)

### 5.2 Performance Metrics

| Metric | Constraint | Measurement |
|--------|------------|-------------|
| OODA Cycle | < 2s | Manual timing |
| Keystroke Latency | < 16ms | Chrome DevTools Performance |
| Store Update | < 16ms | Performance.now() |
| Decoration Calc | < 100ms | Performance.now() |
| API Timeout | 5s | Fetch timeout |
| Health Check | < 100ms | Network timing |
| Mock Analysis | < 200ms | Performance.now() |
| Autocomplete Filter | < 100ms | Performance.now() |

### 5.3 Performance Test Example

```typescript
// frontend/src/lib/ics/decorations.perf.test.ts
describe('Decorations Performance', () => {
  it('creates decorations in < 100ms for 100 entities', () => {
    const analysis = {
      entities: Array.from({ length: 100 }, (_, i) => ({
        id: `e${i}`,
        type: 'TECHNICAL',
        text: `entity${i}`,
        from: i * 10,
        to: i * 10 + 7,
        confidence: 0.9,
      })),
      // ...
    };

    const start = performance.now();
    const decorations = createDecorationsFromAnalysis(doc, analysis);
    const end = performance.now();

    expect(end - start).toBeLessThan(100);
  });
});
```

---

## 6. Accessibility Tests

### 6.1 Accessibility Test Scope

**Target**: WCAG 2.1 AA compliance

**Method**: axe-core (Phase 2), manual audit

**Tools**:
- @axe-core/react (runtime)
- @axe-core/playwright (E2E)

### 6.2 Accessibility Test Example

```typescript
// frontend/e2e/ics-accessibility.spec.ts (Phase 2)
import { injectAxe, checkA11y } from 'axe-playwright';

test('ICS view is accessible', async ({ page }) => {
  await page.goto('/ics');
  await injectAxe(page);

  // Check for accessibility violations
  await checkA11y(page, null, {
    detailedReport: true,
    detailedReportOptions: { html: true },
  });
});
```

---

## 7. Test Infrastructure

### 7.1 Test Commands

```bash
# Unit tests
npm run test                    # Run all unit tests
npm run test:watch             # Watch mode
npm run test:coverage          # With coverage

# Integration tests
npm run test:integration       # Run integration tests

# E2E tests
npm run test:e2e               # Run all E2E tests
npm run test:e2e:ui            # Playwright UI mode
npm run test:e2e:debug         # Debug mode
npm run test:e2e:report        # View HTML report

# Performance tests
npm run test:perf              # Run performance tests (Phase 2)

# Accessibility tests
npm run test:a11y              # Run accessibility tests (Phase 2)

# All tests
npm run test:all               # Unit + Integration + E2E
```

### 7.2 CI Integration

**GitHub Actions**:
```yaml
name: Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v3

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
```

---

## 8. Coverage Targets

### 8.1 Overall Coverage

| Layer | Tests | Coverage | Status |
|-------|-------|----------|--------|
| Unit | 50 | 80% | 🔴 0/50 (TODO) |
| Integration | 20 | 70% | 🔴 0/20 (TODO) |
| E2E | 22 | 100% pass | 🟡 12/22 (55%) |

### 8.2 File-Level Coverage

| File | Target | Priority |
|------|--------|----------|
| mockSemanticAnalysis.ts | 90% | P0 |
| decorations.ts | 85% | P0 |
| store.ts | 80% | P0 |
| SemanticEditor.tsx | 75% | P0 |
| api.ts | 75% | P1 |
| autocomplete.ts | 70% | P1 |

### 8.3 Critical Path Coverage

**Must Have** (Phase 1):
- ✅ Typing → Analysis → Decorations (E2E)
- ❌ Decorations application (fix H2)
- ❌ Mock fallback (unit + integration)
- ❌ Store actions (unit)

**Should Have** (Phase 2):
- Hole dependency graph
- Constraint propagation
- AI assistant

---

## Next Steps

**Phase 1 Test Priorities**:
1. Fix H2 → Get 22/22 E2E tests passing
2. Write unit tests for mock analysis (10 tests)
3. Write unit tests for decorations (10 tests)
4. Write unit tests for store (10 tests)
5. Write integration tests for editor + store (5 tests)
6. Write integration tests for API client (5 tests)

**Phase 2 Test Additions**:
7. Performance test suite
8. Accessibility test suite
9. Visual regression tests (Chromatic/Percy)
10. Load tests (Playwright stress testing)

---

**End of Test Plan**

**Total Specs Created**: 6 (master, state, typed-holes, constraints, test-plan, spec-v1)
