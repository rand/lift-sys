# Forward-Reverse Integration: Issue Tracking Summary

**Created**: October 13, 2025
**Total Issues**: 23 new issues (lift-sys-24 through lift-sys-46)
**Status**: All issues created with dependencies mapped
**Tracking**: Using Beads issue tracker

---

## Overview

This document summarizes the Beads issues created to track the forward-reverse integration plan. Issues are organized into 5 phases with proper dependency chains to ensure work happens in the right order.

---

## Phase 1: Code Generation (6 issues, P0 - Critical)

**Goal**: Close the loop by generating code from finalized IRs

| Issue | Title | Dependencies |
|-------|-------|--------------|
| **lift-sys-24** | Design IR-to-code translation architecture | None (READY!) |
| **lift-sys-25** | Implement basic Python code generator | lift-sys-24 |
| **lift-sys-26** | Add assertion injection to generated code | lift-sys-25 |
| **lift-sys-27** | Build round-trip validator | lift-sys-25, lift-sys-26 |
| **lift-sys-28** | Create code preview UI component | lift-sys-25 |
| **lift-sys-29** | Add code generation API endpoint | lift-sys-25 |

**Key Deliverables:**
- Python code generator from IR
- Assertion injection in generated code
- Round-trip validation (generate → extract → compare)
- Frontend code preview component
- `/api/sessions/{id}/generate` endpoint

**Critical Path**: lift-sys-24 → lift-sys-25 → (lift-sys-26, lift-sys-27, lift-sys-28, lift-sys-29)

**Ready to Start**: lift-sys-24 (no blockers)

---

## Phase 2: Reverse Integration (5 issues, P1 - High)

**Goal**: Allow reverse-extracted IRs to enter forward mode refinement

| Issue | Title | Dependencies |
|-------|-------|--------------|
| **lift-sys-30** | Design reverse-to-forward import flow | lift-sys-29 |
| **lift-sys-31** | Implement improvement area detection | lift-sys-30 |
| **lift-sys-32** | Build IR comparison and diff engine | lift-sys-27 |
| **lift-sys-33** | Create IR diff visualization UI | lift-sys-32 |
| **lift-sys-34** | Add session import from reverse IR | lift-sys-30 |

**Key Deliverables:**
- Import reverse IR into session
- Auto-detect improvement areas as typed holes
- IR comparison/diff engine
- Side-by-side IR diff viewer
- `/api/sessions/import-from-reverse` endpoint

**Critical Path**: lift-sys-27 → lift-sys-32 → lift-sys-33

**Enables**: Legacy code modernization workflow

---

## Phase 3: IR Evolution (4 issues, P1 - High)

**Goal**: Support versioning and evolving IRs over time

| Issue | Title | Dependencies |
|-------|-------|--------------|
| **lift-sys-35** | Add IR versioning schema | lift-sys-32 |
| **lift-sys-36** | Implement IR merge operations | lift-sys-32, lift-sys-35 |
| **lift-sys-37** | Build version history UI | lift-sys-35 |
| **lift-sys-38** | Add provenance tracking to IR | lift-sys-35 |

**Key Deliverables:**
- IR version metadata (version, parent, changes)
- Three-way merge operations
- Version history timeline UI
- Provenance tracking (source, confidence, author)

**Critical Path**: lift-sys-32 → lift-sys-35 → (lift-sys-36, lift-sys-37, lift-sys-38)

**Enables**: Collaborative IR development, conflict resolution

---

## Phase 4: Agent Enhancements (4 issues, P2 - Medium)

**Goal**: Intelligent agent actions throughout the loop

| Issue | Title | Dependencies |
|-------|-------|--------------|
| **lift-sys-39** | Implement proactive IR analysis | lift-sys-32, lift-sys-34 |
| **lift-sys-40** | Build test case generator from IR | lift-sys-29 |
| **lift-sys-41** | Add security suggestion engine | lift-sys-31 |
| **lift-sys-42** | Create refactoring recommender | lift-sys-32 |

**Key Deliverables:**
- AgentAdvisor for IR analysis
- Test case generation from IR
- Security issue detection and fixes
- Refactoring suggestions

**Critical Path**: Multiple paths converge here

**Enables**: Smarter, more proactive assistance

---

## Phase 5: Polish & Optimization (4 issues, P2 - Medium)

**Goal**: Production-ready quality and user experience

| Issue | Title | Dependencies |
|-------|-------|--------------|
| **lift-sys-43** | Performance profiling and optimization | lift-sys-29, lift-sys-34 |
| **lift-sys-44** | UX refinement based on feedback | lift-sys-29, lift-sys-37 |
| **lift-sys-45** | Write comprehensive integration documentation | lift-sys-42 |
| **lift-sys-46** | Create tutorial content and examples | lift-sys-45 |

**Key Deliverables:**
- Performance optimization (< 1s code gen, < 500ms diff)
- Improved UX based on user testing
- Complete documentation
- Tutorial videos and examples

**Critical Path**: lift-sys-45 → lift-sys-46

**Completes**: Production-ready integration

---

## Quick Reference

### Check What's Ready to Work On
```bash
bd ready
```

Currently shows: **lift-sys-24** (Design IR-to-code translation architecture)

### View Issue Details
```bash
bd show lift-sys-24
```

### View Dependency Tree
```bash
bd dep tree lift-sys-29
```

### List All Open Issues
```bash
bd list --status open
```

### Filter by Priority
```bash
bd list --priority 0  # P0 issues only
bd list --priority 1  # P1 issues only
```

---

## Priority Breakdown

**P0 (Critical) - 6 issues:**
- All Phase 1 (Code Generation)
- Must complete to close the loop

**P1 (High) - 9 issues:**
- Phases 2 & 3 (Reverse Integration + IR Evolution)
- Core functionality for integration

**P2 (Medium) - 8 issues:**
- Phases 4 & 5 (Agent Enhancements + Polish)
- Nice-to-have improvements

---

## Workflow States

All issues start as **open**. As work progresses:

1. **Ready to work** → Shows in `bd ready` when no blockers
2. **In Progress** → `bd update lift-sys-24 --status in_progress`
3. **Blocked** → Has open dependencies
4. **Complete** → `bd close lift-sys-24`

When an issue is closed, its dependents may become unblocked.

---

## Key Milestones

### Milestone 1: Basic Code Generation (Weeks 1-6)
**Completes when**: lift-sys-24 through lift-sys-29 are closed
**Deliverable**: Can generate and validate Python code from IR

### Milestone 2: Reverse Integration (Weeks 7-10)
**Completes when**: lift-sys-30 through lift-sys-34 are closed
**Deliverable**: Can import reverse IRs and refine them

### Milestone 3: IR Evolution (Weeks 11-13)
**Completes when**: lift-sys-35 through lift-sys-38 are closed
**Deliverable**: Can version and merge IRs

### Milestone 4: Agent Enhancements (Weeks 14-17)
**Completes when**: lift-sys-39 through lift-sys-42 are closed
**Deliverable**: Proactive agent assistance working

### Milestone 5: Production Polish (Weeks 18-20)
**Completes when**: lift-sys-43 through lift-sys-46 are closed
**Deliverable**: Production-ready integration

---

## Iteration Strategy

These issues are **intentionally flexible** to allow for:

1. **Discovery during implementation**
   - Details will emerge as we build
   - Issue descriptions can be updated
   - New issues can be added

2. **Changing priorities**
   - Priorities can be adjusted based on learnings
   - Dependencies can be modified if needed
   - Timeline is a guide, not a contract

3. **User feedback incorporation**
   - After each milestone, gather feedback
   - Create new issues for improvements
   - Adjust plan based on real usage

4. **Technical pivots**
   - If an approach doesn't work, we can pivot
   - Issues can be closed and replaced
   - Dependencies allow safe changes

---

## Critical Path Analysis

**The absolute critical path** (must complete in order):

```
lift-sys-24 (Design)
    ↓
lift-sys-25 (Basic Code Generator)
    ↓
lift-sys-26 (Assertions) + lift-sys-27 (Validator)
    ↓
lift-sys-29 (API Endpoint)
    ↓
lift-sys-30 (Import Design)
    ↓
lift-sys-32 (IR Diff Engine)
    ↓
[Phases 3-5 can proceed in parallel]
```

**Estimated Critical Path Duration**: ~10-12 weeks

Everything else can be done in parallel or deferred.

---

## Success Metrics

Track these as issues are completed:

**Code Quality:**
- [ ] Round-trip validation score > 95%
- [ ] SMT verification success rate 100%
- [ ] Generated code passes tests > 90%

**Developer Velocity:**
- [ ] Time to finalize IR: Track baseline, aim to reduce
- [ ] Iterations to convergence: < 10
- [ ] Agent suggestion acceptance: > 50%

**System Performance:**
- [ ] Code generation: < 1 second
- [ ] IR comparison: < 500ms
- [ ] Round-trip validation: < 5 seconds

---

## Next Actions

**Immediate (This Week):**
1. Start lift-sys-24: Design IR-to-code translation architecture
2. Create design document with interface definitions
3. Get feedback on design before implementing

**Short Term (Next 2 Weeks):**
1. Complete lift-sys-24 and lift-sys-25
2. Build prototype code generator for simple cases
3. Test with existing IRs from forward mode

**Medium Term (Next Month):**
1. Complete Phase 1 (all 6 issues)
2. Demo working code generation
3. User testing and feedback
4. Begin Phase 2

---

## Related Documentation

- [Complete Integration Plan](FORWARD_REVERSE_INTEGRATION_PLAN.md) - Detailed 20-week plan
- [Reverse Mode Guide](REVERSE_MODE.md) - Current reverse mode features
- [API Session Management](API_SESSION_MANAGEMENT.md) - Forward mode API

---

**Last Updated**: October 13, 2025
**Status**: Issues created, dependencies mapped, ready to begin
**First Task**: lift-sys-24 (Design IR-to-code translation architecture)
