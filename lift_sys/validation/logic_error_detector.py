"""
Logic Error Detector - Step 3 of IR Interpreter

Detects common semantic bug patterns in IR:
1. Off-by-one errors (find first vs find last, enumerate bugs)
2. Invalid validation logic (email, phone, etc.)
3. Unreachable code patterns
4. Logic contradictions

Works with IR and ExecutionTrace to identify potential logic bugs
that can't be caught by syntax checking.
"""

from __future__ import annotations

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.validation.effect_analyzer import ExecutionTrace, SemanticIssue


class LogicErrorDetector:
    """
    Detects common semantic bug patterns.

    Pattern categories:
    1. Off-by-one errors (first/last confusion, loop index bugs)
    2. Invalid validation logic (incomplete checks)
    3. Unreachable code (effects after return)
    4. Logic contradictions
    """

    def detect_all_patterns(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Run all pattern detectors.

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of all issues detected
        """
        issues: list[SemanticIssue] = []

        # Check for off-by-one errors
        issues.extend(self.detect_off_by_one(ir, trace))

        # Check for invalid validation logic
        issues.extend(self.detect_invalid_validation(ir, trace))

        # Check for unreachable code
        issues.extend(self.detect_unreachable_code(ir, trace))

        return issues

    def detect_off_by_one(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Detect potential off-by-one errors.

        Common patterns:
        1. Intent says "first" but implementation might return "last"
        2. Enumerate loop that continues after finding match (returns last instead of first)
        3. Loop index confusion (0-indexed vs 1-indexed)

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of issues found
        """
        issues: list[SemanticIssue] = []

        # Get intent and effect text
        intent_text = ir.intent.summary.lower()
        effect_texts = [e.description.lower() for e in ir.effects]
        all_effects = " ".join(effect_texts)

        # Pattern 1: Intent says "first" but implementation might return "last"
        if "first" in intent_text:
            # Check if there's an immediate return when found
            has_immediate_return = any(
                "return" in e and ("when" in e or "if" in e or "immediately" in e)
                for e in effect_texts
            )

            # Check for enumerate usage
            has_enumerate = any("enumerate" in e for e in effect_texts)

            if has_enumerate and not has_immediate_return:
                # Risk: enumerate loop might continue to end, returning last instead of first
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="off_by_one",
                        message="Intent says 'first' but enumerate loop may return LAST match instead. "
                        "Ensure you return immediately when found, not after loop completes.",
                        suggestion="Add effect: 'Return the index immediately when found' "
                        "or 'Break loop after finding first match'",
                    )
                )

            # Check for any loop that might have this issue
            has_loop = any(
                keyword in all_effects for keyword in ["iterate", "loop", "for", "while", "through"]
            )

            if has_loop and not has_immediate_return:
                # General warning for first/last confusion
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="off_by_one",
                        message="Intent says 'first' but effects don't specify immediate return. "
                        "May return last occurrence instead of first.",
                        suggestion="Add effect: 'Return immediately when found' to ensure first match is returned",
                    )
                )

        # Pattern 2: "Last" in intent but might return first
        if "last" in intent_text:
            has_immediate_return = any(
                "return" in e and ("when" in e or "if" in e or "immediately" in e)
                for e in effect_texts
            )

            if has_immediate_return:
                # Risk: returning immediately might give first instead of last
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="off_by_one",
                        message="Intent says 'last' but effects specify immediate return. "
                        "May return first occurrence instead of last.",
                        suggestion="Remove immediate return, or store index and return after loop completes",
                    )
                )

        return issues

    def detect_invalid_validation(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Detect validation logic that might be incorrect.

        Common patterns:
        1. Email validation that doesn't check for dot after @
        2. Email validation that doesn't check domain length
        3. Phone validation that doesn't validate format
        4. Password validation that's too weak

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of issues found
        """
        issues: list[SemanticIssue] = []

        intent_text = ir.intent.summary.lower()
        effect_texts = [e.description.lower() for e in ir.effects]
        all_effects = " ".join(effect_texts)

        # Check if this is a validation function
        is_validation = any(
            keyword in intent_text for keyword in ["valid", "validate", "check", "verify", "ensure"]
        )

        if not is_validation:
            return issues

        # Pattern 1: Email validation
        if "email" in intent_text:
            has_at_check = "@" in all_effects or "at sign" in all_effects
            has_dot_check = "." in all_effects or "dot" in all_effects or "period" in all_effects

            if has_at_check and has_dot_check:
                # Both @ and . are checked, but are they checked properly?
                # Check if "after" relationship is specified
                has_after_check = any(
                    "after" in e and ("@" in e or "at" in e) for e in effect_texts
                )

                if not has_after_check:
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="invalid_logic",
                            message="Email validation checks for @ and . but doesn't verify dot comes AFTER @. "
                            "This would accept invalid emails like 'test@.com' or 'test.@com'",
                            suggestion="Add effect: 'Check that dot position is after @ position' "
                            "or 'Ensure domain has at least one character before dot'",
                        )
                    )

                # Check for domain validation
                has_domain_check = any("domain" in e or "after @" in e for e in effect_texts)

                if not has_domain_check:
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="invalid_logic",
                            message="Email validation doesn't check domain validity. "
                            "This would accept emails like 'test@.com' or 'test@domain.'",
                            suggestion="Add effect: 'Check domain has characters before and after dot'",
                        )
                    )

            elif has_at_check and not has_dot_check:
                issues.append(
                    SemanticIssue(
                        severity="error",
                        category="invalid_logic",
                        message="Email validation only checks for @, not for dot. "
                        "This would accept invalid emails like 'test@domain'",
                        suggestion="Add effect: 'Check for dot in domain part after @'",
                    )
                )

            elif has_dot_check and not has_at_check:
                issues.append(
                    SemanticIssue(
                        severity="error",
                        category="invalid_logic",
                        message="Email validation only checks for dot, not for @. "
                        "This would accept invalid emails like 'test.domain.com'",
                        suggestion="Add effect: 'Check for @ symbol'",
                    )
                )

        # Pattern 2: Phone validation
        if "phone" in intent_text:
            has_digit_check = any("digit" in e or "number" in e for e in effect_texts)
            has_length_check = any("length" in e or "digits" in e for e in effect_texts)
            has_format_check = any(
                keyword in all_effects
                for keyword in ["format", "pattern", "dash", "hyphen", "parenthes"]
            )

            if not has_digit_check and not has_length_check:
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="invalid_logic",
                        message="Phone validation doesn't check for digits or length",
                        suggestion="Add effect: 'Check that phone number contains only digits and has correct length'",
                    )
                )

        # Pattern 3: Password validation
        if "password" in intent_text:
            has_length_check = any("length" in e for e in effect_texts)
            has_complexity_check = any(
                keyword in all_effects
                for keyword in ["uppercase", "lowercase", "digit", "special", "character"]
            )

            if not has_length_check:
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="invalid_logic",
                        message="Password validation doesn't check minimum length",
                        suggestion="Add effect: 'Check password length is at least N characters'",
                    )
                )

        return issues

    def detect_unreachable_code(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Detect effects that appear after a return statement.

        Such effects will never execute and indicate a logic error.

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of issues found
        """
        issues: list[SemanticIssue] = []

        # Find first effect that contains "return"
        return_index = None
        for i, effect in enumerate(ir.effects):
            effect_lower = effect.description.lower()
            if any(
                keyword in effect_lower for keyword in ["return", "output", "yield", "give back"]
            ):
                return_index = i
                break

        # If we found a return, check if there are effects after it
        if return_index is not None and return_index < len(ir.effects) - 1:
            # There are effects after the return
            remaining_effects = ir.effects[return_index + 1 :]

            # Check if these are conditional returns (which is okay)
            return_effect = ir.effects[return_index].description.lower()
            is_conditional = any(
                keyword in return_effect for keyword in ["if", "when", "else", "otherwise"]
            )

            if not is_conditional:
                # Unconditional return followed by more effects
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="unreachable_code",
                        message=f"Effect {return_index + 1} returns a value, but {len(remaining_effects)} "
                        f"effect(s) appear after it. These effects will never execute.",
                        effect_index=return_index,
                        suggestion="Remove effects after return, or make return conditional",
                    )
                )

        return issues
