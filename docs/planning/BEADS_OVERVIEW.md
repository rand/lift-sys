# Beads Overview: Current Roadmap Structure

**Generated**: 2025-10-20
**Total Beads**: 286 (193 open)
**Strategic Beads**: 15 (2 epics + 3 features + 10 tasks)
**Status**: Ready for team review and approval

---

## Quick Summary

The complete IR 0.9 Adoption and DSPy Migration roadmap has been broken down into **Beads** following the Beads framework workflow. We currently have **15 strategic beads** created with **detailed breakdown for the first 3 months** (IR Phase 1).

**Key Highlights**:
- ✅ 2 epics defining 20-month vision
- ✅ IR Phase 1 fully detailed (6 sequential tasks)
- ✅ Dependencies configured (blocking relationships)
- ✅ Ready-to-start tasks identified
- ⏳ Waiting for team approval to proceed

---

## Epic Structure

### Epic 1: IR 0.9 Adoption (`lift-sys-272`)

**Timeline**: 20 months, 6 phases
**Team**: 4-6 FTE
**Priority**: P0 (highest)

**Goal**: Implement IR 0.9 specification features including dependent types, refinement types, solver integration, hole closures, surface syntax, and provenance tracking.

**Success Metrics**:
- Type system represents all IR 0.9 examples
- SMT solver detects 90%+ unsatisfiable specs
- Partial evaluation works with hole closures
- Users can author Spec-IR syntax
- Beta user satisfaction >8/10

**Phases**:
1. ✓ **Phase 1**: Core Types & Refinements (Months 1-3) - **DETAILED**
2. ○ **Phase 2**: Solver Integration (Months 4-6) - Planned
3. ○ **Phase 3**: Hole Closures (Months 7-10) - To Plan
4. ○ **Phase 4**: Surface Syntax (Months 11-14) - To Plan
5. ○ **Phase 5**: Alignment & Provenance (Months 15-18) - To Plan
6. ○ **Phase 6**: Production Readiness (Months 19-20) - To Plan

---

### Epic 2: DSPy Migration (`lift-sys-273`)

**Timeline**: 14 months, 5 phases (starts Month 4)
**Team**: 2-3 FTE
**Priority**: P0 (highest)
**Dependencies**: Requires IR Phase 1 completion (stable IR schema)

**Goal**: Migrate all AI-driven components from manual prompt engineering to DSPy framework for systematic optimization and continuous improvement.

**Success Metrics**:
- Forward mode (NL→IR) quality +10% vs baseline
- Reverse mode intent extraction +20% vs heuristics
- Hole suggestion acceptance rate 60%+
- Entity resolution 90%+ accuracy
- Monthly quality improvements visible

**Phases**:
1. ○ **Phase 1**: DSPy Setup + Forward Mode (Months 4-6) - Planned
2. ○ **Phase 2**: Reverse Mode Enhancement (Months 7-9) - To Plan
3. ○ **Phase 3**: Ambiguity Detection + Hole Suggestions (Months 10-12) - To Plan
4. ○ **Phase 4**: Entity Resolution + Intent Extraction (Months 13-15) - To Plan
5. ○ **Phase 5**: Continuous Learning + Production (Months 16-17) - To Plan

---

## IR Phase 1: Detailed Breakdown

### Feature: `lift-sys-274` - IR Phase 1: Core Types & Refinements

**Duration**: 3 months (12 weeks)
**Team**: 1 senior eng + 1 mid-level eng
**Status**: Open, ready to start after approval

**6 Sequential Tasks**:

#### 1. `lift-sys-275`: Type System Foundation ⚡ READY
- **Duration**: Weeks 1-2
- **Files**: `lift_sys/ir/types.py` (~400 lines)
- **Deliverable**:
  - BaseType, DependentType, RefinementType
  - ProductType, SumType, EffectType
  - TypeHole
  - JSON serialization/deserialization
- **Tests**: `tests/unit/test_ir_types.py` (~200 lines)
- **Status**: **READY TO START**
- **Blocks**: lift-sys-276

#### 2. `lift-sys-276`: Predicate System
- **Duration**: Weeks 3-4
- **Files**: `lift_sys/ir/predicates.py` (~300 lines)
- **Deliverable**:
  - Predicate AST (BoolLiteral, VarRef, BinaryOp, Quantified)
  - Traversal operations
  - Pretty-printing
  - Variable substitution
- **Dependencies**: Blocked by lift-sys-275
- **Blocks**: lift-sys-277

#### 3. `lift-sys-277`: Enhanced Hole System
- **Duration**: Weeks 5-6
- **Files**: `lift_sys/ir/models.py` (update)
- **Deliverable**:
  - 6 hole kinds (term, type, spec, entity, function, module)
  - Type annotations (can be TypeHole)
  - Hole linking (dependency graph)
  - Hints and provenance
- **Dependencies**: Blocked by lift-sys-276
- **Blocks**: lift-sys-278

#### 4. `lift-sys-278`: FuncSpec Enhancement
- **Duration**: Weeks 7-8
- **Files**: `lift_sys/ir/specs.py` (new, ~300 lines)
- **Deliverable**:
  - FuncSpec (requires, ensures, invariants, measure, cost)
  - IntentSpec (summary, roles, goals, constraints, metrics)
  - AlignmentMap (mappings, confidence, drift detection)
- **Dependencies**: Blocked by lift-sys-277
- **Blocks**: lift-sys-279

#### 5. `lift-sys-279`: Update Core IR
- **Duration**: Weeks 9-10
- **Files**: `lift_sys/ir/models.py` (major update)
- **Deliverable**:
  - Refactored IntermediateRepresentation
  - Backward compatibility via legacy methods
  - Migration path documented
- **Dependencies**: Blocked by lift-sys-278
- **Blocks**: lift-sys-280

#### 6. `lift-sys-280`: Database Schema Updates
- **Duration**: Weeks 11-12
- **Files**: `migrations/007_ir_v09_types.sql`
- **Deliverable**:
  - Supabase tables: holes, func_specs, intent_specs, alignment_maps
  - RLS policies updated
  - Migration tested
- **Dependencies**: Blocked by lift-sys-279
- **Blocks**: lift-sys-285 (Phase 2)

---

## Immediate Next Steps

### 1. `lift-sys-281`: Team Review Meeting ⚡ READY
**Duration**: This week
**Priority**: P0 (critical path)

**Agenda**:
- Review IR_ADOPTION_PLAN.md
- Review DSPY_MIGRATION_PLAN.md
- Review INTEGRATED_STRATEGY.md
- Discuss resource requirements (4-6 FTE, $1.08M)
- Get go/no-go decision
- Secure budget approval

**Outputs**:
- Meeting notes
- Decision: GO or NO-GO
- List of concerns/risks to address
- Commitment from leadership

---

### 2. `lift-sys-282`: Install Dependencies ⚡ READY
**Duration**: 2 days
**Priority**: P0
**Prerequisites**: Team approval

**Tasks**:
```bash
# Install Z3 solver
uv add z3-solver
python -c "import z3; print(z3.get_version_string())"

# Install DSPy
uv add dspy-ai
python -c "import dspy; print(dspy.__version__)"

# Verify Modal environment
modal app list
modal run scripts/test_z3_modal.py
```

**Acceptance**:
- Z3 imports and runs locally
- DSPy imports and runs locally
- Z3 works in Modal environment
- All tests pass

---

### 3. `lift-sys-283`: Collect Training Data
**Duration**: 1 week
**Priority**: P0

**Goal**: Build initial training dataset for DSPy Forward Mode optimization

**Sources**:
- Manual curation: 20 examples (diverse function types)
- Existing tests: 30 examples (extract from test suite)
- Synthetic generation: 50 examples (GPT-4 assisted)

**Target**: 50-100 high-quality examples

**Output**: `lift_sys/dspy_data/forward_mode_train.json`

---

### 4. `lift-sys-284`: Create Phase 2-6 Beads
**Duration**: 1 day
**Priority**: P1 (not blocking)

**Goal**: Detail remaining phases with full bead breakdown

**Deliverables**:
- IR Phase 2: Solver Integration (10-12 beads)
- IR Phase 3: Hole Closures (12-15 beads)
- IR Phase 4: Surface Syntax (15-18 beads)
- IR Phase 5: Alignment (10-12 beads)
- IR Phase 6: Production (8-10 beads)
- DSPy Phases 1-5 (50-60 beads)

**Total**: ~120-140 additional beads

---

## Dependency Graph

### Critical Path (Sequential)

```
lift-sys-281 (Team Review)
    ↓
lift-sys-282 (Setup Dependencies)
    ↓
lift-sys-275 (Type System)
    ↓ blocks
lift-sys-276 (Predicate System)
    ↓ blocks
lift-sys-277 (Enhanced Holes)
    ↓ blocks
lift-sys-278 (FuncSpec)
    ↓ blocks
lift-sys-279 (Core IR Update)
    ↓ blocks
lift-sys-280 (Database Migration)
    ↓ blocks
lift-sys-285 (IR Phase 2: Solvers)
```

### Parallel Track

```
lift-sys-274 (IR Phase 1)
    ↓ related (stable IR schema needed)
lift-sys-286 (DSPy Phase 1)
```

**Note**: DSPy Phase 1 can start in Month 4 once IR Phase 1 stabilizes the IR schema.

---

## Timeline Overview

### Months 1-3: IR Phase 1 + DSPy Prep
- **IR Track**: Types & Refinements (lift-sys-275 through lift-sys-280)
- **DSPy Track**: Install, collect training data, prepare infrastructure

### Months 4-6: IR Phase 2 + DSPy Phase 1
- **IR Track**: Solver Integration (SMT/SAT/CSP)
- **DSPy Track**: Forward Mode migration (NL → IR with DSPy)

### Months 7-10: IR Phase 3 + DSPy Phase 2
- **IR Track**: Hole Closures & Partial Evaluation
- **DSPy Track**: Reverse Mode enhancement (Code → IR with AI)

### Months 11-14: IR Phase 4 + DSPy Phase 3
- **IR Track**: Surface Syntax & Parsing (Spec-IR)
- **DSPy Track**: Ambiguity Detection + Hole Suggestions

### Months 15-18: IR Phase 5 + DSPy Phase 4
- **IR Track**: Alignment & Provenance Tracking
- **DSPy Track**: Entity Resolution + Intent Extraction

### Months 19-20: IR Phase 6 + DSPy Phase 5
- **IR Track**: Production Readiness
- **DSPy Track**: Continuous Learning + Production

---

## How to Work with These Beads

### Check Ready Work
```bash
bd ready --json --limit 10
```

### Claim a Task
```bash
bd update lift-sys-275 --status in_progress
```

### Work on It
- Implement according to bead description
- Follow acceptance criteria
- Write tests (100% coverage target)

### Complete Task
```bash
bd close lift-sys-275 --reason "Type system implemented, all tests pass"
```

### Export State
```bash
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -m "Complete Type System Foundation (lift-sys-275)"
```

### Discover New Work
```bash
# If you discover sub-tasks while working:
bd create "Discovered sub-task" --deps "discovered-from:lift-sys-275"
```

---

## Current Status

### ✅ Completed
- Planning documents (5 docs, ~35K words)
- Strategic beads created (15 beads)
- Dependencies configured
- IR Phase 1 fully detailed

### ⏳ In Progress
- Waiting for team review (lift-sys-281)
- Waiting for go/no-go decision

### 🚀 Ready to Start
- lift-sys-275 (Type System) - Ready once approved
- lift-sys-281 (Team Review) - Ready now
- lift-sys-282 (Install Deps) - Ready after approval

### 🚧 Blocked
- lift-sys-276 through lift-sys-280 - Blocked by dependencies
- lift-sys-285 (Phase 2) - Blocked by Phase 1 completion
- lift-sys-286 (DSPy Phase 1) - Related to IR Phase 1

---

## Work Distribution

### Created (15 beads)
- **Epics**: 2
- **Features**: 3 (Phase 1, Phase 2, DSPy Phase 1)
- **Tasks**: 10 (6 IR Phase 1 + 4 immediate)

### To Be Created (~120-140 beads)
- **IR Phases 2-6**: ~60-70 beads
- **DSPy Phases 1-5**: ~50-60 beads

### Existing Beads (271 other beads)
- Various older work items
- Some may be absorbed into new plan
- Review and close/merge as appropriate

---

## Success Metrics

### Weekly Check-ins
Track via Beads:
- Tasks started: `bd list --status in_progress`
- Tasks completed: `bd list --status closed`
- Blockers: Dependency analysis

### Phase 1 Progress (Target: 3 months)
- **Week 2**: Type System complete (lift-sys-275)
- **Week 4**: Predicate System complete (lift-sys-276)
- **Week 6**: Enhanced Holes complete (lift-sys-277)
- **Week 8**: FuncSpec complete (lift-sys-278)
- **Week 10**: Core IR update complete (lift-sys-279)
- **Week 12**: Database migration complete (lift-sys-280)

### Go/No-Go Decision Points
- **End of Phase 1** (Month 3): Continue to solvers?
- **End of Phase 2** (Month 6): Continue to hole closures?
- **End of Phase 3** (Month 10): Continue to surface syntax?
- **End of Phase 4** (Month 14): Continue to production?
- **End of Phase 5** (Month 18): Launch beta?

---

## Related Documents

- **IR_ADOPTION_PLAN.md**: Detailed 20-month IR 0.9 plan
- **DSPY_MIGRATION_PLAN.md**: Detailed 14-month DSPy plan
- **INTEGRATED_STRATEGY.md**: Master integration document
- **BEADS_ROADMAP.md**: Execution guide
- **EXECUTION_SUMMARY.md**: Quick reference summary

---

## Next Actions

### This Week
1. ⬜ Schedule team review meeting (lift-sys-281)
2. ⬜ Review planning docs with full team
3. ⬜ Get go/no-go decision
4. ⬜ Secure budget approval

### After Approval
1. ⬜ Install dependencies (lift-sys-282)
2. ⬜ Claim lift-sys-275 (Type System)
3. ⬜ Start coding!

### Week 2
1. ⬜ Complete Type System (lift-sys-275)
2. ⬜ Start Predicate System (lift-sys-276)
3. ⬜ Collect training data (lift-sys-283)

---

**Status**: Planning complete, waiting for team approval
**Blocker**: lift-sys-281 (Team Review)
**Next Task**: lift-sys-275 (Type System Foundation)
**Total Program**: 20 months, $1.08M, 4-6 FTE
