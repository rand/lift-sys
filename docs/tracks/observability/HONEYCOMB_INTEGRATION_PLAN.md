# Honeycomb Observability Integration Plan

**Date**: 2025-10-23 (Updated)
**Epic**: Production-Grade Observability with Honeycomb + OpenTelemetry
**Timeline**: 4 days (10 hours total)
**Priority**: P1 (production readiness, not immediate blocker)
**Dependencies**: ✅ Modal deployment, ✅ Supabase integration, ✅ Multi-language generators
**Status**: Ready to implement (infrastructure complete)

---

## Table of Contents

1. [Overview](#overview)
2. [Current State Analysis](#current-state-analysis)
3. [Architecture](#architecture)
4. [OpenTelemetry Integration](#opentelemetry-integration)
5. [Instrumentation Strategy](#instrumentation-strategy)
6. [Implementation Phases](#implementation-phases)
7. [Dashboards & Queries](#dashboards--queries)
8. [Alerting Strategy](#alerting-strategy)
9. [Testing & Validation](#testing--validation)
10. [Deployment Plan](#deployment-plan)
11. [Cost & Performance](#cost--performance)
12. [Success Criteria](#success-criteria)

---

## 0. Current Infrastructure State (2025-10-23)

### What's Changed Since Initial Planning

**Infrastructure Complete**:
- ✅ Modal deployment (Qwen2.5-Coder-32B-Instruct)
- ✅ Supabase database (9 migrations complete)
- ✅ **Multi-language code generation** (TypeScript, Rust, Go, Java)
- ✅ **DSPy meta-framework** (Phase 1, 2, 3, 7 complete)
- ✅ Fixture-based testing (real LLM validation with caching)
- ✅ **TokDrift robustness framework** (Phase 1 complete)

**New Instrumentation Requirements**:
1. **Multi-language code generation** spans (4+ languages, soon 7+)
2. **DSPy optimization** traces (MIPROv2, COPRO experiments)
3. **Robustness testing** metrics (TokDrift sensitivity analysis)
4. **Dual-provider routing** (Best Available vs Modal Inference, per ADR 001)
5. **ExecutionHistory** integration (H11 provides provenance foundation)

**Current Observability Gaps**:
- No distributed tracing across Modal → Supabase → LLM
- No language-specific code generation metrics
- No robustness/quality tracking (TokDrift integration point)
- No DSPy optimization experiment tracking
- No cost attribution per language/provider

---

## 1. Overview

### 1.1 Goal

Implement production-grade observability for lift-sys using **Honeycomb** + **OpenTelemetry** to enable:
- **Real-time debugging** of distributed systems (Modal + Supabase + LLM providers)
- **Performance analysis** (identify slow requests, bottlenecks)
- **Error tracking** (trace failures across service boundaries)
- **Business metrics** (success rates, user behavior, cost tracking)
- **Multi-language quality metrics** (per-language success rates, robustness scores)
- **DSPy optimization tracking** (experiment results, improvements over time)
- **Production readiness** for beta launch

### 1.2 Why Honeycomb

✅ **Built for OpenTelemetry**: Native OTLP support, first-class traces
✅ **High-cardinality queries**: Filter/group by any field combination
✅ **Distributed tracing**: Follow requests across Modal → Supabase → LLMs
✅ **BubbleUp**: Automatic anomaly detection (finds slow/failing patterns)
✅ **SLO tracking**: Built-in Service Level Objectives
✅ **Free tier**: 20M events/month (sufficient for beta)

### 1.3 Key Metrics We'll Track (Updated 2025-10-23)

**Latency**:
- E2E request latency (p50, p90, p95, p99)
- IR generation time
- **Multi-language code generation time** (per language: TypeScript, Rust, Go, Java, Python, Zig, C++)
- Database query time
- LLM provider latency (by provider: Best Available vs Modal Inference)

**Success Rates**:
- **Per-language compilation rate** (TypeScript 80%, Rust 75%, etc.)
- **Per-language execution rate** (track separately for each language)
- Session creation rate
- Hole resolution rate
- **DSPy optimization improvement** (before/after MIPRO)

**Quality Metrics** (NEW):
- **Robustness scores** (TokDrift Phase 2 integration)
  - IR generation sensitivity (% paraphrase variants → non-equivalent IR)
  - Code generation sensitivity (% IR variants → non-equivalent code)
  - Per-language robustness (cross-language consistency)
- **IR quality scores** (from H10 OptimizationMetrics)
- **Code quality scores** (from H10 OptimizationMetrics)
- **Confidence calibration** (from H12 ConfidenceCalibration)

**Errors**:
- LLM failures (rate limit, timeout, invalid response)
- Database errors (connection, query)
- Validation errors (IR, code)
- **Per-language compilation errors** (categorized by language + error type)

**Business Metrics**:
- Active users
- Sessions created/hour
- **Cost per request by language** (TypeScript cheaper than Rust?)
- **Cost per provider** (Best Available vs Modal Inference)
- User satisfaction (session completion rate)
- **Language usage distribution** (which languages are most popular?)

---

## 2. Current State Analysis

### 2.1 Existing Logging

**What exists**:
- Basic Python `logging` module usage
- Print statements in debug scripts
- No structured logging
- No distributed tracing
- No centralized log aggregation

**Where logging happens**:
```
lift_sys/
├── codegen/xgrammar_generator.py (no logging)
├── codegen/validated_generator.py (no logging)
├── validation/ir_interpreter.py (no logging)
├── api/server.py (basic logging.getLogger)
├── providers/*.py (minimal logging)
└── spec_sessions/manager.py (no logging)
```

**Problems**:
- ❌ Can't trace requests across services
- ❌ Can't correlate errors with user actions
- ❌ No performance visibility
- ❌ No alerting on failures
- ❌ Debugging requires log diving

### 2.2 Monitoring Gaps

**Missing**:
1. **Request tracing**: Can't follow NL → IR → Code pipeline
2. **Performance metrics**: No p95/p99 latency tracking
3. **Error rates**: No systematic error tracking
4. **Cost tracking**: No per-request cost visibility
5. **Business metrics**: No session/user analytics

**What this means**:
- Can't debug production issues efficiently
- Can't identify performance bottlenecks
- Can't track success/failure rates
- Can't measure user satisfaction
- Can't optimize costs

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Modal Functions                        │
│                                                          │
│  ┌────────────────┐  OpenTelemetry SDK                  │
│  │ FastAPI Server │  ┌──────────────────┐               │
│  │  (@app.get)    │──│ Auto-instrument  │               │
│  └────────────────┘  │ - HTTP requests  │               │
│                      │ - Database calls │               │
│  ┌────────────────┐  │ - LLM calls      │               │
│  │ Code Generator │──│                  │               │
│  └────────────────┘  └──────────────────┘               │
│                               │                          │
│  ┌────────────────┐          │ Spans & Metrics          │
│  │ Session Mgr    │──────────┤                          │
│  └────────────────┘          │                          │
│                               ▼                          │
│                      ┌──────────────────┐               │
│                      │ OTLP Exporter    │               │
│                      │ (HTTPS/gRPC)     │               │
│                      └──────────────────┘               │
└───────────────────────────────┼──────────────────────────┘
                                │ OTLP over HTTPS
                                ▼
                   ┌────────────────────────┐
                   │   Honeycomb Cloud      │
                   │                        │
                   │  ┌──────────────────┐  │
                   │  │ Trace Storage    │  │
                   │  │ (90 days)        │  │
                   │  └──────────────────┘  │
                   │                        │
                   │  ┌──────────────────┐  │
                   │  │ Query Engine     │  │
                   │  │ (BubbleUp, SLOs) │  │
                   │  └──────────────────┘  │
                   │                        │
                   │  ┌──────────────────┐  │
                   │  │ Dashboards       │  │
                   │  │ + Alerts         │  │
                   │  └──────────────────┘  │
                   └────────────────────────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │ Engineering Team │
                      │ (Web UI)         │
                      └──────────────────┘
```

### 3.2 Data Flow

**Request Journey**:
1. User sends request → FastAPI endpoint
2. OTEL auto-instruments HTTP span
3. SpecSessionManager.create_from_prompt()
   - Manual span: `session.create`
   - Attributes: user_id, prompt_length
4. PromptToIRTranslator.translate()
   - Manual span: `ir.generate`
   - Attributes: provider, model, ir_completeness
   - Supabase query (auto-instrumented)
5. XGrammarCodeGenerator.generate()
   - Manual span: `code.generate`
   - Attributes: ir_constraints, retries, success
   - Modal inference call (manual span)
6. Response returned
   - Span ends with status_code, duration
7. OTLP exporter batches and sends to Honeycomb
8. Honeycomb UI shows full trace tree

**Trace Structure**:
```
POST /api/sessions (root span)
├── session.create (manual)
│   ├── db.insert_session (auto - Supabase)
│   └── ir.generate (manual)
│       ├── llm.call (manual - Anthropic/OpenAI)
│       └── ir.validate (manual)
├── code.generate (manual)
│   ├── modal.inference (manual)
│   ├── ast.repair (manual)
│   └── code.validate (manual)
└── db.update_session (auto - Supabase)
```

### 3.3 Instrumentation Points

**Automatic (via OpenTelemetry)**:
- ✅ HTTP requests/responses (FastAPI)
- ✅ Database queries (Supabase via psycopg/sqlalchemy)
- ✅ Outbound HTTP calls (httpx/requests)

**Manual (custom spans)**:
- ✅ Session operations (create, update, finalize)
- ✅ IR generation (prompt → IR)
- ✅ Code generation (IR → code)
- ✅ LLM provider calls (with token counts)
- ✅ Validation steps (IR, AST, execution)
- ✅ Constraint detection/validation
- ✅ Business events (session_completed, hole_resolved)

---

## 4. OpenTelemetry Integration

### 4.1 Dependencies

```toml
# pyproject.toml additions
[project.dependencies]
opentelemetry-api = "^1.21.0"
opentelemetry-sdk = "^1.21.0"
opentelemetry-exporter-otlp = "^1.21.0"
opentelemetry-instrumentation-fastapi = "^0.42b0"
opentelemetry-instrumentation-httpx = "^0.42b0"
opentelemetry-instrumentation-psycopg2 = "^0.42b0"  # If using Supabase
```

### 4.2 Initialization Code

```python
# lift_sys/observability/__init__.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import os

def setup_observability(service_name: str = "lift-sys"):
    """
    Initialize OpenTelemetry instrumentation for Honeycomb.

    Call this ONCE at application startup (before creating FastAPI app).
    """
    # Skip if already initialized
    if trace.get_tracer_provider() != trace.NoOpTracerProvider():
        return

    # Get Honeycomb API key from environment
    honeycomb_api_key = os.getenv("HONEYCOMB_API_KEY")
    if not honeycomb_api_key:
        print("WARNING: HONEYCOMB_API_KEY not set, telemetry disabled")
        return

    # Configure resource attributes (shows up in Honeycomb UI)
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("LIFT_SYS_VERSION", "dev"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter to Honeycomb
    otlp_exporter = OTLPSpanExporter(
        endpoint="https://api.honeycomb.io:443",
        headers={
            "x-honeycomb-team": honeycomb_api_key,
            "x-honeycomb-dataset": os.getenv("HONEYCOMB_DATASET", "lift-sys"),
        },
    )

    # Use BatchSpanProcessor for better performance
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Auto-instrument HTTP clients
    HTTPXClientInstrumentor().instrument()

    print(f"✓ OpenTelemetry initialized: {service_name}")

def instrument_fastapi_app(app):
    """
    Instrument FastAPI app with automatic request tracing.

    Call this after creating the FastAPI app instance.
    """
    FastAPIInstrumentor.instrument_app(app)
    print("✓ FastAPI instrumentation enabled")

def get_tracer(name: str = "lift-sys"):
    """Get a tracer for manual instrumentation."""
    return trace.get_tracer(name)
```

### 4.3 Application Integration

```python
# lift_sys/api/server.py (modified)
from lift_sys.observability import setup_observability, instrument_fastapi_app

# Initialize BEFORE creating FastAPI app
setup_observability(service_name="lift-sys-api")

app = FastAPI(title="lift-sys API", version="0.1.0")

# Instrument AFTER creating app
instrument_fastapi_app(app)

# ... rest of server setup
```

### 4.4 Manual Span Creation

```python
# lift_sys/spec_sessions/manager.py (example)
from lift_sys.observability import get_tracer

tracer = get_tracer(__name__)

class SpecSessionManager:
    async def create_from_prompt(self, prompt: str, metadata: dict | None = None):
        """Create session with distributed tracing."""
        with tracer.start_as_current_span(
            "session.create",
            attributes={
                "session.prompt_length": len(prompt),
                "session.source": "prompt",
                "session.has_metadata": metadata is not None,
            }
        ) as span:
            # Translate prompt to IR (creates child span)
            draft = await self.translator.translate(prompt, metadata=metadata)

            # Add IR metadata to span
            span.set_attribute("session.ir_version", draft.version)
            span.set_attribute("session.holes_count", len(draft.ambiguities))
            span.set_attribute("session.validation_status", draft.validation_status)

            # Create session (Supabase auto-instrumented)
            session = PromptSession.create_new(...)
            self.store.create(session)

            # Add session ID for correlation
            span.set_attribute("session.id", session.session_id)

            return session
```

---

## 5. Instrumentation Strategy

### 5.1 Instrumentation Pyramid

```
Level 1: Automatic (Zero Code)
├── HTTP requests (FastAPI)
├── Database queries (Supabase)
└── HTTP clients (httpx)

Level 2: Essential Manual (Core Operations)
├── Session lifecycle (create, update, finalize)
├── IR generation (prompt → IR)
├── Code generation (IR → code)
└── LLM provider calls

Level 3: Detailed Manual (Performance Analysis)
├── Constraint detection
├── AST repair
├── Code validation
└── Multishot generation

Level 4: Business Events (Analytics)
├── User sign-up
├── Session completed
├── Hole resolved
└── Error occurred
```

**Implementation Priority**: Level 1 → Level 2 → Level 3 → Level 4

### 5.2 Span Naming Conventions

**Pattern**: `{component}.{operation}`

**Examples**:
- `session.create` - Creating a new session
- `session.update` - Updating session state
- `ir.generate` - Generating IR from prompt
- `code.generate` - Generating code from IR
- `llm.call` - Calling LLM provider
- `db.query` - Database query
- `validation.ir` - Validating IR
- `validation.code` - Validating generated code

### 5.3 Attribute Conventions (Updated 2025-10-23)

**Standard Attributes** (add to all spans):
```python
{
    "user.id": user_id,  # For user-specific filtering
    "request.id": request_id,  # For request correlation
    "environment": "production|staging|dev",
}
```

**Domain-Specific Attributes**:
```python
# Session spans
{
    "session.id": "uuid",
    "session.status": "active|finalized|abandoned",
    "session.holes_count": 3,
    "session.prompt_length": 150,
}

# IR generation spans
{
    "ir.provider": "anthropic|openai|modal",  # Dual-provider routing (ADR 001)
    "ir.provider_route": "best_available|modal_inference",  # NEW
    "ir.model": "claude-3-opus|qwen2.5-coder-32b",
    "ir.completeness": 0.95,
    "ir.constraints_count": 5,
    "ir.validation_status": "valid|incomplete|contradictory",
    "ir.quality_score": 0.87,  # From H10 OptimizationMetrics
}

# Code generation spans (UPDATED for multi-language)
{
    "code.language": "typescript|rust|go|java|python|zig|cpp",  # NEW - critical for per-language metrics
    "code.generator": "TypeScriptGenerator|RustGenerator|...",  # NEW
    "code.retries": 2,
    "code.success": True,
    "code.compilation_success": True,
    "code.execution_success": True,
    "code.lines": 45,
    "code.quality_score": 0.26,  # From H10 OptimizationMetrics
    "code.robustness_score": 0.93,  # From TokDrift Phase 2 (future)
}

# DSPy optimization spans (NEW)
{
    "dspy.optimizer": "miprov2|copro",  # From H8 OptimizationAPI
    "dspy.signature": "IRGenerationSignature",
    "dspy.metric": "ir_quality|code_quality|end_to_end",
    "dspy.improvement": 0.15,  # % improvement from baseline
    "dspy.examples_count": 53,
}

# LLM spans (UPDATED for routing)
{
    "llm.provider": "anthropic|openai|modal",
    "llm.provider_route": "best_available|modal_inference",  # NEW - ADR 001
    "llm.model": "claude-3-opus-20240229|qwen2.5-coder-32b",
    "llm.input_tokens": 1200,
    "llm.output_tokens": 450,
    "llm.cost_usd": 0.0234,
    "llm.latency_ms": 3400,
}

# Robustness testing spans (NEW - TokDrift)
{
    "robustness.test_type": "ir_paraphrase|code_variant",
    "robustness.variant_count": 10,
    "robustness.sensitivity": 0.08,  # % non-equivalent outputs
    "robustness.language": "typescript|rust|go|...",  # For code variants
}

# Database spans
{
    "db.operation": "insert|select|update|delete",
    "db.table": "sessions|holes|func_specs|execution_history",  # Updated tables
    "db.rows_affected": 1,
}
```

### 5.4 Error Handling

```python
# Capture errors in spans
try:
    result = await some_operation()
    span.set_status(Status(StatusCode.OK))
except Exception as e:
    span.set_status(Status(StatusCode.ERROR, str(e)))
    span.record_exception(e)  # Captures stack trace
    raise
```

---

## 6. Implementation Phases

### 6.1 Phase 1: Foundation (Day 1 - 3 hours)

**Tasks**:
1. Add OpenTelemetry dependencies
2. Create `lift_sys/observability/` module
3. Implement initialization code
4. Configure Honeycomb API key (Modal secret)
5. Test basic instrumentation (HTTP requests)
6. Verify traces in Honeycomb UI

**Deliverables**:
- `lift_sys/observability/__init__.py`
- `lift_sys/observability/config.py`
- Honeycomb API key in Modal secrets
- Basic traces visible in Honeycomb

**Acceptance Criteria**:
- ✅ FastAPI requests create traces
- ✅ Traces visible in Honeycomb
- ✅ No performance degradation

**Files**:
- `lift_sys/observability/__init__.py` (~150 lines)
- `lift_sys/observability/config.py` (~50 lines)
- `lift_sys/api/server.py` (modified - add setup calls)

---

### 6.2 Phase 2: Core Instrumentation (Day 2 - 3 hours)

**Tasks**:
1. Instrument Session operations
2. Instrument IR generation
3. Instrument Code generation
4. Instrument LLM provider calls
5. Add span attributes (user_id, session_id, etc.)
6. Test distributed tracing (full request flow)

**Deliverables**:
- Session spans (create, update, finalize)
- IR generation spans
- Code generation spans
- LLM provider spans
- End-to-end trace visibility

**Acceptance Criteria**:
- ✅ Can trace NL → IR → Code pipeline
- ✅ Spans have rich attributes
- ✅ Parent-child relationships correct

**Files**:
- `lift_sys/spec_sessions/manager.py` (modified)
- `lift_sys/forward_mode/synthesizer.py` (modified)
- `lift_sys/codegen/xgrammar_generator.py` (modified)
- `lift_sys/providers/base.py` (add tracing mixin)
- `lift_sys/providers/anthropic_provider.py` (modified)
- `lift_sys/providers/modal_provider.py` (modified)

---

### 6.3 Phase 3: Database & Validation (Day 2-3 - 2 hours)

**Tasks**:
1. Instrument Supabase queries (auto + manual attributes)
2. Instrument validation steps (IR, AST, execution)
3. Instrument constraint detection
4. Add error tracking (exceptions → spans)
5. Test error scenarios

**Deliverables**:
- Database query spans with table/operation
- Validation spans
- Error traces with stack traces

**Acceptance Criteria**:
- ✅ Database queries visible
- ✅ Validation steps traceable
- ✅ Errors captured with context

**Files**:
- `lift_sys/spec_sessions/supabase_storage.py` (modified - add spans)
- `lift_sys/validation/ir_interpreter.py` (modified)
- `lift_sys/validation/code_validator.py` (modified)
- `lift_sys/ir/constraint_validator.py` (modified)

---

### 6.4 Phase 4: Dashboards & Queries (Day 3 - 1.5 hours)

**Tasks**:
1. Create "Request Overview" dashboard
2. Create "Performance Analysis" dashboard
3. Create "Error Tracking" dashboard
4. Create "Business Metrics" dashboard
5. Save key queries (p95 latency, error rate, cost/request)
6. Document dashboard usage

**Deliverables**:
- 4 Honeycomb dashboards
- 10+ saved queries
- Dashboard documentation

**Acceptance Criteria**:
- ✅ Dashboards show key metrics
- ✅ Queries answer common questions
- ✅ Team can navigate dashboards

**Files**:
- `docs/HONEYCOMB_DASHBOARDS.md` (new)
- Dashboards configured in Honeycomb UI (export JSON)

---

### 6.5 Phase 5: Alerting & SLOs (Day 4 - 1.5 hours)

**Tasks**:
1. Define SLOs (p95 latency <10s, success rate >95%)
2. Create alerts (high error rate, slow requests, cost spikes)
3. Configure alert channels (Slack, email)
4. Test alert firing
5. Document runbooks for alerts

**Deliverables**:
- 2 SLOs configured
- 5+ alerts active
- Slack integration working
- Alert runbooks

**Acceptance Criteria**:
- ✅ Alerts fire on test conditions
- ✅ SLOs track target metrics
- ✅ Team notified on Slack

**Files**:
- `docs/HONEYCOMB_ALERTS.md` (new)
- `docs/HONEYCOMB_RUNBOOKS.md` (new)
- Alerts configured in Honeycomb UI

---

## 7. Dashboards & Queries

### 7.1 Dashboard 1: Request Overview

**Purpose**: High-level request health monitoring

**Widgets**:
1. **Request Rate** (line chart)
   - Query: `COUNT() GROUP BY time`
   - Time range: Last 24h

2. **Latency Percentiles** (heatmap)
   - Query: `HEATMAP(duration_ms) GROUP BY time`
   - P50, P90, P95, P99

3. **Success Rate** (line chart)
   - Query: `AVG(http.status_code < 400) GROUP BY time`

4. **Error Rate** (line chart)
   - Query: `AVG(error = true) GROUP BY time`

5. **Top Endpoints** (bar chart)
   - Query: `COUNT() GROUP BY http.route ORDER BY COUNT() DESC`

6. **User Activity** (table)
   - Query: `COUNT() GROUP BY user.id ORDER BY COUNT() DESC LIMIT 10`

### 7.2 Dashboard 2: Performance Analysis

**Purpose**: Identify slow operations and bottlenecks

**Widgets**:
1. **Slowest Operations** (table)
   - Query: `P95(duration_ms) GROUP BY name ORDER BY P95(duration_ms) DESC`

2. **IR Generation Time** (histogram)
   - Query: `HISTOGRAM(duration_ms) WHERE name = "ir.generate"`

3. **Code Generation Time** (histogram)
   - Query: `HISTOGRAM(duration_ms) WHERE name = "code.generate"`

4. **LLM Provider Latency** (line chart)
   - Query: `P95(duration_ms) WHERE name = "llm.call" GROUP BY llm.provider`

5. **Database Query Performance** (table)
   - Query: `P95(duration_ms), COUNT() WHERE name STARTS WITH "db." GROUP BY db.table`

6. **Retry Rate** (line chart)
   - Query: `AVG(code.retries > 0) GROUP BY time`

### 7.3 Dashboard 3: Error Tracking

**Purpose**: Monitor and debug failures

**Widgets**:
1. **Error Rate by Type** (stacked bar)
   - Query: `COUNT() WHERE error = true GROUP BY exception.type`

2. **Failed Operations** (table)
   - Query: `COUNT() WHERE error = true GROUP BY name ORDER BY COUNT() DESC`

3. **Error Distribution** (pie chart)
   - Query: `COUNT() WHERE error = true GROUP BY error.message`

4. **Recent Errors** (table)
   - Query: `*` WHERE error = true ORDER BY time DESC LIMIT 20`
   - Columns: time, trace.trace_id, name, error.message, user.id

5. **Code Generation Failures** (line chart)
   - Query: `AVG(code.success = false) WHERE name = "code.generate" GROUP BY time`

6. **LLM Provider Errors** (stacked area)
   - Query: `COUNT() WHERE name = "llm.call" AND error = true GROUP BY llm.provider`

### 7.4 Dashboard 4: Business Metrics

**Purpose**: Track user behavior and product health

**Widgets**:
1. **Sessions Created** (line chart)
   - Query: `COUNT() WHERE name = "session.create" GROUP BY time`

2. **Session Completion Rate** (line chart)
   - Query: `AVG(session.status = "finalized") GROUP BY time`

3. **Holes Resolved** (line chart)
   - Query: `SUM(session.holes_resolved) GROUP BY time`

4. **Average Holes per Session** (line chart)
   - Query: `AVG(session.holes_count) GROUP BY time`

5. **Cost per Request** (line chart)
   - Query: `AVG(llm.cost_usd) WHERE llm.cost_usd EXISTS GROUP BY time`

6. **Token Usage** (stacked area)
   - Query: `SUM(llm.input_tokens), SUM(llm.output_tokens) GROUP BY time`

### 7.5 Saved Queries

**Query 1: Slow Requests (p95 > 10s)**
```
WHERE duration_ms > 10000
GROUP BY trace.trace_id, http.route, user.id
ORDER BY duration_ms DESC
LIMIT 100
```

**Query 2: High Cost Requests**
```
WHERE llm.cost_usd > 0.05
GROUP BY trace.trace_id, llm.provider, llm.model, user.id
ORDER BY llm.cost_usd DESC
LIMIT 100
```

**Query 3: Failed Code Generations**
```
WHERE name = "code.generate" AND code.success = false
GROUP BY trace.trace_id, code.retries, error.message, session.id
ORDER BY time DESC
LIMIT 100
```

**Query 4: User Success Rate**
```
CALC(
  successful_sessions = COUNT() WHERE session.status = "finalized",
  total_sessions = COUNT(),
  success_rate = successful_sessions / total_sessions
)
GROUP BY user.id
ORDER BY total_sessions DESC
LIMIT 50
```

**Query 5: LLM Provider Comparison**
```
CALC(
  avg_latency = AVG(duration_ms),
  p95_latency = P95(duration_ms),
  error_rate = AVG(error = true),
  avg_cost = AVG(llm.cost_usd)
)
WHERE name = "llm.call"
GROUP BY llm.provider, llm.model
```

---

## 8. Alerting Strategy

### 8.1 Alert Definitions

**Alert 1: High Error Rate**
- **Condition**: Error rate >5% over 5 minutes
- **Query**: `AVG(error = true) > 0.05`
- **Severity**: Critical
- **Channel**: Slack #alerts, PagerDuty
- **Runbook**: HONEYCOMB_RUNBOOKS.md#high-error-rate

**Alert 2: Slow Requests**
- **Condition**: P95 latency >15s over 10 minutes
- **Query**: `P95(duration_ms) > 15000`
- **Severity**: Warning
- **Channel**: Slack #performance
- **Runbook**: HONEYCOMB_RUNBOOKS.md#slow-requests

**Alert 3: LLM Provider Failure**
- **Condition**: >10 LLM errors in 5 minutes
- **Query**: `COUNT() WHERE name = "llm.call" AND error = true > 10`
- **Severity**: Critical
- **Channel**: Slack #alerts
- **Runbook**: HONEYCOMB_RUNBOOKS.md#llm-provider-failure

**Alert 4: Database Connection Failure**
- **Condition**: >5 database errors in 2 minutes
- **Query**: `COUNT() WHERE name STARTS WITH "db." AND error = true > 5`
- **Severity**: Critical
- **Channel**: Slack #alerts, PagerDuty
- **Runbook**: HONEYCOMB_RUNBOOKS.md#database-failure

**Alert 5: Cost Spike**
- **Condition**: Avg cost per request >$0.10 over 1 hour
- **Query**: `AVG(llm.cost_usd) > 0.10`
- **Severity**: Warning
- **Channel**: Slack #cost-alerts
- **Runbook**: HONEYCOMB_RUNBOOKS.md#cost-spike

### 8.2 SLO Definitions

**SLO 1: Request Success Rate**
- **Target**: 95% of requests succeed
- **Measurement**: `AVG(error = false) >= 0.95`
- **Window**: 30 days
- **Budget**: 5% error budget
- **Alert on**: <90% (burning budget too fast)

**SLO 2: Request Latency**
- **Target**: P95 latency <10s
- **Measurement**: `P95(duration_ms) <= 10000`
- **Window**: 30 days
- **Budget**: 5% can exceed
- **Alert on**: P95 >12s

---

## 9. Testing & Validation

### 9.1 Unit Tests

```python
# tests/observability/test_instrumentation.py
import pytest
from opentelemetry import trace
from lift_sys.observability import setup_observability, get_tracer

def test_observability_setup():
    """Test OpenTelemetry initialization."""
    setup_observability("test-service")
    provider = trace.get_tracer_provider()
    assert provider is not None

def test_tracer_creation():
    """Test tracer creation."""
    tracer = get_tracer("test")
    assert tracer is not None

def test_manual_span():
    """Test manual span creation."""
    tracer = get_tracer("test")
    with tracer.start_as_current_span("test.operation") as span:
        span.set_attribute("test.value", 123)
        # Verify span is current
        current_span = trace.get_current_span()
        assert current_span == span
```

### 9.2 Integration Tests

```python
# tests/integration/test_distributed_tracing.py
import pytest
from fastapi.testclient import TestClient
from lift_sys.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_end_to_end_tracing(client):
    """Test full request trace is created."""
    response = client.post("/api/sessions", json={
        "prompt": "Create a function that adds two numbers"
    })

    assert response.status_code == 200

    # Verify trace was created (check Honeycomb API)
    # This would require Honeycomb SDK or API client
    # For now, manual verification in UI

def test_error_tracing(client):
    """Test errors are captured in traces."""
    response = client.post("/api/sessions", json={
        "prompt": ""  # Invalid empty prompt
    })

    assert response.status_code == 400
    # Verify error span in Honeycomb
```

### 9.3 Performance Tests

```python
# tests/performance/test_instrumentation_overhead.py
import time
import pytest
from lift_sys.observability import get_tracer

def test_instrumentation_overhead():
    """Test instrumentation adds minimal overhead."""
    tracer = get_tracer("test")

    # Measure baseline
    start = time.perf_counter()
    for _ in range(1000):
        pass
    baseline = time.perf_counter() - start

    # Measure with instrumentation
    start = time.perf_counter()
    for _ in range(1000):
        with tracer.start_as_current_span("test"):
            pass
    instrumented = time.perf_counter() - start

    overhead = instrumented - baseline
    overhead_pct = (overhead / baseline) * 100

    # Assert overhead <5%
    assert overhead_pct < 5.0, f"Overhead too high: {overhead_pct:.2f}%"
```

---

## 10. Deployment Plan

### 10.1 Pre-Deployment Checklist

- [ ] Honeycomb account created
- [ ] API key generated
- [ ] Dataset created (`lift-sys`)
- [ ] Modal secret configured
- [ ] Dependencies added to pyproject.toml
- [ ] Instrumentation code implemented
- [ ] Unit tests passing
- [ ] Integration tests passing

### 10.2 Deployment Steps

**Step 1: Create Honeycomb Account**
```bash
# Go to https://ui.honeycomb.io/signup
# Choose Free plan (20M events/month)
```

**Step 2: Generate API Key**
```bash
# In Honeycomb UI:
# Settings → Team Settings → API Keys → Create API Key
# Name: "lift-sys-production"
# Copy key (starts with "hcaik_...")
```

**Step 3: Create Dataset**
```bash
# In Honeycomb UI:
# Datasets → Create Dataset
# Name: "lift-sys"
# (Or use environment variable to auto-create)
```

**Step 4: Configure Modal Secrets**
```bash
# Add Honeycomb credentials to Modal
modal secret create honeycomb \
  HONEYCOMB_API_KEY="hcaik_..." \
  HONEYCOMB_DATASET="lift-sys" \
  ENVIRONMENT="production"
```

**Step 5: Add Dependencies**
```bash
uv add opentelemetry-api \
       opentelemetry-sdk \
       opentelemetry-exporter-otlp \
       opentelemetry-instrumentation-fastapi \
       opentelemetry-instrumentation-httpx
```

**Step 6: Deploy to Staging**
```bash
# Deploy Modal app with instrumentation
modal deploy lift_sys/modal_app.py --env staging

# Generate test traffic
curl -X POST https://lift-sys-staging.modal.run/api/sessions \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"prompt": "Test observability"}'
```

**Step 7: Verify in Honeycomb**
```bash
# Check Honeycomb UI for traces
# Should see traces within 30 seconds
```

**Step 8: Deploy to Production**
```bash
modal deploy lift_sys/modal_app.py --env production
```

### 10.3 Post-Deployment Verification

**Checklist**:
- [ ] Traces visible in Honeycomb
- [ ] Spans have correct attributes
- [ ] Parent-child relationships correct
- [ ] No missing spans
- [ ] Latency acceptable (<1% overhead)
- [ ] Error traces captured
- [ ] Dashboards populated
- [ ] Alerts configured
- [ ] Team has access to Honeycomb

---

## 11. Cost & Performance

### 11.1 Honeycomb Pricing

**Free Tier**:
- 20M events/month
- 90-day retention
- Unlimited queries
- Unlimited users

**Pro Tier** ($100/mo):
- 100M events/month
- 365-day retention
- SLOs
- SSO

**Enterprise** (Custom):
- Unlimited events
- Custom retention
- Dedicated support

### 11.2 Event Volume Estimate

**Calculations**:
- Average request creates ~10 spans (HTTP + session + IR + code + DB + LLM)
- 10k requests/month × 10 spans = 100k events/month
- **Well within free tier** (20M events)

**At scale** (100k requests/month):
- 100k requests × 10 spans = 1M events/month
- Still within free tier

**Growth to Pro tier** (2M requests/month):
- 2M requests × 10 spans = 20M events/month
- Hitting free tier limit
- Upgrade to Pro ($100/mo)

### 11.3 Performance Impact

**Instrumentation Overhead**:
- Automatic instrumentation: ~1-2% latency increase
- Manual spans: ~0.1ms per span
- OTLP batching: Async, no blocking

**Example**:
- Baseline request: 10s
- With instrumentation: 10.1s
- **Overhead: 1% (negligible)**

**Mitigation**:
- Batch span export (default 5s batches)
- Async exporter (doesn't block requests)
- Sampling for very high traffic (not needed for beta)

---

## 12. Success Criteria

### 12.1 Functional Requirements

✅ **Distributed Tracing**:
- Can trace requests across Modal → Supabase → LLMs
- Parent-child span relationships correct
- All operations visible (HTTP, DB, LLM)

✅ **Error Tracking**:
- Errors captured with stack traces
- Error rate tracked per operation
- Failed requests debuggable in Honeycomb

✅ **Performance Visibility**:
- p50/p90/p95/p99 latency tracked
- Slow operations identifiable
- Bottlenecks visible

✅ **Business Metrics**:
- Session creation rate tracked
- Success rate tracked
- Cost per request tracked

### 12.2 Non-Functional Requirements

✅ **Low Overhead**:
- <2% latency impact
- No blocking on telemetry export

✅ **Reliability**:
- Telemetry failures don't affect app
- Graceful degradation if Honeycomb down

✅ **Usability**:
- Dashboards answer common questions
- Queries documented
- Runbooks for alerts

✅ **Maintainability**:
- Instrumentation code clean
- Span naming consistent
- Attributes well-documented

### 12.3 Acceptance Criteria

**For Product Owner**:
- [ ] Can see request success rate in dashboard
- [ ] Can debug failed requests with trace ID
- [ ] Can identify slow operations
- [ ] Can track cost per user

**For Engineering**:
- [ ] All tests passing
- [ ] Instrumentation code reviewed
- [ ] Dashboards created
- [ ] Alerts configured
- [ ] Documentation complete

**For Operations**:
- [ ] Alerts fire correctly
- [ ] Runbooks validated
- [ ] Team trained on Honeycomb UI
- [ ] Incident response tested

---

## Appendix A: Code Examples

### A.1 Full Instrumentation Example

```python
# lift_sys/spec_sessions/manager.py
from lift_sys.observability import get_tracer
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode

tracer = get_tracer(__name__)

class SpecSessionManager:
    async def create_from_prompt(
        self,
        prompt: str,
        user_id: str,
        metadata: dict | None = None,
    ) -> PromptSession:
        """Create session with full distributed tracing."""

        # Create root span for this operation
        with tracer.start_as_current_span(
            "session.create",
            attributes={
                "session.prompt_length": len(prompt),
                "session.source": "prompt",
                "user.id": user_id,
            }
        ) as span:
            try:
                # Translate prompt to IR (creates child span)
                with tracer.start_as_current_span(
                    "ir.generate",
                    attributes={"ir.provider": "anthropic"}
                ) as ir_span:
                    draft = await self.translator.translate(prompt, metadata)

                    # Add IR metadata
                    ir_span.set_attribute("ir.version", draft.version)
                    ir_span.set_attribute("ir.holes_count", len(draft.ambiguities))
                    ir_span.set_attribute("ir.validation_status", draft.validation_status)

                # Create session (DB auto-instrumented)
                session = PromptSession.create_new(...)
                session.user_id = user_id
                self.store.create(session)

                # Add final attributes
                span.set_attribute("session.id", session.session_id)
                span.set_attribute("session.holes_count", len(session.holes))
                span.set_status(Status(StatusCode.OK))

                return session

            except Exception as e:
                # Capture error in span
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
```

### A.2 LLM Provider Instrumentation

```python
# lift_sys/providers/anthropic_provider.py
from lift_sys.observability import get_tracer

tracer = get_tracer(__name__)

class AnthropicProvider:
    async def generate(self, prompt: str, **kwargs):
        """Generate with cost tracking."""

        with tracer.start_as_current_span(
            "llm.call",
            attributes={
                "llm.provider": "anthropic",
                "llm.model": self.model,
                "llm.temperature": kwargs.get("temperature", 0.7),
            }
        ) as span:
            response = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            # Add usage metrics
            span.set_attribute("llm.input_tokens", response.usage.input_tokens)
            span.set_attribute("llm.output_tokens", response.usage.output_tokens)

            # Calculate cost (Anthropic pricing)
            input_cost = response.usage.input_tokens * 0.000015  # $15/1M
            output_cost = response.usage.output_tokens * 0.000075  # $75/1M
            total_cost = input_cost + output_cost
            span.set_attribute("llm.cost_usd", total_cost)

            return response.content[0].text
```

---

## 10. Deployment Plan

### 10.1 Pre-Deployment Checklist

**Environment Setup**:
- [ ] Honeycomb account created (free tier supports 20M events/month)
- [ ] API key generated in Honeycomb UI (Settings → API Keys)
- [ ] Dataset created: `lift-sys` (or separate: `lift-sys-dev`, `lift-sys-prod`)
- [ ] Team members added to Honeycomb organization

**Modal Configuration**:
- [ ] Add `HONEYCOMB_API_KEY` to Modal secrets:
  ```bash
  modal secret create honeycomb-secrets \
    HONEYCOMB_API_KEY=<your-api-key>
  ```
- [ ] Add `HONEYCOMB_DATASET` to Modal secrets (optional, can hardcode)
- [ ] Verify secrets accessible in Modal app

**Code Preparation**:
- [ ] OpenTelemetry dependencies added to `pyproject.toml`
- [ ] `lift_sys/observability/` module created
- [ ] Instrumentation code reviewed and tested locally
- [ ] Tests passing with instrumentation enabled

**Documentation**:
- [ ] HONEYCOMB_QUICK_START.md created
- [ ] Team trained on Honeycomb UI navigation
- [ ] Runbooks documented for common alerts

### 10.2 Deployment Steps

**Step 1: Deploy Foundation (Phase 1)**

Deploy observability setup without instrumentation:

```bash
# 1. Install dependencies
uv add opentelemetry-api opentelemetry-sdk \
  opentelemetry-exporter-otlp-proto-grpc \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-httpx \
  opentelemetry-instrumentation-sqlalchemy

# 2. Commit observability module
git add lift_sys/observability/
git commit -m "feat: Add OpenTelemetry and Honeycomb foundation"

# 3. Deploy to Modal
modal deploy lift_sys/api/server.py
```

**Step 2: Enable Auto-Instrumentation (Phase 2)**

Enable FastAPI, HTTP, and DB auto-instrumentation:

```bash
# 1. Update server.py to call setup_observability()
git add lift_sys/api/server.py
git commit -m "feat: Enable OpenTelemetry auto-instrumentation"

# 2. Deploy
modal deploy lift_sys/api/server.py

# 3. Verify in Honeycomb
# - Check for traces appearing in Honeycomb UI
# - Verify service.name = "lift-sys"
# - Verify http.* attributes present
```

**Step 3: Add Core Instrumentation (Phase 3)**

Add manual spans for Session/IR/Code operations:

```bash
# 1. Instrument session operations
git add lift_sys/spec_sessions/
git commit -m "feat: Add session operation instrumentation"

# 2. Instrument IR generation
git add lift_sys/ir/
git commit -m "feat: Add IR generation instrumentation"

# 3. Instrument code generation
git add lift_sys/code_gen/
git commit -m "feat: Add code generation instrumentation"

# 4. Deploy
modal deploy lift_sys/api/server.py
```

**Step 4: Create Dashboards (Phase 4)**

Configure dashboards in Honeycomb UI:

1. Navigate to Honeycomb UI → Boards
2. Create new board: "lift-sys Overview"
3. Add widgets as defined in Section 7.1 (Request Overview)
4. Create additional boards:
   - "lift-sys Performance"
   - "lift-sys Errors"
   - "lift-sys Business Metrics"
5. Export dashboard JSON (Settings → Export)
6. Save to `docs/honeycomb-dashboards.json`

**Step 5: Configure Alerts (Phase 5)**

Create alerts in Honeycomb UI:

1. Navigate to Triggers → Create New Trigger
2. Configure alerts as defined in Section 8
3. Set up Slack integration:
   - Settings → Integrations → Slack
   - Connect workspace
   - Select channel for alerts
4. Test each alert with synthetic data

### 10.3 Verification Steps

**Post-Deployment Verification**:

1. **Traces Flowing**:
   ```bash
   # Make test request
   curl -X POST https://your-modal-app.modal.run/api/sessions \
     -H "Content-Type: application/json" \
     -d '{"prompt": "test"}'

   # Check Honeycomb (within 30 seconds)
   # - Query: WHERE service.name = "lift-sys" | Latest 10
   # - Verify trace appears with http.route = "/api/sessions"
   ```

2. **Span Attributes Complete**:
   ```
   # In Honeycomb, inspect a trace and verify:
   - service.name = "lift-sys"
   - service.version = <git hash or version>
   - deployment.environment = "production"
   - http.method, http.route, http.status_code
   - user.id (if authenticated)
   - session.id, session.holes_count
   - llm.provider, llm.model, llm.cost_usd (if LLM called)
   ```

3. **Dashboards Rendering**:
   - Open each dashboard
   - Verify widgets load data
   - Check time ranges work correctly

4. **Alerts Firing**:
   - Trigger test conditions (e.g., simulate slow request)
   - Verify alert fires within SLA (5 minutes)
   - Verify Slack notification received

5. **Performance Overhead**:
   ```bash
   # Before instrumentation
   modal profile lift_sys/api/server.py
   # Note: p95 latency baseline

   # After instrumentation
   modal profile lift_sys/api/server.py
   # Verify: overhead <5% (typically 1-2%)
   ```

### 10.4 Rollback Plan

If issues arise during deployment:

**Rollback Step 1**: Disable span export (keep instrumentation):

```python
# lift_sys/observability/__init__.py
def setup_observability(service_name: str = "lift-sys"):
    if os.getenv("HONEYCOMB_ENABLED", "true") == "false":
        # Use no-op tracer
        trace.set_tracer_provider(TracerProvider())
        return
    # ... rest of setup
```

Set `HONEYCOMB_ENABLED=false` in Modal secrets, redeploy.

**Rollback Step 2**: Remove instrumentation calls:

Comment out manual `start_as_current_span` calls, redeploy.

**Rollback Step 3**: Remove auto-instrumentation:

Comment out `FastAPIInstrumentor.instrument_app()` calls, redeploy.

**Rollback Step 4**: Full removal:

Revert to commit before observability integration.

**Recovery Time**: Each rollback step takes ~5 minutes (comment + redeploy).

---

## 11. Cost & Performance

### 11.1 Honeycomb Pricing

**Free Tier** (sufficient for early development):
- 20M events/month
- 60-day retention
- Unlimited team members
- Unlimited boards/queries

**Pro Tier** ($0.0001/event above 20M):
- $100/mo for 1B events (avg)
- 180-day retention
- SLA support

**Enterprise** (contact sales):
- Custom retention (1 year+)
- SSO, RBAC
- Dedicated support

### 11.2 Event Volume Estimates

**Baseline (1000 requests/day)**:

Assumptions:
- 1 request = 1 root span (FastAPI auto-instrumentation)
- 1 request = 5 child spans (session create, IR generate, code generate, 2 DB calls)
- Total: 6 spans/request

Calculation:
```
1000 requests/day × 6 spans/request = 6,000 events/day
6,000 events/day × 30 days = 180,000 events/month
```

**Verdict**: Well under 20M free tier limit.

**Growth Scenario (10,000 requests/day)**:

```
10,000 requests/day × 6 spans/request = 60,000 events/day
60,000 events/day × 30 days = 1,800,000 events/month
```

**Verdict**: Still under free tier limit.

**High Scale (100,000 requests/day)**:

```
100,000 requests/day × 6 spans/request = 600,000 events/day
600,000 events/day × 30 days = 18,000,000 events/month
```

**Verdict**: Approaching free tier limit. Consider:
- Sampling (e.g., 50% of requests) to halve volume
- Pro tier at ~$100/mo for headroom

### 11.3 Performance Overhead

**Expected Overhead**:

OpenTelemetry SDK overhead (measured by OpenTelemetry team):
- Span creation: ~1-5 µs
- Attribute setting: ~0.5 µs
- Span export (batched): amortized ~10 µs/span
- Total per request: ~30-50 µs for 6 spans

**Impact on Latency**:

Typical lift-sys request latency:
- IR generation: 2-5 seconds (LLM calls dominate)
- Code generation: 3-8 seconds (LLM calls + validation)
- Total: 5-13 seconds

Instrumentation overhead: 50 µs = 0.00005 seconds

**Overhead percentage**: 0.00005 / 5 = 0.001% (negligible)

**Memory Overhead**:

Span buffer (before export): ~500 bytes/span
6 spans/request × 500 bytes = 3 KB/request

At 100 concurrent requests: 3 KB × 100 = 300 KB (negligible)

**CPU Overhead**:

Measured in production OpenTelemetry deployments:
- <1% CPU increase for typical workloads
- ~2% CPU increase with high cardinality attributes

**Network Overhead**:

OTLP exports batched every 5 seconds:
- 6 spans/request × 1 KB/span (compressed) = 6 KB/request
- At 100 requests/5s: 600 KB/5s = 120 KB/s

Negligible compared to typical LLM API traffic (10s of MB/s).

### 11.4 Sampling Strategy (Future)

If event volume exceeds budget, implement head-based sampling:

```python
# lift_sys/observability/__init__.py
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

def setup_observability(service_name: str = "lift-sys"):
    # Sample 50% of traces
    sampler = TraceIdRatioBased(0.5)

    provider = TracerProvider(
        resource=resource,
        sampler=sampler  # Add sampler
    )
    # ... rest of setup
```

**Trade-offs**:
- Reduces cost by 50% (or configurable ratio)
- Still captures errors (always sample traces with errors)
- Statistically representative performance metrics

**Advanced**: Tail-based sampling (sample slow/error traces at 100%, others at 10%)
- Requires Honeycomb Refinery or OpenTelemetry Collector
- Complexity not justified until >20M events/month

---

## 12. Success Criteria

### 12.1 Functional Requirements

**FR-1: Traces Captured**
- ✅ All HTTP requests generate root spans
- ✅ Session operations create spans with session.* attributes
- ✅ IR operations create spans with ir.* attributes
- ✅ Code operations create spans with code.* attributes
- ✅ LLM calls create spans with llm.* attributes
- ✅ Database calls create spans with db.* attributes

**FR-2: Error Tracking**
- ✅ All exceptions captured in spans
- ✅ Error spans have error=true attribute
- ✅ Stack traces included in span events
- ✅ Error messages searchable in Honeycomb

**FR-3: Dashboards**
- ✅ 4 dashboards created (Request Overview, Performance, Errors, Business)
- ✅ All widgets render data
- ✅ Queries execute in <5 seconds

**FR-4: Alerts**
- ✅ 5+ alerts configured
- ✅ Alerts fire on test conditions
- ✅ Slack notifications delivered

### 12.2 Non-Functional Requirements

**NFR-1: Performance**
- ✅ Instrumentation overhead <5% latency increase
- ✅ Memory overhead <10 MB/container
- ✅ CPU overhead <2%

**NFR-2: Reliability**
- ✅ Span export does not block request processing
- ✅ Failed exports retry automatically
- ✅ Instrumentation failures do not crash app

**NFR-3: Usability**
- ✅ Team trained on Honeycomb UI (1 hour session)
- ✅ Common queries documented
- ✅ Runbooks created for alerts

**NFR-4: Cost**
- ✅ Event volume stays under free tier (20M/month) for first 6 months
- ✅ Pro tier cost <$200/mo at 100k requests/day

### 12.3 Acceptance Testing

**Test 1: End-to-End Trace**

Scenario: Create session → Generate IR → Generate code

Expected:
```
Trace tree in Honeycomb:
├─ POST /api/sessions (root span, FastAPI)
   ├─ session.create (manual span)
   │  ├─ db.insert (auto span, SQLAlchemy)
   ├─ ir.generate (manual span)
   │  ├─ llm.call (manual span)
   ├─ code.generate (manual span)
      ├─ llm.call (manual span)
      ├─ code.validate (manual span)
```

Verification:
- All spans present
- Parent-child relationships correct
- Attributes populated (session.id, llm.cost_usd, etc.)
- Total duration = sum of child durations + overhead

**Test 2: Error Tracking**

Scenario: Trigger ValidationError during code generation

Expected:
- Span `code.validate` has error=true
- Exception message captured
- Stack trace in span events
- Error visible in "Error Tracking" dashboard

Verification:
```
Query in Honeycomb:
WHERE error = true AND name = "code.validate"
| Latest 10
```

**Test 3: High Cardinality Query**

Scenario: Find slowest requests per user

Expected:
```
Query:
GROUP BY user.id, trace.trace_id
CALC P95(duration_ms)
ORDER BY P95(duration_ms) DESC
LIMIT 20
```

Verification:
- Query executes in <5 seconds
- Results show user.id, trace.trace_id, p95 latency

**Test 4: Alert Firing**

Scenario: Simulate high error rate (>10% over 5 minutes)

Expected:
- Alert "High Error Rate" fires within 5 minutes
- Slack notification received with link to Honeycomb query
- Runbook referenced in alert description

Verification:
- Check Slack for alert message
- Click Honeycomb link, verify it opens correct query
- Verify alert auto-resolves when error rate drops

### 12.4 Post-Deployment Monitoring

**Week 1 Checklist**:
- [ ] Review dashboards daily
- [ ] Verify event volume within budget
- [ ] Check for any error spikes
- [ ] Ensure alerts not firing excessively (alert fatigue)

**Month 1 Checklist**:
- [ ] Review SLO compliance (p95 latency <10s, success >95%)
- [ ] Analyze slow queries for optimization opportunities
- [ ] Refine dashboard queries based on team feedback
- [ ] Adjust alert thresholds if needed

**Month 3 Checklist**:
- [ ] Review cost vs budget (should be $0 on free tier)
- [ ] Evaluate need for Pro tier based on growth
- [ ] Document lessons learned
- [ ] Plan for tail-based sampling if needed

### 12.5 Definition of Done

This Honeycomb integration is considered **complete** when:

1. ✅ All code deployed to production Modal environment
2. ✅ Traces flowing to Honeycomb (verified with test requests)
3. ✅ 4 dashboards created and accessible to team
4. ✅ 5+ alerts configured and tested
5. ✅ Team trained on Honeycomb UI (1 hour session completed)
6. ✅ Documentation complete:
   - HONEYCOMB_INTEGRATION_PLAN.md (this document)
   - HONEYCOMB_QUICK_START.md
   - HONEYCOMB_RUNBOOKS.md
7. ✅ Acceptance tests passing (4 tests in Section 12.3)
8. ✅ Performance overhead <5% (verified with profiling)
9. ✅ Event volume under budget (verified in Honeycomb UI)
10. ✅ Zero production incidents caused by instrumentation

**Sign-Off**: Engineering lead reviews and approves completion.

---

## Appendix B: Alert Definitions (Detailed)

### Alert 1: High Error Rate

**Trigger**:
```
Query: AVG(error = true) GROUP BY time(5m)
Threshold: >0.10 (10%)
Window: 5 minutes
```

**Actions**:
- Send to: #engineering-alerts (Slack)
- Severity: P1 (page on-call)
- Runbook: `docs/HONEYCOMB_RUNBOOKS.md#high-error-rate`

**Runbook Steps**:
1. Open Honeycomb alert link
2. Identify error type (GROUP BY exception.type)
3. Find recent deployments (git log)
4. Rollback if deployment-related
5. Investigate root cause if infrastructure issue

### Alert 2: Slow Requests (p95 >10s)

**Trigger**:
```
Query: P95(duration_ms) GROUP BY time(5m)
Threshold: >10000 ms
Window: 5 minutes
```

**Actions**:
- Send to: #performance (Slack)
- Severity: P2 (notify team)
- Runbook: `docs/HONEYCOMB_RUNBOOKS.md#slow-requests`

**Runbook Steps**:
1. Identify slow operation (GROUP BY name, ORDER BY P95(duration_ms) DESC)
2. Check LLM provider latency (WHERE name = "llm.call" GROUP BY llm.provider)
3. Check database performance (WHERE name STARTS WITH "db.")
4. Consider scaling if persistent (increase Modal concurrency)

### Alert 3: LLM Cost Spike

**Trigger**:
```
Query: SUM(llm.cost_usd) GROUP BY time(1h)
Threshold: >$5.00/hour
Window: 1 hour
```

**Actions**:
- Send to: #engineering-alerts (Slack)
- Severity: P2 (notify team)
- Runbook: `docs/HONEYCOMB_RUNBOOKS.md#cost-spike`

**Runbook Steps**:
1. Identify high-cost requests (WHERE llm.cost_usd > 0.05 ORDER BY llm.cost_usd DESC)
2. Check if single user or widespread (GROUP BY user.id)
3. Review prompts for excessive length (llm.input_tokens)
4. Implement rate limiting if abuse detected

### Alert 4: LLM Provider Failure

**Trigger**:
```
Query: AVG(error = true) WHERE name = "llm.call" GROUP BY llm.provider
Threshold: >0.50 (50%)
Window: 5 minutes
```

**Actions**:
- Send to: #engineering-alerts (Slack)
- Severity: P1 (page on-call)
- Runbook: `docs/HONEYCOMB_RUNBOOKS.md#llm-provider-failure`

**Runbook Steps**:
1. Identify failing provider (GROUP BY llm.provider)
2. Check provider status page (Anthropic/OpenAI status)
3. Failover to alternate provider if configured
4. Notify users of degraded service

### Alert 5: Database Connection Errors

**Trigger**:
```
Query: COUNT() WHERE name = "db.connect" AND error = true
Threshold: >10 errors
Window: 5 minutes
```

**Actions**:
- Send to: #engineering-alerts (Slack)
- Severity: P0 (immediate page)
- Runbook: `docs/HONEYCOMB_RUNBOOKS.md#db-connection-errors`

**Runbook Steps**:
1. Check Supabase status (cloud.supabase.com/project/status)
2. Verify connection pooling (Hyperdrive status)
3. Check for connection leaks (review code for unclosed connections)
4. Restart Modal app if connection pool exhausted

---

## Appendix C: Sample Queries Library

### Query: Find User's Slow Sessions

**Purpose**: Debug slow experience for specific user

```
WHERE user.id = "<user-id>"
  AND duration_ms > 10000
GROUP BY trace.trace_id, session.id, http.route
CALC P95(duration_ms)
ORDER BY P95(duration_ms) DESC
LIMIT 20
```

### Query: LLM Cost by Model

**Purpose**: Compare cost efficiency of different models

```
WHERE llm.cost_usd EXISTS
GROUP BY llm.provider, llm.model
CALC SUM(llm.cost_usd), AVG(llm.cost_usd), COUNT()
ORDER BY SUM(llm.cost_usd) DESC
```

### Query: Code Generation Success Rate

**Purpose**: Track code generation reliability

```
WHERE name = "code.generate"
GROUP BY time(1h)
CALC AVG(code.success = true) * 100 AS success_rate
```

### Query: Retry Analysis

**Purpose**: Identify operations requiring retries

```
WHERE code.retries > 0
GROUP BY name, code.retry_reason
CALC AVG(code.retries), COUNT()
ORDER BY AVG(code.retries) DESC
```

### Query: Database Query Breakdown

**Purpose**: Find slowest database queries

```
WHERE name STARTS WITH "db."
GROUP BY db.statement, db.table
CALC P95(duration_ms), COUNT()
ORDER BY P95(duration_ms) DESC
LIMIT 50
```

### Query: Trace a Single Request

**Purpose**: Deep-dive into single request's execution

```
WHERE trace.trace_id = "<trace-id>"
ORDER BY timestamp ASC
```

Click "Trace View" to see waterfall diagram.

---

**Document Status**: ✅ Complete (Sections 1-12 + Appendices)
**Total Length**: ~1,900 lines
**Next Action**: Create Beads work items + supporting documents
**Owner**: Engineering team
**Review Date**: After Phase 5 completion
