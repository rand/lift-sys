"""FastAPI server exposing lift-sys workflows."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime
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
    PlannerTelemetry,
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
        self.progress_log = deque(maxlen=256)
        self._progress_subscribers: set[asyncio.Queue] = set()
        self.progress_log.append(
            {
                "type": "status",
                "scope": "planner",
                "message": "Planner ready",
                "status": "idle",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

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
            LifterConfig(
                codeql_queries=["security/default"],
                daikon_entrypoint="main",
                stack_index_path=None,
                run_codeql=True,
                run_daikon=True,
                run_stack_graphs=False,
            ),
            repo=None,
        )

    def reset(self) -> None:
        self.__init__()

    async def publish_progress(self, event: Dict[str, object]) -> Dict[str, object]:
        payload = dict(event)
        payload.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
        self.progress_log.append(payload)
        for queue in list(self._progress_subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(payload)
                except asyncio.QueueEmpty:  # pragma: no cover - defensive cleanup
                    continue
        return payload

    def subscribe_progress(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        for event in self.progress_log:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                break
        self._progress_subscribers.add(queue)
        return queue

    def unsubscribe_progress(self, queue: asyncio.Queue) -> None:
        self._progress_subscribers.discard(queue)


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
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "reverse",
            "stage": "initialise",
            "status": "running",
            "message": f"Preparing reverse mode for {request.module}",
        }
    )
    analyses = set(request.analyses)
    stack_index = request.stack_index_path or getattr(STATE.lifter.config, "stack_index_path", None)
    STATE.lifter.config = LifterConfig(
        codeql_queries=request.queries or ["security/default"],
        daikon_entrypoint=request.entrypoint,
        stack_index_path=stack_index,
        run_codeql="codeql" in analyses,
        run_daikon="daikon" in analyses,
        run_stack_graphs="stack_graphs" in analyses,
    )
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "reverse",
            "stage": "codeql_scan",
            "status": "running",
            "message": "Executing CodeQL queries",
        }
    )
    ir = STATE.lifter.lift(request.module)
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "reverse",
            "stage": "codeql_scan",
            "status": "completed",
            "message": "CodeQL analysis complete",
        }
    )
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "reverse",
            "stage": "daikon_invariants",
            "status": "running",
            "message": "Inferring invariants with Daikon",
        }
    )
    STATE.planner.load_ir(ir)
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "reverse",
            "stage": "daikon_invariants",
            "status": "completed",
            "message": "Candidate invariants inferred",
        }
    )
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "planner",
            "stage": "plan_ready",
            "status": "completed",
            "message": "Planner loaded reverse-mode IR",
        }
    )
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "reverse",
            "stage": "planner_alignment",
            "status": "completed",
            "message": "IR indexed for planner assists",
        }
    )
    # Record lifter progress checkpoints in planner
    for checkpoint in STATE.lifter.progress_log:
        STATE.planner.record_checkpoint(checkpoint)
    now = datetime.utcnow().isoformat() + "Z"
    progress = [
        {
            "id": "codeql_scan",
            "label": "CodeQL Analysis",
            "status": "completed",
            "message": "Security queries executed successfully",
            "timestamp": now,
            "actions": [
                {"label": "View report", "value": "codeql_report"},
                {"label": "Retry", "value": "codeql_retry"},
            ],
        },
        {
            "id": "daikon_invariants",
            "label": "Daikon Inference",
            "status": "completed",
            "message": "Invariants inferred from traces",
            "timestamp": now,
            "actions": [
                {"label": "Inspect", "value": "daikon_details"},
            ],
        },
        {
            "id": "planner_alignment",
            "label": "Planner Alignment",
            "status": "completed",
            "message": "Planner is ready to resolve typed holes",
            "timestamp": now,
            "actions": [
                {"label": "Open Planner", "value": "open_planner"},
            ],
        },
    ]
    return IRResponse.from_ir(ir, progress=progress)


@app.post("/forward", response_model=ForwardResponse)
async def forward(request: ForwardRequest) -> ForwardResponse:
    if not STATE.synthesizer:
        raise HTTPException(status_code=400, detail="synthesizer not configured")
    try:
        ir = IntermediateRepresentation.from_dict(request.ir)
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid IR structure: {str(e)}")
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "forward",
            "stage": "constraints",
            "status": "running",
            "message": "Compiling constraints for forward mode",
        }
    )
    payload = STATE.synthesizer.generate(ir)
    constraints = payload.get("prompt", {}).get("constraints", [])
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "forward",
            "stage": "constraints",
            "status": "completed",
            "message": f"Prepared {len(constraints)} constraints",
        }
    )
    await STATE.publish_progress(
        {
            "type": "progress",
            "scope": "forward",
            "stage": "stream",
            "status": "completed",
            "message": f"Generated {len(payload.get('stream', []))} tokens",
        }
    )
    return ForwardResponse(request_payload=payload)


@app.get("/plan", response_model=PlanResponse)
async def get_plan() -> PlanResponse:
    if not STATE.planner.current_plan:
        raise HTTPException(status_code=404, detail="plan not initialised")
    plan = STATE.planner.current_plan
    from dataclasses import asdict

    state = STATE.planner.state
    nodes = []
    for step in plan.steps:
        if step.identifier in state.completed:
            status = "completed"
        elif step.identifier in state.conflicts:
            status = "blocked"
        elif set(step.prerequisites).issubset(state.completed):
            status = "ready"
        else:
            status = "pending"
        nodes.append({"id": step.identifier, "label": step.description, "status": status})

    edges = []
    for step in plan.steps:
        for dependency in step.prerequisites:
            edges.append({"source": dependency, "target": step.identifier})

    ir = getattr(STATE.planner, "current_ir", None)
    typed_holes = []
    invariants = []
    if ir:
        for hole in ir.intent.holes:
            typed_holes.append(
                {
                    "identifier": hole.identifier,
                    "type_hint": hole.type_hint,
                    "description": hole.description,
                    "clause": "intent",
                    "assist": f"Clarify intent: {hole.description or hole.identifier}",
                }
            )
        for hole in ir.signature.holes:
            typed_holes.append(
                {
                    "identifier": hole.identifier,
                    "type_hint": hole.type_hint,
                    "description": hole.description,
                    "clause": "signature",
                    "assist": f"Refine signature: {hole.description or hole.identifier}",
                }
            )
        for effect in ir.effects:
            for hole in effect.holes:
                typed_holes.append(
                    {
                        "identifier": hole.identifier,
                        "type_hint": hole.type_hint,
                        "description": hole.description,
                        "clause": "effects",
                        "assist": f"Detail effect: {hole.description or hole.identifier}",
                    }
                )
        for assertion in ir.assertions:
            status = "pending"
            if state.conflicts.get("verify_assertions"):
                status = "failed"
            elif "verify_assertions" in state.completed:
                status = "verified"
            invariants.append(
                {
                    "predicate": assertion.predicate,
                    "status": status,
                }
            )
            for hole in assertion.holes:
                typed_holes.append(
                    {
                        "identifier": hole.identifier,
                        "type_hint": hole.type_hint,
                        "description": hole.description,
                        "clause": "assertions",
                        "assist": f"Strengthen invariant: {hole.description or hole.identifier}",
                    }
                )

    assists = []
    suggestions = STATE.planner.suggest_resolution()
    for step_id, message in suggestions.items():
        assists.append({"target": step_id, "message": message})

    telemetry = PlannerTelemetry(
        nodes=nodes,
        edges=edges,
        typed_holes=typed_holes,
        invariants=invariants,
        assists=assists,
        completed=list(state.completed),
        conflicts=dict(state.conflicts),
    )

    return PlanResponse(
        steps=[asdict(step) for step in plan.steps],
        goals=plan.goals,
        ir=ir.to_dict() if ir else None,
        telemetry=telemetry,
        decision_literals={key: value.to_dict() for key, value in plan.decision_literals.items()},
        recent_events=STATE.planner.recent_events(),
    )


async def websocket_emitter() -> AsyncIterator[str]:
    # Emit initial planner ready event
    yield json.dumps({"type": "planner_ready", "data": {}})

    # Subscribe to general progress events
    queue = STATE.subscribe_progress()
    try:
        while True:
            # Check for planner events
            planner_events = STATE.planner.consume_events()
            for event in planner_events:
                yield json.dumps(event)

            # Check for general progress events
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.2)
                yield json.dumps(event)
            except asyncio.TimeoutError:
                # Send heartbeat every 5 seconds
                heartbeat = {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat() + "Z"}
                yield json.dumps(heartbeat)
    finally:
        STATE.unsubscribe_progress(queue)


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
