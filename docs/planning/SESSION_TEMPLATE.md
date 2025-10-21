# Session N Template

**Date**: YYYY-MM-DD
**Session ID**: N
**Phase**: Phase N
**Duration**: X hours
**Participants**: [Names/IDs]

---

## Session Goals

### Primary Goal
- [ ] [Main objective for this session]

### Secondary Goals
- [ ] [Additional objectives]

---

## Pre-Session State

### Current Hole
**ID**: HX
**Name**: [Hole Name]
**Status**: [Status at session start]

### Phase Progress
**Phase**: N
**Holes in Phase**: [List]
**Resolved**: N/M

### Blockers
- [Any known blockers]

---

## Session Work Log

### Hour 1
**Focus**: [What you worked on]
**Progress**: [What was accomplished]
**Decisions**: [Any decisions made]
**Issues**: [Any issues encountered]

### Hour 2
**Focus**: [What you worked on]
**Progress**: [What was accomplished]
**Decisions**: [Any decisions made]
**Issues**: [Any issues encountered]

[Add more hours as needed]

---

## Holes Worked On

### HX: [Hole Name]

**Status Change**: [Before] → [After]

**Work Done**:
- [Specific work items]

**Files Modified**:
- `path/to/file.py`

**Tests Added**:
- `tests/path/to/test.py`

**Constraints Satisfied**:
- [X] [Constraint 1]
- [ ] [Constraint 2] (in progress)

**Blockers Resolved**:
- [Any blockers removed]

**Blockers Added**:
- [Any new blockers discovered]

---

## Constraint Propagation

### From HX Resolution

**Propagated To**:
- **HY**: [New constraint added]
- **HZ**: [New constraint added]

**Solution Space Impact**:
- HY: [How solution space narrowed]
- HZ: [How solution space narrowed]

**Documented In**: `CONSTRAINT_PROPAGATION_LOG.md` Event N

---

## Decisions Made

### Decision 1: [Title]
**Context**: [Why this decision was needed]
**Options Considered**: [What alternatives were evaluated]
**Decision**: [What was chosen]
**Rationale**: [Why this was chosen]
**Impact**: [What this affects]

### Decision 2: [Title]
[Same structure]

---

## New Constraints Discovered

### Constraint 1
**Applies To**: [Which holes]
**Description**: [What the constraint is]
**Reason**: [Why this constraint exists]
**Impact**: [How this affects the work]

---

## Issues Encountered

### Issue 1: [Title]
**Description**: [What happened]
**Impact**: [How this affects progress]
**Resolution**: [How it was resolved, or status if unresolved]
**Prevention**: [How to avoid in future]

---

## Testing & Validation

### Tests Run
- [ ] Unit tests: `pytest tests/unit/...`
- [ ] Integration tests: `pytest tests/integration/...`
- [ ] Type checking: `mypy --strict ...`
- [ ] Linting: `ruff check ...`

### Test Results
**Passed**: N/M tests
**Failed**: [List any failures and fixes]

### Validation Against Criteria
- [ ] Criterion 1: [Status]
- [ ] Criterion 2: [Status]

---

## Files Changed

### Created
- `path/to/new/file.py` - [Purpose]

### Modified
- `path/to/existing/file.py` - [What changed]

### Deleted
- `path/to/old/file.py` - [Why]

---

## Post-Session State

### Hole Status
**HX**: [Status at session end]

### Phase Progress
**Resolved This Session**: N holes
**Total Resolved**: N/M

### Gate Progress
**Gate N Criteria**: N/M passed

### Next Session Should
1. [Specific next step]
2. [Alternative if #1 blocked]

---

## Handoff Notes

### For Next Session
**Resume Point**: [Exactly where to pick up]
**Context Needed**: [What docs to read]
**Blockers to Resolve**: [Any blockers to address]

### Open Questions
1. [Question that needs answering]
2. [Decision that needs making]

---

## Session Metrics

### Time Breakdown
- Planning: X min
- Implementation: X min
- Testing: X min
- Documentation: X min
- Review: X min

### Productivity
- Holes resolved: N
- Constraints propagated: N
- Tests written: N
- Files modified: N

---

## Commits Made

### Commit 1
```
commit <hash>
Subject: [commit message]

- [Change 1]
- [Change 2]
```

### Commit 2
[Same structure]

---

## Session Checklist

### Before Ending Session
- [ ] Updated `SESSION_STATE.md`
- [ ] Updated `HOLE_INVENTORY.md` (if holes resolved)
- [ ] Updated `CONSTRAINT_PROPAGATION_LOG.md` (if constraints propagated)
- [ ] Updated relevant gate in `PHASE_GATES_VALIDATION.md`
- [ ] Exported beads: `bd export -o .beads/issues.jsonl`
- [ ] Committed all changes
- [ ] Pushed to remote (if applicable)
- [ ] Created this session log

### Quality Checks
- [ ] All modified code has tests
- [ ] All tests passing
- [ ] Type checker passes
- [ ] Documentation updated
- [ ] No TODOs left without tracking

---

## Session Rating

**Productivity**: [1-5]
**Progress vs Plan**: [1-5]
**Code Quality**: [1-5]
**Documentation Quality**: [1-5]

**Overall**: [X/5]

**Notes**: [What went well, what could improve]

---

**Session Status**: [COMPLETE | INCOMPLETE]
**Next Session ID**: N+1
