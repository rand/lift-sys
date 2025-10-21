# ADR 001: Dual-Provider LLM Routing Strategy

**Date**: 2025-10-21
**Status**: Accepted
**Context**: Phase 2 completion, H1 ProviderAdapter implementation
**Impact**: H1, H10, H8, all LLM integration points

---

## Context and Problem Statement

lift-sys integrates LLMs for two distinct use cases with different infrastructure requirements:

1. **Standard LLM tasks**: Text generation, reasoning, classification
2. **Constrained generation tasks**: Schema-based output, parallel speculative decoding

The question: Should all LLM calls route through the same infrastructure, or should we use different providers based on task requirements?

---

## Decision

**We will implement a dual-provider routing strategy**:

### Route 1: Best Available Model (Anthropic/OpenAI/Google)
**Use when**: Task does NOT require inference system access

**Characteristics**:
- Standard API calls via cloud providers
- No access to inference internals needed
- Prioritize: Best quality model available
- Examples: Claude 3.5 Sonnet, GPT-4, Gemini 1.5 Pro

**Use cases**:
- Simple text generation
- Reasoning tasks
- Classification without schema constraints
- Tasks where output format is flexible

**Provider selection**:
```python
# Priority order (configurable)
1. Anthropic Claude 3.5 Sonnet (best reasoning)
2. OpenAI GPT-4 Turbo (best code generation)
3. Google Gemini 1.5 Pro (best multimodal)
# Fallback to next available if primary unavailable
```

### Route 2: Modal Inference System (SGLang on Modal)
**Use when**: Task REQUIRES inference system access

**Characteristics**:
- Runs on Modal.com infrastructure
- Direct inference system access
- Enables advanced features
- May use smaller/faster models

**Required for**:
- **llguidance**: Constrained generation with grammars
- **aici**: Agentic constrained inference control
- **XGrammar**: Schema-based structured output (Pydantic models)
- **Parallel speculative decoding**: Multi-token prediction
- **Custom sampling**: Temperature/top_p manipulation at token level

**Provider**:
```python
# Modal SGLang deployment
- Model: Configurable (e.g., Llama 3.1 70B, Mistral Large)
- Framework: SGLang with llguidance/aici support
- GPU: L40S or H100 depending on model size
```

---

## Routing Logic

### Decision Tree

```
LLM Task Request
    ↓
Requires structured output (Pydantic schema)?
    ├─ YES → Requires XGrammar → Modal Route
    └─ NO → Continue
    ↓
Requires llguidance grammar?
    ├─ YES → Modal Route
    └─ NO → Continue
    ↓
Requires aici control?
    ├─ YES → Modal Route
    └─ NO → Continue
    ↓
Requires parallel speculative decoding?
    ├─ YES → Modal Route
    └─ NO → Continue
    ↓
Requires custom token-level sampling?
    ├─ YES → Modal Route
    └─ NO → Best Available Route
```

### Implementation in ProviderAdapter

```python
from enum import Enum

class ProviderRoute(Enum):
    BEST_AVAILABLE = "best_available"  # Anthropic/OpenAI/Google
    MODAL_INFERENCE = "modal_inference"  # Modal SGLang

class ProviderAdapter:
    def __init__(
        self,
        modal_provider: ModalProvider,
        best_available_provider: BestAvailableProvider,
        config: ProviderConfig,
    ):
        self.modal = modal_provider
        self.best_available = best_available_provider
        self.config = config

    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        llguidance_grammar: str | None = None,
        **kwargs
    ) -> dspy.Prediction:
        # Determine route based on requirements
        route = self._determine_route(
            schema=schema,
            llguidance_grammar=llguidance_grammar,
            **kwargs
        )

        if route == ProviderRoute.MODAL_INFERENCE:
            return await self._call_modal(prompt, schema, **kwargs)
        else:
            return await self._call_best_available(prompt, **kwargs)

    def _determine_route(self, **kwargs) -> ProviderRoute:
        # Requires inference system access?
        if any([
            kwargs.get("schema") is not None,  # XGrammar
            kwargs.get("llguidance_grammar") is not None,
            kwargs.get("aici_control") is not None,
            kwargs.get("speculative_decode", False),
            kwargs.get("custom_sampling", False),
        ]):
            return ProviderRoute.MODAL_INFERENCE

        return ProviderRoute.BEST_AVAILABLE
```

---

## Rationale

### Why Dual Routes?

**Quality vs Capability Tradeoff**:
- Best Available: Highest quality models (Anthropic/OpenAI) for general tasks
- Modal: Necessary infrastructure for constrained generation, may use smaller models

**Cost Optimization**:
- Best Available: Pay per token, use for high-value reasoning
- Modal: Fixed compute costs, use when infrastructure features required

**Flexibility**:
- Can switch Best Available provider without infrastructure changes
- Can upgrade Modal models independently

**Future-Proofing**:
- As constrained generation becomes available via APIs (e.g., Anthropic adds grammar support), can migrate tasks to Best Available route
- Modal route always available for cutting-edge research features

---

## Consequences

### Positive

1. **Best of both worlds**: Quality models for reasoning, advanced features for constrained tasks
2. **Cost efficiency**: Use expensive API calls only when quality matters
3. **Flexibility**: Provider-agnostic for standard tasks
4. **Research velocity**: Can experiment with inference system features on Modal

### Negative

1. **Complexity**: Two integration paths to maintain
2. **Consistency**: Different models may produce different outputs
3. **Monitoring**: Need separate observability for each route
4. **Testing**: Must test both routes independently

### Neutral

1. **Configuration**: Need provider priority/fallback configuration
2. **Migrations**: Tasks may move between routes as capabilities evolve

---

## Implementation Plan

### Phase 2 Updates (Immediate)

1. **Update H1 ProviderAdapter**:
   - Add `BestAvailableProvider` alongside `ModalProvider`
   - Implement routing logic based on kwargs
   - Add `ProviderRoute` enum

2. **Update Documentation**:
   - HOLE_INVENTORY.md: Add routing constraint to H1
   - CONSTRAINT_PROPAGATION_LOG.md: Event 7 (routing decision)

3. **Update Tests**:
   - Test both routes independently
   - Test routing decision logic
   - Mock both providers

### Phase 3 (Optimization)

4. **Update H10 OptimizationMetrics**:
   - Track route used (best_available vs modal)
   - Measure cost per route
   - Optimize route selection based on task

5. **Update H8 OptimizationAPI**:
   - Add route as optimization dimension
   - Consider route switching as optimization strategy

### Future Phases

6. **Implement BestAvailableProvider**:
   - Anthropic API integration
   - OpenAI API integration (fallback)
   - Google Gemini integration (fallback)
   - Priority/fallback logic

7. **Add Route Monitoring**:
   - Track route usage per task type
   - Compare quality metrics across routes
   - Identify migration opportunities

---

## Alternatives Considered

### Alternative 1: Modal Only
**Rejected**: Locks us into Modal infrastructure, limits model quality for simple tasks

### Alternative 2: Best Available Only
**Rejected**: Cannot support constrained generation features critical for IR validation

### Alternative 3: Dynamic Provider per Task
**Rejected**: Too complex, routing logic becomes tangled with business logic

---

## Notes

### Configuration Example

```python
# config/providers.yaml
routing:
  default_route: best_available

  best_available:
    priority:
      - anthropic_claude_3_5_sonnet
      - openai_gpt_4_turbo
      - google_gemini_1_5_pro
    fallback_to_modal: false

  modal_inference:
    model: llama_3_1_70b
    gpu: L40S
    enable_xgrammar: true
    enable_llguidance: true

task_overrides:
  # Force specific tasks to specific routes
  ir_generation: modal_inference  # Always use XGrammar
  reasoning: best_available  # Always use Claude
```

### Migration Path

As API providers add constrained generation:
1. Anthropic adds grammar support → migrate llguidance tasks to best_available
2. OpenAI adds structured output API → evaluate migration
3. Modal route becomes purely experimental/research

---

**Status**: Accepted
**Reviewers**: Architecture team
**Next Review**: After H10 implementation (Phase 3)
