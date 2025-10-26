# Repository Organization

**Last Updated**: October 16, 2025

This document explains the current repository structure and file organization.

## Directory Structure

```
lift-sys/
├── claude.md                    # Project-specific Claude instructions
├── LICENSE.md                   # Project license
├── README.md                    # Main project documentation
├── RELEASE_NOTES.md             # Version history and release notes
│
├── docs/                        # All documentation
│   ├── STRATEGIC_OVERVIEW.md    # Current strategic assessment and paths forward
│   ├── archive/                 # Historical session summaries and reports
│   ├── sessions/                # Recent session results and analysis
│   ├── research/                # Research documents and proposals
│   ├── plans/                   # Strategic plans and roadmaps
│   └── reference/               # Stable reference documentation
│
├── debug/                       # Test runners, debug scripts, utilities
│
├── logs/                        # Test logs and benchmark results
│
├── benchmark_results/           # Benchmark JSON outputs
│
├── lift_sys/                    # Main Python package
│   ├── codegen/                 # Code generation modules
│   ├── forward_mode/            # Forward mode IR generation
│   ├── inference/               # Modal deployment and inference
│   ├── providers/               # LLM provider abstractions
│   ├── reverse_mode/            # Reverse mode code analysis
│   └── validation/              # IR and code validation
│
└── tests/                       # Pytest test suite
    ├── integration/             # Integration tests
    ├── unit/                    # Unit tests
    └── fixtures/                # Test fixtures and helpers
```

## Documentation Organization

### Root Documents
- **STRATEGIC_OVERVIEW.md**: Current state assessment, paths forward
- Keep in `docs/` for easy access

### docs/archive/
Historical session summaries, implementation reports, and phase completion documents:
- `PHASE_*_*.md` - Phase completion summaries
- `SESSION_SUMMARY_*.md` - Older session summaries
- `WEEK_*_*.md` - Weekly progress reports
- `*_IMPLEMENTATION_SUMMARY.md` - Feature implementation summaries
- `*_FIX*.md` - Bug fix summaries

### docs/sessions/
Recent session results and analysis (keep last 2-3 sessions):
- `QWEN25_32B_RESULTS.md` - Baseline testing results
- `BEST_OF_N_ANALYSIS.md` - Best-of-N failure analysis
- `PHASE3_COMPLETE_SUMMARY.md` - Complete Phase 3 summary
- `QWEN3_*.md` - Qwen3 investigation results

### docs/research/
Research documents, proposals, and assessments:
- `CONSTRAINED_GENERATION_RESEARCH.md` - XGrammar/vLLM research
- `AICI_INTEGRATION_PLAN.md` - AICI integration proposal
- `SWE_SMITH_*.md` - SWE-Smith evaluation and integration
- Research on semantic IR, ACE, MUSLR, etc.

### docs/plans/
Strategic plans and roadmaps:
- `BREAKTHROUGH_PATH_EXECUTIVE_SUMMARY.md` - Executive summary
- `TEST_PLAN_COMPREHENSIVE.md` - Comprehensive test strategy
- `THREE_PHASE_*.md` - Multi-phase implementation plans
- Week-by-week implementation plans

### docs/reference/
Stable reference documentation:
- `IR_DESIGN.md` - IR schema and design principles
- `MODAL_SETUP.md` - Modal deployment guide
- `AUTHENTICATION.md` - Auth setup and configuration
- `OAUTH-QUICKSTART.md` - OAuth integration quickstart

## Test and Debug Scripts

### debug/
All test runners, debug scripts, and utilities:
- `run_*.py` - Test runners (phase tests, benchmarks)
- `test_*.py` - Individual test scripts
- `debug_*.py` - Debug and diagnostic scripts
- `check_*.py` - Validation scripts
- `performance_benchmark.py` - Benchmark infrastructure
- `test_cases_*.py` - Test case definitions
- `wake_modal.py` - Modal endpoint wake-up utility

## Logs

### logs/
Test execution logs and results (gitignored):
- `phase*.log` - Phase test execution logs
- `benchmark_*.log` - Benchmark run logs
- `modal_*.log` - Modal deployment logs
- `validation_*.log` - Validation test logs

**Note**: Logs are generated during test runs and are not committed to git.

## Principles

1. **Archive, don't delete**: Historical documents moved to `docs/archive/`, never deleted
2. **Recent vs. historical**: Last 2-3 session summaries in `docs/sessions/`, older ones in `docs/archive/`
3. **Clear categories**: Research, plans, reference, and sessions are distinct
4. **Clean root**: Only essential files (README, LICENSE, CLAUDE, RELEASE_NOTES) in root
5. **Executable scripts**: All `.py` files in `debug/` for easy access

## Migration Notes

**Date**: October 16, 2025

Reorganized repository to improve clarity and maintainability:
- Moved 50+ markdown files from root to organized docs structure
- Moved 50+ Python scripts from root to debug/
- Created clear separation between active and archived documentation
- Preserved all git history through `git mv` (renames tracked)

Previous structure had accumulated files in root over multiple development sessions. New structure provides:
- Easy navigation to current strategic docs
- Clear archival of historical work
- Separation of concerns (docs vs. code vs. logs)
- Better onboarding for new contributors

## Finding Things

**Current strategic assessment**: `docs/STRATEGIC_OVERVIEW.md`
**Recent test results**: `docs/sessions/`
**Historical context**: `docs/archive/`
**Implementation guides**: `docs/reference/`
**Run tests**: `debug/run_*.py`
**Benchmark infrastructure**: `debug/performance_benchmark.py`

## Maintenance

When adding new files:
- Session summaries → `docs/sessions/` (move to archive after 2-3 sessions)
- Research documents → `docs/research/`
- Strategic plans → `docs/plans/`
- Reference docs → `docs/reference/`
- Test scripts → `debug/`
- Logs → `logs/` (gitignored)

When archiving:
- Move older session summaries from `docs/sessions/` to `docs/archive/`
- Keep `docs/sessions/` lean (last 2-3 sessions only)
- Never delete archived documents
