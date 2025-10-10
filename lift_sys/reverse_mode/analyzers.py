"""Wrappers around static and dynamic analysis tooling."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class Finding:
    kind: str
    location: str
    message: str
    metadata: dict


class CodeQLAnalyzer:
    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = database_path

    def run(self, repo_path: str, queries: Iterable[str]) -> List[Finding]:
        # Placeholder implementation that emulates CodeQL outputs.
        findings: List[Finding] = []
        for query in queries:
            findings.append(
                Finding(
                    kind="codeql",
                    location=str(Path(repo_path) / "src" / "module.py:1"),
                    message=f"Query {query} requires refinement",
                    metadata={"query": query},
                )
            )
        return findings


class DaikonAnalyzer:
    def run(self, repo_path: str, entrypoint: str) -> List[Finding]:
        return [
            Finding(
                kind="daikon",
                location=f"{entrypoint}:invariant",
                message="x > 0 inferred",
                metadata={"predicate": "x > 0"},
            )
        ]


__all__ = ["Finding", "CodeQLAnalyzer", "DaikonAnalyzer"]
