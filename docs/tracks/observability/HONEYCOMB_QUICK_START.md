# Honeycomb Observability - Quick Start Guide

**Target Time**: 30 minutes
**Audience**: Engineers deploying lift-sys to production
**Prerequisites**: Modal account, lift-sys codebase access
**Outcome**: Traces flowing to Honeycomb with basic dashboards

---

## Overview

This guide walks through the minimum steps to get Honeycomb observability running in production. For comprehensive details, see [HONEYCOMB_INTEGRATION_PLAN.md](./HONEYCOMB_INTEGRATION_PLAN.md).

**What You'll Get**:
- Distributed tracing of all API requests
- Automatic instrumentation of FastAPI, HTTP calls, and database queries
- Manual instrumentation of Session, IR, Code, and LLM operations
- Real-time performance and error monitoring
- Cost tracking for LLM API calls

---

## Step 1: Create Honeycomb Account (5 minutes)

### 1.1 Sign Up

Visit https://ui.honeycomb.io/signup and create account:
- Choose **Free tier** (20M events/month, sufficient for early development)
- Use company email for team collaboration
- Complete email verification

### 1.2 Create Dataset

1. After login, navigate to **Settings** → **Environments**
2. Click **Create New Environment**
3. Name: `lift-sys` (or `lift-sys-production` if separating dev/prod)
4. Click **Create**

### 1.3 Generate API Key

1. Navigate to **Settings** → **API Keys**
2. Click **Create API Key**
3. Name: `lift-sys-modal` (identifies this key's usage)
4. Permissions: **Send Events** (minimum required)
5. Click **Create**
6. **COPY THE KEY** (you won't see it again)
7. Save to password manager or secure note

**Important**: Treat this key like a password. Never commit to git.

---

## Step 2: Configure Modal Secrets (3 minutes)

### 2.1 Add Honeycomb API Key

```bash
# From terminal in lift-sys project root
modal secret create honeycomb-secrets \
  HONEYCOMB_API_KEY=<paste-your-api-key-here>
```

### 2.2 Verify Secret

```bash
# List secrets to confirm creation
modal secret list | grep honeycomb
```

Expected output:
```
honeycomb-secrets    1 value    <timestamp>
```

---

## Step 3: Install Dependencies (2 minutes)

### 3.1 Add OpenTelemetry Packages

```bash
# From project root
uv add opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp-proto-grpc \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-httpx \
  opentelemetry-instrumentation-sqlalchemy
```

### 3.2 Verify Installation

```bash
# Check pyproject.toml
grep -A 6 "dependencies" pyproject.toml | grep opentelemetry
```

Expected output includes all 6 opentelemetry packages.

---

## Step 4: Create Observability Module (10 minutes)

### 4.1 Create Directory Structure

```bash
mkdir -p lift_sys/observability
touch lift_sys/observability/__init__.py
touch lift_sys/observability/tracing.py
```

### 4.2 Write Initialization Code

Create `lift_sys/observability/__init__.py`:

```python
"""OpenTelemetry and Honeycomb observability setup."""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor

def setup_observability(service_name: str = "lift-sys"):
    """Initialize OpenTelemetry with Honeycomb backend."""

    # Get Honeycomb API key from environment
    honeycomb_api_key = os.getenv("HONEYCOMB_API_KEY")
    if not honeycomb_api_key:
        print("WARNING: HONEYCOMB_API_KEY not set, observability disabled")
        return

    # Create resource with service metadata
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("LIFT_SYS_VERSION", "dev"),
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Create OTLP exporter pointing to Honeycomb
    otlp_exporter = OTLPSpanExporter(
        endpoint="https://api.honeycomb.io:443",
        headers={
            "x-honeycomb-team": honeycomb_api_key,
            "x-honeycomb-dataset": os.getenv("HONEYCOMB_DATASET", "lift-sys"),
        },
    )

    # Add span processor (batches spans before export)
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Enable auto-instrumentation
    HTTPXInstrumentor().instrument()

    print(f"✅ Honeycomb observability initialized for {service_name}")

def get_tracer(name: str):
    """Get a tracer for manual instrumentation."""
    return trace.get_tracer(name)
```

### 4.3 Integrate with FastAPI Server

Update `lift_sys/api/server.py`:

```python
from lift_sys.observability import setup_observability
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ... existing imports ...

# Call setup_observability before creating FastAPI app
setup_observability(service_name="lift-sys")

# Create FastAPI app
app = FastAPI(title="lift-sys API")

# Instrument FastAPI app
FastAPIInstrumentor.instrument_app(app)

# ... rest of server code ...
```

---

## Step 5: Add Manual Instrumentation (5 minutes)

### 5.1 Instrument Session Creation

Update `lift_sys/spec_sessions/manager.py`:

```python
from lift_sys.observability import get_tracer
from opentelemetry.trace import Status, StatusCode

tracer = get_tracer(__name__)

class PromptSessionManager:
    async def create_from_prompt(self, prompt: str, user_id: str):
        """Create session with tracing."""

        with tracer.start_as_current_span(
            "session.create",
            attributes={
                "session.prompt_length": len(prompt),
                "user.id": user_id,
            }
        ) as span:
            try:
                # Existing session creation logic
                session = PromptSession(...)
                # ... your code ...

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

### 5.2 Instrument LLM Calls (Cost Tracking)

Update `lift_sys/providers/anthropic_provider.py`:

```python
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

            # Calculate cost (Anthropic pricing for Claude 3.5 Sonnet)
            input_cost = response.usage.input_tokens * 0.000015  # $15/1M tokens
            output_cost = response.usage.output_tokens * 0.000075  # $75/1M tokens
            total_cost = input_cost + output_cost
            span.set_attribute("llm.cost_usd", round(total_cost, 6))

            return response.content[0].text
```

**Note**: Repeat similar instrumentation for IR and code generation (see HONEYCOMB_INTEGRATION_PLAN.md Section 5 for full examples).

---

## Step 6: Deploy to Modal (2 minutes)

### 6.1 Update Modal App Definition

Ensure your `@app.function()` decorator includes the Honeycomb secret:

```python
import modal

app = modal.App("lift-sys")

@app.function(
    secrets=[
        modal.Secret.from_name("lift-sys-secrets"),
        modal.Secret.from_name("honeycomb-secrets"),  # Add this
    ],
    # ... other config ...
)
def serve():
    from lift_sys.api.server import app as fastapi_app
    return fastapi_app
```

### 6.2 Deploy

```bash
modal deploy lift_sys/api/server.py
```

Wait for deployment to complete (~1-2 minutes).

---

## Step 7: Verify Traces in Honeycomb (3 minutes)

### 7.1 Make Test Request

```bash
# Get your Modal app URL (shown in deploy output)
MODAL_URL="https://your-app.modal.run"

# Make test request
curl -X POST "$MODAL_URL/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a hello world function in Python"}'
```

### 7.2 Check Honeycomb UI

1. Navigate to https://ui.honeycomb.io
2. Select your `lift-sys` environment
3. Go to **Query** tab
4. Run query:
   ```
   WHERE service.name = "lift-sys"
   | Latest 10
   ```
5. **Expected**: You should see traces appear within 30 seconds

### 7.3 Inspect Trace

Click on a trace to see details:
- **Root span**: `POST /api/sessions` (FastAPI auto-instrumentation)
- **Child spans**: `session.create`, `llm.call` (manual instrumentation)
- **Attributes**: `user.id`, `session.id`, `llm.cost_usd`, etc.

If you see traces with attributes, **congratulations!** Observability is working.

---

## Step 8: Create Basic Dashboard (Optional, 5 minutes)

### 8.1 Create Dashboard

1. In Honeycomb UI, navigate to **Boards**
2. Click **Create New Board**
3. Name: `lift-sys Quick Overview`

### 8.2 Add Widgets

**Widget 1: Request Rate**
- Type: Line chart
- Query: `COUNT()`
- Group by: `time`
- Time range: Last 24 hours

**Widget 2: Latency (p95)**
- Type: Line chart
- Query: `P95(duration_ms)`
- Group by: `time`
- Time range: Last 24 hours

**Widget 3: Error Rate**
- Type: Line chart
- Query: `AVG(error = true) * 100`
- Group by: `time`
- Time range: Last 24 hours

**Widget 4: LLM Cost (hourly)**
- Type: Line chart
- Query: `SUM(llm.cost_usd)`
- Group by: `time(1h)`
- Time range: Last 7 days

### 8.3 Save Dashboard

Click **Save** in top-right corner.

---

## Verification Checklist

Before considering setup complete, verify:

- [ ] Honeycomb account created (free tier)
- [ ] API key generated and saved securely
- [ ] Modal secret `honeycomb-secrets` created
- [ ] OpenTelemetry dependencies installed (`uv add ...`)
- [ ] `lift_sys/observability/` module created
- [ ] `setup_observability()` called in `server.py`
- [ ] FastAPI app instrumented
- [ ] Manual spans added to session creation and LLM calls
- [ ] App deployed to Modal (`modal deploy`)
- [ ] Test request made to API
- [ ] Traces visible in Honeycomb UI within 30 seconds
- [ ] Trace attributes correct (`service.name`, `user.id`, `llm.cost_usd`)
- [ ] Basic dashboard created (optional but recommended)

---

## Troubleshooting

### Problem: No traces appear in Honeycomb

**Check 1**: Verify API key is correct
```bash
modal secret get honeycomb-secrets
# Should show HONEYCOMB_API_KEY value (masked)
```

**Check 2**: Check Modal logs for errors
```bash
modal app logs lift-sys
# Look for "Honeycomb observability initialized" message
# or "HONEYCOMB_API_KEY not set" warning
```

**Check 3**: Verify dataset name matches
- In Honeycomb UI: Settings → Environments → Note the name
- In code: `honeycomb-dataset` header should match

**Check 4**: Check firewall/network
- Honeycomb endpoint: `https://api.honeycomb.io:443`
- Modal should have outbound HTTPS access by default

### Problem: Traces appear but attributes missing

**Check 1**: Verify manual instrumentation called
- Add `print()` statements in instrumentation code
- Check Modal logs for span creation

**Check 2**: Verify attribute names
- Honeycomb is case-sensitive
- Use dot notation: `session.id`, not `session_id`

**Check 3**: Check attribute types
- Strings: fine
- Numbers: fine
- Objects: must serialize to JSON first

### Problem: High latency after instrumentation

**Check 1**: Verify batch export enabled
- Code should use `BatchSpanProcessor`, not `SimpleSpanProcessor`
- Batching prevents blocking on export

**Check 2**: Check span volume
- Too many spans (>100/request) can cause overhead
- Review instrumentation strategy

**Check 3**: Disable temporarily to isolate
```python
# In observability/__init__.py, add early return
def setup_observability(service_name: str = "lift-sys"):
    return  # Temporarily disable
```

Redeploy and measure latency. If latency drops, issue is with instrumentation.

---

## Next Steps

**Now that basic observability is working**:

1. **Add more instrumentation**: IR generation, code generation, validation (see HONEYCOMB_INTEGRATION_PLAN.md Section 5)
2. **Create full dashboards**: Performance Analysis, Error Tracking, Business Metrics (Section 7)
3. **Set up alerts**: High error rate, slow requests, cost spikes (Section 8)
4. **Define SLOs**: p95 latency <10s, success rate >95% (Section 8)
5. **Train team**: 1-hour session on Honeycomb UI navigation

**Reference Documents**:
- [HONEYCOMB_INTEGRATION_PLAN.md](./HONEYCOMB_INTEGRATION_PLAN.md) - Comprehensive implementation plan
- [HONEYCOMB_BEADS_SUMMARY.md](./HONEYCOMB_BEADS_SUMMARY.md) - Work breakdown and timeline
- Honeycomb Docs: https://docs.honeycomb.io/getting-started/
- OpenTelemetry Docs: https://opentelemetry.io/docs/languages/python/

---

## FAQ

**Q: How much does Honeycomb cost?**
A: Free tier is 20M events/month (sufficient for early development). At 1000 requests/day with 6 spans/request, you'll use ~180k events/month (under 1% of free tier).

**Q: Can I use Honeycomb with local development?**
A: Yes! Set `HONEYCOMB_API_KEY` locally and run your app. Use a separate dataset like `lift-sys-dev` to isolate dev traces from production.

**Q: How do I disable observability temporarily?**
A: Set Modal secret `HONEYCOMB_ENABLED=false` and redeploy. The code will detect this and skip setup.

**Q: Does observability work with Supabase integration?**
A: Yes! SQLAlchemy auto-instrumentation will automatically trace Supabase queries once you add database calls.

**Q: What's the performance overhead?**
A: Typically <1% CPU and <5ms latency increase. Negligible compared to LLM call latency (2-8 seconds).

**Q: Can I sample traces to reduce cost?**
A: Yes, implement head-based sampling with `TraceIdRatioBased(0.5)` to sample 50% of traces. See HONEYCOMB_INTEGRATION_PLAN.md Section 11.4.

---

**Setup Complete!** You now have production observability with Honeycomb. Your traces are flowing, costs are tracked, and you're ready to monitor lift-sys in production.

**Questions?** See HONEYCOMB_INTEGRATION_PLAN.md or Beads work items (lift-sys-265 through lift-sys-271).
