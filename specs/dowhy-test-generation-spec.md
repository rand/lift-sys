# DoWhy Test Generation - Technical Specification

**Date**: 2025-10-25
**Status**: Draft v1.0
**Phase**: Phase 2 - Full Specification
**Priority**: P2 (HIGH VALUE)
**Parent**: DOWHY_INTEGRATION_SPEC.md
**Dependencies**: dowhy-reverse-mode-spec.md (P1 must be complete)

---

## Document Purpose

This document provides the **complete technical specification** for causal test generation - using DoWhy to generate tests that target causally important code paths.

**Key Insight**: Not all code paths are equally important. Focus tests on paths with highest causal impact on outcomes.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Requirements](#2-requirements)
3. [Architecture](#3-architecture)
4. [Component Specifications](#4-component-specifications)
5. [Data Models](#5-data-models)
6. [API Design](#6-api-design)
7. [Test Plan](#7-test-plan)
8. [Acceptance Criteria](#8-acceptance-criteria)

---

## 1. Overview

### 1.1 Goal

Generate tests that **maximize causal coverage** - cover code paths with highest impact on program outcomes.

### 1.2 Problem with Current Testing

**Coverage-Driven Testing**:
- Goal: Hit all lines/branches
- Problem: Treats all paths equally
- Result: Tests for logging/printing as much as critical logic

**Example**:
```python
def process(data):
    logger.info("Processing")  # Line 1 (low causal impact)
    validated = validate(data)  # Line 2 (HIGH causal impact)
    logger.info("Validated")    # Line 3 (low causal impact)
    return compute(validated)   # Line 4 (HIGH causal impact)
```

**Traditional Coverage**: 100% requires hitting all 4 lines

**Causal Coverage**: Focus on lines 2 & 4 (80% of causal effect with 50% of effort)

### 1.3 Solution: Causal Test Generation

**Approach**:
1. Build causal graph of codebase (P1 infrastructure)
2. Compute **causal importance** for each path
3. Generate tests for high-importance paths first
4. Measure **causal coverage** (% of causal effects covered)

### 1.4 Success Metrics

**Coverage**:
- 20%+ increase in causal coverage over baseline
- 80% of high-impact paths covered

**Quality**:
- 95%+ of generated tests pass on original code
- 90%+ of generated tests detect introduced bugs

**Efficiency**:
- 50% fewer tests for same causal coverage
- < 1s per test generation

---

## 2. Requirements

### 2.1 Functional Requirements

**FR1: Causal Path Extraction**
- MUST identify all causal paths from inputs → outputs
- MUST rank paths by causal importance
- MUST support multi-function paths
- MUST handle conditional paths (if/else)

**FR2: Causal Importance Scoring**
- MUST compute total causal effect for each path
- MUST include direct + indirect effects
- MUST normalize scores (0-1 scale)
- MUST account for path frequency (if traces available)

**FR3: Test Case Generation**
- MUST generate inputs that activate target path
- MUST predict expected outputs
- MUST generate valid Python test code
- MUST use pytest format

**FR4: Test Prioritization**
- MUST rank tests by causal importance
- MUST support priority levels (HIGH/MEDIUM/LOW)
- MUST allow user to filter by priority

**FR5: Integration with Validation**
- MUST integrate with `lift_sys/validation/`
- MUST work with existing test infrastructure
- MUST support both static and dynamic modes

### 2.2 Non-Functional Requirements

**NFR1: Performance**
- Path extraction: < 2s for 100-node graph
- Importance scoring: < 1s for 200 paths
- Test generation: < 1s per test
- Total: < 5min for 1000-file codebase

**NFR2: Quality**
- Generated tests syntactically correct (100%)
- Generated tests pass on original code (95%+)
- Generated tests detect regressions (90%+)
- False positive rate < 5%

**NFR3: Usability**
- Simple API (1 function call to generate tests)
- Clear test names (describe what path they test)
- Actionable failure messages

---

## 3. Architecture

### 3.1 System Context

```
┌─────────────────────────────────────────────────────┐
│               lift-sys                              │
│                                                     │
│  ┌──────────────┐         ┌────────────────────┐   │
│  │  Reverse     │────────►│ Causal Graph (P1)  │   │
│  │  Mode        │         │ + Fitted SCM       │   │
│  └──────────────┘         └──────┬─────────────┘   │
│                                  │                  │
│                                  ▼                  │
│  ┌─────────────────────────────────────────────┐   │
│  │  Test Generation (P2)                       │   │
│  │                                             │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │ H23: CausalPathExtractor           │   │   │
│  │  │ - Extract paths                    │   │   │
│  │  │ - Score importance                 │   │   │
│  │  └──────────┬──────────────────────────┘   │   │
│  │             │                               │   │
│  │             ▼                               │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │ TestCaseGenerator                  │   │   │
│  │  │ - Find activating inputs           │   │   │
│  │  │ - Predict outputs                  │   │   │
│  │  │ - Generate pytest code             │   │   │
│  │  └──────────┬──────────────────────────┘   │   │
│  │             │                               │   │
│  │             ▼                               │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │ Generated Tests (.py files)         │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────┐                                  │
│  │ Validation   │◄──── Tests                       │
│  │              │      (manual + generated)        │
│  └──────────────┘                                  │
└─────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 H23: CausalPathExtractor

**Purpose**: Extract and rank causal paths by importance

**Type Signature**:
```python
from dataclasses import dataclass
import networkx as nx
from dowhy import gcm

@dataclass
class CausalPath:
    """Represents a causal path through code."""
    nodes: list[str]  # Ordered list of nodes
    importance: float  # 0-1 scale (1 = most important)
    direct_effect: float  # Direct causal effect
    indirect_effect: float  # Indirect effects via other paths
    frequency: float  # How often this path executes (0-1)
    priority: str  # "HIGH" | "MEDIUM" | "LOW"

class CausalPathExtractor:
    def extract_paths(
        self,
        scm: gcm.StructuralCausalModel,
        max_paths: Optional[int] = None
    ) -> list[CausalPath]:
        """Extract all causal paths from inputs to outputs.

        Args:
            scm: Fitted structural causal model (from P1)
            max_paths: Optional limit on number of paths

        Returns:
            List of CausalPath objects, sorted by importance (desc)

        Raises:
            ValueError: If SCM has no root or leaf nodes
        """
```

**Algorithm: Path Extraction**:
```
1. Identify root nodes (no incoming edges)
2. Identify leaf nodes (no outgoing edges)
3. For each (root, leaf) pair:
   a. Find all simple paths from root to leaf
   b. Create CausalPath object for each
4. Return all paths
```

**Algorithm: Importance Scoring**:
```
1. For each path P = [n1, n2, ..., nk]:
   a. Compute direct effect:
      - Intervene on n1
      - Measure change in nk
      - direct_effect = E[nk | do(n1=x)] - E[nk]

   b. Compute indirect effect:
      - For each intermediate node ni (i=2..k-1):
        - Intervene on ni
        - Measure effect on nk
        - Sum indirect effects

   c. Total effect = direct_effect + indirect_effect

   d. Normalize: importance = total_effect / max_effect

2. Assign priority:
   - importance > 0.7 → HIGH
   - 0.3 < importance ≤ 0.7 → MEDIUM
   - importance ≤ 0.3 → LOW

3. Sort by importance (descending)
```

**Optimization**:
- Cache intervention results (avoid recomputation)
- Parallelize importance scoring across paths
- Limit to top N paths (configurable, default 100)

**Constraints**:
- MUST handle graphs with 100+ nodes
- MUST complete in < 2s for 100-node graph
- MUST return at least 1 HIGH priority path (if any exist)

**Testing**:
- Unit test: Linear path (A → B → C)
- Unit test: Branching paths (A → B, A → C → D)
- Unit test: Importance scoring (verify HIGH/MEDIUM/LOW)
- Performance test: 100 nodes, 200 paths in < 2s

---

### 4.2 TestCaseGenerator

**Purpose**: Generate pytest test cases for causal paths

**Type Signature**:
```python
from typing import Any

@dataclass
class TestCase:
    """Generated test case."""
    name: str  # e.g., "test_validate_positive_input"
    code: str  # Full pytest test function
    path: CausalPath  # Path this tests
    inputs: dict[str, Any]  # Input values
    expected_output: Any  # Expected result
    priority: str  # Inherited from path

class TestCaseGenerator:
    def generate(
        self,
        path: CausalPath,
        scm: gcm.StructuralCausalModel,
        function_signature: Optional[Signature] = None
    ) -> TestCase:
        """Generate test case for causal path.

        Args:
            path: Causal path to test
            scm: Fitted SCM
            function_signature: Optional function signature from IR

        Returns:
            Generated TestCase

        Raises:
            GenerationError: If cannot generate valid test
        """
```

**Algorithm: Find Activating Inputs**:
```
1. Start at root node of path
2. For each conditional node in path:
   a. Determine condition to activate this branch
   b. Generate input satisfying condition
3. Use constraint solver if needed (e.g., z3)
4. Fallback: Random sampling (verify path activation)
```

**Algorithm: Predict Output**:
```
1. Run SCM forward simulation:
   - Set root nodes to input values
   - Propagate through causal mechanisms
   - Get value at leaf node
2. Return predicted output
```

**Algorithm: Generate Test Code**:
```python
def generate_test_code(
    test_name: str,
    function_name: str,
    inputs: dict,
    expected: Any
) -> str:
    """Generate pytest test function."""
    return f'''
def {test_name}():
    """Test {function_name} via causal path."""
    # Inputs
    {format_inputs(inputs)}

    # Execute
    result = {function_name}({format_args(inputs)})

    # Assert
    assert result == {expected}, \\
        f"Expected {{expected}}, got {{result}}"
'''
```

**Constraints**:
- MUST generate syntactically valid Python
- MUST use pytest conventions
- SHOULD include descriptive docstrings
- MAY use pytest fixtures (if available)

**Testing**:
- Unit test: Simple path (linear)
- Unit test: Conditional path (if/else)
- Unit test: Generated code syntax (ast.parse)
- Integration test: Generated test runs and passes

---

## 5. Data Models

### 5.1 Generated Test Suite

```python
@dataclass
class TestSuite:
    """Collection of generated tests."""
    tests: list[TestCase]
    total_causal_coverage: float  # 0-1
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    generation_time: float  # seconds

    def write_to_file(self, path: Path):
        """Write tests to .py file."""
        with open(path, 'w') as f:
            f.write("import pytest\\n\\n")
            for test in self.tests:
                f.write(test.code)
                f.write("\\n\\n")

    def get_priority_tests(self, priority: str) -> list[TestCase]:
        """Get tests by priority."""
        return [t for t in self.tests if t.priority == priority]
```

---

## 6. API Design

### 6.1 High-Level API

```python
from lift_sys.causal import CausalTestGenerator

# Generate tests from IR
generator = CausalTestGenerator()

# Option 1: Generate all tests
tests = generator.generate_from_ir(
    ir,
    priority_threshold="MEDIUM",  # Only HIGH and MEDIUM
    max_tests=50
)

# Option 2: Generate for specific function
tests = generator.generate_for_function(
    ir,
    function_name="process_data",
    max_tests=10
)

# Write to file
tests.write_to_file("tests/generated/test_causal.py")

# Stats
print(f"Generated {len(tests.tests)} tests")
print(f"Causal coverage: {tests.total_causal_coverage:.1%}")
print(f"HIGH priority: {tests.high_priority_count}")
```

### 6.2 Integration with lift-sys CLI

```bash
# Generate causal tests
lift reverse --causal-tests \
    --repo https://github.com/user/repo \
    --output tests/generated/ \
    --priority HIGH

# Output:
# Analyzing codebase...
# Found 127 causal paths
# Generated 42 tests (HIGH priority only)
# Causal coverage: 78.3%
# Tests written to tests/generated/test_causal.py
```

---

## 7. Test Plan

### 7.1 Unit Tests

**H23: CausalPathExtractor** (`tests/causal/test_path_extractor.py`):
- [ ] test_extract_linear_paths()
- [ ] test_extract_branching_paths()
- [ ] test_importance_scoring()
- [ ] test_priority_assignment()
- [ ] test_max_paths_limit()
- [ ] test_performance_100_nodes()

**TestCaseGenerator** (`tests/causal/test_generator.py`):
- [ ] test_find_activating_inputs()
- [ ] test_predict_output()
- [ ] test_generate_code_syntax()
- [ ] test_pytest_format()
- [ ] test_conditional_paths()

### 7.2 Integration Tests

**End-to-End** (`tests/integration/test_causal_tests.py`):
- [ ] test_generate_from_ir()
- [ ] test_generated_tests_pass()
- [ ] test_generated_tests_detect_bugs()
- [ ] test_causal_coverage_metric()

### 7.3 Validation Tests

**Accuracy** (`tests/validation/test_test_quality.py`):
- [ ] test_syntactically_valid() - 100% valid syntax
- [ ] test_pass_on_original() - 95%+ pass rate
- [ ] test_detect_regressions() - 90%+ detection rate

---

## 8. Acceptance Criteria

### 8.1 Functional

- [ ] **F1**: Extracts causal paths from SCM
- [ ] **F2**: Scores path importance correctly
- [ ] **F3**: Generates syntactically valid tests (100%)
- [ ] **F4**: Generated tests use pytest format
- [ ] **F5**: Causal coverage metric implemented
- [ ] **F6**: Priority filtering works (HIGH/MEDIUM/LOW)

### 8.2 Performance

- [ ] **P1**: Path extraction < 2s for 100 nodes
- [ ] **P2**: Test generation < 1s per test
- [ ] **P3**: Full pipeline < 5min for 1000-file codebase

### 8.3 Quality

- [ ] **Q1**: 95%+ generated tests pass on original code
- [ ] **Q2**: 90%+ generated tests detect introduced bugs
- [ ] **Q3**: 20%+ improvement in causal coverage vs baseline
- [ ] **Q4**: 90%+ test coverage of test generator itself

### 8.4 User Experience

- [ ] **UX1**: Simple API (1 function call)
- [ ] **UX2**: Clear test names
- [ ] **UX3**: Actionable failure messages
- [ ] **UX4**: User satisfaction > 8/10

---

## 9. Timeline & Milestones

**Week 5**: H23 (CausalPathExtractor)
- [ ] Day 1-2: Path extraction algorithm
- [ ] Day 3: Importance scoring
- [ ] Day 4: Unit tests
- [ ] Day 5: Performance optimization

**Week 6**: TestCaseGenerator
- [ ] Day 1-2: Input generation
- [ ] Day 2-3: Test code generation
- [ ] Day 4: pytest format compliance
- [ ] Day 5: Unit tests

**Week 7**: Integration & Validation
- [ ] Day 1: Integration with validation pipeline
- [ ] Day 2: CLI integration
- [ ] Day 3: Real codebase testing
- [ ] Day 4: Documentation + examples
- [ ] Day 5: Code review + polish

**Total: 3 weeks (15 days)**

---

**Specification Status**: DRAFT v1.0
**Dependencies**: P1 (Reverse Mode) must be complete
**Approval Required**: YES (stakeholder sign-off)
