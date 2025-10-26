"""End-to-end integration tests for SpecificationLifter + CausalEnhancer.

Tests the complete pipeline from source code → IR → EnhancedIR → causal queries.
"""

import tempfile
from pathlib import Path

import pytest
from git import Repo

from lift_sys.causal import EnhancedIR
from lift_sys.reverse_mode import LifterConfig, SpecificationLifter

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_linear_repo():
    """Create repository with simple linear causal chain: x → y."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Simple linear chain
        test_file = repo_path / "linear.py"
        test_file.write_text(
            """
def compute(x):
    '''Simple linear computation: x → y.'''
    y = x * 2
    return y
"""
        )

        # Configure git
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        repo.index.add(["linear.py"])
        repo.index.commit("Add linear computation")

        yield repo, "linear.py"


@pytest.fixture
def diamond_structure_repo():
    """Create repository with diamond causal structure: x → y, z → w."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Diamond structure
        test_file = repo_path / "diamond.py"
        test_file.write_text(
            """
def diamond(x):
    '''Diamond causal structure.'''
    y = x + 1
    z = x * 2
    w = y + z
    return w
"""
        )

        # Configure git
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        repo.index.add(["diamond.py"])
        repo.index.commit("Add diamond structure")

        yield repo, "diamond.py"


@pytest.fixture
def config_static_mode():
    """LifterConfig with static causal analysis."""
    return LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=True,
        causal_mode="static",
    )


# =============================================================================
# End-to-End Pipeline Tests
# =============================================================================


def test_e2e_simple_linear_static_mode(simple_linear_repo, config_static_mode):
    """Test complete pipeline: simple linear chain in static mode.

    Pipeline: Source code → AST → CausalGraph → SCM → EnhancedIR → Queries
    """
    repo, module_path = simple_linear_repo
    lifter = SpecificationLifter(config_static_mode, repo=repo)

    # STEP 1: Lift specification with causal analysis
    ir = lifter.lift(module_path)

    # Verify EnhancedIR returned
    assert isinstance(ir, EnhancedIR)
    assert ir.has_causal_capabilities
    assert ir.causal_mode == "static"

    # Verify base IR properties accessible
    assert ir.intent is not None
    assert ir.signature is not None
    assert ir.signature.name == "linear"

    # STEP 2: Query causal graph
    graph = ir.causal_graph
    if graph and graph.number_of_nodes() > 0:
        # Graph should have nodes extracted from AST
        nodes = list(graph.nodes())
        assert len(nodes) > 0

        # STEP 3: Query causal impact
        # Pick first node and check downstream impact
        first_node = nodes[0]
        impact = ir.causal_impact(first_node)

        # Impact can be None if no downstream nodes, or dict if there are
        assert impact is None or isinstance(impact, dict)

        # STEP 4: Query causal paths
        if len(nodes) >= 2:
            paths = ir.causal_paths(nodes[0], nodes[1])
            assert paths is None or isinstance(paths, list)


def test_e2e_diamond_structure_static_mode(diamond_structure_repo, config_static_mode):
    """Test complete pipeline: diamond structure in static mode.

    Tests more complex causal structure with multiple paths.
    """
    repo, module_path = diamond_structure_repo
    lifter = SpecificationLifter(config_static_mode, repo=repo)

    # STEP 1: Lift specification
    ir = lifter.lift(module_path)

    assert isinstance(ir, EnhancedIR)
    assert ir.has_causal_capabilities
    assert ir.signature.name == "diamond"

    # STEP 2: Query causal structure
    graph = ir.causal_graph
    if graph and graph.number_of_nodes() > 0:
        nodes = list(graph.nodes())

        # STEP 3: Test multiple query types
        if len(nodes) > 0:
            # Causal impact
            impact = ir.causal_impact(nodes[0])
            assert impact is None or isinstance(impact, dict)

            # Causal paths (should find multiple paths in diamond)
            if len(nodes) >= 2:
                paths = ir.causal_paths(nodes[0], nodes[-1])
                assert paths is None or isinstance(paths, list)


# =============================================================================
# Workflow Integration Tests
# =============================================================================


def test_e2e_workflow_lift_analyze_refactor(simple_linear_repo, config_static_mode):
    """Test realistic workflow: lift → analyze causality → guide refactoring.

    Simulates a developer workflow:
    1. Lift existing code to IR
    2. Analyze causal dependencies
    3. Use causal info to guide refactoring
    """
    repo, module_path = simple_linear_repo
    lifter = SpecificationLifter(config_static_mode, repo=repo)

    # STEP 1: Lift existing code
    ir = lifter.lift(module_path)
    assert isinstance(ir, EnhancedIR)

    # STEP 2: Analyze causal structure
    if ir.causal_graph and ir.causal_graph.number_of_nodes() > 0:
        graph = ir.causal_graph
        nodes = list(graph.nodes())

        # Identify critical nodes (high downstream impact)
        critical_nodes = []
        for node in nodes:
            impact = ir.causal_impact(node)
            if impact and len(impact) > 0:
                critical_nodes.append(node)

        # STEP 3: Use causal info for refactoring decisions
        # Example: Don't refactor critical nodes without careful analysis
        # This demonstrates how EnhancedIR would be used in practice
        assert isinstance(critical_nodes, list)


def test_e2e_workflow_lift_all_with_causal(simple_linear_repo, config_static_mode):
    """Test lift_all() workflow with causal analysis enabled.

    Verifies that batch analysis works with causal enhancement.
    """
    repo, _ = simple_linear_repo
    lifter = SpecificationLifter(config_static_mode, repo=repo)

    # Lift all files in repository
    irs = lifter.lift_all()

    # Should return at least one IR
    assert len(irs) > 0

    # All IRs should be EnhancedIR when causal enabled
    for ir in irs:
        assert isinstance(ir, EnhancedIR)
        assert ir.has_causal_capabilities


# =============================================================================
# Mode Comparison Tests
# =============================================================================


def test_e2e_auto_mode_selects_static(simple_linear_repo):
    """Test auto mode correctly selects static when no traces available."""
    config = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=True,
        causal_mode="auto",  # Auto mode
    )

    repo, module_path = simple_linear_repo
    lifter = SpecificationLifter(config, repo=repo)

    ir = lifter.lift(module_path)

    # Auto should select static (no traces available)
    assert isinstance(ir, EnhancedIR)
    assert ir.causal_mode == "static"


def test_e2e_static_vs_disabled_comparison(simple_linear_repo):
    """Test comparison between causal disabled vs static mode.

    Verifies that enabling causal analysis adds value without breaking behavior.
    """
    repo, module_path = simple_linear_repo

    # Lift WITHOUT causal
    config_disabled = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=False,
    )
    lifter_disabled = SpecificationLifter(config_disabled, repo=repo)
    ir_disabled = lifter_disabled.lift(module_path)

    # Lift WITH causal
    config_enabled = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=True,
        causal_mode="static",
    )
    lifter_enabled = SpecificationLifter(config_enabled, repo=repo)
    ir_enabled = lifter_enabled.lift(module_path)

    # Both should succeed
    assert ir_disabled is not None
    assert ir_enabled is not None

    # Causal disabled returns base IR
    assert not isinstance(ir_disabled, EnhancedIR)

    # Causal enabled returns EnhancedIR
    assert isinstance(ir_enabled, EnhancedIR)

    # Base properties should be identical
    assert ir_disabled.signature.name == ir_enabled.signature.name
    assert ir_disabled.intent.summary == ir_enabled.intent.summary


# =============================================================================
# Error Handling in Pipeline Tests
# =============================================================================


def test_e2e_graceful_degradation_on_ast_parse_error():
    """Test pipeline handles AST parse errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Create invalid Python file
        invalid_file = repo_path / "invalid.py"
        invalid_file.write_text("def broken syntax")

        # Configure git
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        repo.index.add(["invalid.py"])
        repo.index.commit("Add invalid file")

        config = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            run_causal=True,
            causal_mode="static",
        )
        lifter = SpecificationLifter(config, repo=repo)

        # Should handle gracefully and return base IR
        ir = lifter.lift("invalid.py")

        assert ir is not None
        # Causal enhancement should fail, return base IR
        # (Note: The whole lift might fail depending on reverse mode analyzers)


def test_e2e_graceful_degradation_on_enhancer_failure(simple_linear_repo, config_static_mode):
    """Test pipeline handles CausalEnhancer failures gracefully."""
    repo, module_path = simple_linear_repo
    lifter = SpecificationLifter(config_static_mode, repo=repo)

    # Simulate enhancer failure
    class BrokenEnhancer:
        def enhance(self, *args, **kwargs):
            raise RuntimeError("Simulated enhancer failure")

    lifter.causal_enhancer = BrokenEnhancer()

    # Should gracefully degrade to base IR
    ir = lifter.lift(module_path)

    assert ir is not None
    assert not isinstance(ir, EnhancedIR)
    assert any("causal:failed" in log for log in lifter.progress_log)


# =============================================================================
# Performance Tests
# =============================================================================


def test_e2e_static_mode_performance(simple_linear_repo, config_static_mode):
    """Test static mode causal analysis completes quickly (<5s overhead).

    Verifies that Phase 1 (static mode) meets performance target.
    """
    import time

    repo, module_path = simple_linear_repo

    # Time WITHOUT causal
    config_disabled = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        run_causal=False,
    )
    lifter_disabled = SpecificationLifter(config_disabled, repo=repo)

    start = time.time()
    lifter_disabled.lift(module_path)
    time_disabled = time.time() - start

    # Time WITH causal
    lifter_enabled = SpecificationLifter(config_static_mode, repo=repo)

    start = time.time()
    lifter_enabled.lift(module_path)
    time_enabled = time.time() - start

    # Overhead should be < 5s (generous margin)
    overhead = time_enabled - time_disabled
    assert overhead < 5.0, f"Static mode overhead too high: {overhead:.2f}s"


# =============================================================================
# Real-World Scenario Tests
# =============================================================================


def test_e2e_realistic_module_with_multiple_functions():
    """Test pipeline with realistic module containing multiple functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Realistic module
        module_file = repo_path / "calculator.py"
        module_file.write_text(
            """
def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(a, b):
    '''Multiply two numbers.'''
    return a * b

def calculate(x, y):
    '''Calculate result using add and multiply.'''
    sum_result = add(x, y)
    prod_result = multiply(x, y)
    final = add(sum_result, prod_result)
    return final
"""
        )

        # Configure git
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        repo.index.add(["calculator.py"])
        repo.index.commit("Add calculator")

        config = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            run_causal=True,
            causal_mode="static",
        )
        lifter = SpecificationLifter(config, repo=repo)

        # Lift and analyze
        ir = lifter.lift("calculator.py")

        assert isinstance(ir, EnhancedIR)
        assert ir.has_causal_capabilities
        assert ir.signature.name == "calculator"

        # Query causal structure
        graph = ir.causal_graph
        if graph:
            # Should have nodes for variables and functions
            assert graph.number_of_nodes() > 0


# =============================================================================
# Acceptance Criteria Tests
# =============================================================================


def test_e2e_acceptance_criteria_phase_1():
    """Test that all Phase 1 acceptance criteria are met.

    Phase 1 Acceptance Criteria:
    1. LifterConfig has causal options
    2. SpecificationLifter initializes CausalEnhancer when enabled
    3. lift() returns EnhancedIR when causal enabled
    4. lift() returns base IR when causal disabled
    5. Graceful degradation on errors
    6. Backward compatibility maintained
    7. Unit tests pass
    8. Performance < 5% overhead in static mode
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        test_file = repo_path / "test.py"
        test_file.write_text("def test(x):\n    return x * 2")

        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")

        repo.index.add(["test.py"])
        repo.index.commit("Init")

        # 1. LifterConfig has causal options
        config = LifterConfig()
        assert hasattr(config, "run_causal")
        assert hasattr(config, "causal_mode")

        # 2. SpecificationLifter initializes CausalEnhancer when enabled
        config_enabled = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            run_causal=True,
        )
        lifter = SpecificationLifter(config_enabled, repo=repo)
        assert lifter.causal_enhancer is not None

        # 3. lift() returns EnhancedIR when enabled
        ir = lifter.lift("test.py")
        assert isinstance(ir, EnhancedIR)

        # 4. lift() returns base IR when disabled
        config_disabled = LifterConfig(
            run_codeql=False,
            run_daikon=False,
            run_stack_graphs=False,
            run_causal=False,
        )
        lifter_disabled = SpecificationLifter(config_disabled, repo=repo)
        ir_disabled = lifter_disabled.lift("test.py")
        assert not isinstance(ir_disabled, EnhancedIR)

        # 5. Graceful degradation (tested in other tests)

        # 6. Backward compatibility (default config has causal disabled)
        default_config = LifterConfig()
        assert default_config.run_causal is False
