"""Unit tests for multi-file analysis features in SpecificationLifter.

Tests cover:
- Python file discovery with exclusion patterns
- Multi-file lifting (lift_all)
- Error handling and partial results
- Progress tracking
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter


@pytest.mark.unit
class TestFileDiscovery:
    """Unit tests for discover_python_files method."""

    def test_discover_python_files_finds_all_files(self, temp_repo, temp_dir):
        """Test that discover_python_files finds all Python files."""
        # Create test Python files
        (Path(temp_dir) / "module1.py").write_text("# module 1")
        (Path(temp_dir) / "module2.py").write_text("# module 2")
        (Path(temp_dir) / "subdir").mkdir()
        (Path(temp_dir) / "subdir" / "module3.py").write_text("# module 3")

        temp_repo.index.add(["module1.py", "module2.py", "subdir/module3.py"])
        temp_repo.index.commit("Add test files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 3
        assert Path("module1.py") in files
        assert Path("module2.py") in files
        assert Path("subdir/module3.py") in files

    def test_discover_python_files_excludes_venv(self, temp_repo, temp_dir):
        """Test that venv directories are excluded."""
        # Create files in venv
        venv_dir = Path(temp_dir) / "venv"
        venv_dir.mkdir()
        (venv_dir / "lib.py").write_text("# venv lib")

        # Create file in main directory
        (Path(temp_dir) / "main.py").write_text("# main")

        temp_repo.index.add(["main.py", "venv/lib.py"])
        temp_repo.index.commit("Add files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 1
        assert Path("main.py") in files
        assert Path("venv/lib.py") not in files

    def test_discover_python_files_excludes_pycache(self, temp_repo, temp_dir):
        """Test that __pycache__ directories are excluded."""
        # Create __pycache__ directory
        cache_dir = Path(temp_dir) / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cache.py").write_text("# cache")

        # Create regular file
        (Path(temp_dir) / "app.py").write_text("# app")

        temp_repo.index.add(["app.py", "__pycache__/cache.py"])
        temp_repo.index.commit("Add files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 1
        assert Path("app.py") in files
        assert not any("__pycache__" in str(f) for f in files)

    def test_discover_python_files_excludes_node_modules(self, temp_repo, temp_dir):
        """Test that node_modules directories are excluded."""
        # Create node_modules (in case of mixed projects)
        node_dir = Path(temp_dir) / "node_modules"
        node_dir.mkdir()
        (node_dir / "script.py").write_text("# node script")

        # Create regular file
        (Path(temp_dir) / "server.py").write_text("# server")

        temp_repo.index.add(["server.py", "node_modules/script.py"])
        temp_repo.index.commit("Add files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 1
        assert Path("server.py") in files
        assert not any("node_modules" in str(f) for f in files)

    def test_discover_python_files_excludes_build_directories(self, temp_repo, temp_dir):
        """Test that build/dist directories are excluded."""
        # Create build and dist directories
        for dirname in ["build", "dist", ".eggs"]:
            dir_path = Path(temp_dir) / dirname
            dir_path.mkdir()
            (dir_path / "artifact.py").write_text("# artifact")

        # Create source file
        (Path(temp_dir) / "source.py").write_text("# source")

        temp_repo.index.add(
            ["source.py", "build/artifact.py", "dist/artifact.py", ".eggs/artifact.py"]
        )
        temp_repo.index.commit("Add files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 1
        assert Path("source.py") in files

    def test_discover_python_files_custom_exclusions(self, temp_repo, temp_dir):
        """Test custom exclusion patterns."""
        # Create various files
        (Path(temp_dir) / "keep.py").write_text("# keep")
        exclude_dir = Path(temp_dir) / "exclude_me"
        exclude_dir.mkdir()
        (exclude_dir / "skip.py").write_text("# skip")

        temp_repo.index.add(["keep.py", "exclude_me/skip.py"])
        temp_repo.index.commit("Add files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files(exclude_patterns=["exclude_me"])

        assert len(files) == 1
        assert Path("keep.py") in files
        assert not any("exclude_me" in str(f) for f in files)

    def test_discover_python_files_returns_sorted_paths(self, temp_repo, temp_dir):
        """Test that results are sorted."""
        # Create files in non-alphabetical order
        for name in ["z.py", "a.py", "m.py"]:
            (Path(temp_dir) / name).write_text(f"# {name}")

        temp_repo.index.add(["z.py", "a.py", "m.py"])
        temp_repo.index.commit("Add files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        # Should be sorted
        assert files == [Path("a.py"), Path("m.py"), Path("z.py")]

    def test_discover_python_files_raises_without_repo(self):
        """Test that method raises error when repo not loaded."""
        config = LifterConfig()
        lifter = SpecificationLifter(config)

        with pytest.raises(RuntimeError, match="Repository not loaded"):
            lifter.discover_python_files()

    def test_discover_python_files_nested_directories(self, temp_repo, temp_dir):
        """Test discovery in deeply nested directories."""
        # Create nested structure
        nested = Path(temp_dir) / "src" / "lib" / "utils"
        nested.mkdir(parents=True)
        (nested / "helper.py").write_text("# helper")
        (Path(temp_dir) / "main.py").write_text("# main")

        temp_repo.index.add(["main.py", "src/lib/utils/helper.py"])
        temp_repo.index.commit("Add nested files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 2
        assert Path("main.py") in files
        assert Path("src/lib/utils/helper.py") in files

    def test_discover_python_files_empty_repository(self, temp_repo, temp_dir):
        """Test discovery in repository with no Python files."""
        # Create non-Python files
        (Path(temp_dir) / "README.md").write_text("# README")
        (Path(temp_dir) / "config.json").write_text("{}")

        temp_repo.index.add(["README.md", "config.json"])
        temp_repo.index.commit("Add non-Python files")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        files = lifter.discover_python_files()

        assert len(files) == 0


@pytest.mark.unit
class TestMultiFileLift:
    """Unit tests for lift_all method."""

    @patch("subprocess.run")
    def test_lift_all_analyzes_all_files(self, mock_subprocess, temp_repo, temp_dir, sample_ir):
        """Test that lift_all analyzes all Python files."""
        # Create multiple Python files
        for i in range(3):
            (Path(temp_dir) / f"module{i}.py").write_text(f"# module {i}")

        temp_repo.index.add([f"module{i}.py" for i in range(3)])
        temp_repo.index.commit("Add modules")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Mock the lift method to return sample IR
        with patch.object(lifter, "lift") as mock_lift:
            mock_lift.return_value = sample_ir

            irs = lifter.lift_all()

            assert len(irs) == 3
            assert mock_lift.call_count == 3

    @patch("subprocess.run")
    def test_lift_all_respects_max_files_limit(
        self, mock_subprocess, temp_repo, temp_dir, sample_ir
    ):
        """Test that max_files limit is respected."""
        # Create 10 files
        for i in range(10):
            (Path(temp_dir) / f"file{i}.py").write_text(f"# file {i}")

        temp_repo.index.add([f"file{i}.py" for i in range(10)])
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        with patch.object(lifter, "lift") as mock_lift:
            mock_lift.return_value = sample_ir

            irs = lifter.lift_all(max_files=5)

            assert len(irs) == 5
            assert mock_lift.call_count == 5

    @patch("subprocess.run")
    def test_lift_all_tracks_progress(self, mock_subprocess, temp_repo, temp_dir, sample_ir):
        """Test that lift_all tracks progress for each file."""
        # Create files
        (Path(temp_dir) / "a.py").write_text("# a")
        (Path(temp_dir) / "b.py").write_text("# b")

        temp_repo.index.add(["a.py", "b.py"])
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        with patch.object(lifter, "lift") as mock_lift:
            mock_lift.return_value = sample_ir

            lifter.lift_all()

            # Check progress log
            progress = lifter.progress_log
            assert any("analyzing:a.py:1/2" in p for p in progress)
            assert any("analyzing:b.py:2/2" in p for p in progress)
            assert any("completed successfully" in p for p in progress)

    @patch("subprocess.run")
    def test_lift_all_continues_on_error(self, mock_subprocess, temp_repo, temp_dir, sample_ir):
        """Test that lift_all continues when individual files fail."""
        # Create files
        (Path(temp_dir) / "good.py").write_text("# good")
        (Path(temp_dir) / "bad.py").write_text("# bad")
        (Path(temp_dir) / "ok.py").write_text("# ok")

        temp_repo.index.add(["good.py", "bad.py", "ok.py"])
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        def mock_lift_with_error(path):
            if "bad.py" in path:
                raise ValueError("Simulated error")
            return sample_ir

        with patch.object(lifter, "lift", side_effect=mock_lift_with_error):
            irs = lifter.lift_all()

            # Should have 2 successful IRs (good.py and ok.py)
            assert len(irs) == 2

            # Progress log should contain error
            assert any("error:bad.py" in p for p in lifter.progress_log)
            assert any("completed with 1 failures" in p for p in lifter.progress_log)

    @patch("subprocess.run")
    def test_lift_all_records_all_failures(self, mock_subprocess, temp_repo, temp_dir):
        """Test that all failures are recorded in progress log."""
        # Create files that will all fail
        for i in range(3):
            (Path(temp_dir) / f"fail{i}.py").write_text(f"# fail {i}")

        temp_repo.index.add([f"fail{i}.py" for i in range(3)])
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        with patch.object(lifter, "lift", side_effect=RuntimeError("Analysis failed")):
            irs = lifter.lift_all()

            assert len(irs) == 0

            # All files should be in error log
            progress = lifter.progress_log
            assert any("error:fail0.py" in p for p in progress)
            assert any("error:fail1.py" in p for p in progress)
            assert any("error:fail2.py" in p for p in progress)
            assert any("completed with 3 failures" in p for p in progress)

    @patch("subprocess.run")
    def test_lift_all_returns_empty_for_no_files(self, mock_subprocess, temp_repo, temp_dir):
        """Test lift_all with no Python files in repository."""
        # Create non-Python files
        (Path(temp_dir) / "README.md").write_text("# README")

        temp_repo.index.add(["README.md"])
        temp_repo.index.commit("Add README")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        irs = lifter.lift_all()

        assert len(irs) == 0

    @patch("subprocess.run")
    def test_lift_all_logs_max_files_limit(self, mock_subprocess, temp_repo, temp_dir, sample_ir):
        """Test that max_files limit is logged."""
        # Create more files than limit
        for i in range(10):
            (Path(temp_dir) / f"module{i}.py").write_text(f"# module {i}")

        temp_repo.index.add([f"module{i}.py" for i in range(10)])
        temp_repo.index.commit("Add modules")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        with patch.object(lifter, "lift") as mock_lift:
            mock_lift.return_value = sample_ir

            lifter.lift_all(max_files=3)

            # Should log the limitation
            assert any("limiting to first 3 of 10 files" in p for p in lifter.progress_log)

    @patch("subprocess.run")
    def test_lift_all_raises_without_repo(self, mock_subprocess):
        """Test that lift_all raises error when repo not loaded."""
        config = LifterConfig()
        lifter = SpecificationLifter(config)

        with pytest.raises(RuntimeError, match="Repository not loaded"):
            lifter.lift_all()

    @patch("subprocess.run")
    def test_lift_all_with_mixed_success_and_failure(
        self, mock_subprocess, temp_repo, temp_dir, sample_ir
    ):
        """Test lift_all with mixture of successful and failed analyses."""
        # Create files
        files = ["success1.py", "fail1.py", "success2.py", "fail2.py", "success3.py"]
        for filename in files:
            (Path(temp_dir) / filename).write_text(f"# {filename}")

        temp_repo.index.add(files)
        temp_repo.index.commit("Add mixed files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        def mock_lift_mixed(path):
            if "fail" in path:
                raise ValueError(f"Failed to analyze {path}")
            return sample_ir

        with patch.object(lifter, "lift", side_effect=mock_lift_mixed):
            irs = lifter.lift_all()

            # Should have 3 successful IRs
            assert len(irs) == 3

            # Progress should show 2 failures
            progress = " ".join(lifter.progress_log)
            assert "error:fail1.py" in progress
            assert "error:fail2.py" in progress
            assert "completed with 2 failures out of 5" in progress

    @patch("subprocess.run")
    def test_lift_all_preserves_metadata(self, mock_subprocess, temp_repo, temp_dir):
        """Test that each IR in lift_all has correct source_path metadata."""
        # Create files
        (Path(temp_dir) / "alpha.py").write_text("# alpha")
        (Path(temp_dir) / "beta.py").write_text("# beta")

        temp_repo.index.add(["alpha.py", "beta.py"])
        temp_repo.index.commit("Add files")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig()
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Let the real lift method run to generate proper IRs
        irs = lifter.lift_all()

        assert len(irs) == 2

        # Check that each IR has the correct source path
        source_paths = {ir.metadata.source_path for ir in irs}
        assert "alpha.py" in source_paths
        assert "beta.py" in source_paths
