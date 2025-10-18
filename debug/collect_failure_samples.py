"""
Systematic collection of code samples for the 3 persistent failures.

Generates 10+ variations of each failing test to analyze:
1. AST structure patterns
2. Constraint detection effectiveness
3. Validation results
4. AST repair pattern matching

Run with: uv run python debug/collect_failure_samples.py
"""

import ast
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.ast_repair import ASTRepairEngine
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.ir.constraint_detector import ConstraintDetector
from lift_sys.ir.constraint_validator import ConstraintValidator
from lift_sys.ir.constraints import (
    ConstraintType,
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
)
from lift_sys.providers.modal_provider import ModalProvider

# Ground truth constraints for each test (for diagnostic evaluation)
GROUND_TRUTH_CONSTRAINTS = {
    "count_words": [
        {
            "type": ConstraintType.RETURN,
            "must_return": True,
            "value_name": "count",
        }
    ],
    "find_index": [
        {
            "type": ConstraintType.LOOP_BEHAVIOR,
            "search_type": LoopSearchType.FIRST_MATCH,
            "requirement": LoopRequirement.EARLY_RETURN,
        }
    ],
    "is_valid_email": [
        {
            "type": ConstraintType.POSITION,
            "elements": ["@", "."],
            "requirement": PositionRequirement.NOT_ADJACENT,
            "min_distance": 1,
        }
    ],
}


def evaluate_conjecture_quality(ir, test_name: str) -> float:
    """
    Evaluate IR constraint completeness against ground truth.

    Measures what fraction of expected constraints were detected in the IR.

    Args:
        ir: The generated IR
        test_name: Name of test to get ground truth for

    Returns:
        Completeness score from 0.0 to 1.0
    """
    if test_name not in GROUND_TRUTH_CONSTRAINTS:
        return 1.0  # Unknown test, assume complete

    expected = GROUND_TRUTH_CONSTRAINTS[test_name]
    if not expected:
        return 1.0  # No expected constraints

    detected = ir.constraints if hasattr(ir, "constraints") else []
    if not detected:
        return 0.0  # No constraints detected

    # Check each expected constraint for presence
    matches = 0
    for exp in expected:
        exp_type = exp["type"]

        # Find matching constraint in detected list
        for det in detected:
            if det.type != exp_type:
                continue

            # Type matches, check specifics
            if exp_type == ConstraintType.RETURN:
                # ReturnConstraint match
                if isinstance(det, ReturnConstraint):
                    matches += 1
                    break

            elif exp_type == ConstraintType.LOOP_BEHAVIOR:
                # LoopBehaviorConstraint match - check search type
                if isinstance(det, LoopBehaviorConstraint):
                    if det.search_type == exp.get("search_type"):
                        matches += 1
                        break

            elif exp_type == ConstraintType.POSITION:
                # PositionConstraint match - check elements and requirement
                if isinstance(det, PositionConstraint):
                    if set(det.elements) == set(
                        exp.get("elements", [])
                    ) and det.requirement == exp.get("requirement"):
                        matches += 1
                        break

    completeness = matches / len(expected) if expected else 1.0
    return completeness


def evaluate_constraint_preservation(ir, code: str, test_name: str) -> float:
    """
    Evaluate if generated code satisfies IR constraints.

    Measures what fraction of IR constraints are preserved in the generated code.

    Args:
        ir: The IR with constraints
        code: Generated code
        test_name: Name of test

    Returns:
        Preservation score from 0.0 to 1.0
    """
    if not hasattr(ir, "constraints") or not ir.constraints:
        return 1.0  # No constraints to preserve

    validator = ConstraintValidator()
    violations = validator.validate(code, ir)

    # Calculate preservation: (total - violated) / total
    total_constraints = len(ir.constraints)
    violated_constraints = len(violations)

    preservation = (total_constraints - violated_constraints) / total_constraints
    return max(0.0, preservation)


# Test specifications for the 3 persistent failures
TEST_SPECS = {
    "count_words": {
        "prompt": "Create a function that counts the number of words in a string",
        "test_cases": [
            ({"text": "hello world"}, 2),
            ({"text": "one"}, 1),
            ({"text": ""}, 0),
            ({"text": "a b c d e"}, 5),
            ({"text": "  spaced  "}, 1),
        ],
        "expected_constraint": "ReturnConstraint",
    },
    "find_index": {
        "prompt": "Create a function that finds the first index of a value in a list, returning -1 if not found",
        "test_cases": [
            ({"items": [1, 2, 3], "target": 2}, 1),
            ({"items": [1, 2, 3], "target": 4}, -1),
            ({"items": [], "target": 1}, -1),
            ({"items": [1, 2, 1], "target": 1}, 0),  # Critical: FIRST occurrence
            ({"items": [5], "target": 5}, 0),
        ],
        "expected_constraint": "LoopBehaviorConstraint",
    },
    "is_valid_email": {
        "prompt": "Create a function that validates if a string is a valid email address (must have @ and . with characters in between)",
        "test_cases": [
            ({"email": "test@example.com"}, True),
            ({"email": "invalid"}, False),
            ({"email": "no@at"}, False),
            ({"email": "test@.com"}, False),  # Critical: adjacency bug
            ({"email": "@example.com"}, False),
        ],
        "expected_constraint": "PositionConstraint",
    },
}


class FailureDiagnostic:
    """Collects and analyzes code generation variations for a failing test."""

    def __init__(self, test_name: str, spec: dict[str, Any]):
        self.test_name = test_name
        self.spec = spec
        self.samples: list[dict[str, Any]] = []
        self.provider = None
        self.translator = None
        self.generator = None
        self.ast_repair = ASTRepairEngine()
        self.constraint_detector = ConstraintDetector()
        self.constraint_validator = ConstraintValidator()

    async def initialize(self):
        """Initialize providers and generators."""
        self.provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
        await self.provider.initialize(credentials={})
        self.translator = XGrammarIRTranslator(self.provider)
        self.generator = XGrammarCodeGenerator(self.provider)

    async def collect_samples(self, num_samples: int = 12):
        """Collect multiple code generation samples."""
        print(f"\n{'=' * 80}")
        print(f"Collecting samples for: {self.test_name}")
        print(f"{'=' * 80}\n")

        # Generate IR once (should be consistent)
        print("Generating IR from prompt...")
        ir = await self.translator.translate(self.spec["prompt"], language="python")
        print(f"✓ IR generated: {ir.signature.name}")

        # Check constraint detection on IR
        detected_constraints = ir.constraints if hasattr(ir, "constraints") else []
        print(f"✓ Constraints detected: {len(detected_constraints)}")
        for constraint in detected_constraints:
            print(f"  - {constraint.type.value}: {constraint.description}")

        # Evaluate conjecture quality
        completeness = evaluate_conjecture_quality(ir, self.test_name)
        print(f"✓ Conjecture completeness: {completeness:.2%}")

        # Store IR for use in samples
        self.ir = ir

        # Generate multiple code samples with varying temperatures
        temperatures = [0.3, 0.5, 0.7, 0.8, 0.9]
        samples_per_temp = num_samples // len(temperatures)

        for temp in temperatures:
            print(f"\n--- Temperature {temp} ---")
            for i in range(samples_per_temp):
                print(f"  Sample {i + 1}/{samples_per_temp}...", end=" ", flush=True)
                sample = await self._generate_and_analyze_sample(ir, temp, i)
                self.samples.append(sample)
                status = "✓" if sample["tests_passed"] else "✗"
                print(f"{status} ({sample['tests_passed']}/{len(self.spec['test_cases'])} tests)")

        print(f"\n{'=' * 80}")
        print(f"Collected {len(self.samples)} samples for {self.test_name}")
        print(f"{'=' * 80}\n")

    async def _generate_and_analyze_sample(
        self, ir, temperature: float, sample_num: int
    ) -> dict[str, Any]:
        """Generate code and collect comprehensive diagnostic data."""
        sample = {
            "test_name": self.test_name,
            "sample_num": sample_num,
            "temperature": temperature,
            "timestamp": datetime.now().isoformat(),
        }

        # Generate code
        result = await self.generator.generate(ir, temperature=temperature)
        sample["code"] = result.source_code
        sample["generation_metadata"] = result.metadata

        # Parse AST
        try:
            tree = ast.parse(result.source_code)
            sample["ast_parseable"] = True
            sample["ast_dump"] = ast.dump(tree, indent=2)
        except SyntaxError as e:
            sample["ast_parseable"] = False
            sample["ast_error"] = str(e)
            sample["tests_passed"] = 0
            return sample

        # Apply AST repair
        try:
            repaired_code = self.ast_repair.repair(result.source_code, ir.signature.name)
            sample["ast_repair_applied"] = repaired_code is not None
            sample["repaired_code"] = (
                repaired_code if repaired_code is not None else result.source_code
            )
        except SyntaxError:
            sample["ast_repair_applied"] = False
            sample["repaired_code"] = result.source_code

        # Check constraint validation
        final_code = sample["repaired_code"]
        if ir.constraints:
            violations = self.constraint_validator.validate(final_code, ir)
            sample["constraint_violations"] = [
                {
                    "type": v.constraint_type,
                    "severity": v.severity,
                    "description": v.description,
                }
                for v in violations
            ]
        else:
            sample["constraint_violations"] = []

        # Evaluate constraint preservation (Phase 1 diagnostic)
        preservation_score = evaluate_constraint_preservation(ir, final_code, self.test_name)
        sample["constraint_preservation"] = preservation_score

        # Evaluate conjecture completeness (Phase 1 diagnostic)
        completeness_score = evaluate_conjecture_quality(ir, self.test_name)
        sample["conjecture_completeness"] = completeness_score

        # Execute test cases
        test_results = self._execute_tests(sample["repaired_code"], ir.signature.name)
        sample["test_results"] = test_results
        sample["tests_passed"] = sum(1 for r in test_results if r["passed"])

        return sample

    def _execute_tests(self, code: str, function_name: str) -> list[dict[str, Any]]:
        """Execute test cases and return results."""
        results = []
        namespace = {}

        try:
            exec(code, namespace)
            func = namespace.get(function_name)
            if not func:
                return [{"passed": False, "error": f"Function {function_name} not found"}]

            for inputs, expected in self.spec["test_cases"]:
                try:
                    result = func(**inputs)
                    passed = result == expected
                    results.append(
                        {
                            "inputs": inputs,
                            "expected": expected,
                            "actual": result,
                            "passed": passed,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "inputs": inputs,
                            "expected": expected,
                            "error": str(e),
                            "passed": False,
                        }
                    )
        except Exception as e:
            return [{"passed": False, "error": f"Execution error: {str(e)}"}]

        return results

    def save_samples(self, output_dir: Path):
        """Save collected samples to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{self.test_name}_samples.json"

        with open(output_file, "w") as f:
            json.dump(
                {
                    "test_name": self.test_name,
                    "spec": self.spec,
                    "num_samples": len(self.samples),
                    "samples": self.samples,
                    "summary": self._generate_summary(),
                },
                f,
                indent=2,
            )

        print(f"✓ Saved {len(self.samples)} samples to {output_file}")

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics for collected samples."""
        if not self.samples:
            return {}

        total = len(self.samples)
        passing = sum(1 for s in self.samples if s["tests_passed"] == len(self.spec["test_cases"]))
        ast_repairs = sum(1 for s in self.samples if s.get("ast_repair_applied", False))
        constraint_violations = sum(
            1 for s in self.samples if len(s.get("constraint_violations", [])) > 0
        )

        # Phase 1 diagnostics: average completeness and preservation
        avg_completeness = sum(s.get("conjecture_completeness", 0.0) for s in self.samples) / total
        avg_preservation = sum(s.get("constraint_preservation", 0.0) for s in self.samples) / total

        return {
            "total_samples": total,
            "fully_passing": passing,
            "pass_rate": passing / total if total > 0 else 0,
            "ast_repair_triggered": ast_repairs,
            "ast_repair_rate": ast_repairs / total if total > 0 else 0,
            "constraint_violations_detected": constraint_violations,
            "constraint_violation_rate": constraint_violations / total if total > 0 else 0,
            "avg_conjecture_completeness": avg_completeness,
            "avg_constraint_preservation": avg_preservation,
        }

    def print_summary(self):
        """Print summary of collected samples."""
        summary = self._generate_summary()
        print(f"\n{'=' * 80}")
        print(f"Summary for {self.test_name}")
        print(f"{'=' * 80}")
        print(f"Total samples: {summary['total_samples']}")
        print(f"Fully passing: {summary['fully_passing']} ({summary['pass_rate'] * 100:.1f}%)")
        print(
            f"AST repair triggered: {summary['ast_repair_triggered']} ({summary['ast_repair_rate'] * 100:.1f}%)"
        )
        print(
            f"Constraint violations: {summary['constraint_violations_detected']} ({summary['constraint_violation_rate'] * 100:.1f}%)"
        )
        print("\n--- Phase 1 Diagnostics ---")
        print(f"Avg conjecture completeness: {summary['avg_conjecture_completeness'] * 100:.1f}%")
        print(f"Avg constraint preservation: {summary['avg_constraint_preservation'] * 100:.1f}%")
        print(f"{'=' * 80}\n")


async def main():
    """Run diagnostic collection for all 3 failures."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect diagnostic samples for failing tests")
    parser.add_argument("--output", default="logs/failure_diagnostics", help="Output directory")
    parser.add_argument(
        "--samples-per-test", type=int, default=12, help="Number of samples per test"
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    print(f"\n{'#' * 80}")
    print("# Failure Diagnostic Sample Collection")
    print(f"# Output: {output_dir}")
    print(f"# Samples per test: {args.samples_per_test}")
    print(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#' * 80}\n")

    for test_name, spec in TEST_SPECS.items():
        diagnostic = FailureDiagnostic(test_name, spec)
        await diagnostic.initialize()
        await diagnostic.collect_samples(num_samples=args.samples_per_test)
        diagnostic.save_samples(output_dir)
        diagnostic.print_summary()

    print(f"\n{'#' * 80}")
    print("# Collection Complete")
    print(f"# Review samples in {output_dir}")
    print(f"{'#' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())
