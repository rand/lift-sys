"""Integration tests for NLP pipeline with Phase 2 relationship extraction.

Tests the full SemanticAnalysisPipeline including:
- Relationship extraction via spaCy
- Integration with existing entity/modal/constraint detection
- End-to-end semantic analysis
"""

import pytest

# Try to import spaCy, skip tests if not available
try:
    import spacy

    try:
        spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False

from lift_sys.nlp.pipeline import SemanticAnalysisPipeline

pytestmark = pytest.mark.skipif(not SPACY_AVAILABLE, reason="spaCy model not available")


class TestSemanticAnalysisPipelineIntegration:
    """Integration tests for SemanticAnalysisPipeline with relationship extraction."""

    @pytest.fixture
    def pipeline(self):
        """Create and initialize pipeline."""
        return SemanticAnalysisPipeline()

    def test_pipeline_extracts_relationships(self, pipeline):
        """Test that pipeline extracts relationships from text."""
        text = "The function processes the input data and returns the result"

        result = pipeline.analyze(text)

        # Check that relationships key exists
        assert "relationships" in result

        # Should extract at least one relationship
        assert len(result["relationships"]) >= 1

        # Check relationship structure
        rel = result["relationships"][0]
        assert "id" in rel
        assert "from_entity" in rel or "fromEntity" in rel
        assert "to_entity" in rel or "toEntity" in rel
        assert "relationship_type" in rel or "relationshipType" in rel
        assert "confidence" in rel
        assert "description" in rel

    def test_pipeline_extracts_multiple_relationships(self, pipeline):
        """Test extraction of multiple relationships from complex text."""
        text = "The parser reads the code and generates tokens"

        result = pipeline.analyze(text)

        relationships = result["relationships"]
        assert len(relationships) >= 2

        # Should find "reads code" and "generates tokens"
        rel_types = {r.get("relationship_type", r.get("relationshipType")) for r in relationships}
        assert len(rel_types) >= 2

    def test_pipeline_integrates_with_entities(self, pipeline):
        """Test that relationships integrate with entity extraction."""
        text = "The validation function checks the email address"

        result = pipeline.analyze(text)

        # Both entities and relationships should be extracted
        assert "entities" in result
        assert "relationships" in result

        # Should have at least one relationship
        # Note: NER may not find entities in this sentence (validation, function, etc. aren't named entities)
        # Focus is on verifying relationship extraction works
        assert len(result["relationships"]) >= 1

    def test_pipeline_confidence_scores(self, pipeline):
        """Test that relationships have proper confidence scores."""
        text = "The system uses the database"

        result = pipeline.analyze(text)

        for rel in result["relationships"]:
            confidence = rel["confidence"]
            assert 0.0 <= confidence <= 1.0
            assert isinstance(confidence, (int, float))

    def test_pipeline_handles_empty_text(self, pipeline):
        """Test pipeline behavior with empty text."""
        text = ""

        result = pipeline.analyze(text)

        # Should return empty results, not crash
        assert "relationships" in result
        assert result["relationships"] == []

    def test_pipeline_handles_simple_text(self, pipeline):
        """Test pipeline with simple text that has no clear relationships."""
        text = "The function is fast"

        result = pipeline.analyze(text)

        # Should not crash, may have 0-1 relationships
        assert "relationships" in result
        assert len(result["relationships"]) <= 1

    def test_pipeline_dependency_relationship(self, pipeline):
        """Test extraction of dependency relationships."""
        text = "The module depends on the library"

        result = pipeline.analyze(text)

        relationships = result["relationships"]
        assert len(relationships) >= 1

        # Should find DEPENDS_ON relationship
        dep_rels = [
            r
            for r in relationships
            if r.get("relationship_type", r.get("relationshipType")) == "DEPENDS_ON"
        ]
        assert len(dep_rels) >= 1

    def test_pipeline_writes_to_relationship(self, pipeline):
        """Test extraction of WRITES_TO relationships."""
        text = "The process saves data to the database"

        result = pipeline.analyze(text)

        relationships = result["relationships"]

        # Should find WRITES_TO relationship
        writes_rels = [
            r
            for r in relationships
            if r.get("relationship_type", r.get("relationshipType")) == "WRITES_TO"
        ]
        assert len(writes_rels) >= 1

    def test_pipeline_multiple_components(self, pipeline):
        """Test that all pipeline components work together."""
        text = "The function must validate input and should return true if valid"

        result = pipeline.analyze(text)

        # Should extract all component types
        assert "entities" in result
        assert "relationships" in result
        assert "modalOperators" in result
        assert "constraints" in result
        assert "confidenceScores" in result

        # Should have some results
        assert len(result["entities"]) >= 1 or len(result["relationships"]) >= 1
        assert len(result["modalOperators"]) >= 1  # "must" and "should"

    def test_pipeline_conditional_relationship(self, pipeline):
        """Test extraction of conditional relationships."""
        text = "If validation succeeds then save the data"

        result = pipeline.analyze(text)

        relationships = result["relationships"]

        # Should extract CAUSES relationship from conditional
        causal_rels = [
            r
            for r in relationships
            if r.get("relationship_type", r.get("relationshipType")) == "CAUSES"
        ]
        assert len(causal_rels) >= 1


class TestRealWorldExamples:
    """Integration tests with realistic specification examples."""

    @pytest.fixture
    def pipeline(self):
        """Create and initialize pipeline."""
        return SemanticAnalysisPipeline()

    def test_email_validation_spec(self, pipeline):
        """Test extraction from email validation specification."""
        text = """
        The function validates an email address.
        It checks that the email contains an @ symbol and a dot.
        The function must return true if the email is valid.
        """

        result = pipeline.analyze(text)

        # Should extract relationships
        assert len(result["relationships"]) >= 1

        # Should have modal operators
        assert len(result["modalOperators"]) >= 1

        # Should detect validation operation
        operates_on = [
            r
            for r in result["relationships"]
            if r.get("relationship_type", r.get("relationshipType")) == "OPERATES_ON"
        ]
        assert len(operates_on) >= 1

    def test_data_processing_spec(self, pipeline):
        """Test extraction from data processing specification."""
        text = """
        The system reads input from a file.
        It processes the data and generates a report.
        The report is saved to the database.
        """

        result = pipeline.analyze(text)

        # Should extract multiple relationships
        assert len(result["relationships"]) >= 3

        # Should have different relationship types
        rel_types = {
            r.get("relationship_type", r.get("relationshipType")) for r in result["relationships"]
        }
        assert len(rel_types) >= 2

    def test_workflow_spec(self, pipeline):
        """Test extraction from workflow specification."""
        text = """
        The application depends on the configuration service.
        It validates user input before processing.
        After processing, it sends the results to the notification service.
        """

        result = pipeline.analyze(text)

        # Should extract relationships
        relationships = result["relationships"]
        assert len(relationships) >= 2

        # Should have dependency relationship
        dep_rels = [
            r
            for r in relationships
            if r.get("relationship_type", r.get("relationshipType")) == "DEPENDS_ON"
        ]
        assert len(dep_rels) >= 1

    def test_complex_processing_spec(self, pipeline):
        """Test extraction from complex processing specification."""
        text = """
        The process_data function must validate the input data.
        The function transforms the data using the parser.
        The function stores the results in the database.
        The function should return the number of records processed.
        """

        result = pipeline.analyze(text)

        # Should extract multiple relationships (at least 2)
        # Note: Actual extraction depends on spaCy's parsing
        assert len(result["relationships"]) >= 2

        # Should have modal operators
        assert len(result["modalOperators"]) >= 2  # "must" and "should"

        # Should have various relationship types
        rel_types = {
            r.get("relationship_type", r.get("relationshipType")) for r in result["relationships"]
        }
        assert "OPERATES_ON" in rel_types or "USES" in rel_types or "TRANSFORMS" in rel_types

    def test_api_spec(self, pipeline):
        """Test extraction from API specification."""
        text = """
        The API endpoint receives a JSON payload.
        It validates the request and extracts the user ID.
        The endpoint queries the database for user information.
        It returns a JSON response with the user data.
        """

        result = pipeline.analyze(text)

        # Should extract relationships
        relationships = result["relationships"]
        assert len(relationships) >= 3

        # Check for various operations
        rel_types = {r.get("relationship_type", r.get("relationshipType")) for r in relationships}
        # Should have data flow operations
        assert any(
            t in rel_types for t in ["READS_FROM", "WRITES_TO", "RETURNS", "OPERATES_ON", "USES"]
        )
