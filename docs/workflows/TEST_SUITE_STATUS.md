# Test Suite Workflow Status

**Date**: 2025-10-26
**Status**: Disabled (manually)
**Workflow**: `.github/workflows/test.yml`
**Last Run**: 2025-10-12 (failed)

---

## Current Status

The Test Suite workflow (`.github/workflows/test.yml`) is **manually disabled** in GitHub Actions.

**Workflow ID**: 197157035
**Disabled By**: Manual action (unknown when/who)
**Last Activity**: October 12, 2025 (multiple failures)

---

## Workflow Configuration

The workflow is configured to run on:
- `push` to `main` and `develop` branches
- `pull_request` to `main` branch

**Jobs**:
1. **lint** - Ruff linting and formatting checks
2. **test** - Python tests (3.11, 3.12, 3.13) with coverage
3. **frontend** - Node.js tests and build

---

## Why Was It Disabled?

The workflow was likely disabled because:
1. It was failing consistently (last 5 runs all failed on Oct 12)
2. It was blocking CI/CD for the project
3. Manual decision to disable rather than fix immediately

**Note**: This is speculation - the actual reason is unknown. The workflow was disabled manually via GitHub UI.

---

## Re-enabling Strategy

### Option 1: Enable and Fix Immediately (Recommended if urgent)

```bash
# 1. Enable workflow via GitHub UI
# Go to: https://github.com/rand/lift-sys/actions/workflows/test.yml
# Click "Enable workflow"

# 2. Manually trigger to diagnose
gh workflow enable test.yml
gh workflow run test.yml

# 3. Check results
gh run watch

# 4. Fix any failures found
```

### Option 2: Fix First, Then Enable (Recommended if not urgent)

```bash
# 1. Run tests locally to identify issues
cd /Users/rand/src/lift-sys
uv run pytest tests/ -v

# 2. Fix Python test failures

# 3. Test frontend locally
cd frontend
npm ci
npm test
npm run build

# 4. Fix frontend test/build failures

# 5. Once all tests pass locally, enable workflow
gh workflow enable test.yml
```

### Option 3: Make Advisory Like Robustness (Pragmatic)

Add `continue-on-error: true` to jobs that are failing, similar to what we did with robustness testing.

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    continue-on-error: true  # Advisory mode
    steps:
      # ... existing steps

  test:
    runs-on: ubuntu-latest
    continue-on-error: true  # Advisory mode
    strategy:
      # ... existing config
```

---

## Likely Issues (Based on Oct 12 Failures)

Without access to the failure logs, likely issues include:

### Python Tests
- **Dependency issues**: uv sync might fail or install wrong versions
- **Import errors**: Missing modules or circular imports
- **Test failures**: Actual test assertions failing
- **API server startup**: Uvicorn server might not start properly
- **Database connectivity**: Supabase connection issues (if tests use DB)

### Frontend Tests
- **npm ci failures**: package-lock.json might be out of sync
- **TypeScript errors**: Type checking might fail
- **Vitest failures**: Component tests might be broken
- **Build failures**: Vite build might fail due to TypeScript/lint errors

### Lint
- **Ruff errors**: Code style violations
- **Formatting issues**: Code not formatted with ruff format

---

## Recommended Action

**Priority**: Medium (not blocking current work, but should be addressed)

**Immediate** (if Test Suite is critical):
1. Enable workflow: `gh workflow enable test.yml`
2. Trigger manually: `gh workflow run test.yml`
3. Watch and diagnose: `gh run watch`
4. Fix identified issues

**Short-term** (if Test Suite is nice-to-have):
1. Document as "known issue" (this file)
2. Add to project roadmap
3. Fix when bandwidth allows
4. Consider advisory mode as intermediate step

**Long-term**:
- Keep Test Suite enabled and green
- Monitor regularly
- Fix failures promptly
- Consider making advisory if it becomes flaky

---

## Enabling the Workflow

### Via GitHub UI
1. Go to: https://github.com/rand/lift-sys/actions/workflows/test.yml
2. Click the "⋯" menu (top right)
3. Click "Enable workflow"

### Via gh CLI
```bash
gh workflow enable test.yml
```

### Via API
```bash
curl -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/rand/lift-sys/actions/workflows/197157035/enable
```

---

## Testing Locally Before Re-enabling

### Python Tests
```bash
# Full test suite
uv run pytest tests/ -v

# Specific test categories
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run pytest tests/e2e/ -v

# With coverage
uv run pytest tests/ --cov=lift_sys --cov-report=term
```

### Frontend Tests
```bash
cd frontend

# Install dependencies
npm ci

# Run tests
npm test

# Build
npm run build

# Lint
npm run lint
```

### Lint
```bash
# Ruff check
uv run ruff check lift_sys/ tests/

# Ruff format check
uv run ruff format --check lift_sys/ tests/
```

---

## Next Steps

1. **Decide priority**: Is fixing Test Suite urgent or can it wait?
2. **If urgent**: Follow "Option 1" above
3. **If not urgent**: Follow "Option 2" above
4. **Document decision**: Update this file with chosen approach
5. **Track progress**: Add to project roadmap/beads

---

## Related Documentation

- **Robustness Testing Status**: `docs/workflows/ROBUSTNESS_TESTING_STATUS.md`
- **Workflow Config**: `.github/workflows/test.yml`
- **Testing Strategy**: `CLAUDE.md` Section 6

---

**Last Updated**: 2025-10-26
**Next Review**: TBD (when enabling Test Suite)
**Owner**: lift-sys maintainers
