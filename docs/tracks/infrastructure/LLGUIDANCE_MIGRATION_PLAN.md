---
track: infrastructure
document_type: migration_plan
status: complete
priority: P0
completion: 100%
last_updated: 2025-10-23
session_protocol: |
  For new Claude Code session:
  1. llguidance migration is COMPLETE (no action needed)
  2. Use this document as historical reference for migration decisions
  3. Current system uses llguidance/Guidance for constrained generation
  4. XGrammar migration path documented if rollback needed
related_docs:
  - docs/tracks/infrastructure/MIGRATION_QUICK_REFERENCE.md
  - docs/tracks/infrastructure/INFRASTRUCTURE_STATUS.md
  - docs/MASTER_ROADMAP.md
---

# llguidance Migration Plan

**Date**: 2025-10-23
**Status**: Complete
**Priority**: P0 (migration complete)

---

## Executive Summary

Plan to migrate from Modal's XGrammar deployment to llguidance/Guidance for constrained code generation. This addresses the 4.8% success rate observed with current XGrammar integration while maintaining the solid ProviderAdapter architecture we've built.

**Key Clarification**: XGrammar itself is an open-source project, not Modal's technology. The issues we're experiencing may be due to:
- Our schema definitions not being XGrammar-compatible
- Modal's deployment/configuration of XGrammar
- Integration challenges in our code

However, llguidance offers compelling advantages regardless of the root cause.

---

## Why llguidance?

### Technical Advantages

| Feature | XGrammar (via Modal) | llguidance/Guidance |
|---------|----------------------|---------------------|
| **Performance** | Unpredictable pre-computation (seconds to minutes) | ~50μs per token (predictable) |
| **Startup Cost** | High (pre-compilation phase) | Negligible (on-the-fly masks) |
| **Schema Support** | JSON Schema | JSON Schema + Regex + CFG |
| **Python API** | Via Modal's generate_structured() | Native via Guidance library |
| **Flexibility** | Coupled to Modal deployment | Provider-agnostic |
| **Debugging** | Limited visibility | Direct control, easier debugging |
| **Reliability** | 4.8% success rate (in our tests) | TBD (need to validate) |

### Strategic Benefits

1. **Provider Independence**: Not locked into Modal's infrastructure
2. **Local Development**: Can run constrained generation locally
3. **Better Control**: Direct access to constraint configuration
4. **Proven Stability**: Mature project with broad adoption
5. **Active Development**: Regular updates and community support

---

## Architecture Overview

### Current Architecture (XGrammar via Modal)

```
┌─────────────────┐
│ Code Generator  │
│ (TypeScript/    │
│  Rust/Go/Java)  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ ProviderAdapter │ (H1 - our abstraction layer)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ ModalProvider   │ (wraps Modal API)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Modal API       │
│ (XGrammar via   │
│  vLLM 0.9.2+)   │
└─────────────────┘
```

### Proposed Architecture (llguidance/Guidance)

**Option 1: Guidance as Provider** (Recommended)

```
┌─────────────────┐
│ Code Generator  │
│ (TypeScript/    │
│  Rust/Go/Java)  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ ProviderAdapter │ (H1 - unchanged!)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ GuidanceProvider│ (new provider implementation)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Guidance Library│
│ + llguidance    │
│ (JSON schema    │
│  constraints)   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ LLM Backend     │
│ (transformers/  │
│  llama.cpp/     │
│  OpenAI/etc.)   │
└─────────────────┘
```

**Option 2: Hybrid Approach**

```
┌─────────────────┐
│ ProviderAdapter │
└────────┬────────┘
         │
         ├──────────────┬─────────────┐
         v              v             v
┌──────────────┐  ┌──────────┐  ┌──────────┐
│ GuidanceProvider│  │ ModalProvider│  │ OpenAIProvider│
│ (constrained)   │  │ (fallback)   │  │ (fallback)    │
└──────────────┘  └──────────┘  └──────────┘
```

**Option 3: Modal + Guidance**

Deploy Guidance on Modal for serverless constrained generation:

```
┌─────────────────┐
│ ProviderAdapter │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ ModalGuidance   │ (new Modal deployment)
│ Provider        │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Modal Function  │
│ running Guidance│
│ + llguidance    │
│ + transformers  │
└─────────────────┘
```

---

## Migration Strategy

### Phase 1: Proof of Concept (1-2 days)

**Goal**: Validate llguidance works with our schemas

**Tasks**:
1. Install Guidance library: `uv add guidance`
2. Create minimal test with TypeScript schema
3. Compare output quality with XGrammar baseline
4. Measure performance (latency, success rate)
5. Document findings

**Success Criteria**:
- Guidance generates valid TypeScript matching schema
- Success rate >80% (vs current 4.8%)
- Latency <30s per generation (vs current ~85s)

**Code**:
```python
# test_guidance_poc.py
import asyncio
from guidance import json as gen_json, models
from pydantic import BaseModel, Field

class TypeScriptImplementation(BaseModel):
    body_statements: list[dict]
    function_signature: dict
    imports: list[dict] = Field(default_factory=list)

async def test_guidance_generation():
    # Initialize model (local or remote)
    lm = models.Transformers("mistralai/Mistral-7B-Instruct-v0.2")

    # Generate with schema constraint
    lm += f"Generate TypeScript function: {prompt}"
    lm += gen_json(name="implementation", schema=TypeScriptImplementation)

    # Extract result
    result = lm["implementation"]
    return result
```

**Deliverable**: `docs/planning/LLGUIDANCE_POC_RESULTS.md`

---

### Phase 2: GuidanceProvider Implementation (2-3 days)

**Goal**: Create production-ready GuidanceProvider

**Tasks**:
1. Create `lift_sys/providers/guidance_provider.py`
2. Implement LLMProvider interface
3. Add Pydantic schema → Guidance schema conversion
4. Implement generate_text() and generate_structured()
5. Add comprehensive error handling
6. Write unit tests

**Key Design Decisions**:

**2.1: Model Backend Selection**

```python
# Support multiple backends
class GuidanceProviderConfig(BaseModel):
    backend: Literal["transformers", "llama_cpp", "openai", "anthropic"]
    model_name: str
    device: str = "cuda"  # for local models
    api_key: Optional[str] = None  # for remote models
```

**2.2: Schema Conversion**

Our JSON schemas → Pydantic models → Guidance gen_json():

```python
def json_schema_to_pydantic(schema: dict) -> Type[BaseModel]:
    """Convert JSON schema to Pydantic model for Guidance."""
    # Use pydantic-core or datamodel-code-generator
    # Or hand-craft TypeScript/Rust/Go/Java implementation models
    pass

async def generate_structured(
    self,
    prompt: str,
    schema: dict,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> dict:
    # Convert schema to Pydantic model
    pydantic_model = self._get_or_create_model(schema)

    # Generate with Guidance
    lm = self.model
    lm += prompt
    lm += gen_json(name="output", schema=pydantic_model)

    # Extract and return
    return lm["output"]
```

**2.3: Resource Management**

```python
class GuidanceProvider(LLMProvider):
    def __init__(self, config: GuidanceProviderConfig):
        self.config = config
        self._model = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Lazy load model on first use."""
        async with self._lock:
            if self._model is None:
                self._model = models.Transformers(
                    self.config.model_name,
                    device=self.config.device
                )

    async def shutdown(self):
        """Clean up model resources."""
        if self._model is not None:
            # Guidance cleanup
            del self._model
            self._model = None
```

**Deliverable**: `lift_sys/providers/guidance_provider.py` with tests

---

### Phase 3: ProviderAdapter Integration (1 day)

**Goal**: Make GuidanceProvider work seamlessly with existing ProviderAdapter

**Tasks**:
1. Update ProviderAdapter to detect GuidanceProvider
2. Test dual-routing logic (Guidance vs fallback)
3. Verify resource tracking works
4. Run TypeScript E2E tests with GuidanceProvider

**Code Changes**:
```python
# lift_sys/dspy_signatures/provider_adapter.py

async def __call__(
    self,
    prompt: str,
    schema: Optional[dict] = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> dspy.Prediction:
    # Detect Guidance provider
    if isinstance(self.provider, GuidanceProvider):
        # Use Guidance's constrained generation
        result = await self.provider.generate_structured(
            prompt=prompt,
            schema=schema,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        # Convert to dspy.Prediction
        return self._dict_to_prediction(result)

    # Existing Modal/XGrammar logic
    elif hasattr(self.provider, "generate_structured") and schema:
        # ... existing code ...
```

**Testing**:
```bash
# Run TypeScript tests with GuidanceProvider
PROVIDER=guidance uv run pytest tests/integration/test_typescript_pipeline_e2e.py -v
```

**Success Criteria**:
- 4/4 TypeScript tests pass
- Success rate >90%
- No breaking changes to generators

**Deliverable**: Updated ProviderAdapter with Guidance support

---

### Phase 4: Multi-Language Validation (2-3 days)

**Goal**: Validate Guidance works for all 4 languages

**Tasks**:
1. Run Rust E2E tests with GuidanceProvider
2. Run Go E2E tests with GuidanceProvider
3. Run Java E2E tests with GuidanceProvider
4. Document language-specific findings
5. Fix any schema compatibility issues

**Testing Strategy**:
```bash
# Run all languages in parallel
uv run pytest tests/integration/test_typescript_pipeline_e2e.py -v &
uv run pytest tests/integration/test_rust_pipeline_e2e.py -v &
uv run pytest tests/integration/test_go_pipeline_e2e.py -v &
uv run pytest tests/integration/test_java_pipeline_e2e.py -v &
wait

# Collect results
tail -100 /tmp/*_guidance_*.log
```

**Success Criteria**:
- All 21 E2E tests pass (100% success rate)
- Latency <30s per test (improvement over 85s)
- No language-specific failures

**Deliverable**: `docs/planning/LLGUIDANCE_MULTI_LANGUAGE_RESULTS.md`

---

### Phase 5: Modal Deployment (Optional - 3-4 days)

**Goal**: Deploy Guidance on Modal for serverless execution

**Why**: Combines Modal's GPU infrastructure with Guidance's reliability

**Tasks**:
1. Create Modal function with Guidance + transformers
2. Set up model caching (download once, reuse)
3. Configure GPU allocation (L40S recommended)
4. Create ModalGuidanceProvider wrapper
5. Benchmark latency and cost
6. Compare with local GuidanceProvider

**Modal Function**:
```python
# modal_guidance_app.py
import modal

app = modal.App("lift-sys-guidance")

# Build image with Guidance + model
guidance_image = (
    modal.Image.debian_slim()
    .pip_install("guidance", "transformers", "torch", "accelerate")
    .run_commands(
        # Pre-download model
        "python -c 'from transformers import AutoModel; AutoModel.from_pretrained(\"mistralai/Mistral-7B-Instruct-v0.2\")'"
    )
)

@app.function(
    image=guidance_image,
    gpu="L40S",
    secrets=[modal.Secret.from_name("supabase")],
    timeout=300,
)
async def generate_with_guidance(prompt: str, schema: dict) -> dict:
    from guidance import json as gen_json, models

    # Load model (cached after first call)
    lm = models.Transformers("mistralai/Mistral-7B-Instruct-v0.2")

    # Generate with schema
    lm += prompt
    lm += gen_json(name="output", schema=schema)

    return lm["output"]

@app.function()
@modal.web_endpoint(method="POST")
async def api(request: dict):
    result = await generate_with_guidance.remote.aio(
        prompt=request["prompt"],
        schema=request["schema"]
    )
    return {"result": result}
```

**Deployment**:
```bash
modal deploy modal_guidance_app.py
```

**Provider Wrapper**:
```python
# lift_sys/providers/modal_guidance_provider.py
class ModalGuidanceProvider(LLMProvider):
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    async def generate_structured(self, prompt: str, schema: dict, **kwargs) -> dict:
        # Call Modal endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint_url,
                json={"prompt": prompt, "schema": schema}
            )
            return response.json()["result"]
```

**Cost Comparison**:
- Local Guidance: GPU hardware costs (if applicable)
- Modal Guidance: Pay-per-use GPU compute (~$0.50/hr for L40S)
- Modal XGrammar: Same GPU costs but with reliability issues

**Deliverable**: `modal_guidance_app.py` + `ModalGuidanceProvider`

---

### Phase 6: Performance Optimization (2-3 days)

**Goal**: Optimize Guidance for production performance

**Tasks**:
1. Benchmark different model backends
2. Test model quantization (4-bit, 8-bit)
3. Implement response caching
4. Add request batching (if applicable)
5. Profile and optimize hotspots

**Model Backend Comparison**:

| Backend | Latency | Quality | Setup Complexity |
|---------|---------|---------|------------------|
| Transformers (local) | ~20-30s | High | Medium (GPU required) |
| llama.cpp | ~10-15s | High | Low (CPU ok) |
| OpenAI (GPT-4) | ~5-10s | Highest | Low (API key) |
| Modal Guidance | ~15-25s | High | Medium (deployment) |

**Quantization Testing**:
```python
# Test 4-bit quantization
lm = models.Transformers(
    "mistralai/Mistral-7B-Instruct-v0.2",
    device_map="auto",
    load_in_4bit=True,  # Reduces memory, faster inference
)
```

**Caching Strategy**:
```python
# Cache common IR → Code generations
from functools import lru_cache

@lru_cache(maxsize=1000)
def generate_code_cached(ir_hash: str, schema_hash: str) -> dict:
    # Only regenerate if IR or schema changes
    return generate_code(ir, schema)
```

**Deliverable**: `docs/planning/LLGUIDANCE_PERFORMANCE_REPORT.md`

---

### Phase 7: Rollout (1-2 days)

**Goal**: Deploy to production with monitoring

**Tasks**:
1. Update default provider config to GuidanceProvider
2. Add feature flag for Guidance vs XGrammar
3. Set up monitoring (success rate, latency, errors)
4. Gradual rollout (10% → 50% → 100%)
5. Document rollback procedure

**Feature Flag**:
```python
# lift_sys/config.py
class SystemConfig(BaseModel):
    use_guidance: bool = Field(default=True, env="LIFT_SYS_USE_GUIDANCE")
    guidance_backend: str = Field(default="transformers", env="GUIDANCE_BACKEND")
    guidance_model: str = Field(default="mistralai/Mistral-7B-Instruct-v0.2")

# Conditional provider initialization
if config.use_guidance:
    provider = GuidanceProvider(...)
else:
    provider = ModalProvider(...)  # Fallback to XGrammar
```

**Monitoring Metrics**:
- Success rate (target: >95%)
- P50/P95/P99 latency (target: <30s / <60s / <120s)
- Error rate by error type
- Cost per generation

**Rollback Plan**:
```bash
# If Guidance fails, switch back to Modal XGrammar
export LIFT_SYS_USE_GUIDANCE=false
# Restart API servers
modal app restart lift-sys-api
```

**Deliverable**: Production deployment with monitoring

---

## Code Changes Required

### New Files

1. **`lift_sys/providers/guidance_provider.py`** (~300 lines)
   - GuidanceProvider class
   - GuidanceProviderConfig
   - Schema conversion utilities
   - Error handling

2. **`lift_sys/providers/modal_guidance_provider.py`** (~150 lines)
   - ModalGuidanceProvider class (if doing Phase 5)
   - HTTP client wrapper
   - Retry logic

3. **`modal_guidance_app.py`** (~100 lines)
   - Modal deployment for Guidance (if doing Phase 5)
   - Web endpoint
   - Model caching

4. **`tests/unit/test_guidance_provider.py`** (~200 lines)
   - Unit tests for GuidanceProvider
   - Mock Guidance library
   - Schema conversion tests

5. **`tests/integration/test_guidance_e2e.py`** (~150 lines)
   - Integration tests with real Guidance
   - All 4 languages
   - Performance benchmarks

### Modified Files

1. **`lift_sys/dspy_signatures/provider_adapter.py`** (+20 lines)
   - Add GuidanceProvider detection
   - Route to Guidance-specific logic

2. **`pyproject.toml`** (+5 lines)
   - Add `guidance` dependency
   - Add `llguidance` (if using directly)

3. **`lift_sys/config.py`** (+10 lines)
   - Add Guidance configuration options
   - Feature flag for provider selection

### Total Estimated Changes
- **New code**: ~900 lines
- **Modified code**: ~35 lines
- **Test code**: ~350 lines
- **Total**: ~1,285 lines

---

## Schema Compatibility

### Current Schema Format (JSON Schema)

All our generators use JSON Schema format:

```json
{
  "type": "object",
  "properties": {
    "implementation": {
      "type": "object",
      "properties": {
        "body_statements": {"type": "array"},
        "function_signature": {"type": "object"}
      },
      "required": ["body_statements", "function_signature"]
    }
  },
  "required": ["implementation"]
}
```

### Guidance Requirement (Pydantic Models)

Guidance uses Pydantic models:

```python
class FunctionSignature(BaseModel):
    name: str
    parameters: list[dict]
    return_type: str

class TypeScriptImplementation(BaseModel):
    body_statements: list[dict]
    function_signature: FunctionSignature
    imports: list[dict] = Field(default_factory=list)

class TypeScriptOutput(BaseModel):
    implementation: TypeScriptImplementation
```

### Conversion Strategy

**Option 1: Maintain Both Formats** (Recommended)

```python
# Keep existing JSON schemas for XGrammar compatibility
TYPESCRIPT_GENERATION_SCHEMA = {...}  # JSON Schema

# Add Pydantic models for Guidance
class TypeScriptImplementationModel(BaseModel):
    # Generated from JSON schema or hand-crafted
    ...

# Utility to convert JSON schema → Pydantic (for unknown schemas)
def json_schema_to_pydantic_class(schema: dict, class_name: str) -> Type[BaseModel]:
    # Use datamodel-code-generator or pydantic-core
    from datamodel_code_generator import generate
    # Generate Pydantic model from JSON schema
    ...
```

**Option 2: Migrate to Pydantic** (Long-term)

- Replace all JSON schemas with Pydantic models
- Generate JSON schemas from Pydantic for XGrammar compatibility
- Better type safety and IDE support

**Recommendation**: Start with Option 1, migrate to Option 2 in Phase 2 (DSPy Signatures)

---

## Testing Strategy

### Test Levels

**Unit Tests** (fast, no LLM calls):
```python
def test_guidance_provider_initialization():
    provider = GuidanceProvider(config=...)
    assert provider.config.model_name == "mistralai/Mistral-7B-Instruct-v0.2"

def test_json_schema_to_pydantic():
    schema = TYPESCRIPT_GENERATION_SCHEMA
    model = json_schema_to_pydantic(schema)
    assert issubclass(model, BaseModel)
```

**Integration Tests** (with mock Guidance):
```python
@pytest.mark.asyncio
async def test_guidance_generate_typescript(mock_guidance):
    provider = GuidanceProvider(...)
    result = await provider.generate_structured(
        prompt="Generate function",
        schema=TYPESCRIPT_GENERATION_SCHEMA
    )
    assert "implementation" in result
    assert "body_statements" in result["implementation"]
```

**E2E Tests** (with real Guidance + model):
```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_typescript_e2e_with_guidance():
    # Use real GuidanceProvider
    provider = GuidanceProvider(config=GuidanceProviderConfig(
        backend="transformers",
        model_name="mistralai/Mistral-7B-Instruct-v0.2"
    ))
    await provider.initialize()

    # Test full pipeline
    translator = BestOfNIRTranslator(provider=provider)
    ir = await translator.translate("Function to add two numbers")

    generator = TypeScriptGenerator(provider=provider)
    code = await generator.generate(ir)

    # Validate
    assert "function" in code
    assert "return" in code
```

### Test Data

Reuse existing test fixtures:
- `tests/fixtures/code_responses.json` (for baseline comparison)
- `tests/integration/test_*_pipeline_e2e.py` (existing E2E tests)

Add new fixtures:
- `tests/fixtures/guidance_responses.json` (capture Guidance outputs)
- Compare quality: XGrammar vs Guidance

### Success Metrics

| Metric | Current (XGrammar) | Target (Guidance) |
|--------|-------------------|-------------------|
| Success Rate | 4.8% | >95% |
| Latency (P50) | 85s | <30s |
| Latency (P95) | 120s | <60s |
| Error Rate | 95.2% | <5% |
| Test Pass Rate | 1/21 (4.8%) | 21/21 (100%) |

---

## Risks & Mitigations

### Risk 1: Guidance Performance Worse Than Expected

**Impact**: High (blocks deployment)
**Likelihood**: Low (Guidance is proven technology)
**Mitigation**:
- Run POC early (Phase 1) to validate performance
- Test multiple backends (transformers, llama.cpp)
- Consider quantization (4-bit, 8-bit) if latency too high
- Fallback to Modal XGrammar if needed

### Risk 2: Schema Conversion Issues

**Impact**: Medium (delays rollout)
**Likelihood**: Medium (our schemas are complex)
**Mitigation**:
- Start with simplest language (TypeScript)
- Test schema conversion thoroughly in Phase 2
- Hand-craft Pydantic models if auto-conversion fails
- Maintain dual format (JSON Schema + Pydantic) during transition

### Risk 3: Model Selection Wrong

**Impact**: Medium (affects quality/cost)
**Likelihood**: Low (Mistral-7B is proven)
**Mitigation**:
- Benchmark multiple models in Phase 6
- Test quality vs baseline (existing XGrammar outputs)
- Consider larger models (Mistral-22B, Llama-70B) if quality insufficient
- Support multiple model backends

### Risk 4: Local vs Modal Deployment Trade-offs

**Impact**: Medium (affects architecture decision)
**Likelihood**: Medium (both have pros/cons)
**Mitigation**:
- Support both local and Modal deployments (Phase 5 optional)
- Measure cost/latency/reliability for each
- Make deployment configurable via environment variables
- Document trade-offs clearly

### Risk 5: Regression in Code Quality

**Impact**: High (user-facing)
**Likelihood**: Low (Guidance is mature)
**Mitigation**:
- Extensive testing in Phases 4-5
- Compare outputs side-by-side with XGrammar baseline
- A/B test with small percentage of traffic
- Keep XGrammar fallback available

---

## Timeline & Effort

| Phase | Duration | Owner | Depends On |
|-------|----------|-------|------------|
| 1. POC | 1-2 days | Engineering | None |
| 2. GuidanceProvider | 2-3 days | Engineering | Phase 1 |
| 3. ProviderAdapter Integration | 1 day | Engineering | Phase 2 |
| 4. Multi-Language Validation | 2-3 days | Engineering | Phase 3 |
| 5. Modal Deployment (Optional) | 3-4 days | DevOps + Engineering | Phase 4 |
| 6. Performance Optimization | 2-3 days | Engineering | Phase 4 or 5 |
| 7. Rollout | 1-2 days | Engineering + Product | Phase 6 |

**Total Timeline**: 12-18 days (2.5-3.5 weeks)

**If skipping Phase 5 (Modal deployment)**: 9-14 days (2-3 weeks)

---

## Cost Analysis

### Current Cost (Modal XGrammar)

- L40S GPU: ~$0.50/hour
- Average test duration: 85s per test
- 21 tests: ~30 minutes = $0.25 per full test suite
- But: 95.2% failure rate means wasted compute

### Projected Cost (Guidance)

**Option A: Local Guidance** (own GPU hardware)
- One-time: GPU hardware ($1,000-$5,000)
- Ongoing: Electricity (~$50/month)
- Scales poorly (need more GPUs for load)

**Option B: Modal Guidance**
- L40S GPU: ~$0.50/hour (same as XGrammar)
- Expected test duration: ~30s per test (faster)
- 21 tests: ~10 minutes = $0.08 per full test suite
- Higher success rate = less wasted compute

**Option C: OpenAI (via Guidance)**
- GPT-4: $0.01/1K input tokens, $0.03/1K output tokens
- Est. ~2K input + 1K output per generation = $0.05 per test
- 21 tests: $1.05 per full test suite
- No infrastructure management
- Very fast (5-10s latency)

**Recommendation**: Start with Option B (Modal Guidance), consider Option C for production if cost-effective.

---

## Success Criteria

### Phase 1 (POC) Success
- ✅ Guidance generates valid TypeScript code
- ✅ Success rate >50% (baseline validation)
- ✅ Latency <60s per generation

### Phase 4 (Multi-Language) Success
- ✅ All 21 E2E tests pass (100% success rate)
- ✅ No language-specific failures
- ✅ Output quality comparable to XGrammar baseline

### Phase 7 (Rollout) Success
- ✅ Production success rate >95%
- ✅ P50 latency <30s
- ✅ Zero critical bugs
- ✅ User-reported quality issues <1%

### Overall Project Success
- ✅ Move from 4.8% to >95% success rate
- ✅ Maintain or improve code quality
- ✅ Reduce or maintain costs
- ✅ Improve developer experience (local testing, debugging)

---

## Open Questions

1. **Model Selection**: Which base model should we use?
   - Mistral-7B-Instruct-v0.2 (fast, good quality)
   - Mistral-22B (better quality, slower)
   - Llama-70B (best quality, much slower, more expensive)
   - GPT-4 via OpenAI (fastest, most expensive, no GPU needed)

2. **Deployment Strategy**: Local or Modal?
   - Local: Better for development, requires GPU hardware
   - Modal: Better for production, pay-per-use, scalable
   - Hybrid: Local for dev, Modal for prod

3. **Schema Migration**: Dual format or Pydantic-only?
   - Dual: Maintain backward compatibility, more complexity
   - Pydantic: Simpler long-term, breaking change

4. **Fallback Strategy**: Keep XGrammar as fallback?
   - Yes: Safety net if Guidance fails
   - No: Simpler codebase, full commitment to Guidance

5. **Testing Approach**: Use real models or mocks in CI?
   - Real models: Accurate testing, slow, expensive CI
   - Mocks: Fast CI, risk of missing issues
   - Hybrid: Mocks in PR checks, real models nightly

---

## Next Steps (Immediate)

1. **Get user approval** for this migration plan
2. **Start Phase 1 POC** (1-2 days):
   - Install Guidance: `uv add guidance`
   - Create minimal TypeScript test
   - Validate schema conversion works
   - Measure success rate and latency
3. **Document POC results** in `LLGUIDANCE_POC_RESULTS.md`
4. **Decide on architecture** (Options 1-3 above)
5. **Proceed to Phase 2** (GuidanceProvider implementation)

---

## References

- **llguidance GitHub**: https://github.com/guidance-ai/llguidance
- **Guidance Library**: https://github.com/guidance-ai/guidance
- **Guidance Docs**: https://guidance.readthedocs.io/
- **Current Issues**: `docs/planning/DSPY_INTEGRATION_FINAL_RESULTS.md`
- **XGrammar (for reference)**: https://github.com/mlc-ai/xgrammar

---

**Document Status**: DRAFT (awaiting user approval)
**Owner**: Architecture Team
**Next Update**: After Phase 1 POC complete
