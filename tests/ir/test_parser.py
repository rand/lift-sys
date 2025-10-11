"""Unit tests for the textual IR parser."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("lark")
from lark.exceptions import LarkError

from lift_sys.ir.models import AssertClause, HoleKind, TypedHole
from lift_sys.ir.parser import IRParser

pytestmark = pytest.mark.unit


def test_parser_parses_full_ir_file(parser: IRParser, sample_ir_text: str) -> None:
    ir = parser.parse(sample_ir_text)

    assert ir.signature.name == "sample_module"
    assert ir.intent.summary == "Document sample behaviour"
    assert any(hole.identifier == "intent_gap" for hole in ir.intent.holes)
    assert len(ir.effects) == 1
    assert ir.assertions and isinstance(ir.assertions[0], AssertClause)


def test_parser_raises_on_invalid_syntax(parser: IRParser) -> None:
    invalid_source = "ir broken { intent: Missing signature }"
    with pytest.raises(LarkError):
        parser.parse(invalid_source)


def test_parser_handles_typed_hole_correctly(parser: IRParser) -> None:
    source = (
        "ir hole_demo {\n"
        '  intent: Demonstrate typed hole { <?my_hole: Predicate = "Ensure" @intent?> }\n'
        "  signature: hole_demo() -> int\n"
        "}\n"
    )
    ir = parser.parse(source)

    hole = ir.intent.holes[0]
    assert isinstance(hole, TypedHole)
    assert hole.identifier == "my_hole"
    assert hole.type_hint == "Predicate"
    assert hole.description == "Ensure"
    assert hole.kind is HoleKind.INTENT


def test_parser_rejects_empty_or_comment_only_files(parser: IRParser, fixtures_dir: Path) -> None:
    with pytest.raises(LarkError):
        parser.parse("")

    comments_only = (fixtures_dir / "comments_only.ir").read_text(encoding="utf8")
    with pytest.raises(LarkError):
        parser.parse(comments_only)
