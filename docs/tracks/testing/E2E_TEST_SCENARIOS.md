---
track: testing
document_type: test_scenarios
status: complete
priority: P1
completion: 100%
last_updated: 2025-10-26
session_protocol: |
  For new Claude Code session:
  1. Use this document for E2E test design reference (DoWhy integration)
  2. 10 test repositories defined with comprehensive scenarios
  3. Scenarios cover static mode, dynamic mode, performance, and edge cases
  4. Reference for future causal analysis testing
related_docs:
  - docs/tracks/testing/E2E_VALIDATION_PLAN.md
  - docs/tracks/testing/TESTING_STATUS.md
  - docs/MASTER_ROADMAP.md
---

# End-to-End Test Scenarios for DoWhy Integration

**Date**: 2025-10-26
**Status**: Design Complete
**Related Issues**: H20 (GraphExtractor), H21 (SCMFitter), H22 (InterventionEngine)

---

## Overview

This document defines comprehensive end-to-end test scenarios for the complete DoWhy integration pipeline:

```
Python Code → CausalGraph → FittedSCM → InterventionResult
     (H20)        (H21)           (H22)
```

**Goal**: 100% confidence that the integration works correctly across all edge cases, performance requirements, and error conditions.

---

## Test Repository Structure

We define **10 test repositories** (see `tests/causal/fixtures/test_repositories.py`):

| Repository | Description | Nodes | Edges | Test Focus |
|------------|-------------|-------|-------|------------|
| **simple_linear** | x → y (linear) | 2 | 1 | Basic pipeline |
| **diamond** | x → y,z; y,z → w | 4 | 4 | Multi-path, collider |
| **chain** | x → y → z → w | 4 | 3 | Transitive deps |
| **nonlinear** | x → y (quadratic) | 2 | 1 | Nonlinear mechanisms |
| **multi_parent** | a,b,c → result | 4 | 3 | Multi-variable regression |
| **empty** | Single node, no edges | 1 | 0 | Edge case: minimal |
| **conditional** | x → y (piecewise) | 2 | 1 | Control flow |
| **mixed** | x → y (linear) → z (nonlinear) | 3 | 2 | Mixed mechanisms |
| **wide** | x → [y1..y5] | 6 | 5 | Fan-out structure |
| **large** | 20-node chain | 20 | 19 | Performance at scale |

---

## Scenario Categories

### Category 1: Static Mode (No Traces)

**Scenario 1.1: Simple Linear (Static)**
- **Repository**: `simple_linear`
- **Mode**: Static only (no traces)
- **Steps**:
  1. Extract graph from code → Expect: `x → y`
  2. Fit SCM (static) → Expect: `y` has linear mechanism, coef=2.0
  3. Validate SCM structure → Expect: graph structure preserved
- **Success Criteria**:
  - Graph extraction completes in <1s
  - SCM fitting completes in <1s (static mode requirement)
  - Mechanism type correctly inferred as "linear"
  - Coefficient extracted as 2.0 (or marked as "inferred from static analysis")

**Scenario 1.2: Diamond (Static)**
- **Repository**: `diamond`
- **Mode**: Static only
- **Steps**:
  1. Extract graph → Expect: 4 nodes, 4 edges (diamond structure)
  2. Fit SCM (static) → Expect: All mechanisms are linear
  3. Validate multi-parent node (`w`) → Expect: 2 parent edges preserved
- **Success Criteria**:
  - All 3 functions analyzed correctly
  - Node `w` has parents `[y, z]` in correct order
  - No spurious edges created

**Scenario 1.3: Mixed (Static)**
- **Repository**: `mixed`
- **Mode**: Static only
- **Steps**:
  1. Extract graph → Expect: `x → y → z`
  2. Fit SCM (static) → Expect: `y` is linear, `z` is nonlinear
- **Success Criteria**:
  - Static analyzer correctly distinguishes linear vs nonlinear
  - Polynomial degree inferred for `z` (degree=2)

---

### Category 2: Dynamic Mode (With Traces)

**Scenario 2.1: Simple Linear (Dynamic)**
- **Repository**: `simple_linear`
- **Mode**: Dynamic (100 traces)
- **Steps**:
  1. Extract graph → `x → y`
  2. Collect traces (100 samples) → DataFrame with columns `[x, y]`
  3. Fit SCM (dynamic) → Use DoWhy `gcm.auto.assign_causal_mechanisms()`
  4. Validate fit → R² ≥ 0.7 (should be ~1.0 for perfect linear)
  5. Execute intervention: `do(x=5)` → Expect: `y ≈ 10`
- **Success Criteria**:
  - Trace collection: <0.5s
  - SCM fitting: <2s
  - Intervention query: <100ms
  - R² ≥ 0.99 (perfect fit)
  - Intervention result: `y.mean ≈ 10.0, std < 0.5`

**Scenario 2.2: Diamond (Dynamic)**
- **Repository**: `diamond`
- **Mode**: Dynamic (100 traces)
- **Steps**:
  1. Extract graph → Diamond structure
  2. Collect traces → 100 samples, 4 columns `[x, y, z, w]`
  3. Fit SCM → All mechanisms fitted dynamically
  4. Cross-validate → 80/20 train/test split, R² ≥ 0.7 on test set
  5. Execute intervention: `do(x=5)` → Expect downstream effects on all nodes
- **Success Criteria**:
  - All nodes have fitted mechanisms
  - R² ≥ 0.95 for all edges (linear relationships)
  - Intervention propagates: `x=5 → y≈10 → w≈16`
  - Intervention result includes all 4 nodes

**Scenario 2.3: Multi-Parent (Dynamic)**
- **Repository**: `multi_parent`
- **Mode**: Dynamic (100 traces)
- **Steps**:
  1. Extract graph → `a,b,c → result`
  2. Collect traces → 3 exogenous inputs + 1 output
  3. Fit multi-variable linear regression → `result = 2*a + 3*b - c`
  4. Validate coefficients → Compare fitted vs expected
  5. Execute intervention: `do(a=5, b=2, c=1)` → Expect: `result ≈ 15`
- **Success Criteria**:
  - Multi-parent mechanism correctly fitted
  - Coefficients within 5% of expected: `{a: 2.0, b: 3.0, c: -1.0}`
  - Intervention with all parents set → Deterministic result (std ≈ 0)

**Scenario 2.4: Nonlinear (Dynamic)**
- **Repository**: `nonlinear`
- **Mode**: Dynamic (200 traces, more data for nonlinear)
- **Steps**:
  1. Extract graph → `x → y`
  2. Collect traces → Quadratic relationship
  3. Fit SCM → DoWhy should detect nonlinearity
  4. Validate: Linear fit R² < 0.7, Polynomial fit R² > 0.95
  5. Execute intervention: `do(x=3)` → Expect: `y ≈ 9`
- **Success Criteria**:
  - Nonlinear mechanism detected (not forced linear)
  - Polynomial fit significantly better than linear
  - Intervention result accurate: `y.mean ≈ 9.0, std < 1.0`

**Scenario 2.5: Conditional (Dynamic)**
- **Repository**: `conditional`
- **Mode**: Dynamic (200 traces)
- **Steps**:
  1. Extract graph → `x → y`
  2. Collect traces → Piecewise function (absolute value)
  3. Fit SCM → Should handle piecewise/nonlinear
  4. Execute interventions:
     - `do(x=-5)` → Expect: `y ≈ 5`
     - `do(x=3)` → Expect: `y ≈ 3`
- **Success Criteria**:
  - Piecewise function fitted (not necessarily perfect)
  - Both positive and negative interventions work correctly
  - Results within 10% tolerance (piecewise is harder to fit)

---

### Category 3: Intervention Types

**Scenario 3.1: Hard Intervention**
- **Repository**: `simple_linear`
- **Intervention**: `do(x=5)` (hard intervention)
- **Expected Behavior**:
  - `x` distribution becomes constant at 5.0
  - `x.std ≈ 0.0`
  - `y` affected deterministically: `y.mean ≈ 10.0`
- **Success Criteria**:
  - Hard intervention cuts all edges into `x`
  - Downstream nodes respond to new value

**Scenario 3.2: Soft Intervention (Shift)**
- **Repository**: `simple_linear`
- **Intervention**: `do(x=x+3)` (shift by +3)
- **Expected Behavior**:
  - `x` distribution shifts by +3 (mean increases by 3)
  - `y` distribution shifts by +6 (2 * shift)
- **Success Criteria**:
  - Distribution shape preserved (variance unchanged)
  - Mean shift propagates through mechanism

**Scenario 3.3: Soft Intervention (Scale)**
- **Repository**: `simple_linear`
- **Intervention**: `do(x=x*2)` (scale by 2x)
- **Expected Behavior**:
  - `x` distribution scales (std doubles)
  - `y` distribution scales (std quadruples: 2 * 2x)
- **Success Criteria**:
  - Variance increases by scale factor
  - Mean scales proportionally

**Scenario 3.4: Multiple Interventions**
- **Repository**: `diamond`
- **Intervention**: `do(x=5, z=10)` (two nodes)
- **Expected Behavior**:
  - `x` set to 5.0
  - `z` set to 10.0 (overrides natural mechanism)
  - `y` responds to `x` only: `y ≈ 10`
  - `w` responds to both: `w ≈ 20` (y + z)
- **Success Criteria**:
  - Both interventions applied simultaneously
  - Causal paths correctly preserved/cut

**Scenario 3.5: Intermediate Node Intervention**
- **Repository**: `chain`
- **Intervention**: `do(z=5)` (middle of chain)
- **Expected Behavior**:
  - `x, y` unchanged (upstream)
  - `z` set to 5.0
  - `w` affected: `w ≈ 15` (3*z)
- **Success Criteria**:
  - Intervention only affects downstream nodes
  - Upstream nodes independent of intervention

---

### Category 4: Performance Tests

**Scenario 4.1: Small Repository Performance**
- **Repository**: `simple_linear`
- **Steps**:
  1. Trace collection (100 samples) → <0.5s
  2. SCM fitting → <2s
  3. Intervention query → <100ms
- **Success Criteria**:
  - All timing requirements met
  - Results accurate despite speed

**Scenario 4.2: Medium Repository Performance**
- **Repository**: `diamond`
- **Steps**:
  1. Trace collection (100 samples, 4 nodes) → <1s
  2. SCM fitting → <3s
  3. Intervention query → <100ms
- **Success Criteria**:
  - Scales reasonably with node count

**Scenario 4.3: Large Repository Performance**
- **Repository**: `large` (20 nodes)
- **Steps**:
  1. Trace collection (100 samples, 20 nodes) → <5s
  2. SCM fitting (20 nodes, 19 edges) → <15s
  3. Intervention query → <500ms
- **Success Criteria**:
  - Total E2E time: <30s (requirement)
  - No memory issues with 20 nodes

**Scenario 4.4: High Sample Count Performance**
- **Repository**: `simple_linear`
- **Steps**:
  1. Trace collection (1000 samples) → <5s
  2. SCM fitting (1000 traces) → <10s (requirement)
  3. Intervention query → <100ms
- **Success Criteria**:
  - Meets 1000-trace performance requirement
  - Accuracy improves with more samples

**Scenario 4.5: Wide Graph Performance**
- **Repository**: `wide` (6 nodes, 5 children)
- **Steps**:
  1. Trace collection → <1s
  2. SCM fitting → <3s
  3. Intervention query (affects all children) → <100ms
- **Success Criteria**:
  - Fan-out doesn't degrade performance significantly
  - All children correctly affected by intervention

---

### Category 5: Error Cases

**Scenario 5.1: Invalid Code (Syntax Error)**
- **Input**: Code with syntax error
- **Expected Behavior**:
  - Graph extraction fails with clear error
  - Error message indicates syntax issue
- **Success Criteria**:
  - No crash
  - Error message helpful for debugging

**Scenario 5.2: Circular Dependencies**
- **Input**: Code with cyclic dependencies (not a DAG)
- **Expected Behavior**:
  - Graph extraction detects cycle
  - Raises `GraphError` with cycle information
- **Success Criteria**:
  - Clear error indicating which nodes form cycle
  - Suggests refactoring to break cycle

**Scenario 5.3: Empty File**
- **Input**: Empty Python file
- **Expected Behavior**:
  - Graph extraction returns empty graph
  - SCM fitting handles gracefully (no crash)
- **Success Criteria**:
  - Empty graph returned
  - No error raised (valid edge case)

**Scenario 5.4: Single Function (No Dependencies)**
- **Repository**: `empty`
- **Expected Behavior**:
  - Graph has 1 node, 0 edges
  - SCM fitting treats as exogenous/root node
  - Intervention works on single node
- **Success Criteria**:
  - Handled as valid minimal case
  - Intervention result contains only that node

**Scenario 5.5: Mismatched Traces**
- **Input**: Traces with columns that don't match graph nodes
- **Expected Behavior**:
  - SCM fitting raises `DataError`
  - Error message lists expected vs actual columns
- **Success Criteria**:
  - Clear error before attempting to fit
  - Suggests correcting trace collection

**Scenario 5.6: Insufficient Traces**
- **Input**: Only 5 traces (too few for reliable fitting)
- **Expected Behavior**:
  - SCM fitting raises `DataError` or warning
  - Suggests minimum of 10-50 samples
- **Success Criteria**:
  - Prevents unreliable fits
  - Guidance on sample size

**Scenario 5.7: Invalid Intervention Node**
- **Input**: Intervention on node not in graph (`do(z=5)` but graph has no `z`)
- **Expected Behavior**:
  - Intervention engine raises `ValidationError`
  - Error message: "node 'z' not in causal graph"
- **Success Criteria**:
  - Validation happens before execution
  - Clear error message

**Scenario 5.8: Intervention Without Traces**
- **Input**: SCM fitted in static mode, then try intervention
- **Expected Behavior**:
  - Intervention engine raises `InterventionError`
  - Error message: "SCM must contain 'traces' for interventions"
- **Success Criteria**:
  - Clear error explaining limitation
  - Suggests refitting with traces

---

### Category 6: Integration Tests

**Scenario 6.1: Full Pipeline (Simple)**
- **Repository**: `simple_linear`
- **Steps**:
  1. Extract graph from code
  2. Collect traces (100 samples)
  3. Fit SCM (dynamic)
  4. Execute intervention
  5. Serialize result
  6. Deserialize result
- **Success Criteria**:
  - All steps succeed without error
  - Round-trip serialization preserves data
  - End-to-end time: <5s

**Scenario 6.2: Full Pipeline (Complex)**
- **Repository**: `diamond`
- **Steps**: Same as 6.1
- **Success Criteria**:
  - Handles multi-path dependencies
  - Intervention affects all downstream nodes
  - End-to-end time: <10s

**Scenario 6.3: Multi-Session Workflow**
- **Repository**: `chain`
- **Steps**:
  1. Session 1: Extract graph, fit SCM, serialize
  2. Session 2: Deserialize SCM, execute intervention
- **Success Criteria**:
  - SCM can be saved and loaded
  - Interventions work on loaded SCM

**Scenario 6.4: Repeated Interventions**
- **Repository**: `simple_linear`
- **Steps**:
  1. Fit SCM once
  2. Execute 10 different interventions on same SCM
- **Success Criteria**:
  - SCM reusable across interventions
  - Each intervention query: <100ms

---

### Category 7: Validation Tests

**Scenario 7.1: Cross-Validation (Linear)**
- **Repository**: `simple_linear`
- **Steps**:
  1. Collect 200 traces
  2. Fit SCM with 80/20 train/test split
  3. Validate R² on held-out 20%
- **Success Criteria**:
  - Train R² ≥ 0.95
  - Test R² ≥ 0.95 (no overfitting)

**Scenario 7.2: Cross-Validation (Nonlinear)**
- **Repository**: `nonlinear`
- **Steps**:
  1. Collect 200 traces
  2. Fit SCM with cross-validation
  3. Check for overfitting
- **Success Criteria**:
  - Train R² > Test R² (some overfitting expected)
  - Test R² ≥ 0.7 (still predictive)

**Scenario 7.3: Noise Robustness**
- **Repository**: `simple_linear`
- **Steps**:
  1. Add Gaussian noise to traces (σ=0.5)
  2. Fit SCM on noisy data
  3. Execute intervention
- **Success Criteria**:
  - R² ≥ 0.7 despite noise
  - Intervention results within 10% of expected

---

## Test Execution Strategy

### Phase 1: Basic Functionality
Run scenarios: 1.1, 2.1, 3.1, 5.1, 5.4, 6.1

**Goal**: Verify basic pipeline works for simplest case

### Phase 2: Structural Complexity
Run scenarios: 1.2, 2.2, 2.3, 3.4, 3.5, 6.2

**Goal**: Verify multi-node, multi-edge structures

### Phase 3: Mechanism Complexity
Run scenarios: 1.3, 2.4, 2.5, 3.2, 3.3

**Goal**: Verify nonlinear and conditional mechanisms

### Phase 4: Performance
Run scenarios: 4.1, 4.2, 4.3, 4.4, 4.5

**Goal**: Verify all performance requirements met

### Phase 5: Error Handling
Run scenarios: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7, 5.8

**Goal**: Verify graceful error handling

### Phase 6: Advanced Features
Run scenarios: 6.3, 6.4, 7.1, 7.2, 7.3

**Goal**: Verify advanced workflows and validation

---

## Success Criteria Summary

### Functional Requirements
- ✅ All 10 test repositories extract correct graphs
- ✅ Static mode (no traces) works for all repositories
- ✅ Dynamic mode (with traces) achieves R² ≥ 0.7 for all linear relationships
- ✅ All intervention types work correctly (hard, soft shift, soft scale)
- ✅ Multiple simultaneous interventions work
- ✅ Serialization/deserialization preserves all data

### Performance Requirements
- ✅ Small repository (<5 nodes): <5s total
- ✅ Medium repository (5-10 nodes): <10s total
- ✅ Large repository (20 nodes): <30s total
- ✅ Intervention query: <100ms (small), <500ms (large)
- ✅ 1000-trace fitting: <10s

### Error Handling Requirements
- ✅ Syntax errors caught with helpful messages
- ✅ Cyclic dependencies detected and reported
- ✅ Invalid interventions validated before execution
- ✅ Insufficient data raises clear errors
- ✅ Mismatched traces raise clear errors

### Quality Requirements
- ✅ Linear relationships: R² ≥ 0.95
- ✅ Nonlinear relationships: R² ≥ 0.7
- ✅ Cross-validation: Test R² within 10% of train R²
- ✅ Interventions: Results within 10% of expected for deterministic cases

---

## Test Implementation Notes

### Fixtures
All test repositories defined in: `tests/causal/fixtures/test_repositories.py`

### Test Files
Organized by scenario category:
- `tests/causal/e2e/test_static_mode.py` - Category 1
- `tests/causal/e2e/test_dynamic_mode.py` - Category 2
- `tests/causal/e2e/test_interventions.py` - Category 3
- `tests/causal/e2e/test_performance.py` - Category 4
- `tests/causal/e2e/test_error_cases.py` - Category 5
- `tests/causal/e2e/test_integration.py` - Category 6
- `tests/causal/e2e/test_validation.py` - Category 7

### Helpers
- `tests/causal/e2e/helpers.py` - Assertion helpers, timing utilities
- `tests/causal/conftest.py` - Shared pytest fixtures

---

## Next Steps

1. **Implement test files** for each category (7 files)
2. **Run Phase 1** tests to validate basic functionality
3. **Iterate** through phases 2-6
4. **Document results** in `E2E_TEST_RESULTS.md`
5. **Fix bugs** discovered during testing
6. **Achieve 100% pass rate** across all scenarios
