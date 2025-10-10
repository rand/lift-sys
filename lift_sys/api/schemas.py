"""Pydantic schemas for FastAPI endpoints."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..ir.models import IntermediateRepresentation


class ConfigRequest(BaseModel):
    model_endpoint: str = Field(..., description="Model serving endpoint URL")
    temperature: float = 0.0
    provider_type: str = Field(default="vllm", description="Provider implementation type")
    schema_uri: Optional[str] = Field(default=None, description="URI for schema initialisation")
    grammar_source: Optional[str] = Field(default=None, description="Source text for grammar constraints")
    controller_path: Optional[str] = Field(default=None, description="Path to WebAssembly controller module")


class RepoRequest(BaseModel):
    path: str


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

    @classmethod
    def from_ir(cls, ir: IntermediateRepresentation) -> "IRResponse":
        return cls(ir=ir.to_dict())


class PlanResponse(BaseModel):
    steps: List[dict]
    goals: List[str]


class ForwardResponse(BaseModel):
    request_payload: dict


__all__ = [
    "ConfigRequest",
    "RepoRequest",
    "ReverseRequest",
    "ForwardRequest",
    "IRResponse",
    "PlanResponse",
    "ForwardResponse",
]
