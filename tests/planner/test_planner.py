"""Unit tests for the planning subsystem."""

from __future__ import annotations

import pytest

from lift_sys.ir.parser import IRParser
from lift_sys.planner.plan import derive_plan
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


def test_planner_clause_learning_and_backjump(parser: IRParser, sample_ir_text: str) -> None:
    """The planner records decisions, clauses, and backjump targets."""

    ir = parser.parse(sample_ir_text)
    planner = Planner()
    planner.load_ir(ir)

    first = planner.step("parse_ir", success=True)
    assert any(step.identifier == "verify_assertions" for step in first.next_steps)
    assert any(event["type"] == "decision" for event in first.events)

    conflict = planner.step(
        "verify_assertions",
        success=False,
        reason="blocked_by:controller:synthesiser",
    )

    assert planner.state.conflicts["verify_assertions"].startswith("blocked_by")
    assert conflict.learned_clauses
    learned_literals = conflict.learned_clauses[0].literals
    assert "controller:verifier" in learned_literals
    assert "!controller:synthesiser" in learned_literals
    assert conflict.backjump_target == 0
    assert any(event["type"] == "learned_clause" for event in conflict.events)
    assert planner.suggest_resolution()["verify_assertions"].startswith("Investigate")


def test_learned_clause_blocks_future_candidates(parser: IRParser, sample_ir_text: str) -> None:
    ir = parser.parse(sample_ir_text)
    planner = Planner()
    planner.load_ir(ir)

    planner.step("parse_ir", success=True)
    planner.step("verify_assertions", success=True)
    planner.step("resolve_holes", success=True)

    conflict = planner.step(
        "finalise_ir",
        success=False,
        reason="blocked_by:controller:verifier,controller:planner",
    )

    assert conflict.learned_clauses
    next_ids = [step.identifier for step in conflict.next_steps]
    assert "finalise_ir" not in next_ids
    events = planner.consume_events()
    assert any(evt["type"] == "learned_clause" for evt in events)
    assert any(evt["type"] == "next_decisions" for evt in events)


def test_blocked_step_returns_once_dependency_resolved(
    parser: IRParser, sample_ir_text: str
) -> None:
    """A learned clause only blocks while the dependency literal is absent."""

    ir = parser.parse(sample_ir_text)
    planner = Planner()
    planner.load_ir(ir)

    planner.step("parse_ir", success=True)
    conflict = planner.step(
        "verify_assertions",
        success=False,
        reason="blocked_by:controller:synthesiser",
    )

    blocked_candidates = [step.identifier for step in conflict.next_steps]
    assert "verify_assertions" not in blocked_candidates

    # Completing the synthesiser step activates the missing literal and should
    # allow verify_assertions to be considered again.
    planner.step("synthesise_code", success=True)
    refreshed = planner._filter_next_steps(planner.current_plan.next_steps(planner.state.completed))

    refreshed_ids = [step.identifier for step in refreshed]
    assert "verify_assertions" in refreshed_ids
