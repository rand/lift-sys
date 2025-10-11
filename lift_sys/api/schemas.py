"""Pydantic schemas for FastAPI endpoints."""
from __future__ import annotations

from typing import Dict, List, Optional

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from ..ir.models import IntermediateRepresentation


class UserIdentity(BaseModel):
    """Representation of an authenticated user's identity."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    provider: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = Field(default=None, serialization_alias="avatarUrl")


class SessionInfo(BaseModel):
    """Session metadata exposed to the frontend."""

    authenticated: bool = False
    user: Optional[UserIdentity] = None


class ConfigRequest(BaseModel):
    model_endpoint: str = Field(..., description="Model serving endpoint URL")
    temperature: float = 0.0
    provider_type: str = Field(default="vllm", description="Provider implementation type")
    schema_uri: Optional[str] = Field(default=None, description="URI for schema initialisation")
    grammar_source: Optional[str] = Field(default=None, description="Source text for grammar constraints")
    controller_path: Optional[str] = Field(default=None, description="Path to WebAssembly controller module")


class RepoRequest(BaseModel):
    identifier: str = Field(..., description="GitHub repository full name, e.g. owner/name")
    branch: Optional[str] = Field(default=None, description="Branch to synchronise prior to analysis")


class RepositorySummary(BaseModel):
    identifier: str
    owner: str
    name: str
    description: Optional[str] = None
    default_branch: str = Field(..., serialization_alias="defaultBranch")
    private: bool = False
    last_synced: Optional[datetime] = Field(default=None, serialization_alias="lastSynced")


class RepositoryMetadataModel(RepositorySummary):
    workspace_path: Optional[str] = Field(default=None, serialization_alias="workspacePath")
    source: str = "github"


class RepoListResponse(BaseModel):
    repositories: List[RepositorySummary]


class RepoOpenResponse(BaseModel):
    status: str
    repository: RepositoryMetadataModel


class ReverseRequest(BaseModel):
    module: str
    queries: List[str] = Field(default_factory=list)
    entrypoint: str = "main"
    analyses: List[str] = Field(
        default_factory=lambda: ["codeql", "daikon", "stack_graphs"],
        description="Analyses to execute during reverse lifting",
    )
    stack_index_path: Optional[str] = Field(
        default=None,
        description="Path to stack-graph index directory",
    )


class ForwardRequest(BaseModel):
    ir: dict


class IRResponse(BaseModel):
    ir: dict
    progress: List[dict] = Field(default_factory=list)

    @classmethod
    def from_ir(
        cls,
        ir: IntermediateRepresentation,
        *,
        progress: Optional[List[Dict[str, object]]] = None,
    ) -> "IRResponse":
        return cls(ir=ir.to_dict(), progress=progress or [])


class PlannerTelemetry(BaseModel):
    nodes: List[dict] = Field(default_factory=list)
    edges: List[dict] = Field(default_factory=list)
    typed_holes: List[dict] = Field(default_factory=list)
    invariants: List[dict] = Field(default_factory=list)
    assists: List[dict] = Field(default_factory=list)
    completed: List[str] = Field(default_factory=list)
    conflicts: Dict[str, str] = Field(default_factory=dict)


class DecisionLiteralModel(BaseModel):
    identifier: str
    type: str
    obligation: str
    steps: List[str]


class PlanResponse(BaseModel):
    steps: List[dict]
    goals: List[str]
    ir: Optional[dict] = None
    telemetry: Optional[PlannerTelemetry] = None
    decision_literals: Dict[str, DecisionLiteralModel] = Field(default_factory=dict)
    recent_events: List[dict] = Field(default_factory=list)


class ForwardResponse(BaseModel):
    request_payload: dict


__all__ = [
    "UserIdentity",
    "SessionInfo",
    "ConfigRequest",
    "RepoRequest",
    "RepositorySummary",
    "RepositoryMetadataModel",
    "RepoListResponse",
    "RepoOpenResponse",
    "ReverseRequest",
    "ForwardRequest",
    "DecisionLiteralModel",
    "IRResponse",
    "PlanResponse",
    "PlannerTelemetry",
    "ForwardResponse",
]
