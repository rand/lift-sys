---
track: infrastructure
document_type: optimization_strategy
status: complete
priority: P1
completion: 100%
last_updated: 2025-10-26
session_protocol: |
  For new Claude Code session:
  1. Modal cost optimization is COMPLETE (implemented in lift-sys-374)
  2. Dev mode: 120s scaledown (~$0.13/request), Demo mode: 600s (~$0.67/request)
  3. A100-80GB GPU: $4.00/hour when active, per-second billing
  4. Monthly estimate: ~$30-50 for development (20 hours/week)
  5. Use this as reference for cost management decisions
related_docs:
  - docs/tracks/infrastructure/INFRASTRUCTURE_STATUS.md
  - docs/tracks/dspy/DSPY_INTEGRATION_RESULTS.md
  - docs/MASTER_ROADMAP.md
---

# Modal Cost Optimization Strategy

**Date**: 2025-10-26
**Status**: Implemented
**Related Issue**: lift-sys-374

---

## Overview

Cost-optimized Modal deployment for development and testing phases, with demo mode for presentations. Proactive resource management minimizes costs while maintaining usability.

## Cost Model

### GPU Pricing
- **A100-80GB**: $4.00/hour when active
- **Billing**: Per-second, only when container running

### Cost Breakdown by Mode

| Mode | Scaledown | Hourly Equivalent | Use Case |
|------|-----------|-------------------|----------|
| **DEV** | 120s | ~$0.13 per request | Development, testing (cold starts OK) |
| **DEMO** | 600s | ~$0.67 per request | Presentations, demos (minimize cold starts) |
| **PROD** | 300s | ~$0.33 per request | Future production use |

### Monthly Cost Estimates

**Development usage (20 hours/week, stopped when not in use):**
```
Active time: 20 hrs/week × 4 weeks = 80 hours
Cost: 80 × $4.00 = $320/month
```

**Careless usage (forget to stop, 10 min scaledown):**
```
Active time: 80 hours
Idle time: ~40 hours (10 min buffers after requests)
Cost: 120 × $4.00 = $480/month
```

**With proactive stopping (this strategy):**
```
Active time: 80 hours
Idle time: ~10 hours (2 min buffers in dev mode)
Cost: 90 × $4.00 = $360/month
Savings: $120-160/month vs careless usage
```

---

## Modes

### DEV Mode (Default)

**Configuration:**
```bash
MODAL_MODE=dev
SCALEDOWN_WINDOW=120  # 2 minutes
```

**Use for:**
- Daily development work
- Backend testing
- Integration tests
- Any work where 3-7 min cold starts are acceptable

**Cost profile:**
- Container stops 2 minutes after last request
- Minimal idle costs
- Cold start on first request after idle

**Start:**
```bash
./scripts/modal/start_dev.sh
```

### DEMO Mode

**Configuration:**
```bash
MODAL_MODE=demo
SCALEDOWN_WINDOW=600  # 10 minutes
```

**Use for:**
- Live presentations
- User demos
- Stakeholder reviews
- Testing sessions where responsiveness matters

**Cost profile:**
- Container stays warm for 10 minutes
- Reduces cold starts during demo
- Higher idle costs (but time-limited)

**Start:**
```bash
./scripts/modal/start_demo.sh
```

**⚠️ IMPORTANT:** Always stop after demo!

### PROD Mode (Future)

**Configuration:**
```bash
MODAL_MODE=prod
SCALEDOWN_WINDOW=300  # 5 minutes
```

**Use for:**
- Production deployment with paying users
- Balanced cost/latency for moderate traffic

**Not implemented yet** - requires additional monitoring, SLA tracking.

---

## Workflow

### Starting a Dev Session

```bash
# 1. Start Modal in dev mode
./scripts/modal/start_dev.sh

# 2. Work on your features
# (cold start on first request: 3-7 minutes)

# 3. Subsequent requests are fast (if within 2 min)
# (warm response: ~2-10 seconds)

# 4. Stop when done
./scripts/modal/stop_session.sh
```

### Demo Workflow

```bash
# 1. Start in demo mode (10 min before demo)
./scripts/modal/start_demo.sh
# (This warms up the model proactively)

# 2. Give your demo
# (All requests fast, 10 min buffer between interactions)

# 3. IMMEDIATELY after demo, stop
./scripts/modal/stop_session.sh
```

### End-of-Day Routine

```bash
# Always run before closing your laptop
./scripts/modal/stop_session.sh
```

---

## Scripts

### `start_dev.sh`

**Purpose:** Start Modal inference in cost-optimized dev mode

**What it does:**
1. Sets `MODAL_MODE=dev`
2. Deploys lift-sys-inference app
3. Runs health check
4. Reminds you to stop when done

**Output:**
```
🚀 Starting Modal inference in DEV mode...

Configuration:
  Mode: DEV (cost-optimized)
  Scaledown: 120 seconds
  GPU: A100-80GB (~$4/hr when active)
  Cost: ~$0.13 per active request + 2min buffer

💡 Cold starts expected (3-7 min first request)
💡 Remember to stop when done: ./scripts/modal/stop_session.sh
```

### `start_demo.sh`

**Purpose:** Start Modal inference in demo mode with warmup

**What it does:**
1. Sets `MODAL_MODE=demo`
2. Deploys lift-sys-inference app
3. Runs health check
4. **Warms up model proactively** (3-7 min)
5. Warns you to stop after demo

**Output:**
```
🎬 Starting Modal inference in DEMO mode...

Configuration:
  Mode: DEMO (presentation-optimized)
  Scaledown: 600 seconds (10 minutes)
  Cost: ~$0.67 per request + 10min buffer

⚡ Stays warm for 10 minutes between requests
⚠️  IMPORTANT: Stop after demo to avoid costs!
```

### `stop_session.sh`

**Purpose:** Proactively stop all Modal apps

**What it does:**
1. Lists currently running apps
2. Stops all known lift-sys apps
3. Verifies no apps running
4. Confirms cost savings activated

**Output:**
```
🛑 Stopping all Modal apps...

Stopping lift-sys-inference...
✅ Stopped 1 app(s)

💰 Cost savings activated!
🎯 All clear! No Modal resources running.
```

---

## Best Practices

### ✅ DO

1. **Stop resources when done:**
   ```bash
   ./scripts/modal/stop_session.sh  # End of session
   ```

2. **Use dev mode by default:**
   ```bash
   ./scripts/modal/start_dev.sh  # Cost-optimized
   ```

3. **Reserve demo mode for actual demos:**
   ```bash
   ./scripts/modal/start_demo.sh  # Only when needed
   ```

4. **Check running apps periodically:**
   ```bash
   modal app list  # Should be empty when not working
   ```

5. **Set calendar reminders:**
   - End of workday: Run stop_session.sh
   - Before leaving for vacation: Run stop_session.sh

### ❌ DON'T

1. **Don't deploy and forget:**
   ```bash
   modal deploy ...  # Then walk away → costs accrue!
   ```

2. **Don't use demo mode for development:**
   - 10 min scaledown wastes money during dev

3. **Don't enable `keep_warm=1`:**
   - Costs $2,880/month (24/7 runtime)
   - Not justified until production with users

4. **Don't run multiple instances:**
   - Check `modal app list` before starting new session

---

## Monitoring

### Daily Check

```bash
# Morning: Verify nothing running
modal app list

# Start dev session
./scripts/modal/start_dev.sh

# Work...

# End of day: Stop everything
./scripts/modal/stop_session.sh
modal app list  # Verify stopped
```

### Weekly Budget Check

```bash
# Check Modal dashboard for costs
# Target: <$100/week during development

# If costs are high, audit:
# - Are you stopping resources?
# - Check `modal app list` frequently
# - Review deployment history
```

### Cost Alerts (Recommended)

Set up Modal billing alerts:
1. Go to Modal dashboard
2. Settings → Billing
3. Add alert: $500/month threshold
4. Add alert: $100/week threshold

---

## Migration Path

### Phase 1: Development (Now)

**Strategy:** Aggressive cost optimization
```
Mode: DEV (120s scaledown)
Sessions: Stop proactively when done
Cost target: $300-400/month
```

### Phase 2: Beta Testing

**Strategy:** Demo mode during testing sessions
```
Mode: DEV (default) + DEMO (during tests)
Sessions: 2-3 hour testing windows
Cost target: $400-600/month
```

### Phase 3: Production

**Strategy:** Persistent deployment, balanced scaledown
```
Mode: PROD (300s scaledown)
Monitoring: SLA tracking, error alerts
Cost target: Variable with traffic
Decision point: Revenue justifies always-on
```

### Phase 4: Scale (Future)

**Strategy:** Consider `keep_warm=1` if justified
```
Trigger: >100 DAU or strict SLA requirements
Mode: PROD with keep_warm=1
Cost: $2,880/month base + additional traffic
ROI: Justified by revenue or business value
```

---

## Troubleshooting

### "App not found" when stopping

```bash
modal app list  # Check actual app names
# Update APPS array in stop_session.sh if needed
```

### Cold starts too slow for testing

```bash
# Use demo mode temporarily
./scripts/modal/start_demo.sh

# Or manually warm up
curl https://rand--warmup.modal.run
```

### Forgot to stop overnight

```bash
# Stop immediately
./scripts/modal/stop_session.sh

# Check Modal dashboard for costs
# Typical overnight cost (10 min scaledown): ~$20-40
```

### Want to check costs before running

```bash
# DEV mode cost per request
# Active: ~1 min inference + 2 min buffer = 3 min
# Cost: (3/60) × $4 = $0.20 per request

# DEMO mode cost per request
# Active: ~1 min inference + 10 min buffer = 11 min
# Cost: (11/60) × $4 = $0.73 per request
```

---

## Decision Matrix

**When to use each mode:**

```
Working on backend/tests?
  → Use DEV mode (cold starts OK)

Giving a presentation?
  → Use DEMO mode (pre-warm, stop after)

End of day?
  → ALWAYS stop resources

On vacation?
  → Verify everything stopped

Production launch?
  → Upgrade to PROD mode (separate discussion)

Need <1s response always?
  → Not yet - wait for production phase
```

---

## Summary

**Current Strategy (Phase 1: Development):**
- ✅ DEV mode by default (120s scaledown)
- ✅ DEMO mode for presentations (600s scaledown)
- ✅ Proactive stopping (scripts/modal/stop_session.sh)
- ✅ No `keep_warm` (saves $2,500+/month)
- ✅ Cost target: $300-400/month

**Key Behaviors:**
1. Start session: `./scripts/modal/start_dev.sh`
2. Work with cold starts (3-7 min)
3. Stop when done: `./scripts/modal/stop_session.sh`
4. Reserve demo mode for actual demos

**Cost Savings vs Alternatives:**
- vs. `keep_warm=1`: Save $2,520/month ($2,880 - $360)
- vs. 10min scaledown always: Save $120/month ($480 - $360)
- vs. manual `modal deploy`: Systematic stopping prevents waste

**This strategy is appropriate for development phase. Revisit when launching to users.**
