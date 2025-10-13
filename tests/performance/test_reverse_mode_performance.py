"""Performance tests for reverse mode analysis.

Run with: pytest tests/performance/test_reverse_mode_performance.py -v -s
Profile memory: pytest tests/performance/test_reverse_mode_performance.py -v -s --memray
"""

import time
import tracemalloc
from textwrap import dedent

import pytest

from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter


class TestReverseModePerformance:
    """Performance tests for reverse mode lifter."""

    @pytest.fixture
    def synthetic_repo(self, tmp_path):
        """Create a synthetic repository with many Python files."""
        repo_dir = tmp_path / "synthetic_repo"
        repo_dir.mkdir()

        # Create a variety of Python files with realistic code
        templates = [
            # Simple function
            dedent(
                """
            def process_data_{idx}(data):
                \"\"\"Process data for module {idx}.\"\"\"
                result = []
                for item in data:
                    if item is not None:
                        result.append(item * 2)
                return result
            """
            ),
            # Class with methods
            dedent(
                """
            class Handler_{idx}:
                \"\"\"Handler for module {idx}.\"\"\"

                def __init__(self, config):
                    self.config = config
                    self.state = {{}}

                def process(self, input_data):
                    \"\"\"Process input data.\"\"\"
                    if input_data is None:
                        raise ValueError("Input cannot be None")
                    return self._transform(input_data)

                def _transform(self, data):
                    \"\"\"Transform data internally.\"\"\"
                    return {{k: v * 2 for k, v in data.items()}}
            """
            ),
            # API endpoint style
            dedent(
                """
            from typing import Dict, List, Optional

            def handle_request_{idx}(request_data: Dict) -> Optional[List]:
                \"\"\"Handle request for endpoint {idx}.\"\"\"
                if not request_data:
                    return None

                results = []
                for key, value in request_data.items():
                    if isinstance(value, (int, float)):
                        results.append({{key: value ** 2}})

                return results if results else None
            """
            ),
        ]

        return repo_dir, templates

    def generate_files(self, repo_dir, templates, num_files):
        """Generate synthetic Python files and initialize git repo."""
        import subprocess

        # Initialize git repo if not already done
        if not (repo_dir / ".git").exists():
            subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )

        for i in range(num_files):
            # Distribute files across multiple directories
            subdir = repo_dir / f"module_{i // 10}"
            subdir.mkdir(exist_ok=True)

            file_path = subdir / f"handler_{i}.py"
            template = templates[i % len(templates)]
            content = template.format(idx=i)
            file_path.write_text(content)

        return repo_dir

    def test_baseline_small_repo(self, synthetic_repo):
        """Baseline: Analyze 10 files with all analyzers disabled.

        Target: < 5 seconds
        """
        repo_dir, templates = synthetic_repo
        self.generate_files(repo_dir, templates, num_files=10)

        config = LifterConfig(
            run_codeql=False, run_daikon=False, run_stack_graphs=False, max_files=10
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        start_time = time.time()
        irs = lifter.lift_all()
        elapsed = time.time() - start_time

        print(f"\n✓ Analyzed {len(irs)} files in {elapsed:.2f}s")
        print(f"  Average: {elapsed / len(irs):.2f}s per file")

        assert len(irs) <= 10
        assert elapsed < 5.0, f"Analysis took {elapsed:.2f}s, expected < 5s"

    def test_medium_repo_performance(self, synthetic_repo):
        """Medium: Analyze 50 files with static analysis only.

        Target: < 30 seconds
        """
        repo_dir, templates = synthetic_repo
        self.generate_files(repo_dir, templates, num_files=50)

        config = LifterConfig(
            run_codeql=False,  # CodeQL can be slow
            run_daikon=False,  # Daikon requires running code
            run_stack_graphs=False,
            max_files=50,
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        start_time = time.time()
        irs = lifter.lift_all()
        elapsed = time.time() - start_time

        print(f"\n✓ Analyzed {len(irs)} files in {elapsed:.2f}s")
        print(f"  Average: {elapsed / len(irs):.3f}s per file")

        assert len(irs) <= 50
        assert elapsed < 30.0, f"Analysis took {elapsed:.2f}s, expected < 30s"

    def test_large_repo_with_limit(self, synthetic_repo):
        """Large: Generate 200 files but analyze only first 100.

        Target: < 60 seconds with max_files=100
        """
        repo_dir, templates = synthetic_repo
        self.generate_files(repo_dir, templates, num_files=200)

        config = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            max_files=100,
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        files = lifter.discover_python_files()
        print(f"\nDiscovered {len(files)} files, will analyze {config.max_files}")

        start_time = time.time()
        irs = lifter.lift_all()
        elapsed = time.time() - start_time

        print(f"✓ Analyzed {len(irs)} files in {elapsed:.2f}s")
        print(f"  Average: {elapsed / len(irs):.3f}s per file")

        assert len(irs) == 100, f"Expected 100 files, got {len(irs)}"
        assert elapsed < 60.0, f"Analysis took {elapsed:.2f}s, expected < 60s"

    def test_memory_usage_scaling(self, synthetic_repo):
        """Memory: Test memory usage with increasing file counts.

        Ensure memory usage scales linearly, not quadratically.
        """
        repo_dir, templates = synthetic_repo
        results = []

        for num_files in [10, 25, 50]:
            # Clean and regenerate repo for each test
            import shutil

            for item in repo_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            self.generate_files(repo_dir, templates, num_files)

            config = LifterConfig(
                run_codeql=False,
                run_daikon=False,
                run_stack_graphs=False,
                max_files=num_files,
            )

            lifter = SpecificationLifter(config)
            lifter.load_repository(str(repo_dir))

            # Measure memory usage
            tracemalloc.start()
            start_time = time.time()

            irs = lifter.lift_all()

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            elapsed = time.time() - start_time

            peak_mb = peak / (1024 * 1024)
            results.append(
                {
                    "files": num_files,
                    "peak_memory_mb": peak_mb,
                    "time_seconds": elapsed,
                    "irs_count": len(irs),
                }
            )

            print(f"\n{num_files} files:")
            print(f"  Peak memory: {peak_mb:.2f} MB")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  IRs: {len(irs)}")

        # Check that memory usage is reasonable
        print("\n=== Memory Scaling ===")
        for result in results:
            print(
                f"{result['files']} files: {result['peak_memory_mb']:.2f} MB "
                f"({result['time_seconds']:.2f}s)"
            )

        # Memory should scale roughly linearly
        # 50 files should use less than 6x the memory of 10 files
        if len(results) >= 2:
            ratio = results[-1]["peak_memory_mb"] / results[0]["peak_memory_mb"]
            file_ratio = results[-1]["files"] / results[0]["files"]
            print(f"\nMemory scaling: {ratio:.2f}x for {file_ratio:.1f}x files")
            assert ratio < file_ratio * 1.5, (
                f"Memory scaling too high: {ratio:.2f}x for {file_ratio}x files"
            )

    def test_file_size_limit_performance(self, tmp_path):
        """File size: Ensure large files are skipped efficiently."""
        import subprocess

        repo_dir = tmp_path / "large_file_repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        # Create one huge file and several normal files
        huge_content = "# " + "x" * (15 * 1024 * 1024)  # 15MB
        (repo_dir / "huge.py").write_text(huge_content)

        for i in range(10):
            (repo_dir / f"normal_{i}.py").write_text(f"def func_{i}(): return {i}")

        config = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            max_file_size_mb=10.0,  # Skip files > 10MB
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        start_time = time.time()
        files = lifter.discover_python_files()
        elapsed = time.time() - start_time

        print(f"\nDiscovered {len(files)} files in {elapsed:.3f}s")
        print("Skipped large files efficiently")

        # Should only find the 10 normal files, not the huge one
        assert len(files) == 10
        assert elapsed < 1.0, f"File discovery took {elapsed:.3f}s, expected < 1s"

    def test_progress_callback_overhead(self, synthetic_repo):
        """Progress: Measure overhead of progress callbacks."""
        repo_dir, templates = synthetic_repo
        self.generate_files(repo_dir, templates, num_files=20)

        config = LifterConfig(run_codeql=False, run_daikon=False, run_stack_graphs=False)

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        # Test without callback
        start_time = time.time()
        irs_no_callback = lifter.lift_all()
        time_no_callback = time.time() - start_time

        # Test with callback
        lifter2 = SpecificationLifter(config)
        lifter2.load_repository(str(repo_dir))

        callback_count = [0]

        def progress_callback(file_path, current, total):
            callback_count[0] += 1

        start_time = time.time()
        irs_with_callback = lifter2.lift_all(progress_callback=progress_callback)
        time_with_callback = time.time() - start_time

        print(f"\nWithout callback: {time_no_callback:.2f}s")
        print(f"With callback: {time_with_callback:.2f}s ({callback_count[0]} calls)")

        overhead_pct = ((time_with_callback - time_no_callback) / time_no_callback) * 100
        print(f"Overhead: {overhead_pct:.1f}%")

        # Callback overhead should be minimal (< 20%)
        assert overhead_pct < 20.0, f"Callback overhead too high: {overhead_pct:.1f}%"
        assert len(irs_with_callback) == len(irs_no_callback)

    def test_time_limit_enforcement(self, synthetic_repo):
        """Time limit: Ensure total time limit is enforced efficiently."""
        repo_dir, templates = synthetic_repo
        self.generate_files(repo_dir, templates, num_files=100)

        config = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            max_total_time_seconds=5.0,  # 5 second limit
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        from lift_sys.reverse_mode.lifter import TotalTimeLimitExceededError

        start_time = time.time()
        try:
            irs = lifter.lift_all()
            elapsed = time.time() - start_time

            # If we completed within the limit, that's fine
            print(f"\nCompleted {len(irs)} files in {elapsed:.2f}s (under limit)")
            assert elapsed <= 5.5  # Allow small margin

        except TotalTimeLimitExceededError as e:
            elapsed = time.time() - start_time

            print(f"\n✓ Time limit enforced: {e.elapsed:.2f}s")
            print(f"  Analyzed {e.files_analyzed}/{e.total_files} files")

            # Check that we stopped reasonably close to the limit
            # (not way over, which would indicate poor enforcement)
            assert elapsed < 7.0, f"Stopped too late: {elapsed:.2f}s for 5s limit"
            assert e.files_analyzed > 0, "Should have analyzed at least some files"


@pytest.mark.skip(reason="Stress test - run manually with: pytest -k test_stress_1000")
class TestStressTests:
    """Stress tests for very large repositories.

    These are skipped by default. Run manually with:
    pytest tests/performance/test_reverse_mode_performance.py::TestStressTests -v -s
    """

    def test_stress_1000_files(self, tmp_path):
        """Stress: Analyze 1000 files with max_files=1000.

        This is a manual stress test to evaluate behavior on large repos.
        """
        import subprocess

        repo_dir = tmp_path / "stress_repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        print("\nGenerating 1000 synthetic Python files...")
        template = dedent(
            """
        def process_{idx}(data):
            result = data * 2
            return result
        """
        )

        for i in range(1000):
            subdir = repo_dir / f"module_{i // 100}"
            subdir.mkdir(exist_ok=True)
            file_path = subdir / f"file_{i}.py"
            file_path.write_text(template.format(idx=i))

        config = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            max_files=1000,
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(repo_dir))

        print("Starting analysis of 1000 files...")
        tracemalloc.start()
        start_time = time.time()

        progress_updates = []

        def progress_callback(file_path, current, total):
            if current % 100 == 0:
                elapsed = time.time() - start_time
                current_mem, peak_mem = tracemalloc.get_traced_memory()
                progress_updates.append(
                    {
                        "files": current,
                        "elapsed": elapsed,
                        "peak_memory_mb": peak_mem / (1024 * 1024),
                    }
                )
                print(
                    f"  [{current}/{total}] {elapsed:.1f}s, {peak_mem / (1024 * 1024):.1f}MB peak"
                )

        irs = lifter.lift_all(progress_callback=progress_callback)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed = time.time() - start_time

        print("\n=== Stress Test Results ===")
        print(f"Files analyzed: {len(irs)}")
        print(f"Total time: {elapsed:.2f}s ({elapsed / len(irs):.3f}s per file)")
        print(f"Peak memory: {peak / (1024 * 1024):.2f}MB")
        print(f"Final memory: {current / (1024 * 1024):.2f}MB")

        # Check performance targets
        assert len(irs) == 1000
        assert elapsed < 600, f"Should complete 1000 files in < 10 minutes, took {elapsed:.1f}s"
        assert peak / (1024 * 1024) < 500, f"Memory usage too high: {peak / (1024 * 1024):.1f}MB"
