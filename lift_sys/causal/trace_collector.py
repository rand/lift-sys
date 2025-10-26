"""H21: Execution Trace Collection (STEP-07).

This module collects execution traces from running code to enable dynamic
mechanism fitting in STEP-08.

See specs/typed-holes-dowhy.md for complete H21 specification.
"""

import ast
import logging
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TraceCollectionError(Exception):
    """Base exception for trace collection errors."""

    pass


class ExecutionError(TraceCollectionError):
    """Raised when function execution fails."""

    pass


class InputGenerationError(TraceCollectionError):
    """Raised when input generation fails."""

    pass


class TraceCollector:
    """Collects execution traces from functions for dynamic SCM fitting.

    Type Signature (H21):
        collect_traces: (DiGraph, Dict[str, str], int) → DataFrame

    Constraints:
        - Must generate ≥100 samples per edge (configurable)
        - Must handle exceptions gracefully (skip failed samples)
        - Must return DataFrame with columns = node names
        - Must complete in <10s for 1000 samples (performance)

    Usage:
        >>> collector = TraceCollector()
        >>> traces = collector.collect_traces(
        ...     causal_graph=graph,
        ...     function_code={"node1": "def f(x): return x*2"},
        ...     num_samples=100
        ... )
        >>> traces.shape
        (100, N)  # N = number of nodes in graph

    Implementation: STEP-07 ✅
    """

    def __init__(self, random_seed: int | None = None):
        """Initialize trace collector.

        Args:
            random_seed: Random seed for reproducibility (optional)
        """
        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)

        self.compiled_functions: dict[str, Any] = {}
        self.function_signatures: dict[str, list[str]] = {}

    def collect_traces(
        self,
        causal_graph: nx.DiGraph,
        function_code: dict[str, str],
        num_samples: int = 100,
        input_ranges: dict[str, tuple[float, float]] | None = None,
    ) -> pd.DataFrame:
        """Collect execution traces from functions in causal graph.

        Args:
            causal_graph: Causal DAG from H20
            function_code: Dict of node_id → source code
            num_samples: Number of samples to collect (≥100 recommended)
            input_ranges: Optional dict of parameter → (min, max) for input generation
                         Default: (-10.0, 10.0) for all parameters

        Returns:
            DataFrame with shape (num_samples, num_nodes)
            Columns are node IDs, each row is one execution trace

        Raises:
            TraceCollectionError: If collection fails
            ExecutionError: If too many execution failures occur
            InputGenerationError: If input generation fails

        Performance:
            - <10s for 1000 samples, 100 nodes (requirement)
        """
        if not nx.is_directed_acyclic_graph(causal_graph):
            raise TraceCollectionError("causal_graph must be a DAG")

        if num_samples < 1:
            raise TraceCollectionError(f"num_samples must be ≥1, got {num_samples}")

        # Set default input ranges
        if input_ranges is None:
            input_ranges = {}

        # Compile all functions
        logger.info(f"Compiling {len(function_code)} functions...")
        for node_id, code in function_code.items():
            self._compile_function(node_id, code)

        # Get topological order for execution
        try:
            topo_order = list(nx.topological_sort(causal_graph))
        except nx.NetworkXError as e:
            raise TraceCollectionError(f"Failed to get topological order: {e}")

        # Handle empty graph case
        if len(topo_order) == 0:
            logger.info("Empty graph, returning empty DataFrame")
            return pd.DataFrame(index=range(num_samples))

        logger.info(f"Collecting {num_samples} samples for {len(topo_order)} nodes...")

        # Collect traces
        traces: dict[str, list[Any]] = {node_id: [] for node_id in topo_order}
        successful_samples = 0
        failed_samples = 0

        for sample_idx in range(num_samples):
            try:
                sample = self._collect_single_trace(topo_order, causal_graph, input_ranges)
                for node_id, value in sample.items():
                    traces[node_id].append(value)
                successful_samples += 1
            except Exception as e:
                logger.warning(f"Sample {sample_idx} failed: {e}")
                failed_samples += 1
                # Add NaN for failed samples
                for node_id in topo_order:
                    traces[node_id].append(np.nan)

                # Fail if too many failures
                if failed_samples > num_samples * 0.5:
                    raise ExecutionError(f"Too many failed samples: {failed_samples}/{num_samples}")

        logger.info(
            f"Collection complete: {successful_samples} successful, {failed_samples} failed"
        )

        # Convert to DataFrame
        df = pd.DataFrame(traces)

        # Drop rows with NaN (failed samples)
        df = df.dropna()

        if len(df) < num_samples * 0.5:
            raise ExecutionError(f"Too few successful samples: {len(df)}/{num_samples}")

        return df

    def _compile_function(self, node_id: str, code: str) -> None:
        """Compile function code and extract signature.

        Args:
            node_id: Node identifier
            code: Python source code for function

        Raises:
            TraceCollectionError: If compilation fails
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise TraceCollectionError(f"Failed to parse code for {node_id}: {e}")

        # Find function definition
        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_def = node
                break

        if not func_def:
            raise TraceCollectionError(f"No function definition found in {node_id}")

        # Check for async functions (not supported - would return coroutines)
        if isinstance(func_def, ast.AsyncFunctionDef):
            raise TraceCollectionError(
                f"Async functions not supported for trace collection: {node_id}"
            )

        # Extract parameters
        params = [arg.arg for arg in func_def.args.args]
        self.function_signatures[node_id] = params

        # Compile and execute to get function object
        try:
            compiled_code = compile(tree, f"<{node_id}>", "exec")
            namespace: dict[str, Any] = {}
            exec(compiled_code, namespace)

            # Find the function in namespace
            func = namespace.get(func_def.name)
            if func is None:
                raise TraceCollectionError(f"Function {func_def.name} not found in namespace")

            self.compiled_functions[node_id] = func
            logger.debug(f"Compiled {node_id}: {func_def.name}({', '.join(params)})")

        except Exception as e:
            raise TraceCollectionError(f"Failed to compile {node_id}: {e}")

    def _collect_single_trace(
        self,
        topo_order: list[str],
        causal_graph: nx.DiGraph,
        input_ranges: dict[str, tuple[float, float]],
    ) -> dict[str, Any]:
        """Collect a single execution trace.

        Args:
            topo_order: Topological order of nodes
            causal_graph: Causal DAG
            input_ranges: Parameter ranges for input generation

        Returns:
            Dict of node_id → output value for this trace

        Raises:
            ExecutionError: If execution fails
        """
        trace: dict[str, Any] = {}

        for node_id in topo_order:
            # Get function
            func = self.compiled_functions.get(node_id)
            if func is None:
                # No function for this node (e.g., input variable)
                # Generate random input
                param_range = input_ranges.get(node_id, (-10.0, 10.0))
                trace[node_id] = np.random.uniform(param_range[0], param_range[1])
                continue

            # Get function parameters
            params = self.function_signatures[node_id]

            # Get predecessor values (parent nodes in causal graph)
            predecessors = list(causal_graph.predecessors(node_id))

            # Build function arguments
            args = []
            for param in params:
                # Try to match parameter to predecessor or previous trace values
                value = None

                # First, check if parameter matches a predecessor node
                if param in predecessors:
                    value = trace.get(param)

                # If not, check all trace values (for parameter name matching)
                if value is None:
                    value = trace.get(param)

                # If still not found, generate random input
                if value is None:
                    param_range = input_ranges.get(param, (-10.0, 10.0))
                    value = np.random.uniform(param_range[0], param_range[1])

                args.append(value)

            # Execute function
            try:
                result = func(*args)
                trace[node_id] = result
            except Exception as e:
                raise ExecutionError(f"Failed to execute {node_id} with args {args}: {e}")

        return trace

    def generate_random_inputs(
        self,
        param_names: list[str],
        input_ranges: dict[str, tuple[float, float]] | None = None,
        num_samples: int = 1,
    ) -> dict[str, np.ndarray]:
        """Generate random inputs for parameters.

        Args:
            param_names: List of parameter names
            input_ranges: Optional dict of parameter → (min, max)
            num_samples: Number of samples to generate

        Returns:
            Dict of parameter → array of values (shape: num_samples)

        Example:
            >>> collector = TraceCollector(random_seed=42)
            >>> inputs = collector.generate_random_inputs(
            ...     param_names=["x", "y"],
            ...     input_ranges={"x": (0, 1), "y": (-5, 5)},
            ...     num_samples=10
            ... )
            >>> inputs["x"].shape
            (10,)
        """
        if input_ranges is None:
            input_ranges = {}

        inputs: dict[str, np.ndarray] = {}
        for param in param_names:
            param_range = input_ranges.get(param, (-10.0, 10.0))
            inputs[param] = np.random.uniform(param_range[0], param_range[1], size=num_samples)

        return inputs


def collect_traces(
    causal_graph: nx.DiGraph,
    function_code: dict[str, str],
    num_samples: int = 100,
    input_ranges: dict[str, tuple[float, float]] | None = None,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Collect execution traces from functions (convenience function).

    Args:
        causal_graph: Causal DAG from H20
        function_code: Dict of node_id → source code
        num_samples: Number of samples to collect (≥100 recommended)
        input_ranges: Optional dict of parameter → (min, max) for input generation
        random_seed: Random seed for reproducibility

    Returns:
        DataFrame with shape (num_samples, num_nodes)

    Example:
        >>> import networkx as nx
        >>> graph = nx.DiGraph([("x", "y")])
        >>> code = {"y": "def double(x): return x * 2"}
        >>> traces = collect_traces(graph, code, num_samples=100, random_seed=42)
        >>> traces.shape
        (100, 2)
        >>> traces.columns.tolist()
        ['x', 'y']
    """
    collector = TraceCollector(random_seed=random_seed)
    return collector.collect_traces(causal_graph, function_code, num_samples, input_ranges)
