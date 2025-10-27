---
track: infrastructure
document_type: migration_guide
status: complete
priority: P1
completion: 100%
last_updated: 2025-10-22
session_protocol: |
  For new Claude Code session:
  1. Integration test migration strategy is COMPLETE (planning phase)
  2. 23 integration tests: 10 need real Modal (43%), 13 stay mocked (57%)
  3. Migration pattern: @pytest.mark.real_modal + ir_recorder fixtures
  4. Estimated effort: 3-4 days implementation, 4 weeks part-time
  5. Use as reference for test migration decisions
related_docs:
  - docs/tracks/infrastructure/INTEGRATION_TEST_MIGRATION_PLAN.md
  - docs/tracks/testing/TESTING_STATUS.md
  - docs/tracks/testing/E2E_VALIDATION_PLAN.md
  - docs/MASTER_ROADMAP.md
---

# Integration Test Migration - Quick Reference

**Date**: 2025-10-22
**Status**: Planning Complete

---

## TL;DR

- **Total Integration Tests**: 23 files
- **Need Real Modal**: 10 files (43%)
- **Keep Mocked**: 13 files (57%)
- **Effort**: 3-4 days
- **Timeline**: 4 weeks part-time

---

## Migration Checklist (Per Test)

```bash
# 1. Add pytest marker
@pytest.mark.real_modal
@pytest.mark.asyncio

# 2. Add fixture parameter
async def test_something(ir_recorder):  # or modal_recorder

# 3. Wrap expensive call
ir = await ir_recorder.get_or_record(
    key="test_file_scenario",
    generator_fn=lambda: expensive_modal_call(),
    metadata={"test": "context"}
)

# 4. Record fixtures (first run)
RECORD_FIXTURES=true uv run pytest tests/integration/test_file.py -v

# 5. Validate cache works (subsequent runs)
uv run pytest tests/integration/test_file.py -v  # Should be <1s

# 6. Commit fixtures
git add tests/fixtures/*.json
git commit -m "Add fixtures for test_file.py"
```

---

## Files to Migrate (Priority Order)

### P0 - Week 1 (4 files, 8-12h)
- [x] `test_xgrammar_translator.py` - NLP → IR translation
- [x] `test_xgrammar_translator_with_constraints.py` - With grammar constraints
- [x] `test_xgrammar_code_generator.py` - IR → Code generation
- [x] `test_xgrammar_generator_with_constraints.py` - With code constraints

### P1 - Week 2 (2 files, 6-8h)
- [ ] `test_optimization_e2e.py` - DSPy MIPROv2/COPRO (⚠️ slow)
- [ ] `test_validation_e2e.py` - Statistical validation (⚠️ slow, 50+ examples)

### P2 - Week 3 (3 files, 4-6h)
- [ ] `test_typescript_e2e.py` - TypeScript generation
- [ ] `test_typescript_quality.py` - TypeScript quality checks
- [ ] `test_robustness_integration.py` - Paraphrasing, equivalence

### P3 - Week 4 (2 files, 4-6h + docs)
- [ ] `test_api_endpoints.py` - API E2E (partial)
- [ ] `test_semantic_generator_lsp.py` - LSP semantic gen (if needed)
- [ ] Update TESTING.md
- [ ] Create migration summary

---

## Files to Keep Mocked (13 files)

**Unit tests disguised as integration tests** - NO MIGRATION NEEDED:

1. ✅ `test_lsp_optimization.py` - LSP logic (cache, metrics, ranking)
2. ✅ `test_multifile_analysis.py` - File discovery
3. ✅ `test_reverse_mode.py` - Static/dynamic analysis (no LLM)
4. ✅ `test_tui_session_management.py` - UI state
5. ✅ `test_cli_session_commands.py` - CLI parsing
6. ✅ `test_session_import.py` - Data serialization
7. ✅ `test_backward_compatibility.py` - Format validation
8. ✅ `test_lsp_context.py` - LSP queries
9. ✅ `test_github_repository_client.py` - External API (use stubs)
10. ✅ `test_response_recording_example.py` - Reference doc
11. Plus 2-3 more non-LLM tests

---

## Common Commands

```bash
# Run integration tests with cache (fast)
uv run pytest tests/integration/ -v -m "real_modal"

# Record new fixtures (slow, requires Modal endpoint)
RECORD_FIXTURES=true uv run pytest tests/integration/ -v -m "real_modal"

# Run specific test file
uv run pytest tests/integration/test_xgrammar_translator.py -v

# Run slow tests only
uv run pytest tests/integration/ -v -m "slow"

# Skip slow tests
uv run pytest tests/integration/ -v -m "not slow"

# Check fixture size
du -sh tests/fixtures/
```

---

## Fixture Locations

```
tests/fixtures/
├── modal_responses.json       # Generic Modal API responses
├── ir_responses.json          # IR-specific responses
└── (split by test file later if needed)
```

---

## Risk Levels

| Risk | Files | Mitigation |
|------|-------|------------|
| **High** | optimization_e2e, validation_e2e | `@pytest.mark.slow`, cache fixtures, scheduled runs |
| **Medium** | xgrammar_*, typescript_* | `temperature=0.0`, validate syntax/AST |
| **Low** | robustness, api_endpoints | Standard caching, straightforward migration |

---

## Success Metrics

| Metric | Before | After (Target) |
|--------|--------|----------------|
| Real Modal Coverage | 0% | 30%+ |
| CI Time (integration) | 30s | <120s |
| Fixture Hit Rate | N/A | 100% |
| LLM Calls in CI | 0 | 0 |
| Developer Confidence | Medium | High |

---

## When to Re-Record Fixtures

**Triggers**:
- Weekly scheduled job (automated)
- Major IR schema change (manual)
- New test cases added (manual)
- Fixture validation fails (manual)

**Process**:
```bash
# Delete old fixtures
rm tests/fixtures/modal_responses.json tests/fixtures/ir_responses.json

# Record fresh
RECORD_FIXTURES=true uv run pytest tests/integration/ -v -m "real_modal"

# Validate
uv run pytest tests/integration/ -v -m "real_modal"  # Should be fast

# Commit
git add tests/fixtures/*.json
git commit -m "Refresh integration test fixtures"
```

---

## Troubleshooting

### Fixture Cache Miss
**Symptom**: Test calls real Modal API even without `RECORD_FIXTURES=true`

**Fix**:
- Check key uniqueness (must be unique per test case)
- Verify fixtures file exists and is readable
- Check metadata matches (some recorders use metadata for key hashing)

### Slow Tests in CI
**Symptom**: CI takes >2 minutes for integration tests

**Fix**:
- Verify fixtures are committed to git
- Check `RECORD_FIXTURES` is not set in CI
- Ensure fixture hit rate is 100% (check logs)

### Fixture Size Too Large
**Symptom**: Git complains about large files

**Fix**:
- Split fixtures by test file (`test_xgrammar_translator_fixtures.json`)
- Compress fixtures (gzip)
- Use git-lfs for large fixtures (>100MB)

### Non-Deterministic Results
**Symptom**: Same test fails/passes randomly

**Fix**:
- Set `temperature=0.0` for deterministic sampling
- Cache first valid response, don't re-record
- Check for test interdependencies (isolation issues)

---

## Quick Links

- **Detailed Plan**: `INTEGRATION_TEST_MIGRATION_PLAN.md`
- **Analysis Summary**: `PHASE_2_3_ANALYSIS_SUMMARY.md`
- **Mock Inventory**: `MOCK_INVENTORY.md`
- **Example Implementation**: `tests/integration/test_response_recording_example.py`
- **Fixture Code**: `tests/fixtures/response_recorder.py` (check conftest.py)

---

## Contact

**Questions?** Check:
1. This quick reference
2. Detailed migration plan (`INTEGRATION_TEST_MIGRATION_PLAN.md`)
3. Example test (`test_response_recording_example.py`)
4. Session state (`SESSION_STATE.md`) for hole-driven development context

---

**Last Updated**: 2025-10-22
