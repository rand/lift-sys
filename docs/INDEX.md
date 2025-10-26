# lift-sys Documentation Index

**Last Updated:** 2025-10-25
**Purpose:** Central navigation hub for all lift-sys documentation

---

## Quick Start

**New to lift-sys?** Start here:
1. [README.md](../README.md) - Project overview and setup
2. [CLAUDE.md](../CLAUDE.md) - Development guidelines (project-specific)
3. [CURRENT_STATE.md](../CURRENT_STATE.md) - Current status and active work

**Looking for specific info?** Use the categories below.

---

## Active Work

### ICS (Integrated Context Studio) - PRIMARY UI
**Location:** `docs/ics/`

The interactive specification editor with real-time semantic analysis. This is the primary user interface for lift-sys.

**Key Documents:**
- [ICS Master Spec](ics/ICS_MASTER_SPEC.md) - Complete system architecture
- [ICS Phase 4 Complete](ics/ICS_PHASE4_ARTIFACTS_COMPLETE.md) - Artifact generation status
- [ICS Execution Plan](../plans/ics-execution-plan.md) - 32-step implementation plan
- [ICS Interface Spec](ics/ICS_INTERFACE_SPECIFICATION.md) - Component interfaces

**Status:** Phase 4 complete, Phase 1 implementation ready (32 Beads issues: lift-sys-308 to 339)

### Backend Pipeline (Phases 1-7)
**Status:** Partially working (80% execution success, known gaps)

**See:** [Backend Status](issues/BACKEND_STATUS.md) for detailed breakdown

---

## Infrastructure

### Modal.com (Compute Platform)
**Location:** `docs/modal/`

Serverless GPU compute for LLM inference. Currently operational.

**Key Documents:**
- [Modal Reference](modal/MODAL_REFERENCE.md) - Patterns and best practices
- [Modal Workflow](modal/MODAL_WORKFLOW.md) - Development workflow
- [Modal Endpoints](modal/MODAL_ENDPOINTS.md) - API endpoints
- [Modal Optimizations](modal/MODAL_OPTIMIZATIONS_20251022.md) - Performance tuning

### Supabase (Database)
**Location:** `docs/supabase/`

PostgreSQL database with auth and RLS. Schema designed, deployment pending.

**Key Documents:**
- [Supabase Schema](supabase/SUPABASE_SCHEMA.md) - Database schema
- [Setup Instructions](supabase/SUPABASE_SETUP_INSTRUCTIONS.md) - Configuration guide
- [Connection Troubleshooting](supabase/SUPABASE_CONNECTION_TROUBLESHOOTING.md) - Common issues
- [Session Management](supabase/API_SESSION_MANAGEMENT.md) - Session storage patterns

### Observability (Honeycomb)
**Location:** `docs/observability/`

**Status:** Planned, not yet implemented

---

## Architecture & Planning

### PRDs and RFCs
**Location:** `docs/PRDs and RFCs/`

Product requirements and architectural decisions.

**Key Documents:**
- [PRD_LIFT.md](PRDs and RFCs/PRD_LIFT.md) - Overall product vision
- [RFC_LIFT_ARCHITECTURE.md](PRDs and RFCs/RFC_LIFT_ARCHITECTURE.md) - Technical architecture
- [PRD_INTERACTIVE_REFINEMENT.md](PRDs and RFCs/PRD_INTERACTIVE_REFINEMENT.md) - Human-AI collaboration

### Planning Documents
**Location:** `docs/planning/`

Strategic plans, roadmaps, and execution plans for all features.

**Key Documents:**
- [Master Plan](planning/MASTER_PLAN.md) - Overall strategy
- [Strategic Overview](planning/STRATEGIC_OVERVIEW.md) - High-level direction
- [Integration Roadmap](planning/INTEGRATION_ROADMAP.md) - Component integration
- [Semantic IR Plans](planning/SEMANTIC_IR_IMPLEMENTATION_PLAN.md) - IR development

**Major Feature Plans:**
- DSPy + Pydantic AI: [Hole-driven development planning](planning/)
- Reverse Mode: [whole-project-reverse-mode-plan.md](planning/whole-project-reverse-mode-plan.md)
- Multi-Language: [MULTI_LANGUAGE_STRATEGY.md](planning/MULTI_LANGUAGE_STRATEGY.md)

### Phase Documentation
**Location:** `docs/phases/`

Completion reports and status for development phases.

**Completed Phases:**
- [Phase 4: AST Repair](phases/PHASE_4_COMPLETE.md)
- [Phase 5: Assertion Checking](phases/PHASE_5_COMPLETION_SUMMARY.md)
- [Phase 6: Code Generation](phases/PHASE_6_COMPLETION.md)
- [Phase 7: IR Constraints](phases/PHASE_7_COMPLETE.md) - 97.8% tests passing

**Planning:**
- [Phase Structure](phases/PHASE_STRUCTURE.md) - How phases are organized
- [Phase 5 IR Interpreter](phases/PHASE_5_IR_INTERPRETER_DESIGN.md)
- [Phase 6 Email Validation Analysis](phases/PHASE_6_EMAIL_VALIDATION_ANALYSIS.md)
- [Phase 7 Architecture](phases/PHASE_7_ARCHITECTURE.md)

---

## Research & Analysis

### Research Documents
**Location:** `docs/research/`

Research analyses, assessments, and proposals for enhancements.

**Backend Enhancements (Queued):**
- ACE: [Implementation Proposal](research/ACE_IMPLEMENTATION_PROPOSAL.md), [Research Analysis](research/ACE_RESEARCH_ANALYSIS.md)
- MUSLR: [Implementation Proposal](research/MUSLR_IMPLEMENTATION_PROPOSAL.md), [Examples](research/MUSLR_ENHANCEMENT_EXAMPLES.md)
- [Research Summary: ACE & MUSLR](research/RESEARCH_SUMMARY_ACE_MUSLR.md)

**Technology Assessments:**
- [Constrained Generation Assessment](research/CONSTRAINED_GENERATION_ASSESSMENT.md) - XGrammar evaluation
- [Calligrapher Assessment](research/CALLIGRAPHER_ASSESSMENT.md)
- [Static Analysis Assessment](research/STATIC_ANALYSIS_ASSESSMENT.md)
- [Synthesis Verification](research/SYNTHESIS_VERIFICATION_ASSESSMENT.md)

**All Research Summaries:**
- [All Research Beads Summary](research/ALL_RESEARCH_BEADS_SUMMARY.md)
- [Research Summary Complete](research/RESEARCH_SUMMARY_COMPLETE.md)

---

## Testing & Quality

### Testing Documentation
**Location:** `docs/testing/`

Test strategies, results, and improvements.

**Key Documents:**
- [Persistent Failures Analysis](testing/PERSISTENT_FAILURES_ANALYSIS.md) - Known failures and root causes
- [Test Improvements Summary](testing/TEST_IMPROVEMENTS_SUMMARY.md)
- [Quick Test Reference](testing/QUICK_TEST_REFERENCE.md)
- [Making Tests Faster](testing/MAKING_TESTS_FASTER.md)

### Known Issues
**See:** [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) in root for current blockers and bugs

---

## Reference Documentation

### Technical Specifications
**Location:** `docs/reference/`

Core specifications, guides, and references.

**IR & Architecture:**
- [IR Specification](reference/IR_SPECIFICATION.md) - Intermediate representation format
- [Semantic IR Specification](reference/SEMANTIC_IR_SPECIFICATION.md)
- [IR to Code Architecture](reference/IR_TO_CODE_ARCHITECTURE.md)
- [Constraint Reference](reference/CONSTRAINT_REFERENCE.md)

**Integration Guides:**
- [XGrammar Integration Guide](reference/XGRAMMAR_INTEGRATION_GUIDE.md)
- [Qwen3 Coder Guide](reference/QWEN3_CODER_GUIDE.md)

**Development Guides:**
- [Best Practices](reference/BEST_PRACTICES.md)
- [Workflow Guides](reference/WORKFLOW_GUIDES.md)
- [Response Recording Guide](reference/RESPONSE_RECORDING_GUIDE.md)
- [FAQ](reference/FAQ.md)

**Feature Specs:**
- [Conjecturing Technical Spec](reference/CONJECTURING_TECHNICAL_SPEC.md)
- [Semantic Annotation Proposal](reference/SEMANTIC_ANNOTATION_PROPOSAL.md)
- [User Guide: Constraints](reference/USER_GUIDE_CONSTRAINTS.md)

### Important Top-Level References

**In `docs/` root:**
- [PERFORMANCE.md](PERFORMANCE.md) - Performance benchmarks and optimization
- [REVERSE_MODE.md](REVERSE_MODE.md) - Reverse mode feature overview

---

## Session History & Status

### Session Logs
**Location:** `docs/sessions/`

Historical session summaries, status updates, and reviews.

**Recent Sessions:**
- [Project Review 2025-10-14](sessions/PROJECT_REVIEW_2025-10-14.md)
- [Session Summary 2025-10-14](sessions/session-summary-2025-10-14.md)
- [Plan Status 2025-10-14](sessions/PLAN_STATUS_2025-10-14.md)

**Weekly Summaries:**
- Week 1: [Temperature 0.8 Results](sessions/WEEK_1_TEMPERATURE_08_RESULTS.md)
- Week 2: [AST Repair Expansion](sessions/WEEK_2_AST_REPAIR_EXPANSION.md)
- Week 5: [LSP Summary](sessions/WEEK_5_LSP_SUMMARY.md), [LSP Results](sessions/week5-lsp-results.md)
- Week 6: [Summary](sessions/week6-summary.md)

**State Assessments:**
- [Current State Assessment](sessions/current-state-assessment.md)
- [Implementation Audit](sessions/implementation-audit.md)

---

## Specialized Features

### Conjecturing
**Location:** `docs/conjecturing/`

Auto-suggesting constraints and semantic refinements feature.

**See:** [Conjecturing Index](conjecturing/CONJECTURING_INDEX.md)

### Frontend Design
**Location:** `docs/frontend/`

Frontend-specific design systems and UX documentation.

**Key Documents:**
- [Frontend Design System](frontend/frontend-design-system.md)
- [Full UX Suite Approved](frontend/FULL_UX_SUITE_APPROVED.md)

---

## Archive

### Archived Documentation
**Location:** `docs/archive/`

Deprecated, superseded, or historical documents preserved for reference.

**Categories:**
- `docs/archive/summaries/` - Completed feature summaries
- Other archived files at top level

---

## Repository Organization

**See:** [REPOSITORY_ORGANIZATION.md](../REPOSITORY_ORGANIZATION.md) for detailed rules on where files belong

**Quick Rules:**
- **Documentation** → `docs/{category}/`
- **Scripts** → `scripts/{category}/`
- **Debug data** → `debug/`
- **Root** → Only ~10 essential files

---

## Navigation Tips

### By Role

**Product Manager / Stakeholder:**
- Start: [PRD_LIFT.md](PRDs and RFCs/PRD_LIFT.md)
- Status: [CURRENT_STATE.md](../CURRENT_STATE.md)
- Roadmap: [SEMANTIC_IR_ROADMAP.md](../SEMANTIC_IR_ROADMAP.md)

**Developer (Backend):**
- Architecture: [RFC_LIFT_ARCHITECTURE.md](PRDs and RFCs/RFC_LIFT_ARCHITECTURE.md)
- Status: [Backend Status](issues/BACKEND_STATUS.md)
- Testing: [Persistent Failures](testing/PERSISTENT_FAILURES_ANALYSIS.md)
- Modal: [Modal Reference](modal/MODAL_REFERENCE.md)

**Developer (Frontend):**
- ICS Spec: [ICS Master Spec](ics/ICS_MASTER_SPEC.md)
- Plan: [ICS Execution Plan](../plans/ics-execution-plan.md)
- Design: [Frontend Design System](frontend/frontend-design-system.md)

**Researcher:**
- Research: [Research Summary](research/RESEARCH_SUMMARY_COMPLETE.md)
- Assessments: Browse [docs/research/](research/)
- Enhancements: [ACE](research/ACE_RESEARCH_ANALYSIS.md), [MUSLR](research/MUSLR_RESEARCH_ANALYSIS.md)

### By Task

**Setting up infrastructure:**
- Modal: [docs/modal/](modal/)
- Supabase: [docs/supabase/](supabase/)
- Observability: [docs/observability/](observability/)

**Implementing ICS:**
- Start: [ICS Master Spec](ics/ICS_MASTER_SPEC.md)
- Plan: [ICS Execution Plan](../plans/ics-execution-plan.md)
- Issues: Check Beads (lift-sys-308 to 339)

**Debugging backend:**
- Failures: [Persistent Failures Analysis](testing/PERSISTENT_FAILURES_ANALYSIS.md)
- Status: [Backend Status](issues/BACKEND_STATUS.md)
- Phases: [docs/phases/](phases/)

**Understanding architecture:**
- RFC: [RFC_LIFT_ARCHITECTURE.md](PRDs and RFCs/RFC_LIFT_ARCHITECTURE.md)
- IR: [IR Specification](reference/IR_SPECIFICATION.md)
- Constraints: [Constraint Reference](reference/CONSTRAINT_REFERENCE.md)

---

## Contributing

When adding new documentation:

1. **Choose the right category** based on content type
2. **Follow naming conventions**: `SCREAMING_SNAKE_CASE.md`
3. **Update this INDEX** to make it discoverable
4. **Cross-reference** related docs
5. **Include metadata**: Last Updated, Status, Purpose

**See:** [REPOSITORY_ORGANIZATION.md](../REPOSITORY_ORGANIZATION.md) for complete guidelines

---

**Last Updated:** 2025-10-25
**Maintainer:** See [CLAUDE.md](../CLAUDE.md) for development workflow
