"""Generation endpoints exposing the hybrid orchestrator."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...services.generation_service import GenerationService
from ...services.orchestrator import HybridOrchestrator, Task
from ...services.reasoning_service import ReasoningService

router = APIRouter(prefix="/api/generate", tags=["generate"])


def _get_orchestrator(request: Request) -> HybridOrchestrator:
    orchestrator = getattr(request.app.state, "hybrid_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="hybrid orchestrator not configured")
    return orchestrator


def _get_service(request: Request, service_type: str):
    services = getattr(request.app.state, "services", {})
    if service_type not in services:
        raise HTTPException(status_code=500, detail=f"service '{service_type}' not available")
    return services[service_type]


@router.post("/reasoning")
async def reasoning_endpoint(request: Request, payload: dict[str, object]) -> dict[str, object]:
    service: ReasoningService = _get_service(request, "reasoning")
    prompt = str(payload.get("prompt", ""))
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    temperature = float(payload.get("temperature", 0.7))
    plan = await service.plan(prompt, temperature=temperature)
    return {"provider": "external", "result": plan}


@router.post("/code")
async def code_endpoint(request: Request, payload: dict[str, object]) -> dict[str, object]:
    service: GenerationService = _get_service(request, "generation")
    prompt = str(payload.get("prompt", ""))
    schema = payload.get("schema")
    if not prompt or not isinstance(schema, dict):
        raise HTTPException(status_code=400, detail="prompt and schema are required")
    output = await service.generate_code(prompt, schema)
    return {"provider": "local", "result": output}


@router.post("/structured")
async def structured_endpoint(request: Request, payload: dict[str, object]) -> dict[str, object]:
    orchestrator = _get_orchestrator(request)
    prompt = str(payload.get("prompt", ""))
    schema = payload.get("schema")
    if not prompt or not isinstance(schema, dict):
        raise HTTPException(status_code=400, detail="prompt and schema are required")
    task = Task(prompt=prompt, requires_constrained_output=True, output_schema=schema)
    result = await orchestrator.execute_task(task)
    return {"provider": result.provider, "result": result.content}


@router.post("/hybrid")
async def hybrid_endpoint(request: Request, payload: dict[str, object]) -> dict[str, object]:
    orchestrator = _get_orchestrator(request)
    prompt = str(payload.get("prompt", ""))
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    task = Task(
        prompt=prompt,
        temperature=float(payload.get("temperature", 0.7)),
        requires_constrained_output=bool(payload.get("requires_constrained_output", False)),
        requires_reasoning=bool(payload.get("requires_reasoning", False)),
        requires_verification=bool(payload.get("requires_verification", False)),
        output_schema=payload.get("output_schema"),
        verification_schema=payload.get("verification_schema"),
        metadata={"source": "hybrid-endpoint"},
    )
    result = await orchestrator.execute_task(task)
    return {"provider": result.provider, "result": result.content}


@router.get("/stream")
async def stream_endpoint() -> dict[str, str]:
    raise HTTPException(status_code=501, detail="streaming endpoint not yet implemented")
