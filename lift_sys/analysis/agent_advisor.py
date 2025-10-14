"""Proactive IR analysis and improvement suggestions.

The AgentAdvisor analyzes intermediate representations and provides
actionable recommendations for improving specification quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..ir.models import IntermediateRepresentation, Parameter


class SuggestionCategory(str, Enum):
    """Category of improvement suggestion."""

    TYPE_SAFETY = "type_safety"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    ERROR_HANDLING = "error_handling"
    COMPLETENESS = "completeness"
    BEST_PRACTICES = "best_practices"


class SuggestionSeverity(str, Enum):
    """Severity level of suggestion."""

    INFO = "info"  # Nice to have
    LOW = "low"  # Minor improvement
    MEDIUM = "medium"  # Recommended
    HIGH = "high"  # Important
    CRITICAL = "critical"  # Should be addressed


@dataclass
class Suggestion:
    """A single improvement suggestion for an IR."""

    category: SuggestionCategory
    severity: SuggestionSeverity
    title: str
    description: str
    location: str  # Path in IR (e.g., "signature.parameters[0]")
    current_value: str | None = None
    suggested_value: str | None = None
    rationale: str | None = None
    examples: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "rationale": self.rationale,
            "examples": self.examples,
            "references": self.references,
        }


@dataclass
class AnalysisReport:
    """Complete analysis report for an IR."""

    ir_summary: dict[str, Any]
    suggestions: list[Suggestion]
    summary_stats: dict[str, int]
    overall_quality_score: float  # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "ir_summary": self.ir_summary,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "summary_stats": self.summary_stats,
            "overall_quality_score": self.overall_quality_score,
        }


class AgentAdvisor:
    """Proactive analyzer for intermediate representations."""

    def __init__(self):
        """Initialize the advisor."""
        self._weak_type_patterns = [
            "Any",
            "object",
            "unknown",
            "mixed",
            "*",
        ]

    def analyze(self, ir: IntermediateRepresentation) -> AnalysisReport:
        """
        Perform comprehensive analysis of an IR.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            Complete analysis report with suggestions
        """
        suggestions = []

        # Run all detectors
        suggestions.extend(self._detect_type_issues(ir))
        suggestions.extend(self._detect_documentation_issues(ir))
        suggestions.extend(self._detect_security_concerns(ir))
        suggestions.extend(self._detect_completeness_issues(ir))
        suggestions.extend(self._detect_best_practice_violations(ir))

        # Calculate summary statistics
        summary_stats = self._calculate_stats(suggestions)

        # Calculate overall quality score
        quality_score = self._calculate_quality_score(ir, suggestions)

        # Build IR summary
        ir_summary = {
            "intent_length": len(ir.intent.summary),
            "parameter_count": len(ir.signature.parameters),
            "assertion_count": len(ir.assertions),
            "effect_count": len(ir.effects),
            "has_rationale": ir.intent.rationale is not None,
            "has_return_type": ir.signature.returns is not None,
        }

        return AnalysisReport(
            ir_summary=ir_summary,
            suggestions=suggestions,
            summary_stats=summary_stats,
            overall_quality_score=quality_score,
        )

    def _detect_type_issues(self, ir: IntermediateRepresentation) -> list[Suggestion]:
        """Detect type safety and specificity issues."""
        suggestions = []

        # Check parameter types
        for i, param in enumerate(ir.signature.parameters):
            if self._is_weak_type(param.type_hint):
                suggestions.append(
                    Suggestion(
                        category=SuggestionCategory.TYPE_SAFETY,
                        severity=SuggestionSeverity.HIGH,
                        title=f"Overly broad type '{param.type_hint}' for parameter '{param.name}'",
                        description=f"Parameter '{param.name}' uses the generic type '{param.type_hint}', which reduces type safety and makes the specification less precise.",
                        location=f"signature.parameters[{i}].type_hint",
                        current_value=param.type_hint,
                        suggested_value=self._suggest_specific_type(param),
                        rationale="Specific types enable better validation, error detection, and code generation. They also make the specification more understandable.",
                        examples=[
                            "Instead of 'Any', use 'int' if the parameter is always a number",
                            "Instead of 'object', use 'dict[str, int]' for a dictionary with string keys and integer values",
                            "Instead of 'mixed', use a union type like 'int | str' if the parameter can be multiple types",
                        ],
                    )
                )

        # Check return type
        if ir.signature.returns and self._is_weak_type(ir.signature.returns):
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.TYPE_SAFETY,
                    severity=SuggestionSeverity.HIGH,
                    title=f"Overly broad return type '{ir.signature.returns}'",
                    description=f"Function returns '{ir.signature.returns}', which is too generic and reduces type safety.",
                    location="signature.returns",
                    current_value=ir.signature.returns,
                    suggested_value="Specify a more precise return type based on the function's purpose",
                    rationale="Specific return types help callers understand what to expect and enable compile-time checks.",
                    examples=[
                        "For a function returning a user object: 'dict[str, Any]' or 'User'",
                        "For a function returning a list of numbers: 'list[int]' or 'list[float]'",
                        "For a function that may fail: 'Result[T, Error]' or 'T | None'",
                    ],
                )
            )

        # Check for missing return type
        if ir.signature.returns is None:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.COMPLETENESS,
                    severity=SuggestionSeverity.MEDIUM,
                    title="Missing return type",
                    description="The function signature does not specify a return type.",
                    location="signature.returns",
                    current_value=None,
                    suggested_value="Specify the return type based on what the function produces",
                    rationale="Explicit return types improve clarity and enable type checking.",
                    examples=[
                        "For functions that return nothing: 'None'",
                        "For functions that return a value: specify the type (e.g., 'int', 'str', 'list[dict]')",
                    ],
                )
            )

        return suggestions

    def _detect_documentation_issues(self, ir: IntermediateRepresentation) -> list[Suggestion]:
        """Detect documentation completeness and quality issues."""
        suggestions = []

        # Check intent summary length
        if len(ir.intent.summary) < 20:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.DOCUMENTATION,
                    severity=SuggestionSeverity.LOW,
                    title="Brief intent summary",
                    description="The intent summary is very brief, which may not fully capture the function's purpose.",
                    location="intent.summary",
                    current_value=ir.intent.summary,
                    suggested_value="Expand the summary to include more context",
                    rationale="Detailed summaries help users understand the function's purpose, behavior, and use cases.",
                    examples=[
                        "Instead of: 'Add numbers'",
                        "Use: 'Calculates the sum of two integers and returns the result. Handles positive and negative numbers.'",
                    ],
                )
            )

        # Check for missing rationale
        if not ir.intent.rationale:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.DOCUMENTATION,
                    severity=SuggestionSeverity.LOW,
                    title="Missing intent rationale",
                    description="No rationale provided for why this function exists or what problem it solves.",
                    location="intent.rationale",
                    current_value=None,
                    suggested_value="Add a rationale explaining the function's purpose and context",
                    rationale="Rationales help users understand when and why to use this function.",
                    examples=[
                        "This function is needed to process user input from the web form",
                        "Used to validate data before inserting into the database",
                        "Provides a utility for common string manipulation tasks",
                    ],
                )
            )

        # Check parameter documentation
        undocumented_params = [p for p in ir.signature.parameters if not p.description]
        if undocumented_params:
            for i, param in enumerate(ir.signature.parameters):
                if not param.description:
                    suggestions.append(
                        Suggestion(
                            category=SuggestionCategory.DOCUMENTATION,
                            severity=SuggestionSeverity.MEDIUM,
                            title=f"Parameter '{param.name}' lacks description",
                            description=f"Parameter '{param.name}' has no description, making it unclear what values are expected.",
                            location=f"signature.parameters[{i}].description",
                            current_value=None,
                            suggested_value="Add a description explaining the parameter's purpose and constraints",
                            rationale="Parameter descriptions help users understand what to pass to the function.",
                            examples=[
                                f"For '{param.name}': 'The input value to process (must be positive)'",
                                f"For '{param.name}': 'Username for authentication (3-20 characters)'",
                            ],
                        )
                    )

        return suggestions

    def _detect_security_concerns(self, ir: IntermediateRepresentation) -> list[Suggestion]:
        """Detect potential security issues in the specification."""
        suggestions = []

        # Check for input validation assertions
        input_params = [p for p in ir.signature.parameters if not p.name.startswith("_")]
        if input_params and len(ir.assertions) == 0:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.SECURITY,
                    severity=SuggestionSeverity.HIGH,
                    title="No input validation assertions",
                    description="The function accepts input parameters but has no assertions to validate them. This can lead to security vulnerabilities.",
                    location="assertions",
                    current_value="No assertions defined",
                    suggested_value="Add assertions to validate input parameters",
                    rationale="Input validation prevents injection attacks, buffer overflows, and unexpected behavior.",
                    examples=[
                        "For string parameters: assert len(username) > 0 and len(username) <= 50",
                        "For numeric parameters: assert amount >= 0",
                        "For collections: assert len(items) > 0",
                        "For patterns: assert re.match(r'^[a-zA-Z0-9]+$', input_str)",
                    ],
                    references=[
                        "OWASP Input Validation Cheat Sheet",
                        "CWE-20: Improper Input Validation",
                    ],
                )
            )

        # Check for SQL-related parameters without injection protection
        for i, param in enumerate(ir.signature.parameters):
            param_lower = param.name.lower()
            if any(keyword in param_lower for keyword in ["query", "sql", "statement"]):
                has_sql_assertion = any(
                    "sql" in assertion.predicate.lower() or "inject" in assertion.predicate.lower()
                    for assertion in ir.assertions
                )
                if not has_sql_assertion:
                    suggestions.append(
                        Suggestion(
                            category=SuggestionCategory.SECURITY,
                            severity=SuggestionSeverity.CRITICAL,
                            title=f"SQL injection risk in parameter '{param.name}'",
                            description=f"Parameter '{param.name}' appears to be SQL-related but lacks injection protection assertions.",
                            location=f"signature.parameters[{i}]",
                            current_value=param.name,
                            suggested_value="Add assertion to ensure parameterized queries or input sanitization",
                            rationale="SQL injection is a critical vulnerability that can lead to data breaches.",
                            examples=[
                                "Add assertion: 'Uses parameterized queries (no string concatenation)'",
                                "Add assertion: 'Input is sanitized using prepared statements'",
                            ],
                            references=[
                                "OWASP SQL Injection Prevention",
                                "CWE-89: SQL Injection",
                            ],
                        )
                    )

        return suggestions

    def _detect_completeness_issues(self, ir: IntermediateRepresentation) -> list[Suggestion]:
        """Detect missing or incomplete specifications."""
        suggestions = []

        # Check for effects documentation
        if len(ir.effects) == 0:
            # Only suggest if function likely has side effects
            likely_has_effects = any(
                keyword in ir.intent.summary.lower()
                for keyword in [
                    "write",
                    "save",
                    "update",
                    "delete",
                    "modify",
                    "create",
                    "send",
                    "connect",
                ]
            )
            if likely_has_effects:
                suggestions.append(
                    Suggestion(
                        category=SuggestionCategory.COMPLETENESS,
                        severity=SuggestionSeverity.MEDIUM,
                        title="Missing effect documentation",
                        description="The function likely has side effects based on its description, but no effects are documented.",
                        location="effects",
                        current_value="No effects specified",
                        suggested_value="Document all side effects (I/O, state changes, external interactions)",
                        rationale="Documenting effects helps users understand the function's impact on the system.",
                        examples=[
                            "Writes data to file system at path /var/data",
                            "Sends HTTP request to external API",
                            "Modifies global application state",
                            "Creates database connection that must be closed",
                        ],
                    )
                )

        # Check for error handling documentation
        has_error_handling = any(
            keyword in assertion.predicate.lower()
            or (assertion.rationale and keyword in assertion.rationale.lower())
            for assertion in ir.assertions
            for keyword in ["error", "exception", "fail", "invalid", "raise"]
        )
        if not has_error_handling:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.COMPLETENESS,
                    severity=SuggestionSeverity.MEDIUM,
                    title="No error handling documented",
                    description="The specification does not document how errors are handled or what exceptions can be raised.",
                    location="assertions",
                    current_value="No error handling assertions",
                    suggested_value="Add assertions describing error conditions and how they are handled",
                    rationale="Error handling documentation helps users anticipate and handle failures.",
                    examples=[
                        "Raises ValueError if input is negative",
                        "Returns None if file not found (does not raise exception)",
                        "Raises ConnectionError if network unavailable",
                    ],
                )
            )

        return suggestions

    def _detect_best_practice_violations(self, ir: IntermediateRepresentation) -> list[Suggestion]:
        """Detect violations of specification best practices."""
        suggestions = []

        # Check for overly complex functions (too many parameters)
        if len(ir.signature.parameters) > 5:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.BEST_PRACTICES,
                    severity=SuggestionSeverity.LOW,
                    title="High parameter count",
                    description=f"Function has {len(ir.signature.parameters)} parameters, which may indicate it's doing too much.",
                    location="signature.parameters",
                    current_value=f"{len(ir.signature.parameters)} parameters",
                    suggested_value="Consider grouping related parameters into objects or splitting the function",
                    rationale="Functions with many parameters are harder to use, test, and maintain.",
                    examples=[
                        "Group related params: Instead of (name, email, phone, address), use (user_info: UserInfo)",
                        "Split function: Break into smaller functions with focused responsibilities",
                    ],
                )
            )

        # Check for weak assertions
        weak_assertions = [
            a
            for a in ir.assertions
            if len(a.predicate) < 10 or a.predicate in ["true", "True", "1"]
        ]
        if weak_assertions:
            suggestions.append(
                Suggestion(
                    category=SuggestionCategory.BEST_PRACTICES,
                    severity=SuggestionSeverity.MEDIUM,
                    title="Weak or trivial assertions",
                    description="Some assertions are too simple or trivial to provide meaningful validation.",
                    location="assertions",
                    current_value=f"{len(weak_assertions)} weak assertions",
                    suggested_value="Replace with specific, meaningful assertions",
                    rationale="Strong assertions catch real bugs and document important invariants.",
                    examples=[
                        "Instead of: 'x > 0'",
                        "Use: 'x > 0 and x <= 100 (valid age range)'",
                        "Instead of: 'result != None'",
                        "Use: 'len(result) > 0 and all(isinstance(item, User) for item in result)'",
                    ],
                )
            )

        return suggestions

    def _is_weak_type(self, type_hint: str) -> bool:
        """Check if a type hint is overly generic."""
        return any(pattern.lower() in type_hint.lower() for pattern in self._weak_type_patterns)

    def _suggest_specific_type(self, param: Parameter) -> str:
        """Suggest a more specific type based on parameter context."""
        name_lower = param.name.lower()

        # Common patterns
        if "count" in name_lower or "num" in name_lower or "size" in name_lower:
            return "int"
        if "name" in name_lower or "text" in name_lower or "message" in name_lower:
            return "str"
        if "flag" in name_lower or "is_" in name_lower or "has_" in name_lower:
            return "bool"
        if "list" in name_lower or "items" in name_lower:
            return "list[T] (replace T with element type)"
        if "dict" in name_lower or "map" in name_lower:
            return "dict[K, V] (replace K, V with key/value types)"

        # Description-based hints
        if param.description:
            desc_lower = param.description.lower()
            if "number" in desc_lower or "integer" in desc_lower:
                return "int"
            if "string" in desc_lower or "text" in desc_lower:
                return "str"
            if "list" in desc_lower or "array" in desc_lower:
                return "list[T]"

        return "Specify based on parameter's purpose (e.g., int, str, list[str])"

    def _calculate_stats(self, suggestions: list[Suggestion]) -> dict[str, int]:
        """Calculate summary statistics for suggestions."""
        stats = {
            "total": len(suggestions),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }

        for suggestion in suggestions:
            severity_key = suggestion.severity.value
            stats[severity_key] = stats.get(severity_key, 0) + 1

        return stats

    def _calculate_quality_score(
        self, ir: IntermediateRepresentation, suggestions: list[Suggestion]
    ) -> float:
        """
        Calculate overall quality score (0.0 to 1.0).

        Score is based on:
        - Presence of documentation
        - Type specificity
        - Number and severity of suggestions
        - Completeness of specification
        """
        score = 1.0

        # Deduct points for suggestions based on severity
        for suggestion in suggestions:
            if suggestion.severity == SuggestionSeverity.CRITICAL:
                score -= 0.15
            elif suggestion.severity == SuggestionSeverity.HIGH:
                score -= 0.10
            elif suggestion.severity == SuggestionSeverity.MEDIUM:
                score -= 0.05
            elif suggestion.severity == SuggestionSeverity.LOW:
                score -= 0.02

        # Bonus points for good practices
        if ir.intent.rationale:
            score += 0.05
        if len(ir.assertions) > 0:
            score += 0.05
        if all(p.description for p in ir.signature.parameters):
            score += 0.05

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))


__all__ = [
    "AgentAdvisor",
    "AnalysisReport",
    "Suggestion",
    "SuggestionCategory",
    "SuggestionSeverity",
]
