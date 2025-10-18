# Conjecturing Framework: Technical Specification
## Detailed Implementation Guide for lift-sys

**Version**: 1.0
**Status**: Specification
**Based on**: arXiv:2510.11986 - "Conjecturing: An Overlooked Step in Formal Mathematical Reasoning"
**Epic**: lift-sys-230 (Conjecturing Framework Implementation)
**Related**: lift-sys-229 (3 Failure Investigation)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Phase 1: Diagnostic Enhancement](#phase-1-diagnostic-enhancement)
4. [Phase 2: Two-Phase IR Generation](#phase-2-two-phase-ir-generation)
5. [Phase 3: CSP Integration](#phase-3-csp-integration)
6. [Testing Strategy](#testing-strategy)
7. [Metrics & Monitoring](#metrics--monitoring)
8. [Migration & Rollout](#migration--rollout)

---

## Overview

### Problem Statement

Current lift-sys architecture bundles IR generation (conjecturing) with code generation (formalisation), making it impossible to diagnose where failures occur:

```
Current: Prompt → [Black Box: IR + Holes + Code] → Success/Failure (83.3%)
                         ↑
                  Can't see inside
```

**Result**: Phase 7 constraints had zero impact because we can't tell if:
- Constraints are incomplete (conjecturing problem)
- Code doesn't honor constraints (formalisation problem)
- Both

### Solution Approach

Adopt conjecturing framework from arXiv:2510.11986 to separate concerns:

```
Proposed: Prompt → [Phase 1: IR Skeleton]
                        ↓
                   [Phase 2: Constraint Detection]
                        ↓
                   [Phase 3: Conjecture Generation (Fill Holes)]
                        ↓ (Measure: Conjecture Quality)
                   [Phase 4: Validate Conjectures]
                        ↓
                   [Phase 5: Code Generation]
                        ↓ (Measure: Constraint Preservation)
                   Success/Failure (Target: 95%+)
```

### Key Benefits

1. **Diagnostic clarity**: Separate metrics for IR vs code quality
2. **Targeted improvements**: Fix actual bottleneck, not guess
3. **Theoretical grounding**: Based on peer-reviewed research
4. **Incremental adoption**: Can stop at any phase if not beneficial

### Success Criteria

| Phase | Criteria | Target |
|-------|----------|--------|
| 1 | Bottleneck identified | Clear data-driven answer |
| 1 | Constraint completeness measured | >80% for passing tests |
| 1 | Preservation rate measured | Baseline established |
| 2 | IR conjecture accuracy | >90% |
| 2 | E2E success improvement | +5% (83.3% → 88%+) |
| 3 | E2E success rate | >95% |
| 3 | Complex dependencies supported | Yes |

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Conjecturing Framework                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Phase 1: Skeleton Generator                        │   │
│  │  - Input: Natural language prompt                   │   │
│  │  - Output: IR with explicit typed holes             │   │
│  │  - Example: name="<?hole_1: function_name?>"        │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Phase 2: Constraint Detector (EXISTING)            │   │
│  │  - Input: Prompt + IR Skeleton                      │   │
│  │  - Output: List[Constraint]                         │   │
│  │  - Uses: Phase 7 constraint_detector.py             │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Phase 3: Conjecture Generator (NEW)                │   │
│  │  - Input: Skeleton + Constraints                    │   │
│  │  - Output: Complete IR (holes filled)               │   │
│  │  - Method: Constraint-guided LLM generation         │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Phase 4: Conjecture Validator (NEW)                │   │
│  │  - Input: Complete IR + Constraints                 │   │
│  │  - Output: Validation result + violations           │   │
│  │  - Method: IR-level constraint checking             │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Phase 5: Code Generator (EXISTING)                 │   │
│  │  - Input: Complete IR                               │   │
│  │  - Output: Executable code                          │   │
│  │  - Uses: XGrammarCodeGenerator                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  Metrics Layer   │
                    ├──────────────────┤
                    │ - Conjecture Acc │
                    │ - Constraint Comp│
                    │ - Preservation   │
                    │ - E2E Success    │
                    └──────────────────┘
```

### File Structure

```
lift_sys/
├── conjecturing/                          # NEW: Conjecturing framework
│   ├── __init__.py
│   ├── skeleton_generator.py             # Phase 1: Skeleton generation
│   ├── conjecture_generator.py           # Phase 3: Hole resolution
│   ├── conjecture_validator.py           # Phase 4: IR validation
│   ├── metrics.py                        # Conjecturing metrics
│   └── translator.py                     # Main ConjecturingIRTranslator
│
├── ir/
│   ├── constraint_detector.py            # Phase 2: EXISTING (Phase 7)
│   ├── constraint_validator.py           # EXISTING (Phase 7)
│   └── models.py                         # EXISTING (TypedHole already there)
│
├── codegen/
│   └── xgrammar_generator.py             # Phase 5: EXISTING
│
└── forward_mode/
    ├── xgrammar_translator.py            # EXISTING (baseline)
    └── conjecturing_translator.py        # NEW: Conjecturing-based translator

tests/
├── conjecturing/                          # NEW: Conjecturing tests
│   ├── test_skeleton_generator.py
│   ├── test_conjecture_generator.py
│   ├── test_conjecture_validator.py
│   ├── test_metrics.py
│   └── test_integration.py
│
└── integration/
    └── test_conjecturing_e2e.py          # E2E tests

debug/
├── collect_failure_samples.py            # MODIFIED: Add conjecture metrics
├── analyze_conjecturing_bottleneck.py    # NEW: Bottleneck analysis
└── test_conjecturing_on_3_failures.py    # NEW: Test on known failures

docs/
├── CONJECTURING_RESEARCH_REPORT.md       # EXISTING: Research analysis
├── CONJECTURING_IMPLEMENTATION_PLAN.md   # EXISTING: High-level plan
├── CONJECTURING_TECHNICAL_SPEC.md        # THIS FILE
└── CONJECTURING_USER_GUIDE.md            # NEW: User documentation
```

---

## Phase 1: Diagnostic Enhancement

**Duration**: 1 week (8-12 hours)
**Beads**: lift-sys-231
**Risk**: Low
**Dependencies**: None

### 1.1 Objectives

1. Measure IR conjecture quality independently of code quality
2. Identify bottleneck: conjecturing (IR) vs formalisation (code)
3. Provide data-driven recommendation for Phase 2

### 1.2 Metrics to Add

#### Metric 1: Constraint Completeness

**Definition**: Percentage of expected constraints detected in IR

**Formula**:
```python
constraint_completeness = (
    len(detected_constraints ∩ expected_constraints) /
    len(expected_constraints)
)
```

**Expected values**:
```python
EXPECTED_CONSTRAINTS = {
    "count_words": [
        ReturnConstraint(value_name="count")
    ],
    "find_index": [
        LoopBehaviorConstraint(
            search_type=LoopSearchType.FIRST_MATCH,
            requirement=LoopRequirement.EARLY_RETURN
        )
    ],
    "is_valid_email": [
        PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.NOT_ADJACENT
        )
    ]
}
```

#### Metric 2: Constraint Preservation

**Definition**: Percentage of IR constraints honored in generated code

**Formula**:
```python
preservation_rate = 1.0 - (
    len(violations) / max(len(constraints), 1)
)
```

**Measurement**: Use existing `ConstraintValidator` on generated code

#### Metric 3: IR Semantic Correctness

**Definition**: Manual evaluation of IR quality (subjective)

**Checklist**:
- [ ] Function name semantically appropriate?
- [ ] Parameter types match intent?
- [ ] Return type correct?
- [ ] Effects accurately describe behavior?
- [ ] Constraints capture requirements?

### 1.3 Implementation Details

#### File: `debug/collect_failure_samples.py` (MODIFIED)

**Add functions**:

```python
from lift_sys.ir.constraints import (
    ReturnConstraint,
    LoopBehaviorConstraint,
    PositionConstraint,
    LoopSearchType,
    LoopRequirement,
    PositionRequirement
)
from lift_sys.ir.constraint_validator import ConstraintValidator

# Ground truth for known tests
EXPECTED_CONSTRAINTS: dict[str, list] = {
    "count_words": [
        {"type": "RETURN", "value_name": "count"}
    ],
    "find_index": [
        {
            "type": "LOOP_BEHAVIOR",
            "search_type": "FIRST_MATCH",
            "requirement": "EARLY_RETURN"
        }
    ],
    "is_valid_email": [
        {
            "type": "POSITION",
            "elements": ["@", "."],
            "requirement": "NOT_ADJACENT"
        }
    ]
}

def evaluate_conjecture_quality(
    ir: IntermediateRepresentation,
    test_name: str
) -> dict:
    """
    Evaluate IR as conjecture (independent of code).

    Returns:
        {
            "constraint_completeness": float,  # 0.0-1.0
            "detected_constraints": list[str],
            "expected_constraints": list[str],
            "missing_constraints": list[str],
            "ir_summary": dict
        }
    """
    expected = EXPECTED_CONSTRAINTS.get(test_name, [])
    detected = [
        {
            "type": c.type.value,
            **{k: v for k, v in c.__dict__.items() if k != "type"}
        }
        for c in ir.constraints
    ]

    # Calculate completeness
    detected_types = {c["type"] for c in detected}
    expected_types = {c["type"] for c in expected}

    if not expected_types:
        completeness = 1.0
    else:
        completeness = len(detected_types & expected_types) / len(expected_types)

    return {
        "constraint_completeness": completeness,
        "detected_constraints": detected,
        "expected_constraints": expected,
        "missing_constraints": list(expected_types - detected_types),
        "ir_summary": {
            "function_name": ir.signature.name,
            "return_type": ir.signature.returns,
            "parameter_count": len(ir.signature.parameters),
            "effect_count": len(ir.effects)
        }
    }

def evaluate_constraint_preservation(
    code: str,
    ir: IntermediateRepresentation
) -> dict:
    """
    Measure how well generated code honors IR constraints.

    Returns:
        {
            "preservation_rate": float,  # 0.0-1.0
            "total_constraints": int,
            "violations": list[dict],
            "honored_constraints": list[str]
        }
    """
    validator = ConstraintValidator()
    violations = validator.validate_code(code, ir.constraints)

    total = len(ir.constraints)
    violation_count = len(violations)

    preservation_rate = 1.0 - (violation_count / max(total, 1))

    return {
        "preservation_rate": preservation_rate,
        "total_constraints": total,
        "violations": [
            {
                "constraint_type": v.constraint.type.value,
                "message": v.message,
                "severity": v.severity.value
            }
            for v in violations
        ],
        "honored_constraints": [
            c.type.value
            for c in ir.constraints
            if not any(v.constraint == c for v in violations)
        ]
    }

async def collect_conjecturing_samples(
    test_name: str,
    prompt: str,
    num_samples: int = 12,
    temperature: float = 0.8
) -> dict:
    """
    Collect samples with conjecturing metrics.

    Returns comprehensive diagnostic data for bottleneck analysis.
    """
    translator = XGrammarIRTranslator(provider)
    generator = XGrammarCodeGenerator(provider)

    samples = []

    for i in range(num_samples):
        # Generate IR
        ir = await translator.translate(prompt, temperature=temperature)

        # Evaluate conjecture quality
        conjecture_eval = evaluate_conjecture_quality(ir, test_name)

        # Generate code
        result = await generator.generate(ir)
        code = result.code

        # Evaluate constraint preservation
        preservation_eval = evaluate_constraint_preservation(code, ir)

        # Test execution
        test_result = run_test(test_name, code)

        samples.append({
            "sample_id": i + 1,
            "conjecture_quality": conjecture_eval,
            "constraint_preservation": preservation_eval,
            "test_passed": test_result["passed"],
            "ir": ir.to_dict(),
            "code": code
        })

    # Aggregate statistics
    avg_completeness = np.mean([
        s["conjecture_quality"]["constraint_completeness"]
        for s in samples
    ])
    avg_preservation = np.mean([
        s["constraint_preservation"]["preservation_rate"]
        for s in samples
    ])
    test_pass_rate = sum(s["test_passed"] for s in samples) / len(samples)

    return {
        "test_name": test_name,
        "num_samples": num_samples,
        "temperature": temperature,
        "samples": samples,
        "summary": {
            "avg_constraint_completeness": avg_completeness,
            "avg_constraint_preservation": avg_preservation,
            "test_pass_rate": test_pass_rate,
            "bottleneck_analysis": analyze_bottleneck(
                avg_completeness, avg_preservation, test_pass_rate
            )
        }
    }

def analyze_bottleneck(
    completeness: float,
    preservation: float,
    pass_rate: float
) -> dict:
    """
    Analyze where bottleneck is based on metrics.

    Decision logic:
    - High completeness (>80%) + Low preservation (<50%) → Codegen bottleneck
    - Low completeness (<50%) + High preservation (>80%) → Conjecturing bottleneck
    - Both low → Systemic issues
    - Both high but low pass rate → Test execution issues
    """
    if completeness > 0.8 and preservation < 0.5:
        bottleneck = "FORMALISATION"
        recommendation = "Focus on semantic validation or LLM-based repair (Options 2 or 4)"
        confidence = "HIGH"
    elif completeness < 0.5 and preservation > 0.8:
        bottleneck = "CONJECTURING"
        recommendation = "Implement two-phase IR generation (Phase 2)"
        confidence = "HIGH"
    elif completeness < 0.5 and preservation < 0.5:
        bottleneck = "SYSTEMIC"
        recommendation = "Consider full conjecturing framework (Phase 3)"
        confidence = "MEDIUM"
    elif completeness > 0.8 and preservation > 0.8 and pass_rate < 0.5:
        bottleneck = "EXECUTION"
        recommendation = "Investigate test framework or runtime issues"
        confidence = "MEDIUM"
    else:
        bottleneck = "UNCLEAR"
        recommendation = "Collect more samples or investigate edge cases"
        confidence = "LOW"

    return {
        "bottleneck": bottleneck,
        "recommendation": recommendation,
        "confidence": confidence,
        "metrics": {
            "constraint_completeness": completeness,
            "constraint_preservation": preservation,
            "test_pass_rate": pass_rate
        }
    }
```

#### File: `debug/analyze_conjecturing_bottleneck.py` (NEW)

```python
"""
Analyze conjecturing bottleneck from collected samples.

Usage:
    python debug/analyze_conjecturing_bottleneck.py \
        --input logs/conjecturing_diagnostics/ \
        --output DIAGNOSTIC_REPORT_CONJECTURING.md
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List
import numpy as np

def load_samples(input_dir: Path) -> Dict[str, dict]:
    """Load all collected samples."""
    samples = {}
    for file in input_dir.glob("*.json"):
        test_name = file.stem.replace("_samples", "")
        with open(file) as f:
            samples[test_name] = json.load(f)
    return samples

def generate_report(samples: Dict[str, dict], output_path: Path):
    """Generate diagnostic report."""
    with open(output_path, "w") as f:
        f.write("# Diagnostic Report: Conjecturing vs Formalisation Analysis\n\n")
        f.write("**Based on**: arXiv:2510.11986 conjecturing framework\n")
        f.write("**Date**: {}\n\n".format(datetime.now().strftime("%Y-%m-%d")))

        f.write("## Executive Summary\n\n")

        # Overall metrics
        all_completeness = []
        all_preservation = []
        all_pass_rates = []

        for test_name, data in samples.items():
            summary = data["summary"]
            all_completeness.append(summary["avg_constraint_completeness"])
            all_preservation.append(summary["avg_constraint_preservation"])
            all_pass_rates.append(summary["test_pass_rate"])

        avg_completeness = np.mean(all_completeness)
        avg_preservation = np.mean(all_preservation)
        avg_pass_rate = np.mean(all_pass_rates)

        f.write(f"**Average Constraint Completeness**: {avg_completeness:.1%}\n")
        f.write(f"**Average Constraint Preservation**: {avg_preservation:.1%}\n")
        f.write(f"**Average Test Pass Rate**: {avg_pass_rate:.1%}\n\n")

        # Bottleneck identification
        bottleneck_analysis = analyze_bottleneck(
            avg_completeness, avg_preservation, avg_pass_rate
        )

        f.write("## Bottleneck Identification\n\n")
        f.write(f"**Bottleneck**: {bottleneck_analysis['bottleneck']}\n")
        f.write(f"**Confidence**: {bottleneck_analysis['confidence']}\n")
        f.write(f"**Recommendation**: {bottleneck_analysis['recommendation']}\n\n")

        # Per-test analysis
        f.write("## Per-Test Analysis\n\n")

        for test_name, data in samples.items():
            f.write(f"### {test_name}\n\n")
            summary = data["summary"]

            f.write(f"- **Samples**: {data['num_samples']}\n")
            f.write(f"- **Constraint Completeness**: {summary['avg_constraint_completeness']:.1%}\n")
            f.write(f"- **Constraint Preservation**: {summary['avg_constraint_preservation']:.1%}\n")
            f.write(f"- **Test Pass Rate**: {summary['test_pass_rate']:.1%}\n")
            f.write(f"- **Bottleneck**: {summary['bottleneck_analysis']['bottleneck']}\n\n")

            # Sample details
            f.write("**Sample Breakdown**:\n\n")
            for sample in data["samples"][:3]:  # Show first 3
                f.write(f"- Sample {sample['sample_id']}:\n")
                f.write(f"  - Completeness: {sample['conjecture_quality']['constraint_completeness']:.1%}\n")
                f.write(f"  - Preservation: {sample['constraint_preservation']['preservation_rate']:.1%}\n")
                f.write(f"  - Test Passed: {sample['test_passed']}\n")
            f.write("\n")

        # Recommendations
        f.write("## Recommendations\n\n")

        if bottleneck_analysis["bottleneck"] == "CONJECTURING":
            f.write("### Proceed to Phase 2: Two-Phase IR Generation\n\n")
            f.write("IR constraint detection is incomplete. Implementing separated\n")
            f.write("conjecture generation should improve constraint completeness\n")
            f.write("and overall success rate.\n\n")
        elif bottleneck_analysis["bottleneck"] == "FORMALISATION":
            f.write("### Pivot to Semantic Validation\n\n")
            f.write("IR quality is good but code generation doesn't honor constraints.\n")
            f.write("Focus on:\n")
            f.write("- Semantic validation (Option 2)\n")
            f.write("- LLM-based repair (Option 4)\n")
            f.write("- Improved codegen prompts\n\n")
        else:
            f.write("### Consider Full Framework or Investigate Further\n\n")
            f.write("Results are mixed. Consider:\n")
            f.write("- Collecting more samples\n")
            f.write("- Investigating specific failure modes\n")
            f.write("- Testing on additional test cases\n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    samples = load_samples(args.input)
    generate_report(samples, args.output)
    print(f"Report generated: {args.output}")
```

### 1.4 Execution Plan

```bash
# Step 1: Collect samples for 3 failing tests
mkdir -p logs/conjecturing_diagnostics

python debug/collect_failure_samples.py \
    --test count_words \
    --samples 12 \
    --temperature 0.8 \
    --output logs/conjecturing_diagnostics/count_words_samples.json

python debug/collect_failure_samples.py \
    --test find_index \
    --samples 12 \
    --temperature 0.8 \
    --output logs/conjecturing_diagnostics/find_index_samples.json

python debug/collect_failure_samples.py \
    --test is_valid_email \
    --samples 12 \
    --temperature 0.8 \
    --output logs/conjecturing_diagnostics/is_valid_email_samples.json

# Step 2: Analyze bottleneck
python debug/analyze_conjecturing_bottleneck.py \
    --input logs/conjecturing_diagnostics/ \
    --output DIAGNOSTIC_REPORT_CONJECTURING.md

# Step 3: Review report and make decision
cat DIAGNOSTIC_REPORT_CONJECTURING.md
```

### 1.5 Deliverables

- [ ] Modified `debug/collect_failure_samples.py` with conjecture metrics
- [ ] New `debug/analyze_conjecturing_bottleneck.py` analysis script
- [ ] `DIAGNOSTIC_REPORT_CONJECTURING.md` with bottleneck identification
- [ ] Decision on whether to proceed to Phase 2

### 1.6 Acceptance Criteria

- [ ] 36 samples collected (12 per test)
- [ ] Constraint completeness measured for all samples
- [ ] Constraint preservation measured for all samples
- [ ] Bottleneck identified with confidence level
- [ ] Clear recommendation provided (Phase 2, pivot, or investigate further)

---

## Phase 2: Two-Phase IR Generation

**Duration**: 2-3 weeks (40-60 hours)
**Beads**: lift-sys-232
**Risk**: Medium
**Dependencies**: Phase 1 complete, bottleneck = CONJECTURING

### 2.1 Objectives

1. Implement skeleton-based IR generation with explicit typed holes
2. Create constraint-guided conjecture generator
3. Validate conjectures before code generation
4. Achieve >90% IR conjecture accuracy
5. Improve E2E success rate by >5%

### 2.2 Component Specifications

#### Component 1: Skeleton Generator

**File**: `lift_sys/conjecturing/skeleton_generator.py`

**Responsibilities**:
- Generate IR with explicit typed holes
- Preserve ambiguity rather than guessing
- Provide hole descriptions and constraints

**Interface**:
```python
class SkeletonGenerator:
    """Generate IR skeletons with explicit typed holes."""

    async def generate(
        self,
        prompt: str,
        language: str = "python"
    ) -> IntermediateRepresentation:
        """
        Generate IR skeleton from prompt.

        Returns:
            IR with typed holes for ambiguous values:
            - Function names (if not specified)
            - Parameter types (if unclear)
            - Return types (if not explicit)
            - Implementation patterns (if multiple valid)
        """
```

**Prompt Template**:
```python
SKELETON_PROMPT_TEMPLATE = """
Generate an Intermediate Representation (IR) skeleton for this prompt.
Use typed holes (<?hole_id: type?>) for any ambiguous or unspecified values.

Prompt: {prompt}

Create typed holes for:
1. Function name - if not explicitly stated
2. Parameter types - if not clear from context
3. Return type - if not specified
4. Loop patterns - if multiple approaches valid (early return vs accumulation)
5. Validation logic - if implementation details unclear

Example typed holes:
- Function name: "<?hole_function_name: str?>"
- Parameter type: "<?hole_param_type: str?>"
- Return type: "<?hole_return_type: str?>"
- Loop pattern: "<?hole_loop_pattern: str?>" (values: "early_return", "accumulate", "iterate_all")

Return IR in JSON format following IntermediateRepresentation schema.
Preserve ALL ambiguity - don't guess.
"""
```

**Implementation sketch**:
```python
from lift_sys.providers.base import BaseProvider
from lift_sys.ir.models import IntermediateRepresentation, TypedHole, HoleKind

class SkeletonGenerator:
    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def generate(
        self,
        prompt: str,
        language: str = "python"
    ) -> IntermediateRepresentation:
        # Build skeleton generation prompt
        full_prompt = SKELETON_PROMPT_TEMPLATE.format(prompt=prompt)

        # Generate IR with holes
        response = await self.provider.generate_structured(
            prompt=full_prompt,
            schema=IR_SCHEMA,
            temperature=0.3  # Low temp for skeleton
        )

        # Parse response to IR
        ir = IntermediateRepresentation.from_dict(response)

        # Validate holes are present for ambiguous values
        self._ensure_necessary_holes(ir, prompt)

        return ir

    def _ensure_necessary_holes(
        self,
        ir: IntermediateRepresentation,
        prompt: str
    ):
        """Ensure necessary holes are present based on prompt analysis."""
        # Check if function name is specified
        if not self._function_name_in_prompt(prompt):
            if not any(h.identifier == "hole_function_name" for h in ir.typed_holes()):
                # Add hole for function name
                ir.signature.holes.append(
                    TypedHole(
                        identifier="hole_function_name",
                        type_hint="str",
                        description="Function name not specified in prompt",
                        kind=HoleKind.SIGNATURE
                    )
                )

        # Similar checks for parameters, return type, etc.
```

#### Component 2: Conjecture Generator

**File**: `lift_sys/conjecturing/conjecture_generator.py`

**Responsibilities**:
- Generate candidates for each typed hole
- Filter candidates by constraints
- Select best candidate for each hole

**Interface**:
```python
class ConjectureGenerator:
    """Generate conjectures for typed holes."""

    async def generate_conjectures(
        self,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> dict[str, Any]:
        """
        Generate conjectures for all typed holes.

        Args:
            skeleton: IR with typed holes
            constraints: Detected constraints

        Returns:
            Dictionary mapping hole_id → conjecture value
        """
```

**Implementation**:
```python
class ConjectureGenerator:
    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def generate_conjectures(
        self,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> dict[str, Any]:
        """Generate conjectures for all holes."""
        conjectures = {}

        holes = skeleton.typed_holes()

        # Process holes in dependency order
        # (holes without dependencies first)
        ordered_holes = self._topological_sort(holes, constraints)

        for hole in ordered_holes:
            # Generate conjecture for this hole
            conjecture = await self._generate_single_conjecture(
                hole, skeleton, constraints, conjectures
            )
            conjectures[hole.identifier] = conjecture

        return conjectures

    async def _generate_single_conjecture(
        self,
        hole: TypedHole,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint],
        previous_conjectures: dict[str, Any]
    ) -> Any:
        """Generate conjecture for single hole."""
        # Build context
        context = self._build_conjecture_prompt(
            hole, skeleton, constraints, previous_conjectures
        )

        # Generate candidates
        if "domain" in hole.constraints:
            # Explicit domain provided
            candidates = hole.constraints["domain"]
        else:
            # Generate using LLM
            candidates = await self._generate_candidates(
                context, hole, num_candidates=5
            )

        # Filter by constraints
        relevant_constraints = self._get_relevant_constraints(hole, constraints)
        valid_candidates = [
            c for c in candidates
            if self._validates_constraints(c, hole, relevant_constraints)
        ]

        if not valid_candidates:
            raise ValueError(f"No valid conjecture for {hole.identifier}")

        # Select best (for now, just first valid)
        return valid_candidates[0]

    def _build_conjecture_prompt(
        self,
        hole: TypedHole,
        skeleton: IntermediateRepresentation,
        constraints: list[Constraint],
        previous_conjectures: dict[str, Any]
    ) -> str:
        """Build prompt for conjecture generation."""
        prompt_parts = [
            f"Generate value for typed hole: {hole.identifier}",
            f"Type: {hole.type_hint}",
            f"Description: {hole.description}",
            "",
            "Context:",
            f"Function intent: {skeleton.intent.summary}",
        ]

        # Add previous conjectures as context
        if previous_conjectures:
            prompt_parts.append("\nAlready resolved:")
            for hole_id, value in previous_conjectures.items():
                prompt_parts.append(f"  - {hole_id} = {value}")

        # Add constraints
        relevant = self._get_relevant_constraints(hole, constraints)
        if relevant:
            prompt_parts.append("\nConstraints:")
            for c in relevant:
                prompt_parts.append(f"  - {c.description}")

        # Add hole-specific constraints
        if hole.constraints:
            prompt_parts.append("\nHole constraints:")
            for key, value in hole.constraints.items():
                prompt_parts.append(f"  - {key}: {value}")

        return "\n".join(prompt_parts)
```

#### Component 3: Conjecture Validator

**File**: `lift_sys/conjecturing/conjecture_validator.py`

**Responsibilities**:
- Validate complete IR (after holes filled)
- Check IR-level constraints
- Return violations with explanations

**Interface**:
```python
class ConjectureValidator:
    """Validate IR conjectures against constraints."""

    def validate(
        self,
        ir: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> list[ConstraintViolation]:
        """
        Validate IR conjectures.

        Returns:
            List of violations (empty if all constraints satisfied)
        """
```

**Implementation**:
```python
from lift_sys.ir.constraints import (
    Constraint,
    ReturnConstraint,
    LoopBehaviorConstraint,
    PositionConstraint,
    ConstraintViolation
)

class ConjectureValidator:
    """Validate IR-level conjectures."""

    def validate(
        self,
        ir: IntermediateRepresentation,
        constraints: list[Constraint]
    ) -> list[ConstraintViolation]:
        """Validate all constraints in IR."""
        violations = []

        for constraint in constraints:
            if not self._check_ir_constraint(ir, constraint):
                violations.append(
                    ConstraintViolation(
                        constraint=constraint,
                        message=self._get_violation_message(ir, constraint),
                        severity=constraint.severity
                    )
                )

        return violations

    def _check_ir_constraint(
        self,
        ir: IntermediateRepresentation,
        constraint: Constraint
    ) -> bool:
        """Check single constraint in IR."""
        if isinstance(constraint, ReturnConstraint):
            return self._check_return_constraint_ir(ir, constraint)
        elif isinstance(constraint, LoopBehaviorConstraint):
            return self._check_loop_constraint_ir(ir, constraint)
        elif isinstance(constraint, PositionConstraint):
            return self._check_position_constraint_ir(ir, constraint)
        else:
            # Unknown constraint type - pass for now
            return True

    def _check_return_constraint_ir(
        self,
        ir: IntermediateRepresentation,
        constraint: ReturnConstraint
    ) -> bool:
        """Check return constraint at IR level."""
        # Verify return type is not None
        if ir.signature.returns is None or ir.signature.returns == "None":
            return False

        # Check if effects mention return
        has_return_effect = any(
            "return" in effect.description.lower()
            for effect in ir.effects
        )

        return has_return_effect

    def _check_loop_constraint_ir(
        self,
        ir: IntermediateRepresentation,
        constraint: LoopBehaviorConstraint
    ) -> bool:
        """Check loop behavior constraint at IR level."""
        # Check if effects describe loop behavior
        for effect in ir.effects:
            desc = effect.description.lower()

            # Check for FIRST_MATCH → early return pattern
            if constraint.search_type == LoopSearchType.FIRST_MATCH:
                if "first" in desc and "return" in desc:
                    return True

        # Check assertions for loop pattern
        for assertion in ir.assertions:
            if "first" in assertion.description.lower():
                return True

        return False
```

#### Component 4: Conjecturing Translator

**File**: `lift_sys/conjecturing/translator.py`

**Responsibilities**:
- Orchestrate full two-phase IR generation
- Integrate skeleton, constraints, conjectures, validation
- Provide main API

**Interface**:
```python
class ConjecturingIRTranslator:
    """Two-phase IR translator using conjecturing framework."""

    async def translate(
        self,
        prompt: str,
        language: str = "python"
    ) -> IntermediateRepresentation:
        """
        Translate prompt to IR using conjecturing approach.

        Process:
        1. Generate skeleton with typed holes
        2. Detect constraints
        3. Generate conjectures for holes
        4. Validate conjectures
        5. Return complete IR
        """
```

**Implementation**:
```python
from lift_sys.conjecturing.skeleton_generator import SkeletonGenerator
from lift_sys.conjecturing.conjecture_generator import ConjectureGenerator
from lift_sys.conjecturing.conjecture_validator import ConjectureValidator
from lift_sys.ir.constraint_detector import ConstraintDetector

class ConjecturingIRTranslator:
    """Main conjecturing-based IR translator."""

    def __init__(self, provider: BaseProvider):
        self.provider = provider
        self.skeleton_gen = SkeletonGenerator(provider)
        self.constraint_detector = ConstraintDetector()
        self.conjecture_gen = ConjectureGenerator(provider)
        self.validator = ConjectureValidator()

    async def translate(
        self,
        prompt: str,
        language: str = "python"
    ) -> IntermediateRepresentation:
        """Full two-phase translation."""
        # Phase 1: Generate skeleton
        skeleton = await self.skeleton_gen.generate(prompt, language)

        # Phase 2: Detect constraints
        constraints = self.constraint_detector.detect(skeleton, prompt)

        # Phase 3: Generate conjectures
        conjectures = await self.conjecture_gen.generate_conjectures(
            skeleton, constraints
        )

        # Phase 4: Apply conjectures to skeleton
        complete_ir = self._apply_conjectures(skeleton, conjectures)
        complete_ir.constraints = constraints

        # Phase 5: Validate
        violations = self.validator.validate(complete_ir, constraints)
        if violations:
            # Log violations but don't fail (for now)
            print(f"Warning: {len(violations)} constraint violations in IR")
            for v in violations:
                print(f"  - {v.message}")

        return complete_ir

    def _apply_conjectures(
        self,
        skeleton: IntermediateRepresentation,
        conjectures: dict[str, Any]
    ) -> IntermediateRepresentation:
        """Apply conjecture values to skeleton holes."""
        # This is complex - need to replace typed hole markers
        # with actual values throughout IR structure

        # For MVP: create new IR with filled values
        # For production: use visitor pattern to replace holes

        ir_dict = skeleton.to_dict()

        # Replace holes in JSON representation
        ir_json = json.dumps(ir_dict)

        for hole_id, value in conjectures.items():
            # Replace typed hole markers
            hole_marker = f'"<?{hole_id}: '
            if hole_marker in ir_json:
                # Extract type hint
                # Replace with actual value
                ir_json = ir_json.replace(
                    f'"<?{hole_id}: [^?]*?>"',  # Regex
                    f'"{value}"'
                )

        # Parse back to IR
        filled_dict = json.loads(ir_json)
        complete_ir = IntermediateRepresentation.from_dict(filled_dict)

        # Clear holes list (all filled)
        complete_ir.intent.holes = []
        complete_ir.signature.holes = []
        for effect in complete_ir.effects:
            effect.holes = []
        for assertion in complete_ir.assertions:
            assertion.holes = []

        return complete_ir
```

### 2.3 Testing Strategy

#### Unit Tests

**File**: `tests/conjecturing/test_skeleton_generator.py`
```python
@pytest.mark.asyncio
async def test_skeleton_generation_creates_holes():
    """Skeleton should create typed holes for ambiguous values."""
    prompt = "Process data and return result"  # Vague

    skeleton = await skeleton_gen.generate(prompt)

    # Should have holes for function name, types, etc.
    assert len(skeleton.typed_holes()) > 0
    assert any(h.identifier == "hole_function_name" for h in skeleton.typed_holes())

@pytest.mark.asyncio
async def test_skeleton_no_holes_when_explicit():
    """Skeleton should not create holes when prompt is explicit."""
    prompt = "Create function named 'validate_email' that takes email: str and returns bool"

    skeleton = await skeleton_gen.generate(prompt)

    # Should have no holes (everything specified)
    assert len(skeleton.typed_holes()) == 0
```

**File**: `tests/conjecturing/test_conjecture_generator.py`
```python
@pytest.mark.asyncio
async def test_conjecture_generation_fills_holes():
    """Conjecture generator should fill all holes."""
    skeleton = create_skeleton_with_holes()  # Fixture
    constraints = [ReturnConstraint(value_name="result")]

    conjectures = await conjecture_gen.generate_conjectures(skeleton, constraints)

    # Should have conjecture for each hole
    assert len(conjectures) == len(skeleton.typed_holes())

@pytest.mark.asyncio
async def test_conjecture_respects_constraints():
    """Conjectures should satisfy constraints."""
    skeleton = create_skeleton_with_loop_hole()
    constraints = [
        LoopBehaviorConstraint(
            search_type=LoopSearchType.FIRST_MATCH,
            requirement=LoopRequirement.EARLY_RETURN
        )
    ]

    conjectures = await conjecture_gen.generate_conjectures(skeleton, constraints)

    # Loop pattern should be "early_return", not "accumulate"
    assert conjectures["hole_loop_pattern"] == "early_return"
```

#### Integration Tests

**File**: `tests/integration/test_conjecturing_e2e.py`
```python
@pytest.mark.asyncio
async def test_e2e_conjecturing_translation():
    """Full E2E test of conjecturing translator."""
    translator = ConjecturingIRTranslator(provider)

    prompt = "Find the first index where value appears in list"

    ir = await translator.translate(prompt)

    # IR should be complete (no holes)
    assert len(ir.typed_holes()) == 0

    # Should have correct constraints
    assert any(
        isinstance(c, LoopBehaviorConstraint) and
        c.search_type == LoopSearchType.FIRST_MATCH
        for c in ir.constraints
    )

    # IR should validate
    validator = ConjectureValidator()
    violations = validator.validate(ir, ir.constraints)
    assert len(violations) == 0

@pytest.mark.asyncio
async def test_conjecturing_on_known_failures():
    """Test conjecturing on 3 known failing tests."""
    translator = ConjecturingIRTranslator(provider)

    tests = [
        ("Count the number of words in a string", "count_words"),
        ("Find the first index of value in list", "find_index"),
        ("Validate email address format", "is_valid_email")
    ]

    for prompt, test_name in tests:
        ir = await translator.translate(prompt)

        # Measure conjecture quality
        eval_result = evaluate_conjecture_quality(ir, test_name)

        # Should have high constraint completeness
        assert eval_result["constraint_completeness"] > 0.8
```

### 2.4 Benchmarking

**File**: `debug/benchmark_conjecturing.py`
```python
"""
Benchmark conjecturing translator vs baseline.

Metrics:
- IR conjecture accuracy
- E2E success rate improvement
- Latency overhead
- Cost increase
"""

async def benchmark_conjecturing():
    baseline = XGrammarIRTranslator(provider)
    conjecturing = ConjecturingIRTranslator(provider)

    test_prompts = load_test_prompts()  # 18 tests

    results = {
        "baseline": await run_benchmark(baseline, test_prompts),
        "conjecturing": await run_benchmark(conjecturing, test_prompts)
    }

    # Compare metrics
    comparison = {
        "conjecture_accuracy": {
            "baseline": "N/A (no measurement)",
            "conjecturing": results["conjecturing"]["avg_completeness"]
        },
        "e2e_success": {
            "baseline": results["baseline"]["pass_rate"],
            "conjecturing": results["conjecturing"]["pass_rate"],
            "improvement": results["conjecturing"]["pass_rate"] - results["baseline"]["pass_rate"]
        },
        "latency": {
            "baseline": results["baseline"]["avg_latency"],
            "conjecturing": results["conjecturing"]["avg_latency"],
            "overhead": (
                results["conjecturing"]["avg_latency"] /
                results["baseline"]["avg_latency"] - 1
            )
        },
        "cost": {
            "baseline": results["baseline"]["avg_cost"],
            "conjecturing": results["conjecturing"]["avg_cost"],
            "increase": (
                results["conjecturing"]["avg_cost"] /
                results["baseline"]["avg_cost"] - 1
            )
        }
    }

    return comparison
```

### 2.5 Deliverables

- [ ] `lift_sys/conjecturing/` package with all components
- [ ] >90% test coverage for new code
- [ ] Benchmark results showing improvement
- [ ] Documentation (user guide, API reference)
- [ ] Migration guide from baseline translator

### 2.6 Acceptance Criteria

- [ ] IR conjecture accuracy >90% (on test suite)
- [ ] E2E success improvement >5% (83.3% → 88%+)
- [ ] Latency overhead <20% (vs baseline)
- [ ] All existing tests still pass
- [ ] New tests cover all components (unit + integration)

---

## Phase 3: CSP Integration

**Duration**: 4-6 weeks (120-180 hours)
**Beads**: lift-sys-233
**Risk**: High
**Dependencies**: Phase 2 complete, need for sophisticated hole resolution

### 3.1 Objectives

1. Handle complex hole dependencies (cyclic, hierarchical)
2. Implement backtracking and constraint propagation
3. Support parallel hole resolution
4. Achieve >95% E2E success rate

### 3.2 Architecture

See `CONSTRAINT_PROPAGATION_TYPED_HOLES.md` for full CSP design.

**Integration with conjecturing framework**:

```python
class ConjecturingCSPTranslator(ConjecturingIRTranslator):
    """
    Extends conjecturing translator with CSP solver.

    Replaces simple conjecture generation with sophisticated
    CSP-based approach that handles complex dependencies.
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(provider)
        self.csp_builder = HoleCSPBuilder()
        self.csp_solver = ParallelHoleSolver(provider)

    async def translate(self, prompt: str, language: str = "python"):
        # Phase 1-2: Same as parent (skeleton + constraints)
        skeleton = await self.skeleton_gen.generate(prompt, language)
        constraints = self.constraint_detector.detect(skeleton, prompt)

        # Phase 3: CSP-based conjecture generation (replaces simple version)
        csp = self.csp_builder.build(skeleton, constraints)
        conjectures = await self.csp_solver.solve(csp)

        # Phase 4-5: Same as parent (apply + validate)
        complete_ir = self._apply_conjectures(skeleton, conjectures)
        complete_ir.constraints = constraints

        violations = self.validator.validate(complete_ir, constraints)
        if violations:
            raise ValueError(f"CSP solution violates constraints: {violations}")

        return complete_ir
```

### 3.3 Components

See `CONSTRAINT_PROPAGATION_IMPLEMENTATION_PLAN.md` for detailed breakdown.

**New components**:
1. `HoleCSPBuilder` - Build CSP from skeleton + constraints
2. `ParallelHoleSolver` - Solve CSP with backtracking + propagation
3. `ConstraintGraph` - Represent hole dependencies
4. `DomainGenerator` - LLM-based domain generation (GenD from GenCP paper)

### 3.4 Deliverables

- [ ] Full CSP integration with conjecturing framework
- [ ] Support for complex dependencies (cycles, hierarchies)
- [ ] Parallel hole resolution implementation
- [ ] Comprehensive benchmarks (>95% target)
- [ ] Production deployment

### 3.5 Acceptance Criteria

- [ ] E2E success rate >95%
- [ ] Handles complex dependencies (tested on synthetic examples)
- [ ] Latency <2x baseline (with parallelization)
- [ ] All 18 tests pass consistently

---

## Testing Strategy

### Unit Tests (>90% coverage)

**Per-component tests**:
- `test_skeleton_generator.py` - Skeleton generation logic
- `test_conjecture_generator.py` - Conjecture generation + filtering
- `test_conjecture_validator.py` - IR-level validation
- `test_metrics.py` - Metric calculation

### Integration Tests

**E2E scenarios**:
- Simple prompts (explicit, no holes needed)
- Ambiguous prompts (require conjecture generation)
- Constrained prompts (must satisfy constraints)
- Known failures (3 failing tests)

### Regression Tests

**Baseline comparison**:
- All 18 existing tests must still pass
- Performance must not degrade significantly
- Cost must be justified by improvement

### Benchmark Tests

**Performance metrics**:
- Latency distribution
- Cost per request
- Success rate by test type
- Constraint completeness/preservation

---

## Metrics & Monitoring

### Conjecture Metrics (NEW)

```python
class ConjecturingMetrics:
    """Metrics for conjecturing-based IR generation."""

    def track_conjecture_accuracy(
        self,
        ir: IntermediateRepresentation,
        ground_truth: dict
    ) -> float:
        """Measure semantic correctness of conjectures."""

    def track_constraint_completeness(
        self,
        detected: list[Constraint],
        expected: list[Constraint]
    ) -> float:
        """Measure constraint detection accuracy."""

    def track_constraint_preservation(
        self,
        code: str,
        constraints: list[Constraint]
    ) -> float:
        """Measure codegen fidelity to IR constraints."""
```

### Dashboard Integration

**Add to monitoring dashboard**:
- Conjecture accuracy (per test, over time)
- Constraint completeness (per test type)
- Preservation rate (per constraint type)
- Bottleneck distribution (conjecturing vs formalisation)

---

## Migration & Rollout

### Phase 1: Diagnostic (No migration)

- Add metrics to existing diagnostic tools
- No changes to production code
- 100% safe

### Phase 2: Parallel Deployment

**Week 1**: Deploy alongside existing translator
```python
# Old code (keep running)
ir = await XGrammarIRTranslator(provider).translate(prompt)

# New code (experimental)
ir_conjecturing = await ConjecturingIRTranslator(provider).translate(prompt)

# Compare results
compare_irs(ir, ir_conjecturing)
```

**Week 2**: A/B testing
- 10% traffic to conjecturing translator
- Monitor success rate, latency, cost
- Rollback if regressions

**Week 3**: Gradual rollout
- If successful: 25% → 50% → 100%
- If issues: investigate, fix, retry

### Phase 3: Full Replacement

**Only if Phase 2 shows clear benefit**:
- Replace `XGrammarIRTranslator` with `ConjecturingIRTranslator`
- Deprecate old translator
- Update documentation

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|-----------|
| Concept doesn't transfer to code | Phase 1 diagnostic validates before implementation |
| Increased latency | Parallel hole resolution, benchmark before rollout |
| Increased cost | Track cost per phase, can abort if not justified |
| Complexity | Comprehensive tests, clear logging, incremental rollout |
| Skeleton generation quality | Evaluate on known cases, refine prompts |

### Process Risks

| Risk | Mitigation |
|------|-----------|
| Scope creep | Clear phase boundaries, go/no-go criteria |
| Resource constraints | 1-week phases, can pause after any phase |
| User impact | A/B testing, gradual rollout, rollback plan |
| Documentation debt | Documentation required for each phase |

---

## Success Criteria Summary

| Phase | Go/No-Go Criteria |
|-------|-------------------|
| 1 | Bottleneck identified with high confidence |
| 2 | Conjecture accuracy >90% AND E2E improvement >5% |
| 3 | E2E success >95% AND complex dependencies supported |

**Overall success**: 95%+ E2E success rate with clear diagnostic visibility.

---

## References

- [Conjecturing Research Report](../CONJECTURING_RESEARCH_REPORT.md)
- [Conjecturing Implementation Plan](../CONJECTURING_IMPLEMENTATION_PLAN.md)
- [Constraint Propagation Design](CONSTRAINT_PROPAGATION_TYPED_HOLES.md)
- [Phase 7 Architecture](PHASE_7_ARCHITECTURE.md)
- [Strategic Assessment](../STRATEGIC_ASSESSMENT_2025-10-17.md)
- arXiv:2510.11986 - Conjecturing: An Overlooked Step in Formal Mathematical Reasoning

---

**Status**: Specification complete, ready for Phase 1 implementation
**Next**: Create Beads work items for Phase 1
