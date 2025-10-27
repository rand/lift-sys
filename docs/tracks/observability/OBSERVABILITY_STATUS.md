# Observability Track Status

**Last Updated**: 2025-10-27
**Track Priority**: P2 (Operational excellence)
**Current Phase**: Planning complete, implementation pending

---

## For New Claude Code Session

**Quick Context** (30 seconds):
- Honeycomb.io integration planned but not yet implemented
- Current observability: Basic logs (uvicorn, FastAPI)
- Next: Structured logging, distributed tracing, metrics collection
- Dependencies: Production deployment, meaningful traffic

**Check Status**:
```bash
bd list --label observability --json
# (No active observability work - planning complete, awaiting implementation priority)
```

---

## Current Status (2025-10-27)

### ✅ Planning Complete

**Completed Work**:
- Honeycomb planning documented
- Beads created and closed (planning phase)
- Architecture designed (structured logging, tracing, metrics)
- Cost estimation: ~$100/month for production scale

**Archived Documentation**:
- `HONEYCOMB_PLANNING_COMPLETE.md` → archive/features/
- `HONEYCOMB_BEADS_SUMMARY.md` → archive/features/

### ⏸️ Implementation Pending

**Blocked By**:
- Production deployment (not yet launched)
- Need meaningful traffic to instrument
- Priority: After DSPy Phase 3 and ICS Phase 2

**Estimated Timeline**:
- Start: Q1 2026
- Duration: 2-3 weeks
- Launch: Q1 2026

---

## Architecture Design

### Three Pillars of Observability

```
1. Logs        → Honeycomb (structured, searchable)
2. Metrics     → Honeycomb (counters, histograms)
3. Traces      → Honeycomb (distributed tracing)
```

### Instrumentation Points

**API Layer** (`lift_sys/api/server.py`):
- Request/response logging
- Endpoint latency metrics
- Error rate tracking
- Request ID propagation

**Translation Layer** (`lift_sys/forward_mode/`):
- NLP → IR translation duration
- Success/failure rates
- Prompt characteristics (length, complexity)
- IR validation results

**Code Generation** (`lift_sys/codegen/`):
- Code generation duration
- Language-specific metrics (Python, TypeScript)
- AST validation results
- Syntax error rates

**LLM Providers** (`lift_sys/providers/`):
- Modal.com call latency
- Token usage (input/output)
- Error rates by provider
- Cost tracking

**Database** (`lift_sys/storage/`):
- Query duration
- Connection pool stats
- RLS overhead
- Error rates

### Data Flow

```
Request
  ↓
API Middleware (add trace_id, start_time)
  ↓
Business Logic (emit spans, logs, metrics)
  ↓
Honeycomb SDK (batch and send)
  ↓
Honeycomb Backend
  ↓
Dashboards & Alerts
```

---

## Implementation Plan

### Phase 1: Structured Logging (Week 1)

**Goal**: Replace print statements with structured logs

**Implementation**:
```python
import structlog

logger = structlog.get_logger()

# Before (unstructured)
print(f"Generated IR for prompt: {prompt}")

# After (structured)
logger.info(
    "ir_generated",
    prompt_length=len(prompt),
    effect_count=len(ir.effects),
    duration_ms=duration,
    user_id=user_id,
    session_id=session_id,
)
```

**Deliverables**:
- Configure `structlog` with JSON output
- Add logging to all major operations
- Include context (user_id, session_id, trace_id)

### Phase 2: Distributed Tracing (Week 2)

**Goal**: Track requests across service boundaries

**Implementation**:
```python
from honeycomb.opentelemetry import HoneycombSpanProcessor
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("translate_prompt")
def translate(prompt: str) -> IR:
    span = trace.get_current_span()
    span.set_attribute("prompt_length", len(prompt))

    # ... business logic ...

    span.set_attribute("effect_count", len(ir.effects))
    return ir
```

**Deliverables**:
- Configure OpenTelemetry SDK
- Add spans to critical paths
- Propagate trace context (FastAPI → Modal → Supabase)

### Phase 3: Metrics Collection (Week 3)

**Goal**: Track quantitative metrics over time

**Implementation**:
```python
from opentelemetry.metrics import get_meter

meter = get_meter(__name__)
translation_counter = meter.create_counter(
    "translation_requests_total",
    description="Total translation requests",
)
translation_duration = meter.create_histogram(
    "translation_duration_seconds",
    description="Translation duration",
)

# Emit metrics
translation_counter.add(1, {"language": "python", "success": True})
translation_duration.record(duration, {"language": "python"})
```

**Deliverables**:
- Define key metrics (SLIs)
- Instrument critical operations
- Set up Honeycomb dashboards

---

## Metrics & SLIs

### Service Level Indicators (SLIs)

**Latency** (Target: p95 < 30s):
- Translation latency (NLP → IR)
- Code generation latency (IR → Code)
- End-to-end latency (Prompt → Code)

**Availability** (Target: 99.5%):
- API uptime (excluding maintenance)
- Success rate (valid outputs / total requests)

**Error Rate** (Target: <5%):
- Validation errors (invalid IR)
- Syntax errors (invalid code)
- LLM errors (provider failures)

**Cost** (Target: <$0.05/request):
- LLM costs (Modal.com usage)
- Database costs (Supabase)
- Monitoring costs (Honeycomb)

### Key Metrics

**Request Metrics**:
- `translation_requests_total` (counter, by language/success)
- `code_generation_requests_total` (counter, by language/success)
- `api_requests_total` (counter, by endpoint/status)

**Latency Metrics**:
- `translation_duration_seconds` (histogram, by language)
- `code_generation_duration_seconds` (histogram, by language)
- `llm_call_duration_seconds` (histogram, by provider)

**Error Metrics**:
- `validation_errors_total` (counter, by error_type)
- `syntax_errors_total` (counter, by language)
- `llm_errors_total` (counter, by provider/error_type)

**Business Metrics**:
- `sessions_created_total` (counter, by user_id)
- `code_executions_total` (counter, by language/success)
- `active_users` (gauge)

---

## Dashboards & Queries

### Dashboard 1: System Health

**Panels**:
1. Request rate (rpm) - Line chart
2. Error rate (%) - Line chart with threshold
3. p50/p95/p99 latency - Line chart
4. Active users - Counter

**Query Examples**:
```
# Request rate
COUNT(*) WHERE api_request = true GROUP BY time(1m)

# Error rate
COUNT(*) WHERE error = true / COUNT(*) * 100

# p95 latency
HEATMAP(duration_ms) WHERE api_request = true
```

### Dashboard 2: Translation Performance

**Panels**:
1. Translation success rate by language
2. Translation duration by prompt length
3. Effect count distribution
4. Validation error breakdown

### Dashboard 3: Cost Tracking

**Panels**:
1. Total LLM cost (daily)
2. Cost per request
3. Token usage (input/output)
4. Cost by user

---

## Alerting Strategy

### Critical Alerts (Page On-Call)

**High Error Rate**:
- Trigger: Error rate >10% for 5 minutes
- Action: Investigate immediately
- Runbook: Check logs, verify providers, rollback if needed

**High Latency**:
- Trigger: p95 latency >60s for 5 minutes
- Action: Investigate provider issues
- Runbook: Check Modal status, verify network

**Service Down**:
- Trigger: API availability <95% for 2 minutes
- Action: Emergency response
- Runbook: Check server logs, restart if needed

### Warning Alerts (Slack Notification)

**Elevated Error Rate**:
- Trigger: Error rate >5% for 10 minutes
- Action: Monitor and investigate

**Cost Spike**:
- Trigger: Daily cost >$200 (expected ~$100)
- Action: Review usage patterns

**Low Success Rate**:
- Trigger: Success rate <80% for 10 minutes
- Action: Check validation logic

---

## Cost Estimation

### Honeycomb Pricing (as of 2025-10-27)

**Plan**: Pro ($100/month base)
- 10M events/month included
- $0.50 per 1M additional events
- Unlimited users
- 60-day retention

**Expected Usage**:
- Production: ~5M events/month
- Staging: ~1M events/month
- Dev: ~500K events/month
- **Total**: ~6.5M events/month ($100/month)

### Cost Optimization

**Sampling**:
- Sample routine requests (10%)
- Keep all errors (100%)
- Keep slow requests (100%, >30s)

**Retention**:
- Recent data: 60 days (default)
- Old data: Archive to S3 (long-term analysis)

**Event Size**:
- Limit attribute count (<50 per event)
- Truncate large strings (max 1KB)
- Avoid high-cardinality attributes

---

## Security & Compliance

### Data Privacy

**Sensitive Data**:
- User prompts (PII possible)
- Generated code (may contain secrets)
- Session IDs (linkable to users)

**Handling**:
- Hash user IDs (not reversible)
- Truncate prompts (max 100 chars)
- Scrub secrets from code (regex patterns)
- No credit card data in logs (ever)

### GDPR Compliance

**User Rights**:
- Right to access (export user's events)
- Right to erasure (delete user's events)
- Right to portability (provide JSON export)

**Implementation**:
- Tag events with `user_id` (hashed)
- Provide data export endpoint
- Implement deletion via Honeycomb API

---

## Integration Points

### FastAPI Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id

        with tracer.start_as_current_span("http_request"):
            span = trace.get_current_span()
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("trace_id", trace_id)

            response = await call_next(request)

            span.set_attribute("http.status_code", response.status_code)
            return response
```

### Modal.com Integration

```python
# In Modal function
@app.function()
def generate_ir(prompt: str, trace_id: str):
    with tracer.start_as_current_span("modal_generate_ir"):
        span = trace.get_current_span()
        span.set_attribute("trace_id", trace_id)
        span.set_attribute("prompt_length", len(prompt))

        # ... LLM call ...

        span.set_attribute("tokens_used", tokens)
        return ir
```

### Supabase Logging

```python
# In SupabaseSessionStore
async def create_session(self, user_id: str, prompt: str):
    with tracer.start_as_current_span("db_create_session"):
        span = trace.get_current_span()
        span.set_attribute("user_id", hash(user_id))

        start = time.time()
        result = await self.client.table("sessions").insert({...})
        duration = time.time() - start

        span.set_attribute("duration_ms", duration * 1000)
        return result
```

---

## Known Issues & Limitations

### Current State

**No observability** except:
- uvicorn access logs (basic request logging)
- FastAPI debug logs (in development)
- Manual benchmarking (performance_benchmark.py)

### Limitations

**Local Development**:
- Honeycomb SDK may slow down dev server
- Need dev/staging separation
- Mock Honeycomb in unit tests

**Cold Starts**:
- Modal.com cold starts (~3min) skew latency metrics
- Need to tag cold vs warm starts

**Sampling Trade-offs**:
- Sampling reduces costs but loses granularity
- Need balance (100% errors, 10% success)

---

## Roadmap

### Q1 2026: Implementation

**January**:
- Structured logging setup
- Basic Honeycomb integration
- System health dashboard

**February**:
- Distributed tracing
- Translation performance dashboard
- Cost tracking dashboard

**March**:
- Metrics collection
- Alerting setup
- Documentation and runbooks

### Q2 2026: Optimization

**Enhancements**:
- Advanced sampling strategies
- Cost optimization
- Custom visualizations
- Anomaly detection

---

## Resources

### Documentation

- **Planning**: Archive `docs/archive/2025_q4_completed/features/HONEYCOMB_PLANNING_COMPLETE.md`
- **Honeycomb Docs**: https://docs.honeycomb.io
- **OpenTelemetry**: https://opentelemetry.io

### Internal References

- **Master Roadmap**: `docs/MASTER_ROADMAP.md`
- **Beads Summary**: Archive `docs/archive/2025_q4_completed/features/HONEYCOMB_BEADS_SUMMARY.md`

---

## Quick Commands

```bash
# Check observability beads
bd list --label observability --json

# (Implementation commands TBD)
# honeycomb tail --dataset=lift-sys
# honeycomb query --query="..."
```

---

**End of Observability Track Status**

**For next session**: Implementation awaits production deployment and priority.
