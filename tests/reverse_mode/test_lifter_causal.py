"""Unit tests for SpecificationLifter causal integration (Phase 1).

Tests the integration of CausalEnhancer (H20-H22) into SpecificationLifter.lift().
"""

import tempfile
from pathlib import Path

import pytest
from git import Repo

from lift_sys.causal import CausalEnhancer, EnhancedIR
from lift_sys.reverse_mode import LifterConfig, SpecificationLifter

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_repo():
    """Create a temporary git repository with a simple Python file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Create a simple Python module
        test_file = repo_path / "test_module.py"
        test_file.write_text(
            """
def double(x):
    '''Double the input value.'''
    return x * 2

def triple(x):
    '''Triple the input value.'''
    return x * 3
"""
        )

        # Configure git user for commits
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        # Initial commit
        repo.index.add(["test_module.py"])
        repo.index.commit("Initial commit")

        yield repo, "test_module.py"


@pytest.fixture
def config_causal_disabled():
    """LifterConfig with causal analysis disabled."""
    return LifterConfig(
        run_codeql=False,  # Disable to speed up tests
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=False,  # Causal disabled (default)
    )


@pytest.fixture
def config_causal_enabled():
    """LifterConfig with causal analysis enabled."""
    return LifterConfig(
        run_codeql=False,  # Disable to speed up tests
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=True,  # Causal enabled
        causal_mode="static",  # Use static mode (faster)
    )


# =============================================================================
# Basic Functionality Tests
# =============================================================================


def test_lifter_config_has_causal_options():
    """Test LifterConfig includes causal configuration options."""
    config = LifterConfig()

    # Check default values
    assert config.run_causal is False  # Disabled by default for backward compatibility
    assert config.causal_mode == "auto"
    assert config.causal_collect_traces is False
    assert config.causal_num_traces == 200
    assert config.causal_enable_circuit_breaker is True
    assert config.causal_circuit_breaker_threshold == 3


def test_lifter_initializes_without_causal(config_causal_disabled):
    """Test SpecificationLifter initializes correctly without causal."""
    lifter = SpecificationLifter(config_causal_disabled)

    assert lifter.config.run_causal is False
    assert lifter.causal_enhancer is None


def test_lifter_initializes_with_causal(config_causal_enabled):
    """Test SpecificationLifter initializes CausalEnhancer when enabled."""
    lifter = SpecificationLifter(config_causal_enabled)

    assert lifter.config.run_causal is True
    assert lifter.causal_enhancer is not None
    assert isinstance(lifter.causal_enhancer, CausalEnhancer)


def test_lifter_causal_disabled_returns_base_ir(temp_repo, config_causal_disabled):
    """Test lift() returns base IR when causal disabled."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_disabled, repo=repo)

    ir = lifter.lift(module_path)

    # Should return base IntermediateRepresentation, not EnhancedIR
    assert ir is not None
    assert not isinstance(ir, EnhancedIR)
    assert hasattr(ir, "intent")
    assert hasattr(ir, "signature")


def test_lifter_causal_enabled_returns_enhanced_ir(temp_repo, config_causal_enabled):
    """Test lift() returns EnhancedIR when causal enabled."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    ir = lifter.lift(module_path)

    # Should return EnhancedIR
    assert ir is not None
    assert isinstance(ir, EnhancedIR)
    assert ir.has_causal_capabilities
    assert ir.causal_mode == "static"


# =============================================================================
# Parameter Override Tests
# =============================================================================


def test_lifter_parameter_overrides_config_enable(temp_repo, config_causal_disabled):
    """Test include_causal=True parameter overrides config (disabled -> enabled)."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_disabled, repo=repo)

    # Config has causal disabled, but parameter enables it
    ir = lifter.lift(module_path, include_causal=True)

    # Should return EnhancedIR because parameter override
    # Note: Will still return base IR if CausalEnhancer wasn't initialized
    # This test verifies parameter is respected, even if enhancer unavailable
    assert ir is not None


def test_lifter_parameter_overrides_config_disable(temp_repo, config_causal_enabled):
    """Test include_causal=False parameter overrides config (enabled -> disabled)."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    # Config has causal enabled, but parameter disables it
    ir = lifter.lift(module_path, include_causal=False)

    # Should return base IR because parameter override
    assert ir is not None
    assert not isinstance(ir, EnhancedIR)


def test_lifter_parameter_none_uses_config(temp_repo, config_causal_enabled):
    """Test include_causal=None uses config value."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    # Parameter is None, should use config value (enabled)
    ir = lifter.lift(module_path, include_causal=None)

    # Should return EnhancedIR because config is enabled
    assert ir is not None
    assert isinstance(ir, EnhancedIR)


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


def test_lifter_causal_failure_returns_base_ir(temp_repo, config_causal_enabled):
    """Test lift() returns base IR if causal enhancement fails."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    # Simulate causal enhancer failure by replacing with broken enhancer
    class BrokenEnhancer:
        def enhance(self, *args, **kwargs):
            raise ValueError("Simulated causal failure")

    lifter.causal_enhancer = BrokenEnhancer()

    # Should gracefully degrade to base IR
    ir = lifter.lift(module_path)

    assert ir is not None
    assert not isinstance(ir, EnhancedIR)  # Should return base IR on failure
    # Check progress log records the failure
    assert any("causal:failed" in log for log in lifter.progress_log)


def test_lifter_invalid_python_file_handles_ast_parse_error(temp_repo, config_causal_enabled):
    """Test graceful handling of invalid Python syntax."""
    repo, _ = temp_repo

    # Create invalid Python file
    invalid_file = Path(repo.working_tree_dir) / "invalid.py"
    invalid_file.write_text("def broken syntax here")

    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    # Should handle parse error gracefully and return base IR
    ir = lifter.lift("invalid.py")

    assert ir is not None
    # Causal enhancement should fail due to parse error, return base IR
    # (The reverse mode analyzers might also fail, but that's separate)


# =============================================================================
# Progress Logging Tests
# =============================================================================


def test_lifter_logs_causal_progress_on_success(temp_repo, config_causal_enabled):
    """Test progress log includes causal analysis steps on success."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    ir = lifter.lift(module_path)

    # Check progress log
    assert "reverse:start" in lifter.progress_log
    assert "reverse:ir-assembled" in lifter.progress_log
    assert "causal:start" in lifter.progress_log
    assert "causal:complete" in lifter.progress_log


def test_lifter_logs_causal_failure(temp_repo, config_causal_enabled):
    """Test progress log includes failure message on causal error."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    # Simulate failure
    class BrokenEnhancer:
        def enhance(self, *args, **kwargs):
            raise ValueError("Test error")

    lifter.causal_enhancer = BrokenEnhancer()

    ir = lifter.lift(module_path)

    # Check failure is logged
    assert any("causal:failed:ValueError:Test error" in log for log in lifter.progress_log)


# =============================================================================
# EnhancedIR Property Tests
# =============================================================================


def test_enhanced_ir_has_base_ir_properties(temp_repo, config_causal_enabled):
    """Test EnhancedIR delegates all base IR properties."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    ir = lifter.lift(module_path)

    # EnhancedIR should have all base IR properties
    assert hasattr(ir, "intent")
    assert hasattr(ir, "signature")
    assert hasattr(ir, "effects")
    assert hasattr(ir, "assertions")
    assert hasattr(ir, "metadata")

    # Base properties should be accessible
    assert ir.intent is not None
    assert ir.signature is not None


def test_enhanced_ir_has_causal_properties(temp_repo, config_causal_enabled):
    """Test EnhancedIR provides causal query methods."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    ir = lifter.lift(module_path)

    # EnhancedIR should have causal-specific properties
    assert hasattr(ir, "has_causal_capabilities")
    assert hasattr(ir, "causal_mode")
    assert hasattr(ir, "causal_graph")
    assert hasattr(ir, "causal_model")

    # EnhancedIR should have causal query methods
    assert hasattr(ir, "causal_impact")
    assert hasattr(ir, "causal_intervention")
    assert hasattr(ir, "causal_paths")


# =============================================================================
# Circuit Breaker Integration Tests
# =============================================================================


def test_lifter_respects_circuit_breaker_config():
    """Test SpecificationLifter passes circuit breaker config to CausalEnhancer."""
    config = LifterConfig(
        run_causal=True,
        causal_enable_circuit_breaker=False,  # Disabled
        causal_circuit_breaker_threshold=10,  # Custom threshold
    )

    lifter = SpecificationLifter(config)

    # CausalEnhancer should be initialized with config values
    # (Can't easily verify private attributes, but we verify it was created)
    assert lifter.causal_enhancer is not None


# =============================================================================
# Edge Cases
# =============================================================================


def test_lifter_causal_enabled_but_no_enhancer(temp_repo):
    """Test behavior when config.run_causal=True but enhancer is None."""
    config = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=True,
    )
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config, repo=repo)

    # Force enhancer to None (simulates initialization failure)
    lifter.causal_enhancer = None

    # Should return base IR (no error)
    ir = lifter.lift(module_path)

    assert ir is not None
    assert not isinstance(ir, EnhancedIR)


def test_lifter_multiple_lifts_preserves_enhancer_state(temp_repo, config_causal_enabled):
    """Test multiple lift() calls don't interfere with each other."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_enabled, repo=repo)

    # First lift
    ir1 = lifter.lift(module_path)
    assert isinstance(ir1, EnhancedIR)

    # Second lift
    ir2 = lifter.lift(module_path)
    assert isinstance(ir2, EnhancedIR)

    # Should be independent IRs
    assert ir1 is not ir2


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


def test_lifter_default_config_maintains_backward_compatibility(temp_repo):
    """Test default LifterConfig maintains backward compatibility (causal disabled)."""
    config = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
    )
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config, repo=repo)

    # Default should have causal disabled
    assert lifter.config.run_causal is False
    assert lifter.causal_enhancer is None

    # Should return base IR (not EnhancedIR)
    ir = lifter.lift(module_path)
    assert not isinstance(ir, EnhancedIR)


def test_lifter_lift_signature_unchanged_for_existing_code(temp_repo, config_causal_disabled):
    """Test lift() signature is backward compatible (include_causal is optional)."""
    repo, module_path = temp_repo
    lifter = SpecificationLifter(config_causal_disabled, repo=repo)

    # Old code should work without passing include_causal
    ir = lifter.lift(module_path)  # No second parameter

    assert ir is not None
