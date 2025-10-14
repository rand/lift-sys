"""Tests for LSP file discovery and relevance scoring."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider


class TestFileRelevanceScoring:
    """Tests for file relevance scoring algorithm."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Create test file structure
        self.files = {
            "lift_sys/api/server.py": "",
            "lift_sys/api/routes/generate.py": "",
            "lift_sys/models/user.py": "",
            "lift_sys/services/email_service.py": "",
            "lift_sys/utils/validation.py": "",
            "lift_sys/core/engine.py": "",
            "tests/test_api.py": "",
            "tests/integration/test_endpoints.py": "",
            "lift_sys/__init__.py": "",
            "experiments/prototype.py": "",
        }

        for file_path, content in self.files.items():
            full_path = self.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        self.config = LSPConfig(repository_path=self.repo_path, language="python")
        self.provider = LSPSemanticContextProvider(self.config)

    def teardown_method(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_exact_keyword_match_in_filename(self):
        """Test high score for exact keyword match in filename."""
        file_path = self.repo_path / "lift_sys/services/email_service.py"
        keywords = ["email"]
        intent = "Send email to user"

        score = self.provider._score_file_relevance(file_path, keywords, intent)

        # Should have high score (0.5 for exact match + bonuses)
        assert score >= 0.5

    def test_partial_keyword_match_in_filename(self):
        """Test moderate score for partial keyword match."""
        file_path = self.repo_path / "lift_sys/services/email_service.py"
        keywords = ["mail"]  # Partial match (matches "email")
        intent = "Send email to user"

        score = self.provider._score_file_relevance(file_path, keywords, intent)

        # "mail" matches "email" substring, so should get good score
        assert score >= 0.3

    def test_keyword_match_in_path(self):
        """Test scoring for keyword in path components."""
        file_path = self.repo_path / "lift_sys/api/routes/generate.py"
        keywords = ["generate"]
        intent = "Generate code from IR"

        score = self.provider._score_file_relevance(file_path, keywords, intent)

        # Should match on filename
        assert score > 0.0

    def test_domain_heuristic_api(self):
        """Test domain-specific heuristic for API intent."""
        file_path = self.repo_path / "lift_sys/api/server.py"
        keywords = ["endpoint"]
        intent = "Create new API endpoint for users"

        score = self.provider._score_file_relevance(file_path, keywords, intent)

        # Should get bonus for API domain match
        assert score > 0.0

    def test_domain_heuristic_model(self):
        """Test domain-specific heuristic for model intent."""
        file_path = self.repo_path / "lift_sys/models/user.py"
        keywords = ["user"]
        intent = "Define user model with validation"

        score = self.provider._score_file_relevance(file_path, keywords, intent)

        # Should get bonus for model domain match
        assert score >= 0.5  # Exact match on "user"

    def test_preferred_directory_bonus(self):
        """Test bonus for files in preferred directories."""
        core_file = self.repo_path / "lift_sys/core/engine.py"
        random_file = self.repo_path / "lift_sys/random/helper.py"

        # Create random_file
        random_file.parent.mkdir(parents=True, exist_ok=True)
        random_file.write_text("")

        keywords = ["engine", "helper"]
        intent = "Process data"

        core_score = self.provider._score_file_relevance(core_file, ["engine"], intent)
        random_score = self.provider._score_file_relevance(random_file, ["helper"], intent)

        # Core should have higher score due to preferred directory bonus
        assert core_score > random_score

    def test_test_file_penalty(self):
        """Test penalty for test files when intent doesn't mention testing."""
        test_file = self.repo_path / "tests/test_api.py"
        prod_file = self.repo_path / "lift_sys/api/server.py"

        keywords = ["api"]
        intent = "Create API endpoint"  # No mention of testing

        test_score = self.provider._score_file_relevance(test_file, keywords, intent)
        prod_score = self.provider._score_file_relevance(prod_file, keywords, intent)

        # Production file should score higher
        assert prod_score > test_score

    def test_test_file_no_penalty_when_testing_mentioned(self):
        """Test no penalty for test files when intent mentions testing."""
        test_file = self.repo_path / "tests/test_api.py"

        keywords = ["api", "test"]
        intent = "Write test for API endpoint"

        score = self.provider._score_file_relevance(test_file, keywords, intent)

        # Should not be heavily penalized
        assert score > 0.3

    def test_init_file_penalty(self):
        """Test penalty for __init__.py files."""
        init_file = self.repo_path / "lift_sys/__init__.py"
        regular_file = self.repo_path / "lift_sys/api/server.py"

        keywords = ["lift_sys"]
        intent = "Work with lift_sys code"

        init_score = self.provider._score_file_relevance(init_file, keywords, intent)
        regular_score = self.provider._score_file_relevance(regular_file, keywords, intent)

        # Regular file should score higher
        assert regular_score > init_score

    def test_score_bounded_to_one(self):
        """Test that score never exceeds 1.0."""
        # Create a file that would score very high
        perfect_file = self.repo_path / "lift_sys/core/email.py"
        perfect_file.parent.mkdir(parents=True, exist_ok=True)
        perfect_file.write_text("")

        keywords = ["email"]
        intent = "Email service in core module"

        score = self.provider._score_file_relevance(perfect_file, keywords, intent)

        # Score should be capped at 1.0
        assert score <= 1.0


class TestFileDiscovery:
    """Tests for multi-file discovery."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Create test file structure with varied relevance
        self.files = {
            "lift_sys/api/server.py": "",
            "lift_sys/api/routes/users.py": "",
            "lift_sys/api/routes/auth.py": "",
            "lift_sys/models/user.py": "",
            "lift_sys/services/auth_service.py": "",
            "lift_sys/utils/validation.py": "",
            "tests/test_auth.py": "",
            "experiments/auth_prototype.py": "",
        }

        for file_path, content in self.files.items():
            full_path = self.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        self.config = LSPConfig(repository_path=self.repo_path, language="python")
        self.provider = LSPSemanticContextProvider(self.config)

    def teardown_method(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_find_relevant_files_returns_multiple(self):
        """Test that discovery returns multiple relevant files."""
        keywords = ["auth"]
        intent = "Implement authentication system"

        files = self.provider._find_relevant_files(keywords, intent, limit=3)

        # Should return up to 3 files
        assert 1 <= len(files) <= 3

    def test_find_relevant_files_sorted_by_relevance(self):
        """Test that files are sorted by relevance score."""
        keywords = ["auth"]
        intent = "Implement authentication system"

        files = self.provider._find_relevant_files(keywords, intent, limit=3)

        # Calculate scores to verify sorting
        scores = [self.provider._score_file_relevance(f, keywords, intent) for f in files]

        # Should be in descending order
        assert scores == sorted(scores, reverse=True)

    def test_find_relevant_files_filters_zero_scores(self):
        """Test that files with zero relevance are filtered out."""
        keywords = ["nonexistent_keyword_xyz"]
        intent = "Work with nonexistent functionality"

        files = self.provider._find_relevant_files(keywords, intent, limit=3)

        # Should filter out files with score 0
        # All files should have at least some relevance if returned
        for f in files:
            score = self.provider._score_file_relevance(f, keywords, intent)
            assert score > 0.0

    def test_find_relevant_files_respects_limit(self):
        """Test that limit parameter is respected."""
        keywords = ["lift_sys"]  # Broad keyword
        intent = "Work with lift_sys code"

        files_1 = self.provider._find_relevant_files(keywords, intent, limit=1)
        files_3 = self.provider._find_relevant_files(keywords, intent, limit=3)

        assert len(files_1) <= 1
        assert len(files_3) <= 3

    def test_find_relevant_files_returns_most_relevant(self):
        """Test that most relevant files are selected."""
        keywords = ["user"]
        intent = "Work with user model"

        files = self.provider._find_relevant_files(keywords, intent, limit=2)

        # Should include user.py and users.py as they're most relevant
        file_names = [f.name for f in files]
        assert "user.py" in file_names or "users.py" in file_names

    def test_find_relevant_files_empty_repo(self):
        """Test behavior with empty repository."""
        empty_dir = TemporaryDirectory()
        empty_path = Path(empty_dir.name)

        config = LSPConfig(repository_path=empty_path, language="python")
        provider = LSPSemanticContextProvider(config)

        keywords = ["test"]
        intent = "Test intent"

        files = provider._find_relevant_files(keywords, intent, limit=3)

        # Should return empty list
        assert files == []

        empty_dir.cleanup()

    def test_find_relevant_files_excludes_filtered_dirs(self):
        """Test that excluded directories are filtered out."""
        # Create files in excluded directories
        excluded_files = {
            ".venv/lib/site-packages/test.py": "",
            "__pycache__/cached.py": "",
            "node_modules/package/index.py": "",
            ".git/hooks/pre-commit.py": "",
        }

        for file_path, content in excluded_files.items():
            full_path = self.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        keywords = ["test"]
        intent = "Find test files"

        files = self.provider._find_relevant_files(keywords, intent, limit=10)

        # Should not include any files from excluded directories
        for f in files:
            assert not any(
                excluded in f.parts for excluded in ["__pycache__", ".venv", "node_modules", ".git"]
            )

    def test_find_relevant_files_with_specific_intent(self):
        """Test file discovery with domain-specific intent."""
        keywords = ["api", "user"]
        intent = "Create API endpoint for user management"

        files = self.provider._find_relevant_files(keywords, intent, limit=3)

        # Should prioritize API-related files
        file_paths = [str(f) for f in files]
        api_files = [p for p in file_paths if "api" in p.lower()]

        # At least one API file should be in results
        assert len(api_files) > 0


class TestKeywordExtraction:
    """Tests for keyword extraction from intent."""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        config = LSPConfig(repository_path=Path("/tmp"), language="python", cache_enabled=False)
        provider = LSPSemanticContextProvider(config)

        intent = "validate email address format"
        keywords = provider._extract_keywords(intent)

        # Should extract meaningful keywords
        assert "validate" in keywords
        assert "email" in keywords
        assert "address" in keywords
        assert "format" in keywords

    def test_extract_keywords_filters_short_words(self):
        """Test that short words are filtered out."""
        config = LSPConfig(repository_path=Path("/tmp"), language="python", cache_enabled=False)
        provider = LSPSemanticContextProvider(config)

        intent = "get a new id for the user"
        keywords = provider._extract_keywords(intent)

        # Short words should be filtered
        assert "a" not in keywords
        assert "id" not in keywords
        # But meaningful words should remain
        assert "user" in keywords

    def test_extract_keywords_filters_common_words(self):
        """Test that common stopwords are filtered."""
        config = LSPConfig(repository_path=Path("/tmp"), language="python", cache_enabled=False)
        provider = LSPSemanticContextProvider(config)

        intent = "validate the data for that user with email"
        keywords = provider._extract_keywords(intent)

        # Stopwords should be filtered
        assert "the" not in keywords
        assert "for" not in keywords
        assert "that" not in keywords
        assert "with" not in keywords
