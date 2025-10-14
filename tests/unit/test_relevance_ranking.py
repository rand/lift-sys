"""Tests for symbol relevance ranking."""

from __future__ import annotations

from lift_sys.codegen.semantic_context import (
    FunctionInfo,
    RelevanceScore,
    TypeInfo,
    compute_relevance,
)


class TestRelevanceScore:
    """Tests for RelevanceScore dataclass."""

    def test_create_relevance_score(self):
        """Test creating a relevance score."""
        score = RelevanceScore(
            total=0.85,
            keyword_match=1.0,
            semantic_similarity=0.8,
            usage_frequency=0.0,
        )

        assert score.total == 0.85
        assert score.keyword_match == 1.0
        assert score.semantic_similarity == 0.8
        assert score.usage_frequency == 0.0


class TestComputeRelevance:
    """Tests for compute_relevance function."""

    def test_exact_keyword_match(self):
        """Test exact keyword match gives highest keyword score."""
        score = compute_relevance(
            symbol_name="validate_email",
            symbol_type="function",
            keywords=["validate_email"],
            intent_summary="validate email addresses",
        )

        assert score.keyword_match == 1.0
        assert score.total > 0.6  # At least 60% from keyword match

    def test_substring_keyword_match(self):
        """Test substring keyword match gives high score."""
        score = compute_relevance(
            symbol_name="validate_email",
            symbol_type="function",
            keywords=["email"],
            intent_summary="check email format",
        )

        assert score.keyword_match == 0.7
        assert score.total >= 0.42  # 0.7 * 0.6

    def test_reverse_substring_match(self):
        """Test reverse substring match (symbol in keyword)."""
        score = compute_relevance(
            symbol_name="email",
            symbol_type="type",
            keywords=["email_validation"],
            intent_summary="validate email addresses",
        )

        assert score.keyword_match == 0.5
        assert score.total >= 0.3  # 0.5 * 0.6

    def test_partial_word_match(self):
        """Test partial word match in underscore-separated names."""
        score = compute_relevance(
            symbol_name="user_validation_helper",
            symbol_type="function",
            keywords=["validate"],
            intent_summary="validate user input",
        )

        # "validate" matches part of "validation"
        assert score.keyword_match >= 0.4

    def test_no_keyword_match(self):
        """Test no keyword match gives zero keyword score."""
        score = compute_relevance(
            symbol_name="calculate_tax",
            symbol_type="function",
            keywords=["email"],
            intent_summary="send email",
        )

        assert score.keyword_match == 0.0

    def test_semantic_similarity_validation_pattern(self):
        """Test semantic similarity for validation pattern."""
        score = compute_relevance(
            symbol_name="validate_input",
            symbol_type="function",
            keywords=["check"],
            intent_summary="validate user input",
        )

        # Should match validation pattern
        assert score.semantic_similarity == 0.8
        # Total includes semantic: 0 * 0.6 + 0.8 * 0.3 = 0.24
        # But keyword "check" might partially match "validate"
        assert score.total >= 0.24

    def test_semantic_similarity_calculation_pattern(self):
        """Test semantic similarity for calculation pattern."""
        score = compute_relevance(
            symbol_name="calculate_total",
            symbol_type="function",
            keywords=["price"],
            intent_summary="calculate price with tax",
        )

        # Should match calculation pattern
        assert score.semantic_similarity == 0.8

    def test_semantic_similarity_creation_pattern(self):
        """Test semantic similarity for creation pattern."""
        score = compute_relevance(
            symbol_name="create_user",
            symbol_type="function",
            keywords=["user"],
            intent_summary="create new user account",
        )

        # Should match creation pattern
        assert score.semantic_similarity == 0.8

    def test_semantic_similarity_conversion_pattern(self):
        """Test semantic similarity for conversion pattern."""
        score = compute_relevance(
            symbol_name="to_json",
            symbol_type="function",
            keywords=["json"],
            intent_summary="convert object to JSON",
        )

        # Should match conversion pattern
        assert score.semantic_similarity == 0.8

    def test_semantic_similarity_retrieval_pattern(self):
        """Test semantic similarity for retrieval pattern."""
        score = compute_relevance(
            symbol_name="get_user",
            symbol_type="function",
            keywords=["user"],
            intent_summary="retrieve user from database",
        )

        # Should match retrieval pattern
        assert score.semantic_similarity == 0.8

    def test_semantic_similarity_storage_pattern(self):
        """Test semantic similarity for storage pattern."""
        score = compute_relevance(
            symbol_name="save_config",
            symbol_type="function",
            keywords=["config"],
            intent_summary="store configuration to file",
        )

        # Should match storage pattern
        assert score.semantic_similarity == 0.8

    def test_semantic_similarity_parsing_pattern(self):
        """Test semantic similarity for parsing pattern."""
        score = compute_relevance(
            symbol_name="parse_xml",
            symbol_type="function",
            keywords=["xml"],
            intent_summary="parse XML document",
        )

        # Should match parsing pattern
        assert score.semantic_similarity == 0.8

    def test_semantic_similarity_formatting_pattern(self):
        """Test semantic similarity for formatting pattern."""
        score = compute_relevance(
            symbol_name="format_date",
            symbol_type="function",
            keywords=["date"],
            intent_summary="format date as ISO string",
        )

        # Should match formatting pattern
        assert score.semantic_similarity == 0.8

    def test_no_semantic_similarity(self):
        """Test no semantic similarity when patterns don't match."""
        score = compute_relevance(
            symbol_name="random_function",
            symbol_type="function",
            keywords=["data"],
            intent_summary="process data",
        )

        # No clear pattern match
        assert score.semantic_similarity == 0.0

    def test_combined_high_score(self):
        """Test high combined score with both keyword and semantic match."""
        score = compute_relevance(
            symbol_name="validate_email",
            symbol_type="function",
            keywords=["email", "validate"],
            intent_summary="validate email address format",
        )

        # Should have both keyword match and semantic similarity
        assert score.keyword_match >= 0.7
        assert score.semantic_similarity == 0.8
        # Total: ~0.7*0.6 + 0.8*0.3 = 0.42 + 0.24 = 0.66
        assert score.total >= 0.6

    def test_usage_frequency_placeholder(self):
        """Test usage frequency is always zero (placeholder)."""
        score = compute_relevance(
            symbol_name="validate_email",
            symbol_type="function",
            keywords=["email"],
            intent_summary="validate email",
        )

        # Usage frequency not implemented yet
        assert score.usage_frequency == 0.0

    def test_weighted_combination(self):
        """Test weighted combination of scores."""
        # Create scenario with known scores
        score = compute_relevance(
            symbol_name="check_valid",
            symbol_type="function",
            keywords=["check"],
            intent_summary="validate input data",
        )

        # check matches check_valid: keyword_match = 0.7
        # "validate" in intent, "check" in name: semantic = 0.8
        # usage_frequency = 0.0
        expected_total = (0.7 * 0.6) + (0.8 * 0.3) + (0.0 * 0.1)
        assert abs(score.total - expected_total) < 0.01

    def test_type_vs_function_symbol_type(self):
        """Test that symbol_type parameter is accepted but doesn't affect score."""
        score_type = compute_relevance(
            symbol_name="EmailValidator",
            symbol_type="type",
            keywords=["email"],
            intent_summary="validate email",
        )

        score_function = compute_relevance(
            symbol_name="EmailValidator",
            symbol_type="function",
            keywords=["email"],
            intent_summary="validate email",
        )

        # Symbol type doesn't affect score (yet)
        assert score_type.total == score_function.total

    def test_multiple_keywords_best_match_wins(self):
        """Test that best keyword match is used."""
        score = compute_relevance(
            symbol_name="validate_email",
            symbol_type="function",
            keywords=["user", "email", "validate_email"],
            intent_summary="validate user email",
        )

        # Should match "validate_email" exactly (1.0), not just "email" (0.7)
        assert score.keyword_match == 1.0

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        score_lower = compute_relevance(
            symbol_name="validateemail",
            symbol_type="function",
            keywords=["email"],
            intent_summary="validate email",
        )

        score_upper = compute_relevance(
            symbol_name="ValidateEmail",
            symbol_type="function",
            keywords=["EMAIL"],
            intent_summary="VALIDATE EMAIL",
        )

        # Should produce similar scores
        assert abs(score_lower.total - score_upper.total) < 0.1


class TestSymbolRanking:
    """Tests for symbol ranking using relevance scores."""

    def test_rank_by_relevance(self):
        """Test that symbols are ranked correctly by relevance."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider

        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(repository_path=repo_path, language="python", cache_enabled=False)
        provider = LSPSemanticContextProvider(config)

        # Create symbols with varying relevance
        symbols = [
            FunctionInfo(
                name="random_function",
                module="utils.py",
                signature="random_function()",
                description="Unrelated function",
            ),
            FunctionInfo(
                name="validate_email",
                module="validators.py",
                signature="validate_email(email: str) -> bool",
                description="Exact match function",
            ),
            FunctionInfo(
                name="check_email_format",
                module="validators.py",
                signature="check_email_format(email: str) -> bool",
                description="Partial match function",
            ),
        ]

        keywords = ["email", "validate"]
        intent = "validate email address format"

        ranked = provider._rank_symbols(symbols, keywords, intent)

        # validate_email should be first (exact match + semantic)
        assert ranked[0].name == "validate_email"
        # check_email_format should be second (partial match + semantic)
        assert ranked[1].name == "check_email_format"
        # random_function should be last (no match)
        assert ranked[2].name == "random_function"

        temp_dir.cleanup()

    def test_rank_empty_list(self):
        """Test ranking empty symbol list."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider

        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(repository_path=repo_path, language="python", cache_enabled=False)
        provider = LSPSemanticContextProvider(config)

        ranked = provider._rank_symbols([], ["test"], "test intent")

        assert ranked == []

        temp_dir.cleanup()

    def test_rank_types_vs_functions(self):
        """Test ranking works for both types and functions."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider

        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        config = LSPConfig(repository_path=repo_path, language="python", cache_enabled=False)
        provider = LSPSemanticContextProvider(config)

        types = [
            TypeInfo(
                name="User",
                module="models.py",
                description="User model",
            ),
            TypeInfo(
                name="UserValidator",
                module="validators.py",
                description="User validator",
            ),
        ]

        functions = [
            FunctionInfo(
                name="get_user",
                module="services.py",
                signature="get_user(id: int) -> User",
                description="Get user",
            ),
            FunctionInfo(
                name="validate_user",
                module="validators.py",
                signature="validate_user(user: User) -> bool",
                description="Validate user",
            ),
        ]

        keywords = ["user", "validate"]
        intent = "validate user data"

        ranked_types = provider._rank_symbols(types, keywords, intent)
        ranked_functions = provider._rank_symbols(functions, keywords, intent)

        # UserValidator should be first for types (matches both keywords + semantic)
        assert ranked_types[0].name == "UserValidator"

        # validate_user should be first for functions (matches both + semantic)
        assert ranked_functions[0].name == "validate_user"

        temp_dir.cleanup()
