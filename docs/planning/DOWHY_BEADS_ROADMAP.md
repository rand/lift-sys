# DoWhy Integration - Beads Roadmap

**Date**: 2025-10-25
**Status**: Ready for Implementation
**Phase**: Phase 4 - Artifacts Generation
**Parent**: dowhy-execution-plan.md

---

## Purpose

This document maps the DoWhy execution plan to Beads issues for tracking and execution.

**Total Issues**: 31 (dowhy-001 through dowhy-031)

---

## Issue Creation Commands

### Phase 1: Reverse Mode Enhancement (Weeks 1-4)

**Week 1: H20 - CausalGraphBuilder**

```bash
# STEP-01: Setup DoWhy Environment
bd create "Setup DoWhy Python 3.11 environment and package structure" \
  -t task -p P0 --label dowhy-integration,h20,infrastructure \
  --json

# STEP-02: AST Node Extractor
bd create "Implement AST node extraction for causal graph builder" \
  -t task -p P0 --label dowhy-integration,h20,implementation \
  --json

# STEP-03: Data Flow Edge Extractor
bd create "Implement data flow edge extraction from AST" \
  -t task -p P0 --label dowhy-integration,h20,implementation \
  --json

# STEP-04: Control Flow Edge Extractor
bd create "Implement control flow edge extraction from AST" \
  -t task -p P0 --label dowhy-integration,h20,implementation \
  --json

# STEP-05: Edge Pruning Logic
bd create "Implement causal edge pruning (exclude logging, keep state changes)" \
  -t task -p P0 --label dowhy-integration,h20,implementation \
  --json
```

**Week 2: H21 - SCMFitter**

```bash
# STEP-06: Static Mechanism Inference
bd create "Implement static causal mechanism inference from code" \
  -t task -p P0 --label dowhy-integration,h21,implementation \
  --json

# STEP-07: Execution Trace Collection
bd create "Implement runtime instrumentation for execution trace collection" \
  -t task -p P0 --label dowhy-integration,h21,implementation \
  --json

# STEP-08: Dynamic Mechanism Fitting
bd create "Implement dynamic SCM fitting using DoWhy auto-assignment" \
  -t task -p P0 --label dowhy-integration,h21,implementation \
  --json

# STEP-09: Cross-Validation
bd create "Implement cross-validation for fitted SCM (R² ≥0.7 threshold)" \
  -t task -p P0 --label dowhy-integration,h21,implementation \
  --json
```

**Week 3: H22 - InterventionEngine + IR**

```bash
# STEP-10: Intervention API
bd create "Implement InterventionEngine with estimate_impact() API" \
  -t task -p P0 --label dowhy-integration,h22,implementation \
  --json

# STEP-11: Confidence Intervals
bd create "Implement bootstrap confidence interval estimation (95% CI)" \
  -t task -p P0 --label dowhy-integration,h22,implementation \
  --json

# STEP-12: IR Schema Extension
bd create "Extend IR schema with causal_model and causal_metadata fields" \
  -t task -p P0 --label dowhy-integration,ir-integration,implementation \
  --json

# STEP-13: SCM Serialization
bd create "Implement SCM serialization/deserialization to JSON" \
  -t task -p P0 --label dowhy-integration,ir-integration,implementation \
  --json

# STEP-14: Lifter Integration
bd create "Integrate causal analysis into Lifter.lift() with include_causal flag" \
  -t task -p P0 --label dowhy-integration,ir-integration,implementation \
  --json
```

**Week 4: Testing & Documentation**

```bash
# STEP-15: Performance Benchmarks
bd create "Create performance benchmarks (<30s for 100 files)" \
  -t task -p P0 --label dowhy-integration,testing,performance \
  --json

# STEP-16: Accuracy Validation
bd create "Validate causal graph accuracy (≥90% precision, ≥85% recall)" \
  -t task -p P0 --label dowhy-integration,testing,validation \
  --json

# STEP-17: Real Codebase Testing
bd create "Test causal analysis on 3 real codebases (10-100 files)" \
  -t task -p P0 --label dowhy-integration,testing,validation \
  --json

# STEP-18: Documentation
bd create "Write user guide, API docs, and tutorial for causal analysis" \
  -t task -p P0 --label dowhy-integration,documentation \
  --json

# STEP-19: Code Review & Polish
bd create "Code review and final polish for P1 release" \
  -t task -p P0 --label dowhy-integration,refinement \
  --json
```

### Phase 2: Test Generation (Weeks 5-7)

**Week 5: H23 - CausalPathExtractor**

```bash
# STEP-20: Path Extraction Algorithm
bd create "Implement causal path extraction from SCM" \
  -t task -p P1 --label dowhy-integration,h23,implementation \
  --json

# STEP-21: Importance Scoring
bd create "Implement causal importance scoring for paths" \
  -t task -p P1 --label dowhy-integration,h23,implementation \
  --json

# STEP-22: Priority Assignment
bd create "Implement path priority assignment (HIGH/MEDIUM/LOW)" \
  -t task -p P1 --label dowhy-integration,h23,implementation \
  --json

# STEP-23: Performance Optimization
bd create "Optimize path extraction with caching and parallelization" \
  -t task -p P1 --label dowhy-integration,h23,optimization \
  --json
```

**Week 6: TestCaseGenerator**

```bash
# STEP-24: Input Generation
bd create "Implement activating input generation for causal paths" \
  -t task -p P1 --label dowhy-integration,h23,implementation \
  --json

# STEP-25: Output Prediction
bd create "Implement output prediction using SCM forward simulation" \
  -t task -p P1 --label dowhy-integration,h23,implementation \
  --json

# STEP-26: Test Code Generation
bd create "Implement pytest test code generation from test cases" \
  -t task -p P1 --label dowhy-integration,h23,implementation \
  --json

# STEP-27: Integration
bd create "Create CausalTestGenerator class and integrate components" \
  -t task -p P1 --label dowhy-integration,h23,integration \
  --json
```

**Week 7: Integration & Validation**

```bash
# STEP-28: Integration with Validation Pipeline
bd create "Integrate causal test generation with lift-sys validation" \
  -t task -p P1 --label dowhy-integration,integration,validation \
  --json

# STEP-29: Real Codebase Testing
bd create "Test generation on 3 real codebases (≥95% pass, ≥90% detect bugs)" \
  -t task -p P1 --label dowhy-integration,testing,validation \
  --json

# STEP-30: Documentation
bd create "Write test generation guide, API docs, and examples" \
  -t task -p P1 --label dowhy-integration,documentation \
  --json

# STEP-31: Code Review & Release
bd create "Code review and release v2.0 (P1+P2 complete)" \
  -t task -p P1 --label dowhy-integration,refinement,release \
  --json
```

---

## Issue Dependencies

### Phase 1 Dependencies

```bash
# Week 1 (H20)
bd dep add <STEP-02> <STEP-01> --type blocks  # 02 blocks on 01
bd dep add <STEP-03> <STEP-02> --type blocks  # 03 blocks on 02
bd dep add <STEP-04> <STEP-02> --type blocks  # 04 blocks on 02
bd dep add <STEP-05> <STEP-03> --type blocks  # 05 blocks on 03
bd dep add <STEP-05> <STEP-04> --type blocks  # 05 blocks on 04

# Week 2 (H21)
bd dep add <STEP-06> <STEP-05> --type blocks  # 06 blocks on 05
bd dep add <STEP-07> <STEP-06> --type blocks  # 07 blocks on 06
bd dep add <STEP-08> <STEP-07> --type blocks  # 08 blocks on 07
bd dep add <STEP-09> <STEP-08> --type blocks  # 09 blocks on 08

# Week 3 (H22 + IR)
bd dep add <STEP-10> <STEP-09> --type blocks  # 10 blocks on 09
bd dep add <STEP-11> <STEP-10> --type blocks  # 11 blocks on 10
bd dep add <STEP-12> <STEP-10> --type blocks  # 12 blocks on 10
bd dep add <STEP-13> <STEP-12> --type blocks  # 13 blocks on 12
bd dep add <STEP-14> <STEP-13> --type blocks  # 14 blocks on 13

# Week 4 (Testing)
bd dep add <STEP-15> <STEP-14> --type blocks  # 15 blocks on 14
bd dep add <STEP-16> <STEP-14> --type blocks  # 16 blocks on 14
bd dep add <STEP-17> <STEP-16> --type blocks  # 17 blocks on 16
bd dep add <STEP-18> <STEP-17> --type blocks  # 18 blocks on 17
bd dep add <STEP-19> <STEP-18> --type blocks  # 19 blocks on 18
```

### Phase 2 Dependencies

```bash
# Week 5 (H23 path extraction)
bd dep add <STEP-20> <STEP-19> --type blocks  # 20 blocks on P1 complete
bd dep add <STEP-21> <STEP-20> --type blocks  # 21 blocks on 20
bd dep add <STEP-22> <STEP-21> --type blocks  # 22 blocks on 21
bd dep add <STEP-23> <STEP-22> --type blocks  # 23 blocks on 22

# Week 6 (Test generation)
bd dep add <STEP-24> <STEP-23> --type blocks  # 24 blocks on 23
bd dep add <STEP-25> <STEP-24> --type blocks  # 25 blocks on 24
bd dep add <STEP-26> <STEP-25> --type blocks  # 26 blocks on 25
bd dep add <STEP-27> <STEP-26> --type blocks  # 27 blocks on 26

# Week 7 (Integration + validation)
bd dep add <STEP-28> <STEP-27> --type blocks  # 28 blocks on 27
bd dep add <STEP-29> <STEP-28> --type blocks  # 29 blocks on 28
bd dep add <STEP-30> <STEP-29> --type blocks  # 30 blocks on 29
bd dep add <STEP-31> <STEP-30> --type blocks  # 31 blocks on 30
```

---

## Quick Start (Creating All Issues)

**Option 1: Create all issues at once**

```bash
# Save commands to script
cat > create_dowhy_issues.sh <<'SCRIPT'
#!/bin/bash
# Run all bd create commands from above
# ... (paste all commands)
SCRIPT

chmod +x create_dowhy_issues.sh
./create_dowhy_issues.sh

# Then add dependencies
# (paste all bd dep add commands)
```

**Option 2: Create week by week**

```bash
# Week 1 only
# (paste Week 1 commands)

# Verify
bd list --label dowhy-integration --json

# When Week 1 complete, create Week 2
# ...
```

---

## Tracking Progress

**View all DoWhy issues**:
```bash
bd list --label dowhy-integration --json | jq '.[] | {id, title, status}'
```

**View ready work**:
```bash
bd ready --label dowhy-integration --json --limit 5
```

**View by phase**:
```bash
# Phase 1 (H20-H22)
bd list --label h20,h21,h22 --json

# Phase 2 (H23)
bd list --label h23 --json
```

**View by type**:
```bash
bd list --label implementation --json  # Implementation tasks
bd list --label testing --json         # Testing tasks
bd list --label documentation --json   # Documentation tasks
```

---

## Milestones

**Milestone 1: H20 Complete** (End of Week 1)
- Issues: dowhy-001 through dowhy-005
- Deliverable: Causal graph builder working

**Milestone 2: H21 Complete** (End of Week 2)
- Issues: dowhy-006 through dowhy-009
- Deliverable: SCM fitter working (static + dynamic)

**Milestone 3: H22 + IR Complete** (End of Week 3)
- Issues: dowhy-010 through dowhy-014
- Deliverable: Intervention engine + IR integration

**Milestone 4: P1 Complete** (End of Week 4)
- Issues: dowhy-015 through dowhy-019
- Deliverable: Reverse mode with causal analysis (tested, documented)

**Milestone 5: H23 Complete** (End of Week 7)
- Issues: dowhy-020 through dowhy-027
- Deliverable: Causal test generator

**Milestone 6: P2 Complete** (End of Week 7)
- Issues: dowhy-028 through dowhy-031
- Deliverable: Test generation (tested, documented, released)

---

## Status Updates

**After each step completion**:
```bash
# Mark complete
bd close dowhy-XXX --reason "Completed: <brief summary>" --json

# Export state
bd export -o .beads/issues.jsonl

# Commit
git add .beads/issues.jsonl
git commit -m "beads: Complete dowhy-XXX - <description>"
```

---

## Reference Links

- **Technical Review**: `docs/research/DOWHY_TECHNICAL_REVIEW.md`
- **Integration Spec**: `docs/planning/DOWHY_INTEGRATION_SPEC.md`
- **P1 Spec**: `specs/dowhy-reverse-mode-spec.md`
- **P2 Spec**: `specs/dowhy-test-generation-spec.md`
- **Typed Holes**: `specs/typed-holes-dowhy.md`
- **Execution Plan**: `plans/dowhy-execution-plan.md`

---

**Roadmap Status**: COMPLETE
**Ready for**: Issue creation and implementation kickoff
