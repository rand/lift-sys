# Honeycomb Observability Integration - Work Breakdown

**Date**: 2025-10-19
**Epic**: lift-sys-265
**Total Tasks**: 6
**Estimated Effort**: 8.5 hours over 4 days
**Priority**: P0 (Foundation for production readiness)

---

## Overview

This document summarizes the Beads work items created for the Honeycomb observability integration. For implementation details, see [HONEYCOMB_INTEGRATION_PLAN.md](./HONEYCOMB_INTEGRATION_PLAN.md).

---

## Work Items

### Epic: lift-sys-265

**Title**: Epic: Honeycomb Observability Integration

**Status**: Open
**Priority**: P0
**Type**: Epic

**Description**:
Integrate Honeycomb observability platform with OpenTelemetry to enable distributed tracing, performance monitoring, and error tracking across lift-sys.

**Goals**:
- Deploy production observability without compromising performance
- Track request flows from API → Session → IR → Code → LLM
- Monitor costs, latency, and errors in real-time
- Alert on degraded service quality

**Success Criteria**:
- All traces flowing to Honeycomb
- <5% performance overhead
- Free tier budget compliance (20M events/month)
- Team onboarded and using dashboards

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md (12 sections, 1,900+ lines)

---

### Task 1: lift-sys-266

**Title**: Setup OpenTelemetry and Honeycomb foundation

**Status**: Open
**Priority**: P0
**Type**: Task
**Estimate**: 1.5 hours
**Depends On**: lift-sys-265 (epic)
**Phase**: 1 - Foundation

**Key Activities**:
- Create Honeycomb account (free tier)
- Generate API key in Honeycomb UI
- Add `HONEYCOMB_API_KEY` to Modal secrets
- Create `lift_sys/observability/` module
- Add OpenTelemetry dependencies to `pyproject.toml`
- Write initialization code (TracerProvider, OTLP exporter, Resource)
- Deploy to Modal

**Deliverables**:
- `lift_sys/observability/__init__.py` (new)
- `lift_sys/observability/tracing.py` (new)
- `pyproject.toml` updated with 6 OpenTelemetry packages
- Modal secrets configured

**Acceptance Criteria**:
- ✅ Module imports without errors
- ✅ Secrets accessible in Modal environment
- ✅ Code review passed
- ✅ No instrumentation active yet (foundation only)

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md Section 6.1

---

### Task 2: lift-sys-267

**Title**: Enable auto-instrumentation (FastAPI, HTTP, DB)

**Status**: Open
**Priority**: P0
**Type**: Task
**Estimate**: 1 hour
**Depends On**: lift-sys-266
**Phase**: 2 - Auto-Instrumentation

**Key Activities**:
- Call `FastAPIInstrumentor.instrument_app()` on startup
- Call `HTTPXInstrumentor.instrument()` for HTTP clients
- Call `SQLAlchemyInstrumentor.instrument()` for database (when Supabase integrated)
- Update `lift_sys/api/server.py` to call `setup_observability()`
- Deploy to Modal
- Verify traces appear in Honeycomb UI

**Deliverables**:
- `lift_sys/api/server.py` updated
- Auto-instrumentation active
- Traces flowing to Honeycomb

**Acceptance Criteria**:
- ✅ HTTP requests generate root spans with `http.*` attributes
- ✅ `service.name = "lift-sys"` visible in Honeycomb
- ✅ All FastAPI endpoints traced automatically
- ✅ No errors in Modal logs

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md Section 6.2

---

### Task 3: lift-sys-268

**Title**: Implement core instrumentation (Session, IR, Code)

**Status**: Open
**Priority**: P0
**Type**: Task
**Estimate**: 2.5 hours
**Depends On**: lift-sys-267
**Phase**: 3 - Manual Instrumentation

**Key Activities**:
- Instrument `PromptSessionManager.create_from_prompt()` with `session.*` attributes
- Instrument IR generation operations with `ir.*` attributes
- Instrument code generation operations with `code.*` attributes
- Instrument LLM provider calls with `llm.*` attributes (provider, model, tokens, cost)
- Add error tracking (`span.set_status`, `span.record_exception`)
- Deploy and verify end-to-end traces

**Deliverables**:
- `lift_sys/spec_sessions/manager.py` updated
- `lift_sys/ir/` instrumented
- `lift_sys/code_gen/` instrumented
- `lift_sys/providers/` instrumented with cost tracking

**Acceptance Criteria**:
- ✅ `session.create` spans visible in Honeycomb
- ✅ LLM calls tracked with cost (`llm.cost_usd` attribute)
- ✅ Errors captured in spans with stack traces
- ✅ End-to-end trace tree correct: root → session → ir → code → llm

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md Section 6.3

---

### Task 4: lift-sys-269

**Title**: Create Honeycomb dashboards and queries

**Status**: Open
**Priority**: P0
**Type**: Task
**Estimate**: 1.5 hours
**Depends On**: lift-sys-268
**Phase**: 4 - Dashboards

**Key Activities**:
- Create "Request Overview" dashboard (6 widgets)
- Create "Performance Analysis" dashboard (6 widgets)
- Create "Error Tracking" dashboard (6 widgets)
- Create "Business Metrics" dashboard (6 widgets)
- Save 5+ common queries (slow requests, high cost, error analysis)
- Export dashboard JSON
- Document dashboard usage

**Deliverables**:
- 4 dashboards created in Honeycomb UI
- 5+ saved queries
- `docs/honeycomb-dashboards.json` (exported)
- `docs/HONEYCOMB_DASHBOARDS.md` (documentation)

**Acceptance Criteria**:
- ✅ All dashboards render data correctly
- ✅ Queries execute in <5 seconds
- ✅ Team can navigate and use dashboards

**Dashboard Specifications**:

**1. Request Overview** (6 widgets):
- Request rate (line chart)
- Latency percentiles (heatmap)
- Success rate (line chart)
- Error rate (line chart)
- Top endpoints (bar chart)
- User activity (table)

**2. Performance Analysis** (6 widgets):
- Slowest operations (table)
- IR generation time (histogram)
- Code generation time (histogram)
- LLM provider latency (line chart)
- Database query performance (table)
- Retry rate (line chart)

**3. Error Tracking** (6 widgets):
- Error rate by type (stacked bar)
- Failed operations (table)
- Error distribution (pie chart)
- Recent errors (table)
- Code generation failures (line chart)
- LLM provider errors (stacked area)

**4. Business Metrics** (6 widgets):
- Sessions created (line chart)
- Session completion rate (line chart)
- Holes resolved (line chart)
- Average holes per session (line chart)
- Cost per request (line chart)
- Token usage (stacked area)

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md Section 7

---

### Task 5: lift-sys-270

**Title**: Configure alerting and SLOs

**Status**: Open
**Priority**: P0
**Type**: Task
**Estimate**: 1.5 hours
**Depends On**: lift-sys-269
**Phase**: 5 - Alerting

**Key Activities**:
- Define 2 SLOs (p95 latency <10s, success rate >95%)
- Create 5 alerts (high error rate, slow requests, cost spike, LLM failures, DB errors)
- Configure Slack integration
- Test each alert with synthetic conditions
- Document runbooks for alert response
- Write alert escalation procedures

**Deliverables**:
- 2 SLOs configured in Honeycomb
- 5+ alerts active
- Slack integration working
- `docs/HONEYCOMB_RUNBOOKS.md` (new)
- Alert response procedures documented

**Acceptance Criteria**:
- ✅ Alerts fire on test conditions within 5 minutes
- ✅ Slack notifications delivered with correct links
- ✅ Team can follow runbooks to investigate
- ✅ SLOs track correct metrics

**Alert Specifications**:

**1. High Error Rate**
- Trigger: >10% errors over 5 minutes
- Severity: P1 (page on-call)
- Channel: #engineering-alerts

**2. Slow Requests**
- Trigger: p95 >10s over 5 minutes
- Severity: P2 (notify team)
- Channel: #performance

**3. LLM Cost Spike**
- Trigger: >$5/hour
- Severity: P2 (notify team)
- Channel: #engineering-alerts

**4. LLM Provider Failure**
- Trigger: >50% LLM errors over 5 minutes
- Severity: P1 (page on-call)
- Channel: #engineering-alerts

**5. Database Connection Errors**
- Trigger: >10 errors over 5 minutes
- Severity: P0 (immediate page)
- Channel: #engineering-alerts

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md Sections 8 & Appendix B

---

### Task 6: lift-sys-271

**Title**: Validate integration and complete documentation

**Status**: Open
**Priority**: P1
**Type**: Task
**Estimate**: 1 hour
**Depends On**: lift-sys-270
**Phase**: Validation & Documentation

**Key Activities**:
- Run 4 acceptance tests (end-to-end trace, error tracking, high cardinality, alert firing)
- Verify performance overhead <5% with profiling
- Verify event volume within budget (Honeycomb UI)
- Conduct team training session (1 hour)
- Complete `HONEYCOMB_QUICK_START.md`
- Complete `HONEYCOMB_RUNBOOKS.md`
- Review all documentation for accuracy
- Export Beads state

**Deliverables**:
- All 4 acceptance tests passed
- Performance benchmarks documented
- Team trained (attendance recorded)
- `HONEYCOMB_QUICK_START.md` complete
- `HONEYCOMB_RUNBOOKS.md` complete
- `HONEYCOMB_PLANNING_COMPLETE.md` with final checklist

**Acceptance Criteria**:
- ✅ Zero production incidents from instrumentation
- ✅ Team using dashboards daily
- ✅ All documentation reviewed and approved
- ✅ Integration marked complete in Beads

**Acceptance Tests**:

**Test 1: End-to-End Trace**
- Scenario: Create session → Generate IR → Generate code
- Expected: Full trace tree with all spans and attributes

**Test 2: Error Tracking**
- Scenario: Trigger ValidationError during code generation
- Expected: Error captured in span, visible in dashboard

**Test 3: High Cardinality Query**
- Scenario: Find slowest requests per user
- Expected: Query executes in <5 seconds with accurate results

**Test 4: Alert Firing**
- Scenario: Simulate high error rate (>10% over 5 minutes)
- Expected: Alert fires, Slack notification received, runbook linked

**Reference**: HONEYCOMB_INTEGRATION_PLAN.md Section 12

---

## Timeline & Dependencies

```
Day 1 (2 hours):
  lift-sys-266: Setup foundation (1.5h)
  lift-sys-267: Enable auto-instrumentation (1h)
  ↓
Day 2 (2.5 hours):
  lift-sys-268: Implement core instrumentation (2.5h)
  ↓
Day 3 (1.5 hours):
  lift-sys-269: Create dashboards (1.5h)
  ↓
Day 4 (2.5 hours):
  lift-sys-270: Configure alerting (1.5h)
  lift-sys-271: Validate & document (1h)
  ↓
DONE (Total: 8.5 hours)
```

**Dependency Graph**:
```
lift-sys-265 (Epic)
  ↓
lift-sys-266 (Foundation)
  ↓
lift-sys-267 (Auto-instrumentation)
  ↓
lift-sys-268 (Manual instrumentation)
  ↓
lift-sys-269 (Dashboards)
  ↓
lift-sys-270 (Alerting)
  ↓
lift-sys-271 (Validation)
```

---

## Cost Estimate

**Honeycomb Costs**:
- **Free tier**: 20M events/month (sufficient for early development)
- **Projected usage at 1000 requests/day**: 180k events/month (~1% of free tier)
- **Projected usage at 10k requests/day**: 1.8M events/month (~9% of free tier)
- **Upgrade to Pro tier**: Only needed at ~100k requests/day (18M events/month), ~$100/mo

**Development Time**: 8.5 hours @ $150/hour = $1,275

**Total Cost** (Year 1): $1,275 (one-time) + $0/mo (free tier) = **$1,275**

---

## Success Metrics

After integration completion:

**Performance**:
- ✅ Instrumentation overhead <5% latency increase
- ✅ Memory overhead <10 MB/container
- ✅ CPU overhead <2%

**Observability Coverage**:
- ✅ 100% of HTTP requests traced
- ✅ 100% of LLM calls tracked with cost
- ✅ 100% of errors captured
- ✅ All critical operations instrumented

**Team Adoption**:
- ✅ All engineers trained on Honeycomb UI
- ✅ Dashboards checked daily
- ✅ Alerts responded to within SLA

**Budget Compliance**:
- ✅ Event volume <20M/month (free tier)
- ✅ No unexpected Honeycomb bills

---

## Post-Integration Monitoring

**Week 1 Actions**:
- Review dashboards daily
- Verify event volume within budget
- Check for error spikes
- Ensure alerts not firing excessively

**Month 1 Actions**:
- Review SLO compliance (p95 <10s, success >95%)
- Analyze slow queries for optimization
- Refine dashboards based on team feedback
- Adjust alert thresholds if needed

**Month 3 Actions**:
- Review cost vs budget
- Evaluate need for Pro tier based on growth
- Document lessons learned
- Plan for tail-based sampling if needed

---

## Related Documents

**Planning**:
- [HONEYCOMB_INTEGRATION_PLAN.md](./HONEYCOMB_INTEGRATION_PLAN.md) - Comprehensive implementation spec (12 sections, 1,900+ lines)
- [HONEYCOMB_QUICK_START.md](./HONEYCOMB_QUICK_START.md) - 30-minute setup guide
- [HONEYCOMB_PLANNING_COMPLETE.md](./HONEYCOMB_PLANNING_COMPLETE.md) - Final checklist and sign-off

**Supabase Integration** (parallel workstream):
- [SUPABASE_INTEGRATION_PLAN.md](./SUPABASE_INTEGRATION_PLAN.md) - Database integration (lift-sys-259 through 264)
- [SUPABASE_BEADS_SUMMARY.md](./SUPABASE_BEADS_SUMMARY.md) - Work breakdown

**Strategic Context**:
- [INFRASTRUCTURE_RESEARCH_REPORT.md](./INFRASTRUCTURE_RESEARCH_REPORT.md) - Infrastructure strategy (Modal + Supabase recommended)
- [SEMANTIC_IR_ROADMAP.md](./SEMANTIC_IR_ROADMAP.md) - Product roadmap

---

## Questions & Support

**For implementation questions**:
- See HONEYCOMB_INTEGRATION_PLAN.md Section 10 (Deployment Plan)
- See HONEYCOMB_QUICK_START.md (step-by-step guide)
- Honeycomb docs: https://docs.honeycomb.io/getting-started/

**For Beads workflow**:
- Update status: `bd update lift-sys-266 --status in_progress`
- Close task: `bd close lift-sys-266 --reason "Foundation deployed, traces flowing"`
- Export state: `bd export -o .beads/issues.jsonl`

**For technical support**:
- OpenTelemetry Python docs: https://opentelemetry.io/docs/languages/python/
- Honeycomb community: https://pollinators.honeycomb.io/

---

**Status**: Planning complete, ready for implementation
**Next Action**: Claim lift-sys-266 and start foundation setup
**Owner**: Engineering team
**Estimated Completion**: 4 days from start
