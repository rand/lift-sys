"""Comprehensive integration tests for the lift-sys system."""
import tempfile
import os
from pathlib import Path

import pytest
from git import Repo

from lift_sys.ir.parser import IRParser
from lift_sys.ir.models import IntermediateRepresentation, HoleKind
from lift_sys.verifier.smt_checker import SMTChecker
from lift_sys.planner.planner import Planner
from lift_sys.forward_mode.synthesizer import CodeSynthesizer, SynthesizerConfig
from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig


class TestLiftSysIntegration:
    """Test complete lift-sys workflows."""

    def test_ir_parser_round_trip(self):
        """Test IR parsing and serialization round trip."""
        sample_ir = """
ir fibonacci {
  intent: compute fibonacci sequence efficiently
  signature: fibonacci(n: int) -> int {
    <?max_depth: int = "recursion limit"?>,
    <?optimization: Strategy = "memoization approach"?>
  }
  effects:
    - modifies global cache
    - may raise RecursionError
  assert:
    - n >= 0
    - result >= 0 {<?result_bound: Predicate = "upper bound constraint"?>}
}"""

        parser = IRParser()
        ir = parser.parse(sample_ir)

        # Verify structure
        assert ir.signature.name == "fibonacci"
        assert ir.intent.summary.strip() == "compute fibonacci sequence efficiently"
        assert len(ir.signature.parameters) == 1
        assert ir.signature.parameters[0].name == "n"
        assert len(ir.effects) == 2
        assert len(ir.assertions) == 2
        assert len(ir.typed_holes()) == 3

        # Test serialization
        ir_dict = ir.to_dict()
        assert "intent" in ir_dict
        assert "signature" in ir_dict
        assert "effects" in ir_dict
        assert "assertions" in ir_dict
        assert "metadata" in ir_dict

        # Test deserialization
        ir_restored = IntermediateRepresentation.from_dict(ir_dict)
        assert ir_restored.signature.name == ir.signature.name
        assert ir_restored.intent.summary == ir.intent.summary
        assert len(ir_restored.typed_holes()) == len(ir.typed_holes())

        # Test text output
        text_output = parser.dumps(ir_restored)
        assert "fibonacci" in text_output
        assert "compute fibonacci sequence efficiently" in text_output

    def test_smt_verification(self):
        """Test SMT checker with various predicates."""
        sample_ir = """
ir validate_positive {
  intent: ensure input is positive
  signature: validate_positive(x: int) -> bool
  assert:
    - x > 0
    - x < 1000
}"""

        parser = IRParser()
        ir = parser.parse(sample_ir)

        checker = SMTChecker()

        # Test satisfiable constraints
        result = checker.verify(ir, assumptions=[("x", 50)])
        assert result.success

        # Test unsatisfiable constraints
        result = checker.verify(ir, assumptions=[("x", -5)])
        assert not result.success

    def test_planner_workflow(self):
        """Test planner with conflict-driven learning."""
        sample_ir = """
ir complex_task {
  intent: perform complex computation {<?complexity: Description = "computational complexity"?>}
  signature: complex_task(data: list) -> result
  assert:
    - len(data) > 0
}"""

        parser = IRParser()
        ir = parser.parse(sample_ir)

        planner = Planner()
        plan = planner.load_ir(ir)

        # Check plan structure
        assert len(plan.steps) == 5  # parse_ir, verify_assertions, synthesise_code, resolve_holes, finalise_ir
        assert plan.goals == ["verified_ir", "code_generation"]

        # Test step progression
        next_steps = planner.step("parse_ir", success=True)
        assert len(next_steps) >= 1

        # Test conflict handling
        next_steps = planner.step("verify_assertions", success=False, reason="SMT timeout")
        assert "verify_assertions" in planner.state.conflicts

        suggestions = planner.suggest_resolution()
        assert "verify_assertions" in suggestions

    def test_forward_mode_synthesis(self):
        """Test forward mode code synthesis."""
        sample_ir = """
ir calculator {
  intent: basic arithmetic operations
  signature: add(a: float, b: float) -> float
  assert:
    - result == a + b
    - abs(result) < 1e10
}"""

        parser = IRParser()
        ir = parser.parse(sample_ir)

        config = SynthesizerConfig(model_endpoint="http://localhost:8001", temperature=0.1)
        synthesizer = CodeSynthesizer(config)

        constraints = synthesizer.compile_constraints(ir)
        assert len(constraints) >= 2  # At least the assertions

        output = synthesizer.generate(ir)
        assert output["endpoint"] == "http://localhost:8001"
        assert output["temperature"] == 0.1
        assert "intent" in output["prompt"]
        assert "signature" in output["prompt"]

    def test_reverse_mode_lifting(self):
        """Test reverse mode specification lifting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test repository
            repo = Repo.init(temp_dir)

            # Create sample Python file
            sample_code = '''
def factorial(n):
    """Calculate factorial of n."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def is_prime(n):
    """Check if n is prime."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
'''

            code_file = Path(temp_dir) / "math_utils.py"
            code_file.write_text(sample_code)

            repo.index.add(["math_utils.py"])
            repo.index.commit("Add math utilities")

            # Test specification lifting
            config = LifterConfig(
                codeql_queries=["security/default", "correctness/basic"],
                daikon_entrypoint="factorial"
            )

            lifter = SpecificationLifter(config)
            lifter.load_repository(temp_dir)

            ir = lifter.lift("math_utils.py")

            # Verify lifted IR
            assert ir.signature.name == "math_utils"
            assert ir.intent.summary == "Lifted intent with typed holes"
            assert len(ir.assertions) >= 1
            assert len(ir.typed_holes()) >= 1
            assert ir.metadata.source_path == "math_utils.py"
            assert ir.metadata.origin == "reverse"

            # Verify hole kinds
            holes_by_kind = {}
            for hole in ir.typed_holes():
                holes_by_kind.setdefault(hole.kind, []).append(hole)

            assert HoleKind.INTENT in holes_by_kind

    def test_complete_workflow_round_trip(self):
        """Test complete reverse -> forward workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test repository
            repo = Repo.init(temp_dir)

            sample_code = '''
def validate_and_process(data):
    """Validate input data and process it."""
    if not data or len(data) == 0:
        raise ValueError("Data cannot be empty")

    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)

    return result
'''

            code_file = Path(temp_dir) / "processor.py"
            code_file.write_text(sample_code)
            repo.index.add(["processor.py"])
            repo.index.commit("Add data processor")

            # Reverse mode: Lift specification
            lifter_config = LifterConfig(
                codeql_queries=["security/validation"],
                daikon_entrypoint="validate_and_process"
            )

            lifter = SpecificationLifter(lifter_config)
            lifter.load_repository(temp_dir)
            lifted_ir = lifter.lift("processor.py")

            # Verify and plan
            checker = SMTChecker()
            verification_result = checker.verify(lifted_ir)
            # Note: May not be satisfiable due to placeholder assertions

            planner = Planner()
            plan = planner.load_ir(lifted_ir)
            assert len(plan.steps) >= 3

            # Forward mode: Generate code
            synth_config = SynthesizerConfig(model_endpoint="http://localhost:8001")
            synthesizer = CodeSynthesizer(synth_config)

            generation_request = synthesizer.generate(lifted_ir)
            assert "prompt" in generation_request
            assert "constraints" in generation_request["prompt"]

            # Test serialization compatibility
            ir_dict = lifted_ir.to_dict()
            ir_restored = IntermediateRepresentation.from_dict(ir_dict)

            # Generate from restored IR
            generation_request_2 = synthesizer.generate(ir_restored)
            assert generation_request_2["endpoint"] == generation_request["endpoint"]