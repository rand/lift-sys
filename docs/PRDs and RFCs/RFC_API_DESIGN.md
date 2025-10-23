# RFC: lift API Design

**Version**: 1.0
**Date**: 2025-10-21
**Status**: Active
**Authors**: Codelift Team

**Related Documents**:
- [RFC: lift Architecture](RFC_LIFT_ARCHITECTURE.md) - Overall system architecture
- [PRD: Forward Mode](PRD_FORWARD_MODE.md) - Natural language to code workflows
- [PRD: Reverse Mode](PRD_REVERSE_MODE.md) - Code to specification workflows
- [PRD: Interactive Refinement](PRD_INTERACTIVE_REFINEMENT.md) - Session-based refinement

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [API Architecture](#2-api-architecture)
3. [Session Management Endpoints](#3-session-management-endpoints)
4. [Forward Mode Endpoints](#4-forward-mode-endpoints)
5. [Reverse Mode Endpoints](#5-reverse-mode-endpoints)
6. [IR Operations Endpoints](#6-ir-operations-endpoints)
7. [Hole Management Endpoints](#7-hole-management-endpoints)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [Rate Limiting](#9-rate-limiting)
10. [Versioning Strategy](#10-versioning-strategy)
11. [Error Handling](#11-error-handling)
12. [OpenAPI/Swagger Documentation](#12-openapiswagger-documentation)
13. [Testing Strategy](#13-testing-strategy)

---

## 1. Introduction

### 1.1 Purpose

This RFC defines the complete REST API specification for the lift platform, providing programmatic access to:

- **Forward Mode**: Natural language → IR → Code generation
- **Reverse Mode**: Code → IR → Specification extraction
- **Session Management**: Persistent, resumable refinement workflows
- **Hole Resolution**: Interactive constraint-based refinement
- **IR Validation**: Type checking, SMT verification, constraint satisfaction

### 1.2 Design Philosophy

**API-First Principles**:
1. **Stateful Sessions**: All work organized in resumable sessions
2. **Real-Time Collaboration**: WebSocket support for live updates
3. **Type-Safe Contracts**: Pydantic models with strict validation
4. **Progressive Disclosure**: Simple cases are simple, complex cases are possible
5. **Explicit Over Implicit**: All parameters and constraints visible
6. **Security by Default**: Authentication, rate limiting, input validation built-in

**Target Audiences**:
- **Frontend Developers**: Building UIs on top of lift
- **CLI Developers**: Creating command-line tools
- **SDK Maintainers**: Python, TypeScript, Go client libraries
- **AI Agents**: Autonomous code generation and analysis
- **Enterprise Systems**: Integrating lift into CI/CD pipelines

### 1.3 Base URL & Authentication

**Production Base URL**: `https://api.lift.dev/v1`

**Authentication**: Bearer token (JWT) in Authorization header
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**WebSocket URL**: `wss://api.lift.dev/ws/{session_id}`

---

## 2. API Architecture

### 2.1 Technology Stack

**Framework**: FastAPI (Python 3.11+)
- Automatic OpenAPI/Swagger documentation
- Native async/await support
- Pydantic model validation
- High performance (comparable to Node.js)

**Infrastructure**:
- **API Gateway**: Cloudflare Workers (edge routing, DDoS protection)
- **Application Servers**: Modal.com serverless containers (autoscaling)
- **Database**: Supabase PostgreSQL (sessions, holes, revisions)
- **Cache**: Redis (rate limiting, session state)
- **Real-Time**: WebSocket support via FastAPI WebSocket

### 2.2 Request/Response Flow

```
Client Request
  ↓
Cloudflare Edge (DDoS protection, rate limiting)
  ↓
FastAPI App (authentication, input validation)
  ↓
Business Logic (forward/reverse mode, IR validation)
  ↓
Supabase (state persistence)
  ↓
WebSocket Broadcast (real-time updates to subscribers)
  ↓
Client Response
```

### 2.3 Data Models

**Core Pydantic Models**:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# Session Models
# ============================================================================

class SessionStatus(str, Enum):
    draft = "draft"
    refining = "refining"
    validating = "validating"
    finalized = "finalized"
    paused = "paused"
    abandoned = "abandoned"

class CreateSessionRequest(BaseModel):
    target_language: str = Field("python", description="Target programming language")
    project_context: Optional[str] = Field(None, description="Additional project context")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    ws_url: str = Field(..., description="WebSocket URL for real-time updates")
    target_language: str
    project_context: Optional[str]

class ListSessionsResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int
    limit: int
    offset: int

# ============================================================================
# Forward Mode Models
# ============================================================================

class ForwardModeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000,
                        description="Natural language specification")
    max_refinements: int = Field(3, ge=0, le=10,
                                  description="Maximum refinement iterations")
    target_language: Optional[str] = Field(None,
                                           description="Override session language")

    @validator("prompt")
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()

class IntentSpec(BaseModel):
    summary: str
    user_personas: List[str]
    success_criteria: List[str]
    domain_concepts: List[str]
    goals: List[str]
    constraints: List[str]

class FuncSpec(BaseModel):
    preconditions: List[str]
    postconditions: List[str]
    invariants: List[str]
    effects: Dict[str, List[str]]  # {"Database": ["write accounts"], ...}

class ValidationResult(BaseModel):
    compilation_success: bool
    type_check_success: bool
    execution_success: bool
    smt_satisfiable: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None

class ForwardModeResponse(BaseModel):
    session_id: str
    intent_spec: IntentSpec
    ir_program: Dict[str, Any]  # IR JSON representation
    code: Optional[str]  # Generated code (if successful)
    validation: ValidationResult
    refinement_iterations: int
    latency_ms: int
    cost_usd: float
    holes: List[str] = Field(default_factory=list,
                             description="Remaining typed holes")

# ============================================================================
# Reverse Mode Models
# ============================================================================

class ReverseModeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000,
                     description="Source code to analyze")
    language: str = Field("python", description="Source language")
    extract_intent: bool = Field(True,
                                  description="Generate IntentSpec via AI")
    run_security_analysis: bool = Field(True,
                                        description="Run CodeQL security checks")

    @validator("code")
    def validate_code(cls, v):
        if not v.strip():
            raise ValueError("Code cannot be empty")
        return v

class SecurityFinding(BaseModel):
    severity: str  # critical, high, medium, low
    category: str  # e.g., "SQL Injection", "XSS"
    message: str
    location: Dict[str, int]  # {"line": 42, "column": 10}
    remediation: Optional[str]

class ReverseModeResponse(BaseModel):
    session_id: str
    ir_program: Dict[str, Any]
    intent_spec: Optional[IntentSpec]
    func_spec: FuncSpec
    explanation: str  # Human-readable code explanation
    security_findings: List[SecurityFinding] = Field(default_factory=list)
    analysis: Dict[str, Any]  # AST, call graph, dependency info
    holes: List[str] = Field(default_factory=list,
                             description="Ambiguities marked as holes")
    latency_ms: int

# ============================================================================
# IR Validation Models
# ============================================================================

class ValidateIRRequest(BaseModel):
    ir_program: Dict[str, Any] = Field(..., description="IR JSON to validate")
    smt_timeout_seconds: int = Field(5, ge=1, le=30,
                                     description="SMT solver timeout")

class IRValidationResponse(BaseModel):
    valid: bool
    type_check_passed: bool
    smt_satisfiable: Optional[bool]
    errors: List[str] = Field(default_factory=list)
    counterexample: Optional[Dict[str, Any]] = None  # If UNSAT

# ============================================================================
# Hole Management Models
# ============================================================================

class HoleKind(str, Enum):
    term = "term"
    type = "type"
    spec = "spec"
    entity = "entity"
    function = "function"
    module = "module"

class HoleStatus(str, Enum):
    open = "open"
    closed = "closed"
    blocked = "blocked"
    conflict = "conflict"

class TypedHole(BaseModel):
    hole_id: str
    kind: HoleKind
    status: HoleStatus
    type_constraint: Optional[str]
    constraints: List[str] = Field(default_factory=list)
    provenance: str  # Why this hole exists
    dependencies: List[str] = Field(default_factory=list,
                                    description="Hole IDs this blocks/is blocked by")
    created_at: datetime
    closed_at: Optional[datetime]

class HoleSuggestion(BaseModel):
    value: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    constraints_satisfied: bool
    impact: Optional[str] = Field(None,
                                  description="Effect on dependent holes")

class ListHolesResponse(BaseModel):
    holes: List[TypedHole]
    total: int
    critical_path: List[str] = Field(default_factory=list,
                                     description="Hole IDs in critical path order")

class CloseHoleRequest(BaseModel):
    closure_term: str = Field(..., max_length=5000)
    resolution_type: str = Field("clarify_intent",
                                 description="Why hole is being closed")

    @validator("closure_term")
    def validate_term(cls, v):
        if not v.strip():
            raise ValueError("Closure term cannot be empty")
        return v.strip()

class CloseHoleResponse(BaseModel):
    hole_id: str
    status: HoleStatus  # Should be "closed" on success
    propagated_updates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Updates to dependent holes"
    )
    validation_result: ValidationResult

class HoleSuggestionsResponse(BaseModel):
    hole_id: str
    suggestions: List[HoleSuggestion]
    generated_at: datetime
```

### 2.4 Error Response Format

**Standard Error Response**:

```python
class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="Field that caused error")
    message: str
    error_code: str  # e.g., "VALIDATION_ERROR", "AUTH_ERROR"

class ErrorResponse(BaseModel):
    error: str  # High-level error message
    details: List[ErrorDetail] = Field(default_factory=list)
    request_id: str  # For debugging
    timestamp: datetime
```

**HTTP Status Codes**:
- `200 OK`: Successful request
- `201 Created`: Resource created (e.g., new session)
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing or invalid auth token
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Constraint violation (e.g., hole closure conflict)
- `422 Unprocessable Entity`: Valid syntax but semantic error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Temporary outage

---

## 3. Session Management Endpoints

### 3.1 Create Session

**Endpoint**: `POST /sessions`

**Description**: Create a new lift session for forward mode, reverse mode, or manual IR construction.

**Request**:
```json
{
  "target_language": "python",
  "project_context": "FastAPI web service with PostgreSQL",
  "metadata": {
    "project_name": "payment-api",
    "version": "1.0.0"
  }
}
```

**Response**: `201 Created`
```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "user_id": "usr_xyz789",
  "status": "draft",
  "created_at": "2025-10-21T10:00:00Z",
  "updated_at": "2025-10-21T10:00:00Z",
  "ws_url": "wss://api.lift.dev/ws/ses_a1b2c3d4e5f6",
  "target_language": "python",
  "project_context": "FastAPI web service with PostgreSQL"
}
```

**Implementation**:
```python
@app.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Create new lift session."""

    # Verify authentication
    user_id = await verify_token(creds.credentials)

    # Create session in database
    session = Session(
        session_id=f"ses_{generate_id()}",
        user_id=user_id,
        status=SessionStatus.draft,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        target_language=request.target_language,
        project_context=request.project_context,
        metadata=request.metadata or {}
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Log creation event
    await log_event(
        event_type="session_created",
        session_id=session.session_id,
        user_id=user_id,
        metadata={"language": request.target_language}
    )

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        ws_url=f"wss://api.lift.dev/ws/{session.session_id}",
        target_language=session.target_language,
        project_context=session.project_context
    )
```

**Rate Limit**: 10 requests/minute

---

### 3.2 List Sessions

**Endpoint**: `GET /sessions`

**Description**: List user's sessions with pagination.

**Query Parameters**:
- `limit` (int, default=50, max=100): Number of sessions to return
- `offset` (int, default=0): Pagination offset
- `status` (optional): Filter by session status
- `language` (optional): Filter by target language

**Response**: `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "ses_a1b2c3d4e5f6",
      "user_id": "usr_xyz789",
      "status": "finalized",
      "created_at": "2025-10-21T10:00:00Z",
      "updated_at": "2025-10-21T10:30:00Z",
      "ws_url": "wss://api.lift.dev/ws/ses_a1b2c3d4e5f6",
      "target_language": "python",
      "project_context": "Payment API"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

**Implementation**:
```python
@app.get("/sessions", response_model=ListSessionsResponse)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[SessionStatus] = None,
    language: Optional[str] = None,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> ListSessionsResponse:
    """List user's sessions."""

    user_id = await verify_token(creds.credentials)

    # Build query
    query = select(Session).where(Session.user_id == user_id)

    if status:
        query = query.where(Session.status == status)
    if language:
        query = query.where(Session.target_language == language)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.order_by(Session.updated_at.desc())
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    sessions = result.scalars().all()

    return ListSessionsResponse(
        sessions=[session_to_response(s) for s in sessions],
        total=total,
        limit=limit,
        offset=offset
    )
```

**Rate Limit**: 100 requests/minute

---

### 3.3 Get Session

**Endpoint**: `GET /sessions/{session_id}`

**Description**: Retrieve full session state including IR, holes, and history.

**Response**: `200 OK`
```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "user_id": "usr_xyz789",
  "status": "refining",
  "created_at": "2025-10-21T10:00:00Z",
  "updated_at": "2025-10-21T10:15:00Z",
  "ws_url": "wss://api.lift.dev/ws/ses_a1b2c3d4e5f6",
  "target_language": "python",
  "project_context": "Payment API",
  "current_ir": {
    "version": "0.9",
    "clauses": [...]
  },
  "holes": [
    {
      "hole_id": "?notification_channel",
      "kind": "term",
      "status": "open",
      "type_constraint": "Set[Channel]",
      "constraints": ["at_least_one"],
      "provenance": "Ambiguous prompt: 'send notifications'",
      "dependencies": ["?retry_strategy"],
      "created_at": "2025-10-21T10:05:00Z",
      "closed_at": null
    }
  ],
  "revision_history": [
    {
      "version": 1,
      "action": "create",
      "timestamp": "2025-10-21T10:00:00Z"
    },
    {
      "version": 2,
      "action": "fill_hole",
      "hole_id": "?max_retries",
      "timestamp": "2025-10-21T10:10:00Z"
    }
  ]
}
```

**Implementation**:
```python
@app.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> SessionDetailResponse:
    """Get full session state."""

    user_id = await verify_token(creds.credentials)

    # Load session
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Authorization check
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Load related data
    holes = await db.execute(
        select(Hole).where(Hole.session_id == session_id)
    )
    holes = holes.scalars().all()

    revisions = await db.execute(
        select(Revision)
        .where(Revision.session_id == session_id)
        .order_by(Revision.version.asc())
    )
    revisions = revisions.scalars().all()

    return SessionDetailResponse(
        **session_to_response(session).dict(),
        current_ir=session.current_ir_snapshot,
        holes=[hole_to_response(h) for h in holes],
        revision_history=[rev_to_response(r) for r in revisions]
    )
```

**Rate Limit**: 100 requests/minute

---

### 3.4 Delete Session

**Endpoint**: `DELETE /sessions/{session_id}`

**Description**: Delete session and all associated data (IR, holes, revisions).

**Response**: `200 OK`
```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "deleted": true,
  "timestamp": "2025-10-21T10:30:00Z"
}
```

**Implementation**:
```python
@app.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> DeleteResponse:
    """Delete session."""

    user_id = await verify_token(creds.credentials)

    # Load and authorize
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Cascade delete (holes, revisions)
    await db.delete(session)
    await db.commit()

    # Log deletion
    await log_event(
        event_type="session_deleted",
        session_id=session_id,
        user_id=user_id
    )

    return DeleteResponse(
        session_id=session_id,
        deleted=True,
        timestamp=datetime.utcnow()
    )
```

**Rate Limit**: 50 requests/minute

---

## 4. Forward Mode Endpoints

### 4.1 Execute Forward Mode

**Endpoint**: `POST /sessions/{session_id}/forward`

**Description**: Execute Forward Mode pipeline: Natural Language → IntentSpec → FuncSpec → IR → Code.

**Request**:
```json
{
  "prompt": "Create a REST API endpoint to validate email addresses. Must check format, domain validity, and MX records. Return validation result and error message if invalid.",
  "max_refinements": 3,
  "target_language": "python"
}
```

**Response**: `200 OK`
```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "intent_spec": {
    "summary": "Validate email addresses with format and domain checks",
    "user_personas": ["API consumer"],
    "success_criteria": [
      "Valid emails pass validation",
      "Invalid emails return clear error messages",
      "MX record validation performed"
    ],
    "domain_concepts": ["Email", "Domain", "MXRecord", "ValidationResult"],
    "goals": [
      "Ensure email format correctness",
      "Verify domain exists",
      "Check MX records for deliverability"
    ],
    "constraints": [
      "Email must contain exactly one @",
      "Domain must have valid TLD",
      "MX record lookup timeout: 5s"
    ]
  },
  "ir_program": {
    "version": "0.9",
    "clauses": [
      {
        "type": "FuncSpec",
        "name": "validate_email",
        "signature": {
          "params": [{"name": "email", "type": "str"}],
          "returns": "tuple[bool, Optional[str]]"
        },
        "requires": [
          "isinstance(email, str)",
          "len(email) > 0"
        ],
        "ensures": [
          "result[0] == True implies valid_format(email)",
          "result[0] == False implies result[1] is not None"
        ],
        "effects": {
          "Network": ["DNS MX lookup"]
        }
      }
    ]
  },
  "code": "import re\nimport dns.resolver\nfrom typing import Optional\n\nasync def validate_email(email: str) -> tuple[bool, Optional[str]]:\n    \"\"\"Validate email with format and MX record checks.\"\"\"\n    assert isinstance(email, str), \"Email must be string\"\n    assert len(email) > 0, \"Email cannot be empty\"\n    \n    # Format validation\n    if email.count('@') != 1:\n        return (False, \"Must contain exactly one @ symbol\")\n    \n    local, domain = email.split('@')\n    \n    if not re.match(r'^[a-zA-Z0-9._%+-]+$', local):\n        return (False, \"Invalid local part format\")\n    \n    if not re.match(r'^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$', domain):\n        return (False, \"Invalid domain format\")\n    \n    # MX record validation\n    try:\n        mx_records = dns.resolver.resolve(domain, 'MX', lifetime=5.0)\n        if not mx_records:\n            return (False, \"No MX records found for domain\")\n    except dns.resolver.NXDOMAIN:\n        return (False, \"Domain does not exist\")\n    except dns.resolver.Timeout:\n        return (False, \"MX lookup timeout\")\n    except Exception as e:\n        return (False, f\"DNS error: {str(e)}\")\n    \n    return (True, None)",
  "validation": {
    "compilation_success": true,
    "type_check_success": true,
    "execution_success": true,
    "smt_satisfiable": true,
    "errors": [],
    "warnings": [],
    "test_results": {
      "passed": 5,
      "failed": 0,
      "coverage": 0.95
    }
  },
  "refinement_iterations": 2,
  "latency_ms": 16234,
  "cost_usd": 0.0029,
  "holes": []
}
```

**Response with Holes**: `200 OK` (partial success)
```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "intent_spec": {...},
  "ir_program": {...},
  "code": null,
  "validation": {
    "compilation_success": false,
    "type_check_success": false,
    "execution_success": false,
    "smt_satisfiable": true,
    "errors": ["Cannot generate code with open holes"],
    "warnings": ["3 holes require resolution"]
  },
  "refinement_iterations": 1,
  "latency_ms": 8500,
  "cost_usd": 0.0015,
  "holes": ["?mx_timeout", "?cache_ttl", "?max_retries"]
}
```

**Implementation**:
```python
@app.post("/sessions/{session_id}/forward", response_model=ForwardModeResponse)
@limiter.limit("10/minute")  # Rate limit
async def execute_forward_mode(
    session_id: str,
    request: ForwardModeRequest,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks
) -> ForwardModeResponse:
    """Execute Forward Mode: NL → IR → Code."""

    # Authentication & authorization
    user_id = await verify_token(creds.credentials)
    session = await load_and_authorize_session(db, session_id, user_id)

    # Start latency timer
    start_time = time.time()

    # Execute Forward Mode pipeline
    try:
        # Stage 1: Intent Extraction
        intent_spec = await extract_intent(
            prompt=request.prompt,
            context=session.project_context
        )

        # Stage 2: Signature Generation
        signature = await generate_signature(
            intent_spec=intent_spec,
            target_lang=request.target_language or session.target_language
        )

        # Stage 3: Constraint Extraction
        func_spec = await extract_constraints(
            intent_spec=intent_spec,
            signature=signature
        )

        # Stage 4: Hole Detection
        holes = await detect_holes(intent_spec, func_spec)

        # Build IR
        ir_program = await assemble_ir(
            intent_spec=intent_spec,
            func_spec=func_spec,
            holes=holes
        )

        # Stage 5: Code Generation (only if no holes)
        code = None
        validation_result = None

        if not holes:
            code = await generate_code(
                ir_program=ir_program,
                target_lang=request.target_language or session.target_language,
                max_refinements=request.max_refinements
            )

            # Stage 6: Validation
            validation_result = await validate_code(code, ir_program)
        else:
            validation_result = ValidationResult(
                compilation_success=False,
                type_check_success=False,
                execution_success=False,
                smt_satisfiable=True,
                errors=[f"Cannot generate code with {len(holes)} open holes"],
                warnings=[f"{len(holes)} holes require resolution"]
            )

        # Calculate metrics
        latency_ms = int((time.time() - start_time) * 1000)
        cost_usd = calculate_cost(latency_ms, request.prompt)

        # Update session
        session.status = SessionStatus.refining if holes else SessionStatus.finalized
        session.current_ir_snapshot = ir_program
        session.updated_at = datetime.utcnow()
        await db.commit()

        # Save holes to database
        for hole_id in holes:
            await save_hole(db, session_id, hole_id)

        # Broadcast WebSocket update
        background_tasks.add_task(
            broadcast_session_update,
            session_id,
            event_type="forward_complete",
            data={"code": code, "holes": holes}
        )

        return ForwardModeResponse(
            session_id=session_id,
            intent_spec=intent_spec,
            ir_program=ir_program,
            code=code,
            validation=validation_result,
            refinement_iterations=request.max_refinements,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            holes=[h.hole_id for h in holes]
        )

    except Exception as e:
        # Error handling
        await log_error(
            event_type="forward_mode_error",
            session_id=session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Forward mode execution failed: {str(e)}"
        )
```

**Rate Limit**:
- Free tier: 10/minute
- Pro tier: 50/minute
- Enterprise: Custom

---

## 5. Reverse Mode Endpoints

### 5.1 Execute Reverse Mode

**Endpoint**: `POST /sessions/{session_id}/reverse`

**Description**: Execute Reverse Mode: Code → IR → IntentSpec + FuncSpec.

**Request**:
```json
{
  "code": "def transfer(sender_id: UUID, recipient_id: UUID, amount: int, idempotency_key: Optional[str] = None) -> Result[Transfer, TransferError]:\n    assert amount > 0, \"Amount must be positive\"\n    assert sender_id != recipient_id, \"Cannot transfer to self\"\n    # ... implementation ...",
  "language": "python",
  "extract_intent": true,
  "run_security_analysis": true
}
```

**Response**: `200 OK`
```json
{
  "session_id": "ses_x9y8z7",
  "ir_program": {
    "version": "0.9",
    "clauses": [...]
  },
  "intent_spec": {
    "summary": "Transfer money between user accounts atomically",
    "user_personas": ["Sender", "Recipient", "System"],
    "success_criteria": [
      "Transfer succeeds if sender has sufficient balance",
      "Transfer is atomic (all-or-nothing)",
      "All transfers logged for audit"
    ],
    "domain_concepts": ["Account", "Transfer", "Balance", "AuditLog"],
    "goals": [
      "Debit sender account",
      "Credit recipient account",
      "Create audit trail",
      "Ensure idempotency"
    ],
    "constraints": [
      "sender != recipient",
      "sender.balance >= amount",
      "amount > 0",
      "idempotency_key uniqueness enforced"
    ]
  },
  "func_spec": {
    "preconditions": [
      "sender exists",
      "recipient exists",
      "sender.balance >= amount",
      "amount > 0",
      "sender != recipient"
    ],
    "postconditions": [
      "sender.balance' = sender.balance - amount",
      "recipient.balance' = recipient.balance + amount",
      "transfer record created",
      "idempotent: same key → same result"
    ],
    "invariants": [
      "total_balance unchanged",
      "balance never negative"
    ],
    "effects": {
      "Database": [
        "Read: accounts table",
        "Write: accounts table",
        "Write: transfers table"
      ]
    }
  },
  "explanation": "This function implements an atomic money transfer between two accounts. It validates inputs (positive amount, different accounts), checks sender balance, performs the transfer within a transaction, and logs it for audit purposes. The idempotency_key parameter prevents duplicate transfers from retry attempts.",
  "security_findings": [
    {
      "severity": "medium",
      "category": "Race Condition",
      "message": "Potential race condition in balance check without row-level locking",
      "location": {"line": 15, "column": 8},
      "remediation": "Use SELECT ... FOR UPDATE to lock rows during transaction"
    }
  ],
  "analysis": {
    "call_graph": ["validate_account", "create_audit_log", "send_notification"],
    "cyclomatic_complexity": 5,
    "dependencies": ["uuid", "datetime", "sqlalchemy"]
  },
  "holes": [
    "?notification_strategy",
    "?retry_policy"
  ],
  "latency_ms": 8500
}
```

**Implementation**:
```python
@app.post("/sessions/{session_id}/reverse", response_model=ReverseModeResponse)
@limiter.limit("20/minute")
async def execute_reverse_mode(
    session_id: str,
    request: ReverseModeRequest,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> ReverseModeResponse:
    """Execute Reverse Mode: Code → IR → Specs."""

    user_id = await verify_token(creds.credentials)
    session = await load_and_authorize_session(db, session_id, user_id)

    start_time = time.time()

    # Parse code to AST
    ast_tree = await parse_code(request.code, request.language)

    # Extract signature and structure
    signature = await extract_signature(ast_tree)

    # Infer FuncSpec from code patterns
    func_spec = await infer_funcspec(
        ast_tree=ast_tree,
        signature=signature
    )

    # Extract IntentSpec (AI-assisted)
    intent_spec = None
    if request.extract_intent:
        intent_spec = await extract_intent_from_code(
            code=request.code,
            func_spec=func_spec,
            language=request.language
        )

    # Security analysis
    security_findings = []
    if request.run_security_analysis:
        security_findings = await run_codeql_analysis(
            code=request.code,
            language=request.language
        )

    # Build IR
    ir_program = await code_to_ir(
        ast_tree=ast_tree,
        signature=signature,
        func_spec=func_spec,
        intent_spec=intent_spec
    )

    # Detect holes (ambiguities)
    holes = await detect_holes_in_ir(ir_program)

    # Generate explanation
    explanation = await explain_code(
        code=request.code,
        intent_spec=intent_spec,
        func_spec=func_spec
    )

    # Analyze code structure
    analysis = {
        "call_graph": await build_call_graph(ast_tree),
        "cyclomatic_complexity": calculate_complexity(ast_tree),
        "dependencies": extract_imports(ast_tree)
    }

    latency_ms = int((time.time() - start_time) * 1000)

    # Update session
    session.current_ir_snapshot = ir_program
    session.status = SessionStatus.refining if holes else SessionStatus.finalized
    session.updated_at = datetime.utcnow()
    await db.commit()

    return ReverseModeResponse(
        session_id=session_id,
        ir_program=ir_program,
        intent_spec=intent_spec,
        func_spec=func_spec,
        explanation=explanation,
        security_findings=security_findings,
        analysis=analysis,
        holes=[h.hole_id for h in holes],
        latency_ms=latency_ms
    )
```

**Rate Limit**:
- Free tier: 20/minute
- Pro tier: 100/minute
- Enterprise: Custom

---

## 6. IR Operations Endpoints

### 6.1 Validate IR

**Endpoint**: `POST /sessions/{session_id}/ir/validate`

**Description**: Validate IR program (type check + SMT verification).

**Request**:
```json
{
  "ir_program": {
    "version": "0.9",
    "clauses": [...]
  },
  "smt_timeout_seconds": 5
}
```

**Response**: `200 OK` (valid)
```json
{
  "valid": true,
  "type_check_passed": true,
  "smt_satisfiable": true,
  "errors": [],
  "counterexample": null
}
```

**Response**: `200 OK` (invalid - UNSAT constraints)
```json
{
  "valid": false,
  "type_check_passed": true,
  "smt_satisfiable": false,
  "errors": [
    "Constraint contradiction: x > 10 AND x < 5"
  ],
  "counterexample": {
    "explanation": "No value of x can satisfy both x > 10 and x < 5",
    "conflicting_constraints": [
      "requires x > 10",
      "ensures x < 5"
    ]
  }
}
```

**Implementation**:
```python
@app.post("/sessions/{session_id}/ir/validate",
          response_model=IRValidationResponse)
@limiter.limit("100/minute")
async def validate_ir(
    session_id: str,
    request: ValidateIRRequest,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> IRValidationResponse:
    """Validate IR program."""

    user_id = await verify_token(creds.credentials)
    await load_and_authorize_session(db, session_id, user_id)

    # Parse IR
    ir = parse_ir(request.ir_program)

    # Type check
    type_errors = await type_check_ir(ir)
    type_check_passed = len(type_errors) == 0

    # SMT verification (only if type check passes)
    smt_result = None
    counterexample = None

    if type_check_passed:
        smt_result = await verify_constraints(
            ir,
            timeout_seconds=request.smt_timeout_seconds
        )

        if not smt_result.satisfiable:
            counterexample = {
                "explanation": smt_result.explanation,
                "conflicting_constraints": smt_result.conflicts
            }

    return IRValidationResponse(
        valid=type_check_passed and (smt_result.satisfiable if smt_result else True),
        type_check_passed=type_check_passed,
        smt_satisfiable=smt_result.satisfiable if smt_result else None,
        errors=type_errors + (smt_result.errors if smt_result else []),
        counterexample=counterexample
    )
```

**Rate Limit**:
- Free: 100/minute
- Pro: 500/minute
- Enterprise: Custom

---

### 6.2 Refine IR

**Endpoint**: `POST /sessions/{session_id}/ir/refine`

**Description**: Refine IR based on feedback (e.g., compilation errors, user corrections).

**Request**:
```json
{
  "feedback": "Code failed to compile: IndentationError on line 12",
  "refinement_strategy": "deterministic_repair"
}
```

**Response**: `200 OK`
```json
{
  "refined_ir": {...},
  "changes": [
    {
      "location": "line 12",
      "before": "if condition:",
      "after": "    if condition:",
      "reason": "Fixed indentation (expected 4 spaces)"
    }
  ],
  "validation": {
    "compilation_success": true,
    "errors": []
  }
}
```

**Implementation**: Similar to validate endpoint with IR mutation logic.

**Rate Limit**: 50/minute

---

## 7. Hole Management Endpoints

### 7.1 List Holes

**Endpoint**: `GET /sessions/{session_id}/holes`

**Description**: List all holes in session with optional filtering.

**Query Parameters**:
- `status` (optional): Filter by hole status (open, closed, blocked, conflict)
- `kind` (optional): Filter by hole kind (term, type, spec, entity, function, module)

**Response**: `200 OK`
```json
{
  "holes": [
    {
      "hole_id": "?notification_channel",
      "kind": "term",
      "status": "open",
      "type_constraint": "Set[Channel]",
      "constraints": ["at_least_one", "all_valid_channels"],
      "provenance": "Ambiguous prompt: 'send notifications' - channel not specified",
      "dependencies": ["?retry_strategy", "?rate_limit"],
      "created_at": "2025-10-21T10:05:00Z",
      "closed_at": null
    },
    {
      "hole_id": "?max_retries",
      "kind": "term",
      "status": "closed",
      "type_constraint": "{x: int | x > 0}",
      "constraints": ["positive_integer"],
      "provenance": "Retry count not specified",
      "dependencies": [],
      "created_at": "2025-10-21T10:05:00Z",
      "closed_at": "2025-10-21T10:12:00Z"
    }
  ],
  "total": 2,
  "critical_path": ["?notification_channel", "?retry_strategy", "?max_retries"]
}
```

**Implementation**:
```python
@app.get("/sessions/{session_id}/holes", response_model=ListHolesResponse)
@limiter.limit("100/minute")
async def list_holes(
    session_id: str,
    status: Optional[HoleStatus] = None,
    kind: Optional[HoleKind] = None,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> ListHolesResponse:
    """List holes in session."""

    user_id = await verify_token(creds.credentials)
    await load_and_authorize_session(db, session_id, user_id)

    # Build query
    query = select(Hole).where(Hole.session_id == session_id)

    if status:
        query = query.where(Hole.status == status)
    if kind:
        query = query.where(Hole.kind == kind)

    # Execute
    result = await db.execute(query)
    holes = result.scalars().all()

    # Compute critical path
    critical_path = await compute_critical_path(holes)

    return ListHolesResponse(
        holes=[hole_to_response(h) for h in holes],
        total=len(holes),
        critical_path=[h.hole_id for h in critical_path]
    )
```

**Rate Limit**: 100/minute

---

### 7.2 Close Hole

**Endpoint**: `POST /sessions/{session_id}/holes/{hole_id}/close`

**Description**: Close hole with provided term, propagate constraints to dependents.

**Request**:
```json
{
  "closure_term": "{Email, Push}",
  "resolution_type": "clarify_intent"
}
```

**Response**: `200 OK`
```json
{
  "hole_id": "?notification_channel",
  "status": "closed",
  "propagated_updates": [
    {
      "hole_id": "?retry_strategy",
      "change": "narrowed",
      "before_constraints": ["any_strategy"],
      "after_constraints": ["email_retry", "push_retry"],
      "suggestions_updated": true
    },
    {
      "hole_id": "?rate_limit",
      "change": "updated",
      "before_constraints": ["positive_integer"],
      "after_constraints": ["{email: 100/min, push: 50/min}"]
    }
  ],
  "validation_result": {
    "compilation_success": true,
    "type_check_success": true,
    "execution_success": true,
    "smt_satisfiable": true,
    "errors": [],
    "warnings": []
  }
}
```

**Response**: `409 Conflict` (constraint violation)
```json
{
  "error": "Constraint violation",
  "details": [
    {
      "field": "closure_term",
      "message": "Value '{SMS}' violates type constraint Set[Channel] where Channel in {Email, Push, HTTP}",
      "error_code": "CONSTRAINT_VIOLATION"
    }
  ],
  "request_id": "req_abc123",
  "timestamp": "2025-10-21T10:15:00Z"
}
```

**Implementation**:
```python
@app.post("/sessions/{session_id}/holes/{hole_id}/close",
          response_model=CloseHoleResponse)
@limiter.limit("50/minute")
async def close_hole(
    session_id: str,
    hole_id: str,
    request: CloseHoleRequest,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks
) -> CloseHoleResponse:
    """Close hole with provided term."""

    user_id = await verify_token(creds.credentials)
    session = await load_and_authorize_session(db, session_id, user_id)

    # Load hole
    hole = await db.get(Hole, hole_id)
    if not hole or hole.session_id != session_id:
        raise HTTPException(status_code=404, detail="Hole not found")

    if hole.status == HoleStatus.closed:
        raise HTTPException(status_code=409, detail="Hole already closed")

    # Validate closure term
    try:
        term = parse_term(request.closure_term)
    except SyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid closure term syntax: {e}"
        )

    # Type check
    if not type_matches(term, hole.type_constraint):
        raise HTTPException(
            status_code=409,
            detail=f"Type mismatch: {term} does not match {hole.type_constraint}"
        )

    # Constraint check
    constraint_violations = await check_constraints(term, hole.constraints)
    if constraint_violations:
        raise HTTPException(
            status_code=409,
            detail=f"Constraint violation: {constraint_violations[0]}"
        )

    # Close hole
    hole.status = HoleStatus.closed
    hole.closed_at = datetime.utcnow()
    hole.closure_term = request.closure_term

    # Propagate constraints to dependent holes
    propagated_updates = await propagate_constraints(
        db=db,
        source_hole=hole,
        closure_term=term
    )

    # Update IR in session
    session.current_ir_snapshot = await update_ir_with_closure(
        ir=session.current_ir_snapshot,
        hole_id=hole_id,
        term=term
    )

    # Re-validate IR
    validation_result = await validate_ir_program(session.current_ir_snapshot)

    await db.commit()

    # Broadcast WebSocket update
    background_tasks.add_task(
        broadcast_session_update,
        session_id,
        event_type="hole_closed",
        data={
            "hole_id": hole_id,
            "propagated_updates": propagated_updates
        }
    )

    return CloseHoleResponse(
        hole_id=hole_id,
        status=HoleStatus.closed,
        propagated_updates=propagated_updates,
        validation_result=validation_result
    )
```

**Rate Limit**: 50/minute

---

### 7.3 Get Hole Suggestions

**Endpoint**: `GET /sessions/{session_id}/holes/{hole_id}/suggestions`

**Description**: Get AI-generated suggestions for filling hole.

**Response**: `200 OK`
```json
{
  "hole_id": "?notification_channel",
  "suggestions": [
    {
      "value": "{Email, Push}",
      "confidence": 0.90,
      "rationale": "80% of notification systems use Email and Push channels",
      "constraints_satisfied": true,
      "impact": "Narrows ?retry_strategy to 1 option (email_retry)"
    },
    {
      "value": "{Email}",
      "confidence": 0.70,
      "rationale": "Email-only is common for simpler notification systems",
      "constraints_satisfied": true,
      "impact": null
    },
    {
      "value": "{SMS, Email, Push}",
      "confidence": 0.60,
      "rationale": "Full multi-channel support for complex systems",
      "constraints_satisfied": true,
      "impact": "Increases ?rate_limit complexity (3 channels)"
    }
  ],
  "generated_at": "2025-10-21T10:15:00Z"
}
```

**Implementation**:
```python
@app.get("/sessions/{session_id}/holes/{hole_id}/suggestions",
         response_model=HoleSuggestionsResponse)
@limiter.limit("100/minute")
async def get_hole_suggestions(
    session_id: str,
    hole_id: str,
    limit: int = Query(10, ge=1, le=50),
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> HoleSuggestionsResponse:
    """Get AI suggestions for hole."""

    user_id = await verify_token(creds.credentials)
    session = await load_and_authorize_session(db, session_id, user_id)

    # Load hole
    hole = await db.get(Hole, hole_id)
    if not hole or hole.session_id != session_id:
        raise HTTPException(status_code=404, detail="Hole not found")

    # Generate suggestions
    suggestions = await generate_hole_suggestions(
        hole=hole,
        session=session,
        limit=limit
    )

    return HoleSuggestionsResponse(
        hole_id=hole_id,
        suggestions=suggestions,
        generated_at=datetime.utcnow()
    )
```

**Rate Limit**: 100/minute

---

## 8. Authentication & Authorization

### 8.1 JWT Token Structure

**Token Format**: JWT (JSON Web Token) signed with HS256

**Claims**:
```json
{
  "sub": "usr_xyz789",
  "email": "user@example.com",
  "tier": "pro",
  "scopes": ["sessions:read", "sessions:write", "forward:execute", "reverse:execute"],
  "iat": 1698156000,
  "exp": 1698242400
}
```

**Implementation**:
```python
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

def create_access_token(user_id: str, email: str, tier: str) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "scopes": get_scopes_for_tier(tier),
        "iat": datetime.utcnow(),
        "exp": expire
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(token: str) -> str:
    """Verify JWT token and return user_id."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )

        return user_id

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )
```

### 8.2 Authorization Scopes

**Scope-Based Access Control**:

| Scope | Description | Free | Pro | Enterprise |
|-------|-------------|------|-----|------------|
| `sessions:read` | View own sessions | ✓ | ✓ | ✓ |
| `sessions:write` | Create/delete sessions | ✓ | ✓ | ✓ |
| `forward:execute` | Execute Forward Mode | ✓ | ✓ | ✓ |
| `reverse:execute` | Execute Reverse Mode | ✓ | ✓ | ✓ |
| `ir:validate` | Validate IR programs | ✓ | ✓ | ✓ |
| `holes:manage` | Close holes, get suggestions | ✓ | ✓ | ✓ |
| `admin:sessions` | View all users' sessions | ✗ | ✗ | ✓ |
| `admin:metrics` | Access system metrics | ✗ | ✗ | ✓ |

**Scope Checking**:
```python
from fastapi import Security
from fastapi.security import SecurityScopes

async def verify_scopes(
    security_scopes: SecurityScopes,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify token has required scopes."""

    user_id = await verify_token(creds.credentials)
    payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    token_scopes = payload.get("scopes", [])

    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scope: {scope}"
            )

    return user_id

# Usage in endpoint
@app.post("/sessions/{session_id}/forward")
async def execute_forward_mode(
    session_id: str,
    request: ForwardModeRequest,
    user_id: str = Security(verify_scopes, scopes=["forward:execute"])
):
    # user_id is authenticated and authorized
    ...
```

### 8.3 Row-Level Security

**Database RLS**: Supabase PostgreSQL policies enforce user isolation

```sql
-- Sessions table RLS
CREATE POLICY "Users can view own sessions"
  ON sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own sessions"
  ON sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
  ON sessions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
  ON sessions FOR DELETE
  USING (auth.uid() = user_id);
```

---

## 9. Rate Limiting

### 9.1 Redis-Backed Rate Limiter

**Implementation**:
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

# Initialize on startup
@app.on_event("startup")
async def startup():
    redis_client = redis.from_url(
        os.getenv("REDIS_URL"),
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis_client)

# Apply to endpoints
@app.post("/sessions/{session_id}/forward")
@limiter.limit("10/minute")  # Free tier
async def execute_forward_mode(...):
    ...
```

### 9.2 Tiered Rate Limits

**Rate Limit Matrix**:

| Endpoint | Free | Pro | Enterprise |
|----------|------|-----|------------|
| **Session Management** |
| `POST /sessions` | 10/min | 50/min | Custom |
| `GET /sessions` | 100/min | 500/min | Custom |
| `GET /sessions/{id}` | 100/min | 500/min | Custom |
| `DELETE /sessions/{id}` | 50/min | 200/min | Custom |
| **Forward Mode** |
| `POST /sessions/{id}/forward` | 10/min | 50/min | Custom |
| **Reverse Mode** |
| `POST /sessions/{id}/reverse` | 20/min | 100/min | Custom |
| **IR Operations** |
| `POST /sessions/{id}/ir/validate` | 100/min | 500/min | Custom |
| `POST /sessions/{id}/ir/refine` | 50/min | 200/min | Custom |
| **Hole Management** |
| `GET /sessions/{id}/holes` | 100/min | 500/min | Custom |
| `POST /sessions/{id}/holes/{hole_id}/close` | 50/min | 200/min | Custom |
| `GET /sessions/{id}/holes/{hole_id}/suggestions` | 100/min | 500/min | Custom |

### 9.3 Dynamic Rate Limiting

**Tier-Based Limits**:
```python
def get_rate_limit_for_tier(tier: str, endpoint: str) -> str:
    """Get rate limit string for user tier."""

    limits = {
        "free": {
            "forward": "10/minute",
            "reverse": "20/minute",
            "validate": "100/minute",
        },
        "pro": {
            "forward": "50/minute",
            "reverse": "100/minute",
            "validate": "500/minute",
        },
        "enterprise": {
            "forward": "1000/minute",
            "reverse": "2000/minute",
            "validate": "5000/minute",
        }
    }

    return limits.get(tier, limits["free"]).get(endpoint)

@app.post("/sessions/{session_id}/forward")
async def execute_forward_mode(
    session_id: str,
    request: ForwardModeRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
):
    # Extract tier from token
    payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    tier = payload.get("tier", "free")

    # Apply dynamic rate limit
    limit = get_rate_limit_for_tier(tier, "forward")
    await check_rate_limit(creds.credentials, limit)

    # Continue with request...
```

### 9.4 Rate Limit Headers

**Response Headers**:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1698156060
```

**429 Response**:
```json
{
  "error": "Rate limit exceeded",
  "details": [
    {
      "message": "Forward mode limit: 10 requests per minute",
      "error_code": "RATE_LIMIT_EXCEEDED"
    }
  ],
  "retry_after": 42,
  "request_id": "req_abc123",
  "timestamp": "2025-10-21T10:15:00Z"
}
```

---

## 10. Versioning Strategy

### 10.1 URL Versioning

**Current Version**: v1

**Base URLs**:
- Production: `https://api.lift.dev/v1`
- Staging: `https://staging.api.lift.dev/v1`

**Version in Path**: `/v1/sessions`, `/v2/sessions` (future)

### 10.2 API Evolution Strategy

**Breaking Changes**: Require new version (v2, v3, etc.)

Examples:
- Removing endpoints
- Changing required parameters
- Modifying response schemas (removing fields)

**Non-Breaking Changes**: Same version

Examples:
- Adding optional parameters
- Adding new endpoints
- Adding fields to responses
- Deprecating (but not removing) endpoints

### 10.3 Deprecation Policy

**Deprecation Timeline**:
1. **Announce**: Deprecation notice in API docs + response headers
2. **Grace Period**: 6 months of parallel support
3. **Sunset**: Old version removed, only new version available

**Deprecation Headers**:
```http
Deprecation: true
Sunset: Sat, 31 Oct 2026 23:59:59 GMT
Link: <https://docs.lift.dev/api/migration/v1-to-v2>; rel="deprecation"
```

**Example Migration Path**:
```
2025-10-21: v1 released
2026-04-21: v2 released, v1 deprecated (6-month notice)
2026-10-21: v1 sunset, v2 only
```

### 10.4 Backward Compatibility

**IR Versioning**: IR includes version field
```json
{
  "version": "0.9",
  "clauses": [...]
}
```

**Version Negotiation**:
```python
@app.post("/sessions/{session_id}/forward")
async def execute_forward_mode(
    session_id: str,
    request: ForwardModeRequest,
    api_version: str = Header("v1", alias="X-API-Version")
):
    if api_version == "v1":
        # v1 logic
        ...
    elif api_version == "v2":
        # v2 logic (future)
        ...
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {api_version}"
        )
```

---

## 11. Error Handling

### 11.1 Error Response Format

**Standard Structure**:
```json
{
  "error": "High-level error message",
  "details": [
    {
      "field": "prompt",
      "message": "Prompt cannot be empty",
      "error_code": "VALIDATION_ERROR"
    }
  ],
  "request_id": "req_abc123xyz",
  "timestamp": "2025-10-21T10:15:00Z"
}
```

### 11.2 Error Codes

**Error Code Taxonomy**:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `AUTHENTICATION_ERROR` | 401 | Missing/invalid auth token |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Session/hole not found |
| `CONSTRAINT_VIOLATION` | 409 | Constraint check failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SMT_TIMEOUT` | 422 | SMT solver timeout |
| `SMT_UNSAT` | 422 | Constraints unsatisfiable |
| `COMPILATION_ERROR` | 422 | Code compilation failed |
| `TYPE_ERROR` | 422 | Type checking failed |
| `INTERNAL_ERROR` | 500 | Server-side error |
| `SERVICE_UNAVAILABLE` | 503 | Temporary outage |

### 11.3 Validation Errors

**Pydantic Validation**:
```json
{
  "error": "Validation error",
  "details": [
    {
      "field": "prompt",
      "message": "ensure this value has at least 1 characters",
      "error_code": "VALIDATION_ERROR"
    },
    {
      "field": "max_refinements",
      "message": "ensure this value is less than or equal to 10",
      "error_code": "VALIDATION_ERROR"
    }
  ],
  "request_id": "req_abc123",
  "timestamp": "2025-10-21T10:15:00Z"
}
```

### 11.4 Constraint Violation Errors

**SMT UNSAT Example**:
```json
{
  "error": "Constraint violation",
  "details": [
    {
      "message": "Constraints are unsatisfiable: x > 10 AND x < 5",
      "error_code": "SMT_UNSAT"
    }
  ],
  "counterexample": {
    "explanation": "No value of x can satisfy both constraints",
    "conflicting_constraints": [
      "requires x > 10 (line 5)",
      "ensures x < 5 (line 12)"
    ],
    "suggested_fix": "Relax constraint to: x > 5 AND x < 10"
  },
  "request_id": "req_abc123",
  "timestamp": "2025-10-21T10:15:00Z"
}
```

### 11.5 Error Logging & Monitoring

**Structured Logging**:
```python
import structlog

logger = structlog.get_logger()

@app.post("/sessions/{session_id}/forward")
async def execute_forward_mode(...):
    try:
        result = await forward_mode.execute(...)

        logger.info(
            "forward_mode_success",
            session_id=session_id,
            user_id=user_id,
            latency_ms=result.latency_ms,
            cost_usd=result.cost_usd
        )

        return result

    except Exception as e:
        logger.error(
            "forward_mode_error",
            session_id=session_id,
            user_id=user_id,
            error=str(e),
            traceback=traceback.format_exc()
        )

        raise HTTPException(
            status_code=500,
            detail="Forward mode execution failed"
        )
```

**Monitoring Integration**: Honeycomb, Datadog, or Sentry

---

## 12. OpenAPI/Swagger Documentation

### 12.1 Automatic Documentation

**FastAPI Auto-Generation**:

- **Swagger UI**: `https://api.lift.dev/docs`
- **ReDoc**: `https://api.lift.dev/redoc`
- **OpenAPI JSON**: `https://api.lift.dev/openapi.json`

### 12.2 Custom Documentation Metadata

**Enhanced Endpoint Docs**:
```python
@app.post(
    "/sessions/{session_id}/forward",
    response_model=ForwardModeResponse,
    summary="Execute Forward Mode",
    description="""
    Execute the Forward Mode pipeline: Natural Language → IR → Code.

    This endpoint:
    1. Extracts intent from natural language prompt
    2. Generates function signature
    3. Infers constraints (pre/post conditions)
    4. Detects typed holes for ambiguities
    5. Generates verified code (if no holes remain)

    **Rate Limits**:
    - Free tier: 10/minute
    - Pro tier: 50/minute
    - Enterprise: Custom

    **Latency**: Median ~16s (P95 ~25s)

    **Cost**: ~$0.003 per request
    """,
    response_description="Forward mode execution result with IR and code",
    tags=["Forward Mode"],
    responses={
        200: {
            "description": "Successful execution",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "ses_abc123",
                        "code": "def validate_email(email: str): ...",
                        "holes": []
                    }
                }
            }
        },
        400: {"description": "Invalid prompt or parameters"},
        401: {"description": "Authentication failed"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
async def execute_forward_mode(...):
    ...
```

### 12.3 Model Examples

**Pydantic Model Examples**:
```python
class ForwardModeRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="Natural language specification",
        example="Create a REST API endpoint to validate email addresses"
    )
    max_refinements: int = Field(
        3,
        description="Maximum refinement iterations",
        example=3
    )

    class Config:
        schema_extra = {
            "example": {
                "prompt": "Create a function to validate email addresses with MX record checks",
                "max_refinements": 3,
                "target_language": "python"
            }
        }
```

### 12.4 OpenAPI Specification Export

**Complete OpenAPI 3.1 Schema**:
```yaml
openapi: 3.1.0
info:
  title: lift API
  version: 1.0.0
  description: Production-ready API for lift platform
  contact:
    name: lift Support
    email: support@lift.dev
  license:
    name: Proprietary
servers:
  - url: https://api.lift.dev/v1
    description: Production
  - url: https://staging.api.lift.dev/v1
    description: Staging
paths:
  /sessions:
    post:
      summary: Create Session
      operationId: createSession
      tags: [Sessions]
      ...
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    SessionResponse:
      type: object
      required: [session_id, user_id, status, created_at, ws_url]
      properties:
        session_id:
          type: string
          example: ses_abc123
        ...
```

---

## 13. Testing Strategy

### 13.1 API Contract Tests

**Test Pyramid**:
```
           /\
          /  \
         / E2E \         (10%) - Full workflows
        /--------\
       / Integration\    (30%) - API + DB + External services
      /--------------\
     /   Unit Tests   \  (60%) - Business logic, validation
    /------------------\
```

**Contract Testing with pytest**:
```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_session():
    """Test session creation endpoint."""

    # Arrange
    payload = {
        "target_language": "python",
        "project_context": "Test project"
    }

    # Act
    response = client.post(
        "/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {test_token}"}
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["target_language"] == "python"
    assert data["ws_url"].startswith("wss://")

def test_create_session_invalid_input():
    """Test session creation with invalid input."""

    payload = {}  # Missing required fields

    response = client.post(
        "/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "error" in data
    assert "details" in data

def test_forward_mode_success():
    """Test successful forward mode execution."""

    # Create session
    session = create_test_session()

    # Execute forward mode
    payload = {
        "prompt": "Create a function to add two numbers",
        "max_refinements": 3
    }

    response = client.post(
        f"/sessions/{session['session_id']}/forward",
        json=payload,
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert data["validation"]["compilation_success"] is True

def test_rate_limiting():
    """Test rate limiting enforcement."""

    session = create_test_session()

    # Make requests until rate limit hit
    for i in range(15):  # Free tier limit is 10/min
        response = client.post(
            f"/sessions/{session['session_id']}/forward",
            json={"prompt": f"Test {i}"},
            headers={"Authorization": f"Bearer {free_tier_token}"}
        )

        if i < 10:
            assert response.status_code in [200, 202]
        else:
            assert response.status_code == 429
            assert "X-RateLimit-Reset" in response.headers
```

### 13.2 Load Testing

**Locust Load Test**:
```python
from locust import HttpUser, task, between

class LiftAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Create session on user start."""
        response = self.client.post(
            "/sessions",
            json={"target_language": "python"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.session_id = response.json()["session_id"]

    @task(3)
    def execute_forward_mode(self):
        """Forward mode is the most common operation."""
        self.client.post(
            f"/sessions/{self.session_id}/forward",
            json={
                "prompt": "Create a function to calculate factorial",
                "max_refinements": 3
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def list_holes(self):
        """List holes is secondary operation."""
        self.client.get(
            f"/sessions/{self.session_id}/holes",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

**Load Test Targets**:
- 100 concurrent users: P95 latency <25s
- 1000 requests/minute: 0% error rate
- Sustained load (1 hour): No memory leaks

### 13.3 Security Testing

**OWASP Top 10 Coverage**:

1. **Injection**: Input validation with Pydantic, parameterized queries
2. **Broken Authentication**: JWT tokens, secure password hashing
3. **Sensitive Data Exposure**: HTTPS only, encrypted tokens
4. **XML External Entities**: N/A (JSON only)
5. **Broken Access Control**: RLS policies, scope checks
6. **Security Misconfiguration**: Secure defaults, no debug in prod
7. **XSS**: API-only (no HTML rendering)
8. **Insecure Deserialization**: Pydantic validation before processing
9. **Using Components with Known Vulnerabilities**: Dependabot alerts
10. **Insufficient Logging**: Structured logging with request IDs

**Penetration Testing**:
```bash
# SQL injection attempts
curl -X POST https://api.lift.dev/v1/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"target_language": "python; DROP TABLE sessions;--"}'
# Expected: 400 Bad Request (validation error)

# Rate limit bypass attempts
for i in {1..100}; do
  curl -X POST https://api.lift.dev/v1/sessions/$SESSION_ID/forward \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"prompt": "test"}'
done
# Expected: 429 after limit exceeded

# Authorization bypass attempts
curl -X GET https://api.lift.dev/v1/sessions/$OTHER_USER_SESSION \
  -H "Authorization: Bearer $MY_TOKEN"
# Expected: 403 Forbidden
```

### 13.4 Integration Testing

**End-to-End Workflow Test**:
```python
def test_complete_forward_mode_workflow():
    """Test complete Forward Mode workflow from prompt to code."""

    # 1. Create session
    session_response = client.post(
        "/sessions",
        json={"target_language": "python"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]

    # 2. Execute forward mode
    forward_response = client.post(
        f"/sessions/{session_id}/forward",
        json={"prompt": "Create a function to validate email addresses"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert forward_response.status_code == 200
    data = forward_response.json()

    # 3. Check for holes
    if data["holes"]:
        # 4. Get suggestions for first hole
        hole_id = data["holes"][0]
        suggestions_response = client.get(
            f"/sessions/{session_id}/holes/{hole_id}/suggestions",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert suggestions_response.status_code == 200
        suggestions = suggestions_response.json()["suggestions"]
        assert len(suggestions) > 0

        # 5. Close hole with top suggestion
        close_response = client.post(
            f"/sessions/{session_id}/holes/{hole_id}/close",
            json={"closure_term": suggestions[0]["value"]},
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert close_response.status_code == 200

        # 6. Re-execute forward mode
        forward_response = client.post(
            f"/sessions/{session_id}/forward",
            json={"prompt": "Create a function to validate email addresses"},
            headers={"Authorization": f"Bearer {test_token}"}
        )

    # 7. Validate final output
    final_data = forward_response.json()
    assert final_data["code"] is not None
    assert final_data["validation"]["compilation_success"] is True

    # 8. Clean up
    delete_response = client.delete(
        f"/sessions/{session_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert delete_response.status_code == 200
```

---

## Appendix A: WebSocket Protocol

### Connection

**URL**: `wss://api.lift.dev/ws/{session_id}`

**Authentication**: Token in query parameter or header
```javascript
const ws = new WebSocket(
  `wss://api.lift.dev/ws/${sessionId}?token=${authToken}`
);
```

### Message Types

**Client → Server**:
```json
{
  "type": "resolve_hole",
  "hole_id": "?notification_channel",
  "resolution_text": "{Email, Push}"
}
```

**Server → Client**:
```json
{
  "type": "hole_resolved",
  "hole_id": "?notification_channel",
  "timestamp": "2025-10-21T10:15:00Z"
}
```

```json
{
  "type": "constraints_propagated",
  "source_hole_id": "?notification_channel",
  "affected_holes": [
    {
      "hole_id": "?retry_strategy",
      "change": "narrowed",
      "new_constraints": [...]
    }
  ]
}
```

---

## Appendix B: API Client Examples

### Python SDK

```python
from lift_client import LiftClient

client = LiftClient(api_key="your_api_key")

# Create session
session = client.create_session(target_language="python")

# Execute forward mode
result = client.forward_mode(
    session_id=session.session_id,
    prompt="Create a function to validate email addresses"
)

if result.code:
    print(result.code)
else:
    # Resolve holes
    for hole in result.holes:
        suggestions = client.get_hole_suggestions(session.session_id, hole)
        client.close_hole(session.session_id, hole, suggestions[0].value)

    # Re-execute
    result = client.forward_mode(session.session_id, prompt)
    print(result.code)
```

### TypeScript SDK

```typescript
import { LiftClient } from '@lift/client';

const client = new LiftClient({ apiKey: 'your_api_key' });

// Create session
const session = await client.createSession({ targetLanguage: 'python' });

// Execute forward mode
const result = await client.forwardMode({
  sessionId: session.sessionId,
  prompt: 'Create a function to validate email addresses'
});

if (result.code) {
  console.log(result.code);
}
```

### cURL Examples

```bash
# Create session
curl -X POST https://api.lift.dev/v1/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_language": "python"}'

# Execute forward mode
curl -X POST https://api.lift.dev/v1/sessions/$SESSION_ID/forward \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a function to validate email addresses",
    "max_refinements": 3
  }'
```

---

## Appendix C: Migration Guide (Future v2)

**Breaking Changes in v2** (hypothetical):
- Removed `max_refinements` parameter (auto-determined)
- Changed `holes` field from `List[str]` to `List[TypedHole]`
- Required `project_context` in session creation

**Migration Steps**:
1. Update client library to v2
2. Remove `max_refinements` from forward mode calls
3. Handle `holes` as objects instead of strings
4. Add `project_context` to session creation

**Backward Compatibility**:
- v1 endpoints remain available for 6 months
- Clients can specify version via header: `X-API-Version: v1`

---

**Document Status**: Active
**Last Updated**: 2025-10-21
**Next Review**: Quarterly or with major API changes
**Maintained By**: Engineering Team
**Version History**: v1.0 (2025-10-21) - Initial comprehensive API design specification
