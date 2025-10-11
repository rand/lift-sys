"""Integration tests for the reverse mode lifter."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lift_sys.ir.models import HoleKind, IntermediateRepresentation
from lift_sys.reverse_mode.analyzers import Finding
from lift_sys.reverse_mode.lifter import LifterConfig, SpecificationLifter


def build_stack_index(tmp_path: Path) -> Path:
    index_dir = tmp_path / "stack_index"
    index_dir.mkdir()
    index_payload = {
        "edges": [
            {
                "source": "module.function",
                "target": "module.helper",
                "relation": "calls",
                "ambiguous": True,
            }
        ]
    }
    (index_dir / "module.json").write_text(json.dumps(index_payload), encoding="utf-8")
    return index_dir


pytestmark = pytest.mark.integration


def build_lifter(tmp_path: Path, stack_index: Path | None = None) -> SpecificationLifter:
    config = LifterConfig(
        codeql_queries=["security/default"],
        daikon_entrypoint="main",
        stack_index_path=str(stack_index) if stack_index else None,
        run_stack_graphs=stack_index is not None,
    )
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
    assert ir.intent.holes[0].constraints["provenance"] == "codeql"
    assert ir.assertions[0].predicate == "x > 0"
    assert ir.metadata.source_path == "module.py"
    assert any(bundle["analysis"] == "codeql" for bundle in ir.metadata.evidence)
    assert any(bundle["analysis"] == "daikon" for bundle in ir.metadata.evidence)
    assert "reverse" in ir.signature.holes[0].constraints["provenance"]
    assert "reverse:ir-assembled" in lifter.progress_log


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
                metadata={"predicate": "x < 0", "ambiguous": True},
            )
        ]
    )

    ir = lifter.lift("module.py")

    intent_hole_kinds = {hole.kind for hole in ir.intent.holes}
    assertion_holes = ir.assertions[0].holes

    assert HoleKind.INTENT in intent_hole_kinds
    assert any(hole.kind is HoleKind.ASSERTION for hole in assertion_holes)
    assert any("Assist needed" in hole.description for hole in assertion_holes)


def test_lifter_includes_stack_graph_provenance(tmp_path: Path) -> None:
    stack_index = build_stack_index(tmp_path)
    lifter = build_lifter(tmp_path, stack_index=stack_index)

    lifter.codeql.run = MagicMock(return_value=[])
    lifter.daikon.run = MagicMock(return_value=[])

    ir = lifter.lift("module.py")

    assert ir.effects[0].holes[0].constraints["provenance"] == "stack_graph"
    assert "Assist needed" in ir.effects[0].description
    assert any(bundle["analysis"] == "stack_graph" for bundle in ir.metadata.evidence)
