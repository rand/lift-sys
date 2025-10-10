"""Integration tests for reverse mode specification lifting.

Tests cover:
- Specification lifting workflow
- Mocked CodeQL and Daikon integration
- Conflicting analysis results
- TypedHole generation for ambiguity
"""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.mark.integration
class TestReverseModeLifter:
    """Integration tests for SpecificationLifter with mocked external tools."""

    @patch("subprocess.run")
    def test_lift_specification_from_code(self, mock_subprocess, temp_repo, temp_dir, sample_code):
        """Test basic specification lifting from code file."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        # Create test file
        code_file = Path(temp_dir) / "test_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["test_code.py"])
        temp_repo.index.commit("Add test code")

        # Mock subprocess calls
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="{}",
            stderr="",
        )

        # Test specification lifting
        config = LifterConfig(
            codeql_queries=["security/default"],
            daikon_entrypoint="factorial",
        )

        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("test_code.py")

        assert ir is not None
        assert ir.signature.name == "test_code"
        assert ir.metadata.source_path == "test_code.py"
        assert ir.metadata.origin == "reverse"

    @patch("subprocess.run")
    def test_lift_with_mocked_codeql(self, mock_subprocess, temp_repo, temp_dir, sample_code, mock_codeql_output):
        """Test lifting with mocked CodeQL analysis."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        # Setup test file
        code_file = Path(temp_dir) / "secure_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["secure_code.py"])
        temp_repo.index.commit("Add secure code")

        # Mock CodeQL output
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=mock_codeql_output,
            stderr="",
        )

        config = LifterConfig(codeql_queries=["security/sql-injection"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("secure_code.py")

        assert ir is not None
        # Should have assertions from CodeQL results
        assert len(ir.assertions) >= 1

    @patch("subprocess.run")
    def test_lift_with_mocked_daikon(self, mock_subprocess, temp_repo, temp_dir, sample_code, mock_daikon_output):
        """Test lifting with mocked Daikon dynamic analysis."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        # Setup test file
        code_file = Path(temp_dir) / "dynamic_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["dynamic_code.py"])
        temp_repo.index.commit("Add dynamic code")

        # Mock Daikon output
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=mock_daikon_output,
            stderr="",
        )

        config = LifterConfig(daikon_entrypoint="factorial")
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("dynamic_code.py")

        assert ir is not None
        # Should have assertions from Daikon invariants
        assert len(ir.assertions) >= 1

    @patch("subprocess.run")
    def test_lift_with_conflicting_analyses(self, mock_subprocess, temp_repo, temp_dir, sample_code):
        """Test lifting with conflicting static and dynamic analysis results."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        # Setup test file
        code_file = Path(temp_dir) / "conflict_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["conflict_code.py"])
        temp_repo.index.commit("Add conflict code")

        # Mock conflicting outputs
        codeql_output = json.dumps({
            "runs": [{
                "results": [{
                    "ruleId": "py/security",
                    "message": {"text": "Input must be >= 0"},
                }]
            }]
        })

        daikon_output = """
        factorial(int n) -> int
        n >= -1
        """

        def mock_run(*args, **kwargs):
            # Alternate between CodeQL and Daikon outputs
            if "codeql" in str(args):
                return Mock(returncode=0, stdout=codeql_output, stderr="")
            else:
                return Mock(returncode=0, stdout=daikon_output, stderr="")

        mock_subprocess.side_effect = mock_run

        config = LifterConfig(
            codeql_queries=["security/default"],
            daikon_entrypoint="factorial",
        )
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("conflict_code.py")

        assert ir is not None
        # Should have TypedHoles for conflicting requirements
        holes = ir.typed_holes()
        assert len(holes) >= 1

    @patch("subprocess.run")
    def test_lift_generates_typed_holes_for_ambiguity(self, mock_subprocess, temp_repo, temp_dir, sample_code):
        """Test that ambiguous analysis results generate TypedHoles."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig
        from lift_sys.ir.models import HoleKind

        # Setup test file
        code_file = Path(temp_dir) / "ambiguous_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["ambiguous_code.py"])
        temp_repo.index.commit("Add ambiguous code")

        # Mock ambiguous output
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="",
            stderr="",
        )

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("ambiguous_code.py")

        assert ir is not None
        holes = ir.typed_holes()

        # Should have at least one hole for ambiguous intent
        assert len(holes) >= 1

        # Check that intent holes exist
        intent_holes = [h for h in holes if h.kind == HoleKind.INTENT]
        assert len(intent_holes) >= 1

    @patch("subprocess.run")
    def test_lift_handles_analysis_failure(self, mock_subprocess, temp_repo, temp_dir, sample_code):
        """Test that lifter handles analysis tool failures gracefully."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        # Setup test file
        code_file = Path(temp_dir) / "fail_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["fail_code.py"])
        temp_repo.index.commit("Add fail code")

        # Mock failure
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Analysis failed",
        )

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        # Should still produce IR with placeholders
        ir = lifter.lift("fail_code.py")

        assert ir is not None
        # Should have TypedHoles for failed analysis
        assert len(ir.typed_holes()) >= 1

    @patch("subprocess.run")
    def test_lift_multiple_files(self, mock_subprocess, temp_repo, temp_dir):
        """Test lifting specifications from multiple files."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        # Create multiple files
        file1 = Path(temp_dir) / "module1.py"
        file2 = Path(temp_dir) / "module2.py"

        file1.write_text("def func1(): pass")
        file2.write_text("def func2(): pass")

        temp_repo.index.add(["module1.py", "module2.py"])
        temp_repo.index.commit("Add modules")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir1 = lifter.lift("module1.py")
        ir2 = lifter.lift("module2.py")

        assert ir1 is not None
        assert ir2 is not None
        assert ir1.metadata.source_path != ir2.metadata.source_path

    @patch("subprocess.run")
    def test_lift_preserves_function_signatures(self, mock_subprocess, temp_repo, temp_dir):
        """Test that lifter preserves function signature information."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        code = """
def calculate(x: int, y: int) -> int:
    return x + y
"""

        code_file = Path(temp_dir) / "calc.py"
        code_file.write_text(code)
        temp_repo.index.add(["calc.py"])
        temp_repo.index.commit("Add calc")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("calc.py")

        assert ir is not None
        # Function signatures should be captured
        assert ir.signature is not None

    @patch("subprocess.run")
    def test_lift_creates_metadata(self, mock_subprocess, temp_repo, temp_dir, sample_code):
        """Test that lifter creates proper metadata."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        code_file = Path(temp_dir) / "meta_code.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["meta_code.py"])
        temp_repo.index.commit("Add meta code")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("meta_code.py")

        assert ir is not None
        assert ir.metadata is not None
        assert ir.metadata.source_path == "meta_code.py"
        assert ir.metadata.origin == "reverse"
        assert ir.metadata.language is not None

    @patch("subprocess.run")
    def test_lift_repository_loading(self, mock_subprocess, temp_repo, temp_dir):
        """Test repository loading functionality."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(codeql_queries=["security/default"])
        lifter = SpecificationLifter(config)

        # Should load repository successfully
        lifter.load_repository(str(temp_dir))

        # Verify repository is loaded
        assert hasattr(lifter, 'repo')
        assert lifter.repo is not None

    @patch("subprocess.run")
    def test_lift_with_multiple_queries(self, mock_subprocess, temp_repo, temp_dir, sample_code):
        """Test lifting with multiple CodeQL queries."""
        from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

        code_file = Path(temp_dir) / "multi_query.py"
        code_file.write_text(sample_code)
        temp_repo.index.add(["multi_query.py"])
        temp_repo.index.commit("Add multi query code")

        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        config = LifterConfig(
            codeql_queries=["security/default", "correctness/basic", "performance/efficiency"]
        )
        lifter = SpecificationLifter(config)
        lifter.load_repository(str(temp_dir))

        ir = lifter.lift("multi_query.py")

        assert ir is not None
        # Multiple queries might generate more assertions
        assert ir.assertions is not None
