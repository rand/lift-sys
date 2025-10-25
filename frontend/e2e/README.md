# ICS E2E Tests with Playwright

This directory contains end-to-end tests for the Integrated Context Studio (ICS) using Playwright.

## Test Files

- **`ics-basic.spec.ts`** - Basic layout and navigation tests
- **`ics-semantic-editor.spec.ts`** - Semantic editor, highlighting, autocomplete, and tooltips tests

## Running Tests

### Prerequisites

1. **Install dependencies** (if not already done):
   ```bash
   npm install
   ```

2. **Install Playwright browsers** (if not already done):
   ```bash
   npx playwright install
   ```

### Run Tests

**All tests in headed mode (see browser):**
```bash
npm run test:e2e
```

**All tests in headless mode (CI):**
```bash
npm run test:e2e:headless
```

**Run specific test file:**
```bash
npx playwright test ics-basic.spec.ts
```

**Run tests in UI mode (interactive):**
```bash
npx playwright test --ui
```

**Debug mode (step through tests):**
```bash
npx playwright test --debug
```

### View Test Results

After running tests, view the HTML report:
```bash
npx playwright show-report
```

## Test Structure

### ICS Basic Layout Tests
- Navigation to ICS section
- Panel visibility checks
- Character count display

### Semantic Editor Tests
- **Typing**: Basic text input and character count
- **Semantic Analysis**: Detects entities, modals, constraints, holes, ambiguities
- **Autocomplete**: File (#) and symbol (@) autocomplete triggers
- **Tooltips**: Hover tooltips for all semantic element types
- **Backend Integration**: Graceful fallback between backend NLP and mock analysis

## Key Test Patterns

### Waiting for Semantic Analysis

Semantic analysis has a 500ms debounce, so tests wait ~1000ms after typing:

```typescript
await editor.fill('Text to analyze');
await page.waitForTimeout(1000); // Wait for debounce + analysis
```

### Checking for Semantic Highlights

Different semantic elements have specific CSS classes:

```typescript
const entities = page.locator('.entity');
const modals = page.locator('.modal');
const holes = page.locator('.hole');
const constraints = page.locator('.constraint');
const ambiguities = page.locator('.ambiguity');
```

### Testing Tooltips

Tooltips have a 300ms hover delay:

```typescript
await element.hover();
await page.waitForTimeout(500); // Wait for tooltip delay
const tooltip = page.locator('.semantic-tooltip');
await expect(tooltip).toBeVisible();
```

## Authentication Handling

**✅ IMPLEMENTED**: Tests use the app's demo mode for realistic authentication:

1. **Setup script** (`playwright/auth.setup.ts`) runs before all tests
2. Creates an authenticated demo user in localStorage
3. Saves auth state to `playwright/.auth/user.json`
4. All tests reuse this authenticated state

This provides **realistic system behavior** by using the actual auth code paths with demo data.

## CI/CD Integration

Add to GitHub Actions workflow:

```yaml
- name: Install Playwright Browsers
  run: npx playwright install --with-deps chromium

- name: Run E2E Tests
  run: npm run test:e2e:headless

- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Debugging Failed Tests

1. **Screenshots**: Automatically captured on failure in `test-results/`
2. **Videos**: Captured on failure (if enabled)
3. **Traces**: View with `npx playwright show-trace trace.zip`
4. **Debug mode**: Run with `--debug` flag to step through

## Best Practices

1. **Use data-testid** for stable selectors (future improvement)
2. **Avoid hardcoded timeouts** when possible (use `waitForSelector`)
3. **Test user flows**, not implementation details
4. **Keep tests independent** (each test should work in isolation)
5. **Clean up state** between tests (use `beforeEach`)

## Known Issues

1. **Ambiguity detection**: Probabilistic (30% sampling), tests may be flaky
2. **Backend dependency**: Tests work with or without backend (graceful fallback)

## Future Improvements

- [x] Add authentication handling (COMPLETED - using demo mode)
- [ ] Add visual regression tests (Playwright screenshots)
- [ ] Add accessibility tests (`@axe-core/playwright`)
- [ ] Add performance tests (measure analysis latency)
- [ ] Add data-testid attributes for more stable selectors
- [ ] Add tests for panel resizing and layout persistence
- [ ] Add tests for file explorer and symbols panel
