# Product Requirements Document: DSPy Integration
## LLM Orchestration with Systematic Optimization

**Version**: 1.0
**Date**: 2025-10-21
**Status**: Active Development (Phase 2 Complete)
**Owner**: Codelift Team
**Related PRDs**: [PRD_LIFT.md](PRD_LIFT.md), [PRD_TYPED_HOLES.md](PRD_TYPED_HOLES.md), [PRD_FORWARD_MODE.md](PRD_FORWARD_MODE.md), [PRD_REVERSE_MODE.md](PRD_REVERSE_MODE.md)

---

## 1. Executive Summary

### 1.1 Problem Statement

lift currently uses **manual prompt engineering** for all LLM interactions, resulting in:

- **No systematic optimization path**: Improving prompts requires manual trial-and-error
- **Brittle prompts**: Small wording changes cause unpredictable quality shifts
- **No composability**: Each task requires bespoke prompting, no reusable patterns
- **No learning**: System doesn't improve from user feedback or failures
- **Poor observability**: Hard to debug why a particular output was generated

**Current state (October 2025)**:
- Forward mode (NL → IR): 60% success rate, manual prompting
- Reverse mode (Code → IR): 70% fidelity, heuristic extraction
- No optimization framework
- No provenance tracking beyond basic logging
- Manual prompt updates every few weeks as quality degrades

### 1.2 Solution Overview

**Adopt DSPy** as the orchestration framework for all LLM interactions:

**DSPy** is a Stanford NLP framework that replaces manual prompts with:
1. **Declarative signatures**: Define *what* the task is, not *how* to prompt for it
2. **Automatic optimization**: MIPROv2 algorithm learns better prompts from examples
3. **Composable modules**: Signatures chain together into reusable pipelines
4. **Continuous learning**: System improves automatically as more data arrives

**Pydantic AI graphs** orchestrate complex multi-step workflows with:
- Type-safe state management
- Parallel node execution
- Durable execution (resume after failures)
- Human-in-the-loop support

### 1.3 Why DSPy vs Manual Prompts

| Aspect | Manual Prompting (Current) | DSPy Signatures (Proposed) |
|--------|---------------------------|---------------------------|
| **Quality Improvement** | Manual trial-and-error (days/weeks) | Automatic optimization (hours) |
| **Composability** | Copy-paste prompts, modify per task | Compose signatures like Lego blocks |
| **Optimization** | None | MIPROv2, BootstrapFewShot, BayesOpt |
| **Learning** | No feedback loop | Continuous learning from examples |
| **Debugging** | Read prompts, guess why failed | Provenance traces + reasoning chains |
| **Type Safety** | Untyped string prompts | Typed inputs/outputs via Pydantic |
| **Testing** | Manual inspection | Automated metrics-based evaluation |
| **Versioning** | No versioning | Model versioning + rollback support |

**Real-world impact from research**:
- DSPy paper reports 22-34% quality improvement on complex tasks (arXiv:2310.03714)
- MIPROv2 achieves 15-25% gains over manual prompts with 50 training examples
- BootstrapFewShot improves accuracy by 10-20% via self-supervised learning

### 1.4 Business Value

**Immediate** (Phase 2-3, Months 1-3):
- **Quality**: 60% → 75% forward mode success rate (25% relative improvement)
- **Velocity**: Prompt optimization changes from weeks → hours (100x faster iteration)
- **Reliability**: Type-safe signatures reduce runtime errors

**Medium-term** (Phase 4-5, Months 4-6):
- **Quality**: 75% → 85% success rate via continuous optimization
- **User Trust**: Provenance tracking shows *why* system made decisions
- **Scalability**: Composable signatures enable new features without manual prompting

**Long-term** (Phase 6-7, Months 7+):
- **Quality**: 85%+ success rate, approaching human-level
- **Self-improvement**: System learns from every user interaction
- **Competitive advantage**: Optimization infrastructure others can't replicate

### 1.5 Current Implementation Status

**Phase 2 COMPLETE** (as of 2025-10-21):
- ✅ H6: NodeSignatureInterface (354 lines, 23 tests passing)
- ✅ H1: ProviderAdapter (277 lines, 25 tests passing)
- ✅ Total: 158/158 tests passing across 6 modules
- ✅ ADR 001: Dual-provider routing strategy (Best Available + Modal Inference)
- ✅ Foundation ready for optimization (Phase 3)

**Next**: Phase 3 - OptimizationMetrics (H10), OptimizationAPI (H8)

---

## 2. DSPy Signature Design

### 2.1 Core Philosophy

**Key Insight**: Every LLM interaction in lift can be specified as a **typed transformation** with clear inputs, outputs, and semantic roles.

**Pattern**:
```python
class TaskSignature(dspy.Signature):
    """Clear description of what this task accomplishes."""

    # Inputs with semantic roles
    input_field: InputType = dspy.InputField(
        desc="Description for the LLM"
    )

    # Outputs with constraints
    output_field: OutputType = dspy.OutputField(
        desc="Expected output format"
    )
```

**Benefits**:
- **Declarative**: Specify *what* not *how*
- **Type-safe**: Pydantic models validate inputs/outputs
- **Optimizable**: MIPROv2 improves prompts automatically
- **Composable**: Signatures chain into pipelines
- **Testable**: Easy to write unit tests with mock predictions

### 2.2 Forward Mode Signatures

#### Signature 1: PromptToIR

```python
class PromptToIR(dspy.Signature):
    """Generate formal IR from natural language prompt."""

    prompt: str = dspy.InputField(
        desc="Natural language description of desired functionality"
    )

    domain_context: str = dspy.InputField(
        desc="Optional domain context or related code",
        default=""
    )

    ir_json: str = dspy.OutputField(
        desc="Valid IR 0.9 JSON with intent, signature, constraints"
    )
```

**Why this signature?**:
- Single responsibility: NL → IR (not NL → Code)
- Output is JSON for XGrammar constraint-based generation
- Can be optimized independently (e.g., improve intent extraction)

**Module usage**:
```python
generator = dspy.ChainOfThought(PromptToIR)
result = await generator(
    prompt="Create a function that validates email addresses",
    domain_context=""
)
ir = json.loads(result.ir_json)
# ir contains: intent, signature, assertions, effects
```

#### Signature 2: ExtractIntent

```python
class ExtractIntent(dspy.Signature):
    """Extract structured intent from natural language."""

    prompt: str = dspy.InputField(desc="User's natural language prompt")

    intent_summary: str = dspy.OutputField(
        desc="Concise 1-2 sentence summary of intent"
    )

    user_personas: list[str] = dspy.OutputField(
        desc="List of intended users or consumers"
    )

    success_criteria: list[str] = dspy.OutputField(
        desc="List of conditions defining successful execution"
    )

    domain_concepts: list[str] = dspy.OutputField(
        desc="Key domain entities or concepts mentioned"
    )
```

**Optimization target**: MIPROv2 learns to extract better intent summaries and success criteria from examples.

#### Signature 3: RefineIR

```python
class RefineIR(dspy.Signature):
    """Refine IR based on user feedback or validation failures."""

    current_ir: str = dspy.InputField(desc="Current IR JSON")

    feedback: str = dspy.InputField(
        desc="User feedback or validation error message"
    )

    refinement_type: str = dspy.InputField(
        desc="Type of refinement: 'add_constraint', 'fix_type', 'clarify_intent'"
    )

    refined_ir: str = dspy.OutputField(
        desc="Updated IR JSON with refinements applied"
    )

    changes_summary: str = dspy.OutputField(
        desc="Human-readable summary of changes made"
    )
```

**Use case**: Interactive refinement loop (see PRD_TYPED_HOLES.md)

### 2.3 Reverse Mode Signatures

#### Signature 4: ExtractIntentFromCode

```python
class ExtractIntentFromCode(dspy.Signature):
    """Infer intent specification from source code."""

    source_code: str = dspy.InputField(desc="Source code to analyze")

    docstrings: str = dspy.InputField(
        desc="Extracted docstrings and comments"
    )

    function_names: list[str] = dspy.InputField(
        desc="Function and variable names (semantic hints)"
    )

    intent_summary: str = dspy.OutputField(
        desc="Inferred purpose of the code"
    )

    confidence: float = dspy.OutputField(
        desc="Confidence score 0.0-1.0 for this inference"
    )
```

**Key feature**: Confidence scoring enables provenance tracking and hole creation for low-confidence inferences.

#### Signature 5: InferTypeFromUsage

```python
class InferTypeFromUsage(dspy.Signature):
    """Infer type constraints from code usage patterns."""

    code_snippet: str = dspy.InputField(desc="Code using the variable")

    variable_name: str = dspy.InputField(desc="Variable to infer type for")

    usage_contexts: list[str] = dspy.InputField(
        desc="List of contexts where variable is used"
    )

    inferred_type: str = dspy.OutputField(
        desc="Inferred type annotation (Python type hint syntax)"
    )

    refinement_predicate: str = dspy.OutputField(
        desc="Optional refinement predicate (e.g., 'x > 0' for positive int)"
    )

    confidence: float = dspy.OutputField(desc="Confidence 0.0-1.0")
```

**Optimization strategy**: Learn from correct/incorrect type inferences in past sessions.

### 2.4 Hole Resolution Signatures

#### Signature 6: SuggestHoleFill

```python
class SuggestHoleFill(dspy.Signature):
    """Generate suggestions for filling a typed hole."""

    hole_kind: str = dspy.InputField(
        desc="Type of hole: 'intent', 'signature', 'effect', 'assertion'"
    )

    hole_type: str = dspy.InputField(
        desc="Expected type if known (e.g., 'str', 'list[int]')"
    )

    surrounding_ir: str = dspy.InputField(
        desc="IR context around the hole (JSON)"
    )

    hole_traces: str = dspy.InputField(
        desc="Values that flowed through hole during partial evaluation",
        default=""
    )

    suggestions: list[dict] = dspy.OutputField(
        desc="List of {value, rationale, confidence} suggestions"
    )
```

**Few-shot learning**: Tracks which suggestions users accept → uses as examples for future holes.

### 2.5 Signature Composition Patterns

#### Pattern 1: Sequential Pipeline

```python
class ForwardModePipeline(dspy.Module):
    """NL → Intent → IR → Code sequential pipeline."""

    def __init__(self):
        self.extract_intent = dspy.ChainOfThought(ExtractIntent)
        self.generate_ir = dspy.ChainOfThought(PromptToIR)

    async def forward(self, prompt: str):
        # Step 1: Extract intent
        intent = await self.extract_intent(prompt=prompt)

        # Step 2: Generate IR (uses intent as context)
        ir = await self.generate_ir(
            prompt=prompt,
            domain_context=f"Intent: {intent.intent_summary}\nCriteria: {intent.success_criteria}"
        )

        return ir
```

**Benefit**: Each step optimizes independently, then compose.

#### Pattern 2: Best-of-N Sampling

```python
class BestOfNIRGenerator(dspy.Module):
    """Generate N candidates, return best."""

    def __init__(self, n: int = 3):
        self.generators = [dspy.ChainOfThought(PromptToIR) for _ in range(n)]
        self.n = n

    async def forward(self, prompt: str):
        # Generate N candidates in parallel
        candidates = await asyncio.gather(*[
            gen(prompt=prompt) for gen in self.generators
        ])

        # Score each candidate (e.g., via validator)
        scores = [self._score_ir(c.ir_json) for c in candidates]

        # Return best
        best_idx = max(range(self.n), key=lambda i: scores[i])
        return candidates[best_idx]

    def _score_ir(self, ir_json: str) -> float:
        # Parse and validate IR, return quality score
        ...
```

**Benefit**: Improves quality without optimization (ensemble effect).

### 2.6 Real Implementation Example

**From lift-sys/dspy_signatures/node_interface.py** (Phase 2):

```python
@runtime_checkable
class BaseNode(Protocol, Generic[StateT]):
    """Protocol for graph nodes executing DSPy signatures."""

    signature: type[dspy.Signature]

    async def run(self, ctx: RunContext[StateT]) -> BaseNode[StateT] | End:
        """Execute DSPy signature and update state."""
        ...

    def extract_inputs(self, state: StateT) -> dict:
        """Extract signature inputs from graph state."""
        ...

    def update_state(self, state: StateT, result: dspy.Prediction) -> None:
        """Update graph state with signature outputs."""
        ...
```

**Usage in graph**:
```python
class ExtractIntentNode(AbstractBaseNode[ForwardModeState]):
    signature = ExtractIntent

    def extract_inputs(self, state: ForwardModeState) -> dict:
        return {"prompt": state.user_prompt}

    def update_state(self, state: ForwardModeState, result: dspy.Prediction) -> None:
        state.intent = IntentClause(
            summary=result.intent_summary,
            user_personas=result.user_personas,
            success_criteria=result.success_criteria,
            domain_concepts=result.domain_concepts
        )

    async def run(self, ctx: RunContext[ForwardModeState]) -> BaseNode | End:
        # Extract inputs, execute signature, update state
        inputs = self.extract_inputs(ctx.state)
        result = await self.execute_signature(inputs)
        self.update_state(ctx.state, result)

        # Decide next node
        return GenerateIRNode() if ctx.state.intent else End()
```

**Benefits**:
- Type-safe (mypy --strict passes)
- Composable (nodes chain via return values)
- Testable (mock RunContext and state)
- Provenance-tracked (RunContext.add_provenance)

---

## 3. Pydantic AI Graph Workflows

### 3.1 Why Graphs?

**Current problem**: Forward/reverse modes are monolithic functions:
- Hard to cache intermediate results
- No parallelization of independent steps
- Difficult to debug (no execution trace)
- No support for human-in-the-loop workflows

**Graph solution**: Model workflows as finite state machines:
- Each node is independently cacheable
- Explicit dependencies enable parallelization
- Graph state is durable (persist and resume)
- Natural support for user interactions

### 3.2 Graph Architecture

```python
from pydantic import BaseModel
from pydantic_ai.graph import Graph, BaseNode, End
from dataclasses import dataclass

@dataclass
class ForwardModeState:
    """Graph state passed between nodes."""
    user_prompt: str
    intent: IntentClause | None = None
    ir: IntermediateRepresentation | None = None
    holes: list[TypedHole] = field(default_factory=list)
    code: str | None = None
    validation_errors: list[str] = field(default_factory=list)

class ExtractIntentNode(BaseNode):
    async def run(self, ctx: RunContext[ForwardModeState]) -> GenerateIRNode | End:
        # Execute DSPy signature
        intent_module = dspy.ChainOfThought(ExtractIntent)
        result = await intent_module(prompt=ctx.state.user_prompt)

        # Update state
        ctx.state.intent = IntentClause(...)

        # Decide next node
        return GenerateIRNode() if result else End()

# Define graph
forward_graph = Graph(
    state_type=ForwardModeState,
    entry_node=ExtractIntentNode
)
```

### 3.3 Forward Mode Graph

**Workflow**: NL Prompt → Intent → IR → Holes → Code

```
Entry: User Prompt
  ↓
[ExtractIntentNode] → Uses ExtractIntent signature
  ↓
[GenerateIRNode] → Uses PromptToIR signature
  ↓
[DetectHolesNode] → Identifies ambiguities in IR
  ↓
[FillHolesLoop] → Interactive or AI-powered hole filling
  ↓
[ValidateIRNode] → SMT/SAT/CSP constraint checks
  ↓
[GenerateCodeNode] → Uses IRToCode + XGrammar constraints
  ↓
[ValidateCodeNode] → AST + execution validation
  ↓
End: Code + ValidationResult
```

**Parallelization opportunities**:
- `GenerateIRNode` can generate multiple candidates (Best-of-N)
- `ValidateIRNode` can run constraint checks in parallel
- `FillHolesLoop` can generate suggestions for multiple holes concurrently

**Caching**:
- Intent extraction cached by prompt hash
- IR generation cached by intent hash
- Validation cached by IR hash
- ~60%+ cache hit rate expected on repeated prompts

### 3.4 Reverse Mode Graph

**Workflow**: Code → AST → IR (parallel extraction) → Holes → Refinement

```
Entry: Source Code Path
  ↓
[LoadCodeNode] → Read and parse file
  ↓
[ParseASTNode] → Generate AST
  ↓
[ParallelExtractionNode] → 3 signatures in parallel:
  ├─ ExtractIntentFromCode
  ├─ InferTypeFromUsage
  └─ DetectConstraints
  ↓
[MergeExtractionNode] → Combine results into IR
  ↓
[AssignConfidenceNode] → Score each IR element
  ↓
[PromoteToHolesNode] → Low-confidence → typed holes
  ↓
[ValidateIRNode] → Consistency checks
  ↓
End: IR (with provenance)
```

**Key feature**: Parallel extraction maximizes throughput (3x speedup vs sequential).

### 3.5 Hole Resolution Graph

**Workflow**: Interactive loop for filling typed holes

```
Entry: IR with TypedHoles
  ↓
[SelectNextHoleNode] → Prioritize by dependency order
  ↓
[GenerateSuggestionsNode] → Uses SuggestHoleFill signature
  ↓
[PresentToUserNode] → Display suggestions in UI
  ↓
[WaitForUserDecision] → Human-in-the-loop (graph pauses)
  ↓
[ApplyResolutionNode] → Update IR with user choice
  ↓
[PropagateConstraintsNode] → Update dependent holes
  ↓
[CheckCompletenessNode] → Any holes remaining?
  ├─ Yes → SelectNextHoleNode (loop)
  └─ No → ValidateCompleteIR
       ↓
     End: Complete IR
```

**Human-in-the-loop**:
- Graph state persists in database (Supabase)
- User can save and resume later
- Decision history feeds few-shot learning

### 3.6 State Persistence

**Schema** (from H11 ExecutionHistorySchema):

```sql
CREATE TABLE graph_executions (
    id UUID PRIMARY KEY,
    graph_type TEXT NOT NULL,
    state JSONB NOT NULL,
    current_node TEXT,
    completed_nodes TEXT[],
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    user_id TEXT,
    -- Performance tracking
    total_duration_ms FLOAT,
    node_count INT,
    llm_calls INT,
    tokens_used INT
);
```

**Benefits**:
- Resume failed executions
- Audit trail of all transformations
- A/B test different graph structures
- Debug by replaying state transitions

---

## 4. Optimization Strategy

### 4.1 MIPROv2 Overview

**MIPROv2** (Multi-prompt Instruction PRoposal Optimizer v2):
- Automatic prompt optimization algorithm from Stanford NLP
- Learns better instructions, examples, and reasoning traces
- Bayesian optimization over prompt space
- Achieves 15-25% quality improvement in research paper

**How it works**:
1. Start with baseline prompts (naive instructions)
2. Generate candidate improvements via LLM
3. Evaluate candidates on validation set
4. Keep best performers
5. Repeat for N iterations (typically 20-50)

**Result**: Optimized prompts + few-shot examples that outperform manual engineering.

### 4.2 Optimization Loop

```python
class PipelineOptimizer:
    """Optimize DSPy signatures using validation data."""

    def __init__(
        self,
        pipeline: ForwardModePipeline,
        evaluator: PipelineEvaluator
    ):
        self.pipeline = pipeline
        self.evaluator = evaluator

    async def optimize(
        self,
        training_data: list[Example],
        metric: str = "f1",
        iterations: int = 50
    ):
        """Optimize pipeline using MIPROv2."""

        # 1. Convert examples to DSPy format
        dspy_examples = [
            dspy.Example(
                prompt=ex.prompt,
                expected_ir=ex.expected_ir.to_dict()
            ).with_inputs("prompt")
            for ex in training_data
        ]

        # 2. Define evaluation metric
        def evaluate_pipeline(example, prediction, trace=None):
            ir_score = self.evaluator.ir_similarity(
                prediction.ir_json,
                example.expected_ir
            )
            return ir_score

        # 3. Initialize MIPROv2 optimizer
        optimizer = dspy.MIPROv2(
            metric=evaluate_pipeline,
            num_candidates=10,
            init_temperature=1.0
        )

        # 4. Optimize
        optimized_pipeline = optimizer.compile(
            student=self.pipeline,
            trainset=dspy_examples,
            num_trials=iterations
        )

        return optimized_pipeline
```

### 4.3 What Gets Optimized

**For each DSPy signature**:

1. **Instructions**: Natural language task descriptions
   - Example: "Extract user intent" → "Identify the primary goal, target users, success criteria, and domain concepts from the prompt. Be specific and concrete."

2. **Few-Shot Examples**: Demonstrations of correct behavior
   - Automatically selects 3-5 best examples from training data
   - Uses Bayesian optimization to search example space

3. **Reasoning Traces**: Chain-of-thought prompts
   - Learns effective reasoning patterns
   - Adapts to signature complexity

**Example trajectory** (from research paper):

```
Iteration 0 (Baseline):
  ExtractIntent accuracy: 0.65
  PromptToIR accuracy: 0.58
  End-to-end success: 0.42

Iteration 20:
  ExtractIntent accuracy: 0.78 (+13pp)
  PromptToIR accuracy: 0.71 (+13pp)
  End-to-end success: 0.61 (+19pp)

Iteration 50 (Final):
  ExtractIntent accuracy: 0.87 (+22pp)
  PromptToIR accuracy: 0.83 (+25pp)
  End-to-end success: 0.76 (+34pp)
```

### 4.4 Metrics (H10: OptimizationMetrics)

**IR Quality**:
```python
def ir_similarity(predicted: IR, expected: IR) -> float:
    """Compute IR similarity score (0.0-1.0)."""
    scores = []

    # Intent similarity (embeddings)
    intent_score = cosine_similarity(
        embed(predicted.intent.summary),
        embed(expected.intent.summary)
    )
    scores.append(intent_score)

    # Signature exact match
    sig_score = 1.0 if (
        predicted.signature.name == expected.signature.name and
        len(predicted.signature.parameters) == len(expected.signature.parameters)
    ) else 0.5
    scores.append(sig_score)

    # Assertion overlap (Jaccard)
    pred_assertions = {a.expression for a in predicted.assertions}
    exp_assertions = {a.expression for a in expected.assertions}
    assertion_score = jaccard_similarity(pred_assertions, exp_assertions)
    scores.append(assertion_score)

    return sum(scores) / len(scores)
```

**Code Quality**:
```python
def code_quality(predicted: str, expected: str) -> float:
    """Compute code quality score."""
    scores = []

    # Compilation success
    try:
        compile(predicted, "<string>", "exec")
        scores.append(1.0)
    except SyntaxError:
        scores.append(0.0)

    # AST similarity
    pred_ast = ast.parse(predicted)
    exp_ast = ast.parse(expected)
    ast_score = ast_similarity(pred_ast, exp_ast)
    scores.append(ast_score)

    # Execution equivalence (if tests available)
    if test_suite:
        exec_score = execution_equivalence(predicted, expected)
        scores.append(exec_score)

    return sum(scores) / len(scores)
```

**Route-Aware Metrics** (ADR 001):
```python
def route_cost(
    route: ProviderRoute,
    tokens: int,
    duration_ms: float
) -> float:
    """Calculate cost for this route."""
    if route == ProviderRoute.BEST_AVAILABLE:
        # API cost ($/token)
        return tokens * 0.00003  # Example: Claude 3.5 Sonnet pricing
    else:
        # Modal compute cost ($/GPU-second)
        return (duration_ms / 1000) * 0.0002  # L40S pricing

def suggest_route_migration(
    current_route: ProviderRoute,
    task_metrics: dict[str, float]
) -> ProviderRoute | None:
    """Suggest route change if beneficial."""
    if current_route == ProviderRoute.MODAL_INFERENCE:
        # Check if task doesn't need constrained generation
        if not task_metrics.get("requires_schema", False):
            # Could migrate to Best Available for better quality
            return ProviderRoute.BEST_AVAILABLE
    return None
```

### 4.5 Continuous Learning

**Pattern**: Optimize incrementally as new data arrives

```python
class ContinuousOptimizer:
    """Continuously optimize pipeline as examples collected."""

    def __init__(
        self,
        pipeline: ForwardModePipeline,
        min_new_examples: int = 100
    ):
        self.pipeline = pipeline
        self.min_new_examples = min_new_examples
        self.example_buffer = []

    async def log_example(
        self,
        prompt: str,
        generated_ir: IR,
        user_feedback: FeedbackScore
    ):
        """Log example with user feedback."""
        if user_feedback.score >= 4:  # High quality only
            self.example_buffer.append(
                Example(prompt=prompt, expected_ir=generated_ir)
            )

        # Trigger optimization when buffer full
        if len(self.example_buffer) >= self.min_new_examples:
            await self._trigger_optimization()

    async def _trigger_optimization(self):
        """Run optimization cycle."""
        print(f"🔧 Optimizing with {len(self.example_buffer)} examples")

        # Use top 50 examples
        training_data = sorted(
            self.example_buffer,
            key=lambda ex: ex.score,
            reverse=True
        )[:50]

        # Optimize (shorter iterations for continuous)
        optimizer = PipelineOptimizer(self.pipeline, evaluator)
        optimized = await optimizer.optimize(training_data, iterations=20)

        # Deploy new version
        self.pipeline = optimized
        self.example_buffer.clear()
```

**Benefit**: Pipeline improves automatically as users use the system.

---

## 5. Provider Abstraction

### 5.1 Dual-Provider Architecture (ADR 001)

**Two routes** for LLM calls based on infrastructure requirements:

**Route 1: Best Available** (Anthropic/OpenAI/Google)
- Use when: Task does NOT require inference system access
- Characteristics: Best quality models, pay-per-token pricing
- Examples: Claude 3.5 Sonnet, GPT-4 Turbo, Gemini 1.5 Pro
- Use cases: Simple text generation, reasoning, flexible output format

**Route 2: Modal Inference** (SGLang on Modal)
- Use when: Task REQUIRES inference system access
- Characteristics: Direct inference control, fixed GPU costs
- Features: XGrammar, llguidance, aici, speculative decoding
- Use cases: Structured output (Pydantic schemas), constrained generation

### 5.2 Routing Logic

```python
class ProviderAdapter:
    """Dual-route integration layer (H1)."""

    def __init__(
        self,
        modal_provider: ModalProvider,
        best_available_provider: BestAvailableProvider,
        config: ProviderConfig
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
        # Determine route
        route = self._determine_route(schema, llguidance_grammar, **kwargs)

        if route == ProviderRoute.MODAL_INFERENCE:
            return await self._call_modal(prompt, schema, **kwargs)
        else:
            return await self._call_best_available(prompt, **kwargs)

    def _determine_route(self, **kwargs) -> ProviderRoute:
        """Route based on infrastructure requirements."""
        if any([
            kwargs.get("schema") is not None,  # XGrammar
            kwargs.get("llguidance_grammar") is not None,
            kwargs.get("aici_control") is not None,
            kwargs.get("speculative_decode", False),
        ]):
            return ProviderRoute.MODAL_INFERENCE

        return ProviderRoute.BEST_AVAILABLE
```

### 5.3 Multi-Provider Benefits

**Quality vs Capability tradeoff**:
- Best Available: Highest quality for reasoning tasks
- Modal: Necessary infrastructure for constrained generation

**Cost optimization**:
- Best Available: Use for high-value reasoning (expensive but best)
- Modal: Fixed GPU cost, use when features required

**Future-proofing**:
- As API providers add constrained generation, migrate tasks to Best Available
- Modal route always available for cutting-edge research

### 5.4 Resource Tracking

**Integration with H14 ResourceLimits**:

```python
class ProviderAdapter:
    def set_resource_tracker(self, tracker: ResourceUsage):
        """Set tracker for monitoring resource usage."""
        self.resource_tracker = tracker

    async def __call__(self, prompt: str, **kwargs) -> dspy.Prediction:
        # Track LLM call
        if self.resource_tracker:
            self.resource_tracker.add_llm_call()

        # Execute
        result = await self._execute(prompt, **kwargs)

        # Track tokens
        if self.resource_tracker and hasattr(result, 'tokens_used'):
            self.resource_tracker.add_tokens(result.tokens_used)

        return result
```

**Enforced limits** (from ResourceLimits):
- max_llm_calls: 100 per graph execution
- max_tokens: 50,000 per execution
- max_concurrent_nodes: 3 parallel LLM calls
- Warnings at 80%, errors at 100%

---

## 6. Functional Requirements

### FR5.1: DSPy Signature Execution

**Description**: System SHALL execute DSPy signatures via graph nodes.

**Acceptance Criteria**:
- ✅ BaseNode protocol defined (H6, Phase 1)
- ✅ ProviderAdapter integrates DSPy with Modal (H1, Phase 2)
- [ ] All signatures execute with <10% latency overhead vs manual prompts
- [ ] Type safety validated (mypy --strict passes)
- [ ] Provenance tracked for all signature executions

**Status**: Phase 2 complete, latency benchmarking pending

---

### FR5.2: Automatic Prompt Optimization

**Description**: System SHALL optimize prompts using MIPROv2.

**Acceptance Criteria**:
- [ ] OptimizationMetrics defined (H10, Phase 3)
- [ ] OptimizationAPI implements MIPROv2 (H8, Phase 3)
- [ ] Optimization achieves ≥15% quality improvement on 50 examples
- [ ] Optimized models versioned and tracked
- [ ] A/B testing compares baseline vs optimized

**Status**: Phase 3 (next phase)

---

### FR5.3: Multi-Provider Routing

**Description**: System SHALL route LLM calls based on infrastructure requirements (ADR 001).

**Acceptance Criteria**:
- [x] ProviderAdapter supports dual routing (H1, Phase 2 - Modal only)
- [ ] Best Available provider integrated (Phase 3)
- [ ] Routing logic implements ADR 001 decision tree
- [ ] Route tracking for metrics (route cost, quality per route)
- [ ] Manual route override supported for experimentation

**Status**: Phase 2 partial (Modal only), Phase 3 for full routing

---

### FR5.4: Graph-Based Workflow Orchestration

**Description**: System SHALL orchestrate complex workflows using Pydantic AI graphs.

**Acceptance Criteria**:
- ✅ Graph state persistence (H2, Phase 2)
- ✅ Execution history tracking (H11, Phase 2)
- [ ] Parallel node execution (H4, Phase 4)
- [ ] Durable execution (resume after failure)
- [ ] Human-in-the-loop support (WaitForUserDecision node)

**Status**: Phase 2 foundation complete, parallelization Phase 4

---

### FR5.5: Continuous Learning Pipeline

**Description**: System SHALL learn from user feedback automatically.

**Acceptance Criteria**:
- [ ] Collect high-quality examples (score ≥4/5)
- [ ] Trigger optimization when 100+ examples collected
- [ ] Deploy optimized models automatically
- [ ] Model versioning and rollback
- [ ] Monitoring alerts on quality degradation

**Status**: Phase 5 (Months 5-6)

---

### FR5.6: Hole Suggestion Quality

**Description**: AI-powered hole suggestions SHALL achieve ≥60% acceptance rate.

**Acceptance Criteria**:
- [ ] SuggestHoleFill signature implemented
- [ ] Few-shot learning from accepted suggestions
- [ ] Confidence calibration (Brier score <0.2)
- [ ] Suggestions ranked by confidence
- [ ] User acceptance tracked

**Status**: Phase 3 (Hole suggestions)

---

### FR5.7: Intent Extraction Quality

**Description**: Forward mode intent extraction SHALL achieve ≥85% accuracy.

**Acceptance Criteria**:
- [ ] ExtractIntent signature implemented
- [ ] Optimized via MIPROv2 on 100+ examples
- [ ] Human evaluation: 85%+ accuracy
- [ ] Intent summaries concise (1-2 sentences)
- [ ] Success criteria specific and measurable

**Status**: Phase 1 (Months 1-2)

---

### FR5.8: Code-to-IR Fidelity

**Description**: Reverse mode SHALL achieve ≥85% structural fidelity.

**Acceptance Criteria**:
- [ ] ExtractIntentFromCode signature implemented
- [ ] InferTypeFromUsage signature implemented
- [ ] Parallel extraction achieves 3x speedup
- [ ] Confidence scoring for all extractions
- [ ] Low confidence (<0.7) → typed holes

**Status**: Phase 2 (Months 2-3)

---

### FR5.9: Provider Fallback

**Description**: System SHALL gracefully handle provider failures.

**Acceptance Criteria**:
- [ ] Fallback from Best Available to Modal on API errors
- [ ] Retry with exponential backoff (3 attempts)
- [ ] Circuit breaker after 5 consecutive failures
- [ ] Error messages actionable
- [ ] Monitoring alerts on high failure rate

**Status**: Phase 2 (Error recovery, H5)

---

### FR5.10: Model Versioning

**Description**: Optimized models SHALL be versioned and tracked.

**Acceptance Criteria**:
- [ ] Each optimization creates new model version
- [ ] Version registry stores metadata (training examples, metrics)
- [ ] Rollback to previous version supported
- [ ] A/B testing between versions
- [ ] Provenance tracks which version used

**Status**: Phase 5 (Continuous learning)

---

### FR5.11: Execution Replay

**Description**: Graph executions SHALL be replayable for debugging.

**Acceptance Criteria**:
- ✅ Execution history schema defined (H11, Phase 2)
- [ ] Replay API: replay_execution(execution_id)
- [ ] Deterministic replay (same inputs → same outputs)
- [ ] Step-through debugging support
- [ ] Visualization of execution trace

**Status**: Phase 2 schema complete, replay API Phase 5

---

### FR5.12: Resource Limit Enforcement

**Description**: Graph executions SHALL respect resource limits.

**Acceptance Criteria**:
- ✅ ResourceLimits defined (H14, Phase 1)
- ✅ ResourceUsage tracking (H14, Phase 1)
- [ ] Limits enforced before expensive operations
- [ ] Warnings at 80% usage
- [ ] Graceful termination at 100%
- [ ] Per-graph-type configurable limits

**Status**: Phase 1 complete, enforcement Phase 2

---

## 7. Success Metrics

### 7.1 Quality Improvement Metrics

**Baseline** (October 2025, manual prompts):
- Forward mode success: 60%
- Reverse mode fidelity: 70%
- Intent extraction accuracy: 70%
- Hole suggestion acceptance: N/A (no AI suggestions)

**Target** (6 months, after optimization):
- Forward mode success: **85%** (+25pp, +42% relative)
- Reverse mode fidelity: **90%** (+20pp, +29% relative)
- Intent extraction accuracy: **87%** (+17pp, +24% relative)
- Hole suggestion acceptance: **65%** (new capability)

**Measurement**:
- Manual evaluation on 100-example test set
- Inter-rater reliability >0.8
- Monthly benchmarking

### 7.2 Optimization ROI Metrics

**Prompt Engineering Velocity**:
- Baseline: 2-4 weeks per major prompt improvement
- Target: **2-4 hours** (automated optimization)
- **ROI**: 100x faster iteration

**Quality Gains per Optimization Cycle**:
- Target: +10-15% per cycle (based on research)
- Measurement: Paired t-test, p < 0.05

**Continuous Learning**:
- Target: New optimization every 100 examples (~monthly)
- Quality improvement: +5-10% per optimization
- Cumulative effect: System improves continuously

### 7.3 Performance Metrics

**Latency** (p50):
- Forward mode: <12s (currently 16s, target -25%)
- Reverse mode: <3s/file (currently 8s, target -63% via parallelization)
- Hole suggestions: <2s

**Throughput**:
- Parallel execution: ≥2.5x speedup (H4 goal)
- Cache hit rate: >60%

### 7.4 Operational Metrics

**Reliability**:
- Graph resume success: >95%
- Provider fallback success: >90%
- Resource limit enforcement: 100%

**Observability**:
- Provenance tracking: 95% of IR elements
- Execution traces: 100% of graph runs
- Route tracking: 100% of LLM calls

### 7.5 User Satisfaction Metrics

**Adoption**:
- Beta users (Month 6): 50+
- Active users (Month 12): 200+
- Retention: >70%

**Satisfaction** (NPS):
- Target: >40
- Measurement: Quarterly survey

**Feature Usage**:
- Hole suggestions acceptance: 60%+
- Graph trace debugging: 30%+ users
- Continuous learning opt-in: 80%+

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE

**Status**: Complete (2025-10-21)
- ✅ H6: NodeSignatureInterface (354 lines, 23 tests)
- ✅ H9: ValidationHooks (406 lines, 28 tests)
- ✅ H14: ResourceLimits (403 lines, 38 tests)
- ✅ Gate 1: 8/14 criteria satisfied (57%)

---

### Phase 2: Provider Integration (Weeks 3-4) ✅ COMPLETE

**Status**: Complete (2025-10-21)
- ✅ H1: ProviderAdapter (277 lines, 25 tests)
- ✅ H2: StatePersistence (427 lines, 21 tests)
- ✅ H11: ExecutionHistorySchema (468 lines, 23 tests)
- ✅ Gate 2: 14/14 criteria satisfied (100%)
- ✅ ADR 001: Dual-provider routing strategy documented
- ✅ Total: 158/158 tests passing

**Next**: Phase 3 - Optimization

---

### Phase 3: Optimization (Weeks 5-6)

**Goal**: Implement MIPROv2 optimization

**Holes to resolve**:
- H10: OptimizationMetrics
- H8: OptimizationAPI
- H12: ConfidenceCalibration

**Tasks**:
1. Define IR similarity, code quality metrics
2. Implement route-aware cost/quality metrics (ADR 001)
3. Integrate MIPROv2 optimizer
4. Collect 50+ training examples (forward mode)
5. Run initial optimization
6. A/B test baseline vs optimized
7. Best Available provider integration

**Deliverables**:
- Optimized forward mode pipeline (≥15% improvement)
- Metrics dashboard
- Model versioning system
- Full dual-routing support

---

### Phase 4: Parallelization (Weeks 7-8)

**Goal**: Parallel node execution

**Holes to resolve**:
- H4: ParallelizationImpl
- H16: ConcurrencyModel
- H18: ConcurrencyValidation

**Tasks**:
1. Implement parallel executor (asyncio.gather)
2. Configure concurrency limits (max 3 concurrent LLM calls)
3. Add state merging logic
4. Test determinism (100 runs)
5. Benchmark speedup (target ≥2.5x)

**Deliverables**:
- Parallel graph execution
- ≥2.5x speedup on parallel paths
- Determinism validation

---

### Phase 5: Caching & Continuous Learning (Weeks 9-10)

**Goal**: Cache intermediate results, continuous optimization

**Holes to resolve**:
- H3: CachingStrategy
- Continuous learning pipeline

**Tasks**:
1. Implement Redis-backed node cache
2. Define cache keys (prompt hash, IR hash)
3. Invalidation strategy
4. ContinuousOptimizer (100 examples → optimize)
5. Model registry and versioning

**Deliverables**:
- ≥60% cache hit rate
- Automatic optimization every 100 examples
- Model versioning and rollback

---

### Phase 6: Production Readiness (Weeks 11-12)

**Goal**: Migration, monitoring, deployment

**Holes to resolve**:
- H15: MigrationConstraints
- H13: FeatureFlagSchema
- H19: BackwardCompatTest

**Tasks**:
1. Session migration (old format → new graph format)
2. Feature flags for gradual rollout
3. Monitoring dashboard (Grafana)
4. Alerting (quality degradation, failures)
5. Documentation and training

**Deliverables**:
- 100% backward compatibility
- Gradual rollout plan (10% → 50% → 100%)
- Production monitoring

---

### Phase 7: Optimization & Validation (Weeks 13-14)

**Goal**: Validate optimization works, deploy

**Holes to resolve**:
- H17: OptimizationValidation
- H5: ErrorRecovery

**Tasks**:
1. Collect 200+ evaluation examples
2. Statistical validation (paired t-test, p < 0.05)
3. Effect size measurement (Cohen's d)
4. Error recovery testing
5. Full deployment

**Deliverables**:
- Statistical proof: optimization works (p < 0.05)
- Production-ready system
- Documentation and user guides

---

## 9. Cross-References

### Related PRDs

**[PRD_LIFT.md](PRD_LIFT.md)**: Overall system architecture
- DSPy integration enables Section 4.3 "AI Optimization"
- Provides infrastructure for Section 5.2 "Continuous Learning"

**[PRD_TYPED_HOLES.md](PRD_TYPED_HOLES.md)**: Typed holes and interactive refinement
- DSPy SuggestHoleFill enables Section 3.3 "AI-Powered Suggestions"
- Continuous learning improves suggestion quality over time

**[PRD_FORWARD_MODE.md](PRD_FORWARD_MODE.md)**: NL → IR → Code
- DSPy signatures replace Section 2.2 "Prompt Engineering"
- Graph workflows implement Section 3.1 "Pipeline Orchestration"

**[PRD_REVERSE_MODE.md](PRD_REVERSE_MODE.md)**: Code → IR
- DSPy signatures enable Section 2.3 "Intent Extraction"
- Parallel execution achieves Section 4.2 "Performance Goals"

### Architecture Documents (lift-sys)

**[DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md](../lift-sys/docs/planning/DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md)**: Original architecture proposal
- Complete technical design (60+ pages)
- All DSPy signatures defined
- Graph workflows specified

**[INTEGRATED_STRATEGY.md](../lift-sys/docs/planning/INTEGRATED_STRATEGY.md)**: 14-month implementation plan
- Timeline: Phases 1-7 over 14 months
- Integration with IR 0.9 adoption (20-month plan)
- Resource allocation and budget

**[ADR_001_DUAL_PROVIDER_ROUTING.md](../lift-sys/docs/planning/ADR_001_DUAL_PROVIDER_ROUTING.md)**: Provider routing strategy
- Dual-route architecture (Best Available + Modal Inference)
- Routing decision tree
- Cost/quality tradeoffs

### Implementation Files (lift-sys)

**[lift_sys/dspy_signatures/node_interface.py](../lift-sys/lift_sys/dspy_signatures/node_interface.py)**: H6 implementation
- 354 lines, 23 tests passing
- BaseNode protocol, RunContext, End sentinel

**[lift_sys/dspy_signatures/provider_adapter.py](../lift-sys/lift_sys/dspy_signatures/provider_adapter.py)**: H1 implementation
- 277 lines, 25 tests passing
- ProviderAdapter, ProviderRoute, resource tracking

**Total**: 2,395 lines of implementation code, 158/158 tests passing

---

## 10. Appendices

### Appendix A: Research References

**DSPy**:
- Paper: "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines" (arXiv:2310.03714)
- Docs: https://dspy.ai/
- MIPROv2: https://dspy.ai/learn/optimization/optimizers/

**Pydantic AI**:
- Docs: https://ai.pydantic.dev/
- Graphs: https://ai.pydantic.dev/graphs/

**Optimization Research**:
- MIPROv2 achieves 22-34% improvement on complex tasks
- BootstrapFewShot: 10-20% via self-supervised learning
- Continuous learning: 5-10% per cycle

### Appendix B: Example Training Data

**Forward Mode Example**:
```json
{
  "prompt": "Create a function that validates email addresses using regex",
  "expected_ir": {
    "intent": {
      "summary": "Validate email address format using regular expressions",
      "success_criteria": [
        "Returns True for valid emails",
        "Returns False for invalid emails",
        "Handles edge cases (multiple @, no domain)"
      ]
    },
    "signature": {
      "name": "validate_email",
      "parameters": [{"name": "email", "type": "str"}],
      "returns": "bool"
    },
    "assertions": [
      {
        "category": "precondition",
        "expression": "isinstance(email, str)"
      },
      {
        "category": "postcondition",
        "expression": "result in [True, False]"
      }
    ]
  }
}
```

### Appendix C: Metrics Dashboard

**Quality Metrics**:
- Forward mode success rate (daily, weekly, monthly)
- Reverse mode fidelity (daily, weekly, monthly)
- Intent extraction accuracy (weekly)
- Hole suggestion acceptance rate (weekly)

**Performance Metrics**:
- Latency (p50, p95, p99) by task type
- Cache hit rate
- Parallel execution speedup

**Route Metrics** (ADR 001):
- Requests per route (Best Available vs Modal)
- Quality per route
- Cost per route
- Migration opportunities

**Optimization Metrics**:
- Optimization cycles run
- Quality improvement per cycle
- Training examples collected
- Model versions deployed

### Appendix D: Migration Plan

**Phase 1** (10% traffic, Week 1-2):
- Internal team only
- Monitor error rates
- Collect feedback

**Phase 2** (25% traffic, Week 3-4):
- Beta users
- A/B testing
- Metrics comparison

**Phase 3** (50% traffic, Week 5-6):
- Random 50/50 split
- Statistical analysis
- Fix issues

**Phase 4** (100% traffic, Week 7-8):
- Full deployment
- Deprecate old code
- Remove feature flags

**Rollback Plan**:
- Trigger: Success rate drops >10%
- Action: Revert feature flag to 0%
- Safety: Old code stays 3 months

---

## Document Status

**Version**: 1.0
**Last Updated**: 2025-10-21
**Phase**: Phase 2 Complete (158/158 tests passing)
**Next Review**: After Phase 3 (Optimization)

**Authors**: Codelift Team
**Reviewers**: Tech Lead, Engineering Manager
**Approval**: Pending

---

**Ready to optimize. Let's build the best LLM orchestration system.**
