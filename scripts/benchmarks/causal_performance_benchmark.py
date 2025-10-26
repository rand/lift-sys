#!/usr/bin/env python3
"""Performance Benchmark for Causal Analysis (DoWhy STEP-15).

Tests causal analysis performance with synthetic codebases of varying sizes.

Acceptance Criteria:
- <30s for 100 files in static mode
- Linear scaling with number of files
- Memory usage < 1GB for 100 files
- Detailed timing breakdown (graph extraction, SCM fitting, etc.)

Usage:
    python scripts/benchmarks/causal_performance_benchmark.py
    python scripts/benchmarks/causal_performance_benchmark.py --files 50 --runs 3
"""

import argparse
import tempfile
import time
from pathlib import Path

import pandas as pd
from git import Repo

from lift_sys.reverse_mode import LifterConfig, SpecificationLifter


def create_synthetic_module(file_id: int, num_functions: int = 5) -> str:
    """Generate synthetic Python module for benchmarking.

    Args:
        file_id: Unique identifier for this file
        num_functions: Number of functions per file

    Returns:
        Python source code string
    """
    code_lines = [
        f'"""Synthetic module {file_id} for benchmarking."""',
        "",
        f"MODULE_ID = {file_id}",
        "",
    ]

    for func_id in range(num_functions):
        func_name = f"func_{file_id}_{func_id}"
        code_lines.extend(
            [
                f"def {func_name}(x, y=10):",
                f'    """Function {func_id} in module {file_id}."""',
                f"    result = x * {func_id + 1} + y",
                "    if result > 100:",
                "        result = result // 2",
                "    return result",
                "",
            ]
        )

    return "\n".join(code_lines)


def create_synthetic_codebase(tmpdir: Path, num_files: int) -> Repo:
    """Create synthetic codebase for benchmarking.

    Args:
        tmpdir: Temporary directory path
        num_files: Number of Python files to create

    Returns:
        Git Repo object
    """
    repo_path = tmpdir / "benchmark_repo"
    repo_path.mkdir()

    # Initialize git repo
    repo = Repo.init(repo_path)

    # Configure git user
    with repo.config_writer() as config:
        config.set_value("user", "name", "Benchmark")
        config.set_value("user", "email", "benchmark@test.com")

    # Create files
    for i in range(num_files):
        file_path = repo_path / f"module_{i}.py"
        code = create_synthetic_module(i, num_functions=5)
        file_path.write_text(code)

    # Commit
    repo.index.add([f"module_{i}.py" for i in range(num_files)])
    repo.index.commit(f"Add {num_files} synthetic modules")

    return repo


def benchmark_causal_analysis(num_files: int, runs: int = 1, enable_causal: bool = True) -> dict:
    """Benchmark causal analysis performance.

    Args:
        num_files: Number of files in synthetic codebase
        runs: Number of runs to average
        enable_causal: Whether to enable causal analysis

    Returns:
        Dict with timing results
    """
    results = []

    for run in range(runs):
        print(f"  Run {run + 1}/{runs}...")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create synthetic codebase
            print(f"    Creating {num_files} file codebase...")
            start = time.time()
            repo = create_synthetic_codebase(tmppath, num_files)
            codebase_creation_time = time.time() - start

            # Configure lifter
            config = LifterConfig(
                run_codeql=False,  # Disable to isolate causal performance
                run_daikon=False,
                run_stack_graphs=False,
                run_causal=enable_causal,
                causal_mode="static",  # Static mode for speed
            )

            lifter = SpecificationLifter(config, repo=repo)

            # Benchmark lift_all
            print(f"    Running lift_all (causal={enable_causal})...")
            start = time.time()
            irs = lifter.lift_all()
            total_time = time.time() - start

            # Calculate per-file stats
            per_file_time = total_time / num_files if num_files > 0 else 0

            results.append(
                {
                    "run": run + 1,
                    "num_files": num_files,
                    "causal_enabled": enable_causal,
                    "total_time_s": total_time,
                    "per_file_time_ms": per_file_time * 1000,
                    "codebase_creation_time_s": codebase_creation_time,
                    "num_irs": len(irs),
                }
            )

            print(f"    Completed: {total_time:.2f}s total, {per_file_time * 1000:.1f}ms per file")

    # Average across runs
    avg_results = {
        "num_files": num_files,
        "runs": runs,
        "causal_enabled": enable_causal,
        "avg_total_time_s": sum(r["total_time_s"] for r in results) / runs,
        "avg_per_file_time_ms": sum(r["per_file_time_ms"] for r in results) / runs,
        "min_total_time_s": min(r["total_time_s"] for r in results),
        "max_total_time_s": max(r["total_time_s"] for r in results),
        "all_runs": results,
    }

    return avg_results


def run_benchmark_suite(args):
    """Run complete benchmark suite.

    Args:
        args: Command line arguments
    """
    print("=" * 80)
    print("CAUSAL ANALYSIS PERFORMANCE BENCHMARK (STEP-15)")
    print("=" * 80)
    print()

    file_counts = args.files or [10, 25, 50, 100]
    runs_per_test = args.runs

    all_results = []

    for num_files in file_counts:
        print(f"\n{'=' * 80}")
        print(f"Benchmarking {num_files} files")
        print(f"{'=' * 80}\n")

        # Benchmark WITHOUT causal
        print("Testing WITHOUT causal analysis...")
        results_no_causal = benchmark_causal_analysis(
            num_files, runs=runs_per_test, enable_causal=False
        )
        all_results.append(results_no_causal)

        # Benchmark WITH causal
        print("\nTesting WITH causal analysis (static mode)...")
        results_with_causal = benchmark_causal_analysis(
            num_files, runs=runs_per_test, enable_causal=True
        )
        all_results.append(results_with_causal)

        # Calculate overhead
        overhead_s = results_with_causal["avg_total_time_s"] - results_no_causal["avg_total_time_s"]
        overhead_pct = (
            (overhead_s / results_no_causal["avg_total_time_s"]) * 100
            if results_no_causal["avg_total_time_s"] > 0
            else 0
        )

        print(f"\n{'-' * 80}")
        print(f"SUMMARY: {num_files} files")
        print(f"{'-' * 80}")
        print(
            f"  WITHOUT causal: {results_no_causal['avg_total_time_s']:.2f}s "
            f"({results_no_causal['avg_per_file_time_ms']:.1f}ms/file)"
        )
        print(
            f"  WITH causal:    {results_with_causal['avg_total_time_s']:.2f}s "
            f"({results_with_causal['avg_per_file_time_ms']:.1f}ms/file)"
        )
        print(f"  Overhead:       {overhead_s:.2f}s ({overhead_pct:.1f}%)")
        print()

        # Check acceptance criteria
        if num_files == 100:
            passed = results_with_causal["avg_total_time_s"] < 30.0
            status = "PASS ✅" if passed else "FAIL ❌"
            print(f"  ACCEPTANCE CRITERIA (<30s for 100 files): {status}")
            print()

    # Generate summary table
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print()

    df = pd.DataFrame(all_results)
    print(df[["num_files", "causal_enabled", "avg_total_time_s", "avg_per_file_time_ms"]])
    print()

    # Save results
    if args.output:
        output_path = Path(args.output)
        df.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Benchmark causal analysis performance (STEP-15)")
    parser.add_argument(
        "--files",
        type=int,
        nargs="+",
        help="File counts to test (default: [10, 25, 50, 100])",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per test (default: 1)")
    parser.add_argument(
        "--output",
        type=str,
        help="Output CSV file for results (default: no file)",
    )

    args = parser.parse_args()

    run_benchmark_suite(args)


if __name__ == "__main__":
    main()
