"""Unit tests for the planning subsystem."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lift_sys.ir.parser import IRParser
from lift_sys.planner.plan import PlanStep, derive_plan
from lift_sys.planner.planner import Planner


pytestmark = pytest.mark.unit


def test_plan_generation_includes_hole_resolution(parser: IRParser, sample_ir_text: str) -> None:
    ir = parser.parse(sample_ir_text)

    plan = derive_plan(ir)
    identifiers = [step.identifier for step in plan.steps]

    assert identifiers[:2] == ["parse_ir", "verify_assertions"]
    assert "resolve_holes" in identifiers
    assert "finalise_ir" in identifiers
    assert plan.goals == ["verified_ir", "code_generation"]


def test_planner_learns_from_conflicts(parser: IRParser, sample_ir_text: str) -> None:
    """The planner captures conflicts and surfaces fallback actions."""

    ir = parser.parse(sample_ir_text)
    planner = Planner()
    plan = planner.load_ir(ir)

    fallback_step = PlanStep(
        identifier="rerun_with_constraints",
        description="Retry verification with learnt constraints",
    )

    original_next_steps = plan.next_steps

    def next_steps_side_effect(completed):
        if planner.state.conflicts:
            return [fallback_step]
        return original_next_steps(completed)

    with patch.object(plan, "next_steps", side_effect=next_steps_side_effect) as mocked_next_steps:
        ready_after_parse = planner.step("parse_ir", success=True)
        assert any(step.identifier == "verify_assertions" for step in ready_after_parse)

        ready_after_failure = planner.step("verify_assertions", success=False, reason="model: x = 0")

    mocked_next_steps.assert_called()
    assert planner.state.conflicts["verify_assertions"] == "model: x = 0"
    assert fallback_step in ready_after_failure
    assert planner.suggest_resolution()["verify_assertions"].startswith("Investigate")
