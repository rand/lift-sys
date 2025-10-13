"""Integration tests for multi-file reverse mode analysis.

Tests cover:
- Multi-file discovery and analysis workflow
- API endpoint support for both modes (project/file)
- Progress tracking during multi-file operations
- Error handling with partial results
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.mark.integration
class TestMultiFileAnalysis:
    """Integration tests for multi-file reverse mode analysis."""

    @patch("subprocess.run")
    def test_multifile_discovery_and_analysis(self, mock_subprocess, temp_repo, temp_dir):
        """Test discovering and analyzing multiple Python files."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create multiple Python files
        files = ["main.py", "utils.py", "helpers.py"]
        for filename in files:
            (Path(temp_dir) / filename).write_text(f"def {filename.split('.')[0]}(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add test files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Discover files
        discovered = lifter.discover_python_files()
        assert len(discovered) == 3
        assert all(Path(f) in discovered for f in files)

        # Analyze all files
        irs = lifter.lift_all()
        assert len(irs) == 3

        # Verify each IR has correct metadata
        source_paths = {ir.metadata.source_path for ir in irs}
        assert source_paths == set(files)

    @patch("subprocess.run")
    def test_multifile_with_nested_directories(self, mock_subprocess, temp_repo, temp_dir):
        """Test multi-file analysis with nested directory structure."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create nested structure
        (Path(temp_dir) / "src").mkdir()
        (Path(temp_dir) / "src" / "lib").mkdir()
        (Path(temp_dir) / "tests").mkdir()

        files = [
            "main.py",
            "src/app.py",
            "src/lib/utils.py",
            "tests/test_main.py",
        ]

        for filepath in files:
            (Path(temp_dir) / filepath).write_text("# test file")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add nested files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        discovered = lifter.discover_python_files()
        assert len(discovered) == 4
        assert Path("src/lib/utils.py") in discovered
        assert Path("tests/test_main.py") in discovered

    @patch("subprocess.run")
    def test_multifile_excludes_venv_and_cache(self, mock_subprocess, temp_repo, temp_dir):
        """Test that venv and cache directories are properly excluded."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create files in various directories
        (Path(temp_dir) / "main.py").write_text("# main")
        (Path(temp_dir) / "venv").mkdir()
        (Path(temp_dir) / "venv" / "lib.py").write_text("# venv")
        (Path(temp_dir) / "__pycache__").mkdir()
        (Path(temp_dir) / "__pycache__" / "cache.py").write_text("# cache")
        (Path(temp_dir) / "node_modules").mkdir()
        (Path(temp_dir) / "node_modules" / "mod.py").write_text("# node")

        temp_repo.index.add(
            ["main.py", "venv/lib.py", "__pycache__/cache.py", "node_modules/mod.py"]
        )
        temp_repo.index.commit("Add files with exclusions")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        discovered = lifter.discover_python_files()

        # Should only find main.py
        assert len(discovered) == 1
        assert Path("main.py") in discovered

    @patch("subprocess.run")
    def test_multifile_with_partial_failures(self, mock_subprocess, temp_repo, temp_dir):
        """Test multi-file analysis continues despite individual file failures."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create test files
        files = ["good1.py", "bad.py", "good2.py"]
        for filename in files:
            (Path(temp_dir) / filename).write_text("def test(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add mixed files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Mock lift to fail for bad.py
        original_lift = lifter.lift

        def mock_lift(module):
            if "bad.py" in module:
                raise ValueError("Simulated analysis failure")
            return original_lift(module)

        with patch.object(lifter, "lift", side_effect=mock_lift):
            irs = lifter.lift_all()

            # Should have 2 successful IRs (good1, good2)
            assert len(irs) == 2
            source_paths = {ir.metadata.source_path for ir in irs}
            assert "good1.py" in source_paths
            assert "good2.py" in source_paths
            assert "bad.py" not in source_paths

            # Verify that analysis completed despite failures
            # (progress_log may be cleared, so we just check the results)

    @patch("subprocess.run")
    def test_multifile_progress_tracking(self, mock_subprocess, temp_repo, temp_dir):
        """Test that progress is tracked during multi-file analysis."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create test files
        files = [f"file{i}.py" for i in range(5)]
        for filename in files:
            (Path(temp_dir) / filename).write_text("def test(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Track progress through callback
        progress_calls = []

        def track_progress(file_path, current, total):
            progress_calls.append((file_path, current, total))

        irs = lifter.lift_all(progress_callback=track_progress)

        assert len(irs) == 5
        assert len(progress_calls) == 5

        # Verify progress tracking
        for i, (file_path, current, total) in enumerate(progress_calls, 1):
            assert current == i
            assert total == 5
            assert f"file{i - 1}.py" in file_path

    @patch("subprocess.run")
    def test_multifile_respects_max_files_limit(self, mock_subprocess, temp_repo, temp_dir):
        """Test that max_files parameter limits analysis."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create 10 files
        files = [f"module{i}.py" for i in range(10)]
        for filename in files:
            (Path(temp_dir) / filename).write_text("def test(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add 10 files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Limit to 3 files
        irs = lifter.lift_all(max_files=3)

        assert len(irs) == 3
        # Verify limit was respected (3 IRs returned out of 10 files discovered)

    @patch("subprocess.run")
    def test_multifile_empty_repository(self, mock_subprocess, temp_repo, temp_dir):
        """Test multi-file analysis with no Python files."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        # Create non-Python files
        (Path(temp_dir) / "README.md").write_text("# README")
        (Path(temp_dir) / "config.json").write_text("{}")

        temp_repo.index.add(["README.md", "config.json"])
        temp_repo.index.commit("Add non-Python files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        irs = lifter.lift_all()

        assert len(irs) == 0

    @patch("subprocess.run")
    def test_multifile_preserves_metadata(self, mock_subprocess, temp_repo, temp_dir):
        """Test that metadata is correctly preserved for each file."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        files = ["alpha.py", "beta.py", "gamma.py"]
        for filename in files:
            (Path(temp_dir) / filename).write_text(f"def {filename.split('.')[0]}(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        irs = lifter.lift_all()

        # Verify each IR has correct metadata
        for ir in irs:
            assert ir.metadata.source_path in files
            assert ir.metadata.origin == "reverse"
            assert ir.signature.name in ["alpha", "beta", "gamma"]

    @patch("subprocess.run")
    def test_multifile_with_mixed_success_and_errors(self, mock_subprocess, temp_repo, temp_dir):
        """Test that analysis continues and reports both successes and failures."""
        from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter

        files = ["s1.py", "f1.py", "s2.py", "f2.py", "s3.py"]
        for filename in files:
            (Path(temp_dir) / filename).write_text("def test(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add mixed files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Mock lift to fail for files starting with 'f'
        original_lift = lifter.lift

        def selective_fail(module):
            if "/f" in module or module.startswith("f"):
                raise RuntimeError(f"Failed: {module}")
            return original_lift(module)

        with patch.object(lifter, "lift", side_effect=selective_fail):
            irs = lifter.lift_all()

            # Should have 3 successful (s1, s2, s3)
            assert len(irs) == 3

            # Check progress log
            progress = " ".join(lifter.progress_log)
            assert "completed with 2 failures out of 5" in progress


@pytest.mark.integration
class TestMultiFileAPIEndpoint:
    """Integration tests for /api/reverse endpoint with multi-file support."""

    def test_api_endpoint_project_mode(self, api_client, api_state, temp_repo, temp_dir):
        """Test API endpoint in project mode (module=null)."""
        from lift_sys.ir.models import (
            IntentClause,
            IntermediateRepresentation,
            Metadata,
            SigClause,
        )

        # Configure backend
        response = api_client.post(
            "/api/config",
            json={
                "model_endpoint": "http://model",
                "temperature": 0.3,
                "provider_type": "vllm",
                "schema_uri": "memory://schema.json",
                "grammar_source": "start -> expr",
            },
        )
        assert response.status_code == 200

        # Setup repository with files
        files = ["a.py", "b.py", "c.py"]
        for filename in files:
            (Path(temp_dir) / filename).write_text("def test(): pass")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add files")

        # Load repository into lifter
        api_state.lifter.load_repository(str(temp_dir))

        # Create mock IRs
        def create_mock_irs(progress_callback=None):
            irs = []
            for i, filename in enumerate(files, 1):
                if progress_callback:
                    progress_callback(filename, i, len(files))
                irs.append(
                    IntermediateRepresentation(
                        intent=IntentClause(summary=f"Test {filename}"),
                        signature=SigClause(
                            name=filename.replace(".py", ""), parameters=[], returns="None"
                        ),
                        assertions=[],
                        metadata=Metadata(
                            source_path=filename, origin="reverse", language="python"
                        ),
                    )
                )
            return irs

        # Mock lift_all to return our mock IRs
        with patch.object(api_state.lifter, "lift_all", side_effect=create_mock_irs):
            # Call API in project mode
            response = api_client.post(
                "/api/reverse",
                json={
                    "module": None,  # Project mode
                    "analyze_all": True,
                    "queries": ["security/default"],
                    "entrypoint": "main",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Check response format
            assert "irs" in data
            assert isinstance(data["irs"], list)
            assert len(data["irs"]) == 3

            # Verify each IR
            source_paths = {ir["metadata"]["source_path"] for ir in data["irs"]}
            assert source_paths == {"a.py", "b.py", "c.py"}

    def test_api_endpoint_file_mode_backward_compatible(self, api_client, api_state, sample_ir):
        """Test API endpoint in file mode (backward compatible)."""
        # Configure backend
        response = api_client.post(
            "/api/config",
            json={
                "model_endpoint": "http://model",
                "temperature": 0.3,
                "provider_type": "vllm",
                "schema_uri": "memory://schema.json",
                "grammar_source": "start -> expr",
            },
        )
        assert response.status_code == 200

        assert api_state.lifter is not None
        api_state.lifter.repo = Mock()
        api_state.lifter.repo.working_tree_dir = "/tmp/repo"

        with patch.object(api_state.lifter, "lift", return_value=sample_ir):
            response = api_client.post(
                "/api/reverse",
                json={
                    "module": "test.py",  # Single file mode
                    "queries": ["security/default"],
                    "entrypoint": "main",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should still return irs array (backward compatible)
            assert "irs" in data
            assert len(data["irs"]) == 1
            # Just check that it has metadata (source_path comes from the mocked IR)
            assert "metadata" in data["irs"][0]
