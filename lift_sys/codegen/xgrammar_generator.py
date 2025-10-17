"""xgrammar-enhanced code generation for IR-to-code translation."""

from __future__ import annotations

import ast
import json
from typing import Any

from ..ir.constraint_validator import ConstraintValidator
from ..ir.models import IntermediateRepresentation
from ..providers.base import BaseProvider
from ..validation import AssertionChecker
from ..validation.ir_interpreter import IRInterpreter
from .ast_repair import ASTRepairEngine
from .code_schema import CODE_GENERATION_SCHEMA, get_prompt_for_code_generation
from .generator import CodeGenerator, CodeGeneratorConfig, GeneratedCode
from .multishot import MultishotGenerator
from .validation import CodeValidator


class XGrammarCodeGenerator:
    """
    Generates complete function implementations using xgrammar-constrained generation.

    This class wraps the existing CodeGenerator to handle structure (signature,
    docstring, assertions) and uses xgrammar to generate actual implementations
    instead of stubs.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: CodeGeneratorConfig | None = None,
    ):
        """
        Initialize with LLM provider and configuration.

        Args:
            provider: LLM provider for implementation generation
            config: Code generation configuration
        """
        self.provider = provider
        self.config = config or CodeGeneratorConfig()

        # Disable assertions for structural generator - they're often contradictory
        # and we're not using them in the final code anyway
        structural_config = CodeGeneratorConfig(
            inject_assertions=False,
            include_docstrings=self.config.include_docstrings,
            include_type_hints=self.config.include_type_hints,
            indent=self.config.indent,
        )
        self.structural_generator = CodeGenerator(config=structural_config)
        self.validator = CodeValidator()
        self.repair_engine = ASTRepairEngine()  # Phase 4: Deterministic repair
        self.constraint_validator = ConstraintValidator()  # Phase 7: IR constraint validation
        self.ir_interpreter = IRInterpreter()  # Phase 5: IR semantic validation (before codegen)
        self.assertion_checker = (
            AssertionChecker()
        )  # Phase 5b: Code assertion checking (after codegen)
        self.multishot = MultishotGenerator(num_shots=3)
        self._validation_feedback = ""  # Track validation feedback between attempts

    async def generate(
        self,
        ir: IntermediateRepresentation,
        max_retries: int = 5,
        use_multishot: bool = False,
        test_cases: list | None = None,
        temperature: float = 0.3,
    ) -> GeneratedCode:
        """
        Generate complete code from IR with actual implementation.

        Uses constrained generation with XGrammar when available (Modal provider) for:
        - Guaranteed schema-valid output (no JSON parsing failures)
        - Speculative parallel decoding (faster generation)
        - Higher quality, more consistent code generation

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails (rarely needed with XGrammar)
            use_multishot: If True, use Phase 3 multishot generation with test validation
            test_cases: Test cases for multishot validation [(inputs, expected), ...]
            temperature: Sampling temperature for generation (0.0 = deterministic, higher = more creative)

        Returns:
            GeneratedCode with complete implementation

        Raises:
            ValueError: If generation fails after max_retries
        """
        # Clear any unresolved holes (e.g., from IR deserialization)
        holes = ir.typed_holes()
        if holes:
            # Clear hole lists from all locations (matching performance_benchmark.py:214-227)
            ir.intent.holes = []
            ir.signature.holes = []
            for effect in ir.effects:
                effect.holes = []
            for assertion in ir.assertions:
                assertion.holes = []

            # Filter out TypedHole instances from parameters
            from lift_sys.ir.models import TypedHole

            ir.signature.parameters = [
                p for p in ir.signature.parameters if not isinstance(p, TypedHole)
            ]

            # Validate all holes were cleared
            remaining_holes = ir.typed_holes()
            if remaining_holes:
                raise ValueError(
                    f"IR contains unresolved holes that could not be cleared: {', '.join(h.identifier for h in remaining_holes)}"
                )

        # Phase 5: IR Semantic Validation (before code generation)
        # Interpret IR to detect semantic logic errors
        interpretation = self.ir_interpreter.interpret(ir)

        # Log interpretation results (warnings are informational)
        if interpretation.has_warnings():
            print(f"  ⚠️  IR has {len(interpretation.warnings)} warnings:")
            for warning in interpretation.warnings:
                print(f"      {warning.message}")

        # Block code generation if there are errors
        if interpretation.has_errors():
            error_messages = "\n".join([f"  - {err.message}" for err in interpretation.errors])
            return GeneratedCode(
                source_code="# Code generation blocked due to semantic errors\n"
                f"# Errors detected in IR:\n{error_messages}\n",
                language="python",
                metadata={
                    "ir_origin": ir.metadata.origin,
                    "generator": "xgrammar_blocked",
                    "semantic_validation": "failed",
                    "errors": [err.message for err in interpretation.errors],
                    "warnings": [warn.message for warn in interpretation.warnings],
                },
                warnings=[
                    f"Semantic validation failed: {err.message}" for err in interpretation.errors
                ],
            )

        # Phase 3: Multi-shot generation with empirical testing
        if use_multishot and test_cases:
            candidate = await self.multishot.generate_and_test(self, ir, test_cases)
            if candidate.score > 0:
                return GeneratedCode(
                    source_code=candidate.code,
                    language="python",
                    metadata={
                        "ir_origin": ir.metadata.origin,
                        "generator": "xgrammar_multishot",
                        "multishot_score": candidate.score,
                        "passed_tests": candidate.passed_tests,
                        "total_tests": candidate.total_tests,
                    },
                    warnings=[],
                )
            # If multishot failed, fall through to regular generation

        # First, use structural generator to get signature, docstring, and structure
        structural_code = self.structural_generator.generate(ir)

        # Extract structural elements (signature, docstring, assertions)
        structure = self._parse_structural_code(structural_code.source_code)

        # Generate implementation using constrained generation (XGrammar) or fallback
        for attempt in range(max_retries):
            try:
                # Increase temperature on retries to get more diverse outputs
                # attempt 0: base temperature, attempt 1+: gradually increase
                retry_temperature = temperature + (attempt * 0.15)  # +0.15 per retry
                retry_temperature = min(retry_temperature, 0.9)  # Cap at 0.9
                impl_json = await self._generate_implementation(
                    ir, structure, attempt, retry_temperature
                )

                # Validate implementation JSON
                self._validate_implementation(impl_json)

                # Combine structure + implementation
                complete_code = self._combine_structure_and_implementation(structure, impl_json)

                # Validate syntax
                try:
                    ast.parse(complete_code)
                except SyntaxError as e:
                    if attempt == max_retries - 1:
                        raise ValueError(f"Generated invalid Python syntax: {e}") from e
                    # Retry with error feedback
                    continue

                # Phase 4: Deterministic AST Repair (before validation)
                # Try to fix known bug patterns automatically
                try:
                    repaired_code = self.repair_engine.repair(
                        code=complete_code, function_name=ir.signature.name
                    )
                    if repaired_code:
                        print("  🔧 Applied deterministic AST repairs")
                        complete_code = repaired_code
                except Exception as e:
                    # If repair fails, continue with original code
                    print(f"  ⚠️ AST repair failed (continuing with original): {e}")

                # Phase 7: IR Constraint Validation (after repair, before assertions)
                # Validate that generated code satisfies IR-level constraints
                if ir.constraints:
                    from lift_sys.ir.constraint_messages import format_violations_summary

                    constraint_violations = self.constraint_validator.validate(complete_code, ir)

                    # Filter to error-level violations only (ignore warnings)
                    error_violations = [v for v in constraint_violations if v.severity == "error"]

                    if error_violations and attempt < max_retries - 1:
                        print(
                            f"  ⚠️ Constraint validation failed: {len(error_violations)} violation(s)"
                        )
                        for violation in error_violations[:3]:  # Show first 3 violations
                            print(f"    - {violation.description}")

                        # Format constraint violations with enhanced messages for next retry
                        # Build constraint lookup for better error messages
                        constraint_lookup = {
                            c.type.value if hasattr(c, "type") else "unknown": c
                            for c in ir.constraints
                        }

                        # Generate enhanced violation summary
                        enhanced_summary = format_violations_summary(
                            error_violations, constraint_lookup
                        )

                        self._validation_feedback = f"\n\n{enhanced_summary}"
                        continue
                    elif constraint_violations:
                        # Log violations but continue (may have warnings)
                        warning_violations = [
                            v for v in constraint_violations if v.severity == "warning"
                        ]
                        if warning_violations:
                            print(f"  ⚠️ Constraint warnings: {len(warning_violations)}")

                # Phase 5: Semantic Validation (Assertion Checking)
                # Validate generated code against IR assertions
                assertion_result = self.assertion_checker.validate(
                    code=complete_code, function_name=ir.signature.name, ir=ir
                )

                # If semantic validation fails and we have retries left, retry with feedback
                if not assertion_result.passed and attempt < max_retries - 1:
                    print(
                        f"  ⚠️ Assertion validation failed: {len(assertion_result.issues)} issue(s)"
                    )
                    for issue in assertion_result.issues[:3]:  # Show first 3 issues
                        print(f"    - {issue.message}")

                    # Format assertion issues as feedback for next retry
                    feedback_parts = ["\n\nPrevious attempt had assertion validation failures:"]

                    # Detect if this is a type-checking function returning wrong format
                    # (returning computed types instead of literal strings)
                    has_type_mismatch = any(
                        issue.expected
                        and issue.actual
                        and isinstance(issue.expected, str)
                        and (
                            str(issue.actual).startswith("<class ")
                            or (
                                isinstance(issue.actual, str)
                                and issue.actual not in [issue.expected]
                            )
                        )
                        for issue in assertion_result.issues
                        if issue.test_input and issue.expected and issue.actual
                    )

                    if has_type_mismatch:
                        feedback_parts.append(
                            "\n⚠️ CRITICAL: Function must return LITERAL STRING values, not computed types!\n"
                            "DO NOT use type(value) or type(value).__name__ or str(type(value)).\n"
                            "Use EXPLICIT string literals in return statements:\n"
                            "  ✓ Correct:   return 'int'    return 'str'    return 'list'    return 'other'\n"
                            "  ✗ Wrong:     return type(value)    return type(value).__name__\n"
                            "\n⚠️ PYTHON QUIRK: In Python, isinstance(True, int) returns True!\n"
                            "If checking for booleans, ALWAYS check bool BEFORE int:\n"
                            "  ✓ Correct order:   isinstance(value, bool), isinstance(value, int)\n"
                            "  ✗ Wrong order:     isinstance(value, int), isinstance(value, bool)\n"
                            "Otherwise True/False will incorrectly match 'int' instead of 'other'.\n"
                        )

                    for issue in assertion_result.issues[:5]:  # Include up to 5 issues
                        if issue.test_input and issue.expected and issue.actual:
                            feedback_parts.append(
                                f"- Test failed: {ir.signature.name}{issue.test_input} "
                                f"returned {repr(issue.actual)}, expected {repr(issue.expected)}"
                            )
                        else:
                            feedback_parts.append(f"- {issue.message}")

                    feedback_parts.append("\nPlease fix these issues in the next attempt.")
                    self._validation_feedback = "\n".join(feedback_parts)
                    continue

                # Validate code logic (Phase 2: Code Validation Layer)
                validation_issues = self.validator.validate(
                    code=complete_code,
                    function_name=ir.signature.name,
                    context={
                        "prompt": ir.intent.summary,
                        "effects": [e.description for e in ir.effects],
                    },
                )

                # If critical issues found and we have retries left, retry with feedback
                critical_issues = [i for i in validation_issues if i.severity == "error"]
                if critical_issues and attempt < max_retries - 1:
                    # Add validation feedback to next attempt
                    feedback = self.validator.format_issues_for_retry(critical_issues)
                    # Store feedback for next iteration
                    self._validation_feedback = feedback
                    continue

                # Determine which generator was used
                used_constrained = (
                    hasattr(self.provider, "generate_structured")
                    and self.provider.capabilities.structured_output
                )

                return GeneratedCode(
                    source_code=complete_code,
                    language="python",
                    metadata={
                        "ir_origin": ir.metadata.origin,
                        "generator": "xgrammar_constrained"
                        if used_constrained
                        else "xgrammar_text",
                        "attempts": attempt + 1,
                        "constrained_generation": used_constrained,
                    },
                    warnings=structural_code.warnings,
                )

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                if attempt == max_retries - 1:
                    raise ValueError(
                        f"Failed to generate valid implementation after {max_retries} attempts. Last error: {e}"
                    ) from e
                # Retry with feedback
                continue

        raise ValueError("Unexpected error in code generation")

    async def _generate_implementation(
        self,
        ir: IntermediateRepresentation,
        structure: dict[str, Any],
        attempt: int,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """
        Generate implementation JSON using constrained generation with XGrammar.

        Args:
            ir: IR to implement
            structure: Structural elements (signature, docstring, assertions)
            attempt: Current attempt number (for retry feedback)
            temperature: Sampling temperature (0.0 = deterministic, higher = more creative)

        Returns:
            Implementation as JSON dictionary (guaranteed to match schema)
        """
        # Build constraints from assertions
        constraints = []
        for assertion in ir.assertions:
            constraint_text = assertion.predicate
            if assertion.rationale:
                constraint_text += f" ({assertion.rationale})"
            constraints.append(constraint_text)

        # Extract effects as ordered implementation steps
        # Effects describe the operational semantics - the "how" not just the "what"
        effects = [effect.description for effect in ir.effects]

        # Get generation prompt with effects to constrain the implementation
        prompt = get_prompt_for_code_generation(
            ir_summary=ir.intent.summary,
            signature=structure["signature"],
            constraints=constraints,
            effects=effects if effects else None,
        )

        # Add attempt-specific feedback
        if attempt > 0:
            prompt += (
                f"\n\nPrevious attempt {attempt} failed. Please ensure correct implementation."
            )

        # Add validation feedback if available (from Phase 2: Validation Layer)
        if hasattr(self, "_validation_feedback") and self._validation_feedback:
            prompt += self._validation_feedback
            self._validation_feedback = ""  # Clear after use

        # Check if provider supports constrained generation (Modal with XGrammar)
        if (
            hasattr(self.provider, "generate_structured")
            and self.provider.capabilities.structured_output
        ):
            # Use constrained generation - guaranteed to match schema
            impl_json = await self.provider.generate_structured(
                prompt=prompt,
                schema=CODE_GENERATION_SCHEMA,
                max_tokens=2000,
                temperature=temperature,
            )
            return impl_json

        # Fallback to text generation for providers without structured output
        response = await self.provider.generate_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        # Extract JSON from response
        impl_json = self._extract_json(response)

        return impl_json

    def _extract_json(self, response: str) -> dict[str, Any]:
        """
        Extract JSON from LLM response, handling markdown code blocks.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If no valid JSON found
        """
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try markdown JSON block
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                return json.loads(response[start:end].strip())

        # Try generic markdown block
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return json.loads(response[start:end].strip())

        # Try to find JSON object
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response[start:end])

        raise json.JSONDecodeError("No valid JSON found in response", response, 0)

    def _validate_implementation(self, impl_json: dict[str, Any]) -> None:
        """
        Validate implementation JSON structure.

        Args:
            impl_json: Implementation JSON to validate

        Raises:
            ValueError: If validation fails
        """
        if "implementation" not in impl_json:
            raise ValueError("Missing required field: implementation")

        impl = impl_json["implementation"]

        if "body_statements" not in impl:
            raise ValueError("Missing required field: implementation.body_statements")

        if not isinstance(impl["body_statements"], list):
            raise ValueError("implementation.body_statements must be an array")

        if len(impl["body_statements"]) == 0:
            raise ValueError("implementation.body_statements cannot be empty")

        # Validate each statement
        for i, stmt in enumerate(impl["body_statements"]):
            if "type" not in stmt:
                raise ValueError(f"Statement {i} missing required field: type")
            if "code" not in stmt:
                raise ValueError(f"Statement {i} missing required field: code")

    def _parse_structural_code(self, source_code: str) -> dict[str, Any]:
        """
        Parse structural code to extract signature, docstring, and assertions.

        Args:
            source_code: Generated structural code (from CodeGenerator)

        Returns:
            Dictionary with extracted structural elements
        """
        lines = source_code.split("\n")

        # Extract imports (before function def)
        imports = []
        signature_start = None
        for i, line in enumerate(lines):
            if line.startswith("def "):
                signature_start = i
                break
            elif line.startswith("import ") or line.startswith("from "):
                imports.append(line)

        if signature_start is None:
            raise ValueError("No function definition found in structural code")

        # Extract signature (may span multiple lines)
        signature_lines = []
        i = signature_start
        while i < len(lines):
            signature_lines.append(lines[i])
            if lines[i].rstrip().endswith(":"):
                break
            i += 1

        signature = "\n".join(signature_lines)

        # Extract docstring (if present)
        docstring = None
        docstring_start = i + 1
        if docstring_start < len(lines) and '"""' in lines[docstring_start]:
            docstring_lines = []
            in_docstring = False
            for j in range(docstring_start, len(lines)):
                if '"""' in lines[j]:
                    if in_docstring:
                        docstring_lines.append(lines[j])
                        break
                    else:
                        in_docstring = True
                        docstring_lines.append(lines[j])
                elif in_docstring:
                    docstring_lines.append(lines[j])

            if docstring_lines:
                docstring = "\n".join(docstring_lines)

        # Extract assertions (preconditions before raise NotImplementedError)
        assertions = []
        for line in lines[i + 1 :]:
            line_stripped = line.strip()
            if line_stripped.startswith("assert "):
                assertions.append(line_stripped)
            elif line_stripped.startswith("raise NotImplementedError"):
                break

        return {
            "imports": imports,
            "signature": signature,
            "docstring": docstring,
            "assertions": assertions,
        }

    def _detect_typing_imports(
        self, structure: dict[str, Any], impl_json: dict[str, Any]
    ) -> list[str]:
        """
        Detect required typing imports by scanning signature and implementation.

        Args:
            structure: Structural elements including signature
            impl_json: Implementation JSON

        Returns:
            List of typing constructs that need to be imported
        """
        import re

        # Combine all code to scan
        code_to_scan = structure["signature"]
        for stmt in impl_json["implementation"].get("body_statements", []):
            code_to_scan += " " + stmt.get("code", "")

        # Typing constructs to detect (order matters - check Optional before Option, etc.)
        typing_constructs = [
            "Any",
            "Optional",
            "Union",
            "Callable",
            "TypeVar",
            "Generic",
            "Protocol",
            "Literal",
            "TypedDict",
            "Sequence",
            "Mapping",
            "Iterable",
            "Iterator",
        ]

        detected = []
        for construct in typing_constructs:
            # Use word boundary to avoid matching substrings
            if re.search(rf"\b{construct}\b", code_to_scan):
                detected.append(construct)

        return detected

    def _combine_structure_and_implementation(
        self,
        structure: dict[str, Any],
        impl_json: dict[str, Any],
    ) -> str:
        """
        Combine structural elements with generated implementation.

        Args:
            structure: Signature, docstring, assertions from structural generator
            impl_json: Implementation JSON from xgrammar generation

        Returns:
            Complete Python source code
        """
        lines = []
        indent = self.config.indent

        # Add imports from structure
        if structure["imports"]:
            lines.extend(structure["imports"])
            lines.append("")

        # Detect and add typing imports if needed
        typing_imports = self._detect_typing_imports(structure, impl_json)
        if typing_imports:
            lines.append(f"from typing import {', '.join(typing_imports)}")
            lines.append("")

        # Add additional imports from implementation
        if "imports" in impl_json:
            for imp in impl_json["imports"]:
                module = imp["module"]
                names = ", ".join(imp["names"])
                lines.append(f"from {module} import {names}")
            if impl_json["imports"]:
                lines.append("")

        # Add helper functions (if any)
        if "helper_functions" in impl_json:
            for helper in impl_json["helper_functions"]:
                lines.append(f"def {helper['signature']}:")
                # Indent helper body
                for body_line in helper["body"].split("\n"):
                    lines.append(f"{indent}{body_line}")
                lines.append("")
                lines.append("")

        # Add function signature
        lines.append(structure["signature"])

        # Add docstring (if present) - already has indentation
        if structure["docstring"]:
            for line in structure["docstring"].split("\n"):
                lines.append(line)

        # Add assertions (need to add indentation back)
        # DISABLED: Assertions from specifications are often contradictory
        # TODO: Fix assertion generation logic to be conditional, not absolute
        # if structure["assertions"]:
        #     for assertion in structure["assertions"]:
        #         lines.append(f"{indent}{assertion}")
        #     lines.append("")

        # Add implementation body
        impl = impl_json["implementation"]

        # Add algorithm comment (if present)
        if impl.get("algorithm"):
            algorithm_text = impl["algorithm"]
            # Handle multi-line algorithms by adding # to each line
            algorithm_lines = algorithm_text.split("\n")
            for i, algo_line in enumerate(algorithm_lines):
                if i == 0:
                    lines.append(f"{indent}# Algorithm: {algo_line.strip()}")
                else:
                    # Continuation lines
                    lines.append(f"{indent}# {algo_line.strip()}")
            lines.append("")

        # Add body statements with proper indentation handling
        # Strategy: Stack-based indentation tracking for nested control flow

        control_flow_types = {
            "if_statement",
            "for_loop",
            "while_loop",
            "elif_statement",
            "else_statement",
        }
        indent_stack = [indent]  # Stack of indentation levels

        for i, stmt in enumerate(impl["body_statements"]):
            code = stmt["code"].rstrip()  # Remove trailing whitespace
            stmt_type = stmt.get("type", "expression")  # Get statement type

            # Check if previous statement opened a control flow block
            if i > 0:
                prev_stmt = impl["body_statements"][i - 1]
                prev_type = prev_stmt.get("type", "expression")
                prev_code = prev_stmt["code"].rstrip()

                # Handle else/elif FIRST - pop to same level as if
                if (
                    stmt_type in {"elif_statement", "else_statement"}
                    or code.startswith("else")
                    or code.startswith("elif")
                ):
                    if len(indent_stack) > 1:
                        indent_stack.pop()  # Go back one level

                # Heuristic: After a return inside a control block, next non-return/elif/else should exit
                # Example: if n == 0: return 1; if n < 0: ...  <- second if should be at base level
                if prev_type == "return" and len(indent_stack) > 1:
                    # If current is NOT return/elif/else, it should be outside the previous control block
                    if stmt_type not in {"return", "elif_statement", "else_statement"}:
                        indent_stack.pop()

                # If previous statement was control flow ending with ':', increase indent
                if prev_type in control_flow_types and prev_code.endswith(":"):
                    indent_stack.append(indent_stack[-1] + "    ")

                # Heuristic: Return after return likely means exiting the control block
                # Example: if x: return A; return B  <- B should be outside if
                if stmt_type == "return" and prev_type == "return" and len(indent_stack) > 1:
                    # Pop one level to exit the control block
                    indent_stack.pop()

                # Heuristic: If current is return and we're deeply nested (3+ levels),
                # AND prev was not a control flow that just pushed, pop to base level
                # This handles "for...if...append; return" where return should be outside both blocks
                elif stmt_type == "return" and len(indent_stack) > 2:
                    # Only pop if previous wasn't control flow (otherwise we just pushed for a reason)
                    if prev_type not in control_flow_types:
                        # Pop to base level for final returns
                        indent_stack = [indent]

            current_indent = indent_stack[-1]

            # Add rationale as comment (if present)
            if stmt.get("rationale"):
                lines.append(f"{current_indent}# {stmt['rationale']}")

            # FIX: If this is a return statement, ensure code starts with 'return'
            if stmt_type == "return" and not code.strip().startswith("return"):
                code = f"return {code}"

            # Check if this is a multiline statement with embedded indentation
            code_lines = code.split("\n")
            is_multiline = len(code_lines) > 1

            if is_multiline:
                # Multiline code: preserve internal indentation, add current indent
                for code_line in code_lines:
                    if code_line.strip():
                        lines.append(f"{current_indent}{code_line}")
                    else:
                        lines.append("")
            else:
                # Single-line code: add current indentation
                if code.strip():
                    lines.append(f"{current_indent}{code.strip()}")
                else:
                    lines.append("")

        return "\n".join(lines)


__all__ = ["XGrammarCodeGenerator"]
