# Session Bootstrap Guide - Quick Start

**Purpose**: Get oriented and productive in <5 minutes when resuming work on the meta-framework.

---

## 30-Second Orientation

You are working on **redesigning lift-sys using DSPy + Pydantic AI**.

The approach: Treat the proposal as an **IR with typed holes**, then systematically resolve them over 7 weeks.

**Current Status**: Phase 1, Hole H6 ready to start

---

## 5-Minute Bootstrap

### 1. Where Are We? (1 min)

```bash
# Check current state
cat docs/planning/SESSION_STATE.md | head -20

# What's ready?
python scripts/planning/track_holes.py ready --phase 1
```

**Expected**: H6, H9, H14 are ready (Phase 1)

### 2. What's the Current Task? (1 min)

```bash
# Get detailed context
python scripts/planning/track_holes.py show H6
```

**Read**: Description, constraints, acceptance criteria

### 3. What's the Goal? (1 min)

**This Week**: Resolve H6 (NodeSignatureInterface)
- Create: `lift_sys/dspy_signatures/node_interface.py`
- Define: How graph nodes execute DSPy signatures
- Validate: Type checker passes, prototype works

**This Phase**: Pass Gate 1 (see `PHASE_GATES_VALIDATION.md`)
- Resolve H6, H9, H14
- Establish interface foundation

### 4. How Do I Proceed? (1 min)

**If H6 not started**:
1. Read `HOLE_INVENTORY.md` H6 section (detailed spec)
2. Review `DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md` Section 3.2 (signature design)
3. Start implementing `lift_sys/dspy_signatures/node_interface.py`

**If H6 in progress**:
1. Check `SESSION_STATE.md` "Current Work Context"
2. Continue implementation
3. Validate when done

**If H6 complete**:
1. Mark resolved: `python scripts/planning/track_holes.py resolve H6 --resolution path`
2. Document propagation in `CONSTRAINT_PROPAGATION_LOG.md`
3. Move to H9 or H14

### 5. How Do I Track Progress? (1 min)

```bash
# After completing work
python scripts/planning/track_holes.py resolve H6 --resolution lift_sys/dspy_signatures/node_interface.py

# Update session state
vim docs/planning/SESSION_STATE.md  # Update "Current Work Context"

# Export beads
bd export -o .beads/issues.jsonl

# Commit
git add docs/planning/*.md .beads/issues.jsonl
git commit -m "Session N: Resolved H6 - NodeSignatureInterface"
```

---

## Document Hierarchy (Read in Order)

### Tier 1: State & Orientation (Read Every Session)
1. **`SESSION_STATE.md`** - Where we are, what's next
2. **`SESSION_BOOTSTRAP.md`** (this file) - Quick start

### Tier 2: Context (Read When Needed)
3. **`HOLE_INVENTORY.md`** - Details on current hole
4. **`PHASE_GATES_VALIDATION.md`** - Current phase gate criteria
5. **`REIFICATION_SUMMARY.md`** - How the system works

### Tier 3: Framework (Read Once, Reference as Needed)
6. **`META_FRAMEWORK_DESIGN_BY_HOLES.md`** - Meta-framework details
7. **`CONSTRAINT_PROPAGATION_LOG.md`** - Propagation tracking
8. **`DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md`** - Original proposal

---

## Key Commands

```bash
# === STATE CHECKING ===
# What's ready?
python scripts/planning/track_holes.py ready

# Show hole details
python scripts/planning/track_holes.py show <HOLE_ID>

# Phase status
python scripts/planning/track_holes.py phase-status <N>

# === AFTER WORK ===
# Mark hole resolved
python scripts/planning/track_holes.py resolve <HOLE_ID> --resolution <PATH>

# Update beads
bd export -o .beads/issues.jsonl

# === VISUALIZATION ===
# Dependency graph
python scripts/planning/track_holes.py visualize --output docs/planning/deps.dot
```

---

## Common Scenarios

### Scenario 1: "I just started, what do I do?"

1. Read `SESSION_STATE.md` (current state)
2. Run `python scripts/planning/track_holes.py ready --phase 1`
3. Pick H6 (critical path)
4. Read H6 details: `python scripts/planning/track_holes.py show H6`
5. Start implementation

### Scenario 2: "I'm continuing from last session"

1. Check `SESSION_STATE.md` - "Current Work Context"
2. See what was in progress
3. Continue or validate if done
4. Update state when complete

### Scenario 3: "I just finished a hole"

1. Validate resolution (run tests, type checker)
2. Mark resolved: `track_holes.py resolve <ID> --resolution <PATH>`
3. Document propagation in `CONSTRAINT_PROPAGATION_LOG.md`:
   ```markdown
   ## Event N: <DATE>
   **Hole Resolved**: <ID> - <Name>
   **Resolution**: <Summary>

   ### Constraints Propagated
   #### To <Dependent Hole>
   **New Constraint**: <Description>
   ```
4. Update `SESSION_STATE.md`:
   - Mark hole complete in phase progress
   - Update "Current Work Context" to next hole
5. Export beads: `bd export -o .beads/issues.jsonl`
6. Commit changes

### Scenario 4: "A hole is harder than expected"

1. Check if constraints can be relaxed (review `HOLE_INVENTORY.md`)
2. Consider alternative resolution (see "Resolution Ideas" in hole spec)
3. If stuck, document in `SESSION_STATE.md` "Known Issues"
4. Move to different hole if possible (check `track_holes.py ready`)
5. Return after getting clarity

### Scenario 5: "I discovered a new constraint"

1. Immediately document in `CONSTRAINT_PROPAGATION_LOG.md`
2. Update dependent holes in `HOLE_INVENTORY.md`
3. Check if this blocks current work (may need to backtrack)
4. Note in `SESSION_STATE.md` "Decision Log"

---

## Critical Path Awareness

**Always know**: Am I working on the critical path?

**Critical Path**: H6 → H1 → H10 → H17

**Why It Matters**: These holes block the most other work. Prioritize them.

**Current**: H6 is critical path AND ready. **Work on this first.**

---

## Validation Checklist (Before Marking Resolved)

- [ ] Implementation exists at specified path
- [ ] Type checker passes: `mypy --strict <path>`
- [ ] Tests pass: `pytest tests/...`
- [ ] All constraints from hole spec satisfied
- [ ] Acceptance criteria met
- [ ] Documented in code (docstrings)

---

## Session Handoff Pattern

### End of Your Session
```bash
# 1. Update state
vim docs/planning/SESSION_STATE.md
# - Update current hole status
# - Document progress
# - Note next steps

# 2. Export beads
bd export -o .beads/issues.jsonl

# 3. Commit
git add docs/planning/*.md .beads/issues.jsonl
git commit -m "Session N: <summary>"
git push
```

### Start of Next Session
```bash
# 1. Pull latest
git pull

# 2. Import beads
bd import -i .beads/issues.jsonl

# 3. Check state
cat docs/planning/SESSION_STATE.md | grep "Current Work Context" -A 20

# 4. Resume work
```

---

## Mental Model: The System is an IR

```
Proposal
  ↓
Viewed as IR with 19 typed holes
  ↓
Resolve holes iteratively
  ↓
Constraints propagate
  ↓
Design converges to complete system
```

**You are**: Filling in the holes
**Goal**: All 19 holes resolved with satisfied constraints
**Timeline**: 7 weeks, 7 phases
**Current**: Phase 1, Week 1, Hole H6

---

## Help & References

### Stuck? Read These
- `SESSION_STATE.md` - "Current Work Context"
- `HOLE_INVENTORY.md` - Current hole's full spec
- `REIFICATION_SUMMARY.md` - How the system works

### Need More Context?
- `META_FRAMEWORK_DESIGN_BY_HOLES.md` - Framework design
- `DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md` - Original proposal

### Commands Not Working?
```bash
# Reinstall beads if needed
go install github.com/steveyegge/beads/cmd/bd@latest

# Check script is executable
chmod +x scripts/planning/track_holes.py

# Test script
python scripts/planning/track_holes.py --help
```

---

## Time-Boxed Session Structure

### 30-Minute Session
- 5 min: Bootstrap (this guide)
- 20 min: Work on current hole
- 5 min: Update state, commit

### 2-Hour Session
- 5 min: Bootstrap
- 90 min: Work on current hole
- 15 min: Validate, test, update state
- 10 min: Document propagation if hole resolved

### Full Day Session
- Morning: Resolve 1-2 holes
- Afternoon: Validate, document, check gate criteria
- End of day: Update state, export beads, commit

---

## Success = Fidelity

**High fidelity means**:
- Next session knows exactly where you left off
- Constraints are preserved and propagated
- Dependencies are tracked and respected
- Decisions are documented with rationale

**You achieve this by**:
- Updating `SESSION_STATE.md` every session
- Documenting constraint propagation
- Keeping hole inventory current
- Committing changes

---

**You're ready. Start with**: `python scripts/planning/track_holes.py ready --phase 1`
