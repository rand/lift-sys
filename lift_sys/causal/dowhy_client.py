"""
DoWhy Subprocess Client

Python 3.13-compatible client for calling DoWhy SCM fitting subprocess.
Use this module from lift_sys code to interface with DoWhy.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd


class DoWhySubprocessError(Exception):
    """Error raised when DoWhy subprocess fails."""

    pass


class DoWhyClient:
    """
    Client for calling DoWhy subprocess worker.

    Example:
        >>> client = DoWhyClient()
        >>> result = client.fit_scm(graph, traces)
        >>> print(result["validation"]["mean_r2"])
        0.95
    """

    def __init__(
        self, python_path: str | None = None, script_path: str | None = None, timeout: float = 60.0
    ):
        """
        Initialize DoWhy subprocess client.

        Args:
            python_path: Path to Python 3.11 executable (default: .venv-dowhy/bin/python)
            script_path: Path to fit_scm.py script (default: scripts/dowhy/fit_scm.py)
            timeout: Subprocess timeout in seconds (default: 60.0)
        """
        # Resolve project root (from lift_sys/causal/ → project root)
        self.project_root = Path(__file__).parent.parent.parent

        # Set paths
        if python_path is None:
            self.python_path = self.project_root / ".venv-dowhy" / "bin" / "python"
        else:
            self.python_path = Path(python_path)

        if script_path is None:
            self.script_path = self.project_root / "scripts" / "dowhy" / "fit_scm.py"
        else:
            self.script_path = Path(script_path)

        self.timeout = timeout

        # Validate paths
        if not self.python_path.exists():
            raise FileNotFoundError(
                f"Python 3.11 executable not found: {self.python_path}\n"
                f"Run: uv venv --python 3.11 .venv-dowhy"
            )

        if not self.script_path.exists():
            raise FileNotFoundError(f"DoWhy script not found: {self.script_path}")

    def fit_scm(
        self,
        graph: nx.DiGraph,
        traces: pd.DataFrame,
        quality: str = "GOOD",
        validate_r2: bool = True,
        r2_threshold: float = 0.7,
        test_size: float = 0.2,
    ) -> dict[str, Any]:
        """
        Fit Structural Causal Model using DoWhy subprocess.

        Args:
            graph: Causal graph (NetworkX DiGraph)
            traces: Execution traces (pandas DataFrame)
            quality: Model quality ("GOOD", "BETTER", "BEST")
            validate_r2: Whether to enforce R² threshold
            r2_threshold: Minimum R² required (default: 0.7)
            test_size: Fraction of data for validation (default: 0.2)

        Returns:
            Dict with keys:
                - status: "success", "validation_failed", "warning", or "error"
                - scm: Fitted model structure
                - validation: R² scores and pass/fail status
                - metadata: Fitting time, sample counts, etc.

        Raises:
            DoWhySubprocessError: If subprocess fails
            ValueError: If input validation fails
        """
        # Validate inputs
        if not isinstance(graph, nx.DiGraph):
            raise ValueError("graph must be a NetworkX DiGraph")

        if not isinstance(traces, pd.DataFrame):
            raise ValueError("traces must be a pandas DataFrame")

        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("graph must be a Directed Acyclic Graph (DAG)")

        # Validate graph nodes match trace columns
        graph_nodes = set(graph.nodes())
        trace_columns = set(traces.columns)

        if graph_nodes != trace_columns:
            missing_in_traces = graph_nodes - trace_columns
            missing_in_graph = trace_columns - graph_nodes
            raise ValueError(
                f"Graph nodes and trace columns do not match.\n"
                f"  Missing in traces: {missing_in_traces}\n"
                f"  Missing in graph: {missing_in_graph}"
            )

        # Prepare input
        input_data = {
            "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
            "traces": {col: traces[col].tolist() for col in traces.columns},
            "config": {
                "quality": quality,
                "validate_r2": validate_r2,
                "r2_threshold": r2_threshold,
                "test_size": test_size,
            },
        }

        # Run subprocess
        try:
            result = subprocess.run(
                [str(self.python_path), str(self.script_path)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,  # Don't raise on non-zero exit
            )
        except subprocess.TimeoutExpired as e:
            raise DoWhySubprocessError(f"DoWhy subprocess timed out after {self.timeout}s") from e
        except Exception as e:
            raise DoWhySubprocessError(f"Failed to run DoWhy subprocess: {e}") from e

        # Parse output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise DoWhySubprocessError(
                f"Failed to parse DoWhy output as JSON.\n"
                f"stdout: {result.stdout[:500]}\n"
                f"stderr: {result.stderr[:500]}"
            ) from e

        # Check for errors
        if output.get("status") == "error":
            error_msg = output.get("error", "Unknown error")
            traceback = output.get("traceback", "")
            raise DoWhySubprocessError(
                f"DoWhy subprocess failed: {error_msg}\nTraceback:\n{traceback}"
            )

        return output

    def query_scm(
        self,
        graph: nx.DiGraph,
        traces: pd.DataFrame,
        interventions: list[dict[str, Any]],
        query_nodes: list[str] | None = None,
        num_samples: int = 1000,
        quality: str = "GOOD",
    ) -> dict[str, Any]:
        """
        Execute intervention query on fitted SCM using DoWhy subprocess.

        This method combines SCM fitting and querying in a single subprocess call.

        Args:
            graph: Causal graph (NetworkX DiGraph)
            traces: Execution traces (pandas DataFrame)
            interventions: List of intervention dicts [{"type": "hard", "node": "x", "value": 5}, ...]
            query_nodes: Nodes to query (None = all nodes)
            num_samples: Number of samples to draw (default: 1000)
            quality: Model quality ("GOOD", "BETTER", "BEST")

        Returns:
            Dict with keys:
                - status: "success" or "error"
                - query_type: "interventional"
                - samples: Dict mapping node → list of sample values
                - statistics: Dict mapping node → {mean, std, q05, q50, q95, min, max}
                - metadata: Query time, sample count, etc.

        Raises:
            DoWhySubprocessError: If subprocess fails
            ValueError: If input validation fails
        """
        # Validate inputs
        if not isinstance(graph, nx.DiGraph):
            raise ValueError("graph must be a NetworkX DiGraph")

        if not isinstance(traces, pd.DataFrame):
            raise ValueError("traces must be a pandas DataFrame")

        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("graph must be a Directed Acyclic Graph (DAG)")

        # Validate graph nodes match trace columns
        graph_nodes = set(graph.nodes())
        trace_columns = set(traces.columns)

        if graph_nodes != trace_columns:
            missing_in_traces = graph_nodes - trace_columns
            missing_in_graph = trace_columns - graph_nodes
            raise ValueError(
                f"Graph nodes and trace columns do not match.\n"
                f"  Missing in traces: {missing_in_traces}\n"
                f"  Missing in graph: {missing_in_graph}"
            )

        # Use query_fitted_scm.py script
        query_script = self.project_root / "scripts" / "dowhy" / "query_fitted_scm.py"
        if not query_script.exists():
            raise FileNotFoundError(f"Query script not found: {query_script}")

        # Prepare input
        input_data = {
            "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
            "traces": {col: traces[col].tolist() for col in traces.columns},
            "intervention": {
                "type": "interventional",
                "interventions": interventions,
                "query_nodes": query_nodes,
                "num_samples": num_samples,
            },
            "config": {"quality": quality},
        }

        # Run subprocess
        try:
            result = subprocess.run(
                [str(self.python_path), str(query_script)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise DoWhySubprocessError(
                f"DoWhy query subprocess timed out after {self.timeout}s"
            ) from e
        except Exception as e:
            raise DoWhySubprocessError(f"Failed to run DoWhy query subprocess: {e}") from e

        # Parse output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise DoWhySubprocessError(
                f"Failed to parse DoWhy query output as JSON.\n"
                f"stdout: {result.stdout[:500]}\n"
                f"stderr: {result.stderr[:500]}"
            ) from e

        # Check for errors
        if output.get("status") == "error":
            error_msg = output.get("error", "Unknown error")
            traceback = output.get("traceback", "")
            raise DoWhySubprocessError(
                f"DoWhy query subprocess failed: {error_msg}\nTraceback:\n{traceback}"
            )

        return output

    def check_availability(self) -> bool:
        """
        Check if DoWhy subprocess is available and working.

        Returns:
            True if subprocess can be called successfully
        """
        try:
            # Try to import dowhy
            result = subprocess.run(
                [str(self.python_path), "-c", "import dowhy; print(dowhy.__version__)"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"DoWhy available: version {version}")
                return True
            else:
                print(f"DoWhy import failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"DoWhy check failed: {e}")
            return False


# Convenience function for one-shot usage
def fit_scm(graph: nx.DiGraph, traces: pd.DataFrame, **kwargs) -> dict[str, Any]:
    """
    Convenience function for fitting SCM.

    Args:
        graph: Causal graph
        traces: Execution traces
        **kwargs: Additional arguments for DoWhyClient.fit_scm()

    Returns:
        Fitted SCM result dict
    """
    client = DoWhyClient()
    return client.fit_scm(graph, traces, **kwargs)


if __name__ == "__main__":
    # Quick test
    print("Testing DoWhy subprocess client...")

    client = DoWhyClient()

    if client.check_availability():
        print("✅ DoWhy subprocess is available")
    else:
        print("❌ DoWhy subprocess is NOT available")
        print("   Run: uv venv --python 3.11 .venv-dowhy")
        print("   Then: .venv-dowhy/bin/pip install dowhy pandas numpy scikit-learn")
