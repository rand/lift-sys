"""Tests for the AgentAdvisor proactive IR analysis system."""

from lift_sys.analysis import AgentAdvisor, SuggestionCategory, SuggestionSeverity
from lift_sys.ir import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


class TestAgentAdvisor:
    """Tests for AgentAdvisor."""

    def test_create_advisor(self):
        """Test creating an AgentAdvisor instance."""
        advisor = AgentAdvisor()
        assert advisor is not None

    def test_analyze_perfect_ir(self):
        """Test analyzing a well-formed IR with no issues."""
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Calculate the sum of two positive integers and return the result",
                rationale="Provides basic arithmetic functionality for the application",
            ),
            signature=SigClause(
                name="add_numbers",
                parameters=[
                    Parameter(name="a", type_hint="int", description="First positive integer"),
                    Parameter(name="b", type_hint="int", description="Second positive integer"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(
                    predicate="a > 0 and b > 0", rationale="Only positive integers allowed"
                ),
                AssertClause(predicate="result == a + b", rationale="Ensures correct addition"),
                AssertClause(
                    predicate="raises ValueError if a or b is negative", rationale="Error handling"
                ),
            ],
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        assert report is not None
        assert report.overall_quality_score > 0.8  # High quality
        # Should have very few or no suggestions for a well-formed IR
        assert report.summary_stats["total"] <= 1

    def test_detect_weak_parameter_type(self):
        """Test detection of overly broad parameter types."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process",
                parameters=[
                    Parameter(name="data", type_hint="Any", description="Input data"),
                ],
                returns="str",
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        # Should detect weak type
        type_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.TYPE_SAFETY
        ]
        assert len(type_suggestions) > 0
        assert any("Any" in s.title for s in type_suggestions)

    def test_detect_weak_return_type(self):
        """Test detection of overly broad return type."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Get data"),
            signature=SigClause(
                name="get_data",
                parameters=[],
                returns="Any",
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        type_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.TYPE_SAFETY
        ]
        assert len(type_suggestions) > 0
        assert any("return type" in s.title.lower() for s in type_suggestions)

    def test_detect_missing_return_type(self):
        """Test detection of missing return type."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Do something"),
            signature=SigClause(
                name="do_something",
                parameters=[],
                returns=None,
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        completeness_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.COMPLETENESS
        ]
        assert len(completeness_suggestions) > 0
        assert any("return type" in s.title.lower() for s in completeness_suggestions)

    def test_detect_brief_intent(self):
        """Test detection of brief intent summary."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Add"),  # Very brief
            signature=SigClause(name="add", parameters=[], returns="int"),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        doc_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.DOCUMENTATION
        ]
        assert len(doc_suggestions) > 0
        assert any("brief" in s.title.lower() for s in doc_suggestions)

    def test_detect_missing_rationale(self):
        """Test detection of missing intent rationale."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate sum of two numbers"),
            signature=SigClause(name="sum", parameters=[], returns="int"),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        doc_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.DOCUMENTATION
        ]
        assert len(doc_suggestions) > 0
        assert any("rationale" in s.title.lower() for s in doc_suggestions)

    def test_detect_undocumented_parameters(self):
        """Test detection of parameters without descriptions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate result"),
            signature=SigClause(
                name="calculate",
                parameters=[
                    Parameter(name="x", type_hint="int"),  # No description
                    Parameter(name="y", type_hint="int"),  # No description
                ],
                returns="int",
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        doc_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.DOCUMENTATION
        ]
        # Should have suggestions for both undocumented parameters
        param_suggestions = [s for s in doc_suggestions if "lacks description" in s.title]
        assert len(param_suggestions) == 2

    def test_detect_missing_input_validation(self):
        """Test detection of missing input validation assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process user input"),
            signature=SigClause(
                name="process_input",
                parameters=[
                    Parameter(name="user_input", type_hint="str", description="User input"),
                ],
                returns="str",
            ),
            assertions=[],  # No validation!
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        security_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.SECURITY
        ]
        assert len(security_suggestions) > 0
        assert any("validation" in s.title.lower() for s in security_suggestions)

    def test_detect_sql_injection_risk(self):
        """Test detection of potential SQL injection risks."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Execute database query"),
            signature=SigClause(
                name="execute_query",
                parameters=[
                    Parameter(name="sql_query", type_hint="str", description="SQL query string"),
                ],
                returns="list",
            ),
            assertions=[],  # No SQL safety assertions
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        security_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.SECURITY
        ]
        # Should detect SQL-related parameter without protection
        sql_suggestions = [s for s in security_suggestions if "sql" in s.title.lower()]
        assert len(sql_suggestions) > 0
        assert any(s.severity == SuggestionSeverity.CRITICAL for s in sql_suggestions)

    def test_detect_missing_effects(self):
        """Test detection of likely missing effect documentation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Write data to file system"),  # Implies side effects
            signature=SigClause(
                name="write_data",
                parameters=[
                    Parameter(name="data", type_hint="str", description="Data to write"),
                ],
                returns="None",
            ),
            effects=[],  # No effects documented!
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        completeness_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.COMPLETENESS
        ]
        effect_suggestions = [s for s in completeness_suggestions if "effect" in s.title.lower()]
        assert len(effect_suggestions) > 0

    def test_detect_missing_error_handling(self):
        """Test detection of missing error handling documentation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Connect to database"),
            signature=SigClause(
                name="connect_db",
                parameters=[],
                returns="Connection",
            ),
            assertions=[],  # No error handling documented
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        completeness_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.COMPLETENESS
        ]
        error_suggestions = [s for s in completeness_suggestions if "error" in s.title.lower()]
        assert len(error_suggestions) > 0

    def test_detect_too_many_parameters(self):
        """Test detection of functions with too many parameters."""
        params = [Parameter(name=f"param{i}", type_hint="int") for i in range(7)]

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process many inputs"),
            signature=SigClause(
                name="process",
                parameters=params,
                returns="int",
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        best_practice_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.BEST_PRACTICES
        ]
        param_count_suggestions = [
            s for s in best_practice_suggestions if "parameter count" in s.title.lower()
        ]
        assert len(param_count_suggestions) > 0

    def test_detect_weak_assertions(self):
        """Test detection of trivial or weak assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate value"),
            signature=SigClause(
                name="calculate",
                parameters=[
                    Parameter(name="x", type_hint="int", description="Input value"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(predicate="true"),  # Trivial!
                AssertClause(predicate="x > 0"),  # Very simple
            ],
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        best_practice_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.BEST_PRACTICES
        ]
        weak_assertion_suggestions = [
            s for s in best_practice_suggestions if "weak" in s.title.lower()
        ]
        assert len(weak_assertion_suggestions) > 0

    def test_quality_score_calculation(self):
        """Test that quality score reflects IR quality."""
        # Perfect IR
        perfect_ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="A comprehensive description of what this function does",
                rationale="This function exists to provide specific functionality",
            ),
            signature=SigClause(
                name="function",
                parameters=[
                    Parameter(name="x", type_hint="int", description="Well documented parameter"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(predicate="x > 0 and x < 100", rationale="Valid range"),
            ],
            metadata=Metadata(),
        )

        # Poor IR
        poor_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Do stuff"),
            signature=SigClause(
                name="func",
                parameters=[
                    Parameter(name="data", type_hint="Any"),  # No description, weak type
                ],
                returns="Any",  # Weak type
            ),
            assertions=[],  # No validation
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        perfect_report = advisor.analyze(perfect_ir)
        poor_report = advisor.analyze(poor_ir)

        # Perfect IR should have higher score
        assert perfect_report.overall_quality_score > poor_report.overall_quality_score
        assert perfect_report.overall_quality_score > 0.7
        assert poor_report.overall_quality_score < 0.6

    def test_summary_stats(self):
        """Test that summary statistics are calculated correctly."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Short"),  # Low severity doc issue
            signature=SigClause(
                name="func",
                parameters=[
                    Parameter(name="sql", type_hint="str"),  # Critical security issue
                ],
                returns="Any",  # High severity type issue
            ),
            assertions=[],
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        stats = report.summary_stats
        assert stats["total"] > 0
        assert "critical" in stats
        assert "high" in stats
        assert stats["critical"] > 0  # SQL injection risk

    def test_type_suggestion_examples(self):
        """Test that type suggestions include helpful examples."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process",
                parameters=[
                    Parameter(name="data", type_hint="Any"),
                ],
                returns="str",
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        type_suggestions = [
            s for s in report.suggestions if s.category == SuggestionCategory.TYPE_SAFETY
        ]
        assert len(type_suggestions) > 0
        # Should have examples
        assert any(len(s.examples) > 0 for s in type_suggestions)

    def test_suggestion_includes_rationale(self):
        """Test that suggestions include rationale explaining why it matters."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Simple function"),
            signature=SigClause(
                name="simple",
                parameters=[
                    Parameter(name="x", type_hint="Any"),
                ],
                returns="str",
            ),
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        # All suggestions should have rationale
        for suggestion in report.suggestions:
            assert suggestion.rationale is not None
            assert len(suggestion.rationale) > 0

    def test_ir_summary_generation(self):
        """Test that IR summary includes key metrics."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(predicate="a > 0"),
            ],
            effects=[
                EffectClause(description="Logs result"),
            ],
            metadata=Metadata(),
        )

        advisor = AgentAdvisor()
        report = advisor.analyze(ir)

        summary = report.ir_summary
        assert "parameter_count" in summary
        assert summary["parameter_count"] == 2
        assert "assertion_count" in summary
        assert summary["assertion_count"] == 1
        assert "effect_count" in summary
        assert summary["effect_count"] == 1
