"""Pydantic schemas for FastAPI endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..ir.models import IntermediateRepresentation


class UserIdentity(BaseModel):
    """Representation of an authenticated user's identity."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    provider: str
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = Field(default=None, serialization_alias="avatarUrl")


class SessionInfo(BaseModel):
    """Session metadata exposed to the frontend."""

    authenticated: bool = False
    user: UserIdentity | None = None


class ConfigRequest(BaseModel):
    model_endpoint: str = Field(..., description="Model serving endpoint URL")
    temperature: float = 0.0
    provider_type: str = Field(default="vllm", description="Provider implementation type")
    schema_uri: str | None = Field(default=None, description="URI for schema initialisation")
    grammar_source: str | None = Field(
        default=None, description="Source text for grammar constraints"
    )
    controller_path: str | None = Field(
        default=None, description="Path to WebAssembly controller module"
    )


class RepoRequest(BaseModel):
    identifier: str = Field(..., description="GitHub repository full name, e.g. owner/name")
    branch: str | None = Field(default=None, description="Branch to synchronise prior to analysis")


class RepositorySummary(BaseModel):
    identifier: str
    owner: str
    name: str
    description: str | None = None
    default_branch: str = Field(..., serialization_alias="defaultBranch")
    private: bool = False
    last_synced: datetime | None = Field(default=None, serialization_alias="lastSynced")


class RepositoryMetadataModel(RepositorySummary):
    workspace_path: str | None = Field(default=None, serialization_alias="workspacePath")
    source: str = "github"


class RepoListResponse(BaseModel):
    repositories: list[RepositorySummary]


class RepoOpenResponse(BaseModel):
    status: str
    repository: RepositoryMetadataModel


class ReverseRequest(BaseModel):
    module: str
    queries: list[str] = Field(default_factory=list)
    entrypoint: str = "main"
    analyses: list[str] = Field(
        default_factory=lambda: ["codeql", "daikon", "stack_graphs"],
        description="Analyses to execute during reverse lifting",
    )
    stack_index_path: str | None = Field(
        default=None,
        description="Path to stack-graph index directory",
    )


class ForwardRequest(BaseModel):
    ir: dict


class IRResponse(BaseModel):
    ir: dict
    progress: list[dict] = Field(default_factory=list)

    @classmethod
    def from_ir(
        cls,
        ir: IntermediateRepresentation,
        *,
        progress: list[dict[str, object]] | None = None,
    ) -> IRResponse:
        return cls(ir=ir.to_dict(), progress=progress or [])


class PlannerTelemetry(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    typed_holes: list[dict] = Field(default_factory=list)
    invariants: list[dict] = Field(default_factory=list)
    assists: list[dict] = Field(default_factory=list)
    completed: list[str] = Field(default_factory=list)
    conflicts: dict[str, str] = Field(default_factory=dict)


class DecisionLiteralModel(BaseModel):
    identifier: str
    type: str
    obligation: str
    steps: list[str]


class PlanResponse(BaseModel):
    steps: list[dict]
    goals: list[str]
    ir: dict | None = None
    telemetry: PlannerTelemetry | None = None
    decision_literals: dict[str, DecisionLiteralModel] = Field(default_factory=dict)
    recent_events: list[dict] = Field(default_factory=list)


class ForwardResponse(BaseModel):
    request_payload: dict


# Session management schemas


class CreateSessionRequest(BaseModel):
    prompt: str | None = None
    ir: dict | None = None
    source: str = Field(default="prompt", description="'prompt' or 'reverse_mode'")
    metadata: dict = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str
    status: str
    source: str
    created_at: str
    updated_at: str
    current_draft: dict | None = None
    ambiguities: list[str] = Field(default_factory=list)
    revision_count: int
    metadata: dict = Field(default_factory=dict)


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class ResolveHoleRequest(BaseModel):
    resolution_text: str
    resolution_type: str = Field(
        default="clarify_intent",
        description="Type: clarify_intent, add_constraint, refine_signature, specify_effect",
    )


class AssistResponse(BaseModel):
    hole_id: str
    hole_kind: str
    suggestion: str
    description: str


class AssistsResponse(BaseModel):
    session_id: str
    assists: list[AssistResponse]


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
    "CreateSessionRequest",
    "SessionResponse",
    "SessionListResponse",
    "ResolveHoleRequest",
    "AssistResponse",
    "AssistsResponse",
]
