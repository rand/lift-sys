# Integration Test Fixture Maintenance Guide

**Last Updated**: 2025-10-22
**Status**: Production
**Related**: Phase 2 E2E Validation, CI/CD Integration

---

## Overview

This guide covers maintaining cached integration test fixtures for lift-sys tests that use real Modal.com API calls.

**Key Benefits**:
- ✅ CI runs in <15 seconds using cached fixtures
- ✅ No API costs during normal CI runs
- ✅ Real LLM behavior validation
- ✅ Deterministic test results

---

## Fixture Files

### Location
All fixtures are stored in `tests/fixtures/`:

| File | Size | Tests | Data Type | Purpose |
|------|------|-------|-----------|---------|
| `modal_responses.json` | ~9KB | 6 | Raw JSON | Provider-level API responses |
| `ir_responses.json` | ~24KB | 5 | IntermediateRepresentation | IR translator outputs |
| `code_responses.json` | ~5KB | 4 | GeneratedCode | Code generator outputs |

**Total**: ~38KB, 15 tests cached

### Fixture Structure

Each fixture file is a JSON object with this structure:

```json
{
  "test_key_name": {
    "response": { /* actual cached data */ },
    "original_key": "test_key_name",
    "metadata": {
      "test": "test_name",
      "prompt": "user_prompt",
      /* test-specific metadata */
    }
  }
}
```

---

## Automated Maintenance

### Weekly Refresh Workflow

**Workflow**: `.github/workflows/refresh-fixtures.yml`
**Schedule**: Every Sunday at 2 AM UTC
**Trigger**: Automatic (cron) or manual (workflow_dispatch)

**What It Does**:
1. Runs all fixture-recorded tests with `RECORD_FIXTURES=true`
2. Generates fresh fixtures from real Modal API
3. Creates a PR if fixtures changed
4. Auto-labels PR with `automated`, `fixtures`, `integration-tests`

**Approving Refresh PRs**:
1. Check PR description for fixture changes summary
2. Verify fixture sizes are reasonable (<1MB each)
3. Spot-check IR quality (meaningful summaries, valid signatures)
4. Spot-check code quality (valid Python syntax, reasonable logic)
5. Merge if everything looks good

**Failure Handling**:
- Workflow continues even if some tests fail (`continue-on-error: true`)
- Only changed fixtures are committed
- Review PR to see which tests succeeded/failed

---

## Manual Fixture Refresh

### When to Manually Refresh

Refresh fixtures manually when:
- **Modal model upgraded** (e.g., Qwen2.5-Coder-32B → Qwen3)
- **IR schema changes** (new fields, validation rules)
- **Major prompt engineering updates**
- **Weekly refresh fails** (investigate and re-run)

### How to Refresh All Fixtures

```bash
# 1. Ensure Modal endpoint is configured
export MODAL_ENDPOINT_URL="https://rand--generate.modal.run"

# 2. Record provider fixtures (6 tests, ~5 minutes)
RECORD_FIXTURES=true uv run pytest \
  tests/integration/test_modal_provider_real.py \
  -v

# 3. Record translator fixtures (5 tests, ~4 minutes)
RECORD_FIXTURES=true uv run pytest \
  tests/integration/test_xgrammar_translator.py \
  -v

# 4. Record code generator fixtures (4 tests, ~6 minutes)
RECORD_FIXTURES=true uv run pytest \
  tests/integration/test_xgrammar_code_generator.py::test_xgrammar_generator_simple_sum \
  tests/integration/test_xgrammar_code_generator.py::test_xgrammar_generator_circle_area \
  tests/integration/test_xgrammar_code_generator.py::test_xgrammar_generator_with_imports \
  tests/integration/test_xgrammar_code_generator.py::test_xgrammar_generator_factorial \
  -v

# 5. Verify fixture changes
git diff tests/fixtures/

# 6. Commit changes
git add tests/fixtures/*.json
git commit -m "fixtures: Manual refresh from real Modal

Refreshed all integration test fixtures with latest Modal responses.

**Reason**: <explain why manual refresh was needed>
**Modal model**: Qwen2.5-Coder-32B-Instruct
**Date**: $(date -u +'%Y-%m-%d')
"

# 7. Push and create PR
git push -u origin feature/refresh-fixtures-$(date +%Y%m%d)
gh pr create --title "fixtures: Manual refresh $(date +%Y-%m-%d)" --body "Manual fixture refresh. See commit message for details."
```

**Total Time**: ~15 minutes for all fixtures

### How to Refresh Individual Fixtures

```bash
# Refresh only provider fixtures
RECORD_FIXTURES=true uv run pytest tests/integration/test_modal_provider_real.py -v

# Refresh only translator fixtures
RECORD_FIXTURES=true uv run pytest tests/integration/test_xgrammar_translator.py -v

# Refresh only specific code generator test
RECORD_FIXTURES=true uv run pytest \
  tests/integration/test_xgrammar_code_generator.py::test_xgrammar_generator_simple_sum \
  -v
```

---

## Verifying Fixtures

### After Recording New Fixtures

Always verify fixtures work correctly with caching:

```bash
# 1. Run tests WITHOUT recording (use cached fixtures)
uv run pytest tests/integration/test_modal_provider_real.py -v
uv run pytest tests/integration/test_xgrammar_translator.py -v
uv run pytest tests/integration/test_xgrammar_code_generator.py::test_xgrammar_generator_simple_sum -v

# 2. Verify speed (should be <15s total for all tests)

# 3. Check all tests pass (100% pass rate expected)
```

### Fixture Quality Checks

**Provider Fixtures** (`modal_responses.json`):
- JSON responses should be valid and complete
- IR objects should have all required fields
- No truncated responses

**Translator Fixtures** (`ir_responses.json`):
- IR summaries should be meaningful
- Signatures should have valid parameter names/types
- Effects and assertions should be relevant

**Code Generator Fixtures** (`code_responses.json`):
- Generated code should be valid Python syntax
- Implementations should be reasonable (not just stubs)
- Code should match IR intent

---

## Troubleshooting

### Fixture Recording Fails

**Problem**: Tests fail during `RECORD_FIXTURES=true`

**Solutions**:
1. **Modal endpoint down**: Check https://rand--generate.modal.run/health
2. **API timeout**: Increase timeout or retry
3. **Schema mismatch**: Update IR models to match new schema
4. **Model unavailable**: Wait for Modal deployment to complete

### Fixtures Not Used in CI

**Problem**: CI runs slowly, not using cached fixtures

**Solutions**:
1. Verify `RECORD_FIXTURES` env var is NOT set in CI (should default to `false`)
2. Check fixtures are committed to git
3. Verify fixture file paths match test expectations
4. Check test code uses `*_recorder` fixtures correctly

### Fixtures Too Large

**Problem**: Fixture files exceed size limits

**Solutions**:
1. Review fixture content for unnecessary data
2. Consider splitting tests into multiple fixture files
3. Use fixture compression (gzip) if needed
4. Reduce number of cached test cases

### Fixtures Outdated

**Problem**: Tests fail because fixtures don't match current code

**Solutions**:
1. Run manual fixture refresh (see above)
2. Check if IR schema changed recently
3. Verify Modal model version hasn't changed
4. Review git history for recent IR/schema changes

---

## Adding New Fixture-Recorded Tests

### Step 1: Write Test Using Recorder

```python
@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_new_feature(ir_recorder):  # or code_recorder, modal_recorder
    """Test description."""
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")

    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        translator = XGrammarIRTranslator(provider)

        # Wrap actual call with recorder
        ir = await ir_recorder.get_or_record(
            key="new_feature_test",  # Unique key for this test
            generator_fn=lambda: translator.translate("your prompt here"),
            metadata={"test": "new_feature", "description": "what this tests"},
        )

        # Your assertions
        assert ir.intent.summary is not None
        # ...

    finally:
        await provider.aclose()
```

### Step 2: Record Initial Fixture

```bash
RECORD_FIXTURES=true uv run pytest tests/integration/test_your_file.py::test_new_feature -v
```

### Step 3: Verify Caching Works

```bash
# Run WITHOUT recording (default)
uv run pytest tests/integration/test_your_file.py::test_new_feature -v

# Should complete in <1 second
```

### Step 4: Commit Test + Fixture

```bash
git add tests/integration/test_your_file.py tests/fixtures/*.json
git commit -m "test: Add new_feature integration test with fixture"
```

### Step 5: Update Workflows (If Needed)

If adding many new tests, update `.github/workflows/refresh-fixtures.yml` to include them in weekly refresh.

---

## Best Practices

### DO

✅ **Commit fixtures with tests** - Always commit fixture files alongside test files
✅ **Use descriptive keys** - Make fixture keys meaningful (`translator_circle_area` not `test1`)
✅ **Add metadata** - Include test name, prompt, description in metadata
✅ **Verify before committing** - Run tests with cached fixtures to ensure they work
✅ **Review refresh PRs** - Spot-check quality before merging automated refreshes
✅ **Document changes** - Explain why fixtures were refreshed in commit messages

### DON'T

❌ **Don't manually edit fixtures** - Always regenerate from real API calls
❌ **Don't commit without testing** - Verify cached fixtures work before committing
❌ **Don't ignore refresh failures** - Investigate why weekly refresh failed
❌ **Don't use same key twice** - Each test needs unique fixture key
❌ **Don't record in CI** - CI should always use `RECORD_FIXTURES=false` (default)
❌ **Don't commit secrets** - Fixtures should not contain API keys or credentials

---

## Monitoring

### Fixture Freshness

Check fixture age:
```bash
# See when fixtures were last updated
git log --oneline tests/fixtures/
```

**Recommended**: Fixtures should be <1 month old for optimal quality.

### Fixture Size

Monitor fixture file sizes:
```bash
ls -lh tests/fixtures/*.json
```

**Limits**:
- Single file: <1MB
- Total fixtures: <10MB

### CI Performance

Track CI test execution time:
- **Target**: <15 seconds for all cached integration tests
- **Alert**: If CI time >30 seconds, fixtures may not be caching

---

## FAQ

**Q: How often should fixtures be refreshed?**
A: Weekly automatic refresh is usually sufficient. Manual refresh needed when Modal model changes or IR schema updates.

**Q: What if weekly refresh PR shows no changes?**
A: Normal! If fixtures are fresh and LLM behavior is consistent, no changes expected.

**Q: Can I run fixture recording locally?**
A: Yes! Use `RECORD_FIXTURES=true` locally. Takes ~15 minutes for all fixtures.

**Q: Do fixtures work offline?**
A: Yes! Once committed, tests run from cached fixtures without any API calls.

**Q: What if fixtures conflict with main?**
A: Merge main into your branch, re-record fixtures if needed, verify tests pass.

**Q: Can I delete old fixtures?**
A: Only if corresponding tests are deleted. Each test needs its fixture.

---

## Related Documentation

- [Phase 2 Completion Summary](../planning/PHASE_2_COMPLETION_SUMMARY.md) - Full Phase 2 report
- [Integration Test Migration Plan](../planning/INTEGRATION_TEST_MIGRATION_PLAN.md) - Migration strategy
- [Response Recorder](../../tests/fixtures/response_recorder.py) - Caching implementation
- [test_modal_provider_real.py](../../tests/integration/test_modal_provider_real.py) - Provider tests
- [test_xgrammar_translator.py](../../tests/integration/test_xgrammar_translator.py) - Translator tests
- [test_xgrammar_code_generator.py](../../tests/integration/test_xgrammar_code_generator.py) - Generator tests

---

## Support

**Issues with fixtures?**
1. Check this guide first
2. Review recent git commits for fixture changes
3. Check GitHub Actions workflow runs for automated refresh status
4. Create issue with `fixtures` label if problem persists

**Questions?**
- See [PHASE_2_COMPLETION_SUMMARY.md](../planning/PHASE_2_COMPLETION_SUMMARY.md) for architecture details
- Check [conftest.py](../../tests/conftest.py) for recorder fixture implementations
- Review workflow file: `.github/workflows/refresh-fixtures.yml`
