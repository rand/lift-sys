"""Main code generator facade for IR-to-code translation."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ..ir.models import IntermediateRepresentation, TypedHole
from .assertion_injector import (
    AssertionInjector,
    AssertionMode,
    DefaultAssertionInjector,
)
from .docstring_generator import DefaultDocstringGenerator, DocstringGenerator
from .models import GeneratedCode, ValidationResult
from .type_resolver import DefaultTypeResolver, TypeResolver


class GenerationError(Exception):
    """Base exception for code generation errors."""

    pass


class IncompleteIRError(GenerationError):
    """IR contains unresolved typed holes."""

    def __init__(self, holes: list[TypedHole]):
        self.holes = holes
        hole_ids = ", ".join(h.identifier for h in holes)
        super().__init__(f"IR contains unresolved holes: {hole_ids}")


class InvalidIRError(GenerationError):
    """IR is structurally invalid."""

    def __init__(self, ir: IntermediateRepresentation, reason: str):
        self.ir = ir
        self.reason = reason
        super().__init__(f"Invalid IR: {reason}")


@dataclass
class CodeGeneratorConfig:
    """Configuration for code generation."""

    inject_assertions: bool = True
    """Whether to inject runtime assertion checks."""

    assertion_mode: AssertionMode = "assert"
    """How to handle assertion violations (assert/raise/log/comment)."""

    include_docstrings: bool = True
    """Whether to generate docstrings from intent."""

    include_type_hints: bool = True
    """Whether to include type annotations."""

    format_code: bool = False  # Formatting can be added later
    """Whether to format generated code (e.g., with black)."""

    preserve_metadata: bool = True
    """Whether to include IR metadata as comments."""

    target_python_version: str = "3.10"
    """Target Python version for compatibility."""

    indent: str = "    "
    """Indentation string (default: 4 spaces)."""


class CodeGenerator:
    """Main facade for IR-to-code translation."""

    def __init__(
        self,
        config: CodeGeneratorConfig | None = None,
        type_resolver: TypeResolver | None = None,
        docstring_generator: DocstringGenerator | None = None,
        assertion_injector: AssertionInjector | None = None,
    ):
        """Initialize with optional custom components.

        Args:
            config: Configuration for code generation.
            type_resolver: Custom type resolver (optional).
            docstring_generator: Custom docstring generator (optional).
            assertion_injector: Custom assertion injector (optional).
        """
        self.config = config or CodeGeneratorConfig()
        self.type_resolver = type_resolver or DefaultTypeResolver(
            target_version=self.config.target_python_version
        )
        self.docstring_generator = docstring_generator or DefaultDocstringGenerator()
        self.assertion_injector = assertion_injector or DefaultAssertionInjector(
            indent=self.config.indent
        )

    def generate(self, ir: IntermediateRepresentation) -> GeneratedCode:
        """Generate code from a complete IR.

        Args:
            ir: The intermediate representation to translate.

        Returns:
            Generated code with metadata.

        Raises:
            GenerationError: If IR is invalid or generation fails.
            IncompleteIRError: If IR contains unresolved typed holes.
        """
        # Validate IR first
        validation = self.validate_ir(ir)
        if not validation.is_valid:
            if validation.unresolved_holes:
                raise IncompleteIRError(validation.unresolved_holes)
            else:
                raise InvalidIRError(ir, "; ".join(validation.errors))

        # Generate code
        warnings = validation.warnings.copy()
        lines = []

        # Add metadata as comments (if enabled)
        if self.config.preserve_metadata and ir.metadata.origin:
            lines.append(f"# Generated from IR (origin: {ir.metadata.origin})")
            if ir.metadata.source_path:
                lines.append(f"# Source: {ir.metadata.source_path}")
            lines.append("")

        # Generate imports (collect from type annotations)
        imports = self._collect_imports(ir)
        if imports:
            lines.extend(sorted(imports))
            lines.append("")

        # Generate function signature
        sig_lines = self._generate_signature(ir)
        lines.extend(sig_lines)

        # Generate docstring
        if self.config.include_docstrings:
            docstring = self.docstring_generator.generate(ir.intent, ir.signature)
            # Indent docstring
            doc_lines = docstring.content.split("\n")
            lines.extend([f"{self.config.indent}{line}" for line in doc_lines])

        # Generate function body
        body_lines = self._generate_body(ir)
        lines.extend(body_lines)

        # Join all lines
        source_code = "\n".join(lines)

        # Validate generated code is syntactically correct
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            raise GenerationError(f"Generated invalid Python syntax: {e}") from e

        return GeneratedCode(
            source_code=source_code,
            language="python",
            metadata={
                "ir_origin": ir.metadata.origin,
                "ir_source_path": ir.metadata.source_path,
            },
            warnings=warnings,
        )

    def validate_ir(self, ir: IntermediateRepresentation) -> ValidationResult:
        """Check if IR is ready for code generation.

        Args:
            ir: IR to validate.

        Returns:
            ValidationResult with any issues found.
        """
        errors = []
        warnings = []
        unresolved_holes = []
        missing_types = []

        # Check for unresolved typed holes
        holes = ir.typed_holes()
        if holes:
            unresolved_holes.extend(holes)
            errors.append(f"IR contains {len(holes)} unresolved typed holes")

        # Check for required fields
        if not ir.intent or not ir.intent.summary:
            errors.append("IR missing intent summary")

        if not ir.signature or not ir.signature.name:
            errors.append("IR missing signature name")

        # Check for missing type hints (warnings, not errors)
        if self.config.include_type_hints:
            for param in ir.signature.parameters:
                if not param.type_hint:
                    missing_types.append(param.name)
                    warnings.append(f"Parameter '{param.name}' missing type hint")

            if not ir.signature.returns:
                warnings.append("Function missing return type hint")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            unresolved_holes=unresolved_holes,
            missing_types=missing_types,
        )

    def _collect_imports(self, ir: IntermediateRepresentation) -> list[str]:
        """Collect all required imports from type annotations.

        Args:
            ir: IR to analyze for imports.

        Returns:
            List of import statements.
        """
        imports: set[str] = set()

        # Collect from parameters
        for param in ir.signature.parameters:
            if param.type_hint:
                try:
                    resolved = self.type_resolver.resolve(param.type_hint)
                    imports.update(resolved.imports)
                except Exception:
                    # Ignore type resolution errors in import collection
                    pass

        # Collect from return type
        if ir.signature.returns:
            try:
                resolved = self.type_resolver.resolve(ir.signature.returns)
                imports.update(resolved.imports)
            except Exception:
                pass

        return list(imports)

    def _generate_signature(self, ir: IntermediateRepresentation) -> list[str]:
        """Generate function signature.

        Args:
            ir: IR with signature information.

        Returns:
            List of code lines for the signature.
        """
        func_name = ir.signature.name

        # Generate parameters with type hints
        params = []
        for param in ir.signature.parameters:
            if self.config.include_type_hints and param.type_hint:
                try:
                    resolved = self.type_resolver.resolve(param.type_hint)
                    params.append(f"{param.name}: {resolved.annotation}")
                except Exception:
                    # Fallback to no type hint
                    params.append(param.name)
            else:
                params.append(param.name)

        # Generate return type hint
        return_hint = ""
        if self.config.include_type_hints and ir.signature.returns:
            try:
                resolved = self.type_resolver.resolve(ir.signature.returns)
                return_hint = f" -> {resolved.annotation}"
            except Exception:
                # Fallback to no return hint
                pass

        # Format signature
        if not params:
            sig = f"def {func_name}(){return_hint}:"
        elif len(params) <= 2:
            # Short signature on one line
            params_str = ", ".join(params)
            sig = f"def {func_name}({params_str}){return_hint}:"
        else:
            # Long signature on multiple lines
            lines = [f"def {func_name}("]
            for i, param in enumerate(params):
                if i < len(params) - 1:
                    lines.append(f"{self.config.indent}{param},")
                else:
                    lines.append(f"{self.config.indent}{param}")
            lines.append(f"){return_hint}:")
            return lines

        return [sig]

    def _generate_body(self, ir: IntermediateRepresentation) -> list[str]:
        """Generate function body with assertions.

        Injects assertions as:
        - Preconditions: At start of function
        - Postconditions: Before return (commented for stubs)
        - Invariants: With preconditions

        Args:
            ir: IR with intent and assertions.

        Returns:
            List of code lines for the body.
        """
        lines = []
        indent = self.config.indent

        # Inject assertions if enabled
        if self.config.inject_assertions and ir.assertions:
            injected = self.assertion_injector.inject_all(
                ir.assertions, mode=self.config.assertion_mode
            )

            # Separate by position
            preconditions = [a for a in injected if a.position == "precondition"]
            invariants = [a for a in injected if a.position == "invariant"]
            postconditions = [a for a in injected if a.position == "postcondition"]

            # Add preconditions and invariants at start
            for assertion in preconditions + invariants:
                for line in assertion.code_lines:
                    lines.append(f"{indent}{line}")

            # Add blank line if we have preconditions
            if preconditions or invariants:
                lines.append("")

            # Add postconditions as comments (since we're generating stubs)
            if postconditions:
                lines.append(f"{indent}# Postconditions (TODO: enforce after implementation):")
                for assertion in postconditions:
                    for line in assertion.code_lines:
                        lines.append(f"{indent}# {line}")
                lines.append("")

        # Generate stub implementation
        lines.append(f'{indent}raise NotImplementedError("TODO: Implement {ir.signature.name}")')

        return lines
