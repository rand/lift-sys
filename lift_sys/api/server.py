"""FastAPI server exposing lift-sys workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..auth.oauth_manager import OAuthManager
from ..auth.provider_configs import build_default_configs
from ..auth.token_store import TokenStore
from ..codegen import CodeGenerator, CodeGeneratorConfig
from ..forward_mode.synthesizer import CodeSynthesizer, SynthesizerConfig
from ..ir.models import IntermediateRepresentation
from ..ir.parser import IRParser
from ..planner.planner import Planner
from ..providers import (
    AnthropicProvider,
    BaseProvider,
    GeminiProvider,
    LocalVLLMProvider,
    OpenAIProvider,
)
from ..reverse_mode.improvement_detector import ImprovementDetector
from ..reverse_mode.lifter import LifterConfig, RepositoryHandle, SpecificationLifter
from ..services.generation_service import GenerationService
from ..services.github_repository import (
    GitHubRepositoryClient,
    RepositoryAccessError,
    RepositoryMetadata,
)
from ..services.orchestrator import HybridOrchestrator
from ..services.reasoning_service import ReasoningService
from ..services.verification_service import VerificationService
from ..spec_sessions import (
    InMemorySessionStore,
    PromptToIRTranslator,
    SpecSessionManager,
)
from .auth import AuthenticatedUser, configure_auth, require_authenticated_user
from .middleware.rate_limiting import rate_limiter
from .routes import auth as auth_routes
from .routes import generate as generate_routes
from .routes import health as health_routes
from .routes import providers as provider_routes
from .schemas import (
    AnalysisResponse,
    AssistResponse,
    AssistsResponse,
    ConfigRequest,
    CreateSessionRequest,
    ForwardRequest,
    ForwardResponse,
    GenerateCodeRequest,
    GenerateCodeResponse,
    ImportReverseIRRequest,
    IRResponse,
    PlannerTelemetry,
    PlanResponse,
    RepoListResponse,
    RepoOpenResponse,
    RepoRequest,
    RepositoryMetadataModel,
    ResolveHoleRequest,
    ReverseRequest,
    RollbackRequest,
    SessionListResponse,
    SessionResponse,
    SuggestionResponse,
    VersionComparisonResponse,
    VersionHistoryResponse,
    VersionInfoResponse,
)
from .schemas import (
    RepositorySummary as RepositorySummaryModel,
)

app = FastAPI(title="lift-sys API", version="0.1.0")
auth_router = configure_auth(app)

allowed_origins_raw = os.getenv("LIFT_SYS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
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
# Use higher rate limit for testing (detected via pytest env var)
import os

is_testing = (
    "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("LIFT_SYS_ENABLE_DEMO_USER_HEADER") == "1"
)
rate_limit_config = (10000, 1.0) if is_testing else (60, 60.0)
app.middleware("http")(
    rate_limiter(max_requests=rate_limit_config[0], per_seconds=rate_limit_config[1])
)
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
        self.config: SynthesizerConfig | None = None
        self.synthesizer: CodeSynthesizer | None = None
        self.lifter: SpecificationLifter | None = None
        self.progress_log = deque(maxlen=256)
        self._progress_subscribers: set[asyncio.Queue] = set()
        self.repositories: dict[str, RepositoryMetadata] = {}

        # Session management
        self.session_store = InMemorySessionStore()
        self.translator: PromptToIRTranslator | None = None
        self.session_manager: SpecSessionManager | None = None

        self.progress_log.append(
            {
                "type": "status",
                "scope": "planner",
                "message": "Planner ready",
                "status": "idle",
                "timestamp": datetime.now(UTC).isoformat() + "Z",
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
        """Reset all state to initial values.

        Creates new instances of all stateful objects to ensure complete isolation
        between tests. This is more thorough than just clearing data.
        """
        # Store progress subscribers to preserve them
        old_subscribers = self._progress_subscribers.copy()

        # Reinitialize everything
        self.__init__()

        # Restore subscribers (they may be needed by running tests)
        self._progress_subscribers = old_subscribers

    async def publish_progress(self, event: dict[str, object]) -> dict[str, object]:
        payload = dict(event)
        payload.setdefault("timestamp", datetime.now(UTC).isoformat() + "Z")
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
    """Reset the global STATE object and clear all cached state."""
    # Reset the global STATE object (recreates all attributes)
    STATE.reset()

    # Also clear app.state attributes if they exist to ensure test isolation
    # This is important for tests where app.state may hold stale references
    _clear_app_state()


def _clear_app_state() -> None:
    """Clear app.state attributes for test isolation.

    This function clears all state attributes set by the lifespan context manager
    and test fixtures to ensure proper test isolation. It's safe to call even if
    some attributes don't exist.
    """
    # List of attributes that may be set on app.state
    state_attrs = [
        "providers",
        "hybrid_orchestrator",
        "primary_provider",
        "services",
        "oauth_managers",
        "token_store",
        "default_user_id",
        "github_repositories",
        "allow_demo_user_header",
    ]

    for attr in state_attrs:
        if hasattr(app.state, attr):
            delattr(app.state, attr)


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


async def _echo_text_runner(prompt: str, _: dict[str, Any]) -> str:
    return prompt


async def _echo_structured_runner(prompt: str, payload: dict[str, Any]) -> str:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app startup and shutdown."""
    # Startup
    token_key = os.getenv("LIFT_SYS_TOKEN_KEY")
    encryption_key = token_key.encode("utf-8") if token_key else TokenStore.generate_key()
    token_storage: dict[str, str] = {}
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

    orchestrator = HybridOrchestrator(
        external_provider=providers["anthropic"], local_provider=local_provider
    )
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

    yield  # App runs during this yield

    # Shutdown (add cleanup code here if needed in future)


# Assign lifespan to app router
app.router.lifespan_context = lifespan


@app.get("/")
async def root(user: AuthenticatedUser = Depends(require_authenticated_user)) -> dict[str, str]:
    LOGGER.debug("Root endpoint accessed by %s", user.id)
    return {
        "name": "lift-sys API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/api/health")
async def health(user: AuthenticatedUser = Depends(require_authenticated_user)) -> dict[str, str]:
    LOGGER.debug("Health check by %s", user.id)
    return {"status": "ok"}


@app.post("/api/config")
async def configure(
    request: ConfigRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> dict[str, str]:
    LOGGER.info("%s updated synthesizer configuration", user.id)
    STATE.set_config(request)
    return {"status": "configured"}


@app.get("/api/repos", response_model=RepoListResponse)
async def list_repositories(
    user: AuthenticatedUser = Depends(require_authenticated_user),
    page: int = 1,
    per_page: int = 30,
    sort: str = "updated",
    direction: str = "desc",
) -> RepoListResponse:
    """List repositories with pagination and sorting.

    Args:
        page: Page number (1-indexed)
        per_page: Number of repositories per page (default 30, max 100)
        sort: Sort by 'created', 'updated', 'pushed', or 'full_name'
        direction: Sort direction 'asc' or 'desc'
    """
    client: GitHubRepositoryClient | None = getattr(app.state, "github_repositories", None)
    if client is None:
        raise HTTPException(status_code=503, detail="github_integration_unavailable")
    try:
        summaries = await client.list_repositories(
            user.id, page=page, per_page=per_page, sort=sort, direction=direction
        )
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


@app.post("/api/repos/open", response_model=RepoOpenResponse)
async def open_repository(
    request: RepoRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> RepoOpenResponse:
    LOGGER.info("%s requested repository open for %s", user.id, request.identifier)
    client: GitHubRepositoryClient | None = getattr(app.state, "github_repositories", None)
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


@app.post("/api/reverse", response_model=IRResponse)
async def reverse(
    request: ReverseRequest, user: AuthenticatedUser = Depends(require_authenticated_user)
) -> IRResponse:
    target_desc = request.module if request.module else "entire project"
    LOGGER.info("%s initiated reverse lift for %s", user.id, target_desc)

    if not STATE.lifter:
        raise HTTPException(status_code=400, detail="lifter not configured")

    # Configure lifter
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

    # Choose analysis mode based on request
    if request.module:
        # Single file mode (backward compatible)
        await STATE.publish_progress(
            {
                "type": "progress",
                "scope": "reverse",
                "stage": "initialise",
                "status": "running",
                "message": f"Analyzing single file: {request.module}",
            }
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
        irs = [ir]
        await STATE.publish_progress(
            {
                "type": "progress",
                "scope": "reverse",
                "stage": "codeql_scan",
                "status": "completed",
                "message": "CodeQL analysis complete",
            }
        )
    else:
        # Whole project mode (default)
        await STATE.publish_progress(
            {
                "type": "progress",
                "scope": "reverse",
                "stage": "discovery",
                "status": "running",
                "message": "Discovering Python files in repository",
            }
        )

        # Define progress callback for real-time updates
        def progress_callback(file_path: str, current: int, total: int):
            # Fire-and-forget progress event
            asyncio.create_task(
                STATE.publish_progress(
                    {
                        "type": "progress",
                        "scope": "reverse",
                        "stage": "file_analysis",
                        "status": "running",
                        "message": f"Analyzing {file_path} ({current}/{total})",
                        "current": current,
                        "total": total,
                        "file": file_path,
                    }
                )
            )

        irs = STATE.lifter.lift_all(progress_callback=progress_callback)
        await STATE.publish_progress(
            {
                "type": "progress",
                "scope": "reverse",
                "stage": "file_analysis",
                "status": "completed",
                "message": f"Analyzed {len(irs)} Python file(s)",
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

    # Load all IRs into planner
    for ir in irs:
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
            "message": f"Planner loaded {len(irs)} IR(s)",
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

    now = datetime.now(UTC).isoformat() + "Z"
    progress = [
        {
            "id": "discovery",
            "label": "File Discovery",
            "status": "completed",
            "message": f"Found {len(irs)} Python file(s)",
            "timestamp": now,
        },
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
    return IRResponse.from_irs(irs, progress=progress)


@app.post("/api/forward", response_model=ForwardResponse)
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


@app.get("/api/plan", response_model=PlanResponse)
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


@app.post("/api/spec-sessions", response_model=SessionResponse)
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
        await STATE.publish_progress(
            {
                "type": "session_created",
                "scope": "spec_sessions",
                "session_id": session.session_id,
                "status": session.status,
                "ambiguities": len(session.get_unresolved_holes()),
            }
        )

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


@app.post("/api/spec-sessions/import-from-reverse", response_model=SessionResponse)
async def import_reverse_ir(
    request: ImportReverseIRRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionResponse:
    """
    Import a reverse-extracted IR into a forward-mode refinement session.

    This endpoint accepts an IR from reverse mode lifting and optionally
    runs improvement detection to identify opportunities for enhancement
    based on security findings, completeness analysis, and quality metrics.

    Args:
        request: Contains the serialized IR and options
        user: Authenticated user

    Returns:
        SessionResponse with detected improvement areas as ambiguities
    """
    LOGGER.info(
        "%s importing reverse IR with improvement detection=%s",
        user.id,
        request.detect_improvements,
    )

    if not STATE.session_manager:
        STATE.set_config(ConfigRequest(model_endpoint="http://localhost:8001"))

    assert STATE.session_manager

    try:
        # Deserialize IR
        reverse_ir = IntermediateRepresentation.from_dict(request.ir)

        # Detect improvement opportunities
        improvement_holes = []
        if request.detect_improvements:
            detector = ImprovementDetector()
            improvement_holes = detector.detect_improvements(reverse_ir)
            LOGGER.info("Detected %d improvement opportunities", len(improvement_holes))

        # Build metadata
        session_metadata = {
            "user_id": user.id,
            "import_timestamp": datetime.now(UTC).isoformat() + "Z",
            "improvement_detection_enabled": request.detect_improvements,
        }
        if request.metadata:
            session_metadata.update(request.metadata)

        # Create session with improvement holes
        session = STATE.session_manager.create_from_reverse_mode_enhanced(
            ir=reverse_ir,
            improvement_holes=improvement_holes,
            metadata=session_metadata,
        )

        # Emit session created event
        await STATE.publish_progress(
            {
                "type": "session_imported_from_reverse",
                "scope": "spec_sessions",
                "session_id": session.session_id,
                "status": session.status,
                "improvements_detected": len(improvement_holes),
                "ambiguities": len(session.get_unresolved_holes()),
            }
        )

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
        LOGGER.error("Failed to import reverse IR: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import reverse IR: {str(e)}")


@app.get("/api/spec-sessions", response_model=SessionListResponse)
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


@app.get("/api/spec-sessions/{session_id}", response_model=SessionResponse)
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


@app.post("/api/spec-sessions/{session_id}/holes/{hole_id}/resolve", response_model=SessionResponse)
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
        await STATE.publish_progress(
            {
                "type": "hole_resolved",
                "scope": "spec_sessions",
                "session_id": session_id,
                "hole_id": hole_id,
                "remaining_ambiguities": len(session.get_unresolved_holes()),
            }
        )

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


@app.post("/api/spec-sessions/{session_id}/finalize", response_model=IRResponse)
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
        await STATE.publish_progress(
            {
                "type": "session_finalized",
                "scope": "spec_sessions",
                "session_id": session_id,
                "status": "finalized",
            }
        )

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


@app.get("/api/spec-sessions/{session_id}/assists", response_model=AssistsResponse)
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
        session_id=session_id, assists=[AssistResponse(**assist) for assist in assists]
    )


@app.delete("/api/spec-sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict[str, str]:
    """Delete a session."""
    LOGGER.info("%s deleting session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    # Check if session exists before deleting
    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    STATE.session_manager.delete_session(session_id)

    await STATE.publish_progress(
        {
            "type": "session_deleted",
            "scope": "spec_sessions",
            "session_id": session_id,
        }
    )

    return {"status": "deleted", "session_id": session_id}


@app.post("/api/spec-sessions/{session_id}/generate", response_model=GenerateCodeResponse)
async def generate_code_from_session(
    session_id: str,
    request: GenerateCodeRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> GenerateCodeResponse:
    """Generate code from a finalized session's IR.

    Args:
        session_id: The session ID to generate code from.
        request: Code generation options.
        user: Authenticated user.

    Returns:
        Generated code with metadata and optional validation results.

    Raises:
        HTTPException: If session not found, not finalized, or generation fails.
    """
    LOGGER.info("%s generating code for session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    # Get the session
    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Check if session is finalized
    if session.status != "finalized":
        raise HTTPException(
            status_code=400,
            detail=f"Session must be finalized before code generation. Current status: {session.status}",
        )

    # Get the IR from the session
    if not session.current_draft or not session.current_draft.ir:
        raise HTTPException(status_code=400, detail="Session has no IR available")

    ir = session.current_draft.ir

    # Validate target language
    if request.target_language != "python":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language: {request.target_language}. Only 'python' is supported.",
        )

    # Validate assertion mode
    valid_modes = ["assert", "raise", "log", "comment"]
    if request.assertion_mode not in valid_modes:
        raise HTTPException(
            status_code=400, detail=f"Invalid assertion_mode. Must be one of: {valid_modes}"
        )

    try:
        # Configure the code generator
        config = CodeGeneratorConfig(
            inject_assertions=request.inject_assertions,
            assertion_mode=request.assertion_mode,  # type: ignore
            include_docstrings=request.include_docstrings,
            include_type_hints=request.include_type_hints,
            preserve_metadata=request.preserve_metadata,
        )
        generator = CodeGenerator(config=config)

        # Generate code
        result = generator.generate(ir)

        # Emit generation event
        await STATE.publish_progress(
            {
                "type": "code_generated",
                "scope": "spec_sessions",
                "session_id": session_id,
                "language": result.language,
            }
        )

        return GenerateCodeResponse(
            session_id=session_id,
            source_code=result.source_code,
            language=result.language,
            metadata=result.metadata,
            warnings=result.warnings,
        )

    except Exception as e:
        LOGGER.error("Code generation failed for session %s: %s", session_id, str(e))
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@app.get("/api/spec-sessions/{session_id}/versions", response_model=VersionHistoryResponse)
async def get_version_history(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> VersionHistoryResponse:
    """
    Get version history for a session.

    Returns a timeline of all IR versions with metadata about each version,
    including provenance information and change summaries.

    Args:
        session_id: The session ID
        user: Authenticated user

    Returns:
        Version history with metadata for each version

    Raises:
        HTTPException: If session not found
    """
    LOGGER.debug("%s fetching version history for session %s", user.id, session_id)
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Build version info for each draft
    versions = []
    for draft in session.ir_drafts:
        # Analyze provenance in this version's IR
        provenance_summary = _analyze_provenance(draft.ir)

        # Determine author from provenance or metadata
        author = draft.metadata.get("author")
        if not author and provenance_summary:
            # Infer author from dominant provenance source
            dominant_source = max(provenance_summary.items(), key=lambda x: x[1])[0]
            author = dominant_source

        # Build change summary
        change_summary = draft.metadata.get("change_summary")
        if not change_summary:
            if draft.version == 1:
                change_summary = "Initial version"
            else:
                change_summary = f"Updated to version {draft.version}"

        versions.append(
            VersionInfoResponse(
                version=draft.version,
                created_at=draft.created_at,
                author=author,
                change_summary=change_summary,
                provenance_summary=provenance_summary,
                tags=draft.metadata.get("tags", []),
                has_holes=len(draft.ambiguities) > 0,
                hole_count=len(draft.ambiguities),
            )
        )

    return VersionHistoryResponse(
        session_id=session_id,
        current_version=session.current_draft.version if session.current_draft else 0,
        versions=versions,
        source=session.source,
    )


@app.get(
    "/api/spec-sessions/{session_id}/versions/{from_version}/compare/{to_version}",
    response_model=VersionComparisonResponse,
)
async def compare_versions(
    session_id: str,
    from_version: int,
    to_version: int,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> VersionComparisonResponse:
    """
    Compare two versions of a session's IR.

    Args:
        session_id: The session ID
        from_version: Source version number
        to_version: Target version number
        user: Authenticated user

    Returns:
        Detailed comparison between the two versions

    Raises:
        HTTPException: If session or versions not found
    """
    LOGGER.debug(
        "%s comparing versions %d and %d for session %s",
        user.id,
        from_version,
        to_version,
        session_id,
    )
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Find the drafts
    from_draft = next((d for d in session.ir_drafts if d.version == from_version), None)
    to_draft = next((d for d in session.ir_drafts if d.version == to_version), None)

    if not from_draft:
        raise HTTPException(status_code=404, detail=f"Version {from_version} not found")
    if not to_draft:
        raise HTTPException(status_code=404, detail=f"Version {to_version} not found")

    # Compare the IRs
    from ..ir import IRComparer

    comparer = IRComparer()
    comparison = comparer.compare(from_draft.ir, to_draft.ir)

    return VersionComparisonResponse(
        session_id=session_id,
        from_version=from_version,
        to_version=to_version,
        comparison=comparison.to_dict(),
        from_ir=from_draft.ir.to_dict(),
        to_ir=to_draft.ir.to_dict(),
    )


@app.post(
    "/api/spec-sessions/{session_id}/versions/{version}/rollback", response_model=SessionResponse
)
async def rollback_to_version(
    session_id: str,
    version: int,
    request: RollbackRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionResponse:
    """
    Rollback a session to a previous version.

    Args:
        session_id: The session ID
        version: Version number to rollback to
        request: Rollback options
        user: Authenticated user

    Returns:
        Updated session response

    Raises:
        HTTPException: If session or version not found
    """
    LOGGER.info(
        "%s rolling back session %s to version %d",
        user.id,
        session_id,
        version,
    )
    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Find the target draft
    target_draft = next((d for d in session.ir_drafts if d.version == version), None)
    if not target_draft:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    try:
        if request.create_new_version:
            # Create a new version based on the target
            from ..spec_sessions.models import IRDraft

            new_version = len(session.ir_drafts) + 1
            new_draft = IRDraft(
                version=new_version,
                ir=target_draft.ir,
                validation_status="pending",
                ambiguities=target_draft.ambiguities,
                metadata={
                    "rollback_from": session.current_draft.version if session.current_draft else 0,
                    "rollback_to": version,
                    "author": user.id,
                    "change_summary": f"Rolled back to version {version}",
                },
            )
            session.add_draft(new_draft)
        else:
            # Replace current with target (destructive)
            session.current_draft = target_draft

        # Update session timestamp
        session.updated_at = datetime.now(UTC).isoformat() + "Z"

        return SessionResponse(
            session_id=session.session_id,
            status=session.status,
            source=session.source,
            current_draft=session.current_draft.to_dict() if session.current_draft else None,
            ambiguities=session.get_unresolved_holes(),
            revision_count=len(session.revisions),
            metadata=session.metadata,
        )

    except Exception as e:
        LOGGER.error("Rollback failed for session %s: %s", session_id, str(e))
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


def _analyze_provenance(ir: IntermediateRepresentation) -> dict[str, int]:
    """
    Analyze provenance sources in an IR and return counts.

    Args:
        ir: The intermediate representation to analyze

    Returns:
        Dictionary mapping provenance sources to counts
    """

    counts: dict[str, int] = {}

    # Check intent
    if ir.intent.provenance:
        source = ir.intent.provenance.source.value
        counts[source] = counts.get(source, 0) + 1

    # Check signature
    if ir.signature.provenance:
        source = ir.signature.provenance.source.value
        counts[source] = counts.get(source, 0) + 1

    # Check parameters
    for param in ir.signature.parameters:
        if param.provenance:
            source = param.provenance.source.value
            counts[source] = counts.get(source, 0) + 1

    # Check effects
    for effect in ir.effects:
        if effect.provenance:
            source = effect.provenance.source.value
            counts[source] = counts.get(source, 0) + 1

    # Check assertions
    for assertion in ir.assertions:
        if assertion.provenance:
            source = assertion.provenance.source.value
            counts[source] = counts.get(source, 0) + 1

    return counts


@app.post("/api/spec-sessions/{session_id}/analyze", response_model=AnalysisResponse)
async def analyze_session_ir(
    session_id: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AnalysisResponse:
    """
    Analyze a session's IR and provide improvement suggestions.

    Performs proactive analysis using the AgentAdvisor to detect anti-patterns,
    missing documentation, security concerns, and other quality issues.

    Args:
        session_id: The session ID to analyze
        user: Authenticated user

    Returns:
        Analysis report with suggestions and quality score

    Raises:
        HTTPException: If session not found or has no IR
    """
    LOGGER.info("%s analyzing IR for session %s", user.id, session_id)

    if not STATE.session_manager:
        raise HTTPException(status_code=404, detail="Session manager not initialized")

    session = STATE.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if not session.current_draft or not session.current_draft.ir:
        raise HTTPException(status_code=400, detail="Session has no IR available for analysis")

    try:
        from ..analysis import AgentAdvisor

        advisor = AgentAdvisor()
        report = advisor.analyze(session.current_draft.ir)

        # Convert suggestions to response format
        suggestions = [
            SuggestionResponse(
                category=s.category.value,
                severity=s.severity.value,
                title=s.title,
                description=s.description,
                location=s.location,
                current_value=s.current_value,
                suggested_value=s.suggested_value,
                rationale=s.rationale,
                examples=s.examples,
                references=s.references,
            )
            for s in report.suggestions
        ]

        return AnalysisResponse(
            session_id=session_id,
            ir_summary=report.ir_summary,
            suggestions=suggestions,
            summary_stats=report.summary_stats,
            overall_quality_score=report.overall_quality_score,
        )

    except Exception as e:
        LOGGER.error("Analysis failed for session %s: %s", session_id, str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
            except TimeoutError:
                # Send heartbeat every 5 seconds
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(UTC).isoformat() + "Z",
                }
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
