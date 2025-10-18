"""
Effect Chain Analyzer - Step 1 of IR Interpreter

Parses IR effects and builds a symbolic execution trace to:
1. Track data flow through effect chain
2. Detect values produced by effects
3. Identify missing return logic
4. Support semantic validation

Example:
    IR effects:
    - "Split input string by spaces into words list"
    - "Iterate through words list"
    - "Count the number of elements"

    Trace:
    - input_string (parameter:str) -> words (computed:list[str]) -> count (computed:int)
    - Operations: [split, iterate, count]
    - Return value: None (missing!)
    - Issue: "Effect chain produces 'count' but doesn't return it"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lift_sys.ir.models import IntermediateRepresentation


@dataclass
class SymbolicValue:
    """Represents a value in symbolic execution."""

    name: str
    """Variable name (e.g., 'count', 'words', 'result')"""

    type_hint: str
    """Type of the value (e.g., 'int', 'list[str]', 'bool')"""

    source: str
    """Where value comes from: 'parameter', 'computed', 'literal'"""

    provenance: list[str] = field(default_factory=list)
    """Trail of operations that produced this value"""

    effect_index: int | None = None
    """Index of effect that created this value"""

    def __str__(self) -> str:
        return f"{self.name}:{self.type_hint} ({self.source})"


@dataclass
class SemanticIssue:
    """A semantic error detected during interpretation."""

    severity: str
    """'error' or 'warning'"""

    category: str
    """Type of issue: 'missing_return', 'off_by_one', 'invalid_logic', etc."""

    message: str
    """Human-readable description"""

    effect_index: int | None = None
    """Index of effect where issue was detected"""

    suggestion: str | None = None
    """Suggestion for how to fix the issue"""

    def __str__(self) -> str:
        prefix = "❌" if self.severity == "error" else "⚠️ "
        location = f" (effect {self.effect_index})" if self.effect_index is not None else ""
        return f"{prefix} {self.message}{location}"


@dataclass
class ExecutionTrace:
    """Trace of symbolic execution through effects."""

    values: dict[str, SymbolicValue] = field(default_factory=dict)
    """All symbolic values (parameters + computed)"""

    operations: list[str] = field(default_factory=list)
    """Operations performed (split, iterate, count, etc.)"""

    return_value: SymbolicValue | None = None
    """Value returned by effect chain (if any)"""

    issues: list[SemanticIssue] = field(default_factory=list)
    """Semantic issues detected"""

    def add_value(self, value: SymbolicValue) -> None:
        """Add a symbolic value to the trace."""
        self.values[value.name] = value

    def get_value(self, name: str) -> SymbolicValue | None:
        """Get a symbolic value by name."""
        return self.values.get(name)

    def add_issue(self, issue: SemanticIssue) -> None:
        """Add a semantic issue."""
        self.issues.append(issue)

    def has_errors(self) -> bool:
        """Check if any errors were detected."""
        return any(issue.severity == "error" for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if any warnings were detected."""
        return any(issue.severity == "warning" for issue in self.issues)

    def __str__(self) -> str:
        lines = ["Execution Trace:"]
        lines.append(f"  Values: {len(self.values)}")
        for _name, value in self.values.items():
            lines.append(f"    - {value}")
        lines.append(f"  Operations: {', '.join(self.operations)}")
        lines.append(f"  Return: {self.return_value or 'None'}")
        if self.issues:
            lines.append(f"  Issues: {len(self.issues)}")
            for issue in self.issues:
                lines.append(f"    {issue}")
        return "\n".join(lines)


class EffectChainAnalyzer:
    """
    Analyzes IR effect chains using symbolic execution.

    Approach:
    1. Extract parameters as initial symbolic values
    2. Parse each effect description to understand operations
    3. Track data flow: input -> transformation -> output
    4. Detect produced values and their types
    5. Check if effect chain returns a value
    """

    # Common verbs that indicate operations
    OPERATION_VERBS = {
        # Data transformation
        "split": ["split", "divide", "separate", "break"],
        "join": ["join", "combine", "concatenate", "merge"],
        "filter": ["filter", "select", "keep", "exclude"],
        "map": ["map", "transform", "convert", "apply"],
        "reduce": ["reduce", "aggregate", "accumulate"],
        # Iteration
        "iterate": ["iterate", "loop", "traverse", "walk through", "go through"],
        # Computation
        "count": ["count", "tally", "sum", "total"],
        "calculate": ["calculate", "compute", "determine", "find"],
        "check": ["check", "test", "verify", "validate"],
        # Data access
        "get": ["get", "retrieve", "fetch", "extract", "obtain"],
        "find": ["find", "search", "locate", "look for"],
        # Control flow
        "return": ["return", "output", "yield", "give back"],
        "if": ["if", "when", "in case"],
        "else": ["else", "otherwise"],
    }

    # Type hints that can be inferred from descriptions
    TYPE_KEYWORDS = {
        "int": ["integer", "int", "number", "count", "index"],
        "str": ["string", "str", "text", "word"],
        "bool": ["boolean", "bool", "true", "false"],
        "float": ["float", "decimal", "real number"],
        "list": ["list", "array", "collection", "elements"],
        "dict": ["dict", "dictionary", "map", "object"],
        "tuple": ["tuple", "pair"],
    }

    def analyze(self, ir: IntermediateRepresentation) -> ExecutionTrace:
        """
        Analyze IR effect chain and build symbolic execution trace.

        Args:
            ir: Intermediate representation with effects

        Returns:
            ExecutionTrace with symbolic values, operations, and issues
        """
        trace = ExecutionTrace()

        # Step 1: Initialize with parameters as symbolic values
        self._initialize_parameters(ir, trace)

        # Step 2: Parse each effect and update trace
        for i, effect in enumerate(ir.effects):
            self._parse_effect(effect.description, i, trace)

        # Step 3: Check if return value is set
        self._check_return_value(ir, trace)

        return trace

    def _initialize_parameters(self, ir: IntermediateRepresentation, trace: ExecutionTrace) -> None:
        """Initialize trace with function parameters as symbolic values."""
        for param in ir.signature.parameters:
            value = SymbolicValue(
                name=param.name,
                type_hint=param.type_hint or "Any",
                source="parameter",
                provenance=[f"parameter {param.name}"],
            )
            trace.add_value(value)

    def _parse_effect(self, description: str, effect_index: int, trace: ExecutionTrace) -> None:
        """
        Parse a single effect description and update trace.

        Examples:
        - "Split input string by spaces into words list" -> creates 'words:list[str]'
        - "Count the number of elements" -> creates 'count:int'
        - "Return the count" -> sets return_value to 'count'
        """
        desc_lower = description.lower()

        # Detect operation
        operation = self._detect_operation(desc_lower)
        if operation:
            trace.operations.append(operation)

        # Handle return statements
        if self._is_return_effect(desc_lower):
            self._handle_return(description, effect_index, trace)
            return

        # Extract produced value from effect
        produced_value = self._extract_produced_value(description, effect_index, trace)
        if produced_value:
            trace.add_value(produced_value)

    def _detect_operation(self, description: str) -> str | None:
        """Detect the primary operation in an effect description."""
        for operation, keywords in self.OPERATION_VERBS.items():
            if any(keyword in description for keyword in keywords):
                return operation
        return None

    def _is_return_effect(self, description: str) -> bool:
        """Check if effect is a return statement."""
        return_keywords = ["return", "output", "yield", "give back", "send back"]
        return any(keyword in description for keyword in return_keywords)

    def _handle_return(self, description: str, effect_index: int, trace: ExecutionTrace) -> None:
        """Handle a return effect."""
        # Try to find what value is being returned
        # Patterns: "Return the X", "Return X", "Output X"

        # Look for "return the <variable_name>"
        match = re.search(r"return\s+(?:the\s+)?(\w+)", description, re.IGNORECASE)
        if match:
            var_name = match.group(1)
            value = trace.get_value(var_name)
            if value:
                trace.return_value = value
                return

        # Look for "return <variable_name>"
        words = description.lower().split()
        if "return" in words:
            idx = words.index("return")
            if idx + 1 < len(words):
                potential_var = words[idx + 1].strip(".,;:")
                # Remove articles
                if potential_var in ["the", "a", "an"]:
                    if idx + 2 < len(words):
                        potential_var = words[idx + 2].strip(".,;:")

                value = trace.get_value(potential_var)
                if value:
                    trace.return_value = value
                    return

        # If we get here, we couldn't determine what's being returned
        # Mark it as a generic return
        trace.return_value = SymbolicValue(
            name="<return_value>",
            type_hint="Any",
            source="computed",
            provenance=["return statement"],
            effect_index=effect_index,
        )

    def _extract_produced_value(
        self, description: str, effect_index: int, trace: ExecutionTrace
    ) -> SymbolicValue | None:
        """
        Extract a value produced by this effect.

        Patterns:
        - "Split X into Y" -> produces Y
        - "Create X" -> produces X
        - "Calculate X" -> produces X
        - "Count the elements" -> produces 'count'
        - "Find the index" -> produces 'index'
        """
        desc_lower = description.lower()

        # Pattern 1: "... into <variable>"
        match = re.search(r"into\s+(?:a\s+)?(?:the\s+)?(\w+(?:\s+\w+)?)", desc_lower)
        if match:
            var_phrase = match.group(1).strip()
            var_name = self._extract_variable_name(var_phrase)
            type_hint = self._infer_type(desc_lower, var_phrase)
            return SymbolicValue(
                name=var_name,
                type_hint=type_hint,
                source="computed",
                provenance=[f"effect {effect_index}: {description[:50]}..."],
                effect_index=effect_index,
            )

        # Pattern 2: "Count the ..." -> produces 'count'
        if "count" in desc_lower and "the" in desc_lower:
            return SymbolicValue(
                name="count",
                type_hint="int",
                source="computed",
                provenance=[f"effect {effect_index}: counting"],
                effect_index=effect_index,
            )

        # Pattern 3: "Find the ..." -> produces variable based on what's being found
        if "find" in desc_lower:
            if "index" in desc_lower:
                return SymbolicValue(
                    name="index",
                    type_hint="int",
                    source="computed",
                    provenance=[f"effect {effect_index}: finding index"],
                    effect_index=effect_index,
                )
            elif "value" in desc_lower:
                return SymbolicValue(
                    name="value",
                    type_hint="Any",
                    source="computed",
                    provenance=[f"effect {effect_index}: finding value"],
                    effect_index=effect_index,
                )

        # Pattern 4: "Calculate ..." -> produces 'result'
        if "calculate" in desc_lower or "compute" in desc_lower:
            return SymbolicValue(
                name="result",
                type_hint=self._infer_type(desc_lower, "result"),
                source="computed",
                provenance=[f"effect {effect_index}: calculation"],
                effect_index=effect_index,
            )

        return None

    def _extract_variable_name(self, phrase: str) -> str:
        """Extract a clean variable name from a phrase."""
        # Remove common words
        stop_words = ["the", "a", "an", "this", "that", "new"]
        words = phrase.split()
        words = [w for w in words if w not in stop_words]

        if not words:
            return "value"

        # Join with underscore for multi-word names
        var_name = "_".join(words)

        # Clean up
        var_name = re.sub(r"[^\w]", "", var_name)

        return var_name or "value"

    def _infer_type(self, description: str, context: str = "") -> str:
        """
        Infer type hint from description and context.

        Args:
            description: Effect description
            context: Additional context (e.g., variable name)

        Returns:
            Type hint string (e.g., 'int', 'list[str]', 'bool')
        """
        desc_with_context = f"{description} {context}".lower()

        # Check for each type
        for type_name, keywords in self.TYPE_KEYWORDS.items():
            if any(keyword in desc_with_context for keyword in keywords):
                # Handle list types with element types
                if type_name == "list":
                    # Check if we can infer element type
                    if any(kw in desc_with_context for kw in self.TYPE_KEYWORDS["str"]):
                        return "list[str]"
                    elif any(kw in desc_with_context for kw in self.TYPE_KEYWORDS["int"]):
                        return "list[int]"
                    else:
                        return "list[Any]"
                return type_name

        return "Any"

    def _check_return_value(self, ir: IntermediateRepresentation, trace: ExecutionTrace) -> None:
        """
        Check if return value is properly set.

        Detects: Missing return when signature specifies a return type
        """
        # If signature specifies a return type but trace doesn't have return value
        if ir.signature.returns and not trace.return_value:
            # Check if any computed values exist that could be returned
            computed_values = [v for v in trace.values.values() if v.source == "computed"]

            if computed_values:
                # Effect chain produces values but doesn't return them
                value_names = ", ".join([f"'{v.name}'" for v in computed_values])
                trace.add_issue(
                    SemanticIssue(
                        severity="warning",
                        category="missing_return",
                        message=f"Function returns '{ir.signature.returns}' but effect chain doesn't return anything. "
                        f"Produced values: {value_names}",
                        suggestion=f"Add effect: 'Return the {computed_values[-1].name}'",
                    )
                )
            else:
                # No values produced at all - this is a warning, not error
                # Many IRs have minimal effects and rely on LLM to implement correctly
                trace.add_issue(
                    SemanticIssue(
                        severity="warning",
                        category="missing_return",
                        message=f"Function returns '{ir.signature.returns}' but effect chain produces no value",
                        suggestion="Add effects to compute and return the result",
                    )
                )
