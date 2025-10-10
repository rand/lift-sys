"""Reverse mode lifting of specifications from existing code."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from git import Repo

from ..ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
    TypedHole,
)
from .analyzers import CodeQLAnalyzer, DaikonAnalyzer, Finding


@dataclass
class LifterConfig:
    codeql_queries: Iterable[str] = ("security/default",)
    daikon_entrypoint: str = "main"


class SpecificationLifter:
    def __init__(self, config: LifterConfig, repo: Repo | None = None) -> None:
        self.config = config
        self.repo = repo
        self.codeql = CodeQLAnalyzer()
        self.daikon = DaikonAnalyzer()

    def load_repository(self, path: str) -> Repo:
        repo = Repo(path)
        if repo.bare:
            raise ValueError("Repository is bare")
        self.repo = repo
        return repo

    def lift(self, target_module: str) -> IntermediateRepresentation:
        if not self.repo:
            raise RuntimeError("Repository not loaded")
        repo_path = str(Path(self.repo.working_tree_dir))
        codeql_findings = self.codeql.run(repo_path, self.config.codeql_queries)
        daikon_findings = self.daikon.run(repo_path, self.config.daikon_entrypoint)

        intent = self._build_intent(codeql_findings)
        signature = SigClause(
            name=Path(target_module).stem,
            parameters=[Parameter(name="x", type_hint="int", description="example parameter")],
            returns="int",
            holes=[
                TypedHole(
                    identifier="return_contract",
                    type_hint="Predicate",
                    description="Formal return condition",
                    kind=HoleKind.SIGNATURE,
                )
            ],
        )
        effects = [EffectClause(description="Reads external API", holes=[])]
        assertions = [
            AssertClause(
                predicate=finding.metadata.get("predicate", "True"),
                rationale=finding.message,
                holes=[
                    TypedHole(
                        identifier="assertion_detail",
                        type_hint="Predicate",
                        description=f"Clarify invariant from {finding.kind}",
                        kind=HoleKind.ASSERTION,
                    )
                ],
            )
            for finding in daikon_findings
        ]

        return IntermediateRepresentation(
            intent=intent,
            signature=signature,
            effects=effects,
            assertions=assertions,
            metadata=Metadata(source_path=target_module, origin="reverse", language="python"),
        )

    def _build_intent(self, findings: List[Finding]) -> IntentClause:
        summary = "Lifted intent with typed holes"
        holes = [
            TypedHole(
                identifier="intent_gap",
                type_hint="Description",
                description=finding.message,
                constraints={"source": finding.kind},
                kind=HoleKind.INTENT,
            )
            for finding in findings
        ]
        return IntentClause(summary=summary, rationale="Derived from static analysis", holes=holes)


__all__ = ["LifterConfig", "SpecificationLifter"]
