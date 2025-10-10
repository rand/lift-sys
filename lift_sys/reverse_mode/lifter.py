"""Reverse mode lifting of specifications from existing code."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

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
from .stack_graphs import StackGraphAnalyzer


@dataclass
class LifterConfig:
    codeql_queries: Iterable[str] = field(default_factory=list)
    daikon_entrypoint: str = "main"
    stack_index_path: str | None = None
    run_codeql: bool = True
    run_daikon: bool = True
    run_stack_graphs: bool = True


class SpecificationLifter:
    def __init__(self, config: LifterConfig, repo: Repo | None = None) -> None:
        self.config = config
        self.repo = repo
        self.codeql = CodeQLAnalyzer()
        self.daikon = DaikonAnalyzer()
        self.stack_graphs = StackGraphAnalyzer()
        self.progress_log: List[str] = []

    def load_repository(self, path: str) -> Repo:
        repo = Repo(path)
        if repo.bare:
            raise ValueError("Repository is bare")
        self.repo = repo
        return repo

    def lift(self, target_module: str) -> IntermediateRepresentation:
        if not self.repo:
            raise RuntimeError("Repository not loaded")
        self.progress_log = []
        self._record_progress("reverse:start")
        repo_path = str(Path(self.repo.working_tree_dir))
        codeql_findings: List[Finding] = []
        if self.config.run_codeql and self.config.codeql_queries:
            self._record_progress("analysis:codeql:start")
            codeql_findings = self.codeql.run(repo_path, self.config.codeql_queries)
            self._record_progress("analysis:codeql:complete")

        daikon_findings: List[Finding] = []
        if self.config.run_daikon:
            self._record_progress("analysis:daikon:start")
            daikon_findings = self.daikon.run(repo_path, self.config.daikon_entrypoint)
            self._record_progress("analysis:daikon:complete")

        stack_findings: List[Finding] = []
        if self.config.run_stack_graphs and self.config.stack_index_path:
            self.stack_graphs.set_index_root(self.config.stack_index_path)
            self._record_progress("analysis:stack_graph:start")
            stack_findings = self.stack_graphs.run(target_module)
            self._record_progress("analysis:stack_graph:complete")

        evidence, evidence_lookup = self._bundle_evidence(codeql_findings, daikon_findings, stack_findings)

        intent = self._build_intent(codeql_findings, evidence_lookup)
        signature = SigClause(
            name=Path(target_module).stem,
            parameters=[Parameter(name="x", type_hint="int", description="example parameter")],
            returns="int",
            holes=[
                TypedHole(
                    identifier="return_contract",
                    type_hint="Predicate",
                    description="Assist needed: populate formal return condition",
                    constraints={"provenance": "reverse", "evidence_id": evidence_lookup.get("signature:return")},
                    kind=HoleKind.SIGNATURE,
                )
            ],
        )
        effects = self._build_effects(stack_findings, evidence_lookup)
        assertions = self._build_assertions(daikon_findings, evidence_lookup)

        metadata = Metadata(source_path=target_module, origin="reverse", evidence=evidence)
        self._record_progress("reverse:ir-assembled")

        return IntermediateRepresentation(
            intent=intent,
            signature=signature,
            effects=effects,
            assertions=assertions,
            metadata=metadata,
        )

    def _record_progress(self, label: str) -> None:
        self.progress_log.append(label)

    def _bundle_evidence(
        self, *groups: Iterable[Finding]
    ) -> Tuple[List[Dict[str, object]], Dict[object, str]]:
        bundles: List[Dict[str, object]] = []
        lookup: Dict[object, str] = {}
        counter = 0
        for group in groups:
            for finding in group:
                evidence_id = f"{finding.kind}-{counter}"
                bundles.append(
                    {
                        "id": evidence_id,
                        "analysis": finding.kind,
                        "location": finding.location,
                        "message": finding.message,
                        "metadata": finding.metadata,
                    }
                )
                lookup[id(finding)] = evidence_id
                counter += 1
        # Provide a stable evidence id for signature holes even without findings
        if all(bundle["id"] != "reverse-signature" for bundle in bundles):
            bundles.append(
                {
                    "id": "reverse-signature",
                    "analysis": "reverse",
                    "location": "signature:return",
                    "message": "Signature return contract requires confirmation",
                    "metadata": {},
                }
            )
        lookup.setdefault("signature:return", "reverse-signature")
        return bundles, lookup

    def _build_intent(self, findings: List[Finding], evidence_lookup: Dict[object, str]) -> IntentClause:
        summary = "Lifted intent with typed holes"
        holes = [
            TypedHole(
                identifier="intent_gap",
                type_hint="Description",
                description=finding.message,
                constraints={
                    "provenance": finding.kind,
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.INTENT,
            )
            for finding in findings
        ]
        return IntentClause(summary=summary, rationale="Derived from static analysis", holes=holes)

    def _build_assertions(
        self, findings: List[Finding], evidence_lookup: Dict[object, str]
    ) -> List[AssertClause]:
        assertions: List[AssertClause] = []
        for index, finding in enumerate(findings):
            predicate = finding.metadata.get("predicate", "True")
            description = (
                f"Assist needed: Clarify invariant from {finding.kind}"
                if finding.metadata.get("ambiguous")
                else f"Clarify invariant from {finding.kind}"
            )
            hole = TypedHole(
                identifier=f"assertion_detail_{index}",
                type_hint="Predicate",
                description=description,
                constraints={
                    "provenance": finding.kind,
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.ASSERTION,
            )
            assertions.append(
                AssertClause(
                    predicate=predicate,
                    rationale=finding.message,
                    holes=[hole],
                )
            )
        return assertions

    def _build_effects(
        self, findings: List[Finding], evidence_lookup: Dict[object, str]
    ) -> List[EffectClause]:
        if not findings:
            return [EffectClause(description="Reads external API", holes=[])]

        effects: List[EffectClause] = []
        for index, finding in enumerate(findings):
            ambiguous = bool(finding.metadata.get("ambiguous"))
            description = (
                f"Assist needed: Disambiguate {finding.message}"
                if ambiguous
                else finding.message
            )
            hole_description = (
                f"Assist needed: Resolve {finding.metadata.get('relation', 'relationship')}"
                if ambiguous
                else f"Confirm {finding.metadata.get('relation', 'relationship')} details"
            )
            hole = TypedHole(
                identifier=f"effect_detail_{index}",
                type_hint="SymbolRelationship",
                description=hole_description,
                constraints={
                    "provenance": finding.kind,
                    "relation": finding.metadata.get("relation", "relationship"),
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.EFFECT,
            )
            effects.append(EffectClause(description=description, holes=[hole]))
        return effects


__all__ = ["LifterConfig", "SpecificationLifter"]
