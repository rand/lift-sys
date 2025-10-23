"""Go code generator with xgrammar-constrained generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .go_schema import GO_GENERATION_SCHEMA, get_prompt_for_go_generation
from .go_types import GoTypeResolver


class GoGenerator:
    """
    Generates Go code from IR using xgrammar-constrained generation.

    Similar to TypeScriptGenerator but produces Go instead of TypeScript.
    Handles Go-specific patterns like error returns, defer, goroutines, and channels.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: CodeGeneratorConfig | None = None,
        repository_path: Path | None = None,
    ):
        """
        Initialize Go generator.

        Args:
            provider: LLM provider for code generation
            config: Code generation configuration
            repository_path: Optional repository path for LSP context
        """
        self.provider = provider
        self.config = config or CodeGeneratorConfig()
        self.type_resolver = GoTypeResolver()

        # Set up LSP context provider if repository path provided
        self.context_provider: LSPSemanticContextProvider | None = None
        if repository_path:
            lsp_config = LSPConfig(
                repository_path=repository_path,
                language="go",
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
        Generate Go code from IR.

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails

        Returns:
            GeneratedCode with Go implementation

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

                    # Convert to Go code
                    complete_code = self._build_go_code(ir, impl_json, semantic_context)

                    # Note: Go syntax validation would require running `go build` or `gofmt -e`
                    # which requires a valid Go module. Skipping for now, but could be added.

                    return GeneratedCode(
                        source_code=complete_code,
                        language="go",
                        metadata={
                            "ir_origin": ir.metadata.origin,
                            "generator": "go-xgrammar",
                            "attempts": attempt + 1,
                            "has_lsp_context": semantic_context is not None,
                        },
                        warnings=[],
                    )

                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    if attempt == max_retries - 1:
                        raise ValueError(
                            f"Failed to generate valid Go after {max_retries} attempts. Last error: {e}"
                        ) from e
                    continue

            raise ValueError("Unexpected error in Go generation")

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

        # Detect if function should return error
        returns_error = (
            any("error" in effect.description.lower() for effect in ir.effects)
            if ir.effects
            else False
        )

        # Build Go function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
            returns_error=returns_error,
        )

        # Get generation prompt using schema helper
        prompt = get_prompt_for_go_generation(
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
                f"\n\nPrevious attempt {attempt} failed. Please ensure correct Go implementation."
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
                schema=GO_GENERATION_SCHEMA,
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

    def _build_go_code(
        self,
        ir: IntermediateRepresentation,
        impl_json: dict[str, Any],
        semantic_context: Any,
    ) -> str:
        """Build complete Go code from implementation JSON."""
        lines = []

        # Add package declaration (default to main, but could be configurable)
        lines.append("package main")
        lines.append("")

        # Add imports
        impl = impl_json.get("implementation", {})
        imports = impl.get("imports", [])

        # Add semantic context imports if available
        if semantic_context and hasattr(semantic_context, "import_patterns"):
            for pattern in semantic_context.import_patterns[:2]:
                if pattern.module:
                    imports.append({"package": pattern.module})

        # Deduplicate and format imports
        if imports:
            seen_packages = set()
            import_lines = []
            for imp in imports:
                package = imp.get("package", "")
                alias = imp.get("alias")
                if package and package not in seen_packages:
                    seen_packages.add(package)
                    if alias:
                        import_lines.append(f'\t{alias} "{package}"')
                    else:
                        import_lines.append(f'\t"{package}"')

            if import_lines:
                lines.append("import (")
                lines.extend(import_lines)
                lines.append(")")
                lines.append("")

        # Add GoDoc comment
        lines.append("// " + ir.intent.summary)
        if ir.intent.rationale:
            lines.append("// ")
            lines.append("// " + ir.intent.rationale)

        # Detect if function should return error
        error_handling = impl.get("error_handling", {})
        returns_error = error_handling.get("returns_error", False)

        # Build function signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
            returns_error=returns_error,
        )

        lines.append(signature + " {")

        # Add variable declarations
        variables = impl.get("variables", [])
        if variables:
            for var in variables:
                var_name = var.get("name", "temp")
                var_type = var.get("type_hint", "interface{}")
                go_type = self.type_resolver.resolve(var_type).annotation
                lines.append(f"\tvar {var_name} {go_type}")
            lines.append("")

        # Add channel declarations if any
        channels = impl.get("channels", [])
        if channels:
            for ch in channels:
                ch_name = ch.get("name", "ch")
                elem_type = ch.get("element_type", "interface{}")
                go_elem = self.type_resolver.resolve(elem_type).annotation
                buffered = ch.get("buffered", False)
                buffer_size = ch.get("buffer_size", 0)

                if buffered and buffer_size:
                    lines.append(f"\t{ch_name} := make(chan {go_elem}, {buffer_size})")
                else:
                    lines.append(f"\t{ch_name} := make(chan {go_elem})")
            lines.append("")

        # Add defer statements at the beginning (they execute at end)
        defer_statements = impl.get("defer_statements", [])
        if defer_statements:
            for defer_stmt in defer_statements:
                code = defer_stmt.get("code", "")
                rationale = defer_stmt.get("rationale")
                if rationale:
                    lines.append(f"\t// {rationale}")
                lines.append(f"\tdefer {code}")
            lines.append("")

        # Add body statements
        body_statements = impl.get("body_statements", [])
        for i, stmt in enumerate(body_statements):
            stmt_type = stmt.get("type", "")
            code = stmt.get("code", "")
            rationale = stmt.get("rationale", "")

            # Add comment if rationale provided
            if rationale:
                lines.append(f"\t// {rationale}")

            # Post-process code based on statement type
            if stmt_type == "error_check":
                # Common Go error check pattern
                if "if err != nil" not in code:
                    code = "if err != nil {\n\t\treturn err\n\t}"

            # Add code with proper indentation
            for code_line in code.split("\n"):
                if code_line.strip():
                    lines.append(f"\t{code_line}")

        # Close function
        lines.append("}")

        return "\n".join(lines)

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
