#!/usr/bin/env python3
"""Test causal analysis on real codebases (DoWhy STEP-17).

Tests causal analysis on real Python codebases to validate production readiness.

Acceptance Criteria:
- Successfully analyze 3 real codebases (10-100 files each)
- No crashes or errors during analysis
- Reasonable graph sizes (nodes, edges within expected bounds)
- Performance within acceptable limits

Usage:
    python scripts/causal/test_real_codebases.py
"""

import argparse
import ast
import json
import time
from pathlib import Path

import networkx as nx

from lift_sys.causal.graph_builder import CausalGraphBuilder


def analyze_python_file(file_path: Path, builder: CausalGraphBuilder) -> dict | None:
    """Analyze a single Python file.

    Args:
        file_path: Path to Python file
        builder: CausalGraphBuilder instance

    Returns:
        Dict with analysis results, or None if file can't be analyzed
    """
    try:
        code = file_path.read_text()
        ast_tree = ast.parse(code)
        call_graph = nx.DiGraph()  # Empty call graph for single-file analysis

        start = time.time()
        graph = builder.build(ast_tree, call_graph)
        elapsed = time.time() - start

        return {
            "file": str(file_path),
            "success": True,
            "num_nodes": graph.number_of_nodes(),
            "num_edges": graph.number_of_edges(),
            "time_ms": elapsed * 1000,
            "error": None,
        }
    except SyntaxError as e:
        return {
            "file": str(file_path),
            "success": False,
            "error": f"SyntaxError: {e}",
        }
    except Exception as e:
        return {
            "file": str(file_path),
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


def analyze_codebase(codebase_path: Path, max_files: int = 100) -> dict:
    """Analyze a codebase directory.

    Args:
        codebase_path: Path to codebase root
        max_files: Maximum number of files to analyze

    Returns:
        Dict with aggregate results
    """
    print(f"\nAnalyzing codebase: {codebase_path}")
    print("=" * 80)

    builder = CausalGraphBuilder()
    python_files = list(codebase_path.rglob("*.py"))

    # Filter out test files and __pycache__
    python_files = [
        f
        for f in python_files
        if "__pycache__" not in str(f) and "/.venv/" not in str(f) and "/venv/" not in str(f)
    ]

    # Limit to max_files
    if len(python_files) > max_files:
        python_files = python_files[:max_files]
        print(f"  Limited to first {max_files} files")

    print(f"  Found {len(python_files)} Python files")

    results = []
    total_nodes = 0
    total_edges = 0
    total_time = 0.0
    successes = 0
    failures = 0

    for i, file_path in enumerate(python_files, 1):
        result = analyze_python_file(file_path, builder)
        results.append(result)

        if result and result["success"]:
            successes += 1
            total_nodes += result["num_nodes"]
            total_edges += result["num_edges"]
            total_time += result["time_ms"]
        else:
            failures += 1

        if i % 10 == 0:
            print(f"  Processed {i}/{len(python_files)} files...")

    avg_time = total_time / successes if successes > 0 else 0
    avg_nodes = total_nodes / successes if successes > 0 else 0
    avg_edges = total_edges / successes if successes > 0 else 0

    print("\n  Results:")
    print(
        f"    Success: {successes}/{len(python_files)} ({successes / len(python_files) * 100:.1f}%)"
    )
    print(f"    Failures: {failures}")
    print(f"    Total nodes: {total_nodes}")
    print(f"    Total edges: {total_edges}")
    print(f"    Avg time per file: {avg_time:.1f}ms")
    print(f"    Avg nodes per file: {avg_nodes:.1f}")
    print(f"    Avg edges per file: {avg_edges:.1f}")
    print()

    # Show sample failures if any
    if failures > 0:
        print("  Sample failures (first 5):")
        failure_results = [r for r in results if r and not r["success"]][:5]
        for r in failure_results:
            print(f"    {Path(r['file']).name}: {r['error']}")
        print()

    return {
        "codebase": str(codebase_path),
        "num_files": len(python_files),
        "successes": successes,
        "failures": failures,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "total_time_ms": total_time,
        "avg_time_ms": avg_time,
        "avg_nodes": avg_nodes,
        "avg_edges": avg_edges,
        "results": results,
    }


def main():
    """Run STEP-17 validation."""
    parser = argparse.ArgumentParser(description="Test causal analysis on real codebases (STEP-17)")
    parser.add_argument(
        "--codebases",
        nargs="+",
        help="Paths to codebases to analyze (default: lift-sys)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=100,
        help="Maximum files per codebase (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for results",
    )

    args = parser.parse_args()

    # Default to lift-sys codebase
    if not args.codebases:
        lift_sys_path = Path(__file__).parent.parent.parent / "lift_sys"
        args.codebases = [str(lift_sys_path)]

    print("=" * 80)
    print("CAUSAL ANALYSIS - REAL CODEBASE TESTING (STEP-17)")
    print("=" * 80)

    all_results = []
    total_successes = 0
    total_files = 0

    for codebase in args.codebases:
        codebase_path = Path(codebase)
        if not codebase_path.exists():
            print(f"\nERROR: Codebase path does not exist: {codebase_path}")
            continue

        result = analyze_codebase(codebase_path, max_files=args.max_files)
        all_results.append(result)
        total_successes += result["successes"]
        total_files += result["num_files"]

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Codebases analyzed: {len(all_results)}")
    print(f"  Total files: {total_files}")
    print(
        f"  Total successes: {total_successes}/{total_files} ({total_successes / total_files * 100:.1f}%)"
    )
    print()

    # Acceptance criteria
    all_success = all(r["failures"] == 0 for r in all_results)
    status = "PASS ✅" if all_success else "PARTIAL ⚠️"
    print(f"  No crashes/errors: {status}")
    print()

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(all_results, indent=2))
        print(f"Results saved to: {output_path}")
        print()


if __name__ == "__main__":
    main()
