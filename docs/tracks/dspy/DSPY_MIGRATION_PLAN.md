# Lift-Sys DSPy Migration Plan

**Date**: 2025-10-20
**Status**: Planning
**Related Documents**:
- [IR Adoption Plan](IR_ADOPTION_PLAN.md)
- [DSPy Official Docs](https://dspy.ai/)
- [Current Roadmap](../../SEMANTIC_IR_ROADMAP.md)

---

## Executive Summary

This plan details the migration of all AI-driven components in lift-sys to use **DSPy** (Declarative Self-improving Language Programs). DSPy replaces manual prompt engineering with:

- **Signatures**: Declarative task specifications (input → output)
- **Modules**: Composable AI behaviors (ChainOfThought, ReAct, etc.)
- **Optimizers**: Automatic prompt/weight optimization (MIPROv2, BootstrapFewShot, etc.)

**Why DSPy?**
1. ✅ **Stop prompt hacking**: Move from brittle prompts to declarative signatures
2. ✅ **Systematic optimization**: Let optimizers tune prompts instead of manual iteration
3. ✅ **Better over time**: Collect data, re-optimize, improve automatically
4. ✅ **Composability**: Build complex AI systems from modular components
5. ✅ **Multi-model**: Easy to switch LLM providers

**Timeline**: 12-16 months (phased approach, can overlap with IR adoption)
**Complexity**: Medium - DSPy well-documented, but requires rethinking AI architecture
**Risk**: Low-Medium - Can migrate incrementally, fallback to old prompts if needed

---

## 0. Current State Analysis

### AI-Driven Components in lift-sys

#### 0.1 Forward Mode (NL → IR → Code)

**Current Implementation**:
```python
# lift_sys/forward_mode/xgrammar_translator.py
class XGrammarIRTranslator:
    async def translate(self, prompt: str) -> IntermediateRepresentation:
        """Manual prompt construction"""
        system_prompt = """You are an expert at creating formal IR..."""
        user_prompt = f"""Task: {prompt}\n\nGenerate IR in JSON format..."""
        # XGrammar-constrained generation
        response = await self.provider.generate_structured(
            prompt=f"{system_prompt}\n\n{user_prompt}",
            schema=ir_schema
        )
        return IntermediateRepresentation.from_dict(response)
```

**Problems**:
- ❌ Brittle prompt: Tweaking is manual and slow
- ❌ No optimization: Can't systematically improve
- ❌ No few-shot learning: Hard to add examples
- ❌ Hard to debug: Prompt changes break things unpredictably

#### 0.2 Reverse Mode (Code → IR)

**Current Implementation**:
```python
# lift_sys/reverse_mode/lifter.py
class SpecificationLifter:
    def _build_intent(self, findings: list[Finding]) -> IntentClause:
        """Rule-based intent extraction"""
        # No AI - uses heuristics
        summary = "Lifted intent with typed holes"
        holes = [self._create_hole(f) for f in findings]
        return IntentClause(summary=summary, holes=holes)
```

**Problems**:
- ❌ No AI: Misses semantic nuances
- ❌ Generic summaries: "Lifted intent" not helpful
- ❌ No refinement: Can't improve over time

#### 0.3 Ambiguity Detection

**Current Implementation**:
```python
# lift_sys/spec_sessions/translator.py
class PromptToIRTranslator:
    def _detect_ambiguities(self, ir: IR, prompt: str) -> list[TypedHole]:
        """Rule-based ambiguity detection"""
        holes = []
        # Check for missing parameter types
        if not param.type_hint:
            holes.append(TypedHole(...))
        # Check for vague intent
        if len(ir.intent.summary.split()) < 5:
            holes.append(TypedHole(...))
        return holes
```

**Problems**:
- ❌ Heuristics only: Misses complex ambiguities
- ❌ No semantic understanding: Can't detect contradictions
- ❌ False positives: Flags things that are actually fine

#### 0.4 Hole Filling Suggestions

**Current Implementation**:
```python
# Not yet implemented - planned for Phase 3 of Semantic IR work
# Would benefit from DSPy for generating context-aware suggestions
```

**Opportunity**:
- ✅ DSPy perfect for this: Context → Suggestion
- ✅ Can learn from accepted/rejected suggestions
- ✅ Optimize for user satisfaction

### Summary: Where AI is Used Today

| Component | Current Approach | Quality | Optimizable? |
|-----------|-----------------|---------|--------------|
| **Forward: NL → IR** | Manual prompts | Medium | ❌ No |
| **Reverse: Code → IR** | Heuristics | Low | ❌ No |
| **Ambiguity Detection** | Rules | Low-Medium | ❌ No |
| **Hole Suggestions** | Not implemented | N/A | N/A |
| **Intent Extraction** | Rules | Low | ❌ No |
| **Entity Resolution** | Not implemented | N/A | N/A |

**All of these should use DSPy.**

---

## 1. DSPy Architecture Overview

### Core Abstractions

#### 1.1 Signatures
**What**: Declarative task specification (input → output)

```python
# Simple inline signature
"prompt -> ir_json"

# Class-based signature with descriptions
class PromptToIR(dspy.Signature):
    """Convert natural language prompt to formal IR structure."""

    prompt: str = dspy.InputField(
        desc="Natural language description of desired functionality"
    )
    context: str = dspy.InputField(
        desc="Optional existing IR for refinement",
        default=""
    )
    ir_json: str = dspy.OutputField(
        desc="Valid JSON IR following the schema"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score (0.0-1.0) for the generated IR"
    )
```

#### 1.2 Modules
**What**: Composable AI behaviors

```python
# Predict: Simple input → output
ir_generator = dspy.Predict(PromptToIR)

# ChainOfThought: Adds reasoning
ir_generator = dspy.ChainOfThought(PromptToIR)

# ReAct: Reasoning + tool use
ir_generator = dspy.ReAct(PromptToIR, tools=[validate_ir, check_schema])

# Custom module
class IRGeneratorWithValidation(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generator = dspy.ChainOfThought(PromptToIR)
        self.validator = dspy.Predict(ValidateIR)

    def forward(self, prompt, context=""):
        ir = self.generator(prompt=prompt, context=context)
        validation = self.validator(ir_json=ir.ir_json)
        if not validation.valid:
            # Retry with error feedback
            ir = self.generator(
                prompt=prompt,
                context=f"{context}\n\nPrevious attempt failed: {validation.error}"
            )
        return ir
```

#### 1.3 Optimizers
**What**: Automatic improvement of prompts/weights

```python
# BootstrapFewShot: Learn from examples
optimizer = dspy.BootstrapFewShot(
    metric=ir_quality_metric,
    max_bootstrapped_demos=8
)

# MIPROv2: Advanced optimization
optimizer = dspy.MIPROv2(
    metric=ir_quality_metric,
    num_candidates=50,
    init_temperature=1.0
)

# Compile module with optimizer
optimized_generator = optimizer.compile(
    ir_generator,
    trainset=training_examples
)
```

### DSPy vs Manual Prompts

| Aspect | Manual Prompts | DSPy |
|--------|---------------|------|
| **Task definition** | Hardcoded strings | Declarative signatures |
| **Few-shot examples** | Manual concatenation | Automatic from optimizer |
| **Reasoning** | Manual "think step by step" | `ChainOfThought` module |
| **Optimization** | Trial and error | Systematic with optimizers |
| **Multi-model** | Rewrite prompts per model | Same signature, auto-adapt |
| **Composition** | Manual chaining | Modular with `dspy.Module` |
| **Debugging** | Print statements | Built-in tracing |

---

## 2. Phased Migration Strategy

### Philosophy: Incremental Replacement

We migrate AI components one at a time, with fallback to old implementation:

1. **Phase 1 (3 months)**: DSPy Setup + Forward Mode (NL → IR)
2. **Phase 2 (3 months)**: Reverse Mode Enhancement (Code → IR with AI)
3. **Phase 3 (3 months)**: Ambiguity Detection + Hole Suggestions
4. **Phase 4 (3 months)**: Entity Resolution + Intent Extraction
5. **Phase 5 (2 months)**: Optimization Loop + Production Tuning

**Total**: ~14 months (can overlap with IR adoption after Phase 1)

---

## 3. Phase 1: DSPy Setup + Forward Mode (Months 1-3)

### Goal
- Set up DSPy infrastructure
- Migrate Forward Mode (NL → IR) to DSPy
- Establish optimization workflow
- Prove DSPy value

### Tasks

#### 3.1 DSPy Installation & Setup (Week 1)
**Deliverable**: `pyproject.toml` + config

```bash
# Add DSPy
uv add dspy-ai

# Add evaluation deps
uv add openai anthropic  # For multi-model support
```

```python
# lift_sys/dspy_config.py

import dspy
from lift_sys.providers.base import BaseProvider

class DSPyProviderAdapter(dspy.LM):
    """Adapt our BaseProvider to DSPy LM interface"""

    def __init__(self, provider: BaseProvider):
        self.provider = provider

    def __call__(self, prompt, **kwargs):
        """DSPy expects this interface"""
        response = await self.provider.generate_text(prompt, **kwargs)
        return response

def setup_dspy(provider: BaseProvider):
    """Initialize DSPy with our provider"""
    lm = DSPyProviderAdapter(provider)
    dspy.settings.configure(lm=lm)
```

**Acceptance**:
- DSPy imports work
- Can call basic DSPy modules
- Provider adapter functional

#### 3.2 Signature Definitions (Week 2)
**Deliverable**: `lift_sys/dspy_signatures/`

```python
# lift_sys/dspy_signatures/forward_mode.py

import dspy

class PromptToIR(dspy.Signature):
    """Convert natural language prompt to formal Intermediate Representation.

    The IR captures intent, signature, effects, assertions, and typed holes
    for ambiguous parts. Output must be valid JSON matching the IR schema.
    """

    prompt: str = dspy.InputField(
        desc="Natural language description of desired code functionality"
    )

    context: str = dspy.InputField(
        desc="Optional existing IR JSON for refinement or empty string",
        default=""
    )

    examples: str = dspy.InputField(
        desc="Optional example inputs/outputs to guide IR generation",
        default=""
    )

    ir_json: str = dspy.OutputField(
        desc=(
            "Valid JSON IR with fields: intent, signature, effects, assertions, "
            "metadata. Use typed holes for ambiguous parts."
        )
    )

    rationale: str = dspy.OutputField(
        desc="Brief explanation of key IR design decisions"
    )

class RefineIR(dspy.Signature):
    """Refine existing IR based on user feedback or validation errors."""

    current_ir: str = dspy.InputField(desc="Current IR JSON")
    feedback: str = dspy.InputField(desc="User feedback or validation errors")
    refined_ir: str = dspy.OutputField(desc="Improved IR JSON")

class ExtractIntent(dspy.Signature):
    """Extract high-level intent from natural language prompt."""

    prompt: str = dspy.InputField(desc="Natural language prompt")
    intent_summary: str = dspy.OutputField(desc="Concise intent summary")
    goals: list[str] = dspy.OutputField(desc="List of user goals")
    constraints: list[str] = dspy.OutputField(desc="List of constraints")

class InferSignature(dspy.Signature):
    """Infer function signature from prompt and intent."""

    prompt: str = dspy.InputField(desc="Natural language prompt")
    intent: str = dspy.InputField(desc="Intent summary")
    function_name: str = dspy.OutputField(desc="Suggested function name")
    parameters: str = dspy.OutputField(desc="JSON list of parameters")
    return_type: str = dspy.OutputField(desc="Return type")
```

**Acceptance**:
- All signatures documented
- Field descriptions clear
- Type hints correct

#### 3.3 Forward Mode Module (Week 3-4)
**Deliverable**: `lift_sys/dspy_modules/forward_mode.py`

```python
# lift_sys/dspy_modules/forward_mode.py

import dspy
from lift_sys.dspy_signatures.forward_mode import (
    PromptToIR, RefineIR, ExtractIntent, InferSignature
)
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.ir.parser import IRParser

class IRGenerator(dspy.Module):
    """Generate IR from natural language using multi-stage reasoning."""

    def __init__(self):
        super().__init__()
        # Use ChainOfThought for better reasoning
        self.extract_intent = dspy.ChainOfThought(ExtractIntent)
        self.infer_signature = dspy.ChainOfThought(InferSignature)
        self.generate_ir = dspy.ChainOfThought(PromptToIR)
        self.parser = IRParser()

    def forward(self, prompt: str, context: str = "") -> dspy.Prediction:
        """Generate IR with multi-stage reasoning."""

        # Stage 1: Extract intent
        intent_result = self.extract_intent(prompt=prompt)

        # Stage 2: Infer signature
        sig_result = self.infer_signature(
            prompt=prompt,
            intent=intent_result.intent_summary
        )

        # Stage 3: Generate full IR
        ir_result = self.generate_ir(
            prompt=prompt,
            context=context,
            examples=""  # TODO: Inject examples from optimizer
        )

        # Parse and validate
        try:
            ir = self.parser.parse_json(ir_result.ir_json)
            valid = True
            error = None
        except Exception as e:
            ir = None
            valid = False
            error = str(e)

        return dspy.Prediction(
            ir_json=ir_result.ir_json,
            ir=ir,
            valid=valid,
            error=error,
            rationale=ir_result.rationale,
            intent_summary=intent_result.intent_summary,
            function_name=sig_result.function_name
        )

class IRGeneratorWithValidation(dspy.Module):
    """IR Generator with automatic validation and retry."""

    def __init__(self, max_retries: int = 3):
        super().__init__()
        self.generator = IRGenerator()
        self.refiner = dspy.ChainOfThought(RefineIR)
        self.max_retries = max_retries

    def forward(self, prompt: str, context: str = "") -> dspy.Prediction:
        """Generate IR with validation loop."""

        result = self.generator(prompt=prompt, context=context)

        retries = 0
        while not result.valid and retries < self.max_retries:
            # Refine based on error
            refined = self.refiner(
                current_ir=result.ir_json,
                feedback=f"Validation failed: {result.error}"
            )

            # Re-parse
            try:
                ir = self.parser.parse_json(refined.refined_ir)
                result.ir_json = refined.refined_ir
                result.ir = ir
                result.valid = True
                result.error = None
            except Exception as e:
                result.error = str(e)
                retries += 1

        return result
```

**Acceptance**:
- Generates valid IR for simple prompts
- Validation loop works
- Error handling graceful

#### 3.4 Evaluation Metrics (Week 5)
**Deliverable**: `lift_sys/dspy_eval/metrics.py`

```python
# lift_sys/dspy_eval/metrics.py

import dspy
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.validation.validator import IRValidator

def ir_quality_metric(example: dspy.Example, pred: dspy.Prediction, trace=None) -> float:
    """Metric for IR quality (0.0 to 1.0)."""

    score = 0.0

    # 1. Validity (30%)
    if pred.valid and pred.ir:
        score += 0.3

    # 2. Completeness (30%)
    if pred.ir:
        ir: IntermediateRepresentation = pred.ir
        completeness = 0.0

        # Has intent?
        if ir.intent.summary and len(ir.intent.summary) > 10:
            completeness += 0.2

        # Has signature?
        if ir.signature.name and ir.signature.parameters:
            completeness += 0.2

        # Has effects?
        if ir.effects:
            completeness += 0.1

        # Has assertions?
        if ir.assertions:
            completeness += 0.2

        # Typed holes for ambiguities?
        if ir.typed_holes():
            completeness += 0.1

        # Minimal holes (prefer specific over vague)
        num_holes = len(ir.typed_holes())
        if num_holes < 3:
            completeness += 0.2

        score += 0.3 * completeness

    # 3. Correctness vs ground truth (40%)
    if hasattr(example, 'expected_ir') and pred.ir:
        expected: IntermediateRepresentation = example.expected_ir
        actual: IntermediateRepresentation = pred.ir

        correctness = 0.0

        # Function name match?
        if expected.signature.name == actual.signature.name:
            correctness += 0.3

        # Parameter count match?
        if len(expected.signature.parameters) == len(actual.signature.parameters):
            correctness += 0.2

        # Return type match?
        if expected.signature.returns == actual.signature.returns:
            correctness += 0.2

        # Intent similarity (fuzzy)
        intent_similarity = compute_similarity(
            expected.intent.summary,
            actual.intent.summary
        )
        correctness += 0.3 * intent_similarity

        score += 0.4 * correctness

    return score

def compute_similarity(text1: str, text2: str) -> float:
    """Compute semantic similarity (0.0 to 1.0)."""
    # Use embeddings or simple word overlap for now
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)
```

**Acceptance**:
- Metric rewards valid, complete, correct IR
- Can compare IR quality objectively
- Scores correlate with human judgment (test this!)

#### 3.5 Training Data Collection (Week 6)
**Deliverable**: `lift_sys/dspy_data/forward_mode_train.json`

```python
# scripts/collect_training_data.py

import dspy
from lift_sys.ir.models import IntermediateRepresentation

# Collect training examples
training_examples = []

# Example 1: Simple function
training_examples.append(
    dspy.Example(
        prompt="Create a function that adds two numbers",
        context="",
        expected_ir=IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers and return the sum"),
            signature=SigClause(
                name="add_numbers",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int")
                ],
                returns="int"
            ),
            effects=[],
            assertions=[
                AssertClause(predicate="result == a + b")
            ],
            metadata=Metadata(origin="prompt", language="python")
        ).to_dict()
    ).with_inputs("prompt", "context")
)

# Example 2: Function with ambiguity
training_examples.append(
    dspy.Example(
        prompt="Create a function that processes user data",
        context="",
        expected_ir=IntermediateRepresentation(
            intent=IntentClause(
                summary="Process user data (details ambiguous)",
                holes=[
                    TypedHole(
                        identifier="processing_details",
                        type_hint="string",
                        description="Clarify what 'process' means",
                        kind=HoleKind.INTENT
                    )
                ]
            ),
            signature=SigClause(
                name="process_user_data",
                parameters=[
                    Parameter(
                        name="user_data",
                        type_hint="unknown",  # Ambiguous
                        description="Type of user data unclear"
                    )
                ],
                returns="unknown",
                holes=[
                    TypedHole(
                        identifier="user_data_type",
                        type_hint="type",
                        description="Specify user_data type",
                        kind=HoleKind.SIGNATURE
                    ),
                    TypedHole(
                        identifier="return_type",
                        type_hint="type",
                        description="Specify return type",
                        kind=HoleKind.SIGNATURE
                    )
                ]
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="prompt", language="python")
        ).to_dict()
    ).with_inputs("prompt", "context")
)

# ... Add 20-50 more examples covering:
# - Different function types (CRUD, validation, transformation)
# - Various ambiguities
# - Different parameter counts
# - Side effects
# - Complex assertions
```

**Target**: 50-100 training examples
**Sources**:
- Manual curation (20 examples)
- Existing test cases (30 examples)
- Synthetic generation (50 examples)

**Acceptance**:
- At least 50 diverse examples
- Cover common patterns
- Ground truth IR manually verified

#### 3.6 Optimization (Week 7-8)
**Deliverable**: Optimized IR generator

```python
# scripts/optimize_forward_mode.py

import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2
from lift_sys.dspy_modules.forward_mode import IRGeneratorWithValidation
from lift_sys.dspy_eval.metrics import ir_quality_metric
from lift_sys.dspy_data import load_training_data

# Load data
trainset = load_training_data("forward_mode_train.json")
devset = trainset[:10]  # Hold out for validation

# Create module
module = IRGeneratorWithValidation()

# Option 1: Bootstrap Few-Shot (simpler, faster)
bootstrap_optimizer = BootstrapFewShot(
    metric=ir_quality_metric,
    max_bootstrapped_demos=8,
    max_labeled_demos=4
)
optimized_bootstrap = bootstrap_optimizer.compile(
    module,
    trainset=trainset
)

# Option 2: MIPROv2 (more sophisticated)
mipro_optimizer = MIPROv2(
    metric=ir_quality_metric,
    num_candidates=30,
    init_temperature=1.0,
    verbose=True
)
optimized_mipro = mipro_optimizer.compile(
    module,
    trainset=trainset,
    num_trials=50,
    max_bootstrapped_demos=8,
    max_labeled_demos=4
)

# Evaluate
def evaluate(module, dataset):
    scores = []
    for example in dataset:
        pred = module(prompt=example.prompt, context=example.context)
        score = ir_quality_metric(example, pred)
        scores.append(score)
    return sum(scores) / len(scores)

baseline_score = evaluate(module, devset)
bootstrap_score = evaluate(optimized_bootstrap, devset)
mipro_score = evaluate(optimized_mipro, devset)

print(f"Baseline: {baseline_score:.3f}")
print(f"Bootstrap: {bootstrap_score:.3f}")
print(f"MIPRO: {mipro_score:.3f}")

# Save best
best = optimized_mipro if mipro_score > bootstrap_score else optimized_bootstrap
best.save("optimized_ir_generator.json")
```

**Acceptance**:
- Optimized module outperforms baseline by ≥10%
- Optimization runs in <2 hours
- Saved model loadable

#### 3.7 Integration (Week 9-10)
**Deliverable**: Replace old translator with DSPy version

```python
# lift_sys/spec_sessions/translator.py (UPDATED)

from lift_sys.dspy_modules.forward_mode import IRGeneratorWithValidation
import dspy

class PromptToIRTranslator:
    """Converts natural language prompts to IR drafts with DSPy."""

    def __init__(
        self,
        provider: BaseProvider,
        model_path: str | None = None
    ):
        self.provider = provider
        setup_dspy(provider)

        # Load optimized model if available
        if model_path:
            self.generator = IRGeneratorWithValidation.load(model_path)
        else:
            self.generator = IRGeneratorWithValidation()

    async def translate(
        self,
        prompt: str,
        context: IntermediateRepresentation | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IRDraft:
        """Translate prompt to IR using DSPy."""

        # Convert context to JSON string if present
        context_str = ""
        if context:
            context_str = json.dumps(context.to_dict())

        # Generate with DSPy
        result = self.generator(prompt=prompt, context=context_str)

        if not result.valid:
            # Fallback or raise error
            raise TranslationError(f"Failed to generate valid IR: {result.error}")

        # Create draft
        draft = IRDraft(
            version=1 if not context else (len(context.typed_holes()) + 1),
            ir=result.ir,
            validation_status="complete" if not result.ir.typed_holes() else "incomplete",
            ambiguities=[h.identifier for h in result.ir.typed_holes()],
            metadata=metadata or {},
        )

        return draft
```

**Acceptance**:
- All existing tests pass
- Performance similar or better
- Can switch between old/new with feature flag

#### 3.8 A/B Testing (Week 11-12)
**Deliverable**: Feature flag + metrics

```python
# lift_sys/config.py

class FeatureFlags:
    USE_DSPY_FORWARD_MODE: bool = os.getenv("USE_DSPY_FORWARD_MODE", "false").lower() == "true"

# lift_sys/spec_sessions/translator.py

async def translate(self, prompt: str, ...) -> IRDraft:
    if FeatureFlags.USE_DSPY_FORWARD_MODE:
        return await self._translate_dspy(prompt, ...)
    else:
        return await self._translate_legacy(prompt, ...)
```

**Metrics to Track**:
- IR validity rate (old vs new)
- Time to generate IR
- User satisfaction (surveys)
- Ambiguity detection accuracy

**Acceptance**:
- A/B test runs for 2 weeks
- DSPy version ≥ old version on all metrics
- Ready to switch default

### Phase 1 Success Metrics
- ✅ DSPy infrastructure working
- ✅ Forward mode (NL → IR) using DSPy
- ✅ Optimized module outperforms baseline by ≥10%
- ✅ A/B test shows DSPy ≥ old approach
- ✅ Feature flag ready to flip

**Phase 1 Estimated Effort**: 3 months (1 senior eng + 1 ML eng)

---

## 4. Phase 2: Reverse Mode Enhancement (Months 4-6)

### Goal
Enhance Reverse Mode (Code → IR) with AI:
- Intent extraction from code
- Semantic summary generation
- Type inference for holes
- Ambiguity detection in lifted specs

### Tasks

#### 4.1 Signature Definitions (Week 1)
**Deliverable**: `lift_sys/dspy_signatures/reverse_mode.py`

```python
import dspy

class ExtractIntentFromCode(dspy.Signature):
    """Extract high-level intent from source code."""

    code: str = dspy.InputField(desc="Source code to analyze")
    docstring: str = dspy.InputField(desc="Existing docstring if any", default="")
    function_name: str = dspy.InputField(desc="Function name")

    intent_summary: str = dspy.OutputField(
        desc="High-level summary of what the code does (2-3 sentences)"
    )
    goals: list[str] = dspy.OutputField(desc="Inferred goals of the code")
    roles: list[str] = dspy.OutputField(desc="Roles/actors involved")

class InferTypeFromUsage(dspy.Signature):
    """Infer type annotation from variable usage patterns."""

    variable_name: str = dspy.InputField(desc="Variable name")
    usage_examples: str = dspy.InputField(desc="Examples of variable usage")
    context: str = dspy.InputField(desc="Surrounding code context")

    inferred_type: str = dspy.OutputField(desc="Inferred type hint")
    confidence: float = dspy.OutputField(desc="Confidence score 0.0-1.0")
    rationale: str = dspy.OutputField(desc="Why this type was inferred")

class DetectAmbiguitiesInSpec(dspy.Signature):
    """Detect ambiguities and under-specifications in lifted spec."""

    code: str = dspy.InputField(desc="Original source code")
    lifted_ir: str = dspy.InputField(desc="Lifted IR JSON")

    ambiguities: list[str] = dspy.OutputField(
        desc="List of ambiguous or unclear aspects"
    )
    suggested_holes: str = dspy.OutputField(
        desc="JSON list of suggested TypedHole objects"
    )

class GenerateSpecFromTrace(dspy.Signature):
    """Generate assertions from execution trace / likely invariants."""

    function_signature: str = dspy.InputField(desc="Function signature")
    trace_examples: str = dspy.InputField(desc="Input/output examples from traces")
    invariants: str = dspy.InputField(desc="Likely invariants from Daikon")

    preconditions: list[str] = dspy.OutputField(desc="Inferred preconditions")
    postconditions: list[str] = dspy.OutputField(desc="Inferred postconditions")
    invariants_refined: list[str] = dspy.OutputField(desc="Refined invariants")
```

#### 4.2 Reverse Mode Modules (Week 2-4)
**Deliverable**: `lift_sys/dspy_modules/reverse_mode.py`

```python
import dspy
from lift_sys.dspy_signatures.reverse_mode import (
    ExtractIntentFromCode,
    InferTypeFromUsage,
    DetectAmbiguitiesInSpec,
    GenerateSpecFromTrace
)

class EnhancedIntentExtractor(dspy.Module):
    """Extract intent from code using AI."""

    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(ExtractIntentFromCode)

    def forward(self, code: str, function_name: str, docstring: str = ""):
        """Extract intent with reasoning."""
        return self.extract(
            code=code,
            function_name=function_name,
            docstring=docstring
        )

class TypeInferenceModule(dspy.Module):
    """Infer types from usage patterns."""

    def __init__(self):
        super().__init__()
        self.infer = dspy.ChainOfThought(InferTypeFromUsage)

    def forward(self, variable_name: str, usage_examples: str, context: str):
        """Infer type with confidence."""
        return self.infer(
            variable_name=variable_name,
            usage_examples=usage_examples,
            context=context
        )

class SpecAmbiguityDetector(dspy.Module):
    """Detect ambiguities in lifted specs."""

    def __init__(self):
        super().__init__()
        self.detect = dspy.ChainOfThought(DetectAmbiguitiesInSpec)

    def forward(self, code: str, lifted_ir: str):
        """Detect ambiguities."""
        return self.detect(code=code, lifted_ir=lifted_ir)
```

#### 4.3 Integration with Lifter (Week 5-6)
**Deliverable**: Update `lift_sys/reverse_mode/lifter.py`

```python
class SpecificationLifter:
    def __init__(self, config: LifterConfig, repo: Repo | None = None):
        # ... existing init ...

        # Add DSPy modules
        if config.use_ai_enhancement:
            self.intent_extractor = EnhancedIntentExtractor()
            self.type_inferencer = TypeInferenceModule()
            self.ambiguity_detector = SpecAmbiguityDetector()
        else:
            self.intent_extractor = None
            self.type_inferencer = None
            self.ambiguity_detector = None

    def _build_intent(
        self,
        findings: list[Finding],
        evidence_lookup: dict[object, str],
        code: str,
        function_name: str
    ) -> IntentClause:
        """Build intent with AI enhancement."""

        if self.intent_extractor:
            # Use DSPy to extract better intent
            result = self.intent_extractor(
                code=code,
                function_name=function_name,
                docstring=self._extract_docstring(code)
            )

            summary = result.intent_summary
            rationale = f"Extracted from code analysis. Goals: {', '.join(result.goals)}"
        else:
            # Fallback to old heuristics
            summary = "Lifted intent with typed holes"
            rationale = "Derived from static analysis"

        holes = [
            TypedHole(
                identifier="intent_gap",
                type_hint="Description",
                description=finding.message,
                constraints={
                    "provenance": finding.kind,
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.INTENT,
            )
            for finding in findings
        ]

        return IntentClause(summary=summary, rationale=rationale, holes=holes)
```

#### 4.4 Training Data & Optimization (Week 7-10)
**Deliverable**: Optimized reverse mode modules

**Training Data Sources**:
- Curated examples: 30 functions with ground truth intent
- Synthetic examples: Generate from high-quality codebases
- User feedback: Collect corrections

**Optimization**:
```python
# Optimize intent extraction
intent_optimizer = BootstrapFewShot(
    metric=intent_extraction_metric,
    max_bootstrapped_demos=8
)
optimized_intent_extractor = intent_optimizer.compile(
    EnhancedIntentExtractor(),
    trainset=intent_trainset
)
```

#### 4.5 Evaluation (Week 11-12)
**Metrics**:
- Intent quality (human evaluation)
- Type inference accuracy
- Ambiguity detection precision/recall

**Acceptance**:
- AI-enhanced reverse mode ≥20% better than heuristics
- Type inference 80%+ accurate
- Ambiguity detection 70%+ precision

### Phase 2 Success Metrics
- ✅ Reverse mode uses DSPy for intent extraction
- ✅ Type inference working with 80%+ accuracy
- ✅ Ambiguity detection 70%+ precision
- ✅ User study: AI summaries preferred over generic "Lifted intent"

**Phase 2 Estimated Effort**: 3 months (1 senior eng + 1 ML eng)

---

## 5. Phase 3: Ambiguity Detection + Hole Suggestions (Months 7-9)

### Goal
AI-powered ambiguity detection and hole filling:
- Detect semantic ambiguities (not just syntactic)
- Generate context-aware hole filling suggestions
- Learn from user accept/reject patterns

### Tasks

#### 5.1 Signatures (Week 1)
```python
# lift_sys/dspy_signatures/ambiguity.py

class DetectSemanticAmbiguities(dspy.Signature):
    """Detect semantic ambiguities in natural language prompt."""

    prompt: str = dspy.InputField(desc="User prompt")
    ir_draft: str = dspy.InputField(desc="Current IR draft JSON")

    ambiguities: str = dspy.OutputField(
        desc="JSON list of ambiguity objects with type, description, location"
    )
    confidence_scores: str = dspy.OutputField(
        desc="JSON dict mapping ambiguity to confidence 0.0-1.0"
    )

class SuggestHoleFill(dspy.Signature):
    """Suggest concrete value to fill a typed hole."""

    hole: str = dspy.InputField(desc="Typed hole JSON")
    ir_context: str = dspy.InputField(desc="Full IR JSON for context")
    surrounding_code: str = dspy.InputField(
        desc="Surrounding code if refining existing",
        default=""
    )

    suggestions: list[str] = dspy.OutputField(
        desc="List of suggested fills (ranked by likelihood)"
    )
    rationale: list[str] = dspy.OutputField(
        desc="Rationale for each suggestion"
    )
    confidence: list[float] = dspy.OutputField(
        desc="Confidence for each suggestion 0.0-1.0"
    )

class RefineAmbiguityFromFeedback(dspy.Signature):
    """Refine ambiguity detection based on user feedback."""

    original_prompt: str = dspy.InputField(desc="Original prompt")
    detected_ambiguities: str = dspy.InputField(desc="Ambiguities we detected")
    user_feedback: str = dspy.InputField(
        desc="User feedback: false positives, missed ambiguities"
    )

    refined_ambiguities: str = dspy.OutputField(
        desc="Improved ambiguity list based on feedback"
    )
```

#### 5.2 Modules (Week 2-4)
```python
# lift_sys/dspy_modules/ambiguity.py

class SemanticAmbiguityDetector(dspy.Module):
    """Detect semantic ambiguities with reasoning."""

    def __init__(self):
        super().__init__()
        self.detect = dspy.ChainOfThought(DetectSemanticAmbiguities)

    def forward(self, prompt: str, ir_draft: str):
        return self.detect(prompt=prompt, ir_draft=ir_draft)

class HoleSuggester(dspy.Module):
    """Suggest hole fills with ranked candidates."""

    def __init__(self):
        super().__init__()
        self.suggest = dspy.ChainOfThought(SuggestHoleFill)

    def forward(self, hole: TypedHole, ir: IntermediateRepresentation, code: str = ""):
        return self.suggest(
            hole=json.dumps(hole.to_dict()),
            ir_context=json.dumps(ir.to_dict()),
            surrounding_code=code
        )
```

#### 5.3 Training & Optimization (Week 5-8)
**Data Collection**:
- Collect user interactions with holes
- Track accepted vs rejected suggestions
- Build feedback loop

```python
# Example training data
training_examples = [
    dspy.Example(
        hole=TypedHole(
            identifier="return_type",
            type_hint="type",
            description="Specify return type",
            kind=HoleKind.SIGNATURE
        ).to_dict(),
        ir_context=ir.to_dict(),
        surrounding_code="",
        expected_suggestions=["int", "float", "str"],
        user_selected="int"
    )
]
```

#### 5.4 Integration (Week 9-10)
**API Endpoints**:
```python
# lift_sys/api/routes/holes.py

@router.post("/sessions/{session_id}/suggest-fill")
async def suggest_hole_fill(session_id: str, hole_id: str):
    """Get AI-powered suggestions for filling a hole."""
    ir = await get_ir(session_id)
    hole = find_hole(ir, hole_id)

    suggester = HoleSuggester()
    result = suggester(hole=hole, ir=ir)

    return {
        "suggestions": [
            {
                "value": sugg,
                "rationale": rat,
                "confidence": conf
            }
            for sugg, rat, conf in zip(
                result.suggestions,
                result.rationale,
                result.confidence
            )
        ]
    }

@router.post("/sessions/{session_id}/record-feedback")
async def record_hole_feedback(
    session_id: str,
    hole_id: str,
    accepted: bool,
    selected_value: str | None
):
    """Record user feedback for continuous learning."""
    # Store in database for future training
    await store_feedback(session_id, hole_id, accepted, selected_value)
```

### Phase 3 Success Metrics
- ✅ Semantic ambiguity detection working
- ✅ Hole suggestions 60%+ acceptance rate
- ✅ Users report suggestions helpful (survey >7/10)
- ✅ Feedback loop collecting data for re-training

**Phase 3 Estimated Effort**: 3 months (1 senior eng + 1 ML eng)

---

## 6. Phase 4: Entity Resolution + Intent Extraction (Months 10-12)

### Goal
AI-powered semantic understanding for new IR features:
- Entity resolution (pronouns, references)
- Intent classification
- Relationship extraction

### Tasks

#### 6.1 Signatures (Week 1-2)
```python
# lift_sys/dspy_signatures/semantic.py

class ResolveEntities(dspy.Signature):
    """Resolve entities and coreferences in natural language."""

    prompt: str = dspy.InputField(desc="Natural language prompt")
    previous_context: str = dspy.InputField(
        desc="Previous conversation context",
        default=""
    )

    entities: str = dspy.OutputField(
        desc="JSON list of entities with name, type, span"
    )
    coreferences: str = dspy.OutputField(
        desc="JSON dict mapping pronouns to entity IDs"
    )

class ClassifyIntent(dspy.Signature):
    """Classify user intent into taxonomy categories."""

    prompt: str = dspy.InputField(desc="User prompt")
    context: str = dspy.InputField(desc="Conversation context", default="")

    primary_intent: str = dspy.OutputField(
        desc="Primary intent category (CRUD, transformation, validation, etc.)"
    )
    secondary_intents: list[str] = dspy.OutputField(
        desc="Additional intent categories"
    )
    confidence: float = dspy.OutputField(desc="Confidence 0.0-1.0")

class ExtractRelationships(dspy.Signature):
    """Extract relationships between entities."""

    entities: str = dspy.InputField(desc="JSON list of entities")
    prompt: str = dspy.InputField(desc="Original prompt")

    relationships: str = dspy.OutputField(
        desc="JSON list of relationships (entity1, relation, entity2)"
    )
```

#### 6.2 Modules & Integration (Week 3-8)
Similar pattern to previous phases

#### 6.3 Training & Optimization (Week 9-12)
Focus on building high-quality training data for entity resolution

### Phase 4 Success Metrics
- ✅ Entity resolution 90%+ accuracy
- ✅ Intent classification 80%+ accuracy
- ✅ Relationship extraction working
- ✅ Integrated with semantic IR (from IR adoption Phase 1)

**Phase 4 Estimated Effort**: 3 months (1 senior eng + 1 ML eng + 1 NLP specialist)

---

## 7. Phase 5: Optimization Loop + Production (Months 13-14)

### Goal
- Continuous optimization pipeline
- Production monitoring
- Re-training workflow
- Model versioning

### Tasks

#### 7.1 Continuous Learning Pipeline (Week 1-4)
```python
# lift_sys/dspy_training/continuous_learning.py

class ContinuousOptimizer:
    """Continuously re-optimize DSPy modules from user feedback."""

    def __init__(self):
        self.feedback_store = FeedbackStore()
        self.model_registry = ModelRegistry()

    async def collect_feedback(self, days: int = 7) -> list[dspy.Example]:
        """Collect feedback from last N days."""
        feedback = await self.feedback_store.get_recent(days)

        # Convert to training examples
        examples = []
        for item in feedback:
            if item.user_accepted:
                examples.append(
                    dspy.Example(
                        prompt=item.prompt,
                        context=item.context,
                        expected_ir=item.ir_json
                    ).with_inputs("prompt", "context")
                )
        return examples

    async def retrain(self, module_name: str):
        """Re-train and deploy improved model."""
        # Load current model
        current_model = self.model_registry.load(module_name)

        # Collect new training data
        new_examples = await self.collect_feedback(days=30)
        if len(new_examples) < 10:
            logger.info("Not enough new data for retraining")
            return

        # Optimize
        optimizer = BootstrapFewShot(metric=ir_quality_metric)
        improved_model = optimizer.compile(
            current_model,
            trainset=new_examples
        )

        # Evaluate on held-out set
        devset = await self.feedback_store.get_validation_set()
        current_score = evaluate(current_model, devset)
        improved_score = evaluate(improved_model, devset)

        if improved_score > current_score:
            # Deploy new model
            version = self.model_registry.save(module_name, improved_model)
            logger.info(
                f"Deployed {module_name} v{version}: "
                f"{current_score:.3f} → {improved_score:.3f}"
            )
        else:
            logger.info(f"No improvement for {module_name}, keeping current")
```

#### 7.2 Monitoring & Observability (Week 5-6)
```python
# lift_sys/dspy_monitoring/metrics.py

class DSPyMetrics:
    """Track DSPy module performance in production."""

    def record_prediction(
        self,
        module_name: str,
        prediction: dspy.Prediction,
        latency_ms: float,
        user_satisfaction: float | None = None
    ):
        """Record prediction metrics."""
        # Send to OpenTelemetry
        metrics.record_histogram(
            "dspy.prediction.latency_ms",
            latency_ms,
            {"module": module_name}
        )

        if hasattr(prediction, 'confidence'):
            metrics.record_gauge(
                "dspy.prediction.confidence",
                prediction.confidence,
                {"module": module_name}
            )

        if user_satisfaction:
            metrics.record_gauge(
                "dspy.prediction.user_satisfaction",
                user_satisfaction,
                {"module": module_name}
            )
```

#### 7.3 Model Versioning (Week 7-8)
```python
# lift_sys/dspy_registry/model_registry.py

class ModelRegistry:
    """Version and manage DSPy models."""

    def save(self, module_name: str, module: dspy.Module) -> str:
        """Save model with version."""
        version = self._next_version(module_name)
        path = f"models/{module_name}/v{version}.json"
        module.save(path)

        # Store metadata
        await self.db.insert_model_version(
            name=module_name,
            version=version,
            path=path,
            metrics=self._compute_metrics(module),
            created_at=datetime.now()
        )

        return version

    def load(self, module_name: str, version: str | None = None) -> dspy.Module:
        """Load model (latest if version not specified)."""
        if not version:
            version = self._latest_version(module_name)

        path = f"models/{module_name}/v{version}.json"
        # Load appropriate module class
        ModuleClass = self._get_module_class(module_name)
        return ModuleClass.load(path)
```

### Phase 5 Success Metrics
- ✅ Continuous learning pipeline running
- ✅ Models improve over time (track monthly)
- ✅ Monitoring dashboard shows all DSPy metrics
- ✅ Model versioning working
- ✅ Automated re-training on schedule

**Phase 5 Estimated Effort**: 2 months (1 senior eng + 1 ML eng)

---

## 8. Migration Checklist

### Pre-Migration
- [ ] Install DSPy: `uv add dspy-ai`
- [ ] Set up provider adapter
- [ ] Define success metrics
- [ ] Prepare training data (at least 50 examples)

### Per Component Migration
- [ ] Define DSPy signatures
- [ ] Implement DSPy modules
- [ ] Create evaluation metrics
- [ ] Collect training data
- [ ] Run optimization
- [ ] A/B test vs old implementation
- [ ] Feature flag for gradual rollout
- [ ] Monitor metrics
- [ ] Flip default to DSPy

### Post-Migration
- [ ] Remove old implementation
- [ ] Update documentation
- [ ] Set up continuous learning
- [ ] Monitor production metrics

---

## 9. Risk Mitigation

### High Risks

#### 9.1 DSPy Performance
**Risk**: DSPy adds latency

**Mitigation**:
- Measure latency in A/B tests
- Optimize prompts for speed
- Cache predictions where possible
- Set timeout budgets

#### 9.2 Quality Regression
**Risk**: DSPy performs worse than manual prompts

**Mitigation**:
- Extensive evaluation before rollout
- A/B testing required
- Feature flags for quick rollback
- Keep old implementation as fallback

#### 9.3 Training Data Quality
**Risk**: Insufficient or poor-quality training data

**Mitigation**:
- Manual curation (at least 20 examples)
- Synthetic generation
- Continuous collection from user feedback
- Regular data quality audits

### Medium Risks

#### 9.4 Optimizer Instability
**Risk**: Optimizers produce inconsistent results

**Mitigation**:
- Use stable optimizers (BootstrapFewShot first)
- Multiple optimization runs
- Validation on held-out set
- Version control for reproducibility

#### 9.5 Integration Complexity
**Risk**: DSPy hard to integrate with existing code

**Mitigation**:
- Provider adapter (already designed)
- Gradual migration (one component at a time)
- Clear interfaces between DSPy and non-DSPy code
- Extensive testing

---

## 10. Success Metrics

### Technical Metrics

**Phase 1 (Forward Mode)**:
- ✅ IR generation quality +10% vs baseline
- ✅ A/B test: DSPy ≥ manual prompts
- ✅ Latency: <5s for 90% of queries

**Phase 2 (Reverse Mode)**:
- ✅ Intent extraction quality +20% vs heuristics
- ✅ Type inference 80%+ accuracy
- ✅ Ambiguity detection 70%+ precision

**Phase 3 (Hole Suggestions)**:
- ✅ Suggestion acceptance rate 60%+
- ✅ User satisfaction >7/10

**Phase 4 (Entity Resolution)**:
- ✅ Entity resolution 90%+ accuracy
- ✅ Intent classification 80%+ accuracy

**Phase 5 (Continuous Learning)**:
- ✅ Monthly quality improvement visible
- ✅ Automated retraining working
- ✅ Monitoring dashboard live

### Business Metrics

**Adoption**:
- Feature flags flipped to DSPy by default
- Old implementations removed
- User satisfaction maintained or improved

**Quality**:
- IR generation success rate +10%
- User-reported issues -20%
- Faster iteration on prompts (days → hours)

---

## 11. Resource Requirements

### Team Composition

**Core Team**:
- 1 Senior Engineer (Phases 1-5)
- 1 ML Engineer (Phases 1-5)
- 1 NLP Specialist (Phase 4 only)

**Part Time**:
- 1 Data Engineer (data collection pipelines)
- 1 DevOps (monitoring, deployment)

**Total**: ~2.5 FTE over 14 months

### Infrastructure

- DSPy compute: ~$500/month
- LLM API costs: ~$1K/month (for optimization)
- Training data storage: ~$100/month
- Monitoring: ~$200/month

**Total**: ~$1.8K/month = ~$25K over 14 months

---

## 12. Integration with IR Adoption Plan

### Coordination Points

**Phase 1 (IR Types & Refinements) + Phase 1 (DSPy Forward Mode)**:
- **Month 4**: IR types stable → DSPy can consume new IR schema
- **Synergy**: DSPy signatures updated to generate new IR format

**Phase 2 (IR Solver Integration) + Phase 2 (DSPy Reverse Mode)**:
- **Month 6**: Solvers ready → DSPy can use solver feedback for training
- **Synergy**: Solver counterexamples become training data

**Phase 3 (IR Hole Closures) + Phase 3 (DSPy Hole Suggestions)**:
- **Month 10**: Hole traces available → DSPy uses traces for suggestions
- **Synergy**: Hole evaluation traces inform suggestion generation

**Phase 4 (IR Surface Syntax) + Phase 4 (DSPy Entity Resolution)**:
- **Month 14**: Surface syntax parser → DSPy can work with Spec-IR
- **Synergy**: Entity resolution improves surface syntax parsing

**Phase 5 (IR Alignment) + Phase 5 (DSPy Continuous Learning)**:
- **Month 18**: Provenance tracking → DSPy training data has provenance
- **Synergy**: Intent ledger tracks DSPy optimization steps

### Timeline Alignment

```
Month    IR Adoption                   DSPy Migration
───────────────────────────────────────────────────────────
1-3      Phase 1: Types & Refinements  (Prep work)
4-6      Phase 2: Solvers              Phase 1: Forward Mode
7-10     Phase 3: Hole Closures        Phase 2: Reverse Mode
11-14    Phase 4: Surface Syntax       Phase 3: Hole Suggestions
15-18    Phase 5: Alignment            Phase 4: Entity Resolution
19-20    Phase 6: Production           Phase 5: Continuous Learning
```

**DSPy starts 3 months after IR adoption** to ensure IR schema is stable.

**Both converge around Month 18-20** for integrated production system.

---

## 13. Timeline Summary

```
Month   Phase                         Deliverables
────────────────────────────────────────────────────────────────
1-3     Phase 1: Forward Mode         DSPy setup
                                      NL → IR with DSPy
                                      Optimization pipeline
                                      A/B testing

4-6     Phase 2: Reverse Mode         Code → IR with AI
                                      Intent extraction
                                      Type inference
                                      Ambiguity detection

7-9     Phase 3: Hole Suggestions     Semantic ambiguity detection
                                      AI-powered suggestions
                                      Feedback collection

10-12   Phase 4: Entity Resolution    Entity resolution
                                      Intent classification
                                      Relationship extraction

13-14   Phase 5: Continuous Learning  Optimization pipeline
                                      Monitoring
                                      Model versioning
```

**Total Duration**: 14 months
**Parallel with IR**: Can run concurrently after Month 4
**Aggressive Timeline**: 12 months with larger team

---

## 14. Next Steps

### Immediate (This Week)
1. ✅ Review this plan with team
2. ⬜ Get buy-in on DSPy approach
3. ⬜ Install DSPy: `uv add dspy-ai`
4. ⬜ Set up provider adapter

### Week 2
1. ⬜ Define first signatures (Forward Mode)
2. ⬜ Start collecting training data
3. ⬜ Build simple prototype

### Month 1
1. ⬜ Complete DSPy setup
2. ⬜ Implement Forward Mode module
3. ⬜ Run first optimization

---

## 15. Conclusion

Migrating to DSPy will transform lift-sys AI components from brittle prompt hacking to **systematic, improvable, composable AI systems**.

**Key Benefits**:
1. ✅ **Stop prompt hacking**: Declarative signatures > manual prompts
2. ✅ **Get better over time**: Optimizers + continuous learning
3. ✅ **Faster iteration**: Change signatures, re-optimize (not rewrite prompts)
4. ✅ **Multi-model**: Easy LLM provider switching
5. ✅ **Composability**: Build complex AI from modules
6. ✅ **Reproducibility**: Version control for AI behavior

**Integration with IR 0.9**:
- DSPy generates new IR format
- Solver feedback improves DSPy training
- Hole traces inform suggestions
- Provenance tracks DSPy optimizations

**This is the AI infrastructure for the codelift.space vision.**

---

**Status**: Ready for review and approval
**Next Action**: Team review + kickoff meeting
**Owner**: Tech Lead + ML Engineer
