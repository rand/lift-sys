"""Stack graph analysis utilities for reverse-mode lifting."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from .analyzers import Finding


@dataclass
class SymbolRelationship:
    """Represents an edge in the symbol relationship graph."""

    source: str
    target: str
    relation: str
    metadata: Dict[str, object]

    def to_finding(self, module: str) -> Finding:
        """Convert this relationship to a ``Finding`` consumable by the lifter."""

        location = f"{module}:{self.source}->{self.target}"
        message = f"{self.source} {self.relation} {self.target}"
        meta = {"relation": self.relation, **self.metadata}
        return Finding(kind="stack_graph", location=location, message=message, metadata=meta)


@dataclass
class StackGraphIndex:
    """In-memory representation of a stack-graph index for a repository."""

    module: str
    relationships: List[SymbolRelationship]


class StackGraphAnalyzer:
    """Adapter for reading stack-graph indexes and exposing relationships."""

    def __init__(self, index_root: str | None = None) -> None:
        self.index_root = Path(index_root) if index_root else None

    def set_index_root(self, index_root: str | Path) -> None:
        self.index_root = Path(index_root)

    def _load_module_index(self, module: str) -> StackGraphIndex | None:
        if not self.index_root:
            return None

        module_name = Path(module).stem
        candidate = self.index_root / f"{module_name}.json"
        if not candidate.exists():
            return None

        with candidate.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        relationships: List[SymbolRelationship] = []
        for edge in payload.get("edges", []):
            relationship = SymbolRelationship(
                source=edge.get("source", ""),
                target=edge.get("target", ""),
                relation=edge.get("relation", "related"),
                metadata={k: v for k, v in edge.items() if k not in {"source", "target", "relation"}},
            )
            relationships.append(relationship)

        return StackGraphIndex(module=module, relationships=relationships)

    def run(self, module: str) -> List[Finding]:
        """Return stack-graph findings for ``module`` if an index exists."""

        index = self._load_module_index(module)
        if not index:
            return []
        return [relationship.to_finding(module) for relationship in index.relationships]


__all__: Iterable[str] = [
    "StackGraphAnalyzer",
    "StackGraphIndex",
    "SymbolRelationship",
]

