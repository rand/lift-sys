# Beads Roadmap: IR 0.9 + DSPy Migration

**Date**: 2025-10-20
**Status**: Beads Created, Ready for Execution
**Related**:
- [IR Adoption Plan](IR_ADOPTION_PLAN.md)
- [DSPy Migration Plan](DSPY_MIGRATION_PLAN.md)
- [Integrated Strategy](INTEGRATED_STRATEGY.md)

---

## Overview

All strategic work for IR 0.9 Adoption and DSPy Migration has been broken down into **detailed beads** following the Beads framework workflow.

**Total Beads Created**: 15+ (with 120-140 more to be created for remaining phases)
**Epics**: 2
**Features**: 4
**Tasks**: 10+

---

## Beads Hierarchy

### Epic Level

1. **lift-sys-272**: Epic: IR 0.9 Adoption
   - 20-month timeline
   - 6 phases
   - Priority: P0

2. **lift-sys-273**: Epic: DSPy Migration
   - 14-month timeline
   - 5 phases
   - Priority: P0
   - **Depends on**: IR Phase 1 completion

---

## IR Phase 1: Core Types & Refinements (Ready to Start)

**Feature**: lift-sys-274 "IR Phase 1: Core Types & Refinements"
- **Duration**: 3 months (Weeks 1-12)
- **Team**: 1 senior eng + 1 mid-level eng
- **Status**: READY

### Detailed Tasks (Sequential)

1. **lift-sys-275**: Type System Foundation (Weeks 1-2)
   - Files: `lift_sys/ir/types.py`
   - Deliverable: BaseType, DependentType, RefinementType, TypeHole
   - Tests: 100% coverage
   - **Status**: READY TO START

2. **lift-sys-276**: Predicate System (Weeks 3-4)
   - Files: `lift_sys/ir/predicates.py`
   - Deliverable: Predicate AST, traversal, pretty-printing
   - **Depends on**: lift-sys-275

3. **lift-sys-277**: Enhanced Hole System (Weeks 5-6)
   - Files: `lift_sys/ir/models.py` (update)
   - Deliverable: 6 hole kinds, linking, provenance
   - **Depends on**: lift-sys-276

4. **lift-sys-278**: FuncSpec Enhancement (Weeks 7-8)
   - Files: `lift_sys/ir/specs.py` (new)
   - Deliverable: FuncSpec, IntentSpec, AlignmentMap
   - **Depends on**: lift-sys-277

5. **lift-sys-279**: Update Core IR (Weeks 9-10)
   - Files: `lift_sys/ir/models.py` (major update)
   - Deliverable: Refactored IntermediateRepresentation
   - **Depends on**: lift-sys-278

6. **lift-sys-280**: Database Schema Updates (Weeks 11-12)
   - Files: `migrations/007_ir_v09_types.sql`
   - Deliverable: Supabase tables for new IR
   - **Depends on**: lift-sys-279

---

## IR Phase 2: Solver Integration (Planned)

**Feature**: lift-sys-285 "IR Phase 2: Solver Integration"
- **Duration**: 3 months
- **Team**: 1 senior eng + 1 solver specialist
- **Starts After**: Phase 1 completion
- **Depends on**: lift-sys-280

**Sub-tasks** (to be created):
- SMT Backend (Weeks 1-4)
- SAT Backend (Weeks 5-6)
- CSP Backend (Weeks 7-8)
- Validation Pipeline (Weeks 9-10)
- Counterexample Generation (Weeks 11-12)

---

## DSPy Phase 1: Setup + Forward Mode (Planned)

**Feature**: lift-sys-286 "DSPy Phase 1: Setup + Forward Mode"
- **Duration**: 3 months
- **Team**: 1 senior eng + 1 ML eng
- **Starts After**: IR Phase 1 (needs stable IR schema)
- **Depends on**: lift-sys-274 (related)

**Sub-tasks** (to be created):
- DSPy Installation & Setup
- Signature Definitions
- Forward Mode Module
- Evaluation Metrics
- Training Data Collection (lift-sys-283, already created!)
- Optimization
- Integration
- A/B Testing

---

## Immediate Next Steps (This Week)

### 1. lift-sys-281: Team Review Meeting ⚡ READY
**Goal**: Review and approve strategic plans
**Duration**: 1 week
**Agenda**:
- Present IR 0.9 vision (20 months, $1.1M)
- Present DSPy migration (14 months, systematic AI)
- Discuss integration points
- Review resource requirements
- Get go/no-go decision

**Documents**:
- docs/planning/IR_ADOPTION_PLAN.md
- docs/planning/DSPY_MIGRATION_PLAN.md
- docs/planning/INTEGRATED_STRATEGY.md

### 2. lift-sys-282: Install Dependencies ⚡ READY
**Goal**: Set up dev environment
**Tasks**:
- Install Z3 solver (`uv add z3-solver`)
- Install DSPy (`uv add dspy-ai`)
- Verify Modal environment
- Update documentation

### 3. lift-sys-283: Collect Training Data
**Goal**: Build DSPy training dataset
**Target**: 50-100 examples for Forward Mode
**Sources**:
- Manual curation (20)
- Existing tests (30)
- Synthetic generation (50)

### 4. lift-sys-284: Create Phase 2-6 Beads
**Goal**: Detail remaining phases
**Deliverable**: ~120-140 additional beads
**Covers**:
- IR Phases 2-6 (60-70 beads)
- DSPy Phases 1-5 (50-60 beads)

---

## Workflow Instructions

### To Start Working

```bash
# 1. Check ready work
bd ready --json --limit 10

# 2. Claim a task (example: Type System)
bd update lift-sys-275 --status in_progress

# 3. Work on it...

# 4. Mark complete when done
bd close lift-sys-275 --reason "Type system implemented, all tests pass"

# 5. Export state
bd export -o .beads/issues.jsonl

# 6. Commit
git add .beads/issues.jsonl
git commit -m "Complete Type System Foundation (lift-sys-275)"
```

### Dependencies

Beads framework automatically handles:
- **Blocking dependencies**: Can't start lift-sys-276 until lift-sys-275 is closed
- **Related dependencies**: Informational links between related work
- **Automatic sequencing**: `bd ready` only shows tasks whose dependencies are met

### Viewing Work

```bash
# Show ready work
bd ready --json --limit 10

# Show all Phase 1 tasks
bd list --json | jq '.[] | select(.title | contains("Phase 1"))'

# Show epic status
bd show lift-sys-272 --json

# Show dependency graph (future feature)
bd graph lift-sys-272
```

---

## Progress Tracking

### Phase 1 Progress (0/6 tasks complete)

- [ ] lift-sys-275: Type System Foundation
- [ ] lift-sys-276: Predicate System
- [ ] lift-sys-277: Enhanced Hole System
- [ ] lift-sys-278: FuncSpec Enhancement
- [ ] lift-sys-279: Update Core IR
- [ ] lift-sys-280: Database Schema Updates

**Estimated Completion**: 3 months from start
**Blocker**: Waiting for team approval

### Immediate Next Steps (0/4 tasks complete)

- [ ] lift-sys-281: Team Review ⚡
- [ ] lift-sys-282: Install Dependencies ⚡
- [ ] lift-sys-283: Collect Training Data
- [ ] lift-sys-284: Create Phase 2-6 Beads

**Critical Path**: lift-sys-281 (team approval) blocks everything else

---

## Success Metrics (Beads-Tracked)

### Weekly Check-ins
- **Tasks started**: Track via `bd list --status in_progress`
- **Tasks completed**: Track via `bd list --status closed`
- **Blockers**: Track via dependency analysis

### Monthly Reviews
- **Phase progress**: % tasks complete per phase
- **Timeline adherence**: Are we on track for 20-month plan?
- **Quality**: Test coverage, review feedback

### Go/No-Go Decision Points

Each phase has a go/no-go bead at the end:
- Review metrics
- Decide: continue, pivot, or stop
- Document decision rationale

---

## Related Beads (Existing Work)

### Honeycomb Integration (Parallel)
- lift-sys-266 to lift-sys-270: Already planned
- Can run in parallel with IR/DSPy work
- Priority: Lower than strategic initiatives

### Old Semantic IR Work (Superseded)
- lift-sys-53, lift-sys-73, lift-sys-100, etc.
- Some tasks may be absorbed into new plan
- Review and close/merge as appropriate

---

## Next Actions

### This Week
1. ✅ **Done**: Plans created (IR, DSPy, Integration)
2. ✅ **Done**: Beads created for immediate work
3. ⬜ **TODO**: Schedule team review meeting (lift-sys-281)
4. ⬜ **TODO**: Get team buy-in on approach
5. ⬜ **TODO**: Get budget approval

### Next Week
1. ⬜ Install dependencies (lift-sys-282)
2. ⬜ Start collecting training data (lift-sys-283)
3. ⬜ Create detailed Phase 2-6 beads (lift-sys-284)

### Month 1
1. ⬜ **Start Phase 1.1**: Type System Foundation (lift-sys-275)
2. ⬜ Complete Type System (Week 2)
3. ⬜ Start Predicate System (Week 3, lift-sys-276)

---

## Beads Best Practices for This Project

### 1. Claim Before Starting
```bash
bd update <id> --status in_progress
```

### 2. Close When Complete
```bash
bd close <id> --reason "Detailed completion reason"
```

### 3. Export Frequently
```bash
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -m "Update beads state"
```

### 4. Discover Sub-tasks
```bash
# When you discover new work while executing:
bd create "Discovered sub-task" --deps "discovered-from:lift-sys-XXX"
```

### 5. Link Related Work
```bash
bd dep add lift-sys-XXX lift-sys-YYY --type related
```

---

## Summary

**We have a detailed, executable roadmap** for both IR 0.9 Adoption and DSPy Migration:

✅ **2 epics** defining the vision
✅ **15+ beads** for immediate and Phase 1 work
✅ **Clear dependencies** showing critical path
✅ **Ready-to-start tasks** for first 3 months
✅ **Tracking mechanism** via Beads framework

**Next**: Get team approval and start executing! 🚀

---

**Status**: Beads created and committed
**Blocker**: Waiting for team review (lift-sys-281)
**Ready to execute**: lift-sys-275 (Type System) as soon as approved
