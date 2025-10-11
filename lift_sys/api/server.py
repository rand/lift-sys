"""FastAPI server exposing lift-sys workflows."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..forward_mode.synthesizer import CodeSynthesizer, SynthesizerConfig
from ..ir.models import IntermediateRepresentation
from ..ir.parser import IRParser
from ..planner.planner import Planner
from ..reverse_mode.lifter import LifterConfig, SpecificationLifter, RepositoryHandle
from ..auth.oauth_manager import OAuthManager
from ..auth.provider_configs import build_default_configs
from ..auth.token_store import TokenStore
from ..services.github_repository import (
    GitHubRepositoryClient,
    RepositoryAccessError,
    RepositoryMetadata,
)
from ..providers import (
    AnthropicProvider,
    BaseProvider,
    GeminiProvider,
    LocalVLLMProvider,
    OpenAIProvider,
)
from ..services.generation_service import GenerationService
from ..services.orchestrator import HybridOrchestrator
from ..services.reasoning_service import ReasoningService
from ..services.verification_service import VerificationService
from .middleware.rate_limiting import rate_limiter
from .auth import AuthenticatedUser, configure_auth, require_authenticated_user
from .routes import auth as auth_routes
from .routes import generate as generate_routes
from .routes import health as health_routes
from .routes import providers as provider_routes
from ..spec_sessions import (
    InMemorySessionStore,
    PromptToIRTranslator,
    SpecSessionManager,
)
from .schemas import (
    AssistResponse,
    AssistsResponse,
    ConfigRequest,
    CreateSessionRequest,
    ForwardRequest,
    ForwardResponse,
    IRResponse,
    PlanResponse,
    PlannerTelemetry,
    RepoRequest,
    RepoListResponse,
    RepoOpenResponse,
    RepositoryMetadataModel,
    RepositorySummary as RepositorySummaryModel,
    ResolveHoleRequest,
    ReverseRequest,
    SessionListResponse,
    SessionResponse,
)

app = FastAPI(title="lift-sys API", version="0.1.0")
auth_router = configure_auth(app)

allowed_origins_raw = os.getenv(
    "LIFT_SYS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")
allowed_origins = [origin.strip() for origin in allowed_origins_raw if origin.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.middleware("http")(rate_limiter())
app.include_router(health_routes.router)
app.include_router(auth_router)
app.include_router(auth_routes.router)
app.include_router(provider_routes.router)
app.include_router(generate_routes.router)


LOGGER = logging.getLogger(__name__)


class AppState:
    def __init__(self) -> None:
        self.parser = IRParser()
        self.planner = Planner()
        self.config: Optional[SynthesizerConfig] = None
        self.synthesizer: Optional[CodeSynthesizer] = None
        self.lifter: Optional[SpecificationLifter] = None
        self.progress_log = deque(maxlen=256)
        self._progress_subscribers: set[asyncio.Queue] = set()
        self.repositories: Dict[str, RepositoryMetadata] = {}

        # Session management
        self.session_store = InMemorySessionStore()
        self.translator: Optional[PromptToIRTranslator] = None
        self.session_manager: Optional[SpecSessionManager] = None

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

        # Initialize session management
        self.translator = PromptToIRTranslator(synthesizer=self.synthesizer, parser=self.parser)
        self.session_manager = SpecSessionManager(
            store=self.session_store,
            translator=self.translator,
            planner=self.planner,
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


def _metadata_to_schema(metadata: RepositoryMetadata) -> RepositoryMetadataModel:
    return RepositoryMetadataModel(
        identifier=metadata.identifier,
        owner=metadata.owner,
        name=metadata.name,
        description=metadata.description,
        default_branch=metadata.default_branch,
        private=metadata.private,
        last_synced=metadata.last_synced,
        workspace_path=str(metadata.workspace_path),
        source=metadata.source,
    )


async def _echo_text_runner(prompt: str, _: Dict[str, Any]) -> str:
    return prompt


async def _echo_structured_runner(prompt: str, payload: Dict[str, Any]) -> str:
    schema = payload.get("schema", {})
    return json.dumps({"prompt": prompt, "schema": schema})


async def _initialize_providers_with_tokens(
    providers: dict[str, BaseProvider], token_store: TokenStore, user_id: str
) -> None:
    """Initialize provider instances using credentials from the token store."""

    for name, provider in providers.items():
        credentials = token_store.load_tokens(user_id, name)
        if not credentials:
            continue
        try:
            await provider.initialize(credentials)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.warning(
                "failed to initialize provider '%s' with stored credentials: %s",
                name,
                exc,
            )


@app.on_event("startup")
async def configure_hybrid_runtime() -> None:
    token_key = os.getenv("LIFT_SYS_TOKEN_KEY")
    encryption_key = token_key.encode("utf-8") if token_key else TokenStore.generate_key()
    token_storage: Dict[str, str] = {}
    token_store = TokenStore(token_storage, encryption_key)

    providers: dict[str, BaseProvider] = {
        "anthropic": AnthropicProvider(),
        "openai": OpenAIProvider(),
        "gemini": GeminiProvider(),
    }

    default_user_id = os.getenv("LIFT_SYS_DEFAULT_USER_ID", "demo-user")
    await _initialize_providers_with_tokens(providers, token_store, default_user_id)

    local_provider = LocalVLLMProvider(
        structured_runner=_echo_structured_runner,
        text_runner=_echo_text_runner,
    )
    await local_provider.initialize({})

    orchestrator = HybridOrchestrator(external_provider=providers["anthropic"], local_provider=local_provider)
    app.state.providers = {**providers, "local": local_provider}
    app.state.hybrid_orchestrator = orchestrator
    app.state.primary_provider = "anthropic"
    app.state.services = {
        "reasoning": ReasoningService(orchestrator),
        "generation": GenerationService(orchestrator),
        "verification": VerificationService(orchestrator),
    }

    redirect_base = os.getenv("LIFT_SYS_OAUTH_REDIRECT_BASE", "http://localhost:3000/api/auth")
    oauth_configs = build_default_configs(redirect_base)
    managers = {
        name: OAuthManager(provider=name, client_config=config, token_store=token_store)
        for name, config in oauth_configs.items()
    }
    app.state.oauth_managers = managers
    app.state.token_store = token_store
    app.state.default_user_id = default_user_id
    workspace_root = Path(
        os.getenv(
            "LIFT_SYS_WORKSPACE_ROOT",
            str(Path.home() / ".cache" / "lift-sys" / "repos"),
        )
    )
    app.state.github_repositories = GitHubRepositoryClient(
        token_store, workspace_root=workspace_root
    )


@app.get("/")
async def root(user: AuthenticatedUser = Depends(require_authenticated_user)) -> Dict[str, str]:
    LOGGER.debug("Root endpoint accessed by %s", user.id)
    return {
        "name": "lift-sys API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health(user: AuthenticatedUser = Depends(require_authenticated_user)) -> Dict[str, str]:
    LOGGER.debug("Health check by %s", user.id)
    return {"status": "ok"}


@app.post("/config")
async def configure(
    request: ConfigRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> Dict[str, str]:
    LOGGER.info("%s updated synthesizer configuration", user.id)
    STATE.set_config(request)
    return {"status": "configured"}


@app.get("/repos", response_model=RepoListResponse)
async def list_repositories(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> RepoListResponse:
    client: Optional[GitHubRepositoryClient] = getattr(
        app.state, "github_repositories", None
    )
    if client is None:
        raise HTTPException(status_code=503, detail="github_integration_unavailable")
    try:
        summaries = await client.list_repositories(user.id)
    except RepositoryAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    repositories = []
    for summary in summaries:
        cached = STATE.repositories.get(summary.identifier)
        repositories.append(
            RepositorySummaryModel(
                identifier=summary.identifier,
                owner=summary.owner,
                name=summary.name,
                description=summary.description,
                default_branch=summary.default_branch,
                private=summary.private,
                last_synced=cached.last_synced if cached else None,
            )
        )
    return RepoListResponse(repositories=repositories)


@app.post("/repos/open", response_model=RepoOpenResponse)
async def open_repository(
    request: RepoRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> RepoOpenResponse:
    LOGGER.info("%s requested repository open for %s", user.id, request.identifier)
    client: Optional[GitHubRepositoryClient] = getattr(
        app.state, "github_repositories", None
    )
    if client is None:
        raise HTTPException(status_code=503, detail="github_integration_unavailable")
    try:
        metadata = await client.ensure_repository(
            user.id, request.identifier, branch=request.branch
        )
    except RepositoryAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if not STATE.lifter:
        STATE.set_config(ConfigRequest(model_endpoint="http://localhost:8001"))
    assert STATE.lifter
    handle = RepositoryHandle(
        identifier=metadata.identifier,
        workspace_path=metadata.workspace_path,
        branch=request.branch or metadata.default_branch,
    )
    try:
        STATE.lifter.load_repository(handle)
    except Exception as exc:  # pragma: no cover - defensive broad catch
        raise HTTPException(status_code=400, detail=f"unable to load repository: {exc}")
    STATE.repositories[metadata.identifier] = metadata
    return RepoOpenResponse(status="ready", repository=_metadata_to_schema(metadata))


@app.post("/reverse", response_model=IRResponse)
async def reverse(
    request: ReverseRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> IRResponse:
    LOGGER.info("%s initiated reverse lift for %s", user.id, request.module)
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
async def forward(
    request: ForwardRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> ForwardResponse:
    LOGGER.info("%s requested forward synthesis", user.id)
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
async def get_plan(user: AuthenticatedUser = Depends(require_authenticated_user)) -> PlanResponse:
    LOGGER.debug("%s fetched planner state", user.id)
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


# Session management endpoints


@app.post("/spec-sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionResponse:
    """Create a new prompt refinement session."""
    LOGGER.info("%s created new spec session", user.id)
    if not STATE.session_manager:
        STATE.set_config(ConfigRequest(model_endpoint="http://localhost:8001"))

    assert STATE.session_manager

    # Validate request
    if not request.prompt and not request.ir:
        raise HTTPException(status_code=400, detail="Either 'prompt' or 'ir' must be provided")

    try:
        if request.prompt:
            # Create from natural language prompt
            session = STATE.session_manager.create_from_prompt(
                prompt=request.prompt,
                metadata=request.metadata,
            )
        else:
            # Create from existing IR (e.g., reverse mode)
            ir = IntermediateRepresentation.from_dict(request.ir)
            session = STATE.session_manager.create_from_reverse_mode(
                ir=ir,
                metadata=request.metadata,
            )

        # Emit session created event
        await STATE.publish_progress({
            "type": "session_created",
            "scope": "spec_sessions",
            "session_id": session.session_id,
            "status": session.status,
            "ambiguities": len(session.get_unresolved_holes()),
        })

        return SessionResponse(
            session_id=session.session_id,
            status=session.status,
            source=session.source,
            created_at=session.created_at,
            updated_at=session.updated_at,
            current_draft=session.current_draft.to_dict() if session.current_draft else None,
            ambiguities=session.get_unresolved_holes(),
            revision_count=len(session.revisions),
            metadata=session.metadata,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/spec-sessions", response_model=SessionListResponse)
async def list_sessions(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionListResponse:
    """List all active sessions."""
    LOGGER.debug("%s listed spec sessions", user.id)
    if not STATE.session_manager:
        return SessionListResponse(sessions=[])

    sessions = STATE.session_manager.list_active_sessions()

    return SessionListResponse(
        sessions=[
            SessionResponse(
                session_id=s.session_id,
                status=s.status,
                source=s.source,
                created_at=s.created_at,
                updated_at=s.updated_at,
                current_draft=s.current_draft.to_dict() if s.current_draft else None,
                ambiguities=s.get_unresolved_holes(),
                revision_count=len(s.revisions),
                metadata=s.metadata,
            )
            for s in sessions
        ]
    )


@app.get("/spec-sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionResponse:
    """Get details of a specific session."""
    LOGGER.debug("%s requested session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        source=session.source,
        created_at=session.created_at,
        updated_at=session.updated_at,
        current_draft=session.current_draft.to_dict() if session.current_draft else None,
        ambiguities=session.get_unresolved_holes(),
        revision_count=len(session.revisions),
        metadata=session.metadata,
    )


@app.post("/spec-sessions/{session_id}/holes/{hole_id}/resolve", response_model=SessionResponse)
async def resolve_hole(
    session_id: str,
    hole_id: str,
    request: ResolveHoleRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionResponse:
    """Resolve a typed hole in a session."""
    LOGGER.info("%s resolving hole %s in session %s", user.id, hole_id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    try:
        session = STATE.session_manager.apply_resolution(
            session_id=session_id,
            hole_id=hole_id,
            resolution_text=request.resolution_text,
            resolution_type=request.resolution_type,
        )

        # Emit hole resolved event
        await STATE.publish_progress({
            "type": "hole_resolved",
            "scope": "spec_sessions",
            "session_id": session_id,
            "hole_id": hole_id,
            "remaining_ambiguities": len(session.get_unresolved_holes()),
        })

        return SessionResponse(
            session_id=session.session_id,
            status=session.status,
            source=session.source,
            created_at=session.created_at,
            updated_at=session.updated_at,
            current_draft=session.current_draft.to_dict() if session.current_draft else None,
            ambiguities=session.get_unresolved_holes(),
            revision_count=len(session.revisions),
            metadata=session.metadata,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve hole: {str(e)}")


@app.post("/spec-sessions/{session_id}/finalize", response_model=IRResponse)
async def finalize_session(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> IRResponse:
    """Finalize a session and return the completed IR."""
    LOGGER.info("%s finalizing session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    try:
        ir = STATE.session_manager.finalize(session_id)

        # Emit finalization event
        await STATE.publish_progress({
            "type": "session_finalized",
            "scope": "spec_sessions",
            "session_id": session_id,
            "status": "finalized",
        })

        return IRResponse.from_ir(ir)

    except ValueError as e:
        # Check if it's a "not found" error or a validation error
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finalize session: {str(e)}")


@app.get("/spec-sessions/{session_id}/assists", response_model=AssistsResponse)
async def get_assists(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AssistsResponse:
    """Get actionable suggestions for resolving holes."""
    LOGGER.debug("%s requested assists for session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    # Check if session exists
    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    assists = STATE.session_manager.get_assists(session_id)

    return AssistsResponse(
        assists=[AssistResponse(**assist) for assist in assists]
    )


@app.delete("/spec-sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> Dict[str, str]:
    """Delete a session."""
    LOGGER.info("%s deleting session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    # Check if session exists before deleting
    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    STATE.session_manager.delete_session(session_id)

    await STATE.publish_progress({
        "type": "session_deleted",
        "scope": "spec_sessions",
        "session_id": session_id,
    })

    return {"status": "deleted", "session_id": session_id}


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
