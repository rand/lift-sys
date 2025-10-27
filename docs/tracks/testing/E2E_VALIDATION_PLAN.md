---
track: testing
document_type: validation_plan
status: planning
priority: P2
completion: 20%
last_updated: 2025-10-22
session_protocol: |
  For new Claude Code session:
  1. Use this document for planning real Modal integration testing
  2. Mock inventory: 1246 mock occurrences across 50 files
  3. Current focus: DSPy architecture validation (Phases 1-3 complete)
  4. Future: Replace critical path mocks with real Modal calls
related_docs:
  - docs/tracks/testing/E2E_TEST_SCENARIOS.md
  - docs/tracks/testing/TESTING_STATUS.md
  - docs/tracks/infrastructure/INFRASTRUCTURE_STATUS.md
---

# End-to-End Validation Plan: Replacing Mocks with Real Modal Integration

**Date**: 2025-10-22
**Status**: Planning → Implementation
**Owner**: Architecture Team
**Estimated Timeline**: 2-3 weeks

---

## Executive Summary

**Problem**: Recent work has implemented DSPy + Pydantic AI architecture (holes H1-H19) but has NOT validated against real Modal/XGrammar infrastructure. Tests use extensive mocking (1246 mock occurrences across 50 files), creating a disconnect between "implemented" and "validated."

**Goal**: Replace all mocks/stubs with real end-to-end implementations, validate against Modal XGrammar constrained generation, and establish performance baseline.

**Success Criteria**:
- ✅ 100% of integration tests run against real Modal endpoint
- ✅ Performance meets or exceeds baseline (47s p50 latency, 100% success rate)
- ✅ XGrammar constrained generation validated for all IR schemas
- ✅ Observability in place for debugging and optimization
- ✅ No regressions in test success rate

---

## Phase 1: Audit & Configuration (Week 1, Days 1-2)

### 1.1 Mock/Stub Inventory

**Current State**:
- **1246 mock occurrences** across 50 test files
- **Mock categories identified**:
  - Provider mocks (ModalProvider, AnthropicProvider): ~400 occurrences
  - DSPy signature mocks (test_provider_adapter.py): ~100 occurrences
  - Database mocks (Supabase): ~150 occurrences
  - GitHub client stubs (_StubGitHubClient): ~50 occurrences
  - File system/session mocks: ~200 occurrences
  - Response recorders (cached fixtures): ~100 occurrences
  - Miscellaneous (CLI, TUI, orchestrator): ~246 occurrences

**Action Items**:
- [ ] Create detailed mock inventory by component (see Appendix A)
- [ ] Categorize mocks by replacement strategy (real API, fixture, leave mocked)
- [ ] Identify dependencies between mocked components
- [ ] Document which mocks are **critical path** (block real validation)

**Deliverable**: `docs/planning/MOCK_INVENTORY.md` with full breakdown

---

### 1.2 Modal Endpoint Configuration

**Current Deployment**:
- ✅ Modal app deployed: `lift-sys-inference` (ap-ibeiutbqDfhjaNJUokFMu7)
- ✅ Endpoints available:
  - Health: https://rand--health-dev.modal.run
  - Generate: https://rand--generate-dev.modal.run
- ❌ Local .env.local NOT configured with endpoint URL
- ✅ Model: Qwen2.5-Coder-32B-Instruct (upgraded from 7B)
- ✅ Backend: vLLM 0.9.2 + XGrammar (native support)

**Action Items**:
- [ ] Get production endpoint URLs: `modal app list`
- [ ] Add to .env.local:
  ```bash
  MODAL_ENDPOINT_URL=https://rand--generate.modal.run
  MODAL_HEALTH_URL=https://rand--health.modal.run
  ```
- [ ] Test connectivity: `curl https://rand--health.modal.run`
- [ ] Verify XGrammar support with test schema
- [ ] Measure cold start (first call) vs warm latency
- [ ] Document endpoint behavior in `docs/MODAL_ENDPOINTS.md`

**Deliverable**: Working Modal connection with documented performance characteristics

---

### 1.3 Baseline Performance Measurement

**Historical Baseline** (from docs/benchmarks/SERIAL_BENCHMARK_ANALYSIS.md):
- Success rate: **100%** (10/10 tests)
- Median latency: **47.04s**
- Mean latency: **68.28s**
- Cost per test: **~$0.011**
- Model: Qwen2.5-Coder-7B-Instruct (older)

**New Baseline Requirements**:
- Re-run with **Qwen2.5-Coder-32B-Instruct** (current deployment)
- Measure with **real Modal calls** (not cached responses)
- Capture **detailed telemetry**:
  - Modal cold start time
  - Model inference time
  - Network latency
  - Token usage
  - XGrammar constraint application time

**Action Items**:
- [ ] Run benchmark suite: `./scripts/benchmarks/run_benchmark.sh --real-modal`
- [ ] Document new baseline in `docs/benchmarks/BASELINE_32B_20251022.md`
- [ ] Compare against 7B baseline (expect higher quality, longer latency)
- [ ] Establish regression thresholds (e.g., <30% latency increase)

**Deliverable**: New performance baseline with 32B model

---

## Phase 2: Provider Integration (Week 1, Days 3-5)

### 2.1 ModalProvider Real Implementation

**Current State**:
- ✅ `lift_sys/providers/modal_provider.py` exists
- ✅ Implements `generate_text()` and `generate_structured()`
- ❌ Extensive mocking in tests (no real validation)
- ❌ No integration tests with real Modal endpoint

**Replacement Strategy**:

1. **Update ModalProvider configuration**:
   ```python
   # lift_sys/providers/modal_provider.py
   import os

   class ModalProvider(BaseProvider):
       def __init__(self, endpoint_url: str | None = None):
           # Use env var with fallback to deployed endpoint
           self.endpoint_url = endpoint_url or os.getenv(
               "MODAL_ENDPOINT_URL",
               "https://rand--generate.modal.run"
           )
   ```

2. **Add real integration tests**:
   ```python
   # tests/integration/test_modal_provider_real.py
   @pytest.mark.integration
   @pytest.mark.real_modal  # New marker for tests requiring Modal
   async def test_modal_provider_xgrammar_constrained():
       """Test real Modal endpoint with XGrammar constraints."""
       provider = ModalProvider()
       await provider.initialize()

       schema = IRSchema.model_json_schema()
       result = await provider.generate_structured(
           prompt="Create a function to add two numbers",
           schema=schema,
           max_tokens=2048
       )

       # Validate structure matches schema
       assert "intent" in result
       assert "signature" in result
       # Validate XGrammar enforced constraints
       assert re.match(r'^[a-z_][a-z0-9_]*$', result["signature"]["name"])
   ```

3. **Response recording for CI/CD**:
   - Use existing `ResponseRecorder` fixture
   - First run: `RECORD_FIXTURES=true pytest -m real_modal` (hits Modal)
   - Subsequent runs: Use cached responses (fast CI)
   - Periodic refresh: Re-record fixtures weekly

**Action Items**:
- [ ] Implement ModalProvider configuration updates
- [ ] Create `tests/integration/test_modal_provider_real.py`
- [ ] Add `@pytest.mark.real_modal` marker to pytest config
- [ ] Run with `RECORD_FIXTURES=true` to create fixture cache
- [ ] Validate fixture cache works for CI (offline tests)
- [ ] Document provider behavior in `docs/providers/MODAL_PROVIDER.md`

**Acceptance Criteria**:
- ✅ Real Modal endpoint successfully generates IR with XGrammar constraints
- ✅ Test suite has both real and cached modes
- ✅ Latency within expected range (2-60s depending on cold/warm)
- ✅ Token usage tracked and logged

**Deliverable**: Working ModalProvider with real integration tests

---

### 2.2 DSPy ProviderAdapter Integration (H1)

**Current State**:
- ✅ H1 (ProviderAdapter) implemented: `lift_sys/dspy_signatures/provider_adapter.py`
- ✅ Supports dual routing (ADR 001):
  - Route 1: Best Available (Anthropic/OpenAI/Google)
  - Route 2: Modal Inference (XGrammar/llguidance/aici)
- ❌ Only tested with mocked providers
- ❌ No validation of route selection logic

**Replacement Strategy**:

1. **Test Route 2 (Modal) with real endpoint**:
   ```python
   # tests/integration/test_provider_adapter_real.py
   @pytest.mark.integration
   @pytest.mark.real_modal
   async def test_provider_adapter_modal_route():
       """Test ProviderAdapter routes to Modal for XGrammar."""
       modal_provider = ModalProvider()
       await modal_provider.initialize()

       adapter = ProviderAdapter(modal_provider)

       # Provide schema to trigger Modal route
       schema = IRSchema.model_json_schema()
       result = await adapter(
           prompt="Create add function",
           schema=schema  # Should trigger Modal route
       )

       # Verify route selection
       assert adapter._last_route == ProviderRoute.MODAL_INFERENCE
       # Verify result is dspy.Prediction
       assert isinstance(result, dspy.Prediction)
   ```

2. **Test Route 1 (Best Available) with real provider**:
   - Use Anthropic or OpenAI (whichever has API key configured)
   - Validate standard DSPy calls work without XGrammar

**Action Items**:
- [ ] Implement route tracking (`_last_route` property) in ProviderAdapter
- [ ] Create integration tests for both routes
- [ ] Test route selection criteria (schema present → Modal, otherwise → Best Available)
- [ ] Measure latency difference between routes
- [ ] Document routing behavior in `docs/dspy/PROVIDER_ADAPTER_ROUTING.md`

**Acceptance Criteria**:
- ✅ ProviderAdapter correctly routes to Modal for XGrammar requests
- ✅ ProviderAdapter correctly routes to Best Available for standard requests
- ✅ Both routes return valid dspy.Prediction objects
- ✅ Resource tracking works (token usage, LLM call counts)

**Deliverable**: Validated ProviderAdapter with real dual-route implementation

---

## Phase 3: DSPy Signature Validation (Week 2, Days 1-3)

### 3.1 Hole Validation Strategy

**Holes to Validate** (H1-H19):

| Hole | Component | Validation Method |
|------|-----------|-------------------|
| H6 | NodeSignatureInterface | Integration test with real DSPy modules |
| H9 | ValidationHooks | Test with real RunContext and validation |
| H14 | ResourceLimits | Test resource enforcement with real Modal calls |
| H1 | ProviderAdapter | Dual-route testing (covered in Phase 2.2) |
| H2 | StatePersistence | Real Supabase database tests |
| H11 | ExecutionHistorySchema | Real Supabase execution tracking |
| H10 | OptimizationMetrics | Real IR/code quality measurement |
| H8 | OptimizationAPI | Real MIPROv2/COPRO optimization runs |
| H17 | OptimizationValidation | Statistical validation with real data |
| H12 | ConfidenceCalibration | Real calibration curve with Modal data |
| H3-H7, H13, H15-H16, H18-H19 | Various | Integration tests as appropriate |

**Action Items**:
- [ ] For each hole, create `tests/integration/test_h{N}_real.py`
- [ ] Use real dependencies (Modal, Supabase, etc.)
- [ ] Validate acceptance criteria from HOLE_INVENTORY.md
- [ ] Document any gaps or failures
- [ ] Update SESSION_STATE.md with validation status

**Deliverable**: Integration test suite for all 19 holes

---

### 3.2 Critical Path Validation (H6 → H1 → H10 → H8 → H17)

**Why Critical**: These holes form the backbone of the DSPy architecture. Failure here blocks everything else.

**Validation Plan**:

1. **H6 (NodeSignatureInterface)**:
   ```python
   # Test real DSPy module execution
   @pytest.mark.real_modal
   async def test_h6_real_dspy_execution():
       provider = ModalProvider()
       adapter = ProviderAdapter(provider)
       dspy.settings.configure(lm=adapter)

       # Create node using H6 interface
       class TranslateNode(AbstractBaseNode[AppState]):
           async def run(self, state: AppState, context: RunContext):
               signature = dspy.ChainOfThought(PromptToIR)
               result = await signature(prompt=state.user_prompt)
               return End()  # Terminal node

       # Execute with real state
       node = TranslateNode()
       state = AppState(user_prompt="Add two numbers")
       context = RunContext(...)
       result = await node.run(state, context)

       # Validate provenance tracking works
       assert context.provenance.node_executions > 0
   ```

2. **H1 → H10 → H8 chain**:
   - Test that ProviderAdapter metrics flow to H10 (OptimizationMetrics)
   - Test that H10 metrics are used by H8 (OptimizationAPI)
   - Validate route-aware cost/quality tracking works

3. **H17 (OptimizationValidation)**:
   - Run real optimization experiment
   - Validate statistical significance with paired t-test
   - Ensure p < 0.05 and effect size d > 0.2

**Action Items**:
- [ ] Implement critical path integration test: `test_critical_path_e2e.py`
- [ ] Run with real Modal and validate end-to-end flow
- [ ] Measure latency at each stage
- [ ] Document any bottlenecks or issues

**Acceptance Criteria**:
- ✅ Full critical path executes without errors
- ✅ Provenance tracking captures all executions
- ✅ Metrics flow correctly through pipeline
- ✅ Optimization produces measurable improvement

**Deliverable**: Validated critical path with real infrastructure

---

## Phase 4: End-to-End Pipeline Validation (Week 2, Days 4-5)

### 4.1 Full NLP → IR → Code Pipeline

**Pipeline Stages**:
1. **Input**: Natural language prompt
2. **Translation**: NLP → IR (via BestOfNIRTranslator + ModalProvider)
3. **Validation**: IR validation (schema, constraints, IR interpreter)
4. **Generation**: IR → Code (via TemplatedCodeGenerator)
5. **Validation**: Code validation (syntax, AST, execution)
6. **Output**: Executable Python code

**Integration Test**:
```python
@pytest.mark.e2e
@pytest.mark.real_modal
async def test_full_pipeline_real():
    """Test complete NLP → IR → Code pipeline with real Modal."""
    # Setup
    provider = ModalProvider()
    translator = BestOfNIRTranslator(provider, n_candidates=3)
    generator = TemplatedCodeGenerator()

    # Input
    prompt = """
    Create a function called find_max that takes a list of numbers
    and returns the maximum value. If the list is empty, return None.
    """

    # Stage 1: NLP → IR
    ir = await translator.translate(prompt)
    assert ir is not None
    assert ir.signature.name == "find_max"

    # Stage 2: IR Validation
    validate_ir(ir)  # Should not raise

    # Stage 3: IR → Code
    code = generator.generate(ir)
    assert "def find_max" in code

    # Stage 4: Code Validation
    validate_code(code)  # Syntax, AST checks

    # Stage 5: Execution Test
    result = execute_code(code, [
        {"numbers": [3, 1, 4, 1, 5]},  # Expected: 5
        {"numbers": []},                # Expected: None
    ])
    assert result[0] == 5
    assert result[1] is None
```

**Action Items**:
- [ ] Create `tests/e2e/test_full_pipeline_real.py`
- [ ] Test with 10 diverse prompts (simple → complex)
- [ ] Measure end-to-end latency breakdown
- [ ] Compare success rate to baseline (target: 100%)
- [ ] Document failures and create beads for fixes

**Acceptance Criteria**:
- ✅ 100% success rate on 10 test prompts
- ✅ Median latency <60s (allowing for 32B model increase)
- ✅ All validation stages pass
- ✅ Generated code executes correctly

**Deliverable**: Validated end-to-end pipeline with real Modal

---

### 4.2 Robustness Testing

**Robustness Tools** (from lift_sys/robustness/):
- **EquivalenceChecker**: Verify semantic equivalence of IR/code variants
- **IRVariantGenerator**: Generate naming/effect/assertion variants
- **ParaphraseGenerator**: Generate prompt paraphrases (requires spaCy - currently failing)

**Robustness Test Plan**:
1. Generate 5 paraphrases of prompt
2. Translate each to IR with real Modal
3. Check IR equivalence (should be semantically equivalent)
4. Generate code from each IR
5. Check code equivalence (execution on test inputs)

**Action Items**:
- [ ] Fix spaCy model loading issue (blocking ParaphraseGenerator tests)
- [ ] Create `tests/e2e/test_robustness_real.py`
- [ ] Run robustness tests with real Modal on 5 prompts
- [ ] Measure robustness metrics:
  - IR equivalence rate (target: >80%)
  - Code equivalence rate (target: >90%)
  - Prompt sensitivity (variance in quality)
- [ ] Document robustness results in `docs/benchmarks/ROBUSTNESS_32B_20251022.md`

**Acceptance Criteria**:
- ✅ ParaphraseGenerator works with spaCy
- ✅ IR equivalence >80% across paraphrases
- ✅ Code equivalence >90% across paraphrases
- ✅ Robustness metrics documented

**Deliverable**: Robustness validation with real infrastructure

---

## Phase 5: Observability & Monitoring (Week 3, Days 1-2)

### 5.1 Tracing Infrastructure

**Current State**:
- ❌ No distributed tracing
- ❌ No structured logging for Modal calls
- ❌ No latency breakdown visibility

**Target State**:
- ✅ Trace every LLM call (Modal, Anthropic, etc.)
- ✅ Measure latency at each pipeline stage
- ✅ Track token usage and costs
- ✅ Log XGrammar constraint application
- ✅ Capture errors and retries

**Implementation**:
1. **Structured logging**:
   ```python
   import structlog

   logger = structlog.get_logger()

   async def generate_structured(self, prompt, schema, **kwargs):
       with logger.contextualize(
           provider="modal",
           operation="generate_structured",
           schema_size=len(json.dumps(schema)),
       ):
           start = time.perf_counter()
           result = await self._call_modal(prompt, schema, **kwargs)
           latency = time.perf_counter() - start

           logger.info(
               "modal_generation_complete",
               latency_ms=latency * 1000,
               tokens_used=result.get("tokens_used"),
               finish_reason=result.get("finish_reason"),
           )
           return result
   ```

2. **OpenTelemetry traces** (optional, future):
   - Honeycomb integration (planned in docs)
   - Distributed trace across Modal → vLLM → XGrammar

**Action Items**:
- [ ] Add structlog to dependencies: `uv add structlog`
- [ ] Instrument ModalProvider with structured logging
- [ ] Instrument ProviderAdapter with route logging
- [ ] Add latency tracking to each pipeline stage
- [ ] Create log analysis script: `scripts/observability/analyze_logs.py`
- [ ] Document logging schema in `docs/observability/LOGGING_SCHEMA.md`

**Deliverable**: Structured logging infrastructure for debugging

---

### 5.2 Performance Dashboard

**Metrics to Track**:
- Modal call latency (cold start, warm, p50, p95, p99)
- Token usage per request
- Cost per request
- Success rate (IR validation pass, code execution pass)
- Route selection distribution (Modal vs Best Available)
- XGrammar constraint enforcement rate

**Implementation**:
- Extract metrics from structured logs
- Visualize with simple dashboard (Jupyter notebook or Streamlit)
- Alert on regressions (>30% latency increase, <90% success rate)

**Action Items**:
- [ ] Create `scripts/observability/metrics_dashboard.py`
- [ ] Extract metrics from logs
- [ ] Generate performance report: `docs/benchmarks/PERFORMANCE_REPORT_20251022.md`
- [ ] Set up regression alerts (CI integration)

**Deliverable**: Performance metrics dashboard and reporting

---

## Phase 6: Gap Analysis & Documentation (Week 3, Days 3-5)

### 6.1 Identify Gaps Between Mocked and Real

**Expected Gaps**:
1. **Latency**: Real Modal calls slower than mocked responses
2. **Error rates**: Real infrastructure has transient failures
3. **Schema mismatches**: Mock data may not match real XGrammar constraints
4. **Resource limits**: Real Modal has GPU memory limits
5. **Rate limiting**: Real APIs have rate limits

**Action Items**:
- [ ] Document all test failures when switching from mocks to real
- [ ] Categorize failures:
  - Schema issues (XGrammar rejected invalid JSON)
  - Latency timeouts (increase timeout thresholds)
  - Resource limits (reduce batch size, max_tokens)
  - Transient failures (add retry logic)
  - Real bugs (create beads for fixes)
- [ ] Create `docs/planning/MOCK_TO_REAL_GAPS.md`
- [ ] Prioritize fixes (P0: blocking, P1: important, P2: nice-to-have)

**Deliverable**: Gap analysis document with prioritized fixes

---

### 6.2 Update Documentation

**Documents to Update**:
- [ ] `README.md` - Update quickstart with real Modal setup
- [ ] `docs/MODAL_REFERENCE.md` - Add real endpoint usage
- [ ] `docs/TESTING.md` - Document integration test strategy
- [ ] `CLAUDE.md` - Update testing protocol with real Modal guidelines
- [ ] `docs/planning/SESSION_STATE.md` - Mark holes as validated
- [ ] Architecture diagrams - Show real data flow

**Deliverable**: Updated documentation reflecting real system

---

## Phase 7: Deployment & Validation (Week 3, Day 5)

### 7.1 Production Deployment Checklist

**Pre-Deployment**:
- [ ] All integration tests pass with real Modal
- [ ] Performance meets baseline thresholds
- [ ] No critical bugs (P0) outstanding
- [ ] Observability in place
- [ ] Documentation updated

**Deployment Steps**:
1. [ ] Verify Modal app deployed: `modal app list`
2. [ ] Run smoke test: `modal run lift_sys/inference/modal_app.py::test`
3. [ ] Configure production secrets (if needed)
4. [ ] Run full test suite: `pytest -m "not real_modal"` (cached)
5. [ ] Run integration tests: `pytest -m real_modal` (real Modal)
6. [ ] Monitor metrics for 24 hours
7. [ ] Document any issues

**Rollback Plan**:
- Keep mocked tests as fallback
- Use `@pytest.mark.real_modal` to toggle real vs mocked
- Revert to cached fixtures if Modal unavailable

**Deliverable**: Production deployment with validated performance

---

## Appendix A: Mock Inventory (Detailed)

### Provider Mocks
**File**: `lift_sys/providers/mock.py`
**Occurrences**: ~400 across tests
**Replacement Strategy**:
- Keep MockProvider for unit tests
- Add real ModalProvider tests in `tests/integration/`
- Use ResponseRecorder for CI (cached fixtures)

### DSPy Signature Mocks
**Files**: `tests/unit/dspy_signatures/*`
**Occurrences**: ~100
**Replacement Strategy**:
- Unit tests keep mocks (fast, isolated)
- Add integration tests with real DSPy + Modal
- Validate H6-H19 implementations

### Database Mocks (Supabase)
**Occurrences**: ~150
**Replacement Strategy**:
- Keep mocks for unit tests
- Use real Supabase test instance for integration
- Use transaction rollback for test isolation

### Response Recording (Fixtures)
**File**: `tests/fixtures.py` (ResponseRecorder)
**Occurrences**: ~100
**Replacement Strategy**:
- First run: Record real responses (`RECORD_FIXTURES=true`)
- CI runs: Use cached responses (fast, offline)
- Periodic refresh: Re-record weekly

---

## Appendix B: Skills Used

This plan utilizes the following skills from `~/.claude/skills/`:

### Primary Skills
1. **modal-functions-basics.md** - Modal app structure and deployment
2. **modal-gpu-workloads.md** - GPU configuration for inference
3. **modal-web-endpoints.md** - FastAPI endpoint setup
4. **beads-workflow.md** - Task tracking and session management

### Supporting Skills
5. **modal-volumes-secrets.md** - Secrets management
6. **modal-image-building.md** - Image optimization

### Future Skills (Phase 5+)
7. **observability/structured-logging.md** - Logging infrastructure (if exists)
8. **observability/distributed-tracing.md** - OpenTelemetry integration (if exists)

---

## Appendix C: Success Metrics

### Quantitative Metrics
- **Integration test coverage**: >80% using real Modal
- **Success rate**: ≥100% (match baseline)
- **Median latency**: <60s (allowing for 32B model)
- **Test execution time (CI)**: <5 minutes (using cached fixtures)
- **Cost per test run**: <$0.50 (10 tests)

### Qualitative Metrics
- **Developer confidence**: Team can debug issues with real traces
- **Deployment safety**: No surprises when deploying to production
- **Architecture validation**: Holes H1-H19 proven to work with real infrastructure

---

## Next Steps

1. **Immediate** (Day 1):
   - Run beads workflow: `go install github.com/steveyegge/beads/cmd/bd@latest`
   - Create Phase 1 bead: `bd create "E2E Validation: Phase 1 - Audit & Configuration" -t epic -p P0`
   - Start mock inventory: Begin Appendix A detailed breakdown

2. **This Week** (Days 1-5):
   - Complete Phase 1 (Audit & Configuration)
   - Complete Phase 2 (Provider Integration)
   - Start Phase 3 (DSPy Signature Validation)

3. **Next Week** (Week 2):
   - Complete Phase 3 (DSPy Signature Validation)
   - Complete Phase 4 (End-to-End Pipeline Validation)
   - Start Phase 5 (Observability)

4. **Week 3**:
   - Complete Phase 5 (Observability)
   - Complete Phase 6 (Gap Analysis)
   - Complete Phase 7 (Deployment)

---

**This is a living document. Update as implementation progresses and new gaps are discovered.**
