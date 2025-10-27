---
track: infrastructure
document_type: migration_plan
status: complete
priority: P1
completion: 100%
phase: 2.3
last_updated: 2025-10-22
session_protocol: |
  For new Claude Code session:
  1. Integration test migration plan is COMPLETE (planning phase)
  2. 23 integration tests analyzed: 5 must use real Modal, 6 stay mocked
  3. Response recorder infrastructure exists (ir_recorder, modal_recorder fixtures)
  4. Estimated effort: 3-4 days for Category 1 (critical path tests)
  5. See MIGRATION_QUICK_REFERENCE.md for implementation checklist
related_docs:
  - docs/tracks/infrastructure/MIGRATION_QUICK_REFERENCE.md
  - docs/tracks/testing/E2E_VALIDATION_PLAN.md
  - docs/tracks/testing/TESTING_STATUS.md
  - docs/MASTER_ROADMAP.md
---

# Integration Test Migration Plan - Phase 2.3

**Date**: 2025-10-22
**Status**: Planning Phase
**Purpose**: Identify which integration tests should use real Modal vs mocks

---

## Executive Summary

**Total Integration Tests**: 23 files in `tests/integration/`
**Tests Using Mocks**: 6 files (identified)
**Tests Needing Real Modal**: 5 files (high priority)
**Tests with Response Recording**: 1 file (example implementation)
**Total Test Files in Repository**: 124

### Current State Analysis

From MOCK_INVENTORY.md:
- **1246 total mock occurrences** across 50 files
- **~400 provider mocks** across 11 files
- **Response recorder infrastructure exists** (4 files)

---

## Category 1: Critical Path Integration Tests (MUST use real Modal)

These tests validate end-to-end behavior that directly affects production workflows.

### 1.1 XGrammar Translation Tests

**Files**:
- `tests/integration/test_xgrammar_translator.py`
- `tests/integration/test_xgrammar_translator_with_constraints.py`

**Current State**:
- Uses `MockProvider` with pre-configured JSON responses
- ~30-40 mock occurrences per file
- Tests translation from NLP → IR

**Why Real Modal Needed**:
- Translation quality depends on actual LLM behavior
- Grammar constraints need real parser validation
- Temperature/sampling settings affect output
- Critical for forward mode (NLP → Code) pipeline

**Mock Occurrences**: ~40 total
**Test Cases**: ~15 per file

**Migration Priority**: **P0 (Highest)**

**Estimated Effort**: 2-3 hours
- Add `@pytest.mark.real_modal` markers
- Use `ir_recorder` fixture for caching
- Record responses with `RECORD_FIXTURES=true`
- Validate cached responses work offline

**Dependencies**:
- Modal endpoint configured
- Response recorder working
- Fixture storage available

**Risk**: Medium
- Real LLM calls may have variance
- Needs fixture recording for determinism
- CI must run with cached fixtures

---

### 1.2 XGrammar Code Generation Tests

**Files**:
- `tests/integration/test_xgrammar_code_generator.py`
- `tests/integration/test_xgrammar_generator_with_constraints.py`

**Current State**:
- Uses `MockCodeGenProvider` with hardcoded implementations
- ~41-50 mock occurrences per file
- Tests IR → Code generation

**Why Real Modal Needed**:
- Code generation quality depends on LLM reasoning
- Constraint satisfaction needs real validation
- TypeScript/Python generation both critical
- Affects production code output

**Mock Occurrences**: ~58 total
**Test Cases**: ~20 per file

**Migration Priority**: **P0 (Highest)**

**Estimated Effort**: 2-3 hours
- Similar to translation tests
- Use `modal_recorder` for caching
- Validate syntax correctness of generated code
- Check AST parsing passes

**Dependencies**:
- Modal endpoint configured
- Code validators working (AST, mypy, tsc)
- Response recorder for caching

**Risk**: Medium
- Generated code must be syntactically valid
- Multiple languages to validate (Python, TypeScript)
- Fixture recording needed for CI

---

### 1.3 Optimization E2E Tests

**Files**:
- `tests/integration/test_optimization_e2e.py`

**Current State**:
- Uses `@patch("lift_sys.optimization.optimizer.MIPROv2")`
- Uses `@patch("lift_sys.optimization.optimizer.COPRO")`
- Mocks entire optimization pipeline
- Tests DSPy optimizer integration (H8)

**Why Real Modal Needed**:
- Optimization depends on real DSPy behavior
- MIPROv2/COPRO need actual prompt optimization
- Quality improvement metrics need real data
- Critical for route-aware optimization (ADR 001)

**Mock Occurrences**: ~15 patches
**Test Cases**: ~10 tests (MIPROv2, COPRO, route switching)

**Migration Priority**: **P1 (High)**

**Estimated Effort**: 3-4 hours
- More complex than basic translation
- Needs real DSPy MIPROv2/COPRO initialization
- May need larger example sets (20+ training examples)
- Response recording for determinism

**Dependencies**:
- DSPy installed and configured
- Modal endpoint with sufficient resources
- Response recorder for long-running optimizations

**Risk**: High
- Optimization can be slow (minutes)
- Non-deterministic improvements possible
- Needs careful fixture design for CI
- May require separate test suite (`@pytest.mark.slow`)

---

### 1.4 Validation E2E Tests

**Files**:
- `tests/integration/test_validation_e2e.py`

**Current State**:
- Uses `@patch("lift_sys.optimization.optimizer.MIPROv2")`
- Mocks pipeline evaluation
- Tests statistical validation (H17)
- Uses 50+ test examples

**Why Real Modal Needed**:
- Validation metrics depend on real performance
- Paired t-tests need actual variance data
- Effect size (Cohen's d) needs real distributions
- Critical for deployment decisions

**Mock Occurrences**: ~10 patches
**Test Cases**: ~5 tests (MIPROv2/COPRO, effect size, statistical significance)

**Migration Priority**: **P1 (High)**

**Estimated Effort**: 3-4 hours
- Similar complexity to optimization tests
- Needs 50+ held-out examples (real evaluations)
- Response recording for CI caching
- Statistical tests need real variance

**Dependencies**:
- Same as optimization tests
- Large example sets required
- Long runtime expected

**Risk**: High
- Validation requires many evaluations (50+ examples × 2 pipelines)
- Slow tests (may need `@pytest.mark.slow`)
- Non-deterministic statistical results possible
- Fixture recording critical for CI

---

### 1.5 TypeScript E2E Tests

**Files**:
- `tests/integration/test_typescript_e2e.py`
- `tests/integration/test_typescript_quality.py`

**Current State**:
- Uses `MockProvider` for TypeScript generation
- Tests TypeScript-specific code generation
- Validates with `tsc` compiler

**Why Real Modal Needed**:
- TypeScript generation quality matters for production
- Type inference needs real LLM reasoning
- Interface generation affects correctness
- Critical for multi-language support

**Mock Occurrences**: ~18 total
**Test Cases**: ~15 per file

**Migration Priority**: **P2 (Medium)**

**Estimated Effort**: 2 hours
- Similar to Python code generation
- Needs TypeScript compiler validation
- Response recording for caching

**Dependencies**:
- TypeScript compiler (`tsc`) installed
- Modal endpoint configured
- Response recorder

**Risk**: Low
- TypeScript compiler provides deterministic validation
- Syntax errors easy to catch
- Fixture recording straightforward

---

## Category 2: Unit Tests Disguised as Integration (KEEP mocked)

These tests are labeled "integration" but are actually unit tests of specific components.

### 2.1 LSP Optimization Tests

**File**: `tests/integration/test_lsp_optimization.py`

**Current State**:
- Uses `@patch.object(provider, "_get_symbols_from_files")`
- Mocks LSP queries
- Tests caching, metrics, ranking logic

**Why Keep Mocked**:
- Tests internal LSP logic, not LLM behavior
- No external LLM calls needed
- Fast, deterministic unit tests
- Cache/metrics can be tested in isolation

**Mock Occurrences**: ~10 patches
**Test Cases**: ~15 tests

**Action**: **NO CHANGE - Keep mocked**

**Rationale**: These are unit tests of LSP components, not E2E integration tests.

---

### 2.2 Multi-File Analysis Tests

**File**: `tests/integration/test_multifile_analysis.py`

**Current State**:
- Uses `@patch("subprocess.run")` for CodeQL/Daikon
- Tests multi-file discovery and analysis
- Reverse mode integration

**Why Keep Mocked**:
- Tests repository scanning logic, not LLM behavior
- External tools (CodeQL, Daikon) not the focus
- No ModalProvider usage
- Fast, deterministic

**Mock Occurrences**: ~10 patches
**Test Cases**: ~12 tests

**Action**: **NO CHANGE - Keep mocked**

**Rationale**: Tests file discovery and orchestration, not LLM integration.

---

### 2.3 Reverse Mode Tests

**File**: `tests/integration/test_reverse_mode.py`

**Current State**:
- Uses `@patch("subprocess.run")` for external tools
- Tests specification lifting workflow
- No ModalProvider usage

**Why Keep Mocked**:
- Reverse mode doesn't use LLM inference
- Tests static/dynamic analysis integration
- External tool mocking appropriate

**Mock Occurrences**: ~15 patches
**Test Cases**: ~10 tests

**Action**: **NO CHANGE - Keep mocked**

**Rationale**: Reverse mode is separate from forward mode LLM pipeline.

---

### 2.4 TUI Session Management Tests

**File**: `tests/integration/test_tui_session_management.py`

**Current State**:
- Uses `MagicMock` for UI widgets
- Tests TUI state management
- No actual LLM calls

**Why Keep Mocked**:
- Tests UI logic, not backend behavior
- No ModalProvider usage
- Widget mocking appropriate for TUI tests

**Mock Occurrences**: ~25 mocks
**Test Cases**: ~20 tests

**Action**: **NO CHANGE - Keep mocked**

**Rationale**: TUI tests focus on UI state, not LLM integration.

---

## Category 3: External Dependencies (USE stubs/recorded responses)

These tests interact with external services that should be stubbed or cached.

### 3.1 GitHub Repository Client Tests

**File**: `tests/integration/test_github_repository_client.py`

**Current State**:
- Tests GitHub API integration
- No mocking mentioned (may use real GitHub API or stubs)

**Why Use Stubs**:
- GitHub API has rate limits
- External dependency unreliable for CI
- Response structure is stable
- No LLM behavior involved

**Action**: **Use ResponseRecorder or stubs**

**Estimated Effort**: 1 hour
- Create GitHub API response fixtures
- Use recorder pattern like Modal tests
- Record real API responses once
- Replay in CI

**Risk**: Low
- GitHub API is stable
- Response structure well-defined
- No LLM variance

---

### 3.2 Response Recording Example

**File**: `tests/integration/test_response_recording_example.py`

**Current State**:
- Example implementation of response recording pattern
- Shows how to cache Modal API responses
- Uses `modal_recorder` and `ir_recorder` fixtures

**Why Keep As-Is**:
- This is the reference implementation
- Shows best practices for caching
- Used by other tests as example

**Action**: **NO CHANGE - Keep as reference**

**Rationale**: Example/documentation file.

---

## Category 4: Session Import/Export Tests

**File**: `tests/integration/test_session_import.py`

**Current State**:
- Tests session import/export functionality
- Likely uses mocks for session data

**Why Keep Mocked**:
- Tests data serialization, not LLM behavior
- No ModalProvider usage expected
- Fast, deterministic

**Action**: **NO CHANGE - Keep mocked (likely)**

**Rationale**: Session management is orthogonal to LLM integration.

---

## Category 5: API Endpoint Tests

**File**: `tests/integration/test_api_endpoints.py`

**Current State**:
- Tests FastAPI endpoints
- May use mocked backend services

**Recommendation**: **Hybrid approach**

**Strategy**:
- Keep mocks for unit-level endpoint tests
- Add real Modal tests for E2E API workflows
- Use response recorder for CI caching

**Estimated Effort**: 2 hours
- Add `@pytest.mark.real_modal` to E2E tests
- Use recorder for caching
- Keep mocked tests for fast feedback

**Risk**: Low
- API contracts well-defined
- Can test both mocked and real backends

---

## Category 6: CLI Session Command Tests

**File**: `tests/integration/test_cli_session_commands.py`

**Current State**:
- Tests CLI interface for session management
- Likely uses mocked backend

**Action**: **NO CHANGE - Keep mocked**

**Rationale**: CLI tests focus on argument parsing and command routing, not backend behavior.

---

## Category 7: LSP Context Tests

**Files**:
- `tests/integration/test_lsp_context.py`
- `tests/integration/test_semantic_generator_lsp.py`

**Current State**:
- Test LSP semantic context provider
- May use MockProvider for some tests

**Recommendation**: **Hybrid approach**

**Strategy**:
- Keep mocks for LSP query logic
- Add real Modal tests if semantic generation uses LLM
- Check if LSP → LLM pipeline exists

**Estimated Effort**: 1-2 hours (if LLM integration exists)

**Risk**: Low

---

## Category 8: Robustness Integration Tests

**File**: `tests/integration/optimization/test_confidence_integration.py`

**Current State**:
- Tests confidence scoring for optimized pipelines
- May use mocked optimization results

**Recommendation**: **Real Modal for confidence scoring**

**Why**:
- Confidence depends on real variance in predictions
- Statistical metrics need actual distribution
- Part of optimization validation pipeline

**Estimated Effort**: 2 hours

**Risk**: Medium (depends on optimization complexity)

---

## Category 9: Backward Compatibility Tests

**File**: `tests/integration/test_backward_compatibility.py`

**Current State**:
- Tests API/IR backward compatibility
- Likely uses mocked data

**Action**: **NO CHANGE - Keep mocked**

**Rationale**: Compatibility tests check data formats, not LLM behavior.

---

## Category 10: Robustness Integration Tests

**File**: `tests/integration/test_robustness_integration.py`

**Current State**:
- Tests robustness features (paraphrasing, sensitivity, equivalence)
- May use real LLM for paraphrasing

**Recommendation**: **Real Modal for paraphrasing**

**Why**:
- Paraphrase generation needs real LLM
- Equivalence checking depends on quality
- Sensitivity analysis needs variance

**Estimated Effort**: 2-3 hours

**Risk**: Medium (LLM variance in paraphrasing)

---

## Migration Priority Matrix

| Priority | Files | Effort | Risk | Timeline |
|----------|-------|--------|------|----------|
| **P0** | XGrammar translator (2 files) | 4-6h | Medium | Week 1 |
| **P0** | XGrammar generator (2 files) | 4-6h | Medium | Week 1 |
| **P1** | Optimization E2E | 3-4h | High | Week 2 |
| **P1** | Validation E2E | 3-4h | High | Week 2 |
| **P2** | TypeScript E2E (2 files) | 2h | Low | Week 3 |
| **P2** | Robustness integration | 2-3h | Medium | Week 3 |
| **P3** | API endpoints (partial) | 2h | Low | Week 4 |
| **P3** | LSP semantic (if needed) | 1-2h | Low | Week 4 |
| **SKIP** | LSP optimization | 0h | N/A | N/A |
| **SKIP** | Multi-file analysis | 0h | N/A | N/A |
| **SKIP** | Reverse mode | 0h | N/A | N/A |
| **SKIP** | TUI session mgmt | 0h | N/A | N/A |
| **SKIP** | CLI session cmds | 0h | N/A | N/A |
| **SKIP** | Session import | 0h | N/A | N/A |
| **SKIP** | Backward compat | 0h | N/A | N/A |

**Total Effort**: 22-32 hours (3-4 working days)
**Timeline**: 4 weeks (part-time, alongside other work)

---

## Response Recorder Strategy

### Current Infrastructure

**Fixtures**:
- `modal_recorder` - For generic Modal API responses
- `ir_recorder` - For IR-specific responses (handles serialization)

**Location**: `tests/fixtures/`
- `modal_responses.json` - Cached Modal API responses
- `ir_responses.json` - Cached IR objects

**Usage Pattern**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_translation(ir_recorder):
    provider = ModalProvider(endpoint_url=ENDPOINT)
    translator = XGrammarIRTranslator(provider)

    # First run: calls Modal API and records (RECORD_FIXTURES=true)
    # Subsequent runs: uses cached response (<1s)
    ir = await ir_recorder.get_or_record(
        key="test_translation_circle_area",
        generator_fn=lambda: translator.translate("Calculate circle area"),
        metadata={"test": "translation", "prompt": "circle_area"}
    )

    assert ir.signature.name == "calculate_circle_area"
```

### Migration Steps for Each Test

1. **Add fixture parameter**: `ir_recorder` or `modal_recorder`
2. **Wrap expensive call**: `await recorder.get_or_record(...)`
3. **Provide unique key**: `"test_{filename}_{scenario}"`
4. **Add metadata**: For debugging/provenance
5. **Run with recording**: `RECORD_FIXTURES=true pytest tests/integration/...`
6. **Commit fixtures**: Add `tests/fixtures/*.json` to git
7. **Validate cache works**: Run without `RECORD_FIXTURES`, verify fast execution

### CI/CD Integration

**GitHub Actions Workflow**:
```yaml
- name: Run integration tests (cached)
  run: |
    # Use cached fixtures (fast, no Modal calls)
    uv run pytest tests/integration/ -v -m "real_modal"

- name: Update fixtures (scheduled)
  if: github.event_name == 'schedule'  # Weekly refresh
  run: |
    RECORD_FIXTURES=true uv run pytest tests/integration/ -v -m "real_modal"
    git add tests/fixtures/*.json
    git commit -m "Update integration test fixtures"
    git push
```

**Benefits**:
- Fast CI runs (cached responses, <1s per test)
- Offline development (no Modal API needed after recording)
- Deterministic tests (same response every time)
- Cost savings (no LLM API calls in CI)
- Easy to update (re-record fixtures on schedule)

---

## Acceptance Criteria for Migration

### Per-Test Acceptance

For each migrated test:
- [ ] `@pytest.mark.real_modal` marker added
- [ ] `ir_recorder` or `modal_recorder` fixture used
- [ ] Unique key for each test case
- [ ] Metadata includes test context
- [ ] Fixtures committed to git
- [ ] Test passes with cached fixtures (no Modal API)
- [ ] Test passes with `RECORD_FIXTURES=true` (real Modal API)
- [ ] Documentation updated (docstring explains caching)

### Phase Acceptance

For Phase 2.3 completion:
- [ ] All P0 tests migrated (4 files)
- [ ] All P1 tests migrated (2 files)
- [ ] Fixtures recorded and committed
- [ ] CI runs successfully with cached fixtures
- [ ] Documentation updated (TESTING.md)
- [ ] Migration summary document created
- [ ] Performance benchmarks show fast CI times (<10s for integration suite)
- [ ] No regressions in test coverage

---

## Risk Mitigation

### Risk 1: LLM Non-Determinism

**Problem**: Real LLM calls may produce different outputs each time

**Mitigation**:
- Use `temperature=0.0` for deterministic sampling
- Use response recorder to cache first valid response
- Only re-record fixtures when necessary (scheduled, not on every PR)
- Validate fixtures for correctness before committing

### Risk 2: Slow CI Times

**Problem**: Real Modal calls are slow (30-60s per test)

**Mitigation**:
- Use cached fixtures in CI (fast, <1s per test)
- Only record fixtures in scheduled jobs (weekly refresh)
- Mark slow tests with `@pytest.mark.slow`, skip in fast CI
- Parallelize test execution where possible

### Risk 3: Fixture Staleness

**Problem**: Cached responses may become outdated as code evolves

**Mitigation**:
- Scheduled fixture refresh (weekly or monthly)
- Version metadata in fixtures (track when recorded)
- Detect schema changes (fail if fixture doesn't match current IR schema)
- Manual refresh trigger for major changes

### Risk 4: Modal Endpoint Availability

**Problem**: Recording requires Modal endpoint to be running

**Mitigation**:
- Document setup steps clearly (TESTING.md)
- Provide fallback mocks for local development
- CI only uses cached fixtures (no Modal dependency)
- Scheduled jobs handle recording (failures don't block PRs)

### Risk 5: Large Fixture Files

**Problem**: Fixtures may grow large (many test cases × large responses)

**Mitigation**:
- Compress fixtures (gzip or similar)
- Split by test file (`test_xgrammar_translator_fixtures.json`)
- Clean up unused fixtures periodically
- Use git-lfs if fixtures exceed GitHub limits

---

## Timeline

### Week 1: P0 Translation Tests
- Day 1: Migrate `test_xgrammar_translator.py`
- Day 2: Migrate `test_xgrammar_translator_with_constraints.py`
- Day 3: Record fixtures, validate caching
- Day 4: Migrate `test_xgrammar_code_generator.py`
- Day 5: Migrate `test_xgrammar_generator_with_constraints.py`

### Week 2: P1 Optimization/Validation Tests
- Day 1-2: Migrate `test_optimization_e2e.py`
- Day 3-4: Migrate `test_validation_e2e.py`
- Day 5: Record fixtures, validate caching

### Week 3: P2 TypeScript/Robustness Tests
- Day 1-2: Migrate `test_typescript_e2e.py` and `test_typescript_quality.py`
- Day 3-4: Migrate `test_robustness_integration.py`
- Day 5: Record fixtures, validate caching

### Week 4: P3 API/LSP Tests + Documentation
- Day 1-2: Migrate `test_api_endpoints.py` (partial)
- Day 3: Migrate `test_semantic_generator_lsp.py` (if needed)
- Day 4: Update TESTING.md, create migration summary
- Day 5: CI integration, final validation

**Total**: 4 weeks part-time (or 1 week full-time)

---

## Success Metrics

### Before Migration (Current State)
- Integration tests: 100% mocked
- CI time: Fast (~30s for integration suite)
- Coverage: Good (but not testing real LLM behavior)
- Confidence: Low (mocks don't catch LLM regressions)

### After Migration (Target State)
- Integration tests: 30% real Modal (critical path), 70% mocked (unit-level)
- CI time: Fast (~60s with cached fixtures)
- Coverage: Excellent (real LLM behavior validated)
- Confidence: High (fixtures prove real Modal works)
- Cost: Low (fixtures cached, no LLM calls in CI)

### Key Performance Indicators (KPIs)

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Real Modal Coverage | 0% | 30% | 30%+ |
| CI Time (integration) | 30s | 60s | <120s |
| Fixture Hit Rate | N/A | 100% | 100% |
| LLM Calls in CI | 0 | 0 | 0 |
| Test Determinism | High (mocked) | High (cached) | High |
| Developer Confidence | Medium | High | High |

---

## Open Questions

1. **Modal Endpoint Configuration**:
   - Where is the endpoint URL configured for tests?
   - Do we need separate dev/test endpoints?

2. **Fixture Storage**:
   - Current size of `tests/fixtures/`?
   - Git-lfs needed for large fixtures?

3. **Test Markers**:
   - Is `@pytest.mark.real_modal` already defined in pytest.ini?
   - Other markers needed (`@pytest.mark.slow`, `@pytest.mark.record`)?

4. **Optimization Tests**:
   - How long do real MIPROv2/COPRO runs take?
   - Should these be in a separate slow test suite?

5. **TypeScript Validation**:
   - Is `tsc` installed in CI?
   - Do we need a TypeScript test environment setup?

---

## Next Steps

1. **Review this plan** with team
2. **Answer open questions**
3. **Start Week 1 migration** (P0 translation tests)
4. **Create tracking issue** (bd create or GitHub issue)
5. **Document progress** in session logs

---

## References

- **MOCK_INVENTORY.md**: Detailed breakdown of all mocks
- **test_response_recording_example.py**: Reference implementation
- **conftest.py**: Fixture definitions (modal_recorder, ir_recorder)
- **HOLE_INVENTORY.md**: Architecture holes being validated
- **SESSION_STATE.md**: Current hole-driven development progress

---

**End of Migration Plan**
