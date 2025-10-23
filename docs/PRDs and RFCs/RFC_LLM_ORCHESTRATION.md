# RFC: LLM Orchestration Layer
## DSPy + Pydantic AI Integration with Dual-Provider Routing

**RFC Number**: RFC-003
**Title**: lift LLM Orchestration Architecture
**Status**: Draft
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Authors**: Codelift Team
**Related Documents**: RFC_LIFT_ARCHITECTURE.md, ADR_001_DUAL_PROVIDER_ROUTING.md, PRD_DSPY_INTEGRATION.md

---

## 1. Introduction & LLM Orchestration Philosophy

### 1.1 Vision

The LLM Orchestration Layer is the intelligence engine of lift. While the IR Core provides formal semantics and the Constraint Solver ensures correctness, the Orchestration Layer bridges human intent with machine verification through systematic, optimizable LLM interactions.

**Core Philosophy**: Replace manual prompt engineering with **declarative signatures** that specify *what* tasks accomplish, then use **automatic optimization** (MIPROv2) to learn *how* to prompt effectively.

### 1.2 Current State (Phase 2 Complete)

**Production Metrics** (October 2025):
- Forward mode: 80% compilation rate, 60% execution rate
- Average latency: 16 seconds (p50), 45 seconds (p95)
- Cost: $0.0029 per request
- Provider: Modal SGLang (single route)

**Implementation Status**:
- ✅ H1 ProviderAdapter: 277 lines, 25 tests passing
- ✅ H6 NodeSignatureInterface: 354 lines, 23 tests passing
- ✅ ADR 001 Accepted: Dual-provider routing architecture
- ✅ Gate 2 PASSED: 100% criteria satisfied

**Phase 3 Targets**:
- Forward mode: 90% compilation, 80% execution
- Latency: <10 seconds (p50)
- Cost: Optimized via dual-routing
- Provider: Best Available + Modal Inference

### 1.3 Key Innovations

1. **Dual-Provider Routing (ADR 001)**
   - Route 1: Best Available (Claude 3.5/GPT-4) for reasoning
   - Route 2: Modal Inference (SGLang + XGrammar) for structured output
   - Automatic route determination based on task requirements

2. **DSPy Systematic Orchestration**
   - 6 core signatures: PromptToIR, ExtractIntent, RefineIR, VerifyIR, GenerateCode, ExplainCode
   - MIPROv2 optimization: 60% → 85% success rate target
   - Type-safe, composable modules

3. **Modal SGLang Deployment**
   - GPU-optimized inference (L40S/H100)
   - XGrammar integration for constrained decoding
   - llguidance/aici support for advanced control

4. **Provenance Tracking**
   - Every LLM decision tracked with confidence scores
   - Route metrics for cost/quality analysis
   - Execution history for debugging

### 1.4 Design Principles

**Principle 1: Signatures Over Prompts**
- Manual prompts → Brittle, hard to optimize, no composability
- DSPy signatures → Declarative, automatically optimizable, composable

**Principle 2: Route by Requirement, Not by Default**
- Tasks requiring XGrammar/llguidance → Modal Inference
- Standard reasoning/classification → Best Available
- Automatic fallback on provider failure

**Principle 3: Optimize the System, Not the Prompts**
- MIPROv2 learns from examples automatically
- Continuous improvement as data accumulates
- A/B testing validates optimization gains

**Principle 4: Provenance is First-Class**
- Track which route used, why, cost, quality
- Enable route migration analysis
- Debug failures via execution traces

---

## 2. ADR 001: Dual-Provider Routing

### 2.1 Decision Summary

**Status**: Accepted (2025-10-21)
**Context**: lift integrates LLMs for two distinct use cases:
1. Standard tasks (reasoning, classification, flexible output)
2. Constrained generation (schema-based output, structured decoding)

**Decision**: Implement dual-provider routing strategy with automatic route determination.

### 2.2 Route 1: Best Available (Anthropic/OpenAI/Google)

**When to use**: Task does NOT require inference system access.

**Characteristics**:
- **Quality priority**: Use best available models (Claude 3.5 Sonnet, GPT-4 Turbo, Gemini 1.5 Pro)
- **Standard API calls**: No inference internals needed
- **Pay-per-token pricing**: Cost scales with usage
- **Provider flexibility**: Can switch providers without infrastructure changes

**Use cases**:
- Intent extraction (ExtractIntent signature)
- Code explanation (ExplainCode signature)
- Verification reports (VerifyIR signature)
- Code generation without schema constraints (GenerateCode signature)
- Refinement suggestions
- Classification tasks

**Provider priority** (configurable):
```python
DEFAULT_PRIORITY = [
    "anthropic_claude_3_5_sonnet",  # Best reasoning
    "openai_gpt_4_turbo",           # Best code generation
    "google_gemini_1_5_pro",        # Best multimodal
]
```

**Example API call**:
```python
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": "Extract the intent from: Create a function to validate emails"
    }]
)
```

### 2.3 Route 2: Modal Inference (SGLang on Modal)

**When to use**: Task REQUIRES inference system access.

**Characteristics**:
- **Capability priority**: Direct inference system control
- **Fixed GPU costs**: Pay for compute time, not tokens
- **Advanced features**: XGrammar, llguidance, aici, speculative decoding
- **Infrastructure control**: Custom sampling, token-level manipulation

**Required for**:
- **XGrammar**: Schema-based structured output (Pydantic models)
  - IR generation (PromptToIR signature)
  - IR refinement (RefineIR signature)
- **llguidance**: Grammar-constrained generation
  - Type-safe code generation
  - DSL generation with formal grammars
- **aici**: Agentic constrained inference control
  - Multi-step reasoning with constraints
- **Parallel speculative decoding**: Multi-token prediction for speedup
- **Custom sampling**: Temperature/top_p at token level

**GPU configuration**:
```python
MODAL_GPU_CONFIG = {
    "development": "T4",      # Cheap, slow ($0.60/hr)
    "standard": "L40S",       # Cost/performance sweet spot ($1.50/hr)
    "performance": "H100",    # Max performance ($4.00/hr)
}
```

**Example Modal deployment**:
```python
import modal

app = modal.App("lift-inference")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("sglang[all]", "xgrammar", "pydantic")
)

@app.function(
    image=image,
    gpu=modal.gpu.L40S(),
    timeout=300,
)
async def generate_ir(prompt: str, schema: dict) -> str:
    """Generate IR with XGrammar constraints."""
    import sglang as sgl

    runtime = sgl.Runtime(
        model_path="meta-llama/Llama-3.1-70B-Instruct",
        xgrammar_backend=True,
    )

    result = runtime.generate(
        prompt=prompt,
        schema=schema,
        max_tokens=4096,
    )

    return result.text
```

### 2.4 Routing Decision Tree

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

### 2.5 Implementation in ProviderAdapter (H1)

**Complete implementation** (Phase 2, 277 lines):

```python
from enum import Enum
from typing import Any
import dspy
from pydantic import BaseModel

class ProviderRoute(Enum):
    """Available provider routes."""
    BEST_AVAILABLE = "best_available"
    MODAL_INFERENCE = "modal_inference"

class ProviderAdapter:
    """
    Dual-route LLM integration layer.

    Routes requests to appropriate provider based on infrastructure
    requirements. Tracks metrics, handles fallback, enables observability.
    """

    def __init__(
        self,
        modal_provider: "ModalProvider",
        best_available_provider: "BestAvailableProvider",
        config: "ProviderConfig",
    ):
        self.modal = modal_provider
        self.best_available = best_available_provider
        self.config = config
        self.route_metrics = RouteMetrics()

    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        llguidance_grammar: str | None = None,
        **kwargs
    ) -> dspy.Prediction:
        """
        Execute LLM call with automatic routing.

        Args:
            prompt: Input prompt
            schema: Optional Pydantic schema for structured output
            llguidance_grammar: Optional grammar for constrained generation
            **kwargs: Additional provider-specific arguments

        Returns:
            DSPy Prediction with generated output and metadata
        """
        # Determine route based on requirements
        route = self._determine_route(
            schema=schema,
            llguidance_grammar=llguidance_grammar,
            **kwargs
        )

        # Track route decision
        self.route_metrics.record_decision(route, prompt)

        try:
            if route == ProviderRoute.MODAL_INFERENCE:
                result = await self._call_modal(prompt, schema, **kwargs)
            else:
                result = await self._call_best_available(prompt, **kwargs)

            # Track success
            self.route_metrics.record_success(route)
            return result

        except Exception as e:
            # Track failure
            self.route_metrics.record_failure(route, error=str(e))

            # Attempt fallback
            if self.config.enable_fallback:
                return await self._fallback(prompt, route, **kwargs)
            raise

    def _determine_route(self, **kwargs) -> ProviderRoute:
        """
        Determine which route to use based on requirements.

        Route to Modal Inference if ANY of these are present:
        - schema: Pydantic model (requires XGrammar)
        - llguidance_grammar: Grammar string
        - aici_control: AICI controller
        - speculative_decode: Enable parallel speculative decoding
        - custom_sampling: Custom temperature/top_p per token

        Otherwise route to Best Available.
        """
        # Check for inference system requirements
        requires_modal = any([
            kwargs.get("schema") is not None,
            kwargs.get("llguidance_grammar") is not None,
            kwargs.get("aici_control") is not None,
            kwargs.get("speculative_decode", False),
            kwargs.get("custom_sampling", False),
        ])

        if requires_modal:
            return ProviderRoute.MODAL_INFERENCE

        # Check for manual override
        if override := kwargs.get("force_route"):
            return ProviderRoute(override)

        return ProviderRoute.BEST_AVAILABLE

    async def _call_modal(
        self,
        prompt: str,
        schema: BaseModel | None,
        **kwargs
    ) -> dspy.Prediction:
        """Call Modal inference system."""
        start_time = time.time()

        result = await self.modal.generate(
            prompt=prompt,
            schema=schema.model_json_schema() if schema else None,
            **kwargs
        )

        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        self.route_metrics.record_latency(
            ProviderRoute.MODAL_INFERENCE,
            duration_ms
        )
        self.route_metrics.record_cost(
            ProviderRoute.MODAL_INFERENCE,
            self._compute_modal_cost(duration_ms)
        )

        return dspy.Prediction(
            **result,
            _route=ProviderRoute.MODAL_INFERENCE.value,
            _latency_ms=duration_ms,
        )

    async def _call_best_available(
        self,
        prompt: str,
        **kwargs
    ) -> dspy.Prediction:
        """Call best available provider (Anthropic/OpenAI/Google)."""
        start_time = time.time()

        result = await self.best_available.generate(
            prompt=prompt,
            **kwargs
        )

        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        self.route_metrics.record_latency(
            ProviderRoute.BEST_AVAILABLE,
            duration_ms
        )
        self.route_metrics.record_cost(
            ProviderRoute.BEST_AVAILABLE,
            self._compute_api_cost(result.tokens_used)
        )

        return dspy.Prediction(
            **result,
            _route=ProviderRoute.BEST_AVAILABLE.value,
            _latency_ms=duration_ms,
        )

    async def _fallback(
        self,
        prompt: str,
        failed_route: ProviderRoute,
        **kwargs
    ) -> dspy.Prediction:
        """
        Fallback to alternative route on failure.

        Strategy:
        - Modal → Best Available: Strip schema, attempt generation
        - Best Available → Modal: Add minimal schema, use Modal
        """
        if failed_route == ProviderRoute.MODAL_INFERENCE:
            # Try Best Available without schema
            return await self._call_best_available(
                prompt=prompt,
                **{k: v for k, v in kwargs.items() if k not in ["schema", "llguidance_grammar"]}
            )
        else:
            # Try Modal with minimal schema
            return await self._call_modal(
                prompt=prompt,
                schema=None,
                **kwargs
            )
```

**Key features**:
- **Automatic routing**: Based on kwargs inspection
- **Fallback logic**: Degrades gracefully on provider failure
- **Metrics tracking**: Latency, cost, success rate per route
- **Manual override**: `force_route` for experimentation
- **Observability**: Every call tagged with route metadata

### 2.6 Consequences

**Positive**:
- Best of both worlds: Quality models for reasoning, advanced features for constraints
- Cost efficiency: Use expensive API calls only when needed
- Flexibility: Provider-agnostic for standard tasks
- Future-proofing: As APIs add constrained generation, can migrate tasks

**Negative**:
- Complexity: Two integration paths to maintain
- Consistency: Different models may produce different outputs
- Monitoring: Separate observability per route required

**Migration path**:
As API providers add constrained generation (e.g., Anthropic adds XGrammar support):
1. Update routing logic to check provider capabilities
2. Migrate eligible tasks to Best Available route
3. Modal route becomes research/experimentation

---

## 3. DSPy Integration

### 3.1 DSPy Overview

**DSPy** (Declarative Self-improving Prompting) is a Stanford NLP framework that replaces manual prompt engineering with:

1. **Signatures**: Typed specifications of LLM tasks
2. **Modules**: Composable units (ChainOfThought, ReAct, etc.)
3. **Optimizers**: Automatic prompt improvement (MIPROv2, BootstrapFewShot)
4. **Evaluation**: Metrics-driven quality assessment

**Key benefit**: Transform prompt engineering from art → science.

**Research results** (arXiv:2310.03714):
- 22-34% quality improvement on complex tasks
- 15-25% gains with 50 training examples (MIPROv2)
- 10-20% gains via self-supervised learning (BootstrapFewShot)

### 3.2 Signature Design Pattern

**Core philosophy**: Specify *what* the task accomplishes, let DSPy figure out *how* to prompt.

**Pattern**:
```python
class TaskSignature(dspy.Signature):
    """Clear description of task goal."""

    # Inputs with semantic roles
    input_field: InputType = dspy.InputField(
        desc="What this input represents for the LLM"
    )

    # Outputs with constraints
    output_field: OutputType = dspy.OutputField(
        desc="Expected output format and constraints"
    )
```

**Example - Intent Extraction**:
```python
class ExtractIntent(dspy.Signature):
    """Extract structured intent specification from natural language."""

    prompt: str = dspy.InputField(
        desc="User's natural language description of desired functionality"
    )

    domain_context: str = dspy.InputField(
        desc="Optional project context, related code, or dependencies",
        default=""
    )

    intent_summary: str = dspy.OutputField(
        desc="Concise 1-2 sentence summary of what the code should do"
    )

    user_personas: list[str] = dspy.OutputField(
        desc="List of intended users or consumers of this functionality"
    )

    success_criteria: list[str] = dspy.OutputField(
        desc="Specific, measurable conditions that define successful execution"
    )

    domain_concepts: list[str] = dspy.OutputField(
        desc="Key domain entities, concepts, or terminology mentioned"
    )
```

**Module usage**:
```python
# Create module
extract_intent = dspy.ChainOfThought(ExtractIntent)

# Execute
result = await extract_intent(
    prompt="Create a function that validates email addresses and checks domain existence",
    domain_context="Python backend service, using requests library"
)

# Access outputs
print(result.intent_summary)
# → "Validate email address format and verify domain exists via DNS/HTTP"

print(result.success_criteria)
# → ["Returns True for valid emails with reachable domains",
#     "Returns False for malformed emails",
#     "Returns False for emails with non-existent domains",
#     "Handles network timeouts gracefully"]
```

### 3.3 Module Types

**ChainOfThought**: Adds reasoning trace before output
```python
cot = dspy.ChainOfThought(ExtractIntent)
# Internal: "Let's think step by step: First, identify the main action..."
```

**Predict**: Direct prediction without reasoning
```python
predict = dspy.Predict(ExtractIntent)
# Internal: Just generates output directly
```

**ReAct**: Reasoning + acting in environment
```python
react = dspy.ReAct(ExtractIntent)
# Internal: "Observation: ... → Thought: ... → Action: ..."
```

**ProgramOfThought**: Code-based reasoning
```python
pot = dspy.ProgramOfThought(ExtractIntent)
# Internal: Generates Python code to solve task
```

### 3.4 Optimizers

**MIPROv2** (Multi-prompt Instruction PRoposal Optimizer v2):
- **Goal**: Learn better instructions, examples, reasoning traces
- **Method**: Bayesian optimization over prompt space
- **Input**: Training examples with ground truth
- **Output**: Optimized module with improved prompts

**BootstrapFewShot**:
- **Goal**: Self-supervised learning from unlabeled data
- **Method**: Generate synthetic examples via self-prompting
- **Input**: Task signature + small seed set
- **Output**: Module with bootstrapped few-shot examples

**COPRO** (Chain-of-Prompts Optimizer):
- **Goal**: Optimize multi-step pipelines end-to-end
- **Method**: Gradient descent on prompt parameters
- **Input**: Pipeline + validation metric
- **Output**: Jointly optimized pipeline

### 3.5 Evaluation Metrics

**Success metrics for lift**:

```python
from dspy.evaluate import Evaluate

def ir_compilation_success(example, prediction, trace=None):
    """
    Metric: Does generated IR compile and validate?

    Returns 1.0 if IR is valid, 0.0 otherwise.
    """
    try:
        ir = IRProgram.model_validate_json(prediction.ir_json)
        validator = IRValidator()
        result = validator.validate(ir)
        return 1.0 if result.is_valid else 0.0
    except Exception:
        return 0.0

def ir_similarity(example, prediction, trace=None):
    """
    Metric: How similar is generated IR to ground truth?

    Returns float in [0.0, 1.0] based on:
    - Intent similarity (embeddings)
    - Signature match (exact)
    - Assertion overlap (Jaccard)
    """
    predicted_ir = IRProgram.model_validate_json(prediction.ir_json)
    expected_ir = example.expected_ir

    # Intent similarity via embeddings
    intent_score = cosine_similarity(
        embed(predicted_ir.intent.summary),
        embed(expected_ir.intent.summary)
    )

    # Signature exact match
    sig_score = 1.0 if (
        predicted_ir.signature.name == expected_ir.signature.name and
        len(predicted_ir.signature.parameters) == len(expected_ir.signature.parameters)
    ) else 0.5

    # Assertion overlap (Jaccard)
    pred_asserts = {a.expression for a in predicted_ir.assertions}
    exp_asserts = {a.expression for a in expected_ir.assertions}
    assert_score = len(pred_asserts & exp_asserts) / len(pred_asserts | exp_asserts)

    return (intent_score + sig_score + assert_score) / 3.0

# Create evaluator
evaluator = Evaluate(
    devset=test_examples,
    metric=ir_similarity,
    num_threads=4,
    display_progress=True,
)

# Evaluate module
score = evaluator(extract_intent)
print(f"IR Similarity: {score:.2%}")
```

---

## 4. Six Core Signatures

### 4.1 Signature 1: PromptToIR

**Purpose**: Generate complete IR program from natural language prompt.

**Route**: Modal Inference (requires XGrammar for IR schema validation)

**Signature**:
```python
class PromptToIR(dspy.Signature):
    """
    Generate formal IR 0.9 program from natural language description.

    Output must be valid JSON conforming to IRProgram schema.
    Uses XGrammar-constrained generation for syntactic correctness.
    """

    prompt: str = dspy.InputField(
        desc="Natural language description of desired functionality"
    )

    domain_context: str = dspy.InputField(
        desc="Project context: dependencies, existing code, architectural constraints",
        default=""
    )

    ir_program: str = dspy.OutputField(
        desc="Valid IR 0.9 JSON program with intent, signature, assertions, effects"
    )
```

**Usage**:
```python
# Configure Modal provider with XGrammar
modal_provider = ModalProvider(
    model="meta-llama/Llama-3.1-70B-Instruct",
    gpu="L40S",
    xgrammar_enabled=True,
)

adapter = ProviderAdapter(
    modal_provider=modal_provider,
    best_available_provider=None,  # Not needed for this signature
    config=ProviderConfig(),
)

# Create module
generate_ir = dspy.ChainOfThought(PromptToIR)

# Configure DSPy to use adapter
dspy.settings.configure(lm=adapter)

# Execute with XGrammar constraints
result = await generate_ir(
    prompt="Create a function that validates email addresses",
    domain_context="Python 3.11, no external dependencies",
    schema=IRProgram,  # Triggers Modal route + XGrammar
)

ir = IRProgram.model_validate_json(result.ir_program)
print(f"Generated: {ir.signature.name}")
# → "validate_email"
```

**Optimization target**: 60% → 85% compilation success rate

### 4.2 Signature 2: ExtractIntent

**Purpose**: Extract structured intent specification from natural language.

**Route**: Best Available (no schema needed, pure reasoning task)

**Signature**:
```python
class ExtractIntent(dspy.Signature):
    """
    Extract structured intent specification from natural language.

    Intent captures WHAT the user wants, not HOW to implement it.
    Focuses on goals, users, success criteria, domain concepts.
    """

    prompt: str = dspy.InputField(
        desc="User's natural language prompt"
    )

    intent_summary: str = dspy.OutputField(
        desc="Concise 1-2 sentence summary of intent"
    )

    user_personas: list[str] = dspy.OutputField(
        desc="List of intended users or consumers"
    )

    success_criteria: list[str] = dspy.OutputField(
        desc="Specific, measurable success conditions"
    )

    domain_concepts: list[str] = dspy.OutputField(
        desc="Key domain entities or concepts"
    )
```

**Usage**:
```python
# Routes to Claude 3.5 Sonnet (best reasoning)
extract_intent = dspy.ChainOfThought(ExtractIntent)

result = await extract_intent(
    prompt="Build a rate limiter for API endpoints using Redis"
)

print(result.intent_summary)
# → "Implement distributed rate limiting for API requests using Redis as backing store"

print(result.user_personas)
# → ["API developers", "DevOps engineers", "System architects"]

print(result.success_criteria)
# → ["Limits requests per user per time window",
#     "Distributes limit tracking across Redis cluster",
#     "Returns 429 status when limit exceeded",
#     "Handles Redis failures gracefully"]
```

**Optimization target**: 70% → 87% intent accuracy (human evaluation)

### 4.3 Signature 3: RefineIR

**Purpose**: Refine IR based on user feedback or validation errors.

**Route**: Modal Inference (requires XGrammar for IR output)

**Signature**:
```python
class RefineIR(dspy.Signature):
    """
    Refine IR program based on user feedback or validation failures.

    Applies targeted changes while preserving correct parts.
    Outputs valid IR 0.9 JSON with refinements applied.
    """

    current_ir: str = dspy.InputField(
        desc="Current IR program as JSON string"
    )

    feedback: str = dspy.InputField(
        desc="User feedback or validation error message describing needed changes"
    )

    refinement_type: str = dspy.InputField(
        desc="Type of refinement: 'add_constraint', 'fix_type', 'clarify_intent', 'add_effect'"
    )

    refined_ir: str = dspy.OutputField(
        desc="Updated IR program JSON with refinements applied"
    )

    changes_summary: str = dspy.OutputField(
        desc="Human-readable summary of changes made (for provenance)"
    )
```

**Usage**:
```python
refine_ir = dspy.ChainOfThought(RefineIR)

result = await refine_ir(
    current_ir=ir.model_dump_json(),
    feedback="Add precondition that email parameter cannot be empty",
    refinement_type="add_constraint",
    schema=IRProgram,  # Triggers Modal route
)

refined_ir = IRProgram.model_validate_json(result.refined_ir)
print(result.changes_summary)
# → "Added precondition: len(email) > 0"
```

**Optimization target**: 85% refinement correctness (preserves valid parts, fixes issue)

### 4.4 Signature 4: VerifyIR

**Purpose**: Verify IR program and generate detailed validation report.

**Route**: Best Available (analysis task, no schema needed)

**Signature**:
```python
class VerifyIR(dspy.Signature):
    """
    Verify IR program for correctness and generate validation report.

    Checks:
    - Type consistency
    - Refinement type satisfiability
    - Assertion coherence
    - Effect completeness
    - Hole closure rules
    """

    ir_program: str = dspy.InputField(
        desc="IR program JSON to verify"
    )

    validation_report: dict = dspy.OutputField(
        desc="Structured validation report with errors, warnings, suggestions"
    )
```

**Usage**:
```python
verify_ir = dspy.ChainOfThought(VerifyIR)

result = await verify_ir(
    ir_program=ir.model_dump_json()
)

report = result.validation_report
if report["errors"]:
    print("Errors found:")
    for error in report["errors"]:
        print(f"  - {error['message']} at {error['location']}")
```

**Optimization target**: 90% error detection recall (catches actual issues)

### 4.5 Signature 5: GenerateCode

**Purpose**: Generate target language code from verified IR.

**Route**: Best Available (code generation, no schema needed unless type-safe output required)

**Signature**:
```python
class GenerateCode(dspy.Signature):
    """
    Generate target language code from verified IR program.

    Code must:
    - Implement IR signature exactly
    - Include all assertions as runtime checks
    - Document effects clearly
    - Follow target language best practices
    """

    ir_program: str = dspy.InputField(
        desc="Verified IR program JSON"
    )

    target_lang: str = dspy.InputField(
        desc="Target language: 'python', 'rust', 'go', 'typescript'"
    )

    code: str = dspy.OutputField(
        desc="Generated code implementing IR specification"
    )

    implementation_notes: str = dspy.OutputField(
        desc="Notes on implementation choices, trade-offs, limitations"
    )
```

**Usage**:
```python
# Routes to GPT-4 Turbo (best code generation)
generate_code = dspy.ChainOfThought(GenerateCode)

result = await generate_code(
    ir_program=ir.model_dump_json(),
    target_lang="python"
)

print(result.code)
# → Generated Python function

print(result.implementation_notes)
# → "Used re module for regex validation. Domain check uses socket.getaddrinfo."
```

**Optimization target**: 80% → 95% compilation rate, 60% → 90% execution success

### 4.6 Signature 6: ExplainCode

**Purpose**: Generate natural language explanation from code/IR.

**Route**: Best Available (reasoning task)

**Signature**:
```python
class ExplainCode(dspy.Signature):
    """
    Generate clear natural language explanation of code functionality.

    Explanation should:
    - Describe what the code does (intent)
    - Explain how it works (mechanism)
    - Highlight constraints and edge cases
    - Note effects and side effects
    """

    code: str = dspy.InputField(
        desc="Source code to explain"
    )

    ir_program: str | None = dspy.InputField(
        desc="Optional IR program for semantic context",
        default=None
    )

    explanation: str = dspy.OutputField(
        desc="Clear, structured explanation suitable for documentation"
    )
```

**Usage**:
```python
explain_code = dspy.ChainOfThought(ExplainCode)

result = await explain_code(
    code=generated_code,
    ir_program=ir.model_dump_json()
)

print(result.explanation)
# → "This function validates email addresses by checking format and domain existence..."
```

**Optimization target**: 85% explanation quality (human evaluation)

---

## 5. ProviderAdapter Implementation (H1)

### 5.1 Architecture

**Resolved in Phase 2**: 277 lines, 25 tests passing

**Key responsibilities**:
1. **Route determination**: Analyze task requirements, select provider
2. **Fallback logic**: Graceful degradation on provider failure
3. **Metrics tracking**: Latency, cost, success rate per route
4. **Resource tracking**: Integration with H14 ResourceLimits
5. **Observability**: Provenance metadata for all calls

### 5.2 Complete Implementation

```python
"""
Provider Adapter (H1): Dual-route LLM integration layer.

Routes LLM requests to appropriate provider based on infrastructure
requirements. Implements ADR 001.
"""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass
import time
import dspy
from pydantic import BaseModel

class ProviderRoute(Enum):
    """Available provider routes."""
    BEST_AVAILABLE = "best_available"
    MODAL_INFERENCE = "modal_inference"

@dataclass
class RouteMetrics:
    """Track metrics per route."""
    decisions: dict[ProviderRoute, int] = field(default_factory=lambda: defaultdict(int))
    successes: dict[ProviderRoute, int] = field(default_factory=lambda: defaultdict(int))
    failures: dict[ProviderRoute, int] = field(default_factory=lambda: defaultdict(int))
    latencies: dict[ProviderRoute, list[float]] = field(default_factory=lambda: defaultdict(list))
    costs: dict[ProviderRoute, list[float]] = field(default_factory=lambda: defaultdict(list))

    def record_decision(self, route: ProviderRoute, prompt: str):
        """Record route decision."""
        self.decisions[route] += 1

    def record_success(self, route: ProviderRoute):
        """Record successful execution."""
        self.successes[route] += 1

    def record_failure(self, route: ProviderRoute, error: str):
        """Record failed execution."""
        self.failures[route] += 1

    def record_latency(self, route: ProviderRoute, latency_ms: float):
        """Record execution latency."""
        self.latencies[route].append(latency_ms)

    def record_cost(self, route: ProviderRoute, cost: float):
        """Record execution cost."""
        self.costs[route].append(cost)

    def get_success_rate(self, route: ProviderRoute) -> float:
        """Calculate success rate for route."""
        total = self.successes[route] + self.failures[route]
        return self.successes[route] / total if total > 0 else 0.0

    def get_avg_latency(self, route: ProviderRoute) -> float:
        """Calculate average latency for route."""
        latencies = self.latencies[route]
        return sum(latencies) / len(latencies) if latencies else 0.0

    def get_total_cost(self, route: ProviderRoute) -> float:
        """Calculate total cost for route."""
        return sum(self.costs[route])

class ProviderAdapter:
    """
    Dual-route LLM integration layer.

    Implements ADR 001 dual-provider routing strategy.
    Routes requests based on infrastructure requirements:
    - Best Available: Standard API calls (Claude/GPT-4/Gemini)
    - Modal Inference: XGrammar/llguidance/aici support

    Features:
    - Automatic route determination
    - Fallback on failure
    - Metrics tracking per route
    - Resource usage tracking
    - Provenance metadata
    """

    def __init__(
        self,
        modal_provider: "ModalProvider",
        best_available_provider: Optional["BestAvailableProvider"] = None,
        config: "ProviderConfig" = None,
    ):
        """
        Initialize provider adapter.

        Args:
            modal_provider: Modal inference provider (required)
            best_available_provider: Best available provider (optional, Phase 3)
            config: Provider configuration
        """
        self.modal = modal_provider
        self.best_available = best_available_provider
        self.config = config or ProviderConfig()
        self.route_metrics = RouteMetrics()
        self.resource_tracker: Optional["ResourceUsage"] = None

    def set_resource_tracker(self, tracker: "ResourceUsage"):
        """Set resource tracker for monitoring."""
        self.resource_tracker = tracker

    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        llguidance_grammar: str | None = None,
        **kwargs
    ) -> dspy.Prediction:
        """
        Execute LLM call with automatic routing.

        Args:
            prompt: Input prompt
            schema: Optional Pydantic schema for structured output
            llguidance_grammar: Optional grammar for constrained generation
            **kwargs: Additional provider-specific arguments

        Returns:
            DSPy Prediction with generated output and metadata

        Raises:
            ProviderError: On provider failure (if fallback disabled)
        """
        # Track LLM call
        if self.resource_tracker:
            self.resource_tracker.add_llm_call()

        # Determine route
        route = self._determine_route(
            schema=schema,
            llguidance_grammar=llguidance_grammar,
            **kwargs
        )

        # Track decision
        self.route_metrics.record_decision(route, prompt)

        try:
            # Execute based on route
            if route == ProviderRoute.MODAL_INFERENCE:
                result = await self._call_modal(prompt, schema, **kwargs)
            else:
                result = await self._call_best_available(prompt, **kwargs)

            # Track success
            self.route_metrics.record_success(route)

            # Track tokens
            if self.resource_tracker and hasattr(result, 'tokens_used'):
                self.resource_tracker.add_tokens(result.tokens_used)

            return result

        except Exception as e:
            # Track failure
            self.route_metrics.record_failure(route, error=str(e))

            # Attempt fallback if enabled
            if self.config.enable_fallback and self._can_fallback(route):
                return await self._fallback(prompt, route, **kwargs)

            raise

    def _determine_route(self, **kwargs) -> ProviderRoute:
        """
        Determine which provider route to use.

        Routes to Modal Inference if ANY of these are present:
        - schema: Pydantic model (requires XGrammar)
        - llguidance_grammar: Grammar string
        - aici_control: AICI controller
        - speculative_decode: Enable parallel speculative decoding
        - custom_sampling: Custom temperature/top_p per token

        Otherwise routes to Best Available.

        Manual override: Set force_route="best_available" or "modal_inference"
        """
        # Check for manual override
        if override := kwargs.get("force_route"):
            return ProviderRoute(override)

        # Check for inference system requirements
        requires_modal = any([
            kwargs.get("schema") is not None,
            kwargs.get("llguidance_grammar") is not None,
            kwargs.get("aici_control") is not None,
            kwargs.get("speculative_decode", False),
            kwargs.get("custom_sampling", False),
        ])

        if requires_modal:
            return ProviderRoute.MODAL_INFERENCE

        return ProviderRoute.BEST_AVAILABLE

    async def _call_modal(
        self,
        prompt: str,
        schema: BaseModel | None,
        **kwargs
    ) -> dspy.Prediction:
        """
        Call Modal inference system.

        Supports:
        - XGrammar-constrained generation (via schema)
        - llguidance grammars
        - aici control
        - Parallel speculative decoding
        """
        start_time = time.time()

        # Prepare schema for XGrammar
        schema_dict = schema.model_json_schema() if schema else None

        # Execute on Modal
        result = await self.modal.generate(
            prompt=prompt,
            schema=schema_dict,
            llguidance_grammar=kwargs.get("llguidance_grammar"),
            aici_control=kwargs.get("aici_control"),
            speculative_decode=kwargs.get("speculative_decode", False),
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )

        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        self.route_metrics.record_latency(ProviderRoute.MODAL_INFERENCE, duration_ms)
        self.route_metrics.record_cost(
            ProviderRoute.MODAL_INFERENCE,
            self._compute_modal_cost(duration_ms)
        )

        # Return with metadata
        return dspy.Prediction(
            **result,
            _route=ProviderRoute.MODAL_INFERENCE.value,
            _latency_ms=duration_ms,
            _model=self.modal.model_name,
        )

    async def _call_best_available(
        self,
        prompt: str,
        **kwargs
    ) -> dspy.Prediction:
        """
        Call best available provider (Anthropic/OpenAI/Google).

        Tries providers in priority order until success.
        Priority: Claude 3.5 Sonnet > GPT-4 Turbo > Gemini 1.5 Pro
        """
        if not self.best_available:
            raise ProviderError("Best Available provider not configured (Phase 3)")

        start_time = time.time()

        # Execute via best available
        result = await self.best_available.generate(
            prompt=prompt,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            provider_priority=self.config.provider_priority,
        )

        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        self.route_metrics.record_latency(ProviderRoute.BEST_AVAILABLE, duration_ms)
        self.route_metrics.record_cost(
            ProviderRoute.BEST_AVAILABLE,
            self._compute_api_cost(result.tokens_used, result.model)
        )

        # Return with metadata
        return dspy.Prediction(
            **result,
            _route=ProviderRoute.BEST_AVAILABLE.value,
            _latency_ms=duration_ms,
            _model=result.model,
        )

    def _can_fallback(self, failed_route: ProviderRoute) -> bool:
        """Check if fallback is possible."""
        if failed_route == ProviderRoute.MODAL_INFERENCE:
            # Can fallback to Best Available if available
            return self.best_available is not None
        else:
            # Can fallback to Modal
            return self.modal is not None

    async def _fallback(
        self,
        prompt: str,
        failed_route: ProviderRoute,
        **kwargs
    ) -> dspy.Prediction:
        """
        Fallback to alternative route on failure.

        Fallback strategy:
        - Modal → Best Available: Strip schema, attempt generation
        - Best Available → Modal: Add minimal schema, use Modal
        """
        if failed_route == ProviderRoute.MODAL_INFERENCE:
            # Try Best Available without schema requirements
            return await self._call_best_available(
                prompt=prompt,
                **{k: v for k, v in kwargs.items()
                   if k not in ["schema", "llguidance_grammar", "aici_control"]}
            )
        else:
            # Try Modal with minimal schema
            return await self._call_modal(
                prompt=prompt,
                schema=None,
                **kwargs
            )

    def _compute_modal_cost(self, duration_ms: float) -> float:
        """
        Compute cost for Modal GPU usage.

        Pricing (as of 2025-10):
        - T4: $0.60/hour = $0.000167/second
        - L40S: $1.50/hour = $0.000417/second
        - H100: $4.00/hour = $0.001111/second
        """
        gpu_cost_per_second = {
            "T4": 0.000167,
            "L40S": 0.000417,
            "H100": 0.001111,
        }

        gpu_type = self.config.modal_gpu or "L40S"
        cost_per_second = gpu_cost_per_second[gpu_type]

        return (duration_ms / 1000) * cost_per_second

    def _compute_api_cost(self, tokens_used: int, model: str) -> float:
        """
        Compute cost for API usage.

        Pricing (as of 2025-10, per million tokens):
        - Claude 3.5 Sonnet: $3.00 input, $15.00 output
        - GPT-4 Turbo: $10.00 input, $30.00 output
        - Gemini 1.5 Pro: $1.25 input, $5.00 output
        """
        # Simplified: assume 50/50 input/output split
        pricing = {
            "claude-3-5-sonnet": (3.00 + 15.00) / 2 / 1_000_000,
            "gpt-4-turbo": (10.00 + 30.00) / 2 / 1_000_000,
            "gemini-1.5-pro": (1.25 + 5.00) / 2 / 1_000_000,
        }

        cost_per_token = pricing.get(model, 0.00001)
        return tokens_used * cost_per_token

    def get_route_stats(self) -> dict[str, Any]:
        """Get route usage statistics."""
        return {
            "best_available": {
                "requests": self.route_metrics.decisions[ProviderRoute.BEST_AVAILABLE],
                "success_rate": self.route_metrics.get_success_rate(ProviderRoute.BEST_AVAILABLE),
                "avg_latency_ms": self.route_metrics.get_avg_latency(ProviderRoute.BEST_AVAILABLE),
                "total_cost": self.route_metrics.get_total_cost(ProviderRoute.BEST_AVAILABLE),
            },
            "modal_inference": {
                "requests": self.route_metrics.decisions[ProviderRoute.MODAL_INFERENCE],
                "success_rate": self.route_metrics.get_success_rate(ProviderRoute.MODAL_INFERENCE),
                "avg_latency_ms": self.route_metrics.get_avg_latency(ProviderRoute.MODAL_INFERENCE),
                "total_cost": self.route_metrics.get_total_cost(ProviderRoute.MODAL_INFERENCE),
            }
        }
```

### 5.3 Configuration

```python
@dataclass
class ProviderConfig:
    """Provider adapter configuration."""

    # Routing
    enable_fallback: bool = True
    force_route: ProviderRoute | None = None

    # Modal settings
    modal_gpu: str = "L40S"  # T4, L40S, H100
    modal_timeout: int = 300  # seconds

    # Best Available settings
    provider_priority: list[str] = field(default_factory=lambda: [
        "anthropic_claude_3_5_sonnet",
        "openai_gpt_4_turbo",
        "google_gemini_1_5_pro",
    ])

    # Retry settings
    max_retries: int = 3
    retry_backoff: float = 2.0  # exponential backoff multiplier

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = True

# Usage
config = ProviderConfig(
    modal_gpu="L40S",
    provider_priority=[
        "anthropic_claude_3_5_sonnet",  # Best reasoning
        "openai_gpt_4_turbo",           # Fallback
    ],
    enable_fallback=True,
)

adapter = ProviderAdapter(
    modal_provider=modal,
    best_available_provider=best,
    config=config,
)
```

---

## 6. Modal SGLang Deployment

### 6.1 Modal Infrastructure

**Modal.com**: Serverless compute platform for ML inference.

**Benefits for lift**:
- On-demand GPU provisioning
- Auto-scaling based on load
- Built-in logging and monitoring
- Easy deployment via Python decorators

### 6.2 GPU Configuration

**GPU options**:

| GPU | Cost/hr | Memory | Throughput | Use Case |
|-----|---------|--------|------------|----------|
| T4 | $0.60 | 16 GB | Low | Development, testing |
| L40S | $1.50 | 48 GB | High | Production (sweet spot) |
| H100 | $4.00 | 80 GB | Max | Large models, max performance |

**Recommendation**: L40S for production (best cost/performance ratio)

### 6.3 SGLang + XGrammar Integration

**SGLang**: Fast inference system with RadixAttention and structured output support.

**XGrammar**: Constrained decoding library ensuring syntactic correctness.

**Modal deployment**:

```python
import modal

app = modal.App("lift-inference")

# Define container image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "sglang[all]==0.2.0",
        "xgrammar==0.1.0",
        "pydantic==2.9.0",
        "torch==2.1.0",
    )
    .run_commands(
        "pip install flash-attn --no-build-isolation",  # Flash Attention 2
    )
)

# Define inference function
@app.function(
    image=image,
    gpu=modal.gpu.L40S(),  # L40S GPU
    timeout=300,            # 5 minute timeout
    container_idle_timeout=60,  # Keep warm for 60s
    allow_concurrent_inputs=10,  # Handle 10 concurrent requests
)
async def generate_ir(
    prompt: str,
    schema: dict | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict:
    """
    Generate IR with XGrammar-constrained decoding.

    Args:
        prompt: Input prompt
        schema: JSON schema for XGrammar constraints
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature

    Returns:
        Dictionary with:
        - text: Generated text
        - tokens_used: Total tokens consumed
        - latency_ms: Generation latency
    """
    import sglang as sgl
    import time

    # Initialize runtime (cached across calls)
    runtime = sgl.Runtime(
        model_path="meta-llama/Llama-3.1-70B-Instruct",
        tokenizer_path="meta-llama/Llama-3.1-70B-Instruct",
        tp_size=1,  # Tensor parallelism
        xgrammar_backend=True,  # Enable XGrammar
        enable_flashinfer=True,  # Flash Attention
    )

    start_time = time.time()

    # Generate with XGrammar constraints
    if schema:
        result = runtime.generate(
            prompt=prompt,
            schema=schema,  # XGrammar enforces this
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        result = runtime.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    latency_ms = (time.time() - start_time) * 1000

    return {
        "text": result.text,
        "tokens_used": result.meta_info.get("prompt_tokens", 0) +
                      result.meta_info.get("completion_tokens", 0),
        "latency_ms": latency_ms,
    }

# Deploy
if __name__ == "__main__":
    with app.run():
        result = generate_ir.remote(
            prompt="Create a function to validate emails",
            schema=IRProgram.model_json_schema(),
        )
        print(result)
```

### 6.4 XGrammar Schema Example

**XGrammar enforces JSON schema**:

```python
from pydantic import BaseModel

class IRProgram(BaseModel):
    """IR 0.9 Program structure."""
    intent: IntentSpec
    signature: FuncSpec
    assertions: list[AssertClause]
    effects: list[EffectClause]

# Convert to JSON schema
schema = IRProgram.model_json_schema()

# XGrammar uses this to constrain generation token-by-token
# Guarantees output is valid JSON conforming to schema
```

**Benefits**:
- **100% syntactic correctness**: Invalid JSON impossible
- **Type safety**: Field types enforced during generation
- **Performance**: No retries needed for parse errors
- **Reduced latency**: Single pass generation

### 6.5 Modal Function Decorators

**Key parameters**:

```python
@app.function(
    image=image,                    # Container image
    gpu=modal.gpu.L40S(),           # GPU type
    timeout=300,                    # Max execution time (seconds)
    container_idle_timeout=60,      # Keep container warm (seconds)
    allow_concurrent_inputs=10,     # Concurrent request limit
    retries=3,                      # Retry on failure
    secrets=[modal.Secret.from_name("hf-token")],  # HuggingFace token
)
```

**Container lifecycle**:
1. Cold start: ~30s to provision GPU + load model
2. Warm: <100ms if container already running
3. Idle timeout: Container kept warm for specified duration

**Optimization**: Keep containers warm during active hours, shut down overnight.

---

## 7. Best Available Provider

### 7.1 Provider Integration

**Phase 3 implementation** (current: Modal only)

**Providers**:
1. **Anthropic Claude 3.5 Sonnet**: Best reasoning, intent extraction
2. **OpenAI GPT-4 Turbo**: Best code generation
3. **Google Gemini 1.5 Pro**: Best multimodal (future: image/diagram support)

### 7.2 Priority and Fallback

**Strategy**: Try providers in priority order until success.

```python
class BestAvailableProvider:
    """
    Best available provider integration.

    Tries providers in priority order:
    1. Anthropic Claude 3.5 Sonnet (best reasoning)
    2. OpenAI GPT-4 Turbo (fallback)
    3. Google Gemini 1.5 Pro (fallback)

    Implements circuit breaker: After 5 consecutive failures,
    skip provider for 5 minutes.
    """

    def __init__(self, provider_priority: list[str]):
        self.provider_priority = provider_priority
        self.circuit_breakers = {}  # provider -> CircuitBreaker

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> dict:
        """
        Generate via best available provider.

        Tries providers in priority order until success.
        Skips providers with open circuit breakers.
        """
        last_error = None

        for provider_name in self.provider_priority:
            # Check circuit breaker
            breaker = self.circuit_breakers.get(provider_name)
            if breaker and breaker.is_open():
                continue

            try:
                result = await self._call_provider(
                    provider_name,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                # Success: Close circuit breaker
                if breaker:
                    breaker.record_success()

                return result

            except Exception as e:
                last_error = e

                # Record failure
                if not breaker:
                    breaker = CircuitBreaker(threshold=5, timeout=300)
                    self.circuit_breakers[provider_name] = breaker

                breaker.record_failure()

                # Try next provider
                continue

        # All providers failed
        raise ProviderError(f"All providers failed. Last error: {last_error}")

    async def _call_provider(
        self,
        provider_name: str,
        prompt: str,
        **kwargs
    ) -> dict:
        """Call specific provider."""
        if provider_name.startswith("anthropic"):
            return await self._call_anthropic(prompt, **kwargs)
        elif provider_name.startswith("openai"):
            return await self._call_openai(prompt, **kwargs)
        elif provider_name.startswith("google"):
            return await self._call_google(prompt, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    async def _call_anthropic(self, prompt: str, **kwargs) -> dict:
        """Call Anthropic API."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "text": response.content[0].text,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "model": "claude-3-5-sonnet",
        }

    async def _call_openai(self, prompt: str, **kwargs) -> dict:
        """Call OpenAI API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

        response = await client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "text": response.choices[0].message.content,
            "tokens_used": response.usage.prompt_tokens + response.usage.completion_tokens,
            "model": "gpt-4-turbo",
        }

    async def _call_google(self, prompt: str, **kwargs) -> dict:
        """Call Google Gemini API."""
        import google.generativeai as genai

        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-pro")

        response = await model.generate_content_async(
            prompt,
            generation_config={
                "max_output_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            }
        )

        return {
            "text": response.text,
            "tokens_used": response.usage_metadata.prompt_token_count +
                          response.usage_metadata.candidates_token_count,
            "model": "gemini-1.5-pro",
        }

class CircuitBreaker:
    """Circuit breaker for provider failures."""

    def __init__(self, threshold: int = 5, timeout: int = 300):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: float | None = None

    def record_failure(self):
        """Record a failure."""
        self.failures += 1
        self.last_failure_time = time.time()

    def record_success(self):
        """Record a success (closes breaker)."""
        self.failures = 0
        self.last_failure_time = None

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.failures < self.threshold:
            return False

        # Check if timeout expired
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.timeout:
                # Reset breaker
                self.failures = 0
                self.last_failure_time = None
                return False

        return True
```

### 7.3 API Integration Examples

**Anthropic Claude 3.5 Sonnet**:
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": "Extract intent from: Build a rate limiter"
    }]
)

print(response.content[0].text)
```

**OpenAI GPT-4 Turbo**:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

response = await client.chat.completions.create(
    model="gpt-4-turbo-2024-04-09",
    messages=[{
        "role": "user",
        "content": "Generate Python code for email validation"
    }]
)

print(response.choices[0].message.content)
```

**Google Gemini 1.5 Pro**:
```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-pro")

response = await model.generate_content_async(
    "Explain this code: def validate_email(email): ..."
)

print(response.text)
```

---

## 8. MIPROv2 Optimization

### 8.1 Optimization Overview

**MIPROv2** (Multi-prompt Instruction PRoposal Optimizer v2):
- Automatic prompt optimization via Bayesian search
- Learns better instructions, examples, reasoning traces
- Targets specific metrics (accuracy, F1, similarity)
- Iterative improvement (20-50 iterations typical)

**Research results**: 15-25% quality improvement with 50 training examples

### 8.2 Training Data Collection

**Example structure**:
```python
from dspy import Example

# Training example for PromptToIR
example = Example(
    prompt="Create a function that validates email addresses",
    domain_context="Python 3.11, no external dependencies",
    expected_ir=IRProgram(
        intent=IntentSpec(
            summary="Validate email address format using regular expressions",
            success_criteria=[
                "Returns True for valid emails",
                "Returns False for invalid emails",
                "Handles edge cases (multiple @, no domain)"
            ]
        ),
        signature=FuncSpec(
            name="validate_email",
            parameters=[Param(name="email", type="str")],
            returns="bool"
        ),
        assertions=[
            AssertClause(
                category="precondition",
                expression="isinstance(email, str)"
            )
        ],
        effects=[]
    ).model_dump_json()
).with_inputs("prompt", "domain_context")

# Training set
train_examples = [example1, example2, ...  # 50-200 examples
```

**Sources**:
- **Manual curation**: 20-50 hand-crafted examples
- **User sessions**: High-quality sessions (score ≥4/5)
- **Synthetic generation**: DSPy BootstrapFewShot

### 8.3 Metrics Definition

**IR Similarity**:
```python
def ir_similarity_metric(example, prediction, trace=None) -> float:
    """
    Compute IR similarity score (0.0-1.0).

    Components:
    - Intent similarity (40%): Embedding cosine similarity
    - Signature match (30%): Exact name + parameter count
    - Assertion overlap (30%): Jaccard similarity
    """
    predicted_ir = IRProgram.model_validate_json(prediction.ir_program)
    expected_ir = IRProgram.model_validate_json(example.expected_ir)

    # Intent similarity via embeddings
    intent_score = cosine_similarity(
        embed(predicted_ir.intent.summary),
        embed(expected_ir.intent.summary)
    )

    # Signature exact match
    sig_score = 1.0 if (
        predicted_ir.signature.name == expected_ir.signature.name and
        len(predicted_ir.signature.parameters) == len(expected_ir.signature.parameters)
    ) else 0.5

    # Assertion overlap (Jaccard)
    pred_asserts = {a.expression for a in predicted_ir.assertions}
    exp_asserts = {a.expression for a in expected_ir.assertions}
    if pred_asserts | exp_asserts:
        assert_score = len(pred_asserts & exp_asserts) / len(pred_asserts | exp_asserts)
    else:
        assert_score = 0.0

    return 0.4 * intent_score + 0.3 * sig_score + 0.3 * assert_score
```

**Compilation Success**:
```python
def compilation_success_metric(example, prediction, trace=None) -> float:
    """Binary metric: Does IR compile and validate?"""
    try:
        ir = IRProgram.model_validate_json(prediction.ir_program)
        validator = IRValidator()
        result = validator.validate(ir)
        return 1.0 if result.is_valid else 0.0
    except Exception:
        return 0.0
```

### 8.4 Optimization Execution

```python
from dspy.teleprompt import MIPROv2
from dspy.evaluate import Evaluate

# Define program to optimize
class ForwardModePipeline(dspy.Module):
    def __init__(self):
        self.generate_ir = dspy.ChainOfThought(PromptToIR)

    async def forward(self, prompt, domain_context=""):
        return await self.generate_ir(
            prompt=prompt,
            domain_context=domain_context
        )

# Create optimizer
optimizer = MIPROv2(
    metric=ir_similarity_metric,
    num_candidates=10,          # Generate 10 prompt candidates per iteration
    init_temperature=1.0,       # Initial exploration temperature
    verbose=True,
)

# Run optimization
program = ForwardModePipeline()

optimized_program = optimizer.compile(
    student=program,
    trainset=train_examples,
    num_trials=50,              # 50 optimization iterations
    max_bootstrapped_demos=5,   # Use up to 5 bootstrapped examples
    max_labeled_demos=10,       # Use up to 10 labeled examples
)

# Evaluate baseline vs optimized
evaluator = Evaluate(
    devset=test_examples,
    metric=ir_similarity_metric,
    num_threads=4,
)

baseline_score = evaluator(program)
optimized_score = evaluator(optimized_program)

print(f"Baseline: {baseline_score:.2%}")
print(f"Optimized: {optimized_score:.2%}")
print(f"Improvement: {(optimized_score - baseline_score):.2%}")
```

**Expected trajectory** (based on research):
```
Iteration 0 (Baseline): 60% success rate
Iteration 10: 68% (+8pp)
Iteration 20: 74% (+14pp)
Iteration 30: 79% (+19pp)
Iteration 50: 85% (+25pp) ← Target
```

### 8.5 Prompt Tuning Examples

**Before optimization** (baseline):
```
Generate IR 0.9 program from the following prompt:
{prompt}

Output valid JSON conforming to IRProgram schema.
```

**After optimization** (MIPROv2 learned):
```
You are a formal specification expert. Analyze the user's intent carefully.

User request: {prompt}
Project context: {domain_context}

Generate a complete IR 0.9 program with:
1. Intent: Clear 1-2 sentence summary of what the code should do
2. Signature: Function name, parameters (with types), return type
3. Assertions: Preconditions (what must be true before execution) and postconditions (what must be true after)
4. Effects: Any side effects (I/O, state changes, network calls)

Be specific with types. Use refinement types for constraints (e.g., {x: Int | x > 0}).

Output ONLY valid JSON conforming to IRProgram schema. No preamble, no explanation.

Example:
Prompt: "Create a function to calculate factorial"
Output: {{"intent": {{"summary": "Calculate factorial of non-negative integer"}}, ...}}
```

**Key improvements**:
- Explicit role ("formal specification expert")
- Step-by-step guidance (1-4)
- Type hint emphasis ("Be specific with types")
- Few-shot example
- Clear output format ("ONLY valid JSON")

**Result**: 60% → 85% compilation success

### 8.6 Continuous Learning Pipeline

**Goal**: System improves automatically as data accumulates.

```python
class ContinuousOptimizer:
    """
    Continuous learning pipeline.

    Collects high-quality examples from production usage.
    Triggers optimization when buffer reaches threshold.
    Deploys optimized models automatically.
    """

    def __init__(
        self,
        program: dspy.Module,
        metric: Callable,
        min_examples: int = 100,
        optimization_interval: int = 50,  # iterations
    ):
        self.program = program
        self.metric = metric
        self.min_examples = min_examples
        self.optimization_interval = optimization_interval
        self.example_buffer: list[Example] = []
        self.version = 0

    async def log_example(
        self,
        prompt: str,
        generated_ir: str,
        user_feedback: FeedbackScore,
        **kwargs
    ):
        """
        Log example with user feedback.

        High-quality examples (score ≥4/5) added to buffer.
        """
        if user_feedback.score >= 4:
            example = Example(
                prompt=prompt,
                domain_context=kwargs.get("domain_context", ""),
                expected_ir=generated_ir,
                feedback_score=user_feedback.score,
            ).with_inputs("prompt", "domain_context")

            self.example_buffer.append(example)

        # Trigger optimization when buffer full
        if len(self.example_buffer) >= self.min_examples:
            await self.optimize_and_deploy()

    async def optimize_and_deploy(self):
        """
        Run optimization and deploy new version.

        Steps:
        1. Select best examples from buffer (top 50 by feedback score)
        2. Run MIPROv2 optimization (shorter: 20 iterations)
        3. Validate improvement on test set
        4. Deploy if improvement ≥5%
        5. Clear buffer
        """
        print(f"🔧 Starting optimization with {len(self.example_buffer)} examples")

        # Select best examples
        training_data = sorted(
            self.example_buffer,
            key=lambda ex: ex.feedback_score,
            reverse=True
        )[:50]

        # Optimize
        optimizer = MIPROv2(
            metric=self.metric,
            num_candidates=10,
            init_temperature=1.0,
        )

        optimized_program = optimizer.compile(
            student=self.program,
            trainset=training_data,
            num_trials=20,  # Shorter for continuous optimization
        )

        # Validate improvement
        evaluator = Evaluate(devset=test_set, metric=self.metric)
        baseline_score = evaluator(self.program)
        optimized_score = evaluator(optimized_program)

        improvement = optimized_score - baseline_score

        if improvement >= 0.05:  # 5% threshold
            # Deploy new version
            self.version += 1
            self.program = optimized_program

            # Save model
            self._save_model(self.version, optimized_program)

            print(f"✅ Version {self.version} deployed: {baseline_score:.2%} → {optimized_score:.2%} (+{improvement:.2%})")
        else:
            print(f"⚠️  Improvement insufficient: +{improvement:.2%} < 5% threshold")

        # Clear buffer
        self.example_buffer.clear()

    def _save_model(self, version: int, program: dspy.Module):
        """Save optimized model to registry."""
        path = f"models/forward_mode_v{version}.pkl"
        with open(path, "wb") as f:
            pickle.dump(program, f)

        # Update model registry
        registry.register(
            name=f"forward_mode_v{version}",
            path=path,
            metrics={
                "version": version,
                "training_examples": len(self.example_buffer),
                "timestamp": datetime.now().isoformat(),
            }
        )
```

**Benefits**:
- Automatic quality improvement
- No manual intervention needed
- Safe deployment (5% threshold)
- Model versioning and rollback

---

## 9. Signature Composition

### 9.1 Sequential Chaining

**Pattern**: Output of signature N becomes input to signature N+1.

```python
class IntentToIRPipeline(dspy.Module):
    """
    Sequential pipeline: Extract intent → Generate IR.

    Step 1: ExtractIntent (Best Available route)
    Step 2: PromptToIR (Modal route, uses intent as context)
    """

    def __init__(self):
        self.extract_intent = dspy.ChainOfThought(ExtractIntent)
        self.generate_ir = dspy.ChainOfThought(PromptToIR)

    async def forward(self, prompt: str):
        # Step 1: Extract intent
        intent_result = await self.extract_intent(prompt=prompt)

        # Step 2: Generate IR with intent as context
        ir_result = await self.generate_ir(
            prompt=prompt,
            domain_context=f"""
Intent Summary: {intent_result.intent_summary}

Success Criteria:
{chr(10).join(f"- {c}" for c in intent_result.success_criteria)}

Domain Concepts: {', '.join(intent_result.domain_concepts)}
            """.strip()
        )

        return ir_result
```

**Benefits**:
- Explicit intent extraction step improves IR quality
- Each step optimizable independently
- Clear provenance chain

### 9.2 Parallel Execution

**Pattern**: Execute multiple signatures concurrently, aggregate results.

```python
class MultiCandidateIRGenerator(dspy.Module):
    """
    Generate N IR candidates in parallel, return best.

    Uses ensemble voting to select highest-quality candidate.
    """

    def __init__(self, n_candidates: int = 3):
        self.generators = [
            dspy.ChainOfThought(PromptToIR)
            for _ in range(n_candidates)
        ]
        self.n_candidates = n_candidates

    async def forward(self, prompt: str, domain_context: str = ""):
        # Generate N candidates in parallel
        candidates = await asyncio.gather(*[
            gen(prompt=prompt, domain_context=domain_context)
            for gen in self.generators
        ])

        # Score each candidate
        scores = [
            self._score_ir(c.ir_program)
            for c in candidates
        ]

        # Return best
        best_idx = max(range(self.n_candidates), key=lambda i: scores[i])
        return candidates[best_idx]

    def _score_ir(self, ir_json: str) -> float:
        """
        Score IR quality.

        Metrics:
        - Compilation success (50%)
        - Assertion completeness (30%)
        - Type coverage (20%)
        """
        try:
            ir = IRProgram.model_validate_json(ir_json)

            # Compilation success
            compilation_score = 1.0

            # Assertion completeness (has both pre/post conditions)
            has_pre = any(a.category == "precondition" for a in ir.assertions)
            has_post = any(a.category == "postcondition" for a in ir.assertions)
            assertion_score = (has_pre + has_post) / 2.0

            # Type coverage (all parameters typed)
            typed_params = sum(1 for p in ir.signature.parameters if p.type)
            type_score = typed_params / len(ir.signature.parameters) if ir.signature.parameters else 0.0

            return 0.5 * compilation_score + 0.3 * assertion_score + 0.2 * type_score

        except Exception:
            return 0.0
```

**Benefits**:
- Improved quality via ensemble
- Natural fit for GPU parallelism (Modal)
- Robustness to stochastic failures

### 9.3 Error Handling

**Pattern**: Catch failures, refine, retry.

```python
class RobustIRGenerator(dspy.Module):
    """
    IR generation with automatic error recovery.

    If generation fails validation:
    1. Extract error message
    2. Refine IR via RefineIR signature
    3. Retry (max 3 attempts)
    """

    def __init__(self, max_retries: int = 3):
        self.generate_ir = dspy.ChainOfThought(PromptToIR)
        self.refine_ir = dspy.ChainOfThought(RefineIR)
        self.max_retries = max_retries

    async def forward(self, prompt: str, domain_context: str = ""):
        last_ir = None
        last_error = None

        for attempt in range(self.max_retries):
            try:
                if attempt == 0:
                    # Initial generation
                    result = await self.generate_ir(
                        prompt=prompt,
                        domain_context=domain_context
                    )
                else:
                    # Refinement after error
                    result = await self.refine_ir(
                        current_ir=last_ir,
                        feedback=f"Validation error: {last_error}",
                        refinement_type="fix_validation_error"
                    )

                # Validate
                ir = IRProgram.model_validate_json(result.ir_program)
                validator = IRValidator()
                validation_result = validator.validate(ir)

                if validation_result.is_valid:
                    # Success
                    return result
                else:
                    # Validation failed, prepare for refinement
                    last_ir = result.ir_program
                    last_error = validation_result.errors[0].message

            except Exception as e:
                last_error = str(e)
                continue

        # All retries exhausted
        raise ValidationError(f"Failed after {self.max_retries} attempts. Last error: {last_error}")
```

**Benefits**:
- Automatic recovery from validation failures
- Reduced manual intervention
- Higher success rate

---

## 10. Observability

### 10.1 Tracing

**Every LLM call tracked**:

```python
@dataclass
class LLMTrace:
    """Trace for single LLM call."""
    trace_id: str
    timestamp: datetime
    signature: str                  # Signature name (e.g., "PromptToIR")
    route: ProviderRoute            # best_available or modal_inference
    provider: str                   # Specific provider (e.g., "claude-3-5-sonnet")
    inputs: dict                    # Signature inputs
    outputs: dict                   # Signature outputs
    latency_ms: float               # Execution time
    tokens_used: int                # Total tokens
    cost: float                     # Execution cost
    success: bool                   # Success/failure
    error: str | None               # Error message if failed

# Store in database
CREATE TABLE llm_traces (
    trace_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    session_id TEXT,
    signature TEXT NOT NULL,
    route TEXT NOT NULL,
    provider TEXT NOT NULL,
    inputs TEXT,  -- JSON
    outputs TEXT,  -- JSON
    latency_ms FLOAT,
    tokens_used INT,
    cost FLOAT,
    success BOOLEAN,
    error TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

**Usage**:
```python
# Query traces
traces = db.query("""
    SELECT signature, AVG(latency_ms), AVG(cost)
    FROM llm_traces
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY signature
""")

# Analyze route distribution
route_dist = db.query("""
    SELECT route, COUNT(*), AVG(cost)
    FROM llm_traces
    WHERE timestamp > NOW() - INTERVAL '1 day'
    GROUP BY route
""")
```

### 10.2 Metrics Dashboard

**Key metrics**:

1. **Request volume**: Requests per signature per hour
2. **Success rate**: % successful by signature and route
3. **Latency**: p50, p95, p99 by signature and route
4. **Cost**: Total cost per route, cost per request
5. **Route distribution**: % requests per route
6. **Quality**: Compilation rate, execution rate, user satisfaction

**Grafana dashboard**:
```yaml
panels:
  - title: "Request Volume"
    query: "rate(llm_requests_total[5m])"
    group_by: ["signature", "route"]

  - title: "Success Rate"
    query: "sum(rate(llm_requests_success[5m])) / sum(rate(llm_requests_total[5m]))"
    group_by: ["signature"]

  - title: "Latency (p95)"
    query: "histogram_quantile(0.95, llm_latency_ms)"
    group_by: ["signature", "route"]

  - title: "Cost per Route"
    query: "sum(rate(llm_cost_total[1h]))"
    group_by: ["route"]

  - title: "Quality Metrics"
    query: "compilation_success_rate"
    group_by: ["signature"]
```

### 10.3 Route Analytics

**Route migration analysis**:

```python
def analyze_route_migration_opportunities() -> list[dict]:
    """
    Identify tasks that could migrate from Modal to Best Available.

    Criteria:
    - Currently using Modal route
    - NOT using XGrammar/llguidance/aici
    - Quality ≥ Best Available on similar tasks
    - Cost savings > 20%
    """
    # Query traces
    modal_traces = db.query("""
        SELECT signature, COUNT(*) as count, AVG(cost) as avg_cost
        FROM llm_traces
        WHERE route = 'modal_inference'
          AND timestamp > NOW() - INTERVAL '7 days'
        GROUP BY signature
    """)

    opportunities = []

    for trace in modal_traces:
        # Check if XGrammar actually used
        uses_xgrammar = db.query("""
            SELECT COUNT(*)
            FROM llm_traces
            WHERE signature = ?
              AND route = 'modal_inference'
              AND inputs LIKE '%schema%'
        """, trace.signature)

        if uses_xgrammar == 0:
            # Could potentially migrate
            best_avg_cost = get_best_available_avg_cost(trace.signature)
            cost_savings = (trace.avg_cost - best_avg_cost) / trace.avg_cost

            if cost_savings > 0.2:  # 20% savings threshold
                opportunities.append({
                    "signature": trace.signature,
                    "current_route": "modal_inference",
                    "suggested_route": "best_available",
                    "cost_savings_pct": cost_savings * 100,
                    "monthly_savings": cost_savings * trace.avg_cost * trace.count * 30 / 7,
                })

    return opportunities

# Example output
# [
#   {
#     "signature": "VerifyIR",
#     "current_route": "modal_inference",
#     "suggested_route": "best_available",
#     "cost_savings_pct": 45.2,
#     "monthly_savings": 124.50
#   }
# ]
```

### 10.4 Alerting

**Alert conditions**:

```python
# Success rate degradation
if success_rate < 0.85 for 1 hour:
    alert(severity="warning", message="Success rate dropped to {success_rate:.1%}")

# Latency spike
if p95_latency > 20_000 for 15 minutes:
    alert(severity="warning", message="Latency spike: p95={p95_latency}ms")

# Cost anomaly
if hourly_cost > 2 * avg_hourly_cost:
    alert(severity="critical", message="Cost anomaly: ${hourly_cost:.2f}/hour")

# Provider failure
if provider_success_rate < 0.5 for 5 minutes:
    alert(severity="critical", message="Provider {provider} failing: {provider_success_rate:.1%} success rate")
```

---

## 11. Testing Strategy

### 11.1 Mock Providers

**Test without API calls**:

```python
class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.calls: list[dict] = []

    async def generate(self, prompt: str, **kwargs) -> dict:
        """Mock generation."""
        # Record call
        self.calls.append({
            "prompt": prompt,
            "kwargs": kwargs,
        })

        # Return canned response
        response = self.responses.get(prompt, "Mock response")

        return {
            "text": response,
            "tokens_used": len(response.split()),
            "model": "mock-model",
        }

# Usage in tests
mock_modal = MockProvider({
    "Create a function to validate emails": '{"intent": {"summary": "Validate email format"}, ...}'
})

adapter = ProviderAdapter(
    modal_provider=mock_modal,
    best_available_provider=None,
    config=ProviderConfig(),
)

# Test signature
generate_ir = dspy.ChainOfThought(PromptToIR)
dspy.settings.configure(lm=adapter)

result = await generate_ir(
    prompt="Create a function to validate emails",
    schema=IRProgram
)

assert len(mock_modal.calls) == 1
assert "schema" in mock_modal.calls[0]["kwargs"]
```

### 11.2 Integration Tests

**Test with real providers** (expensive, run nightly):

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
async def test_prompt_to_ir_real_modal():
    """Test PromptToIR with real Modal provider."""
    adapter = ProviderAdapter(
        modal_provider=RealModalProvider(),
        best_available_provider=None,
        config=ProviderConfig(),
    )

    generate_ir = dspy.ChainOfThought(PromptToIR)
    dspy.settings.configure(lm=adapter)

    result = await generate_ir(
        prompt="Create a function that validates email addresses",
        domain_context="Python 3.11, no external dependencies",
        schema=IRProgram
    )

    # Validate result
    ir = IRProgram.model_validate_json(result.ir_program)
    assert ir.signature.name == "validate_email"
    assert len(ir.signature.parameters) == 1
    assert ir.signature.parameters[0].name == "email"
```

### 11.3 E2E Tests with Real LLMs

**Complete pipeline tests**:

```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_forward_mode_complete():
    """Test complete forward mode pipeline."""
    # Setup
    adapter = ProviderAdapter(
        modal_provider=RealModalProvider(),
        best_available_provider=RealBestAvailableProvider(),
        config=ProviderConfig(),
    )

    pipeline = ForwardModePipeline(adapter)

    # Execute
    result = await pipeline.execute(
        prompt="Create a rate limiter for API endpoints using Redis",
        target_lang="python"
    )

    # Validate IR
    assert result.ir is not None
    assert result.ir.signature.name == "rate_limit"

    # Validate code
    assert result.code is not None
    compile(result.code, "<string>", "exec")  # Must compile

    # Check provenance
    assert len(result.trace.llm_calls) >= 2  # At least intent + IR generation

    # Check routes used
    routes_used = {call.route for call in result.trace.llm_calls}
    assert ProviderRoute.MODAL_INFERENCE in routes_used  # IR generation
```

### 11.4 Optimization Tests

**Validate optimization improves quality**:

```python
@pytest.mark.optimization
@pytest.mark.slow
async def test_miprov2_optimization():
    """Test that MIPROv2 optimization improves IR quality."""
    # Baseline
    baseline_program = ForwardModePipeline()

    # Train set (20 examples)
    train_set = load_examples("data/train_examples.jsonl")[:20]
    test_set = load_examples("data/test_examples.jsonl")[:50]

    # Evaluate baseline
    evaluator = Evaluate(devset=test_set, metric=ir_similarity_metric)
    baseline_score = evaluator(baseline_program)

    # Optimize
    optimizer = MIPROv2(
        metric=ir_similarity_metric,
        num_candidates=5,
        init_temperature=1.0,
    )

    optimized_program = optimizer.compile(
        student=baseline_program,
        trainset=train_set,
        num_trials=10,  # Short for test
    )

    # Evaluate optimized
    optimized_score = evaluator(optimized_program)

    # Validate improvement
    improvement = optimized_score - baseline_score
    assert improvement > 0.05, f"Optimization failed: only +{improvement:.2%}"

    print(f"✅ Optimization successful: {baseline_score:.2%} → {optimized_score:.2%} (+{improvement:.2%})")
```

### 11.5 Performance Benchmarks

**Latency and cost benchmarks**:

```python
@pytest.mark.benchmark
async def test_latency_benchmarks():
    """Benchmark latency for each signature."""
    signatures = [
        ("ExtractIntent", ExtractIntent),
        ("PromptToIR", PromptToIR),
        ("RefineIR", RefineIR),
        ("GenerateCode", GenerateCode),
    ]

    results = {}

    for name, signature_cls in signatures:
        module = dspy.ChainOfThought(signature_cls)

        # Warm up
        await module(prompt="test prompt")

        # Benchmark (10 runs)
        latencies = []
        for _ in range(10):
            start = time.time()
            await module(prompt="Create a function to validate emails")
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        results[name] = {
            "p50": percentile(latencies, 0.5),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        }

    # Validate targets
    assert results["PromptToIR"]["p50"] < 10_000, "PromptToIR too slow"
    assert results["ExtractIntent"]["p50"] < 5_000, "ExtractIntent too slow"

    print(f"Benchmark results: {results}")
```

---

## 12. Summary & Next Steps

### 12.1 Current State (Phase 2 Complete)

**Implemented**:
- ✅ H1 ProviderAdapter: 277 lines, 25 tests passing
- ✅ H6 NodeSignatureInterface: 354 lines, 23 tests passing
- ✅ ADR 001: Dual-provider routing architecture documented
- ✅ Modal-only routing (Phase 2 scope)
- ✅ Gate 2: 100% criteria satisfied

**Production metrics**:
- Forward mode: 80% compilation, 60% execution
- Latency: 16s (p50), 45s (p95)
- Cost: $0.0029/request
- Provider: Modal SGLang (L40S)

### 12.2 Phase 3 Targets (Next)

**Goals**:
- Implement Best Available provider integration
- Full dual-routing support (ADR 001 complete)
- H10 OptimizationMetrics
- H8 OptimizationAPI (MIPROv2 integration)
- Initial optimization: 60% → 75% success rate

**Deliverables**:
- BestAvailableProvider class (Anthropic/OpenAI/Google)
- Complete routing logic in ProviderAdapter
- MIPROv2 optimizer integration
- 50+ training examples
- Metrics dashboard

**Timeline**: 2 weeks (Weeks 5-6)

### 12.3 Long-Term Vision

**Phase 4-5 (Months 3-4)**:
- Continuous learning pipeline
- Automatic optimization every 100 examples
- Model versioning and rollback
- Target: 85% success rate

**Phase 6-7 (Months 5-6)**:
- Production deployment
- A/B testing (baseline vs optimized)
- Migration complete (100% traffic)
- Target: 90% success rate

### 12.4 Success Metrics

| Metric | Baseline | Phase 3 | Phase 6 | Long-term |
|--------|----------|---------|---------|-----------|
| Forward mode success | 60% | 75% | 85% | 90% |
| Latency (p50) | 16s | 12s | 10s | 8s |
| Cost per request | $0.0029 | $0.0025 | $0.0020 | $0.0015 |
| Route efficiency | N/A | 70% | 85% | 90% |
| Optimization velocity | N/A | 1 week | 1 day | Auto |

### 12.5 Key Innovations Summary

1. **Dual-Provider Routing (ADR 001)**
   - Quality models (Claude/GPT-4) for reasoning
   - Infrastructure-aware models (Modal SGLang) for constraints
   - Automatic route determination
   - Cost-optimized execution

2. **DSPy Systematic Orchestration**
   - 6 core signatures (PromptToIR, ExtractIntent, etc.)
   - MIPROv2 optimization: 60% → 85% target
   - Continuous learning from production data
   - Composable, type-safe modules

3. **Modal SGLang Deployment**
   - XGrammar-constrained generation
   - L40S GPU for cost/performance balance
   - llguidance/aici support for advanced control
   - 80% compilation rate (Phase 2)

4. **Provenance & Observability**
   - Every LLM call traced with route, cost, quality
   - Route analytics for migration opportunities
   - Grafana dashboards for monitoring
   - Alerting on quality degradation

**Result**: Systematic, optimizable, cost-efficient LLM orchestration for lift.

---

## Document Status

**RFC Number**: RFC-003
**Status**: Draft
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Phase**: Phase 2 Complete, Phase 3 Ready
**Next Review**: After Phase 3 completion

**Authors**: Codelift Team
**Reviewers**: Tech Lead, Engineering Manager
**Approval**: Pending

---

**Ready to optimize. Building the future of AI-native development.**
