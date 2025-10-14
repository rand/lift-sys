"""Analysis package for IR quality and improvement suggestions."""

from .agent_advisor import (
    AgentAdvisor,
    AnalysisReport,
    Suggestion,
    SuggestionCategory,
    SuggestionSeverity,
)

__all__ = [
    "AgentAdvisor",
    "AnalysisReport",
    "Suggestion",
    "SuggestionCategory",
    "SuggestionSeverity",
]
