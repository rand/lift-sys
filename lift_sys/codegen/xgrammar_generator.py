"""xgrammar-enhanced code generation for IR-to-code translation."""

from __future__ import annotations

import ast
import json
from typing import Any

from ..ir.models import IntermediateRepresentation
from ..providers.base import BaseProvider
from .code_schema import get_prompt_for_code_generation
from .generator import CodeGenerator, CodeGeneratorConfig, GeneratedCode


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
        self.structural_generator = CodeGenerator(config=self.config)

    async def generate(
        self,
        ir: IntermediateRepresentation,
        max_retries: int = 3,
    ) -> GeneratedCode:
        """
        Generate complete code from IR with actual implementation.

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails

        Returns:
            GeneratedCode with complete implementation

        Raises:
            ValueError: If generation fails after max_retries
        """
        # First, use structural generator to get signature, docstring, and structure
        structural_code = self.structural_generator.generate(ir)

        # Extract structural elements (signature, docstring, assertions)
        structure = self._parse_structural_code(structural_code.source_code)

        # Generate implementation using xgrammar
        for attempt in range(max_retries):
            try:
                impl_json = await self._generate_implementation(ir, structure, attempt)

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

                return GeneratedCode(
                    source_code=complete_code,
                    language="python",
                    metadata={
                        "ir_origin": ir.metadata.origin,
                        "generator": "xgrammar",
                        "attempts": attempt + 1,
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
    ) -> dict[str, Any]:
        """
        Generate implementation JSON using LLM.

        Args:
            ir: IR to implement
            structure: Structural elements (signature, docstring, assertions)
            attempt: Current attempt number (for retry feedback)

        Returns:
            Implementation as JSON dictionary
        """
        # Build constraints from assertions
        constraints = []
        for assertion in ir.assertions:
            constraint_text = assertion.predicate
            if assertion.rationale:
                constraint_text += f" ({assertion.rationale})"
            constraints.append(constraint_text)

        # Get generation prompt
        prompt = get_prompt_for_code_generation(
            ir_summary=ir.intent.summary,
            signature=structure["signature"],
            constraints=constraints,
        )

        # Add attempt-specific feedback
        if attempt > 0:
            prompt += f"\n\nPrevious attempt {attempt} failed. Please ensure valid JSON output with all required fields."

        # Generate using LLM
        response = await self.provider.generate_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,  # Lower temperature for more deterministic code
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
        if structure["assertions"]:
            for assertion in structure["assertions"]:
                lines.append(f"{indent}{assertion}")
            lines.append("")

        # Add implementation body
        impl = impl_json["implementation"]

        # Add algorithm comment (if present)
        if impl.get("algorithm"):
            lines.append(f"{indent}# Algorithm: {impl['algorithm']}")
            lines.append("")

        # Add body statements
        for stmt in impl["body_statements"]:
            code = stmt["code"]

            # Add rationale as comment (if present)
            if stmt.get("rationale"):
                lines.append(f"{indent}# {stmt['rationale']}")

            # Add the code (may be multi-line)
            for code_line in code.split("\n"):
                if code_line.strip():  # Skip empty lines
                    lines.append(f"{indent}{code_line}")
                else:
                    lines.append("")

        return "\n".join(lines)


__all__ = ["XGrammarCodeGenerator"]
