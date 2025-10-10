"""Integration tests for the reverse mode lifter."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lift_sys.ir.models import HoleKind, IntermediateRepresentation
from lift_sys.reverse_mode.analyzers import Finding
from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter


pytestmark = pytest.mark.integration


def build_lifter(tmp_path: Path) -> SpecificationLifter:
    config = LifterConfig(codeql_queries=["security/default"], daikon_entrypoint="main")
    lifter = SpecificationLifter(config)
    lifter.repo = MagicMock()
    lifter.repo.working_tree_dir = str(tmp_path)
    return lifter


def test_lifter_fuses_static_and_dynamic_outputs(tmp_path: Path) -> None:
    lifter = build_lifter(tmp_path)

    codeql_findings = [
        Finding(
            kind="codeql",
            location="src/module.py:10",
            message="Potential injection point",
            metadata={"query": "security/default"},
        )
    ]
    daikon_findings = [
        Finding(
            kind="daikon",
            location="module:main",
            message="x > 0",
            metadata={"predicate": "x > 0"},
        )
    ]

    lifter.codeql.run = MagicMock(return_value=codeql_findings)
    lifter.daikon.run = MagicMock(return_value=daikon_findings)

    ir = lifter.lift("module.py")

    assert isinstance(ir, IntermediateRepresentation)
    assert ir.intent.holes[0].constraints["source"] == "codeql"
    assert ir.assertions[0].predicate == "x > 0"
    assert ir.metadata.source_path == "module.py"


def test_lifter_creates_typed_hole_for_conflicting_analysis(tmp_path: Path) -> None:
    lifter = build_lifter(tmp_path)

    lifter.codeql.run = MagicMock(
        return_value=[
            Finding(
                kind="codeql",
                location="src/module.py:20",
                message="Document missing",
                metadata={"predicate": "x > 0"},
            )
        ]
    )
    lifter.daikon.run = MagicMock(
        return_value=[
            Finding(
                kind="daikon",
                location="module:main",
                message="x < 0",
                metadata={"predicate": "x < 0"},
            )
        ]
    )

    ir = lifter.lift("module.py")

    intent_hole_kinds = {hole.kind for hole in ir.intent.holes}
    assertion_holes = ir.assertions[0].holes

    assert HoleKind.INTENT in intent_hole_kinds
    assert any(hole.kind is HoleKind.ASSERTION for hole in assertion_holes)
    assert any("Clarify invariant" in hole.description for hole in assertion_holes)
