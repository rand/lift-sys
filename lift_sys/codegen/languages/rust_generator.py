"""Rust code generator with xgrammar-constrained generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .rust_schema import RUST_GENERATION_SCHEMA, get_prompt_for_rust_generation
from .rust_types import RustTypeResolver


class RustGenerator:
    """
    Generates Rust code from IR using xgrammar-constrained generation.

    Similar to TypeScriptGenerator but produces Rust instead of TypeScript.
    Supports schema-constrained generation with Modal provider.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: CodeGeneratorConfig | None = None,
        repository_path: Path | None = None,
    ):
        """
        Initialize Rust generator.

        Args:
            provider: LLM provider for code generation
            config: Code generation configuration
            repository_path: Optional repository path for LSP context
        """
        self.provider = provider
        self.config = config or CodeGeneratorConfig()
        self.type_resolver = RustTypeResolver()

        # Set up LSP context provider if repository path provided
        self.context_provider: LSPSemanticContextProvider | None = None
        if repository_path:
            lsp_config = LSPConfig(
                repository_path=repository_path,
                language="rust",
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
        Generate Rust code from IR.

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails

        Returns:
            GeneratedCode with Rust implementation

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

                    # Convert to Rust code
                    complete_code = self._build_rust_code(ir, impl_json, semantic_context)

                    # Validate Rust syntax
                    validation_result, error_output = self._validate_rust_syntax(complete_code)
                    if not validation_result:
                        # Validation failed, retry if attempts remaining
                        if attempt == max_retries - 1:
                            raise ValueError(
                                f"Generated invalid Rust syntax. Rustc Error: {error_output[:200]}"
                            )
                        continue

                    return GeneratedCode(
                        source_code=complete_code,
                        language="rust",
                        metadata={
                            "ir_origin": ir.metadata.origin,
                            "generator": "rust-xgrammar",
                            "attempts": attempt + 1,
                            "has_lsp_context": semantic_context is not None,
                        },
                        warnings=[],
                    )

                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    if attempt == max_retries - 1:
                        raise ValueError(
                            f"Failed to generate valid Rust after {max_retries} attempts. Last error: {e}"
                        ) from e
                    continue

            raise ValueError("Unexpected error in Rust generation")

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

        # Extract effects as implementation steps
        effects = [effect.description for effect in ir.effects] if ir.effects else None

        # Build Rust function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
        )

        # Get generation prompt using schema helper
        prompt = get_prompt_for_rust_generation(
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
            prompt += (
                f"\n\nPrevious attempt {attempt} failed. Please ensure correct Rust implementation."
            )

        # Check if provider supports constrained generation (Modal with XGrammar)
        if (
            hasattr(self.provider, "generate_structured")
            and hasattr(self.provider, "capabilities")
            and self.provider.capabilities.structured_output
        ):
            # Use constrained generation - guaranteed to match schema
            impl_json = await self.provider.generate_structured(
                prompt=prompt,
                schema=RUST_GENERATION_SCHEMA,
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

    def _build_rust_code(
        self,
        ir: IntermediateRepresentation,
        impl_json: dict[str, Any],
        semantic_context: Any,
    ) -> str:
        """Build complete Rust code from implementation JSON."""
        lines = []

        # Add use statements (imports)
        impl = impl_json.get("implementation", {})
        imports = impl_json.get("imports", [])

        # Add semantic context imports if available
        if semantic_context and hasattr(semantic_context, "import_patterns"):
            for pattern in semantic_context.import_patterns[:2]:
                if hasattr(pattern, "module") and hasattr(pattern, "common_imports"):
                    imports.append(
                        {
                            "path": pattern.module,
                            "items": pattern.common_imports[:2],
                        }
                    )

        # Deduplicate imports
        seen_paths = set()
        for imp in imports:
            path = imp.get("path", "")
            if path and path not in seen_paths:
                seen_paths.add(path)
                items = imp.get("items", [])
                alias = imp.get("alias")
                if items:
                    items_str = ", ".join(items)
                    use_stmt = f"use {path}::{{{items_str}}}"
                    if alias:
                        use_stmt += f" as {alias}"
                    lines.append(use_stmt + ";")
                else:
                    use_stmt = f"use {path}"
                    if alias:
                        use_stmt += f" as {alias}"
                    lines.append(use_stmt + ";")

        if lines:
            lines.append("")  # Blank line after imports

        # Add doc comment
        lines.append("/// " + ir.intent.summary)
        if ir.intent.rationale:
            lines.append("///")
            lines.append("/// " + ir.intent.rationale)
        lines.append("///")

        # Add parameter documentation
        for param in ir.signature.parameters:
            rust_type = self.type_resolver.resolve(param.type_hint).annotation
            lines.append("/// # Arguments")
            lines.append(f"/// * `{param.name}` - Parameter of type {rust_type}")

        # Add return documentation
        rust_return = self.type_resolver.resolve(ir.signature.returns).annotation
        if rust_return != "()":
            lines.append("///")
            lines.append("/// # Returns")
            lines.append(f"/// {rust_return}")

        # Add function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
        )

        lines.append(signature + " {")

        # Add variable declarations
        variables = impl.get("variables", [])
        if variables:
            for var in variables:
                var_name = var.get("name", "temp")
                var_type = var.get("type_hint", "()")
                mutability = var.get("mutability", "immutable")
                rust_type = self.type_resolver.resolve(var_type).annotation

                if mutability == "mut":
                    lines.append(f"    let mut {var_name}: {rust_type};")
                else:
                    lines.append(f"    let {var_name}: {rust_type};")
            lines.append("")

        # Add body statements
        body_statements = impl.get("body_statements", [])
        for i, stmt in enumerate(body_statements):
            code = stmt.get("code", "")
            rationale = stmt.get("rationale", "")

            # Add comment if rationale provided
            if rationale:
                lines.append(f"    // {rationale}")

            # Post-process code to ensure proper return
            # If it's the last statement and looks like a standalone expression, ensure proper return
            is_last_statement = i == len(body_statements) - 1
            stmt_type = stmt.get("type", "")

            # Rust allows implicit returns (no semicolon on last expression)
            # But if statement has explicit return, keep it
            if (
                is_last_statement
                and code.strip()
                and not any(
                    code.strip().startswith(keyword)
                    for keyword in ["return", "if", "match", "for", "while", "loop", "let"]
                )
                and rust_return != "()"
            ):
                # Standalone expression at end - use Rust implicit return (no semicolon)
                for code_line in code.split("\n"):
                    if code_line.strip():
                        lines.append(f"    {code_line}")
            else:
                # Add code with proper indentation and semicolon
                for code_line in code.split("\n"):
                    if code_line.strip():
                        # Add semicolon if not already present and not a block
                        if not code_line.rstrip().endswith((";", "{", "}")) and stmt_type not in [
                            "if_statement",
                            "match_expression",
                            "for_loop",
                            "while_loop",
                            "loop",
                        ]:
                            lines.append(f"    {code_line};")
                        else:
                            lines.append(f"    {code_line}")

        # Close function
        lines.append("}")

        return "\n".join(lines)

    def _validate_rust_syntax(self, code: str) -> tuple[bool, str]:
        """
        Validate Rust syntax using rustc.

        Args:
            code: Rust code to validate

        Returns:
            Tuple of (is_valid, error_output)
        """
        try:
            # Write to temporary file
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".rs", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run rustc --crate-type lib to check syntax only
                result = subprocess.run(
                    ["rustc", "--crate-type", "lib", "--", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                # rustc returns 0 for success
                is_valid = result.returncode == 0
                # rustc outputs errors to stderr
                error_output = result.stderr if not is_valid else ""
                return (is_valid, error_output)

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            # If rustc not available or other error, assume valid
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
