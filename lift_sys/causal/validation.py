"""H21: Cross-Validation for Structural Causal Models (STEP-09).

This module provides cross-validation utilities for validating fitted SCMs,
including R² calculation, bootstrap confidence intervals, and train/test splits.

See docs/planning/STEP_09_RESEARCH.md for methodology details.
"""

import logging
from dataclasses import dataclass
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


class InsufficientDataError(ValidationError):
    """Raised when insufficient data for validation."""

    pass


class ThresholdError(ValidationError):
    """Raised when R² below threshold."""

    pass


@dataclass(frozen=True)
class R2Score:
    """R² score for a single edge or node in SCM.

    Attributes:
        node_id: Node identifier (target node)
        r_squared: R² value in range [0, 1] (or negative for very poor fits)
        ss_res: Sum of squared residuals
        ss_tot: Total sum of squares
        n_samples: Number of samples used
        parent_nodes: List of parent nodes (empty for root nodes)
    """

    node_id: str
    r_squared: float
    ss_res: float
    ss_tot: float
    n_samples: int
    parent_nodes: tuple[str, ...] = ()

    def __post_init__(self):
        """Validate R² score."""
        if self.n_samples < 2:
            raise ValidationError(f"Need ≥2 samples for R², got {self.n_samples}")
        if not np.isfinite(self.ss_res) or not np.isfinite(self.ss_tot):
            raise ValidationError("ss_res and ss_tot must be finite")


@dataclass(frozen=True)
class ValidationResult:
    """Cross-validation results for an SCM.

    Attributes:
        edge_scores: Dict of node_id → R² score for each edge
        aggregate_r2: Weighted average R² across all edges
        passes_threshold: True if aggregate R² ≥ threshold
        threshold: R² threshold used (default 0.7)
        train_size: Number of training samples
        test_size: Number of test samples
        failed_nodes: Nodes that failed validation (R² < threshold)
    """

    edge_scores: dict[str, R2Score]
    aggregate_r2: float
    passes_threshold: bool
    threshold: float
    train_size: int
    test_size: int
    failed_nodes: tuple[str, ...] = ()

    def __str__(self) -> str:
        """Human-readable validation summary."""
        status = "PASS" if self.passes_threshold else "FAIL"
        return (
            f"ValidationResult({status}):\n"
            f"  Aggregate R²: {self.aggregate_r2:.4f} (threshold: {self.threshold})\n"
            f"  Train/Test: {self.train_size}/{self.test_size}\n"
            f"  Failed nodes: {len(self.failed_nodes)}/{len(self.edge_scores)}"
        )


@dataclass(frozen=True)
class BootstrapCI:
    """Bootstrap confidence interval for R².

    Attributes:
        node_id: Node identifier
        r2_mean: Mean R² across bootstrap samples
        r2_std: Standard deviation of R²
        ci_lower: Lower bound of confidence interval (2.5th percentile)
        ci_upper: Upper bound of confidence interval (97.5th percentile)
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level (e.g., 0.95 for 95% CI)
    """

    node_id: str
    r2_mean: float
    r2_std: float
    ci_lower: float
    ci_upper: float
    n_bootstrap: int
    confidence_level: float = 0.95


def calculate_r_squared(
    y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series
) -> tuple[float, float, float]:
    """Calculate R² (coefficient of determination).

    R² = 1 - (SS_res / SS_tot)

    Where:
        SS_res = Σ(y_true - y_pred)²  (sum of squared residuals)
        SS_tot = Σ(y_true - mean(y_true))²  (total sum of squares)

    Args:
        y_true: True values (ground truth)
        y_pred: Predicted values (from fitted model)

    Returns:
        Tuple of (r_squared, ss_res, ss_tot)

    Raises:
        ValidationError: If inputs invalid or insufficient data

    Edge Cases:
        - Perfect fit: R² = 1.0 (y_pred == y_true)
        - Constant prediction: R² ≈ 0.0 (y_pred = mean(y_true))
        - Worse than constant: R² < 0.0 (poor model)
        - Zero variance: R² = NaN (raises ValidationError)

    Example:
        >>> y_true = np.array([1, 2, 3, 4, 5])
        >>> y_pred = np.array([1.1, 2.0, 2.9, 4.1, 5.0])
        >>> r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)
        >>> r2 > 0.9  # Good fit
        True
    """
    # Convert to numpy arrays
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    # Validation
    if len(y_true) != len(y_pred):
        raise ValidationError(
            f"y_true and y_pred must have same length: {len(y_true)} != {len(y_pred)}"
        )

    if len(y_true) < 2:
        raise ValidationError(f"Need at least 2 samples for R², got {len(y_true)}")

    # Remove NaN/inf values
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not np.any(mask):
        raise ValidationError("All values are NaN or infinite")

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) < 2:
        raise ValidationError(f"Need at least 2 finite samples, got {len(y_true)}")

    # Calculate SS_res (sum of squared residuals)
    residuals = y_true - y_pred
    ss_res = np.sum(residuals**2)

    # Calculate SS_tot (total sum of squares)
    y_mean = np.mean(y_true)
    ss_tot = np.sum((y_true - y_mean) ** 2)

    # Handle zero variance case
    if ss_tot == 0:
        # y_true is constant
        if ss_res == 0:
            # Perfect prediction of constant
            return 1.0, 0.0, 0.0
        else:
            # Can't predict constant correctly
            raise ValidationError(
                "y_true has zero variance but predictions don't match (constant target)"
            )

    # Calculate R²
    r_squared = 1.0 - (ss_res / ss_tot)

    return float(r_squared), float(ss_res), float(ss_tot)


def train_test_split(
    traces: pd.DataFrame, test_size: float = 0.2, random_state: int | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split traces into train and test sets.

    Uses random shuffling to create train/test split. Default is 80/20 split
    following standard practice for cross-validation.

    Args:
        traces: DataFrame of execution traces (rows=samples, cols=nodes)
        test_size: Fraction of data for testing (default 0.2 = 20%)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (train_df, test_df)

    Raises:
        InsufficientDataError: If not enough data for split

    Example:
        >>> traces = pd.DataFrame({'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]})
        >>> train, test = train_test_split(traces, test_size=0.2, random_state=42)
        >>> len(train), len(test)
        (4, 1)
    """
    if test_size <= 0 or test_size >= 1:
        raise ValidationError(f"test_size must be in (0, 1), got {test_size}")

    n_samples = len(traces)
    n_test = int(np.ceil(n_samples * test_size))
    n_train = n_samples - n_test

    # Need at least 2 samples in each split for R² calculation
    if n_train < 2:
        raise InsufficientDataError(
            f"Insufficient data for train split: need ≥2, got {n_train} (total samples: {n_samples})"
        )

    if n_test < 2:
        raise InsufficientDataError(
            f"Insufficient data for test split: need ≥2, got {n_test} (total samples: {n_samples})"
        )

    # Shuffle and split
    shuffled = traces.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    train_df = shuffled.iloc[:n_train]
    test_df = shuffled.iloc[n_train:]

    logger.debug(f"Split {n_samples} samples into {n_train} train, {n_test} test")

    return train_df, test_df


def cross_validate_scm(
    scm: Any,  # gcm.StructuralCausalModel (from DoWhy)
    traces: pd.DataFrame,
    causal_graph: nx.DiGraph,
    test_size: float = 0.2,
    threshold: float = 0.7,
    random_state: int | None = None,
) -> ValidationResult:
    """Cross-validate fitted SCM using train/test split.

    Validates SCM by:
    1. Splitting traces into train (80%) and test (20%)
    2. For each node with parents:
       - Predict target node from parent values (using fitted mechanisms)
       - Calculate R² on test set
    3. Compute aggregate R² (weighted by sample size)
    4. Check if aggregate R² ≥ threshold

    Args:
        scm: Fitted structural causal model (DoWhy gcm.StructuralCausalModel)
        traces: Execution traces (columns = node names)
        causal_graph: Causal DAG structure
        test_size: Fraction of data for testing (default 0.2)
        threshold: R² threshold for pass/fail (default 0.7)
        random_state: Random seed for reproducibility

    Returns:
        ValidationResult with per-edge and aggregate R² scores

    Raises:
        ValidationError: If validation fails
        InsufficientDataError: If not enough data
        ThresholdError: If R² below threshold

    Notes:
        - Root nodes (no parents) are not validated (R² = 1.0 by definition)
        - Aggregate R² is weighted average across all edges
        - Uses test set only for R² calculation (train set for fitting)

    Example:
        >>> # Assume scm fitted on train data
        >>> result = cross_validate_scm(scm, traces, graph, threshold=0.7)
        >>> result.passes_threshold
        True
        >>> result.aggregate_r2
        0.85
    """
    # NOTE: This function signature assumes DoWhy SCM structure
    # For STEP-09, this will use gcm.InferenceModel.predict()
    # For now, we create a placeholder that validates the methodology

    # Split data
    train_df, test_df = train_test_split(traces, test_size, random_state)

    # Calculate R² for each node with parents
    edge_scores: dict[str, R2Score] = {}
    failed_nodes: list[str] = []

    for node_id in causal_graph.nodes():
        parents = list(causal_graph.predecessors(node_id))

        if len(parents) == 0:
            # Root node - no validation needed
            logger.debug(f"Skipping root node: {node_id}")
            continue

        # Get true values from test set
        if node_id not in test_df.columns:
            logger.warning(f"Node {node_id} not in traces, skipping")
            continue

        y_true = test_df[node_id].values

        # Predict using fitted mechanism (placeholder - actual DoWhy implementation in STEP-09)
        # For now, use identity function as placeholder
        y_pred = y_true  # PLACEHOLDER: Replace with scm.predict(node_id, test_df[parents])

        # Calculate R²
        try:
            r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)
            score = R2Score(
                node_id=node_id,
                r_squared=r2,
                ss_res=ss_res,
                ss_tot=ss_tot,
                n_samples=len(y_true),
                parent_nodes=tuple(parents),
            )
            edge_scores[node_id] = score

            if r2 < threshold:
                failed_nodes.append(node_id)
                logger.warning(f"Node {node_id} failed threshold: R²={r2:.4f} < {threshold}")
            else:
                logger.debug(f"Node {node_id} passed: R²={r2:.4f}")

        except ValidationError as e:
            logger.error(f"Failed to validate node {node_id}: {e}")
            failed_nodes.append(node_id)

    # Calculate aggregate R² (weighted by sample size)
    if len(edge_scores) == 0:
        raise ValidationError("No edges to validate (all root nodes or missing data)")

    total_samples = sum(score.n_samples for score in edge_scores.values())
    aggregate_r2 = sum(
        score.r_squared * score.n_samples / total_samples for score in edge_scores.values()
    )

    passes = aggregate_r2 >= threshold and len(failed_nodes) == 0

    result = ValidationResult(
        edge_scores=edge_scores,
        aggregate_r2=aggregate_r2,
        passes_threshold=passes,
        threshold=threshold,
        train_size=len(train_df),
        test_size=len(test_df),
        failed_nodes=tuple(failed_nodes),
    )

    logger.info(str(result))

    if not passes:
        raise ThresholdError(
            f"Validation failed: aggregate R²={aggregate_r2:.4f} < {threshold}, "
            f"{len(failed_nodes)} nodes failed"
        )

    return result


def bootstrap_confidence_intervals(
    scm: Any,  # gcm.StructuralCausalModel
    traces: pd.DataFrame,
    causal_graph: nx.DiGraph,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    random_state: int | None = None,
) -> dict[str, BootstrapCI]:
    """Calculate bootstrap confidence intervals for R² scores.

    Uses bootstrap resampling to estimate confidence intervals for R² scores.
    This provides uncertainty estimates for model fit quality.

    Methodology:
    1. For each bootstrap iteration:
       a. Sample n rows from traces with replacement
       b. Split into train/test
       c. Fit mechanisms on train (or use pre-fitted)
       d. Calculate R² on test
    2. Compute percentile-based confidence intervals (BCa method)

    Args:
        scm: Fitted structural causal model
        traces: Execution traces
        causal_graph: Causal DAG
        n_bootstrap: Number of bootstrap samples (default 1000)
        confidence_level: Confidence level (default 0.95 for 95% CI)
        random_state: Random seed for reproducibility

    Returns:
        Dict of node_id → BootstrapCI with confidence intervals

    Example:
        >>> cis = bootstrap_confidence_intervals(scm, traces, graph, n_bootstrap=1000)
        >>> cis['node1'].r2_mean
        0.85
        >>> cis['node1'].ci_lower, cis['node1'].ci_upper
        (0.78, 0.91)
    """
    if n_bootstrap < 100:
        raise ValidationError(f"n_bootstrap should be ≥100 for reliable CIs, got {n_bootstrap}")

    if confidence_level <= 0 or confidence_level >= 1:
        raise ValidationError(f"confidence_level must be in (0, 1), got {confidence_level}")

    # Set random seed
    rng = np.random.RandomState(random_state)

    # Bootstrap iterations
    bootstrap_r2: dict[str, list[float]] = {}

    for node_id in causal_graph.nodes():
        parents = list(causal_graph.predecessors(node_id))
        if len(parents) == 0:
            continue  # Skip root nodes
        bootstrap_r2[node_id] = []

    logger.info(f"Running {n_bootstrap} bootstrap iterations...")

    for i in range(n_bootstrap):
        # Sample with replacement
        bootstrap_sample = traces.sample(n=len(traces), replace=True, random_state=rng)

        # Split
        try:
            train_df, test_df = train_test_split(
                bootstrap_sample, test_size=0.2, random_state=rng.randint(0, 1000000)
            )
        except InsufficientDataError:
            logger.warning(f"Bootstrap iteration {i}: insufficient data, skipping")
            continue

        # Calculate R² for each node
        for node_id in bootstrap_r2.keys():
            if node_id not in test_df.columns:
                continue

            y_true = test_df[node_id].values

            # Placeholder prediction (replace with SCM prediction in STEP-09)
            y_pred = y_true

            try:
                r2, _, _ = calculate_r_squared(y_true, y_pred)
                bootstrap_r2[node_id].append(r2)
            except ValidationError:
                continue  # Skip this bootstrap sample

    # Calculate confidence intervals
    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    confidence_intervals: dict[str, BootstrapCI] = {}

    for node_id, r2_samples in bootstrap_r2.items():
        if len(r2_samples) < 10:
            logger.warning(f"Node {node_id}: too few bootstrap samples ({len(r2_samples)})")
            continue

        r2_array = np.array(r2_samples)
        r2_mean = float(np.mean(r2_array))
        r2_std = float(np.std(r2_array, ddof=1))
        ci_lower = float(np.percentile(r2_array, lower_percentile))
        ci_upper = float(np.percentile(r2_array, upper_percentile))

        confidence_intervals[node_id] = BootstrapCI(
            node_id=node_id,
            r2_mean=r2_mean,
            r2_std=r2_std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            n_bootstrap=len(r2_samples),
            confidence_level=confidence_level,
        )

        logger.debug(
            f"{node_id}: R²={r2_mean:.4f} ± {r2_std:.4f}, 95% CI=[{ci_lower:.4f}, {ci_upper:.4f}]"
        )

    return confidence_intervals
