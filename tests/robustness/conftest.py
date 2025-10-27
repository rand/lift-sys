"""Shared pytest fixtures for robustness tests."""

import json
from pathlib import Path

import pytest

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.robustness import (
    EquivalenceChecker,
    IRVariantGenerator,
    ParaphraseGenerator,
    SensitivityAnalyzer,
)


@pytest.fixture
def paraphrase_generator():
    """Paraphrase generator for testing.

    Uses enhanced configuration:
    - max_variants=10 (allow up to 10 paraphrases)
    - min_diversity=0.2 (lowered from 0.3 to allow more variants)
    """
    return ParaphraseGenerator(max_variants=10, min_diversity=0.2)


@pytest.fixture
def ir_variant_generator():
    """IR variant generator for testing."""
    return IRVariantGenerator()


@pytest.fixture
def equivalence_checker():
    """Equivalence checker with naming normalization."""
    return EquivalenceChecker(normalize_naming=True)


@pytest.fixture
def sensitivity_analyzer():
    """Sensitivity analyzer for robustness testing."""
    return SensitivityAnalyzer(normalize_naming=True)


@pytest.fixture
def sample_prompts():
    """Sample prompts for robustness testing."""
    return [
        "Create a function that sorts a list of numbers",
        "Write a function to validate email addresses",
        "Implement a function that filters even numbers from a list",
        "Create a function that calculates the factorial of a number",
        "Write a function to reverse a string",
    ]


@pytest.fixture
def sample_ir():
    """Sample IR for testing."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Sort a list of numbers"),
        signature=SigClause(
            name="sort_numbers",
            parameters=[Parameter(name="numbers", type_hint="list[int]")],
            returns="list[int]",
        ),
        effects=[],  # No effects for simple IR
        assertions=[AssertClause(predicate="result is sorted in ascending order")],
    )


@pytest.fixture
def complex_ir():
    """Complex IR with multiple effects and assertions."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Validate and process user data"),
        signature=SigClause(
            name="process_user_data",
            parameters=[
                Parameter(name="user_data", type_hint="dict[str, Any]"),
                Parameter(name="strict_mode", type_hint="bool", description="Defaults to False"),
            ],
            returns="dict[str, Any]",
        ),
        effects=[
            EffectClause(description="Validate email format"),
            EffectClause(description="Check age is positive integer"),
            EffectClause(description="Normalize name to title case"),
            EffectClause(description="Remove whitespace from fields"),
        ],
        assertions=[
            AssertClause(predicate="email matches regex pattern"),
            AssertClause(predicate="age > 0"),
            AssertClause(predicate="all required fields present"),
        ],
    )


@pytest.fixture
def test_fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_test_prompts(test_fixtures_dir):
    """Load test prompts from fixtures."""

    def _load():
        prompts_file = test_fixtures_dir / "prompts.json"
        if prompts_file.exists():
            with open(prompts_file) as f:
                return json.load(f)
        return []

    return _load


@pytest.fixture
def load_test_irs(test_fixtures_dir):
    """Load test IRs from fixtures."""

    def _load():
        irs_file = test_fixtures_dir / "irs.json"
        if irs_file.exists():
            with open(irs_file) as f:
                data = json.load(f)
                # Convert JSON to IR objects using from_dict to properly deserialize nested objects
                return [IntermediateRepresentation.from_dict(ir_data) for ir_data in data]
        return []

    return _load


@pytest.fixture
def load_expected_results(test_fixtures_dir):
    """Load expected robustness results from fixtures."""

    def _load():
        results_file = test_fixtures_dir / "expected_results.json"
        if results_file.exists():
            with open(results_file) as f:
                return json.load(f)
        return {}

    return _load


@pytest.fixture
def robustness_threshold():
    """Target robustness threshold (97% = <3% sensitivity)."""
    return 0.97


@pytest.fixture
def warning_threshold():
    """Warning threshold for robustness (90% = 10% sensitivity)."""
    return 0.90


@pytest.fixture
def failure_threshold():
    """Failure threshold for robustness (80% = 20% sensitivity)."""
    return 0.80
