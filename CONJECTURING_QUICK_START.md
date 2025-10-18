# Conjecturing Framework: Quick Start Guide
## TL;DR for Immediate Action

**Status**: Ready to begin Phase 1
**First Task**: lift-sys-232
**Time to First Milestone**: 1 week

---

## What Is This?

Implement **conjecturing framework** (from arXiv:2510.11986) to separate:
- **IR generation** (conjecturing) - What we want to build
- **Code generation** (formalisation) - How we build it

**Why**: Currently stuck at 83.3% success with 3 persistent failures. Can't tell if problem is in IR quality or code quality.

---

## 30-Second Overview

```
Current:  Prompt → [Black Box] → Code (83.3% success)
                    ↑ Can't see inside

Proposed: Prompt → IR Skeleton → Fill Holes → Validate → Code
                      ↓            ↓           ↓         ↓
                   Measure    Measure    Measure   Measure
                   Each       Step       Independently
```

**Goal**: >95% success rate with clear diagnostic visibility.

---

## Work Items Created

**Total**: 18 Beads work items (lift-sys-230 through lift-sys-247)

| Phase | Items | Effort | Goal |
|-------|-------|--------|------|
| Epic | 1 | N/A | Overall coordination |
| Phase 1 | 6 | 8-12 hours (1 week) | Identify bottleneck |
| Phase 2 | 10 | 40-60 hours (2-3 weeks) | Implement framework |
| Phase 3 | 1 | 120-180 hours (4-6 weeks) | CSP integration (optional) |

---

## Start Here: Phase 1 (This Week)

**Goal**: Figure out WHERE the problem is (IR vs code)

### Step 1: Check out the work (5 min)

```bash
# View epic
bd show lift-sys-230

# View Phase 1 main task
bd show lift-sys-231

# List all Phase 1 tasks
bd list -p 1 -t task | grep "23[2-6]"
```

### Step 2: Start first task (lift-sys-232)

```bash
# Mark as in progress
bd update lift-sys-232 --status in-progress

# Read the task
bd show lift-sys-232
```

### Step 3: Implement (2-3 hours)

**File**: `debug/collect_failure_samples.py`

**Add**: `evaluate_conjecture_quality()` function
- Extract constraints from IR
- Compare to expected constraints (ground truth)
- Calculate completeness metric

**See**: `docs/CONJECTURING_TECHNICAL_SPEC.md` Section 1.3 for implementation details

### Step 4: Next tasks (5-6 hours)

```bash
# After completing lift-sys-232:
bd update lift-sys-232 --status done
bd update lift-sys-233 --status in-progress  # Constraint preservation

# Then:
# lift-sys-234: Analysis script
# lift-sys-235: Collect samples
# lift-sys-236: Generate report & decide
```

### Step 5: Decision point (Friday)

**Output**: `DIAGNOSTIC_REPORT_CONJECTURING.md`

**Decision**:
- ✅ If bottleneck = CONJECTURING → Proceed to Phase 2
- ❌ If bottleneck = FORMALISATION → Pivot to semantic validation
- ⚠️ If unclear → Collect more data

---

## Phase 1 Checklist

Use this to track progress:

```markdown
Phase 1: Diagnostic Enhancement (lift-sys-231)
├─ [ ] lift-sys-232: Add conjecture quality evaluation
├─ [ ] lift-sys-233: Add constraint preservation measurement
├─ [ ] lift-sys-234: Create bottleneck analysis script
├─ [ ] lift-sys-235: Collect 36 diagnostic samples
└─ [ ] lift-sys-236: Generate report and make decision

Deliverables:
├─ [ ] Modified debug/collect_failure_samples.py
├─ [ ] New debug/analyze_conjecturing_bottleneck.py
└─ [ ] DIAGNOSTIC_REPORT_CONJECTURING.md

Success Criteria:
├─ [ ] 36 samples collected (12 per failing test)
├─ [ ] Constraint completeness measured
├─ [ ] Constraint preservation measured
├─ [ ] Bottleneck identified with confidence level
└─ [ ] Clear recommendation for next steps
```

---

## Quick Commands Reference

### View work items

```bash
# Show epic with all dependencies
bd show lift-sys-230 --deps

# List Phase 1 tasks
bd list -p 1 -t task

# List Phase 2 tasks
bd list -p 2 -t task

# Show specific task
bd show lift-sys-232
```

### Update status

```bash
# Start working on task
bd update lift-sys-232 --status in-progress

# Complete task
bd update lift-sys-232 --status done

# Block task (if stuck)
bd update lift-sys-232 --status blocked

# Add notes
bd update lift-sys-232 --comment "Implemented evaluation function, 90% complete"
```

### Track progress

```bash
# See all open P1 tasks
bd list -p 1 -s open

# See what's in progress
bd list -s in_progress

# See what's done
bd list -s done
```

---

## Key Documents

**Read First** (in order):
1. `CONJECTURING_RESEARCH_REPORT.md` - Research summary (15 min read)
2. `CONJECTURING_IMPLEMENTATION_PLAN.md` - High-level plan (10 min read)
3. `docs/CONJECTURING_TECHNICAL_SPEC.md` - Implementation details (reference)

**Track Progress**:
- `CONJECTURING_BEADS_SUMMARY.md` - All work items and dependencies

**Implementation Reference**:
- `docs/CONJECTURING_TECHNICAL_SPEC.md` - Detailed specifications
- `CONSTRAINT_PROPAGATION_TYPED_HOLES.md` - CSP design (Phase 3)

---

## Success Metrics

| Metric | Baseline | Phase 1 | Phase 2 | Phase 3 |
|--------|----------|---------|---------|---------|
| **E2E Success** | 83.3% | Measure | >88% | >95% |
| **IR Quality** | Unknown | Measure | >90% | >95% |
| **Completeness** | Unknown | Measure | >80% | >90% |
| **Preservation** | Unknown | Measure | >70% | >85% |

---

## Phase Transition Criteria

### Phase 1 → Phase 2
- ✅ Bottleneck = CONJECTURING (high confidence)
- ✅ IR constraint completeness < 80%
- ✅ Team approval for 2-3 week implementation

### Phase 2 → Phase 3
- ✅ Phase 2 complete and deployed
- ✅ E2E success 88%+ but <95%
- ✅ Complex dependencies identified
- ✅ Team approval for 4-6 week implementation

### Phase 2 → Done
- ✅ E2E success >95%
- ✅ No need for further sophistication

---

## Troubleshooting

**Q: Where do I start?**
→ Read `CONJECTURING_RESEARCH_REPORT.md`, then start lift-sys-232

**Q: What if I don't understand the conjecturing concept?**
→ Read Section 2 of `CONJECTURING_RESEARCH_REPORT.md` (The Typed Hole ≈ Missing Conjecture Parallel)

**Q: What if Phase 1 shows bottleneck is NOT conjecturing?**
→ Don't do Phase 2. Pivot to semantic validation or LLM repair (see STRATEGIC_ASSESSMENT)

**Q: How do I know if I'm on track?**
→ Phase 1 should take 1 week. If blocked for >2 days, reassess.

**Q: Can I skip Phase 1 and go straight to implementation?**
→ No. Phase 1 validates the approach. Don't build before we know where the problem is.

---

## Who to Ask

**Questions about**:
- Research paper concepts → See `CONJECTURING_RESEARCH_REPORT.md` Appendix A
- Implementation details → See `docs/CONJECTURING_TECHNICAL_SPEC.md`
- Beads workflow → See `CONJECTURING_BEADS_SUMMARY.md`
- Strategic direction → See `STRATEGIC_ASSESSMENT_2025-10-17.md`

**Stuck?**:
1. Check documentation first
2. Add comment to Beads work item
3. Create new work item if significant issue

---

## Timeline Expectations

**Phase 1** (This week):
- Mon-Tue: Implement evaluation functions
- Wed-Thu: Collect and analyze samples
- Fri: Decision meeting

**Phase 2** (If approved, 2-3 weeks):
- Week 1: Core components (skeleton, conjecture, validator)
- Week 2: Integration and testing
- Week 3: Benchmark and deploy

**Phase 3** (If needed, 4-6 weeks):
- Weeks 1-2: CSP implementation
- Weeks 3-4: Integration and testing
- Weeks 5-6: Optimization and deployment

---

## Critical Success Factors

1. **Don't skip Phase 1** - Validate before building
2. **Measure independently** - Separate IR quality from code quality
3. **Data-driven decisions** - Let metrics guide, not intuition
4. **Clear go/no-go** - If Phase 1 says "no", pivot
5. **Incremental** - Can stop after any phase

---

## Quick Wins

**After 1 day**: Evaluation functions implemented
**After 3 days**: Diagnostic samples collected
**After 1 week**: Clear understanding of bottleneck
**After 3 weeks**: (If Phase 2) Two-phase IR generation working
**After 2 months**: (If Phase 3) >95% success rate achieved

---

## Next Actions (Right Now)

1. ✅ Read research report (15 min)
2. ✅ Review technical spec Phase 1 section (10 min)
3. ✅ Start lift-sys-232 (mark in-progress)
4. ⏳ Implement `evaluate_conjecture_quality()` (2-3 hours)
5. ⏳ Move to lift-sys-233 (constraint preservation)

**First commit**: Modified `debug/collect_failure_samples.py` with conjecture evaluation

**First measurement**: Constraint completeness for count_words, find_index, is_valid_email

**First insight**: Whether IR quality or codegen quality is the bottleneck

---

**Ready to start? Begin with lift-sys-232** ✨

```bash
bd update lift-sys-232 --status in-progress
```
