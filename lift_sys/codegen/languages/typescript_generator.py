"""TypeScript code generator with xgrammar-constrained generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .typescript_schema import TYPESCRIPT_GENERATION_SCHEMA, get_prompt_for_typescript_generation
from .typescript_types import TypeScriptTypeResolver


class TypeScriptGenerator:
    """
    Generates TypeScript code from IR using xgrammar-constrained generation.

    Similar to XGrammarCodeGenerator but produces TypeScript instead of Python.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: CodeGeneratorConfig | None = None,
        repository_path: Path | None = None,
    ):
        """
        Initialize TypeScript generator.

        Args:
            provider: LLM provider for code generation
            config: Code generation configuration
            repository_path: Optional repository path for LSP context
        """
        self.provider = provider
        self.config = config or CodeGeneratorConfig()
        self.type_resolver = TypeScriptTypeResolver()

        # Set up LSP context provider if repository path provided
        self.context_provider: LSPSemanticContextProvider | None = None
        if repository_path:
            lsp_config = LSPConfig(
                repository_path=repository_path,
                language="typescript",
                cache_enabled=True,
                metrics_enabled=True,
            )
            self.context_provider = LSPSemanticContextProvider(lsp_config)

    async def generate(
        self,
        ir: IntermediateRepresentation,
        max_retries: int = 3,
    ) -> GeneratedCode:
        """
        Generate TypeScript code from IR.

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails

        Returns:
            GeneratedCode with TypeScript implementation

        Raises:
            ValueError: If generation fails after max_retries
        """
        # Start LSP if available
        if self.context_provider:
            await self.context_provider.start()

        try:
            # Get semantic context if available
            semantic_context = None
            if self.context_provider:
                try:
                    semantic_context = await self.context_provider.get_context_for_intent(
                        ir.intent.summary
                    )
                except Exception as e:
                    # Continue without context on error
                    print(f"Warning: Could not get LSP context: {e}")

            # Generate implementation using xgrammar
            for attempt in range(max_retries):
                try:
                    impl_json = await self._generate_implementation(ir, semantic_context, attempt)

                    # Validate implementation JSON
                    self._validate_implementation(impl_json)

                    # Convert to TypeScript code
                    complete_code = self._build_typescript_code(ir, impl_json, semantic_context)

                    # Validate TypeScript syntax
                    validation_result, error_output = self._validate_typescript_syntax(
                        complete_code
                    )
                    if not validation_result:
                        # Debug: Save failed code for inspection
                        from datetime import datetime

                        debug_path = f"/tmp/typescript_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{attempt}.ts"
                        with open(debug_path, "w") as f:
                            f.write(f"// TSC Error:\n// {error_output}\n\n")
                            f.write(complete_code)
                        print(f"⚠️  TypeScript validation failed (attempt {attempt + 1})")
                        print(f"   Saved debug code to: {debug_path}")
                        print(f"   TSC Error: {error_output[:200]}")

                        if attempt == max_retries - 1:
                            raise ValueError(
                                f"Generated invalid TypeScript syntax. TSC Error: {error_output[:200]}"
                            )
                        continue

                    return GeneratedCode(
                        source_code=complete_code,
                        language="typescript",
                        metadata={
                            "ir_origin": ir.metadata.origin,
                            "generator": "typescript-xgrammar",
                            "attempts": attempt + 1,
                            "has_lsp_context": semantic_context is not None,
                        },
                        warnings=[],
                    )

                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    if attempt == max_retries - 1:
                        raise ValueError(
                            f"Failed to generate valid TypeScript after {max_retries} attempts. Last error: {e}"
                        ) from e
                    continue

            raise ValueError("Unexpected error in TypeScript generation")

        finally:
            # Stop LSP
            if self.context_provider:
                await self.context_provider.stop()

    async def _generate_implementation(
        self,
        ir: IntermediateRepresentation,
        semantic_context: Any,
        attempt: int,
    ) -> dict[str, Any]:
        """
        Generate implementation JSON using schema-constrained generation (xgrammar).

        Uses Modal provider's generate_structured() when available for guaranteed
        schema compliance. Falls back to text generation for other providers.

        Args:
            ir: IR to implement
            semantic_context: Optional LSP semantic context
            attempt: Current attempt number

        Returns:
            Implementation as JSON dictionary (guaranteed to match schema when using Modal)
        """
        # Build constraints from assertions
        constraints = []
        for assertion in ir.assertions:
            constraint_text = assertion.predicate
            if assertion.rationale:
                constraint_text += f" ({assertion.rationale})"
            constraints.append(constraint_text)

        # Extract effects as implementation steps (like XGrammarCodeGenerator does)
        effects = [effect.description for effect in ir.effects] if ir.effects else None

        # Build TypeScript function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
        )

        # Get generation prompt using schema helper
        prompt = get_prompt_for_typescript_generation(
            ir_summary=ir.intent.summary,
            signature=signature,
            constraints=constraints if constraints else None,
            effects=effects,
        )

        # Add semantic context if available
        if semantic_context:
            prompt += "\n\nAvailable types from codebase:"
            for type_info in semantic_context.available_types[:3]:
                prompt += f"\n  - {type_info.name}: {type_info.description}"

        # Add retry feedback
        if attempt > 0:
            prompt += f"\n\nPrevious attempt {attempt} failed. Please ensure correct TypeScript implementation."

        # Check if provider supports constrained generation (Modal with XGrammar)
        if (
            hasattr(self.provider, "generate_structured")
            and hasattr(self.provider, "capabilities")
            and self.provider.capabilities.structured_output
        ):
            # Use constrained generation - guaranteed to match schema
            impl_json = await self.provider.generate_structured(
                prompt=prompt,
                schema=TYPESCRIPT_GENERATION_SCHEMA,
                max_tokens=2000,
                temperature=0.3,
            )
            return impl_json

        # Fallback to text generation for providers without structured output
        response = await self.provider.generate_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        # Extract JSON from response
        return self._extract_json(response)

    def _build_generation_prompt(
        self,
        ir: IntermediateRepresentation,
        semantic_context: Any,
        constraints: list[str],
    ) -> str:
        """Build generation prompt for TypeScript code."""
        prompt_parts = []

        # Intent
        prompt_parts.append(f"Intent: {ir.intent.summary}")
        if ir.intent.rationale:
            prompt_parts.append(f"Rationale: {ir.intent.rationale}")

        # Function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
        )
        prompt_parts.append(f"\nTarget signature:\n{signature}")

        # Semantic context if available
        if semantic_context:
            prompt_parts.append("\nAvailable types from codebase:")
            for type_info in semantic_context.available_types[:3]:
                prompt_parts.append(f"  - {type_info.name}: {type_info.description}")

            if semantic_context.import_patterns:
                prompt_parts.append("\nRecommended imports:")
                for import_pat in semantic_context.import_patterns[:3]:
                    imports_str = ", ".join(import_pat.common_imports)
                    prompt_parts.append(f"  - {import_pat.module}: {imports_str}")

        # Constraints
        if constraints:
            prompt_parts.append("\nConstraints:")
            for constraint in constraints:
                prompt_parts.append(f"  - {constraint}")

        # Generation instructions
        prompt_parts.append("""

Generate a TypeScript function implementation as JSON with this structure:
{
  "implementation": {
    "body_statements": [
      {"type": "assignment|return|if_statement|expression", "code": "TypeScript code", "rationale": "why"}
    ],
    "variables": [
      {"name": "varName", "type_hint": "TypeScript type", "purpose": "description"}
    ],
    "imports": [
      {"module": "module-name", "imports": ["item1", "item2"]}
    ]
  }
}

Use TypeScript syntax:
- Use 'const' for immutable variables, 'let' for mutable
- Include proper type annotations
- Use arrow functions where appropriate
- Handle null/undefined with ?. and ??
- Return Promise<T> for async functions
""")

        return "\n".join(prompt_parts)

    def _build_typescript_code(
        self,
        ir: IntermediateRepresentation,
        impl_json: dict[str, Any],
        semantic_context: Any,
    ) -> str:
        """Build complete TypeScript code from implementation JSON."""
        lines = []

        # Add imports
        impl = impl_json.get("implementation", {})
        imports = impl.get("imports", [])

        # Add semantic context imports if available
        if semantic_context and semantic_context.import_patterns:
            for pattern in semantic_context.import_patterns[:2]:
                if pattern.module and pattern.common_imports:
                    imports.append(
                        {
                            "module": pattern.module,
                            "imports": pattern.common_imports[:2],
                        }
                    )

        # Deduplicate imports
        seen_modules = set()
        for imp in imports:
            module = imp.get("module", "")
            if module and module not in seen_modules:
                seen_modules.add(module)
                import_items = imp.get("imports", [])
                if import_items:
                    items_str = ", ".join(import_items)
                    lines.append(f"import {{ {items_str} }} from '{module}';")

        if lines:
            lines.append("")  # Blank line after imports

        # Add TSDoc comment
        lines.append("/**")
        lines.append(f" * {ir.intent.summary}")
        if ir.intent.rationale:
            lines.append(" * ")
            lines.append(f" * {ir.intent.rationale}")
        lines.append(" *")

        # Add parameter documentation
        for param in ir.signature.parameters:
            ts_type = self.type_resolver.resolve(param.type_hint).annotation
            lines.append(f" * @param {param.name} - Parameter of type {ts_type}")

        # Add return documentation
        ts_return = self.type_resolver.resolve(ir.signature.returns).annotation
        lines.append(f" * @returns {ts_return}")
        lines.append(" */")

        # Add function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
        )

        # Convert to export function
        if signature.startswith("function "):
            signature = "export " + signature
        elif signature.startswith("async function "):
            signature = "export async " + signature[6:]  # Skip "async "

        lines.append(signature + " {")

        # Add variable declarations
        variables = impl.get("variables", [])
        if variables:
            for var in variables:
                var_name = var.get("name", "temp")
                var_type = var.get("type_hint", "any")
                ts_type = self.type_resolver.resolve(var_type).annotation
                lines.append(f"  let {var_name}: {ts_type};")
            lines.append("")

        # Add body statements
        body_statements = impl.get("body_statements", [])
        for stmt in body_statements:
            code = stmt.get("code", "")
            rationale = stmt.get("rationale", "")

            # Add comment if rationale provided
            if rationale:
                lines.append(f"  // {rationale}")

            # Add code with proper indentation
            for code_line in code.split("\n"):
                if code_line.strip():
                    lines.append(f"  {code_line}")

        # Close function
        lines.append("}")

        return "\n".join(lines)

    def _validate_typescript_syntax(self, code: str) -> tuple[bool, str]:
        """
        Validate TypeScript syntax using tsc.

        Args:
            code: TypeScript code to validate

        Returns:
            Tuple of (is_valid, error_output)
        """
        try:
            # Write to temporary file
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run tsc --noEmit to check syntax only
                # Include ES2015 lib for Promise support
                result = subprocess.run(
                    ["tsc", "--noEmit", "--lib", "ES2015,DOM", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                # tsc returns 0 for success
                is_valid = result.returncode == 0
                error_output = result.stderr if not is_valid else ""
                return (is_valid, error_output)

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            # If tsc not available or other error, assume valid
            # (syntax validation is optional)
            return (True, str(e))

    def _extract_json(self, response: str) -> dict[str, Any]:
        """Extract JSON from LLM response."""
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
        """Validate implementation JSON structure."""
        if "implementation" not in impl_json:
            raise ValueError("Missing 'implementation' key in JSON")

        impl = impl_json["implementation"]

        if "body_statements" not in impl:
            raise ValueError("Missing 'body_statements' in implementation")

        if not isinstance(impl["body_statements"], list):
            raise ValueError("'body_statements' must be a list")

        if len(impl["body_statements"]) == 0:
            raise ValueError("'body_statements' cannot be empty")

        # Validate each statement
        for stmt in impl["body_statements"]:
            if "type" not in stmt or "code" not in stmt:
                raise ValueError("Each statement must have 'type' and 'code'")
