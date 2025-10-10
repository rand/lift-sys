"""Shared pytest fixtures for the lift-sys test suite."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.ir.parser import IRParser


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def parser() -> IRParser:
    return IRParser()


@pytest.fixture
def sample_ir_text(fixtures_dir: Path) -> str:
    return (fixtures_dir / "sample_valid.ir").read_text(encoding="utf8")


@pytest.fixture
def sample_ir() -> IntermediateRepresentation:
    return IntermediateRepresentation(
        intent=IntentClause(summary="Verify sample"),
        signature=SigClause(
            name="sample_module",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        ),
        effects=[EffectClause(description="No side effects")],
        assertions=[AssertClause(predicate="x > 0")],
        metadata=Metadata(origin="tests"),
    )


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    from lift_sys.api.server import app, reset_state

    reset_state()
    with TestClient(app) as client:
        yield client
    reset_state()


@pytest.fixture
def api_state():
    from lift_sys.api import server

    return server.STATE
