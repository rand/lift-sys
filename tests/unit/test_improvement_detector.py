"""Tests for improvement area detection."""

import pytest

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.reverse_mode.improvement_detector import ImprovementDetector


@pytest.fixture
def detector():
    """Create an improvement detector."""
    return ImprovementDetector()


@pytest.fixture
def minimal_ir():
    """Create a minimal IR for testing."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Test function"),
        signature=SigClause(name="test", parameters=[], returns="int"),
        metadata=Metadata(evidence=[]),
    )


@pytest.fixture
def ir_with_security_issues():
    """Create an IR with security findings in evidence."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Execute database query"),
        signature=SigClause(
            name="get_user",
            parameters=[Parameter(name="username", type_hint="str")],
            returns="dict",
        ),
        metadata=Metadata(
            evidence=[
                {
                    "id": "codeql-001",
                    "analysis": "codeql",
                    "message": "Potential SQL injection vulnerability",
                    "location": "get_user:5",
                    "metadata": {"severity": "critical"},
                },
                {
                    "id": "codeql-002",
                    "analysis": "codeql",
                    "message": "Hardcoded database password",
                    "location": "get_user:2",
                    "metadata": {"severity": "high"},
                },
                {
                    "id": "codeql-003",
                    "analysis": "codeql",
                    "message": "Missing input validation",
                    "location": "get_user:3",
                    "metadata": {"severity": "medium"},
                },
            ]
        ),
    )


@pytest.fixture
def ir_with_incomplete_specs():
    """Create an IR with incomplete specifications."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Add"),  # Too brief
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="unknown"),  # Missing type
                Parameter(name="b", type_hint="unknown"),  # Missing type
            ],
            returns="unknown",  # Missing return type
        ),
        # No assertions
        metadata=Metadata(evidence=[]),
    )


@pytest.fixture
def ir_with_resource_handling():
    """Create an IR with resource handling but no cleanup."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Process file data"),
        signature=SigClause(
            name="process_file",
            parameters=[Parameter(name="path", type_hint="str")],
            returns="str",
        ),
        effects=[
            EffectClause(description="Open file at path"),
            # Missing: Close file
        ],
        metadata=Metadata(evidence=[]),
    )


@pytest.fixture
def ir_with_daikon_findings():
    """Create an IR with Daikon analysis results."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Calculate result"),
        signature=SigClause(
            name="calc",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        ),
        metadata=Metadata(
            evidence=[
                {
                    "id": "daikon-001",
                    "analysis": "daikon",
                    "message": "x == x (trivial)",
                    "metadata": {"tags": ["trivial"]},
                },
                {
                    "id": "daikon-002",
                    "analysis": "daikon",
                    "message": "x >= 0",
                    "metadata": {"tags": []},
                },
            ]
        ),
    )


@pytest.fixture
def ir_with_undocumented_params():
    """Create an IR with undocumented parameters."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Calculate discount price"),
        signature=SigClause(
            name="apply_discount",
            parameters=[
                Parameter(name="price", type_hint="float"),  # No description
                Parameter(name="rate", type_hint="float", description="Discount"),  # Too short
            ],
            returns="float",
        ),
        metadata=Metadata(evidence=[]),
    )


class TestImprovementDetector:
    """Tests for ImprovementDetector class."""

    def test_detector_initialization(self, detector):
        """Test detector can be initialized."""
        assert detector is not None

    def test_detect_improvements_returns_list(self, detector, minimal_ir):
        """Test detect_improvements returns a list."""
        result = detector.detect_improvements(minimal_ir)
        assert isinstance(result, list)

    def test_minimal_ir_has_some_improvements(self, detector, minimal_ir):
        """Test that even minimal IR has improvement suggestions."""
        result = detector.detect_improvements(minimal_ir)
        # Should at least suggest adding preconditions and clarifying intent
        assert len(result) > 0


class TestSecurityAnalysis:
    """Tests for security improvement detection."""

    def test_detect_security_improvements_no_findings(self, detector, minimal_ir):
        """Test no security holes when no findings."""
        holes = detector.detect_security_improvements(minimal_ir)
        assert len(holes) == 0

    def test_detect_critical_security_issue(self, detector, ir_with_security_issues):
        """Test detection of critical security issues."""
        holes = detector.detect_security_improvements(ir_with_security_issues)

        critical_holes = [h for h in holes if h.identifier.startswith("security_critical")]
        assert len(critical_holes) == 1
        assert "CRITICAL" in critical_holes[0].description
        assert "SQL injection" in critical_holes[0].description

    def test_detect_high_security_issue(self, detector, ir_with_security_issues):
        """Test detection of high-severity security issues."""
        holes = detector.detect_security_improvements(ir_with_security_issues)

        high_holes = [h for h in holes if h.identifier.startswith("security_high")]
        assert len(high_holes) == 1
        assert "HIGH" in high_holes[0].description
        assert "Hardcoded" in high_holes[0].description

    def test_detect_medium_security_batch(self, detector, ir_with_security_issues):
        """Test batching of medium-severity issues."""
        holes = detector.detect_security_improvements(ir_with_security_issues)

        medium_holes = [h for h in holes if h.identifier == "security_medium_batch"]
        assert len(medium_holes) == 1
        assert "1 medium-severity" in medium_holes[0].description

    def test_security_hole_has_kind_assertion(self, detector, ir_with_security_issues):
        """Test security holes are marked as assertions."""
        holes = detector.detect_security_improvements(ir_with_security_issues)

        critical_hole = [h for h in holes if h.identifier.startswith("security_critical")][0]
        assert critical_hole.kind == HoleKind.ASSERTION

    def test_security_remediation_sql_injection(self, detector):
        """Test SQL injection remediation suggestion."""
        finding = {"message": "SQL injection vulnerability"}
        remediation = detector._get_security_remediation(finding)
        assert "parameterized" in remediation.lower() or "orm" in remediation.lower()

    def test_security_remediation_path_traversal(self, detector):
        """Test path traversal remediation suggestion."""
        finding = {"message": "Path traversal vulnerability"}
        remediation = detector._get_security_remediation(finding)
        assert "whitelist" in remediation.lower()

    def test_security_assertion_generation(self, detector):
        """Test security assertion generation."""
        finding = {"message": "SQL injection in query"}
        assertion = detector._generate_security_assertion(finding)
        assert "sanitized" in assertion.lower() or "parameterized" in assertion.lower()


class TestCompletenessAnalysis:
    """Tests for completeness improvement detection."""

    def test_detect_missing_preconditions(self, detector, minimal_ir):
        """Test detection of missing preconditions."""
        holes = detector.detect_completeness_issues(minimal_ir)

        precond_holes = [h for h in holes if h.identifier == "add_preconditions"]
        assert len(precond_holes) == 1
        assert "pre-conditions" in precond_holes[0].description.lower()

    def test_detect_missing_postconditions(self, detector, minimal_ir):
        """Test detection of missing postconditions."""
        holes = detector.detect_completeness_issues(minimal_ir)

        postcond_holes = [h for h in holes if h.identifier == "add_postconditions"]
        assert len(postcond_holes) == 1
        assert "post-conditions" in postcond_holes[0].description.lower()

    def test_detect_untyped_parameters(self, detector, ir_with_incomplete_specs):
        """Test detection of parameters without types."""
        holes = detector.detect_completeness_issues(ir_with_incomplete_specs)

        type_holes = [h for h in holes if h.identifier.startswith("type_")]
        assert len(type_holes) == 2  # Both parameters
        assert any("a" in h.description for h in type_holes)
        assert any("b" in h.description for h in type_holes)

    def test_detect_missing_return_type(self, detector, ir_with_incomplete_specs):
        """Test detection of missing return type."""
        holes = detector.detect_completeness_issues(ir_with_incomplete_specs)

        return_holes = [h for h in holes if h.identifier == "return_type"]
        assert len(return_holes) == 1
        assert "Return type not specified" in return_holes[0].description

    def test_detect_vague_intent(self, detector, ir_with_incomplete_specs):
        """Test detection of vague intent descriptions."""
        holes = detector.detect_completeness_issues(ir_with_incomplete_specs)

        intent_holes = [h for h in holes if h.identifier == "clarify_intent"]
        assert len(intent_holes) == 1
        assert "brief" in intent_holes[0].description.lower()

    def test_detect_missing_rationale(self, detector, minimal_ir):
        """Test detection of missing rationale."""
        holes = detector.detect_completeness_issues(minimal_ir)

        rationale_holes = [h for h in holes if h.identifier == "add_rationale"]
        assert len(rationale_holes) == 1
        assert "rationale" in rationale_holes[0].description.lower()

    def test_completeness_holes_have_suggestions(self, detector, ir_with_incomplete_specs):
        """Test that completeness holes include suggestions."""
        holes = detector.detect_completeness_issues(ir_with_incomplete_specs)

        for hole in holes:
            if "suggestions" in hole.constraints:
                assert len(hole.constraints["suggestions"]) > 0


class TestErrorHandlingAnalysis:
    """Tests for error handling improvement detection."""

    def test_detect_missing_error_specs(self, detector, minimal_ir):
        """Test detection of missing error specifications."""
        holes = detector.detect_error_handling_gaps(minimal_ir)

        error_holes = [h for h in holes if h.identifier == "specify_error_handling"]
        assert len(error_holes) == 1
        assert "Error handling not specified" in error_holes[0].description

    def test_no_error_hole_when_error_effects_present(self, detector):
        """Test no error hole when error effects are documented."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
            effects=[EffectClause(description="Raises ValueError on invalid input")],
            metadata=Metadata(evidence=[]),
        )

        holes = detector.detect_error_handling_gaps(ir)
        error_holes = [h for h in holes if h.identifier == "specify_error_handling"]
        assert len(error_holes) == 0

    def test_detect_missing_resource_cleanup(self, detector, ir_with_resource_handling):
        """Test detection of missing resource cleanup."""
        holes = detector.detect_error_handling_gaps(ir_with_resource_handling)

        cleanup_holes = [h for h in holes if h.identifier == "specify_resource_cleanup"]
        assert len(cleanup_holes) == 1
        assert "cleanup not specified" in cleanup_holes[0].description.lower()

    def test_no_cleanup_hole_when_cleanup_present(self, detector):
        """Test no cleanup hole when cleanup is documented."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
            effects=[
                EffectClause(description="Open file"),
                EffectClause(description="Close file"),
            ],
            metadata=Metadata(evidence=[]),
        )

        holes = detector.detect_error_handling_gaps(ir)
        cleanup_holes = [h for h in holes if h.identifier == "specify_resource_cleanup"]
        assert len(cleanup_holes) == 0


class TestQualityAnalysis:
    """Tests for quality improvement detection."""

    def test_detect_weak_invariants(self, detector, ir_with_daikon_findings):
        """Test detection of trivial/weak invariants."""
        holes = detector.detect_quality_issues(ir_with_daikon_findings)

        weak_holes = [h for h in holes if h.identifier == "strengthen_invariants"]
        assert len(weak_holes) == 1
        assert "trivial invariants" in weak_holes[0].description.lower()

    def test_no_weak_invariant_holes_without_daikon(self, detector, minimal_ir):
        """Test no weak invariant holes without Daikon findings."""
        holes = detector.detect_quality_issues(minimal_ir)

        weak_holes = [h for h in holes if h.identifier == "strengthen_invariants"]
        assert len(weak_holes) == 0

    def test_detect_missing_test_evidence(self, detector, minimal_ir):
        """Test detection of missing test coverage."""
        holes = detector.detect_quality_issues(minimal_ir)

        test_holes = [h for h in holes if h.identifier == "add_test_evidence"]
        assert len(test_holes) == 1
        assert "test coverage" in test_holes[0].description.lower()

    def test_no_test_hole_when_daikon_present(self, detector, ir_with_daikon_findings):
        """Test no test hole when Daikon evidence exists."""
        holes = detector.detect_quality_issues(ir_with_daikon_findings)

        test_holes = [h for h in holes if h.identifier == "add_test_evidence"]
        # Should not appear because Daikon findings indicate tests were run
        assert len(test_holes) == 0


class TestDocumentationAnalysis:
    """Tests for documentation improvement detection."""

    def test_detect_undocumented_parameters(self, detector, ir_with_undocumented_params):
        """Test detection of undocumented parameters."""
        holes = detector.detect_documentation_gaps(ir_with_undocumented_params)

        doc_holes = [h for h in holes if h.identifier == "document_parameters"]
        assert len(doc_holes) == 1
        assert "2 parameters" in doc_holes[0].description

    def test_no_param_doc_hole_when_documented(self, detector):
        """Test no parameter documentation hole when all documented."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(
                        name="a",
                        type_hint="int",
                        description="A detailed description of parameter a",
                    ),
                ],
                returns="int",
            ),
            metadata=Metadata(evidence=[]),
        )

        holes = detector.detect_documentation_gaps(ir)
        doc_holes = [h for h in holes if h.identifier == "document_parameters"]
        assert len(doc_holes) == 0

    def test_detect_missing_examples(self, detector, minimal_ir):
        """Test detection of missing usage examples."""
        holes = detector.detect_documentation_gaps(minimal_ir)

        example_holes = [h for h in holes if h.identifier == "add_usage_examples"]
        assert len(example_holes) == 1
        assert "examples" in example_holes[0].description.lower()

    def test_no_example_hole_when_present(self, detector):
        """Test no example hole when examples are present."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers. For example: add(2, 3) returns 5"),
            signature=SigClause(name="add", parameters=[], returns="int"),
            metadata=Metadata(evidence=[]),
        )

        holes = detector.detect_documentation_gaps(ir)
        example_holes = [h for h in holes if h.identifier == "add_usage_examples"]
        assert len(example_holes) == 0


class TestPrioritization:
    """Tests for hole prioritization."""

    def test_security_issues_come_first(self, detector, ir_with_security_issues):
        """Test that security issues are prioritized highest."""
        holes = detector.detect_improvements(ir_with_security_issues)

        # First hole should be security critical
        assert holes[0].identifier.startswith("security_critical")

    def test_prioritization_order(self, detector):
        """Test overall prioritization order."""
        # Create IR with multiple issue types
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),  # Brief (low priority)
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="unknown")],  # Missing type (high)
                returns="int",
            ),
            # No assertions (high priority)
            metadata=Metadata(
                evidence=[
                    {
                        "id": "codeql-001",
                        "analysis": "codeql",
                        "message": "Critical security issue",
                        "metadata": {"severity": "critical"},
                    }
                ]
            ),
        )

        holes = detector.detect_improvements(ir)

        # Should be: security, then completeness, then documentation
        assert holes[0].identifier.startswith("security")
        assert any(h.identifier == "add_preconditions" for h in holes[:5])
        assert any(h.identifier == "clarify_intent" for h in holes[-5:])


class TestHelperMethods:
    """Tests for helper methods."""

    def test_infer_type_from_numeric_usage(self, detector):
        """Test type inference from numeric operations."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="unknown")],
                returns="int",
            ),
            assertions=[AssertClause(predicate="x > 0")],
            metadata=Metadata(evidence=[]),
        )

        param = ir.signature.parameters[0]
        usages = detector._infer_type_from_usage(param, ir)

        assert any("numeric" in u.lower() for u in usages)

    def test_infer_type_from_sequence_usage(self, detector):
        """Test type inference from sequence operations."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="items", type_hint="unknown")],
                returns="int",
            ),
            assertions=[AssertClause(predicate="len(items) > 0")],
            metadata=Metadata(evidence=[]),
        )

        param = ir.signature.parameters[0]
        usages = detector._infer_type_from_usage(param, ir)

        assert any("sequence" in u.lower() for u in usages)

    def test_infer_return_type_from_assertions(self, detector):
        """Test return type inference from postconditions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="unknown"),
            assertions=[AssertClause(predicate="return value > 0")],
            metadata=Metadata(evidence=[]),
        )

        return_type = detector._infer_return_type(ir)

        assert "numeric" in return_type.lower()

    def test_has_test_evidence_with_daikon(self, detector, ir_with_daikon_findings):
        """Test test evidence detection with Daikon findings."""
        has_evidence = detector._has_test_evidence(ir_with_daikon_findings)
        assert has_evidence is True

    def test_has_test_evidence_without_tests(self, detector, minimal_ir):
        """Test test evidence detection without tests."""
        has_evidence = detector._has_test_evidence(minimal_ir)
        assert has_evidence is False
