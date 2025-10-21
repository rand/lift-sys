"""Optimization metrics for lift-sys pipeline evaluation.

This module implements the mathematical metric definitions specified in
docs/planning/H10_OPTIMIZATION_METRICS_SPEC.md.

All metrics return values in [0.0, 1.0] unless otherwise noted.
"""

import ast
import math
from typing import Any

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from lift_sys.dspy_signatures.provider_adapter import ProviderRoute
from lift_sys.ir import IntermediateRepresentation

# ============================================================================
# Core Quality Metrics
# ============================================================================


def ir_quality(
    predicted: IntermediateRepresentation, expected: IntermediateRepresentation
) -> float:
    """Compute IR quality score [0.0, 1.0].

    Args:
        predicted: Generated IR from pipeline
        expected: Ground truth IR (human-labeled)

    Returns:
        Quality score where 1.0 = perfect match

    Formula:
        ir_quality(P, E) = w1·intent_match(P, E)
                         + w2·signature_match(P, E)
                         + w3·structure_match(P, E)
                         + w4·constraint_match(P, E)

        where w1=0.3, w2=0.3, w3=0.2, w4=0.2
    """
    w1, w2, w3, w4 = 0.3, 0.3, 0.2, 0.2

    return (
        w1 * intent_match(predicted, expected)
        + w2 * signature_match(predicted, expected)
        + w3 * structure_match(predicted, expected)
        + w4 * constraint_match(predicted, expected)
    )


def intent_match(
    predicted: IntermediateRepresentation, expected: IntermediateRepresentation
) -> float:
    """Measure intent description similarity using embeddings.

    Args:
        predicted: Generated IR
        expected: Ground truth IR

    Returns:
        Cosine similarity of intent descriptions [0.0, 1.0]
    """
    return semantic_similarity(
        predicted.intent.summary,
        expected.intent.summary,
        model="sentence-transformers/all-MiniLM-L6-v2",
    )


def signature_match(
    predicted: IntermediateRepresentation, expected: IntermediateRepresentation
) -> float:
    """Measure function signature correctness.

    Args:
        predicted: Generated IR
        expected: Ground truth IR

    Returns:
        Average score across function name, parameters, and return type [0.0, 1.0]
    """
    scores = []

    # Function name exact match
    scores.append(1.0 if predicted.signature.name == expected.signature.name else 0.0)

    # Parameter names and types
    p_params = {(p.name, p.type_hint) for p in predicted.signature.parameters}
    e_params = {(p.name, p.type_hint) for p in expected.signature.parameters}
    param_score = len(p_params & e_params) / max(len(p_params | e_params), 1)
    scores.append(param_score)

    # Return type
    scores.append(1.0 if predicted.signature.returns == expected.signature.returns else 0.5)

    return sum(scores) / len(scores)


def structure_match(
    predicted: IntermediateRepresentation, expected: IntermediateRepresentation
) -> float:
    """Measure structural similarity of effects.

    Args:
        predicted: Generated IR
        expected: Ground truth IR

    Returns:
        Sequence similarity using Levenshtein distance [0.0, 1.0]
    """
    p_effects = [e.description for e in predicted.effects]
    e_effects = [e.description for e in expected.effects]

    return sequence_similarity(p_effects, e_effects)


def constraint_match(
    predicted: IntermediateRepresentation, expected: IntermediateRepresentation
) -> float:
    """Measure constraint satisfaction.

    Args:
        predicted: Generated IR
        expected: Ground truth IR

    Returns:
        Fraction of constraints satisfied [0.0, 1.0]
    """
    if not expected.constraints:
        return 1.0

    satisfied = sum(1 for c in expected.constraints if constraint_satisfied(predicted, c))
    return satisfied / len(expected.constraints)


# ============================================================================
# Code Quality Metrics
# ============================================================================


def code_quality(
    predicted: str,
    expected: str,
    tests: list[tuple[dict, Any]],
) -> float:
    """Compute code quality score [0.0, 1.0].

    Args:
        predicted: Generated Python code
        expected: Ground truth code (human-written)
        tests: List of (input_dict, expected_output) pairs

    Returns:
        Quality score where 1.0 = perfect match

    Formula:
        code_quality(P, E, T) = w1·syntax_correctness(P)
                              + w2·test_pass_rate(P, T)
                              + w3·semantic_similarity(P, E)
                              + w4·style_conformance(P, E)

        where w1=0.2, w2=0.4, w3=0.3, w4=0.1
    """
    w1, w2, w3, w4 = 0.2, 0.4, 0.3, 0.1

    return (
        w1 * syntax_correctness(predicted)
        + w2 * code_test_pass_rate(predicted, tests)
        + w3 * semantic_similarity(predicted, expected)
        + w4 * style_conformance(predicted, expected)
    )


def syntax_correctness(code: str) -> float:
    """Check if code is syntactically valid Python.

    Args:
        code: Python code string

    Returns:
        1.0 if valid, 0.0 if syntax error
    """
    try:
        ast.parse(code)
        return 1.0
    except SyntaxError:
        return 0.0


def code_test_pass_rate(code: str, tests: list[tuple[dict, Any]]) -> float:
    """Measure fraction of tests that pass.

    Args:
        code: Python code to execute
        tests: List of (input_dict, expected_output) pairs

    Returns:
        Fraction of tests passed [0.0, 1.0]
    """
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


def semantic_similarity(
    text1: str, text2: str, model: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> float:
    """Measure semantic similarity via embeddings.

    Args:
        text1: First text (code or natural language)
        text2: Second text (code or natural language)
        model: Sentence transformer model name

    Returns:
        Cosine similarity [0.0, 1.0]
    """
    # Load model (cached after first call)
    encoder = SentenceTransformer(model)

    # Generate embeddings
    emb1 = encoder.encode([text1])
    emb2 = encoder.encode([text2])

    # Compute cosine similarity
    similarity = cosine_similarity(emb1, emb2)[0][0]

    # Normalize to [0, 1] (cosine similarity is [-1, 1])
    return (similarity + 1.0) / 2.0


def style_conformance(predicted: str, expected: str) -> float:
    """Measure style/idiom similarity.

    Args:
        predicted: Generated code
        expected: Ground truth code

    Returns:
        Average score across import, naming, and docstring metrics [0.0, 1.0]
    """
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


# ============================================================================
# End-to-End Metrics
# ============================================================================


def end_to_end(
    ir_score: float,
    code_score: float,
    latency_ms: float,
    target_ms: float = 16000,
) -> float:
    """Compute end-to-end pipeline quality [0.0, 1.0].

    Args:
        ir_score: IR quality score from ir_quality()
        code_score: Code quality score from code_quality()
        latency_ms: Execution latency in milliseconds
        target_ms: Target latency (default 16s)

    Returns:
        Aggregate quality score

    Formula:
        end_to_end = w1·ir_score + w2·code_score + w3·latency_penalty(latency_ms)

        where w1=0.4, w2=0.5, w3=0.1
    """
    w1, w2, w3 = 0.4, 0.5, 0.1

    return w1 * ir_score + w2 * code_score + w3 * latency_penalty(latency_ms, target_ms)


def latency_penalty(latency_ms: float, target_ms: float = 16000) -> float:
    """Penalize slow executions.

    Args:
        latency_ms: Actual latency in milliseconds
        target_ms: Target latency (default 16s)

    Returns:
        Penalty score [0.0, 1.0] where 1.0 = at or below target

    Formula:
        - If latency <= target: 1.0
        - Otherwise: exp(-2 * (latency/target - 1))
          (50% penalty at 2x target, ~0 at 4x target)
    """
    if latency_ms <= target_ms:
        return 1.0
    else:
        # Exponential decay
        return math.exp(-2 * (latency_ms / target_ms - 1))


# ============================================================================
# Route-Aware Metrics (ADR 001)
# ============================================================================


def route_cost(
    route: ProviderRoute,
    tokens: int = 0,
    duration_ms: float = 0,
    gpu_type: str = "L40S",
) -> float:
    """Compute cost in USD for a single execution.

    Args:
        route: Provider route used (BEST_AVAILABLE or MODAL_INFERENCE)
        tokens: Total tokens consumed (for Best Available route)
        duration_ms: Execution duration in ms (for Modal route)
        gpu_type: GPU type for Modal (L40S, H100, A100)

    Returns:
        Cost in USD
    """
    if route == ProviderRoute.BEST_AVAILABLE:
        return route_cost_best_available(tokens)
    elif route == ProviderRoute.MODAL_INFERENCE:
        return route_cost_modal_inference(duration_ms, gpu_type)
    else:
        raise ValueError(f"Unknown route: {route}")


def route_cost_best_available(tokens: int) -> float:
    """Cost for API providers (pay per token).

    Assumes Claude 3.5 Sonnet pricing:
      Input: $3.00 / 1M tokens
      Output: $15.00 / 1M tokens

    Approximation: 50/50 input/output split

    Args:
        tokens: Total tokens consumed

    Returns:
        Cost in USD
    """
    avg_cost_per_token = (3.00 + 15.00) / 2 / 1_000_000
    return tokens * avg_cost_per_token


def route_cost_modal_inference(duration_ms: float, gpu_type: str = "L40S") -> float:
    """Cost for Modal compute (pay per second).

    GPU costs (per second):
      L40S: $0.001 / sec
      H100: $0.003 / sec
      A100: $0.002 / sec

    Args:
        duration_ms: Execution duration in milliseconds
        gpu_type: GPU type (L40S, H100, A100)

    Returns:
        Cost in USD
    """
    gpu_costs = {
        "L40S": 0.001,
        "H100": 0.003,
        "A100": 0.002,
    }
    cost_per_second = gpu_costs.get(gpu_type, 0.001)
    return (duration_ms / 1000) * cost_per_second


def route_quality(
    route: ProviderRoute,
    task_type: str,
    metrics: dict[str, float],
) -> float:
    """Compute quality score for route/task combination.

    Args:
        route: Provider route used
        task_type: Task category (reasoning, constrained_gen, classification)
        metrics: Dict with ir_quality, code_quality, test_pass_rate

    Returns:
        Aggregate quality score [0.0, 1.0]
    """
    # Different tasks prioritize different metrics
    weights = {
        "reasoning": {"ir_quality": 0.5, "code_quality": 0.3, "test_pass_rate": 0.2},
        "constrained_gen": {"ir_quality": 0.3, "code_quality": 0.2, "test_pass_rate": 0.5},
        "classification": {"ir_quality": 0.4, "code_quality": 0.4, "test_pass_rate": 0.2},
    }

    task_weights = weights.get(
        task_type,
        {"ir_quality": 0.4, "code_quality": 0.4, "test_pass_rate": 0.2},
    )

    score = sum(metrics.get(k, 0.0) * v for k, v in task_weights.items())
    return score


def suggest_route_migration(
    current_route: ProviderRoute,
    task_metrics: dict[str, float],
) -> ProviderRoute | None:
    """Recommend route change if beneficial.

    Args:
        current_route: Current provider route
        task_metrics: Observed metrics (quality, cost, latency, requires_schema)

    Returns:
        Recommended route or None if current is best

    Decision tree:
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


# ============================================================================
# Metric Aggregation
# ============================================================================


def aggregate_metric(
    ir_score: float,
    code_score: float,
    e2e_score: float,
    cost: float,
    latency_ms: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Aggregate multiple metrics into single optimization target.

    Args:
        ir_score: IR quality score
        code_score: Code quality score
        e2e_score: End-to-end quality score
        cost: Cost in USD
        latency_ms: Latency in milliseconds
        weights: Optional custom weights (default: quality=0.7, cost=0.2, latency=0.1)

    Returns:
        Aggregate score [0.0, 1.0]

    Formula:
        aggregate = w_quality * avg(ir, code, e2e)
                  + w_cost * (1 - min(cost/0.10, 1.0))
                  + w_latency * (1 - min(latency/60000, 1.0))
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
    latency_normalized = 1.0 - min(latency_ms / 60000, 1.0)  # 60s = worst

    return (
        weights["quality"] * quality
        + weights["cost"] * cost_normalized
        + weights["latency"] * latency_normalized
    )


# ============================================================================
# Helper Functions
# ============================================================================


def sequence_similarity(seq1: list[str], seq2: list[str]) -> float:
    """Compute sequence similarity using Levenshtein distance.

    Args:
        seq1: First sequence
        seq2: Second sequence

    Returns:
        Similarity score [0.0, 1.0]
    """
    # Levenshtein distance
    n, m = len(seq1), len(seq2)
    if n == 0 and m == 0:
        return 1.0
    if n == 0 or m == 0:
        return 0.0

    # Dynamic programming table
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    distance = dp[n][m]
    max_len = max(n, m)

    # Normalize to [0, 1]
    return 1.0 - (distance / max_len)


def constraint_satisfied(ir: IntermediateRepresentation, constraint: Any) -> bool:
    """Check if IR satisfies a constraint.

    Args:
        ir: IR to check
        constraint: Constraint to validate

    Returns:
        True if constraint is satisfied

    Note: This is a placeholder. Actual implementation depends on
    constraint representation in IR.
    """
    # TODO: Implement constraint checking based on IR constraint schema
    return True


def execute_code(code: str, inputs: dict) -> Any:
    """Execute code with given inputs.

    Args:
        code: Python code string
        inputs: Input dictionary

    Returns:
        Execution result

    Raises:
        Exception: If execution fails
    """
    # Simple execution context - creates 'inputs' variable for code to use
    namespace = {"inputs": inputs}
    exec(code, namespace)

    # Code should set 'result' variable
    return namespace.get("result")


def extract_imports(code: str) -> set[str]:
    """Extract import statements from code.

    Args:
        code: Python code string

    Returns:
        Set of imported module names
    """
    imports = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except SyntaxError:
        pass

    return imports


def check_naming_conventions(code: str) -> float:
    """Check if code follows Python naming conventions.

    Args:
        code: Python code string

    Returns:
        Score [0.0, 1.0] based on convention adherence
    """
    try:
        tree = ast.parse(code)
        total = 0
        correct = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total += 1
                # snake_case for functions
                if node.name.islower() and "_" not in node.name or node.name.count("_") > 0:
                    correct += 1
            elif isinstance(node, ast.ClassDef):
                total += 1
                # PascalCase for classes
                if node.name[0].isupper():
                    correct += 1

        return correct / total if total > 0 else 1.0
    except SyntaxError:
        return 0.0


def has_docstring(code: str) -> bool:
    """Check if code has a docstring.

    Args:
        code: Python code string

    Returns:
        True if docstring is present
    """
    try:
        tree = ast.parse(code)
        return ast.get_docstring(tree) is not None
    except SyntaxError:
        return False
