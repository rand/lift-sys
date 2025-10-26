# Error Handling Strategy: DoWhy Causal Analysis Integration

**Date**: 2025-10-26
**Context**: Comprehensive error handling for DoWhy subprocess integration
**Dependencies**: INTEGRATION_RECOMMENDATIONS.md, INTEGRATION_PATTERNS_RESEARCH.md

---

## Executive Summary

This document defines a **comprehensive error handling strategy** for integrating DoWhy causal analysis into lift-sys, covering:

1. **Graph Extraction Failures** - AST analysis errors
2. **SCM Fitting Failures** - Model fitting errors
3. **Intervention Query Failures** - Query execution errors
4. **Subprocess Failures** - DoWhy process crashes, timeouts
5. **Data Quality Issues** - Insufficient/noisy data

**Key Principle**: **Graceful degradation** - causal analysis failures should NEVER break core lift-sys functionality.

**Error Taxonomy**:
- **Fatal Errors** (raise exception): Programmer errors, invalid inputs
- **Expected Failures** (return None + log): DoWhy unavailable, timeout, data issues
- **Warnings** (return partial result): Low confidence, degraded quality

---

## Table of Contents

1. [Error Taxonomy](#1-error-taxonomy)
2. [Graph Extraction Errors](#2-graph-extraction-errors)
3. [SCM Fitting Errors](#3-scm-fitting-errors)
4. [Intervention Query Errors](#4-intervention-query-errors)
5. [Subprocess Errors](#5-subprocess-errors)
6. [Data Quality Errors](#6-data-quality-errors)
7. [Error Messages & User Guidance](#7-error-messages--user-guidance)
8. [Logging Strategy](#8-logging-strategy)
9. [Recovery Strategies](#9-recovery-strategies)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Error Taxonomy

### 1.1 Error Categories

**Category 1: Fatal Errors (Raise Exception)**
- **Definition**: Programmer errors or invalid inputs that should never occur in production
- **Response**: Raise exception with clear message
- **Examples**: `None` passed as AST, malformed IR, invalid function call

**Category 2: Expected Failures (Return None + Log Warning)**
- **Definition**: External failures outside our control
- **Response**: Return `None`, log warning, continue execution
- **Examples**: DoWhy subprocess timeout, DoWhy not installed, graph contains cycles

**Category 3: Data Quality Warnings (Return Partial Result + Warning)**
- **Definition**: Analysis completes but with low confidence or degraded quality
- **Response**: Return result, attach warnings, log warning
- **Examples**: Low R² score, insufficient data, noisy relationships

**Category 4: Informational (Log Info)**
- **Definition**: Expected behaviors that users should know about
- **Response**: Log at INFO level, no error
- **Examples**: Circuit breaker opened, cache hit, analysis skipped (feature disabled)

---

### 1.2 Decision Tree

```
Error occurs
  |
  +-- Is it a programmer error? (None input, wrong type, etc.)
  |   YES -> FATAL: Raise exception
  |   NO  -> Continue
  |
  +-- Is it an external failure? (subprocess crash, DoWhy unavailable)
  |   YES -> EXPECTED FAILURE: Return None, log warning
  |   NO  -> Continue
  |
  +-- Is it a data quality issue? (low R², insufficient samples)
  |   YES -> WARNING: Return partial result, attach warning
  |   NO  -> Continue
  |
  +-- Is it informational? (cache hit, analysis skipped)
      YES -> INFO: Log at INFO level, continue normally
```

---

## 2. Graph Extraction Errors

### 2.1 Common Failure Modes

**Failure Mode 1: Empty AST**
- **Cause**: Module has no functions/variables
- **Category**: Warning
- **Response**: Return empty graph with warning

**Failure Mode 2: AST Parse Error**
- **Cause**: Invalid Python syntax (should not happen in lift-sys context)
- **Category**: Fatal (if AST is invalid, IR extraction already failed)
- **Response**: Raise `ValueError`

**Failure Mode 3: Cycle Detection**
- **Cause**: Recursive functions create cycles (not a DAG)
- **Category**: Expected Failure
- **Response**: Return `None`, log warning

**Failure Mode 4: Too Large Graph**
- **Cause**: Graph has >10,000 nodes (performance issue)
- **Category**: Expected Failure
- **Response**: Return `None`, log warning with size

---

### 2.2 Error Handling Implementation

```python
from typing import Optional
import logging

class CausalGraphBuilder:
    """Builds causal graphs from AST."""

    MAX_NODES = 10_000  # Performance limit

    def build(self, ast_tree) -> Optional[CausalGraph]:
        """Build causal graph from AST.

        Args:
            ast_tree: Python AST node

        Returns:
            CausalGraph if successful, None if failed

        Raises:
            ValueError: If AST is None or malformed (programmer error)
        """
        # FATAL: Validate inputs
        if ast_tree is None:
            raise ValueError("AST cannot be None")

        try:
            # Extract nodes and edges
            nodes = self._extract_nodes(ast_tree)
            edges = self._extract_edges(ast_tree, nodes)

            # WARNING: Empty graph
            if len(nodes) == 0:
                logging.warning("Empty causal graph (no functions/variables found)")
                return CausalGraph(nodes=[], edges=[])

            # EXPECTED FAILURE: Graph too large
            if len(nodes) > self.MAX_NODES:
                logging.warning(
                    f"Causal graph too large ({len(nodes)} nodes > "
                    f"{self.MAX_NODES} limit), skipping"
                )
                return None

            # Build graph
            graph = CausalGraph(nodes=nodes, edges=edges)

            # EXPECTED FAILURE: Cycle detection
            if graph.has_cycles():
                logging.warning(
                    "Causal graph contains cycles (not a DAG), cannot fit SCM"
                )
                return None

            # INFO: Success
            logging.info(
                f"Built causal graph: {len(nodes)} nodes, {len(edges)} edges"
            )
            return graph

        except Exception as e:
            # EXPECTED FAILURE: Unexpected error during extraction
            logging.error(f"Causal graph extraction failed: {e}", exc_info=True)
            return None
```

---

### 2.3 User-Facing Error Messages

**Empty Graph**:
```
WARNING: Causal graph is empty (module contains no functions or variables)
Suggestion: Ensure the module defines functions with data flow relationships
```

**Graph Too Large**:
```
WARNING: Causal graph too large (12,534 nodes > 10,000 limit)
Suggestion: Analyze a smaller module or increase MAX_NODES configuration
```

**Cycle Detected**:
```
WARNING: Causal graph contains cycles (not a DAG)
Suggestion: Recursive functions are not supported by DoWhy SCM fitting.
Consider analyzing non-recursive subgraphs separately.
```

---

## 3. SCM Fitting Errors

### 3.1 Common Failure Modes

**Failure Mode 1: Graph Not a DAG**
- **Cause**: Cycles in graph (should be caught earlier, but defense-in-depth)
- **Category**: Expected Failure
- **Response**: Return `None`, log error

**Failure Mode 2: Insufficient Data**
- **Cause**: <100 samples for fitting
- **Category**: Warning
- **Response**: Return fitted SCM with low-confidence warning

**Failure Mode 3: Low R² Score**
- **Cause**: Noisy data, non-linear relationships
- **Category**: Warning (or Expected Failure if below threshold)
- **Response**: Return fitted SCM with warning, or `None` if `validate_r2=True`

**Failure Mode 4: DoWhy Fitting Crash**
- **Cause**: DoWhy internal error (singular matrix, numerical instability, etc.)
- **Category**: Expected Failure
- **Response**: Return `None`, log error with traceback

**Failure Mode 5: Column Mismatch**
- **Cause**: Graph nodes don't match execution trace columns
- **Category**: Expected Failure (trace collection may have failed for some variables)
- **Response**: Return `None`, log warning

---

### 3.2 Error Handling Implementation

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class FittedSCM:
    """Fitted Structural Causal Model with metadata."""
    scm: Any  # DoWhy SCM object
    r2_scores: Dict[str, float]
    mean_r2: float
    warnings: List[str]

class SCMFitter:
    """Fits Structural Causal Models from causal graphs and traces."""

    MIN_SAMPLES = 100
    R2_WARNING_THRESHOLD = 0.7

    def fit(
        self,
        causal_graph: CausalGraph,
        traces: Optional[pd.DataFrame] = None,
        config: Optional[CausalConfig] = None
    ) -> Optional[FittedSCM]:
        """Fit SCM from graph and traces.

        Args:
            causal_graph: Causal DAG
            traces: Execution traces (optional, uses static inference if None)
            config: Causal analysis configuration

        Returns:
            FittedSCM if successful, None if failed

        Raises:
            ValueError: If graph is None (programmer error)
        """
        config = config or CausalConfig.default()

        # FATAL: Validate inputs
        if causal_graph is None:
            raise ValueError("Causal graph cannot be None")

        # EXPECTED FAILURE: Empty graph
        if len(causal_graph.nodes) == 0:
            logging.warning("Cannot fit SCM: causal graph is empty")
            return None

        # EXPECTED FAILURE: Cycles (defense-in-depth)
        if causal_graph.has_cycles():
            logging.error("Cannot fit SCM: graph contains cycles (not a DAG)")
            return None

        warnings = []

        # WARNING: Insufficient data
        if traces is not None and len(traces) < self.MIN_SAMPLES:
            warnings.append(
                f"Insufficient data for fitting ({len(traces)} samples < "
                f"{self.MIN_SAMPLES} recommended). Results may be unreliable."
            )
            logging.warning(warnings[-1])

        # EXPECTED FAILURE: Column mismatch
        if traces is not None:
            missing_cols = set(causal_graph.nodes) - set(traces.columns)
            if missing_cols:
                logging.error(
                    f"Cannot fit SCM: missing trace data for nodes: {missing_cols}"
                )
                return None

        try:
            # Call DoWhy subprocess
            result = self._call_dowhy_fit(causal_graph, traces, config)

            # EXPECTED FAILURE: DoWhy subprocess failed
            if result is None:
                logging.error("SCM fitting failed: DoWhy subprocess unavailable")
                return None

            # Extract results
            scm = result["scm"]
            r2_scores = result["validation"]["r2_scores"]
            mean_r2 = result["validation"]["mean_r2"]

            # WARNING: Low R² score
            if mean_r2 < self.R2_WARNING_THRESHOLD:
                warnings.append(
                    f"Low R² score ({mean_r2:.3f} < {self.R2_WARNING_THRESHOLD}). "
                    f"Causal relationships may be weak or non-linear."
                )
                logging.warning(warnings[-1])

                # EXPECTED FAILURE: Enforce R² threshold (if configured)
                if config.validate_r2 and mean_r2 < config.r2_threshold:
                    logging.error(
                        f"SCM validation failed: R² {mean_r2:.3f} < "
                        f"threshold {config.r2_threshold}"
                    )
                    return None

            # INFO: Success
            logging.info(
                f"Fitted SCM: {len(scm['mechanisms'])} mechanisms, "
                f"mean R² = {mean_r2:.3f}"
            )

            return FittedSCM(
                scm=scm,
                r2_scores=r2_scores,
                mean_r2=mean_r2,
                warnings=warnings
            )

        except Exception as e:
            # EXPECTED FAILURE: Unexpected error
            logging.error(f"SCM fitting failed: {e}", exc_info=True)
            return None

    def _call_dowhy_fit(
        self,
        graph: CausalGraph,
        traces: Optional[pd.DataFrame],
        config: CausalConfig
    ) -> Optional[Dict[str, Any]]:
        """Call DoWhy subprocess to fit SCM."""
        from lift_sys.causal.dowhy_client import call_dowhy

        input_data = {
            "graph": {
                "nodes": graph.nodes,
                "edges": graph.edges
            },
            "traces": {
                col: traces[col].tolist()
                for col in traces.columns
            } if traces is not None else None,
            "config": {
                "quality": config.quality,
                "validate_r2": config.validate_r2,
                "r2_threshold": config.r2_threshold
            }
        }

        return call_dowhy(input_data)
```

---

### 3.3 User-Facing Error Messages

**Insufficient Data**:
```
WARNING: Insufficient data for SCM fitting (47 samples < 100 recommended)
Results may be unreliable. Consider collecting more execution traces.
Impact: Lower confidence in causal effect estimates
```

**Low R² Score**:
```
WARNING: Low R² score (0.52 < 0.70 threshold)
Possible causes:
  - Noisy data (add more samples or reduce measurement noise)
  - Non-linear relationships (try config.quality = "BETTER")
  - Missing confounders (check if all relevant variables are traced)
Impact: Causal estimates may be inaccurate
```

**Column Mismatch**:
```
ERROR: Cannot fit SCM - missing trace data for nodes: ['validate_input', 'sanitize_data']
Suggestion: Ensure execution traces include all variables in the causal graph.
Run with debug logging to see which variables were traced.
```

---

## 4. Intervention Query Errors

### 4.1 Common Failure Modes

**Failure Mode 1: Node Not in Graph**
- **Cause**: User queries non-existent node
- **Category**: Fatal (programmer error or user input validation failure)
- **Response**: Raise `ValueError`

**Failure Mode 2: SCM Not Fitted**
- **Cause**: User tries to intervene without fitted SCM
- **Category**: Fatal
- **Response**: Raise `RuntimeError`

**Failure Mode 3: Invalid Intervention Value**
- **Cause**: User provides wrong type (string for numeric variable)
- **Category**: Fatal
- **Response**: Raise `TypeError`

**Failure Mode 4: DoWhy Query Crash**
- **Cause**: DoWhy internal error during intervention estimation
- **Category**: Expected Failure
- **Response**: Return `None`, log error

**Failure Mode 5: Numerical Instability**
- **Cause**: Intervention causes overflow/underflow in DoWhy
- **Category**: Expected Failure
- **Response**: Return `None`, log warning

---

### 4.2 Error Handling Implementation

```python
from typing import Optional, Dict, Any

class InterventionEngine:
    """Execute interventional queries on fitted SCMs."""

    def intervene(
        self,
        scm: FittedSCM,
        intervention: Dict[str, Any],
        num_samples: int = 1000
    ) -> Optional[InterventionResult]:
        """Estimate impact of intervention.

        Args:
            scm: Fitted SCM
            intervention: {node: new_value} mapping
            num_samples: Number of samples for estimation

        Returns:
            InterventionResult if successful, None if failed

        Raises:
            ValueError: If intervention contains non-existent nodes
            RuntimeError: If SCM is not fitted
            TypeError: If intervention values have wrong type
        """
        # FATAL: Validate SCM
        if scm is None:
            raise RuntimeError(
                "Cannot perform intervention: SCM not fitted. "
                "Call lifter.fit_scm() first."
            )

        # FATAL: Validate intervention nodes exist
        graph_nodes = set(scm.scm["graph"]["nodes"])
        intervention_nodes = set(intervention.keys())
        invalid_nodes = intervention_nodes - graph_nodes

        if invalid_nodes:
            raise ValueError(
                f"Cannot intervene on non-existent nodes: {invalid_nodes}. "
                f"Valid nodes: {sorted(graph_nodes)}"
            )

        # FATAL: Validate intervention value types
        for node, value in intervention.items():
            # Get expected type from SCM metadata (if available)
            expected_type = scm.scm.get("types", {}).get(node)
            if expected_type and not isinstance(value, expected_type):
                raise TypeError(
                    f"Invalid intervention value for '{node}': "
                    f"expected {expected_type.__name__}, got {type(value).__name__}"
                )

        try:
            # Call DoWhy subprocess
            result = self._call_dowhy_intervene(scm, intervention, num_samples)

            # EXPECTED FAILURE: DoWhy subprocess failed
            if result is None:
                logging.error(
                    f"Intervention query failed: DoWhy subprocess unavailable"
                )
                return None

            # Check for numerical instability warnings
            if result.get("warnings"):
                for warning in result["warnings"]:
                    logging.warning(f"Intervention warning: {warning}")

            # INFO: Success
            logging.info(
                f"Intervention completed: {len(intervention)} nodes, "
                f"{num_samples} samples"
            )

            return InterventionResult.from_dict(result)

        except Exception as e:
            # EXPECTED FAILURE: Unexpected error
            logging.error(f"Intervention query failed: {e}", exc_info=True)
            return None
```

---

### 4.3 User-Facing Error Messages

**Node Not in Graph**:
```
ERROR: Cannot intervene on non-existent node 'invalid_function'
Available nodes: ['validate_input', 'process_data', 'generate_output', 'save_results']
Suggestion: Check spelling or use ir.causal_graph.nodes to see available nodes
```

**SCM Not Fitted**:
```
ERROR: Cannot perform intervention - SCM not fitted
Suggestion: Ensure causal analysis succeeded:
  1. Check ir.causal_graph is not None
  2. Check ir.causal_model is not None
  3. If both are None, DoWhy subprocess may have failed (check logs)
```

**Invalid Intervention Value**:
```
ERROR: Invalid intervention value for 'threshold': expected float, got str
Suggestion: Provide correct type:
  ir.causal_intervention({"threshold": 0.5})  # ✓ Correct
  ir.causal_intervention({"threshold": "0.5"})  # ✗ Wrong
```

---

## 5. Subprocess Errors

### 5.1 Common Failure Modes

**Failure Mode 1: DoWhy Not Installed**
- **Cause**: `.venv-dowhy/bin/python` doesn't exist
- **Category**: Expected Failure
- **Response**: Return `None`, log error with setup instructions

**Failure Mode 2: Subprocess Timeout**
- **Cause**: DoWhy analysis takes >30s
- **Category**: Expected Failure
- **Response**: Return `None`, log warning

**Failure Mode 3: Subprocess Crash (Exit Code ≠ 0)**
- **Cause**: DoWhy internal error, Python exception
- **Category**: Expected Failure
- **Response**: Return `None`, log error with stderr

**Failure Mode 4: Invalid JSON Output**
- **Cause**: DoWhy prints to stdout (corrupts JSON), malformed response
- **Category**: Expected Failure
- **Response**: Return `None`, log error with partial output

**Failure Mode 5: Circuit Breaker Open**
- **Cause**: 3+ consecutive failures
- **Category**: Expected Failure (fail-fast)
- **Response**: Return `None`, log info (circuit breaker state)

---

### 5.2 Error Handling Implementation

```python
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

class DoWhySubprocessError(Exception):
    """Base exception for DoWhy subprocess errors."""
    pass

class DoWhyNotInstalledError(DoWhySubprocessError):
    """DoWhy environment not found."""
    pass

class DoWhyTimeoutError(DoWhySubprocessError):
    """DoWhy subprocess timed out."""
    pass

class DoWhyCrashError(DoWhySubprocessError):
    """DoWhy subprocess crashed."""
    pass

class DoWhyOutputError(DoWhySubprocessError):
    """DoWhy returned invalid output."""
    pass


def call_dowhy_subprocess(
    input_data: Dict[str, Any],
    timeout: float = 30.0
) -> Optional[Dict[str, Any]]:
    """Call DoWhy subprocess with comprehensive error handling.

    Args:
        input_data: JSON-serializable input
        timeout: Timeout in seconds

    Returns:
        DoWhy output dict, or None if failed

    Note: This function NEVER raises exceptions (graceful degradation)
    """
    # Check if DoWhy venv exists
    venv_python = Path(".venv-dowhy/bin/python")
    if not venv_python.exists():
        # EXPECTED FAILURE: DoWhy not installed
        error_msg = (
            "DoWhy environment not found (.venv-dowhy/bin/python missing).\n"
            "Setup instructions:\n"
            "  1. uv venv --python 3.11 .venv-dowhy\n"
            "  2. source .venv-dowhy/bin/activate\n"
            "  3. uv pip install dowhy pandas numpy\n"
            "Or run: ./scripts/setup/install_dowhy.sh"
        )
        logging.error(error_msg)
        return None

    script_path = Path("scripts/dowhy/fit_scm.py")
    if not script_path.exists():
        # FATAL: This should never happen (script missing)
        logging.error(f"DoWhy script not found: {script_path}")
        return None

    try:
        # Run subprocess with timeout
        result = subprocess.run(
            [str(venv_python), str(script_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=timeout
        )

    except subprocess.TimeoutExpired:
        # EXPECTED FAILURE: Timeout
        logging.warning(
            f"DoWhy subprocess timed out after {timeout}s. "
            f"Consider increasing timeout or simplifying graph."
        )
        return None

    except Exception as e:
        # EXPECTED FAILURE: Unexpected subprocess error
        logging.error(f"DoWhy subprocess failed: {e}", exc_info=True)
        return None

    # Check exit code
    if result.returncode != 0:
        # EXPECTED FAILURE: DoWhy crashed
        logging.error(
            f"DoWhy subprocess failed (exit code {result.returncode}):\n"
            f"STDERR: {result.stderr[:500]}"
        )
        return None

    # Parse JSON output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        # EXPECTED FAILURE: Invalid JSON
        logging.error(
            f"DoWhy returned invalid JSON: {e}\n"
            f"Output (first 500 chars): {result.stdout[:500]}"
        )
        return None

    # Check status field
    if output.get("status") == "error":
        # EXPECTED FAILURE: DoWhy reported error
        logging.error(
            f"DoWhy error: {output.get('error', 'Unknown error')}\n"
            f"Traceback: {output.get('traceback', 'N/A')}"
        )
        return None

    # INFO: Success
    logging.info("DoWhy subprocess succeeded")
    return output
```

---

### 5.3 User-Facing Error Messages

**DoWhy Not Installed**:
```
ERROR: DoWhy environment not found (.venv-dowhy/bin/python missing)

Setup Instructions:
  1. Create Python 3.11 venv:
     uv venv --python 3.11 .venv-dowhy

  2. Activate venv:
     source .venv-dowhy/bin/activate

  3. Install DoWhy:
     uv pip install dowhy pandas numpy

  4. Verify:
     .venv-dowhy/bin/python -c "import dowhy; print(dowhy.__version__)"

Or use automated setup script:
  ./scripts/setup/install_dowhy.sh

Documentation: docs/setup/DOWHY_SETUP.md
```

**Subprocess Timeout**:
```
WARNING: DoWhy analysis timed out after 30.0s

Possible causes:
  - Large causal graph (>1,000 nodes)
  - Complex SCM fitting (non-linear mechanisms)
  - Insufficient system resources

Suggestions:
  - Increase timeout: CausalConfig(call_timeout=60.0)
  - Simplify graph: analyze smaller modules
  - Use faster quality setting: CausalConfig(quality="GOOD")
```

**Subprocess Crash**:
```
ERROR: DoWhy subprocess crashed (exit code 1)

STDERR:
  Traceback (most recent call last):
    File "scripts/dowhy/fit_scm.py", line 42, in main
      scm = fit_structural_causal_model(graph, traces)
    File "...dowhy/gcm/fitting.py", line 123, in fit
      raise ValueError("Graph contains cycles")
  ValueError: Graph contains cycles

Suggestion: This is likely a DoWhy bug or unsupported input.
  - Check that causal graph is a valid DAG (no cycles)
  - Report issue: https://github.com/py-why/dowhy/issues
  - Enable debug logging: logging.basicConfig(level=logging.DEBUG)
```

**Invalid JSON Output**:
```
ERROR: DoWhy returned invalid JSON

Output (first 500 chars):
  Fitting SCM...
  Progress: 50%
  Progress: 100%
  {"status": "success", "scm": ...}

Cause: DoWhy printed to stdout (should only output JSON)

Suggestion: This is a DoWhy script bug. Check:
  - scripts/dowhy/fit_scm.py has no print() statements
  - DoWhy warnings suppressed (warnings.filterwarnings('ignore'))
```

---

## 6. Data Quality Errors

### 6.1 Common Failure Modes

**Failure Mode 1: Insufficient Samples**
- **Cause**: <100 execution traces
- **Category**: Warning
- **Response**: Return fitted SCM with low-confidence warning

**Failure Mode 2: Noisy Data**
- **Cause**: High variance, outliers
- **Category**: Warning
- **Response**: Return fitted SCM with R² warning

**Failure Mode 3: Missing Variables**
- **Cause**: Some graph nodes have no trace data
- **Category**: Expected Failure
- **Response**: Return `None`, suggest which variables missing

**Failure Mode 4: Constant Variables**
- **Cause**: Variable never changes (no variance)
- **Category**: Warning
- **Response**: Return fitted SCM, warn about uninformative variables

**Failure Mode 5: Perfect Correlation**
- **Cause**: Y = X exactly (R² = 1.0)
- **Category**: Info
- **Response**: Return fitted SCM, note deterministic relationship

---

### 6.2 Error Handling Implementation

```python
def validate_traces(
    graph: CausalGraph,
    traces: pd.DataFrame
) -> List[str]:
    """Validate execution traces for quality issues.

    Args:
        graph: Causal graph
        traces: Execution traces

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []

    # Check sample size
    if len(traces) < 100:
        warnings.append(
            f"Insufficient samples ({len(traces)} < 100). "
            f"Results may be unreliable."
        )

    # Check for missing columns
    missing = set(graph.nodes) - set(traces.columns)
    if missing:
        warnings.append(
            f"Missing trace data for nodes: {sorted(missing)}. "
            f"These variables cannot be included in the SCM."
        )

    # Check for constant variables
    for col in traces.columns:
        if traces[col].nunique() == 1:
            warnings.append(
                f"Variable '{col}' is constant (no variance). "
                f"Cannot learn causal mechanism."
            )

    # Check for high correlation (potential multicollinearity)
    corr_matrix = traces.corr().abs()
    high_corr = []
    for i in range(len(corr_matrix)):
        for j in range(i + 1, len(corr_matrix)):
            if corr_matrix.iloc[i, j] > 0.95:
                high_corr.append(
                    (corr_matrix.index[i], corr_matrix.columns[j])
                )

    if high_corr:
        warnings.append(
            f"High correlation detected (>0.95): {high_corr[:3]}. "
            f"May cause multicollinearity issues."
        )

    return warnings
```

---

### 6.3 User-Facing Error Messages

**Insufficient Samples**:
```
WARNING: Insufficient samples (47 < 100 recommended)

Impact:
  - Lower confidence in causal estimates
  - Higher variance in intervention predictions
  - Overfitting risk

Suggestions:
  - Collect more execution traces (run code with diverse inputs)
  - Use cross-validation to detect overfitting
  - Interpret results with caution
```

**Missing Variables**:
```
ERROR: Missing trace data for nodes: ['validate_input', 'sanitize_data']

Cause: These variables were not captured during execution tracing

Suggestions:
  1. Ensure these variables are assigned in executed code paths
  2. Check if variables are local (may not be traced)
  3. Use static analysis only (no traces): lifter.fit_scm(traces=None)

Debug: Enable trace logging to see which variables are captured
```

**Constant Variables**:
```
WARNING: Variable 'DEBUG_MODE' is constant (value always False)

Impact: Cannot learn causal mechanism (no variance to explain)

Suggestions:
  - Run code with different configurations (e.g., DEBUG_MODE=True)
  - Remove constant variables from causal graph
  - Use static analysis to infer mechanism
```

---

## 7. Error Messages & User Guidance

### 7.1 Error Message Template

**Structure**:
```
[LEVEL]: [Brief description]

[Optional: Detailed explanation]

[Optional: Impact/Consequences]

Suggestions:
  - [Actionable suggestion 1]
  - [Actionable suggestion 2]
  - [Actionable suggestion 3]

[Optional: Related documentation]
```

**Example**:
```
ERROR: DoWhy subprocess timed out after 30.0s

Cause: Causal graph is very large (12,534 nodes) and SCM fitting is slow

Impact: Causal analysis unavailable for this module

Suggestions:
  - Increase timeout: lifter.lift(..., causal_config=CausalConfig(call_timeout=60))
  - Analyze smaller modules (split large files)
  - Use faster quality setting: CausalConfig(quality="GOOD")

Documentation: docs/troubleshooting/CAUSAL_ANALYSIS.md#timeout-errors
```

---

### 7.2 Contextual Help

**Include in error messages**:
1. **Root cause** (why did this happen?)
2. **Impact** (what can't I do now?)
3. **Actionable suggestions** (how do I fix it?)
4. **Documentation links** (where can I learn more?)

**Avoid**:
- Vague messages ("Analysis failed")
- Technical jargon without explanation
- Suggestions that don't help ("Try again later")
- Blaming the user ("You provided invalid input")

---

## 8. Logging Strategy

### 8.1 Logging Levels

**DEBUG**: Internal state, function entry/exit
```python
logging.debug("Entering build_causal_graph(ast=%s)", ast)
logging.debug("Extracted %d nodes: %s", len(nodes), nodes)
```

**INFO**: Expected operations, success paths
```python
logging.info("Built causal graph: %d nodes, %d edges", len(nodes), len(edges))
logging.info("Fitted SCM: mean R² = %.3f", mean_r2)
```

**WARNING**: Degraded functionality, low confidence
```python
logging.warning("Insufficient data (%d samples < 100)", len(traces))
logging.warning("Low R² score (%.3f < %.3f)", mean_r2, threshold)
```

**ERROR**: Operation failed, feature unavailable
```python
logging.error("DoWhy subprocess failed: %s", stderr)
logging.error("Cannot fit SCM: graph contains cycles")
```

**CRITICAL**: Should never happen (logic bugs)
```python
logging.critical("Unreachable code reached in intervention_engine.py:123")
```

---

### 8.2 Structured Logging

**Use structured logging for analytics**:
```python
import structlog

logger = structlog.get_logger()

# Good: Structured
logger.info(
    "causal_graph_built",
    num_nodes=len(nodes),
    num_edges=len(edges),
    has_cycles=graph.has_cycles()
)

# Bad: Unstructured
logging.info(f"Built graph with {len(nodes)} nodes")
```

**Benefits**:
- Easy to parse logs programmatically
- Track metrics (success rate, performance)
- Filter/aggregate by field

---

### 8.3 Log Sampling

**For high-frequency events, sample logs**:
```python
import random

# Sample 1% of debug logs (avoid log spam)
if random.random() < 0.01:
    logging.debug("Processing node: %s", node)
```

---

## 9. Recovery Strategies

### 9.1 Automatic Recovery

**Strategy 1: Retry with Backoff**
```python
def call_with_retry(func, max_retries=3, backoff=2.0):
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff ** attempt
            logging.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)
```

**Use case**: Transient DoWhy subprocess failures

---

**Strategy 2: Fallback to Cached Result**
```python
def get_causal_graph_with_cache(ast):
    """Get causal graph with cache fallback."""
    try:
        return build_causal_graph(ast)
    except Exception as e:
        # Try cache
        cached = cache.get(hash(str(ast)))
        if cached:
            logging.warning(f"Using cached causal graph due to: {e}")
            return cached
        else:
            logging.error("No cache available, analysis failed")
            return None
```

**Use case**: DoWhy subprocess unavailable, but have cached result from previous run

---

**Strategy 3: Fallback to Static Analysis**
```python
def fit_scm_with_fallback(graph, traces):
    """Fit SCM with fallback to static inference."""
    if traces is not None and len(traces) >= 100:
        # Try dynamic fitting (with traces)
        scm = fit_scm_dynamic(graph, traces)
        if scm is not None:
            return scm

    # Fallback: static inference (no traces)
    logging.warning("Falling back to static SCM inference (no traces)")
    return fit_scm_static(graph)
```

**Use case**: Execution traces unavailable or insufficient

---

### 9.2 User-Initiated Recovery

**Strategy 4: Manual Retry Button** (UI)
```python
# In UI/CLI
if ir.causal_graph is None:
    print("Causal analysis failed. Retry with different settings?")
    choice = input("[1] Retry with longer timeout\n[2] Skip causal analysis\n> ")

    if choice == "1":
        ir = lifter.lift(
            "file.py",
            include_causal=True,
            causal_config=CausalConfig(call_timeout=60)
        )
```

---

## 10. Testing Strategy

### 10.1 Error Injection Tests

**Test all failure modes with mocked errors**:
```python
# In tests/causal/test_error_handling.py

def test_dowhy_not_installed(monkeypatch):
    """Test graceful degradation when DoWhy not installed."""
    # Mock: .venv-dowhy doesn't exist
    monkeypatch.setattr(Path, "exists", lambda self: False)

    # Should return None, not crash
    result = call_dowhy_subprocess({})
    assert result is None

def test_dowhy_timeout(monkeypatch):
    """Test timeout handling."""
    # Mock: subprocess.run raises TimeoutExpired
    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=30)

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Should return None, log warning
    result = call_dowhy_subprocess({}, timeout=30)
    assert result is None

def test_dowhy_crash(monkeypatch):
    """Test subprocess crash handling."""
    # Mock: subprocess returns exit code 1
    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="DoWhy crashed: ValueError"
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Should return None, log error
    result = call_dowhy_subprocess({})
    assert result is None
```

---

### 10.2 Error Message Validation Tests

**Test error messages are helpful**:
```python
def test_error_messages_are_helpful(caplog):
    """Ensure error messages provide actionable guidance."""
    # Trigger error
    with caplog.at_level(logging.ERROR):
        result = call_dowhy_subprocess({})

    # Check error message content
    error_log = caplog.records[0].message

    # Should include:
    assert "DoWhy" in error_log
    assert "Setup instructions" in error_log or "Suggestion" in error_log

    # Should NOT include:
    assert "Unknown error" not in error_log
    assert "Contact support" not in error_log
```

---

### 10.3 Integration Tests with Real Failures

**Test with real DoWhy installed but broken**:
```python
def test_with_broken_dowhy():
    """Integration test: DoWhy installed but broken."""
    # Modify DoWhy script to crash
    with open(".venv-dowhy/lib/python3.11/site-packages/dowhy/__init__.py", "a") as f:
        f.write("\nraise RuntimeError('Test failure')")

    try:
        # Should handle gracefully
        ir = lifter.lift("test.py", include_causal=True)
        assert ir.causal_graph is None  # Feature unavailable
    finally:
        # Restore DoWhy
        subprocess.run(["uv", "pip", "install", "--force-reinstall", "dowhy"])
```

---

## 11. Summary

### 11.1 Error Handling Principles

1. **Graceful Degradation**: Core lift-sys works even if causal analysis fails
2. **Clear Errors**: Users understand what failed and why
3. **Actionable Guidance**: Suggestions help users fix issues
4. **Fail-Fast**: Timeouts and circuit breakers prevent hanging
5. **Defensive Programming**: Validate inputs, handle unexpected errors
6. **Comprehensive Logging**: Track failures for debugging and analytics

---

### 11.2 Error Handling Checklist

For every error scenario:
- [ ] Categorize error (Fatal, Expected Failure, Warning, Info)
- [ ] Write error handling code (try/except, validation, etc.)
- [ ] Create helpful error message (cause, impact, suggestions)
- [ ] Add logging (appropriate level)
- [ ] Write test to trigger error
- [ ] Verify error message in test
- [ ] Document error in troubleshooting guide

---

### 11.3 Key Takeaways

**For Graph Extraction**:
- Empty graphs → Warning (return empty graph)
- Cycles → Expected Failure (return None)
- Too large → Expected Failure (return None)

**For SCM Fitting**:
- Insufficient data → Warning (return SCM with warning)
- Low R² → Warning or Expected Failure (configurable)
- DoWhy crash → Expected Failure (return None)

**For Interventions**:
- Invalid node → Fatal (raise ValueError)
- DoWhy crash → Expected Failure (return None)

**For Subprocess**:
- DoWhy not installed → Expected Failure (return None + setup instructions)
- Timeout → Expected Failure (return None + timeout suggestion)
- Crash → Expected Failure (return None + error details)

**Always**:
- Return `None` for expected failures (graceful degradation)
- Raise exceptions for programmer errors (fail-fast)
- Log at appropriate level (ERROR for failures, WARNING for degraded quality)
- Provide actionable error messages (cause, impact, suggestions)

---

## References

- [INTEGRATION_RECOMMENDATIONS.md](./INTEGRATION_RECOMMENDATIONS.md) - Integration design
- [INTEGRATION_PATTERNS_RESEARCH.md](./INTEGRATION_PATTERNS_RESEARCH.md) - Pattern research
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Resilient Systems Design](https://newrelic.com/blog/best-practices/design-software-for-graceful-degradation)

**Last Updated**: 2025-10-26
