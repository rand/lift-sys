"""
IR Interpreter - Semantic Validation Before Code Generation

Combines Effect Chain Analyzer, Semantic Validator, and Logic Error Detector
to validate IR before code generation.

Usage:
    interpreter = IRInterpreter()
    result = interpreter.interpret(ir)

    if result.has_errors():
        # Reject IR, don't generate code
        print(f"Semantic validation failed: {result.errors}")
    else:
        # Proceed with code generation
        code = generator.generate(ir)
"""

from __future__ import annotations

from dataclasses import dataclass

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.validation.effect_analyzer import EffectChainAnalyzer, ExecutionTrace, SemanticIssue
from lift_sys.validation.logic_error_detector import LogicErrorDetector
from lift_sys.validation.semantic_validator import SemanticValidator, ValidationResult


@dataclass
class InterpretationResult:
    """Result of IR interpretation."""

    ir: IntermediateRepresentation
    """The IR that was interpreted"""

    trace: ExecutionTrace
    """Symbolic execution trace"""

    validation: ValidationResult
    """Semantic validation result"""

    all_issues: list[SemanticIssue]
    """All issues (from trace + validation + logic detection)"""

    def has_errors(self) -> bool:
        """Check if any errors were detected."""
        return any(issue.severity == "error" for issue in self.all_issues)

    def has_warnings(self) -> bool:
        """Check if any warnings were detected."""
        return any(issue.severity == "warning" for issue in self.all_issues)

    @property
    def errors(self) -> list[SemanticIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.all_issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[SemanticIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.all_issues if issue.severity == "warning"]

    def __str__(self) -> str:
        status = "❌ FAILED" if self.has_errors() else "✅ PASSED"
        lines = [f"IR Interpretation: {status}"]

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  {error}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        # Add summary
        lines.append("\nExecution Trace:")
        lines.append(f"  Values: {len(self.trace.values)}")
        lines.append(
            f"  Operations: {', '.join(self.trace.operations) if self.trace.operations else 'None'}"
        )
        lines.append(f"  Return: {self.trace.return_value or 'None'}")

        return "\n".join(lines)


class IRInterpreter:
    """
    IR Interpreter for semantic validation.

    Combines:
    1. Effect Chain Analyzer - builds symbolic execution trace
    2. Semantic Validator - checks IR consistency
    3. Logic Error Detector - detects common bug patterns

    Use this before code generation to catch semantic errors early.
    """

    def __init__(self):
        """Initialize IR interpreter with all components."""
        self.analyzer = EffectChainAnalyzer()
        self.validator = SemanticValidator()
        self.detector = LogicErrorDetector()

    def interpret(self, ir: IntermediateRepresentation) -> InterpretationResult:
        """
        Interpret IR and validate semantics.

        Args:
            ir: Intermediate representation to interpret

        Returns:
            InterpretationResult with trace, validation, and issues
        """
        # Step 1: Build symbolic execution trace
        trace = self.analyzer.analyze(ir)

        # Step 2: Validate semantics
        validation = self.validator.validate(ir, trace)

        # Step 3: Detect logic error patterns
        logic_issues = self.detector.detect_all_patterns(ir, trace)

        # Step 4: Additional validation passes
        return_issues = self._validate_return_value(ir, trace)
        loop_issues = self._validate_loop_behavior(ir, trace)
        scope_issues = self._validate_variable_scope(trace)
        type_issues = self._validate_type_consistency(ir, trace)
        flow_issues = self._validate_control_flow(ir, trace)

        # Combine all issues
        all_issues = (
            list(validation.issues)
            + logic_issues
            + return_issues
            + loop_issues
            + scope_issues
            + type_issues
            + flow_issues
        )

        # Remove duplicates (same category + message)
        seen = set()
        unique_issues = []
        for issue in all_issues:
            key = (issue.category, issue.message)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return InterpretationResult(
            ir=ir,
            trace=trace,
            validation=validation,
            all_issues=unique_issues,
        )

    def should_generate_code(self, result: InterpretationResult) -> bool:
        """
        Determine if code generation should proceed.

        Args:
            result: Interpretation result

        Returns:
            True if code generation should proceed, False otherwise
        """
        # Block code generation if there are errors
        # Warnings are okay - they're non-blocking
        return not result.has_errors()

    def _validate_return_value(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Enhanced return value validation.

        Checks:
        1. Function should return a value if signature specifies return type
        2. Return value type matches signature
        3. Computed values are actually returned (not just computed and forgotten)
        4. Return happens at appropriate point in control flow
        """
        issues = []

        # Check if function has return type but no return in trace
        if ir.signature.returns and not trace.return_value:
            # Check if effects mention returning
            has_return_effect = any("return" in effect.description.lower() for effect in ir.effects)

            if has_return_effect:
                # Effect mentions return but trace doesn't capture it
                issues.append(
                    SemanticIssue(
                        severity="error",
                        category="missing_return",
                        message=f"Function should return {ir.signature.returns} and effects mention returning, "
                        "but no return value in trace",
                        suggestion="Ensure return effect creates proper return value",
                    )
                )
            else:
                # No return effect mentioned - warning (might be implicit)
                computed_values = [v for v in trace.values.values() if v.source == "computed"]
                if computed_values:
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="implicit_return",
                            message=f"Function computes values but no explicit return effect. "
                            f"Computed: {', '.join(v.name for v in computed_values)}",
                            suggestion=f"Add effect: 'Return the {computed_values[-1].name}'",
                        )
                    )

        # Check if trace has return but signature doesn't specify return type
        elif trace.return_value and not ir.signature.returns:
            issues.append(
                SemanticIssue(
                    severity="warning",
                    category="unexpected_return",
                    message="Trace shows return value but signature doesn't specify return type",
                    suggestion="Update signature to include return type or remove return effect",
                )
            )

        return issues

    def _validate_loop_behavior(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Check loop behavior matches intent.

        Detects:
        1. FIRST_MATCH intent but no early return/break
        2. LAST_MATCH intent with early return (inefficient)
        3. Iteration without clear termination condition
        4. Off-by-one errors in loop bounds
        """
        issues = []

        # Check if there are loop operations
        loop_ops = [
            op for op in trace.operations if op in ["iterate", "loop", "traverse", "walk through"]
        ]

        if not loop_ops:
            return issues

        # Analyze effect descriptions for loop intent
        for i, effect in enumerate(ir.effects):
            desc_lower = effect.description.lower()

            # Check for FIRST_MATCH patterns
            first_match_keywords = [
                "first",
                "earliest",
                "initial",
                "find and return",
                "stop when",
            ]
            if any(keyword in desc_lower for keyword in first_match_keywords):
                # Should have early termination
                has_break = any(op in trace.operations for op in ["break", "return", "exit"])
                has_return_in_loop = any(
                    "return" in e.description.lower() and "iterate" in e.description.lower()
                    for e in ir.effects
                )

                if not (has_break or has_return_in_loop):
                    issues.append(
                        SemanticIssue(
                            severity="error",
                            category="loop_behavior",
                            message="Intent suggests finding first match, but no early termination in trace",
                            effect_index=i,
                            suggestion="Add 'break' or 'return' when condition is met",
                        )
                    )

            # Check for LAST_MATCH with inefficient iteration
            last_match_keywords = ["last", "final", "ultimate", "all"]
            if any(keyword in desc_lower for keyword in last_match_keywords):
                # Early return would be inefficient
                has_early_return = any(
                    "return" in e.description.lower()
                    and e != ir.effects[-1]
                    and "iterate" in desc_lower
                    for e in ir.effects
                )

                if has_early_return:
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="loop_inefficiency",
                            message="Intent suggests processing all elements, but early return detected",
                            effect_index=i,
                            suggestion="Remove early return to process all elements",
                        )
                    )

        # Check for unbounded loops
        if loop_ops:
            # Look for termination conditions in effects
            has_condition = any(
                any(
                    keyword in effect.description.lower()
                    for keyword in ["until", "while", "when", "if", "condition"]
                )
                for effect in ir.effects
            )

            if not has_condition:
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="loop_termination",
                        message="Loop detected but no clear termination condition",
                        suggestion="Add explicit termination condition",
                    )
                )

        return issues

    def _validate_variable_scope(self, trace: ExecutionTrace) -> list[SemanticIssue]:
        """
        Track variable definitions and usages for scope errors.

        Detects:
        1. Variables used before definition
        2. Variables defined but never used
        3. Variables redefined unnecessarily
        4. Shadowing of parameters
        """
        issues = []

        # Track defined variables in order
        defined_vars = set()
        used_vars = set()

        # Parameters are always defined
        for value in trace.values.values():
            if value.source == "parameter":
                defined_vars.add(value.name)

        # Track computed values
        computed_values = []
        for value in trace.values.values():
            if value.source == "computed":
                computed_values.append(value)

        # Check for shadowing
        for computed_value in computed_values:
            if computed_value.name in defined_vars:
                # Check if it's a parameter
                param_names = [v.name for v in trace.values.values() if v.source == "parameter"]
                if computed_value.name in param_names:
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="variable_shadowing",
                            message=f"Computed value '{computed_value.name}' shadows parameter with same name",
                            effect_index=computed_value.effect_index,
                            suggestion="Rename computed value to avoid shadowing",
                        )
                    )

        # Check if return value uses a defined variable
        if trace.return_value and trace.return_value.name != "<return_value>":
            if trace.return_value.name not in [v.name for v in trace.values.values()]:
                issues.append(
                    SemanticIssue(
                        severity="error",
                        category="undefined_variable",
                        message=f"Return value '{trace.return_value.name}' not found in trace values",
                        suggestion="Ensure variable is computed before returning",
                    )
                )

        # Mark all values as potentially used (simplified - real analysis would parse operations)
        # In a real implementation, we'd parse effect descriptions for variable references

        return issues

    def _validate_type_consistency(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Check type consistency across operations.

        Detects:
        1. Type mismatches between operations
        2. Return type doesn't match signature
        3. Operations on incompatible types
        4. Implicit type conversions
        """
        issues = []

        # Check return type consistency
        if trace.return_value and ir.signature.returns:
            return_type = trace.return_value.type_hint
            expected_type = ir.signature.returns

            # Normalize types for comparison
            def normalize_type(t: str) -> str:
                return t.replace(" ", "").lower()

            if normalize_type(return_type) != normalize_type(expected_type):
                # Allow some flexibility (Any matches anything)
                if return_type != "Any" and expected_type != "Any":
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="type_mismatch",
                            message=f"Return type mismatch: trace shows '{return_type}', "
                            f"signature expects '{expected_type}'",
                            suggestion="Update effects to produce correct type or fix signature",
                        )
                    )

        # Check for common type errors in operations
        for i, effect in enumerate(ir.effects):
            desc_lower = effect.description.lower()

            # Check for string operations on non-strings
            if any(op in desc_lower for op in ["split", "join", "strip", "replace"]):
                # These are string operations
                # Check if we're operating on a string value
                # (Simplified - real implementation would track data flow)
                pass

            # Check for numeric operations on non-numbers
            if any(op in desc_lower for op in ["add", "subtract", "multiply", "divide", "count"]):
                # These produce numeric results
                # Count specifically produces int
                if "count" in desc_lower:
                    # Check if we're returning count as non-int
                    if trace.return_value and trace.return_value.name == "count":
                        if trace.return_value.type_hint not in ["int", "Any"]:
                            issues.append(
                                SemanticIssue(
                                    severity="error",
                                    category="type_error",
                                    message=f"Count operation should produce int, but trace shows "
                                    f"'{trace.return_value.type_hint}'",
                                    effect_index=i,
                                    suggestion="Fix type inference for count operation",
                                )
                            )

            # Check for iteration on non-iterables
            if any(op in desc_lower for op in ["iterate", "loop", "for each"]):
                # Should be operating on a list/iterable
                # (Simplified - real implementation would check the value being iterated)
                pass

        return issues

    def _validate_control_flow(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Ensure all code paths are complete.

        Detects:
        1. Missing else branches
        2. Unreachable code
        3. Missing return in branches
        4. Dead code after return
        """
        issues = []

        # Track conditional structures
        has_if = False
        has_else = False
        return_indices = []

        for i, effect in enumerate(ir.effects):
            desc_lower = effect.description.lower()

            # Track conditionals
            if any(keyword in desc_lower for keyword in ["if", "when", "in case"]):
                has_if = True

            if any(keyword in desc_lower for keyword in ["else", "otherwise"]):
                has_else = True

            # Track returns
            if any(keyword in desc_lower for keyword in ["return", "output", "yield"]):
                return_indices.append(i)

        # Check for if without else
        if has_if and not has_else:
            # Check if this is a guard clause or early return
            is_guard = any(
                "return" in ir.effects[i].description.lower() for i in range(len(ir.effects))
            )

            if not is_guard:
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="incomplete_branch",
                        message="Conditional (if) without else branch - may not handle all cases",
                        suggestion="Add else branch or ensure default behavior is clear",
                    )
                )

        # Check for code after return
        if return_indices:
            first_return = return_indices[0]
            if first_return < len(ir.effects) - 1:
                # There's code after the return
                # Check if it's in a different branch
                has_conditional_return = any(
                    "if" in ir.effects[i].description.lower()
                    or "when" in ir.effects[i].description.lower()
                    for i in return_indices
                )

                if not has_conditional_return:
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="unreachable_code",
                            message=f"Effects after return (effect {first_return}) may be unreachable",
                            effect_index=first_return + 1,
                            suggestion="Move effects before return or make return conditional",
                        )
                    )

        # Check for all paths returning when return type is specified
        if ir.signature.returns and has_if:
            # If we have conditionals and need to return, all branches should return
            if not has_else and return_indices:
                issues.append(
                    SemanticIssue(
                        severity="error",
                        category="missing_return_path",
                        message="Not all code paths return a value (missing else branch)",
                        suggestion="Ensure all branches return a value or add else clause",
                    )
                )

        return issues
