# H10: Optimization Metrics Specification

**Date**: 2025-10-21
**Status**: Design
**Phase**: 3 (Week 3)
**Priority**: CRITICAL PATH
**Blocks**: H8 (OptimizationAPI), H17 (OptimizationValidation)

---

## Overview

This document specifies the mathematical definitions for optimization metrics used to evaluate and improve the lift-sys pipeline. These metrics guide DSPy optimization (MIPROv2, COPRO) and route selection per ADR 001.

### Design Principles

1. **Measurable**: Computable from examples with ground truth
2. **Differentiable**: Smooth functions suitable for optimization
3. **Correlated**: Align with user satisfaction and real-world quality
4. **Composable**: Combine sub-metrics into aggregate scores
5. **Route-aware**: Track quality and cost per provider route (ADR 001)

---

## Core Quality Metrics

### 1. IR Quality Metric

**Purpose**: Measure how well predicted IR matches expected IR

**Signature**:
```python
def ir_quality(predicted: IR, expected: IR) -> float:
    """
    Compute IR quality score [0.0, 1.0].

    Args:
        predicted: Generated IR from pipeline
        expected: Ground truth IR (human-labeled)

    Returns:
        Quality score where 1.0 = perfect match
    """
```

**Mathematical Definition**:

```
ir_quality(P, E) = w1·intent_match(P, E)
                 + w2·signature_match(P, E)
                 + w3·structure_match(P, E)
                 + w4·constraint_match(P, E)

where:
  w1, w2, w3, w4 are weights (default: 0.3, 0.3, 0.2, 0.2)
  all sub-metrics return values in [0.0, 1.0]
```

**Sub-Metrics**:

**Intent Match** (w1 = 0.3):
```python
def intent_match(predicted: IR, expected: IR) -> float:
    """Measure intent description similarity."""
    return semantic_similarity(
        predicted.intent.description,
        expected.intent.description,
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    # Cosine similarity of embeddings
```

**Signature Match** (w2 = 0.3):
```python
def signature_match(predicted: IR, expected: IR) -> float:
    """Measure function signature correctness."""
    scores = []

    # Function name exact match
    scores.append(1.0 if predicted.signature.name == expected.signature.name else 0.0)

    # Parameter names and types
    p_params = set((p.name, p.type_hint) for p in predicted.signature.parameters)
    e_params = set((p.name, p.type_hint) for p in expected.signature.parameters)
    param_score = len(p_params & e_params) / max(len(p_params | e_params), 1)
    scores.append(param_score)

    # Return type
    scores.append(1.0 if predicted.signature.return_type == expected.signature.return_type else 0.5)

    return sum(scores) / len(scores)
```

**Structure Match** (w3 = 0.2):
```python
def structure_match(predicted: IR, expected: IR) -> float:
    """Measure structural similarity of effects."""
    p_effects = [type(e).__name__ for e in predicted.effects]
    e_effects = [type(e).__name__ for e in expected.effects]

    # Sequence similarity (order matters)
    return sequence_similarity(p_effects, e_effects)
    # Uses Levenshtein distance normalized to [0, 1]
```

**Constraint Match** (w4 = 0.2):
```python
def constraint_match(predicted: IR, expected: IR) -> float:
    """Measure constraint satisfaction."""
    if not expected.constraints:
        return 1.0

    satisfied = sum(
        1 for c in expected.constraints
        if constraint_satisfied(predicted, c)
    )
    return satisfied / len(expected.constraints)
```

---

### 2. Code Quality Metric

**Purpose**: Measure how well generated code matches expected code and passes tests

**Signature**:
```python
def code_quality(
    predicted: str,
    expected: str,
    tests: list[tuple[dict, Any]]
) -> float:
    """
    Compute code quality score [0.0, 1.0].

    Args:
        predicted: Generated Python code
        expected: Ground truth code (human-written)
        tests: List of (input_dict, expected_output) pairs

    Returns:
        Quality score where 1.0 = perfect match
    """
```

**Mathematical Definition**:

```
code_quality(P, E, T) = w1·syntax_correctness(P)
                      + w2·test_pass_rate(P, T)
                      + w3·semantic_similarity(P, E)
                      + w4·style_conformance(P, E)

where:
  w1, w2, w3, w4 are weights (default: 0.2, 0.4, 0.3, 0.1)
```

**Sub-Metrics**:

**Syntax Correctness** (w1 = 0.2):
```python
def syntax_correctness(code: str) -> float:
    """Check if code is syntactically valid Python."""
    try:
        ast.parse(code)
        return 1.0
    except SyntaxError:
        return 0.0
```

**Test Pass Rate** (w2 = 0.4):
```python
def test_pass_rate(code: str, tests: list[tuple[dict, Any]]) -> float:
    """Measure fraction of tests that pass."""
    if not tests:
        return 1.0

    passed = 0
    for inputs, expected_output in tests:
        try:
            result = execute_code(code, inputs)
            if result == expected_output:
                passed += 1
        except Exception:
            pass  # Test failed

    return passed / len(tests)
```

**Semantic Similarity** (w3 = 0.3):
```python
def semantic_similarity(predicted: str, expected: str) -> float:
    """Measure code semantic similarity via embeddings."""
    # Use CodeBERT or similar code embedding model
    pred_emb = embed_code(predicted)
    exp_emb = embed_code(expected)
    return cosine_similarity(pred_emb, exp_emb)
```

**Style Conformance** (w4 = 0.1):
```python
def style_conformance(predicted: str, expected: str) -> float:
    """Measure style/idiom similarity."""
    scores = []

    # Import similarity
    p_imports = extract_imports(predicted)
    e_imports = extract_imports(expected)
    import_score = len(p_imports & e_imports) / max(len(p_imports | e_imports), 1)
    scores.append(import_score)

    # Naming conventions (snake_case, etc.)
    scores.append(check_naming_conventions(predicted))

    # Docstring presence
    scores.append(1.0 if has_docstring(predicted) else 0.5)

    return sum(scores) / len(scores)
```

---

### 3. End-to-End Metric

**Purpose**: Measure overall pipeline quality from NLP prompt to working code

**Signature**:
```python
def end_to_end(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """
    Compute end-to-end pipeline quality [0.0, 1.0].

    Args:
        example: Input example with prompt and ground truth
        prediction: Pipeline output with IR and code

    Returns:
        Aggregate quality score
    """
```

**Mathematical Definition**:

```
end_to_end(Ex, Pr) = w1·ir_quality(Pr.ir, Ex.expected_ir)
                   + w2·code_quality(Pr.code, Ex.expected_code, Ex.tests)
                   + w3·latency_penalty(Pr.latency_ms)

where:
  w1, w2, w3 are weights (default: 0.4, 0.5, 0.1)
```

**Latency Penalty**:
```python
def latency_penalty(latency_ms: float, target_ms: float = 16000) -> float:
    """Penalize slow executions."""
    if latency_ms <= target_ms:
        return 1.0
    else:
        # Exponential decay: 50% penalty at 2x target, ~0 at 4x
        return math.exp(-2 * (latency_ms / target_ms - 1))
```

---

## Route-Aware Metrics (ADR 001)

### 4. Route Cost Metric

**Purpose**: Calculate cost per provider route for optimization

**Signature**:
```python
def route_cost(
    route: ProviderRoute,
    tokens: int,
    duration_ms: float
) -> float:
    """
    Compute cost in USD for a single execution.

    Args:
        route: Provider route used (BEST_AVAILABLE or MODAL_INFERENCE)
        tokens: Total tokens consumed
        duration_ms: Execution duration

    Returns:
        Cost in USD
    """
```

**Mathematical Definition**:

**Best Available Route**:
```python
def route_cost_best_available(tokens: int) -> float:
    """
    Cost for API providers (pay per token).

    Assumes Claude 3.5 Sonnet pricing:
      Input: $3.00 / 1M tokens
      Output: $15.00 / 1M tokens

    Approximation: 50/50 input/output split
    """
    avg_cost_per_token = (3.00 + 15.00) / 2 / 1_000_000
    return tokens * avg_cost_per_token
```

**Modal Inference Route**:
```python
def route_cost_modal_inference(duration_ms: float, gpu_type: str = "L40S") -> float:
    """
    Cost for Modal compute (pay per second).

    GPU costs (per second):
      L40S: $0.001 / sec
      H100: $0.003 / sec
      A100: $0.002 / sec
    """
    gpu_costs = {
        "L40S": 0.001,
        "H100": 0.003,
        "A100": 0.002,
    }
    cost_per_second = gpu_costs.get(gpu_type, 0.001)
    return (duration_ms / 1000) * cost_per_second
```

---

### 5. Route Quality Metric

**Purpose**: Measure quality by route and task type for migration decisions

**Signature**:
```python
def route_quality(
    route: ProviderRoute,
    task_type: str,
    metrics: dict[str, float]
) -> float:
    """
    Compute quality score for route/task combination.

    Args:
        route: Provider route used
        task_type: Task category ("reasoning", "constrained_gen", "classification")
        metrics: Dict with ir_quality, code_quality, test_pass_rate

    Returns:
        Aggregate quality score [0.0, 1.0]
    """
```

**Implementation**:
```python
def route_quality(
    route: ProviderRoute,
    task_type: str,
    metrics: dict[str, float]
) -> float:
    """Task-specific quality weighting."""

    # Different tasks prioritize different metrics
    weights = {
        "reasoning": {"ir_quality": 0.5, "code_quality": 0.3, "test_pass_rate": 0.2},
        "constrained_gen": {"ir_quality": 0.3, "code_quality": 0.2, "test_pass_rate": 0.5},
        "classification": {"ir_quality": 0.4, "code_quality": 0.4, "test_pass_rate": 0.2},
    }

    task_weights = weights.get(task_type, {"ir_quality": 0.4, "code_quality": 0.4, "test_pass_rate": 0.2})

    score = sum(metrics.get(k, 0.0) * v for k, v in task_weights.items())
    return score
```

---

### 6. Route Migration Suggestion

**Purpose**: Recommend route switches based on cost/quality tradeoffs

**Signature**:
```python
def suggest_route_migration(
    current_route: ProviderRoute,
    task_metrics: dict[str, float]
) -> ProviderRoute | None:
    """
    Suggest route change if beneficial.

    Args:
        current_route: Current provider route
        task_metrics: Observed metrics (quality, cost, latency)

    Returns:
        Recommended route or None if current is best
    """
```

**Migration Logic**:
```python
def suggest_route_migration(
    current_route: ProviderRoute,
    task_metrics: dict[str, float]
) -> ProviderRoute | None:
    """
    Decision tree for route migration.

    Rules:
    1. If quality < 0.6 on Modal → Try Best Available (better models)
    2. If cost > $0.05/request on Best Available → Try Modal (cheaper)
    3. If latency > 30s on Modal → Try Best Available (faster)
    4. If requires XGrammar → Must stay on Modal
    5. Otherwise → No change
    """
    requires_xgrammar = task_metrics.get("requires_schema", False)
    quality = task_metrics.get("quality", 0.0)
    cost = task_metrics.get("cost_usd", 0.0)
    latency_ms = task_metrics.get("latency_ms", 0.0)

    # Rule 4: XGrammar requirement
    if requires_xgrammar:
        return ProviderRoute.MODAL_INFERENCE  # No choice

    if current_route == ProviderRoute.MODAL_INFERENCE:
        # Rule 1: Low quality → try better models
        if quality < 0.6:
            return ProviderRoute.BEST_AVAILABLE

        # Rule 3: Slow execution → try faster API
        if latency_ms > 30000:
            return ProviderRoute.BEST_AVAILABLE

    elif current_route == ProviderRoute.BEST_AVAILABLE:
        # Rule 2: High cost → try cheaper compute
        if cost > 0.05:
            return ProviderRoute.MODAL_INFERENCE

    # No migration recommended
    return None
```

---

## Metric Aggregation

### Weighted Combination

For optimization, combine metrics into single score:

```python
def aggregate_metric(
    ir_score: float,
    code_score: float,
    e2e_score: float,
    cost: float,
    latency_ms: float,
    weights: dict[str, float] | None = None
) -> float:
    """
    Aggregate multiple metrics into single optimization target.

    Default weights:
      - quality (ir + code + e2e): 0.7
      - cost: 0.2
      - latency: 0.1
    """
    if weights is None:
        weights = {
            "quality": 0.7,
            "cost": 0.2,
            "latency": 0.1,
        }

    # Quality component (average of quality metrics)
    quality = (ir_score + code_score + e2e_score) / 3

    # Cost component (normalize to [0, 1], invert so lower cost = higher score)
    cost_normalized = 1.0 - min(cost / 0.10, 1.0)  # $0.10 = worst score 0.0

    # Latency component (normalize, invert)
    latency_normalized = 1.0 - min(latency_ms / 60000, 1.0)  # 60s = worst score 0.0

    return (
        weights["quality"] * quality
        + weights["cost"] * cost_normalized
        + weights["latency"] * latency_normalized
    )
```

---

## Validation Requirements

### Inter-Rater Reliability

Metrics must be validated against human judgment:

```python
def validate_metrics(
    examples: list[tuple[IR, IR, float]],  # (predicted, expected, human_score)
    metric_fn: Callable
) -> float:
    """
    Measure correlation between metric and human scores.

    Returns:
        Pearson correlation coefficient (target: >0.8)
    """
    metric_scores = [metric_fn(pred, exp) for pred, exp, _ in examples]
    human_scores = [score for _, _, score in examples]
    return pearson_correlation(metric_scores, human_scores)
```

### Acceptance Criteria Validation

1. **Measurability**: All metrics computable from examples ✓
2. **Smoothness**: Metrics use weighted sums and continuous functions ✓
3. **Correlation**: Validation against 20 hand-labeled examples with >0.8 correlation
4. **Composability**: Metrics combine via weighted aggregation ✓
5. **Route tracking**: All route-aware metrics implemented per ADR 001 ✓

---

## Implementation Checklist

- [ ] Implement core quality metrics (ir_quality, code_quality, end_to_end)
- [ ] Implement route-aware metrics (route_cost, route_quality, suggest_route_migration)
- [ ] Implement aggregation functions
- [ ] Create 20+ hand-labeled examples for validation
- [ ] Validate inter-rater reliability (>0.8 target)
- [ ] Create tests for all metric functions
- [ ] Integrate with H8 (OptimizationAPI)
- [ ] Document usage examples

---

**Status**: Specification Complete
**Next**: Implementation in `lift_sys/optimization/metrics.py`
