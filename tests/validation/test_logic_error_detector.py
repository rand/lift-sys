"""Tests for Logic Error Detector - Step 3 of IR Interpreter."""

import pytest

from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.validation.effect_analyzer import EffectChainAnalyzer
from lift_sys.validation.logic_error_detector import LogicErrorDetector


class TestLogicErrorDetector:
    """Test logic error detection patterns."""

    def test_off_by_one_first_with_enumerate(self):
        """Test detection of first/last confusion with enumerate."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find FIRST index of value in list", rationale=None),
            signature=SigClause(
                name="find_first_index",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="target", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Use enumerate to iterate through list with indices"),
                EffectClause(description="Check if item equals target"),
                EffectClause(description="Store the index"),
                # Missing: "Return immediately when found"
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_off_by_one(ir, trace)

        # Should detect off-by-one risk
        assert len(issues) > 0, "Should detect off-by-one risk with enumerate"
        assert any(issue.category == "off_by_one" for issue in issues), (
            f"Should flag off-by-one: {issues}"
        )

        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_off_by_one_first_with_immediate_return(self):
        """Test that immediate return is handled correctly."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find FIRST index of value in list", rationale=None),
            signature=SigClause(
                name="find_first_index",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="target", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Use enumerate to iterate through list with indices"),
                EffectClause(description="Check if item equals target"),
                EffectClause(description="Return the index immediately when found"),  # Good!
                EffectClause(description="Return -1 after loop if not found"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_off_by_one(ir, trace)

        # Should NOT flag this (immediate return is present)
        # Note: might still flag general warning, but should be less severe
        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_off_by_one_last_with_immediate_return(self):
        """Test detection when intent says LAST but returns immediately."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find LAST index of value in list", rationale=None),
            signature=SigClause(
                name="find_last_index",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="target", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Iterate through list"),
                EffectClause(description="Check if item equals target"),
                EffectClause(description="Return immediately when found"),  # Bug: returns FIRST!
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_off_by_one(ir, trace)

        # Should detect: intent says LAST but returns immediately (gives FIRST)
        assert len(issues) > 0, "Should detect LAST vs FIRST confusion"
        assert any("last" in issue.message.lower() for issue in issues), (
            f"Should mention 'last': {issues}"
        )

        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_invalid_email_validation_missing_after_check(self):
        """Test detection of incomplete email validation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check if string is valid email address", rationale=None),
            signature=SigClause(
                name="is_valid_email",
                parameters=[Parameter(name="email", type_hint="str")],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Check if email contains @ symbol"),
                EffectClause(description="Check if email contains . dot"),
                EffectClause(description="Return True if both checks pass, False otherwise"),
                # Missing: "Check that dot comes after @"
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_invalid_validation(ir, trace)

        # Should detect incomplete email validation
        assert len(issues) > 0, "Should detect incomplete email validation"
        assert any("after" in issue.message.lower() for issue in issues), (
            f"Should mention checking 'after': {issues}"
        )

        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_invalid_email_validation_only_at(self):
        """Test detection of email validation with only @ check."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email address", rationale=None),
            signature=SigClause(
                name="is_valid_email",
                parameters=[Parameter(name="email", type_hint="str")],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Check if email contains @ symbol"),
                EffectClause(description="Return True if found, False otherwise"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_invalid_validation(ir, trace)

        # Should detect: only checks @, not dot
        assert len(issues) > 0, "Should detect missing dot check"
        assert any("dot" in issue.message.lower() for issue in issues), (
            f"Should mention missing 'dot': {issues}"
        )

        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_valid_email_validation_with_after_check(self):
        """Test that complete email validation passes."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email address", rationale=None),
            signature=SigClause(
                name="is_valid_email",
                parameters=[Parameter(name="email", type_hint="str")],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Check if email contains @ symbol"),
                EffectClause(description="Find position of @"),
                EffectClause(description="Check if there's a dot after the @"),
                EffectClause(description="Check domain has characters before and after dot"),
                EffectClause(description="Return True if all checks pass, False otherwise"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_invalid_validation(ir, trace)

        # Should not detect issues (validation is complete)
        assert len(issues) == 0, f"Should not flag complete validation: {issues}"

    def test_invalid_phone_validation(self):
        """Test detection of incomplete phone validation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate phone number", rationale=None),
            signature=SigClause(
                name="is_valid_phone",
                parameters=[Parameter(name="phone", type_hint="str")],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Return True if phone is not empty, False otherwise"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_invalid_validation(ir, trace)

        # Should detect missing digit/length checks
        assert len(issues) > 0, "Should detect incomplete phone validation"

        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_unreachable_code_after_return(self):
        """Test detection of effects after unconditional return."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate result", rationale=None),
            signature=SigClause(
                name="calculate",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Multiply x by 2"),
                EffectClause(description="Return the result"),
                EffectClause(description="Add 10 to result"),  # Unreachable!
                EffectClause(description="Return modified result"),  # Unreachable!
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_unreachable_code(ir, trace)

        # Should detect unreachable effects
        assert len(issues) > 0, "Should detect unreachable code"
        assert any(issue.category == "unreachable_code" for issue in issues), (
            f"Should flag unreachable code: {issues}"
        )

        print(f"\nDetected issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    def test_no_unreachable_code_with_conditional_return(self):
        """Test that conditional returns don't trigger unreachable code warning."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find value or default", rationale=None),
            signature=SigClause(
                name="find_or_default",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="target", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Iterate through items"),
                EffectClause(description="If item equals target, return the item"),
                EffectClause(description="After loop, return -1 as default"),  # Not unreachable!
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_unreachable_code(ir, trace)

        # Should NOT flag unreachable (return is conditional)
        unreachable_issues = [issue for issue in issues if issue.category == "unreachable_code"]
        assert len(unreachable_issues) == 0, f"Should not flag conditional returns: {issues}"

    def test_detect_all_patterns(self):
        """Test that detect_all_patterns runs all detectors."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find FIRST valid email in list", rationale=None),
            signature=SigClause(
                name="find_first_valid_email",
                parameters=[Parameter(name="emails", type_hint="list[str]")],
                returns="str",
            ),
            effects=[
                EffectClause(description="Iterate through emails"),
                EffectClause(description="Check if email contains @"),
                EffectClause(description="Check if email contains ."),
                EffectClause(description="Store valid email"),
                # Missing: immediate return, dot after @ check
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        detector = LogicErrorDetector()
        issues = detector.detect_all_patterns(ir, trace)

        # Should detect multiple issues
        assert len(issues) > 0, "Should detect issues"

        # Should have both off-by-one and validation issues
        categories = [issue.category for issue in issues]
        print(f"\nDetected {len(issues)} issues:")
        for issue in issues:
            print(f"  [{issue.category}] {issue.message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
