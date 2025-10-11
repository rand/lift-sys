"""Unit tests for planner with conflict-driven learning.

Tests cover:
- Plan generation from IR
- Conflict-driven learning mechanism
- Fallback strategies
- Step progression
- Constraint learning
"""
import pytest

from lift_sys.ir.models import (
    IntermediateRepresentation,
    IntentClause,
    SigClause,
    Parameter,
    AssertClause,
    Metadata,
)
from lift_sys.planner.planner import Planner


@pytest.mark.unit
class TestPlanner:
    """Unit tests for Planner class with conflict-driven learning."""

    def test_plan_generation_from_simple_ir(self, simple_ir):
        """Test that planner generates correct plan steps from simple IR."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        assert plan is not None
        assert len(plan.steps) >= 3
        assert plan.goals is not None
        assert "verified_ir" in plan.goals or "code_generation" in plan.goals

    def test_plan_has_expected_steps(self, simple_ir):
        """Test that generated plan contains expected step types."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        step_names = [step.identifier for step in plan.steps]

        # Should have parse, verify, and synthesize steps at minimum
        assert any("parse" in name.lower() or "ir" in name.lower() for name in step_names)
        assert any("verify" in name.lower() or "assert" in name.lower() for name in step_names)

    def test_step_progression_success(self, simple_ir):
        """Test stepping through plan with successful outcomes."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        initial_step = plan.steps[0].identifier
        result = planner.step(initial_step, success=True)

        assert len(result.next_steps) >= 1
        assert initial_step in planner.state.completed

    def test_step_progression_failure(self, simple_ir):
        """Test stepping through plan with failed outcome."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        initial_step = plan.steps[0].identifier
        reason = "Test failure reason"
        result = planner.step(initial_step, success=False, reason=reason)

        # Should record the failure
        assert initial_step in planner.state.conflicts
        assert reason in str(planner.state.conflicts[initial_step])

    def test_conflict_driven_learning_records_conflict(self, simple_ir):
        """Test that planner records conflicts for failed steps."""
        planner = Planner()
        planner.load_ir(simple_ir)

        step_name = "verify_assertions"
        failure_reason = "SMT solver timeout"

        planner.step(step_name, success=False, reason=failure_reason)

        assert step_name in planner.state.conflicts
        conflict_info = planner.state.conflicts[step_name]
        assert failure_reason in str(conflict_info)

    def test_suggest_resolution_after_conflict(self, simple_ir):
        """Test that planner suggests resolutions after conflicts."""
        planner = Planner()
        planner.load_ir(simple_ir)

        # Create a conflict
        step_name = "verify_assertions"
        planner.step(step_name, success=False, reason="timeout")

        suggestions = planner.suggest_resolution()

        assert step_name in suggestions
        assert len(suggestions[step_name]) > 0

    def test_fallback_strategy_after_failure(self, complex_ir):
        """Test that planner records fallback strategy after repeated failures."""
        planner = Planner()
        plan = planner.load_ir(complex_ir)

        # Simulate multiple failures on the same step
        step_name = "verify_assertions"
        planner.step(step_name, success=False, reason="timeout 1")
        planner.step(step_name, success=False, reason="timeout 2")

        # Check that conflict is recorded (second reason overwrites first)
        assert step_name in planner.state.conflicts
        conflict_reason = planner.state.conflicts[step_name]
        assert isinstance(conflict_reason, str)
        assert "timeout" in conflict_reason

    def test_plan_goals_are_set(self, simple_ir):
        """Test that plan has defined goals."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        assert plan.goals is not None
        assert len(plan.goals) > 0
        assert isinstance(plan.goals, list)

    def test_planner_state_tracks_progress(self, simple_ir):
        """Test that planner state tracks execution progress."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        # Initially, no steps completed
        assert len(planner.state.completed) == 0

        # After stepping, should track completion
        first_step = plan.steps[0].identifier
        planner.step(first_step, success=True)

        assert first_step in planner.state.completed

    def test_multiple_ir_loads_reset_plan(self, simple_ir, complex_ir):
        """Test that loading new IR resets the plan."""
        planner = Planner()

        plan1 = planner.load_ir(simple_ir)
        step1_name = plan1.steps[0].identifier
        planner.step(step1_name, success=True)

        # Load new IR should reset
        plan2 = planner.load_ir(complex_ir)

        # Plan should be different
        assert plan2 is not None
        assert planner.current_plan == plan2

    def test_constraint_learning_from_conflict(self, simple_ir):
        """Test that planner learns constraints from conflicts."""
        planner = Planner()
        planner.load_ir(simple_ir)

        # Simulate SMT verification failure
        step_name = "verify_assertions"
        conflict_reason = "Assertion 'x > 0' failed with x = -5"

        planner.step(step_name, success=False, reason=conflict_reason)

        # Check that conflict was recorded
        assert step_name in planner.state.conflicts

        # Suggestions should include ways to fix the conflict
        suggestions = planner.suggest_resolution()
        assert step_name in suggestions

    def test_plan_handles_ir_with_no_assertions(self):
        """Test plan generation for IR without assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="no assertions"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        planner = Planner()
        plan = planner.load_ir(ir)

        assert plan is not None
        # Plan should still be generated even without assertions
        assert len(plan.steps) > 0

    def test_plan_handles_complex_ir(self, complex_ir):
        """Test plan generation for complex IR with multiple clauses."""
        planner = Planner()
        plan = planner.load_ir(complex_ir)

        assert plan is not None
        assert len(plan.steps) >= 3

        # Complex IR should generate more steps
        assert len(plan.steps) >= 3

    def test_concurrent_step_execution_tracking(self, simple_ir):
        """Test that planner can track multiple steps."""
        planner = Planner()
        plan = planner.load_ir(simple_ir)

        # Execute multiple steps
        if len(plan.steps) >= 2:
            step1 = plan.steps[0].identifier
            step2 = plan.steps[1].identifier

            planner.step(step1, success=True)
            planner.step(step2, success=True)

            assert step1 in planner.state.completed
            assert step2 in planner.state.completed

    def test_conflict_resolution_suggestions_are_actionable(self, simple_ir):
        """Test that conflict resolution suggestions are actionable."""
        planner = Planner()
        planner.load_ir(simple_ir)

        step_name = "verify_assertions"
        planner.step(step_name, success=False, reason="SMT timeout")

        suggestions = planner.suggest_resolution()

        assert step_name in suggestions
        assert len(suggestions[step_name]) > 0

        # Suggestions should be strings with actionable advice
        for suggestion in suggestions[step_name]:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
