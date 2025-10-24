"""Java code generator with xgrammar-constrained generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# DSPy Architecture Integration (Phase A: Minimal Integration)
from ...dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig
from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .java_schema import JAVA_GENERATION_SCHEMA, get_prompt_for_java_generation
from .java_types import JavaTypeResolver


class JavaGenerator:
    """
    Generates Java code from IR using xgrammar-constrained generation.

    Similar to TypeScriptGenerator but produces Java instead of TypeScript.
    Follows the proven pattern: schema-constrained generation with Modal provider
    support and backward compatibility fallback.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: CodeGeneratorConfig | None = None,
        repository_path: Path | None = None,
    ):
        """
        Initialize Java generator.

        Args:
            provider: LLM provider for code generation
            config: Code generation configuration
            repository_path: Optional repository path for LSP context
        """
        self.provider = provider
        self.config = config or CodeGeneratorConfig()
        self.type_resolver = JavaTypeResolver(prefer_primitives=True)

        # Set up LSP context provider if repository path provided
        self.context_provider: LSPSemanticContextProvider | None = None
        if repository_path:
            lsp_config = LSPConfig(
                repository_path=repository_path,
                language="java",
                cache_enabled=True,
                metrics_enabled=True,
            )
            self.context_provider = LSPSemanticContextProvider(lsp_config)

        # DSPy Architecture Integration: Create ProviderAdapter for dual routing
        # This enables resource tracking (H14) and prepares for DSPy signature integration
        self.adapter = ProviderAdapter(
            provider=provider,
            config=ProviderConfig(
                max_tokens=2000,
                temperature=0.3,
                use_xgrammar=True,  # Enable XGrammar constraints when available
            ),
        )

    async def generate(
        self,
        ir: IntermediateRepresentation,
        max_retries: int = 3,
    ) -> GeneratedCode:
        """
        Generate Java code from IR.

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails

        Returns:
            GeneratedCode with Java implementation

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

                    # Convert to Java code
                    complete_code = self._build_java_code(ir, impl_json, semantic_context)

                    # Validate Java syntax (if javac available)
                    validation_result, error_output = self._validate_java_syntax(complete_code)
                    if not validation_result:
                        # Validation failed, retry if attempts remaining
                        if attempt == max_retries - 1:
                            raise ValueError(
                                f"Generated invalid Java syntax. javac Error: {error_output[:200]}"
                            )
                        continue

                    return GeneratedCode(
                        source_code=complete_code,
                        language="java",
                        metadata={
                            "ir_origin": ir.metadata.origin,
                            "generator": "java-xgrammar",
                            "attempts": attempt + 1,
                            "has_lsp_context": semantic_context is not None,
                        },
                        warnings=[],
                    )

                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    if attempt == max_retries - 1:
                        raise ValueError(
                            f"Failed to generate valid Java after {max_retries} attempts. Last error: {e}"
                        ) from e
                    continue

            raise ValueError("Unexpected error in Java generation")

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

        # Build Java method signature
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]
        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
            access_modifier="public",
            is_static=False,
        )

        # Get generation prompt using schema helper
        prompt = get_prompt_for_java_generation(
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
                f"\n\nPrevious attempt {attempt} failed. Please ensure correct Java implementation."
            )

        # DSPy Architecture Integration: Use ProviderAdapter for dual routing
        # ProviderAdapter automatically:
        # - Routes to Modal (XGrammar) when schema provided and supported
        # - Falls back to best available provider otherwise
        # - Tracks token usage and LLM calls (H14 ResourceLimits)
        # - Prepares for future DSPy signature integration
        prediction = await self.adapter(
            prompt=prompt,
            schema=JAVA_GENERATION_SCHEMA,
            max_tokens=2000,
            temperature=0.3,
        )

        # Extract implementation dict from dspy.Prediction
        # ProviderAdapter returns prediction with fields: implementation, imports, etc.
        # Convert back to dict for compatibility with existing code
        impl_json = {
            k: v
            for k, v in prediction.__dict__.items()
            if not k.startswith("_")  # Filter out internal dspy attributes
        }

        return impl_json

    def _build_java_code(
        self,
        ir: IntermediateRepresentation,
        impl_json: dict[str, Any],
        semantic_context: Any,
    ) -> str:
        """Build complete Java code from implementation JSON."""
        lines = []

        # Add imports
        impl = impl_json.get("implementation", {})
        imports = impl_json.get("imports", [])

        # Add semantic context imports if available
        if semantic_context and semantic_context.import_patterns:
            for pattern in semantic_context.import_patterns[:2]:
                if pattern.module:
                    imports.append({"package": pattern.module, "is_static": False})

        # Deduplicate imports
        seen_imports = set()
        for imp in imports:
            package = imp.get("package", "")
            if package and package not in seen_imports:
                seen_imports.add(package)
                is_static = imp.get("is_static", False)
                if is_static:
                    lines.append(f"import static {package};")
                else:
                    lines.append(f"import {package};")

        if lines:
            lines.append("")  # Blank line after imports

        # Add Javadoc comment
        lines.append("/**")
        lines.append(f" * {ir.intent.summary}")
        if ir.intent.rationale:
            lines.append(" * <p>")
            lines.append(f" * {ir.intent.rationale}")
        lines.append(" *")

        # Add parameter documentation
        for param in ir.signature.parameters:
            java_type = self.type_resolver.resolve(param.type_hint).annotation
            lines.append(f" * @param {param.name} Parameter of type {java_type}")

        # Add return documentation
        java_return = self.type_resolver.resolve(ir.signature.returns).annotation
        if java_return != "void":
            lines.append(f" * @return {java_return}")

        # Add checked exceptions if any
        exception_handling = impl_json.get("exception_handling", {})
        checked_exceptions = exception_handling.get("checked_exceptions", [])
        for exc in checked_exceptions:
            lines.append(f" * @throws {exc}")

        lines.append(" */")

        # Add method annotations
        annotations = impl_json.get("annotations", [])
        for annotation in annotations:
            name = annotation.get("name", "")
            params = annotation.get("parameters")
            if params:
                lines.append(f"@{name}({params})")
            else:
                lines.append(f"@{name}")

        # Build method signature
        access_modifier = impl_json.get("access_modifier", "public")
        params = [(p.name, p.type_hint) for p in ir.signature.parameters]

        # Add generics if present
        generics = impl_json.get("generics", [])
        generic_str = ""
        if generics:
            type_params = []
            for g in generics:
                tp = g.get("type_parameter", "")
                bounds = g.get("bounds")
                if bounds:
                    type_params.append(f"{tp} {bounds}")
                else:
                    type_params.append(tp)
            generic_str = f"<{', '.join(type_params)}> "

        signature = self.type_resolver.format_function_signature(
            ir.signature.name,
            params,
            ir.signature.returns,
            access_modifier=access_modifier,
            is_static=False,
        )

        # Insert generics if present
        if generic_str:
            # Insert generics after access modifier and before return type
            parts = signature.split()
            # Find position of return type (after access modifier, possibly "static")
            insert_pos = 1
            if len(parts) > 1 and parts[1] == "static":
                insert_pos = 2
            parts.insert(insert_pos, generic_str.strip())
            signature = " ".join(parts)

        # Add throws clause if needed
        if checked_exceptions:
            signature += f" throws {', '.join(checked_exceptions)}"

        lines.append(signature + " {")

        # Add variable declarations
        variables = impl.get("variables", [])
        if variables:
            for var in variables:
                var_name = var.get("name", "temp")
                var_type = var.get("type_hint", "Object")
                java_type = self.type_resolver.resolve(var_type).annotation
                is_final = var.get("is_final", False)

                # Get default value
                default_value = self.type_resolver.get_default_value(var_type)

                if is_final:
                    lines.append(f"    final {java_type} {var_name} = {default_value};")
                else:
                    lines.append(f"    {java_type} {var_name} = {default_value};")
            lines.append("")

        # Add body statements
        body_statements = impl.get("body_statements", [])
        for i, stmt in enumerate(body_statements):
            code = stmt.get("code", "")
            rationale = stmt.get("rationale", "")
            stmt_type = stmt.get("type", "")

            # Add comment if rationale provided
            if rationale:
                lines.append(f"    // {rationale}")

            # Post-process code to fix missing return keywords
            # If it's the last statement and looks like a standalone expression, add return
            is_last_statement = i == len(body_statements) - 1
            if (
                is_last_statement
                and code.strip()
                and stmt_type not in ["return", "throw_statement"]
                and java_return != "void"
                and not any(
                    code.strip().startswith(keyword)
                    for keyword in [
                        "return",
                        "throw",
                        "if",
                        "for",
                        "while",
                        "try",
                        "switch",
                    ]
                )
            ):
                # Standalone expression at end - likely missing return keyword
                code = f"return {code.strip()};"

            # Ensure statement ends with semicolon (except control structures)
            if code.strip() and not code.rstrip().endswith((";", "{", "}")):
                if stmt_type not in [
                    "if_statement",
                    "for_loop",
                    "while_loop",
                    "try_catch",
                    "switch_statement",
                ]:
                    code = code.rstrip() + ";"

            # Add code with proper indentation
            for code_line in code.split("\n"):
                if code_line.strip():
                    lines.append(f"    {code_line}")

        # Close method
        lines.append("}")

        # Add helper methods
        helper_methods = impl_json.get("helper_methods", [])
        if helper_methods:
            lines.append("")
            for helper in helper_methods:
                lines.append("")
                access_mod = helper.get("access_modifier", "private")
                signature = helper.get("signature", "")
                body = helper.get("body", "")
                name = helper.get("name", "")

                lines.append("    /**")
                lines.append(f"     * Helper method: {name}")
                lines.append("     */")
                lines.append(f"    {access_mod} {signature} {{")
                for body_line in body.split("\n"):
                    if body_line.strip():
                        lines.append(f"        {body_line}")
                lines.append("    }")

        return "\n".join(lines)

    def _validate_java_syntax(self, code: str) -> tuple[bool, str]:
        """
        Validate Java syntax using javac (if available).

        Args:
            code: Java code to validate

        Returns:
            Tuple of (is_valid, error_output)
        """
        try:
            import tempfile

            # Create a temporary class file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".java", delete=False, prefix="JavaValidator"
            ) as f:
                # Wrap method in a class for javac validation
                class_code = f"public class JavaValidator {{\n{code}\n}}"
                f.write(class_code)
                temp_path = f.name

            try:
                # Run javac to check syntax only
                result = subprocess.run(
                    ["javac", "-Xlint:none", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                # javac returns 0 for success
                is_valid = result.returncode == 0
                # javac outputs errors to stderr
                error_output = result.stderr if not is_valid else ""
                return (is_valid, error_output)

            finally:
                # Clean up temp files
                Path(temp_path).unlink(missing_ok=True)
                # Also remove .class file if created
                class_file = Path(temp_path).with_suffix(".class")
                class_file.unlink(missing_ok=True)

        except Exception as e:
            # If javac not available or other error, assume valid
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
