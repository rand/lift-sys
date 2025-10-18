# lift-sys Phase Structure

**Last Updated**: 2025-10-17
**Status**: Active Development

## Overview

This document clarifies the phase structure used throughout lift-sys documentation and planning.

---

## Phase Numbering

### Phase 0: Foundation & CSP Implementation
**Status**: Planned (not started)
**Beads**: lift-sys-182 through lift-sys-189
**Goal**: Implement GenCP-style constraint programming foundation for systematic typed hole resolution

### Phase 1: Enhanced IR + NLP + Typed Holes
**Status**: Planned (not started)
**Beads**: lift-sys-70 through lift-sys-86
**Goal**: Enhanced IR data models, NLP infrastructure, typed hole detection, and prompt highlighting
**Research Foundation**:
- Cyrus Omar et al. - "Statically Contextualizing LLMs with Typed Holes" (arXiv:2409.00921)
- Type-Constrained Code Generation (arXiv:2504.09246)

### Phase 2: Clause Analysis + Ambiguity Detection
**Status**: Planned (not started)
**Beads**: lift-sys-87 through lift-sys-103
**Goal**: Clause extraction, ambiguity detection, intent classification

### Phase 3: Refinement UI + LLM Suggestions
**Status**: Active (in progress)
**Beads**: lift-sys-104 through lift-sys-118
**Goal**: Iterative refinement UI, LLM-powered suggestions, real-time updates
**Research Foundation**:
- ACE: Agentic Context Engineering (arXiv:2510.04618) - Delta-based updates
- MuSLR: Multimodal Symbolic Logical Reasoning (arXiv:2510.04618) - Confidence levels
**Beads Approved**: lift-sys-163, lift-sys-167, lift-sys-168, lift-sys-169

### Phase 4: Provenance + Graph Visualization
**Status**: Planned (not started)
**Beads**: lift-sys-119 through lift-sys-130
**Goal**: Provenance tracking, relationship graphs, bidirectional navigation
**Note**: Phase 4 v2 (AST Repair) was completed historically but is a different scope

### Phase 5: Reverse Mode (Code → IR)
**Status**: In Progress
**Beads**: lift-sys-131 through lift-sys-145, lift-sys-178
**Goal**: AST-based entity extraction, code→IR analysis, split-view UI, round-trip validation
**Current**: lift-sys-178 (IR Interpreter) is in_progress

### Phase 6: Performance + Testing + Deployment
**Status**: Planned (not started)
**Beads**: lift-sys-146 through lift-sys-162, lift-sys-179
**Goal**: Performance optimization, comprehensive testing, documentation, production deployment

### Phase 7: IR-Level Constraints
**Status**: COMPLETE ✅
**Beads**: lift-sys-174, lift-sys-175, lift-sys-177
**Goal**: IR-level constraint detection and validation for code generation quality
**Completion**: Week 2 finished 2025-10-17 (54/56 tests passing)

---

## Cross-Cutting Infrastructure

These technologies are used across multiple phases and don't map to a single phase number:

### Constrained Generation Infrastructure
**Research Foundation**:
- XGrammar (arXiv:2411.15100) - Efficient CFG constrained generation
- llguidance (Microsoft Research) - Super-fast structured outputs
- Constrained Decoding (arXiv:2501.10868) - Foundational techniques

**Usage**: All phases use constrained generation for:
- JSON schema enforcement in IR generation
- Guaranteed valid output structure
- ~50μs/token mask computation

---

## Future Work (Not Yet Assigned to Phases)

### GenCP Integration
**Research**: arXiv:2407.13490
**Goal**: CSP-based systematic typed hole filling with coordinated constraint propagation
**Note**: Related to Phase 0 beads (182-189) but implementation timeline TBD

### Conjecturing Framework
**Research**: arXiv:2510.11986
**Goal**: Separate diagnostic measurement of IR generation quality vs code generation fidelity
**Note**: Epic lift-sys-230, designed but awaiting implementation

### MuSLR Enhancements
**Research**: arXiv:2510.04618
**Goal**: Advanced confidence scoring and reasoning taxonomies
**Note**: Some features (lift-sys-163) approved for Phase 3, others deferred

---

## Historical Phases (Completed)

These phases were completed before the current roadmap structure:

- **Phase 1 (historical)**: Backend foundation for whole-project reverse mode (COMPLETE)
- **Phase 2 (historical)**: Frontend UI with mode toggle (COMPLETE)
- **Phase 3 (historical)**: Results display, multi-IR visualization (COMPLETE)
- **Phase 4 (historical)**: Testing & polish (COMPLETE)
- **Phase 4 v2**: Deterministic AST repair (COMPLETE, lift-sys-177)
- **Phase 5A**: Various fixes and improvements (COMPLETE)

---

## Labeling Guidelines

When referencing phases in documentation:

1. **Use phase numbers** for active roadmap work (Phase 0-7)
2. **Use "Infrastructure"** for cross-cutting technologies (XGrammar, llguidance, etc.)
3. **Use "Future Work"** for planned research without assigned phases
4. **Avoid ad-hoc labels** like "Foundation", "Diagnostic", "Enhancement" without phase context

### Examples

✅ **Good**:
- "Phase 1: Enhanced IR + Typed Holes"
- "Infrastructure: Constrained Generation"
- "Future Work: Conjecturing Framework"

❌ **Bad**:
- "Phase 5 – Production" (Phase 5 is reverse mode, not production)
- "Foundation" (ambiguous - what phase?)
- "Diagnostic – Planned" (not a phase)

---

## See Also

- `ALL_RESEARCH_BEADS_SUMMARY.md` - Complete bead list with research enhancements
- `APPROVED_ENHANCEMENTS_SUMMARY.md` - Approved Phase 3 enhancements (ACE + MuSLR)
- Phase-specific docs: `PHASE_7_WEEK_2_COMPLETE.md`, etc.
