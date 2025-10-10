"""FastAPI server exposing lift-sys workflows."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from ..forward_mode.synthesizer import CodeSynthesizer, SynthesizerConfig
from ..ir.models import IntermediateRepresentation
from ..ir.parser import IRParser
from ..planner.planner import Planner
from ..reverse_mode.lifter import LifterConfig, SpecificationLifter
from .schemas import (
    ConfigRequest,
    ForwardRequest,
    ForwardResponse,
    IRResponse,
    PlanResponse,
    RepoRequest,
    ReverseRequest,
)

app = FastAPI(title="lift-sys API", version="0.1.0")


class AppState:
    def __init__(self) -> None:
        self.parser = IRParser()
        self.planner = Planner()
        self.config: Optional[SynthesizerConfig] = None
        self.synthesizer: Optional[CodeSynthesizer] = None
        self.lifter: Optional[SpecificationLifter] = None

    def set_config(self, config: ConfigRequest) -> None:
        self.config = SynthesizerConfig(
            model_endpoint=config.model_endpoint,
            temperature=config.temperature,
            provider_type=config.provider_type,
            schema_uri=config.schema_uri,
            grammar_source=config.grammar_source,
            controller_path=config.controller_path,
        )
        self.synthesizer = CodeSynthesizer(self.config)
        self.lifter = SpecificationLifter(
            LifterConfig(codeql_queries=["security/default"], daikon_entrypoint="main"),
            repo=None,
        )

    def reset(self) -> None:
        self.__init__()


STATE = AppState()


def reset_state() -> None:
    STATE.reset()


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "name": "lift-sys API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/config")
async def configure(request: ConfigRequest) -> Dict[str, str]:
    STATE.set_config(request)
    return {"status": "configured"}


@app.post("/repos/open")
async def open_repository(request: RepoRequest) -> Dict[str, str]:
    if not STATE.lifter:
        STATE.set_config(ConfigRequest(model_endpoint="http://localhost:8001"))
    assert STATE.lifter
    try:
        STATE.lifter.load_repository(request.path)
    except Exception as exc:  # pragma: no cover - defensive broad catch for repository errors
        raise HTTPException(status_code=404, detail=f"repository not accessible: {exc}")
    return {"status": "ready"}


@app.post("/reverse", response_model=IRResponse)
async def reverse(request: ReverseRequest) -> IRResponse:
    if not STATE.lifter:
        raise HTTPException(status_code=400, detail="lifter not configured")
    STATE.lifter.config = LifterConfig(codeql_queries=request.queries or ["security/default"], daikon_entrypoint=request.entrypoint)
    ir = STATE.lifter.lift(request.module)
    STATE.planner.load_ir(ir)
    return IRResponse.from_ir(ir)


@app.post("/forward", response_model=ForwardResponse)
async def forward(request: ForwardRequest) -> ForwardResponse:
    if not STATE.synthesizer:
        raise HTTPException(status_code=400, detail="synthesizer not configured")
    try:
        ir = IntermediateRepresentation.from_dict(request.ir)
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid IR structure: {str(e)}")
    payload = STATE.synthesizer.generate(ir)
    return ForwardResponse(request_payload=payload)


@app.get("/plan", response_model=PlanResponse)
async def get_plan() -> PlanResponse:
    if not STATE.planner.current_plan:
        raise HTTPException(status_code=404, detail="plan not initialised")
    plan = STATE.planner.current_plan
    from dataclasses import asdict
    return PlanResponse(
        steps=[asdict(step) for step in plan.steps],
        goals=plan.goals,
        decision_literals={key: value.to_dict() for key, value in plan.decision_literals.items()},
        recent_events=STATE.planner.recent_events(),
    )


async def websocket_emitter() -> AsyncIterator[str]:
    yield json.dumps({"type": "planner_ready", "data": {}})
    while True:
        events = STATE.planner.consume_events()
        if events:
            for event in events:
                yield json.dumps(event)
        else:
            await asyncio.sleep(0.2)


@app.websocket("/ws/progress")
async def progress_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        async for message in websocket_emitter():
            await websocket.send_text(message)
    except WebSocketDisconnect:  # pragma: no cover - network cleanup
        return


def run() -> None:
    uvicorn.run("lift_sys.api.server:app", host="0.0.0.0", port=8000, reload=False)


__all__ = ["app", "run"]
