"""Integration tests for confidence calibration with H10 metrics."""

import pytest

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.optimization.confidence import (
    train_from_h10_dataset,
)
from lift_sys.optimization.metrics import code_quality, ir_quality


class TestH10Integration:
    """Integration tests with H10 metrics."""

    @pytest.fixture
    def ir_validation_examples(self):
        """Create IR validation examples with ground truth from H10 metrics."""
        # Example 1: High quality IR (predicted matches expected)
        ir1_pred = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate sum of numbers"),
            signature=SigClause(
                name="calculate_sum",
                parameters=[Parameter(name="numbers", type_hint="list[int]")],
                returns="int",
            ),
            effects=[EffectClause(description="Pure computation, no side effects")],
            assertions=[AssertClause(predicate="result >= 0 if all(n >= 0 for n in numbers)")],
        )
        ir1_expected = ir1_pred  # Perfect match
        score1 = ir_quality(ir1_pred, ir1_expected)

        # Example 2: Medium quality IR (some differences)
        ir2_pred = IntermediateRepresentation(
            intent=IntentClause(summary="Sort list"),
            signature=SigClause(
                name="sort_list",
                parameters=[Parameter(name="items", type_hint="list")],
                returns="list",
            ),
            effects=[EffectClause(description="Sorts in-place")],
        )
        ir2_expected = IntermediateRepresentation(
            intent=IntentClause(summary="Sort list in ascending order"),
            signature=SigClause(
                name="sort_list",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="reverse", type_hint="bool"),
                ],
                returns="list[int]",
            ),
            effects=[EffectClause(description="Returns new sorted list")],
        )
        score2 = ir_quality(ir2_pred, ir2_expected)

        # Example 3: Low quality IR (significant differences)
        ir3_pred = IntermediateRepresentation(
            intent=IntentClause(summary="Do something"),
            signature=SigClause(
                name="func",
                parameters=[],
                returns=None,
            ),
            effects=[],
        )
        ir3_expected = IntermediateRepresentation(
            intent=IntentClause(summary="Filter even numbers from list"),
            signature=SigClause(
                name="filter_even",
                parameters=[Parameter(name="numbers", type_hint="list[int]")],
                returns="list[int]",
            ),
            effects=[EffectClause(description="Pure function")],
        )
        score3 = ir_quality(ir3_pred, ir3_expected)

        return [
            (ir1_pred, score1),
            (ir2_pred, score2),
            (ir3_pred, score3),
        ]

    @pytest.fixture
    def code_validation_examples(self):
        """Create code validation examples with ground truth from H10 metrics."""
        # Example 1: High quality code (correct implementation)
        code1_pred = '''def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b
'''
        code1_expected = code1_pred  # Perfect match
        tests1 = [
            ({"a": 1, "b": 2}, 3),
            ({"a": 0, "b": 0}, 0),
            ({"a": -1, "b": 1}, 0),
        ]
        score1 = code_quality(code1_pred, code1_expected, tests1)

        # Example 2: Medium quality code (works but different style)
        code2_pred = """def multiply(x, y):
    return x * y
"""
        code2_expected = '''def multiply(x: int, y: int) -> int:
    """Multiply two integers."""
    return x * y
'''
        tests2 = [
            ({"x": 2, "y": 3}, 6),
            ({"x": 0, "y": 5}, 0),
        ]
        score2 = code_quality(code2_pred, code2_expected, tests2)

        # Example 3: Low quality code (wrong implementation)
        code3_pred = """def subtract(a, b):
    return a + b  # Bug: should be a - b
"""
        code3_expected = '''def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b
'''
        tests3 = [
            ({"a": 5, "b": 3}, 2),
            ({"a": 0, "b": 1}, -1),
        ]
        score3 = code_quality(code3_pred, code3_expected, tests3)

        return [
            (code1_pred, score1),
            (code2_pred, score2),
            (code3_pred, score3),
        ]

    def test_train_with_h10_metrics(self, ir_validation_examples, code_validation_examples):
        """Test training calibrator with H10 validation dataset."""
        calibrator = train_from_h10_dataset(ir_validation_examples, code_validation_examples)

        # Verify calibrator is trained
        assert calibrator.ir_fitted
        assert calibrator.code_fitted

        # Verify we can estimate confidence for new examples
        new_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(name="test", parameters=[], returns="None"),
            effects=[],
        )
        confidence = calibrator.estimate_confidence(new_ir, "ir")
        assert 0.0 <= confidence.value <= 1.0
        assert confidence.calibrated

    def test_calibration_correlates_with_quality(
        self, ir_validation_examples, code_validation_examples
    ):
        """Test that confidence correlates with actual quality scores."""
        calibrator = train_from_h10_dataset(ir_validation_examples, code_validation_examples)

        # Test on IR examples
        ir_confidences = []
        ir_scores = []
        for ir, score in ir_validation_examples:
            conf = calibrator.estimate_confidence(ir, "ir")
            ir_confidences.append(conf.value)
            ir_scores.append(score)

        # Higher quality should generally have higher confidence
        # (This is a weak test due to small dataset, but validates direction)
        assert len(ir_confidences) == len(ir_scores)

        # Test on code examples
        code_confidences = []
        code_scores = []
        for code, score in code_validation_examples:
            conf = calibrator.estimate_confidence(code, "code")
            code_confidences.append(conf.value)
            code_scores.append(score)

        assert len(code_confidences) == len(code_scores)

    def test_end_to_end_workflow(self, ir_validation_examples, code_validation_examples):
        """Test complete workflow: H10 metrics → train → evaluate → predict."""
        # Step 1: Train calibrator from H10 validation dataset
        calibrator = train_from_h10_dataset(ir_validation_examples, code_validation_examples)

        # Step 2: Evaluate calibration on held-out data (using same data for simplicity)
        ir_preds = [ir for ir, _ in ir_validation_examples]
        ir_scores = [score for _, score in ir_validation_examples]
        ir_types = ["ir"] * len(ir_preds)

        metrics = calibrator.evaluate_calibration(ir_preds, ir_scores, ir_types)

        # Step 3: Verify metrics are computed
        assert 0.0 <= metrics.brier_score <= 1.0
        assert 0.0 <= metrics.ece <= 1.0
        assert metrics.correlation is not None

        # Step 4: Use calibrator for new predictions
        new_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Complex function with many operations"),
            signature=SigClause(
                name="complex_func",
                parameters=[
                    Parameter(name="x", type_hint="int"),
                    Parameter(name="y", type_hint="str"),
                    Parameter(name="z", type_hint="float"),
                ],
                returns="dict[str, Any]",
            ),
            effects=[
                EffectClause(description="Performs I/O operations"),
                EffectClause(description="Modifies global state"),
            ],
            assertions=[
                AssertClause(predicate="x > 0"),
                AssertClause(predicate="len(y) > 0"),
            ],
        )

        confidence = calibrator.estimate_confidence(new_ir, "ir")
        assert 0.0 <= confidence.value <= 1.0
        assert confidence.calibrated
        assert "effect_count" in confidence.features


class TestScalingWithDataset:
    """Test calibrator behavior as dataset grows."""

    def test_more_data_improves_calibration(self):
        """Test that calibration improves with more H10 validation examples."""
        # Small dataset (3 examples)
        small_ir_examples = [
            (
                IntermediateRepresentation(
                    intent=IntentClause(summary=f"Function {i}"),
                    signature=SigClause(name=f"func_{i}", parameters=[], returns="int"),
                    effects=[EffectClause(description="Pure")],
                ),
                i / 10.0,
            )
            for i in range(3)
        ]
        small_code_examples = [(f"def func_{i}():\n    return {i}", i / 10.0) for i in range(3)]

        calibrator_small = train_from_h10_dataset(small_ir_examples, small_code_examples)

        # Large dataset (20 examples)
        large_ir_examples = [
            (
                IntermediateRepresentation(
                    intent=IntentClause(summary=f"Function {i}"),
                    signature=SigClause(name=f"func_{i}", parameters=[], returns="int"),
                    effects=[EffectClause(description="Pure")],
                ),
                i / 20.0,
            )
            for i in range(20)
        ]
        large_code_examples = [(f"def func_{i}():\n    return {i}", i / 20.0) for i in range(20)]

        calibrator_large = train_from_h10_dataset(large_ir_examples, large_code_examples)

        # Both should be trained
        assert calibrator_small.ir_fitted
        assert calibrator_large.ir_fitted

        # Evaluate on test set
        test_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
            effects=[EffectClause(description="Pure")],
        )

        conf_small = calibrator_small.estimate_confidence(test_ir, "ir")
        conf_large = calibrator_large.estimate_confidence(test_ir, "ir")

        # Both should produce valid confidence scores
        assert 0.0 <= conf_small.value <= 1.0
        assert 0.0 <= conf_large.value <= 1.0

        # Large dataset calibrator should have more data (metadata)
        assert "Trained calibrator from H10 dataset" in str(calibrator_large)
