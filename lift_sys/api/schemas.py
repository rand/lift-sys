"""Pydantic schemas for FastAPI endpoints."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..ir.models import IntermediateRepresentation


class ConfigRequest(BaseModel):
    model_endpoint: str = Field(..., description="vLLM endpoint URL")
    temperature: float = 0.0


class RepoRequest(BaseModel):
    path: str


class ReverseRequest(BaseModel):
    module: str
    queries: List[str] = Field(default_factory=list)
    entrypoint: str = "main"


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
