---
track: infrastructure
status: stable
priority: P2
phase: maintenance
completion: 100%
last_updated: 2025-10-27
session_protocol: |
  For new Claude Code session:
  1. Read this STATUS.md (< 30 seconds context)
  2. Check Modal status: `modal app list`
  3. Check deployment: `modal app logs lift-sys --follow`
  4. Infrastructure is stable, focus on application features
  5. Only work here for performance optimization or issues
related_docs:
  - docs/tracks/infrastructure/LLGUIDANCE_MIGRATION_PLAN.md
  - docs/tracks/infrastructure/MODAL_COST_OPTIMIZATION.md
  - docs/MASTER_ROADMAP.md
---

# Infrastructure Track Status

**Last Updated**: 2025-10-27
**Track Priority**: P2 (Operational foundation)
**Current Phase**: Stable - llguidance migration complete

---

## For New Claude Code Session

**Quick Context** (30 seconds):
- Infrastructure is stable and production-ready
- llguidance migration from XGrammar complete
- Modal.com deployment working (H100 GPUs, ~2.7s latency)
- Supabase integration complete (PostgreSQL + RLS)
- Next: Performance optimization, monitoring, cost analysis

**Check Status**:
```bash
# Check Modal deployment
modal app list
modal app logs lift-sys --follow

# Check Supabase
bd list --label supabase --json

# Test API
curl http://localhost:8000/health
```

---

## Current Status (2025-10-27)

### ✅ Core Infrastructure Complete

**Completed Work**:
1. **llguidance Migration** ✅
   - Migrated from XGrammar to llguidance backend
   - vLLM 0.11.0 integration
   - GPU selection optimized (H100 for production)

2. **Modal.com Deployment** ✅
   - Serverless functions deployed
   - GPU workers configured (H100 GPUs)
   - API endpoints exposed
   - Cost-effective (~$0.02/request)

3. **Supabase Integration** ✅
   - PostgreSQL database
   - Row Level Security (RLS) enforced
   - Session storage working
   - Authentication integration

4. **FastAPI Backend** ✅
   - REST API endpoints
   - Session management
   - Error handling
   - CORS configuration

### 🔄 Maintenance & Optimization

**Ongoing**:
- Performance monitoring
- Cost optimization
- Scaling preparation
- Security hardening

---

## Technology Stack

### Compute: Modal.com

**Why Modal**:
- Serverless GPU access (no server management)
- Fast cold starts (~3min initially, then ~2.7s)
- Cost-effective (pay-per-use)
- Python-native (seamless integration)

**Configuration**:
```python
import modal

app = modal.App("lift-sys")

# GPU selection
gpu_config = modal.gpu.H100(count=1)  # Production
# gpu_config = modal.gpu.L40S(count=1)  # Cost/performance balance
# gpu_config = modal.gpu.T4(count=1)    # Development

# Image with dependencies
image = (
    modal.Image.debian_slim()
    .pip_install_from_pyproject("pyproject.toml")
    .env({"VLLM_VERSION": "0.11.0"})
)

# Function
@app.function(
    image=image,
    gpu=gpu_config,
    secrets=[modal.Secret.from_name("supabase")],
    timeout=600,
)
async def generate_ir(prompt: str) -> dict:
    # Implementation
    pass
```

**GPU Options**:
- **H100**: Max performance (~2.7s), higher cost ($2.50/hr)
- **L40S**: Cost/perf balance (~4s), moderate cost ($1.00/hr)
- **A100**: Fallback option (~5s), moderate cost ($1.50/hr)
- **T4**: Dev/testing (~10s), low cost ($0.30/hr)

**Current**: H100 for production, L40S for staging

### Database: Supabase

**Why Supabase**:
- PostgreSQL (reliable, SQL-based)
- Row Level Security (RLS) built-in
- Authentication included
- Real-time subscriptions
- Auto-generated REST API

**Configuration**:
- **URL**: `https://bqokcxjusdkywfgfqhzo.supabase.co`
- **Region**: US East 1 (Virginia)
- **Plan**: Pro ($25/month)
- **Database**: PostgreSQL 15

**Tables**:
```sql
-- sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    prompt TEXT NOT NULL,
    current_ir JSONB,
    generated_code TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'complete', 'error')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own sessions"
    ON sessions
    FOR ALL
    USING (auth.uid() = user_id);
```

**Migrations**: Located in `migrations/`, run via `scripts/database/run_migrations.py`

### Backend: FastAPI

**Why FastAPI**:
- Fast (async/await native)
- Type-safe (Pydantic validation)
- Auto-generated OpenAPI docs
- Easy to test

**Endpoints**:
```
POST   /api/sessions           # Create session
GET    /api/sessions/{id}      # Get session details
GET    /api/sessions           # List user sessions
PUT    /api/sessions/{id}      # Update session
DELETE /api/sessions/{id}      # Delete session
GET    /health                 # Health check
```

**Configuration** (`lift_sys/api/server.py`):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="lift-sys API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(sessions_router, prefix="/api")
```

**Running Locally**:
```bash
uv run uvicorn lift_sys.api.server:app --reload --port 8000
```

### LLM Backend: llguidance

**Why llguidance**:
- Constraint-guided generation (JSON schema compliance)
- vLLM 0.11.0 support
- Better performance than XGrammar
- Active development

**Migration from XGrammar**:
- **Before**: XGrammar backend (deprecated)
- **After**: llguidance backend (current)
- **Changes**: Minimal (API compatible)
- **Status**: Complete ✅

**Configuration**:
```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="Qwen/Qwen2.5-7B-Instruct",
    gpu_memory_utilization=0.95,
    guided_decoding_backend="llguidance",  # ← Key change
)

# Generate with schema constraints
output = llm.generate(
    prompt,
    sampling_params=SamplingParams(
        temperature=0.3,
        max_tokens=2000,
        guided_json=schema,  # JSON schema constraint
    ),
)
```

---

## Performance Metrics

### Current Performance (2025-10-27)

**Latency**:
- Cold start: ~3 minutes (first call)
- Warm: ~2.7s median (H100 GPU)
- p95: ~5s
- p99: ~10s

**Success Rate**:
- Valid outputs: 60% (real success rate)
- Syntax valid: 80%
- Passes tests: 60%

**Cost**:
- Per request: ~$0.02 (H100 usage)
- Modal compute: ~$100/month (low traffic)
- Supabase: $25/month (Pro plan)
- **Total**: ~$125/month

### Performance Goals

**Latency** (Target):
- Warm calls: <2s (current: 2.7s)
- p95: <5s (current: 5s) ✅
- p99: <10s (current: 10s) ✅

**Success Rate** (Target):
- Valid outputs: >80% (current: 60%)
- Syntax valid: >95% (current: 80%)

**Cost** (Target):
- Per request: <$0.02 (current: ~$0.02) ✅
- Monthly: <$150 (current: ~$125) ✅

---

## Security

### Secrets Management

**Modal Secrets** (Production):
```bash
modal secret create supabase \
  SUPABASE_URL="https://bqokcxjusdkywfgfqhzo.supabase.co" \
  SUPABASE_ANON_KEY="<public-key>" \
  SUPABASE_SERVICE_KEY="<secret-key>"

modal secret list
```

**Local Development** (`.env.local`, gitignored):
```bash
SUPABASE_URL=https://bqokcxjusdkywfgfqhzo.supabase.co
SUPABASE_ANON_KEY=<public-key>
SUPABASE_SERVICE_KEY=<secret-key>
DATABASE_URL=<connection-string>
```

**Critical Rules**:
- ❌ NEVER commit secrets to git
- ❌ NEVER hardcode secrets in code
- ✅ ALWAYS use environment variables or Modal secrets
- ✅ ALWAYS use `.env.local` (gitignored) for local dev

### Row Level Security (RLS)

**Enabled on all tables**:
```sql
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own data
CREATE POLICY "user_isolation"
    ON sessions
    FOR ALL
    USING (auth.uid() = user_id);
```

**Benefits**:
- User data isolation (automatic)
- No SQL injection vulnerabilities
- Defense in depth

**Trade-offs**:
- Slight performance overhead
- More complex debugging
- Must test RLS policies

### API Security

**Current**:
- CORS configured (restrict origins)
- FastAPI automatic validation (Pydantic)
- Supabase RLS (user isolation)

**Future** (Q1 2026):
- Rate limiting (per user/IP)
- Authentication (JWT tokens)
- API keys (for programmatic access)
- Request size limits (prevent abuse)

---

## Deployment

### Modal.com Deployment

**Deploy**:
```bash
# Deploy app
modal deploy lift_sys/modal_app.py

# Check status
modal app list

# View logs
modal app logs lift-sys --follow

# Stop resources
modal app stop lift-sys
```

**Environment**:
- **Production**: `modal deploy` (always-on)
- **Staging**: `modal serve --dev` (dev mode, local changes)
- **Development**: Local FastAPI (no Modal)

### Database Migrations

**Run Migrations**:
```bash
python scripts/database/run_migrations.py
```

**Create Migration**:
```bash
# 1. Create SQL file: migrations/003_new_feature.sql
# 2. Write migration SQL
# 3. Run: python scripts/database/run_migrations.py
# 4. Verify: Check Supabase dashboard
```

**Migration Order**:
- `001_initial_schema.sql` - Create tables
- `002_add_rls.sql` - Enable RLS policies
- Future: `003_*.sql`, `004_*.sql`, ...

---

## Monitoring

### Current Monitoring

**Modal.com**:
- Built-in logs (modal app logs)
- GPU utilization (Modal dashboard)
- Function call counts
- Error rates

**Supabase**:
- Query performance (dashboard)
- Database size (dashboard)
- Connection pool stats

**FastAPI**:
- uvicorn access logs
- Debug logs (development)

### Future Monitoring (Honeycomb)

**Planned** (Q1 2026):
- Structured logging
- Distributed tracing
- Custom metrics
- Alerting

**See**: `docs/tracks/observability/OBSERVABILITY_STATUS.md`

---

## Cost Analysis

### Monthly Costs (Low Traffic)

**Modal.com** (~$100/month):
- GPU compute: $80/month (H100 usage)
- Function calls: $10/month
- Storage: $5/month
- Network: $5/month

**Supabase** ($25/month):
- Pro plan: $25/month base
- Database storage: Included (8GB)
- Bandwidth: Included (50GB)

**Other** (~$0/month):
- Domain: N/A (using localhost)
- CDN: N/A (no static assets)
- Monitoring: Free tier (future Honeycomb)

**Total**: ~$125/month

### Cost Optimization Strategies

**GPU Selection**:
- Use L40S for staging ($1.00/hr vs $2.50/hr)
- Use T4 for development ($0.30/hr)
- Reserve H100 for production

**Caching**:
- Cache validation results (H17 ValidationCache)
- Cache common prompts (Redis - future)
- Cache LLM responses (expensive calls)

**Batching**:
- Batch multiple requests (reduce overhead)
- Use vLLM batching (automatic)

**Monitoring**:
- Track cost per request
- Alert on spikes (>$200/day)
- Optimize hot paths

---

## Known Issues & Limitations

### Current Limitations

**Cold Starts**:
- First Modal call: ~3 minutes (GPU allocation)
- Subsequent calls: ~2.7s (warm)
- **Mitigation**: Keep-alive requests (future)

**Success Rate**:
- 60% real success rate (prompt → working code)
- 20% syntax errors
- 20% logic errors
- **Mitigation**: Better prompts, validation, retry logic

**Single Region**:
- Modal: US East (no multi-region)
- Supabase: US East (single region)
- **Mitigation**: Not needed for current scale

### Technical Debt

**Infrastructure**:
- No automated backups (rely on Supabase)
- No disaster recovery plan
- No load testing
- No capacity planning

**Monitoring**:
- Limited observability (logs only)
- No distributed tracing
- No custom metrics
- No alerting

---

## Roadmap

### Q4 2025

**October** (Now):
- Infrastructure stable ✅
- Focus on application features (DSPy, ICS)

**November**:
- Performance optimization (reduce latency)
- Cost analysis and optimization

**December**:
- Capacity planning
- Load testing
- Security hardening

### Q1 2026

**January**:
- Observability (Honeycomb integration)
- Monitoring and alerting
- Cost tracking dashboards

**February**:
- Multi-region planning (if needed)
- CDN setup (for frontend)
- API rate limiting

**March**:
- Disaster recovery plan
- Automated backups
- Security audit

---

## Resources

### Documentation

- **llguidance Migration**: `docs/planning/LLGUIDANCE_INTEGRATION.md`
- **Supabase Setup**: `docs/supabase/SUPABASE_QUICK_START.md`
- **Phase 3 Fixes**: `docs/planning/PHASE3_INFRASTRUCTURE_FIXES_STATUS.md`

### External Links

- **Modal.com Docs**: https://modal.com/docs
- **Supabase Docs**: https://supabase.com/docs
- **llguidance**: https://github.com/guidance-ai/llguidance
- **vLLM**: https://docs.vllm.ai

### Internal References

- **Master Roadmap**: `docs/MASTER_ROADMAP.md`
- **Observability Track**: `docs/tracks/observability/OBSERVABILITY_STATUS.md`

---

## Quick Commands

```bash
# Modal deployment
modal deploy lift_sys/modal_app.py
modal app list
modal app logs lift-sys --follow
modal app stop lift-sys

# Supabase migrations
python scripts/database/run_migrations.py

# Local development
uv run uvicorn lift_sys.api.server:app --reload --port 8000

# Health check
curl http://localhost:8000/health

# Modal secrets
modal secret list
modal secret create supabase SUPABASE_URL="..." SUPABASE_ANON_KEY="..."
```

---

**End of Infrastructure Track Status**

**For next session**: Infrastructure is stable. Focus on application features or performance optimization.
