"""Round-trip validation for generated code."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum

from ..ir.models import IntermediateRepresentation, Parameter
from .generator import CodeGenerator


class DifferenceKind(str, Enum):
    """Type of difference found between IRs."""

    SIGNATURE_NAME = "signature_name"
    PARAMETER_COUNT = "parameter_count"
    PARAMETER_NAME = "parameter_name"
    PARAMETER_TYPE = "parameter_type"
    RETURN_TYPE = "return_type"
    INTENT_SUMMARY = "intent_summary"
    ASSERTION_COUNT = "assertion_count"
    ASSERTION_PREDICATE = "assertion_predicate"


@dataclass
class IRDifference:
    """A single difference between two IRs."""

    kind: DifferenceKind
    """Type of difference."""

    path: str
    """Path to the difference (e.g., 'signature.parameters[0].name')."""

    original_value: object
    """Value from original IR."""

    extracted_value: object
    """Value from extracted IR."""

    severity: str = "error"  # "error" | "warning" | "info"
    """How severe this difference is."""


@dataclass
class DiffResult:
    """Result of comparing two IRs."""

    differences: list[IRDifference] = field(default_factory=list)
    """List of differences found."""

    matches: int = 0
    """Number of fields that matched."""

    total_fields: int = 0
    """Total number of fields compared."""

    def is_match(self) -> bool:
        """Check if IRs match (no errors)."""
        return len([d for d in self.differences if d.severity == "error"]) == 0

    def fidelity_score(self) -> float:
        """Calculate fidelity score (0.0 to 1.0)."""
        if self.total_fields == 0:
            return 1.0
        return self.matches / self.total_fields


@dataclass
class RoundTripResult:
    """Result of round-trip validation."""

    original_ir: IntermediateRepresentation
    """The original IR."""

    generated_code: str
    """The generated code."""

    extracted_ir: IntermediateRepresentation
    """IR extracted from generated code."""

    diff_result: DiffResult
    """Comparison between original and extracted."""

    def is_valid(self) -> bool:
        """Check if round-trip validation passed."""
        return self.diff_result.is_match()

    def fidelity_score(self) -> float:
        """Get fidelity score (0.0 to 1.0)."""
        return self.diff_result.fidelity_score()


class IRDiffer:
    """Compares two IRs and finds differences."""

    def diff(
        self, original: IntermediateRepresentation, extracted: IntermediateRepresentation
    ) -> DiffResult:
        """Compare two IRs and return differences.

        Args:
            original: The original IR.
            extracted: The extracted IR.

        Returns:
            DiffResult with all differences found.
        """
        differences = []
        matches = 0
        total_fields = 0

        # Compare signature name
        total_fields += 1
        if original.signature.name == extracted.signature.name:
            matches += 1
        else:
            differences.append(
                IRDifference(
                    kind=DifferenceKind.SIGNATURE_NAME,
                    path="signature.name",
                    original_value=original.signature.name,
                    extracted_value=extracted.signature.name,
                )
            )

        # Compare return type
        total_fields += 1
        if original.signature.returns == extracted.signature.returns:
            matches += 1
        else:
            differences.append(
                IRDifference(
                    kind=DifferenceKind.RETURN_TYPE,
                    path="signature.returns",
                    original_value=original.signature.returns,
                    extracted_value=extracted.signature.returns,
                    severity="warning",  # Type differences are warnings
                )
            )

        # Compare parameter count
        total_fields += 1
        orig_param_count = len(original.signature.parameters)
        ext_param_count = len(extracted.signature.parameters)
        if orig_param_count == ext_param_count:
            matches += 1
        else:
            differences.append(
                IRDifference(
                    kind=DifferenceKind.PARAMETER_COUNT,
                    path="signature.parameters",
                    original_value=orig_param_count,
                    extracted_value=ext_param_count,
                )
            )

        # Compare individual parameters
        for i in range(min(orig_param_count, ext_param_count)):
            orig_param = original.signature.parameters[i]
            ext_param = extracted.signature.parameters[i]

            # Compare parameter name
            total_fields += 1
            if orig_param.name == ext_param.name:
                matches += 1
            else:
                differences.append(
                    IRDifference(
                        kind=DifferenceKind.PARAMETER_NAME,
                        path=f"signature.parameters[{i}].name",
                        original_value=orig_param.name,
                        extracted_value=ext_param.name,
                    )
                )

            # Compare parameter type
            total_fields += 1
            if orig_param.type_hint == ext_param.type_hint:
                matches += 1
            else:
                differences.append(
                    IRDifference(
                        kind=DifferenceKind.PARAMETER_TYPE,
                        path=f"signature.parameters[{i}].type_hint",
                        original_value=orig_param.type_hint,
                        extracted_value=ext_param.type_hint,
                        severity="warning",
                    )
                )

        # Compare intent summary (relaxed - just check if present)
        total_fields += 1
        if original.intent.summary and extracted.intent.summary:
            matches += 1
        else:
            differences.append(
                IRDifference(
                    kind=DifferenceKind.INTENT_SUMMARY,
                    path="intent.summary",
                    original_value=original.intent.summary,
                    extracted_value=extracted.intent.summary,
                    severity="info",
                )
            )

        # Compare assertion count
        total_fields += 1
        orig_assert_count = len(original.assertions)
        ext_assert_count = len(extracted.assertions)
        if orig_assert_count == ext_assert_count:
            matches += 1
        else:
            differences.append(
                IRDifference(
                    kind=DifferenceKind.ASSERTION_COUNT,
                    path="assertions",
                    original_value=orig_assert_count,
                    extracted_value=ext_assert_count,
                    severity="warning",
                )
            )

        # Compare individual assertions (predicates only)
        for i in range(min(orig_assert_count, ext_assert_count)):
            total_fields += 1
            orig_pred = original.assertions[i].predicate
            ext_pred = extracted.assertions[i].predicate
            if orig_pred.strip() == ext_pred.strip():
                matches += 1
            else:
                differences.append(
                    IRDifference(
                        kind=DifferenceKind.ASSERTION_PREDICATE,
                        path=f"assertions[{i}].predicate",
                        original_value=orig_pred,
                        extracted_value=ext_pred,
                        severity="warning",
                    )
                )

        return DiffResult(differences=differences, matches=matches, total_fields=total_fields)


class SimpleIRExtractor:
    """Extracts IR from generated Python code using AST parsing."""

    def extract(self, code: str) -> IntermediateRepresentation:
        """Extract IR from generated code.

        Args:
            code: Python source code.

        Returns:
            IntermediateRepresentation extracted from the code.

        Raises:
            ValueError: If code cannot be parsed or no function found.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code: {e}") from e

        # Find the first function definition
        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_def = node
                break

        if not func_def:
            raise ValueError("No function definition found in code")

        # Extract signature
        parameters = []
        for arg in func_def.args.args:
            param_name = arg.arg
            param_type = "Any"  # Default

            # Extract type annotation if present
            if arg.annotation:
                param_type = self._ast_to_type_string(arg.annotation)

            parameters.append(Parameter(name=param_name, type_hint=param_type))

        # Extract return type
        return_type = None
        if func_def.returns:
            return_type = self._ast_to_type_string(func_def.returns)

        # Extract docstring (intent)
        intent_summary = ""
        if (
            func_def.body
            and isinstance(func_def.body[0], ast.Expr)
            and isinstance(func_def.body[0].value, ast.Constant)
        ):
            docstring = func_def.body[0].value.value
            if isinstance(docstring, str):
                # Extract first line as summary
                intent_summary = docstring.split("\n")[0].strip().strip("\"'")

        # Extract assertions
        assertions = []
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assert):
                # Extract predicate from assert statement
                predicate = self._ast_to_string(node.test)
                # Extract rationale from message if present
                rationale = None
                if node.msg and isinstance(node.msg, ast.Constant):
                    rationale = node.msg.value

                from ..ir.models import AssertClause

                assertions.append(AssertClause(predicate=predicate, rationale=rationale))

        # Build IR
        from ..ir.models import IntentClause, Metadata, SigClause

        return IntermediateRepresentation(
            intent=IntentClause(summary=intent_summary),
            signature=SigClause(name=func_def.name, parameters=parameters, returns=return_type),
            assertions=assertions,
            metadata=Metadata(origin="extracted"),
        )

    def _ast_to_type_string(self, node: ast.AST) -> str:
        """Convert AST type annotation to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            # Generic type like list[int]
            base = self._ast_to_type_string(node.value)
            index = self._ast_to_type_string(node.slice)
            return f"{base}[{index}]"
        elif isinstance(node, ast.Tuple):
            # Multiple type parameters like dict[str, int]
            elements = [self._ast_to_type_string(elt) for elt in node.elts]
            return ", ".join(elements)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union type like str | None
            left = self._ast_to_type_string(node.left)
            right = self._ast_to_type_string(node.right)
            return f"{left} | {right}"
        else:
            # Fallback
            return ast.unparse(node) if hasattr(ast, "unparse") else "Any"

    def _ast_to_string(self, node: ast.AST) -> str:
        """Convert AST node to string representation."""
        if hasattr(ast, "unparse"):
            return ast.unparse(node)
        else:
            # Fallback for older Python
            return ast.dump(node)


class RoundTripValidator:
    """Validates round-trip fidelity of code generation."""

    def __init__(
        self,
        code_generator: CodeGenerator | None = None,
        ir_extractor: SimpleIRExtractor | None = None,
        ir_differ: IRDiffer | None = None,
    ):
        """Initialize validator with optional custom components.

        Args:
            code_generator: Code generator to use (optional).
            ir_extractor: IR extractor to use (optional).
            ir_differ: IR differ to use (optional).
        """
        self.code_generator = code_generator or CodeGenerator()
        self.ir_extractor = ir_extractor or SimpleIRExtractor()
        self.ir_differ = ir_differ or IRDiffer()

    def validate(self, ir: IntermediateRepresentation) -> RoundTripResult:
        """Perform round-trip validation on an IR.

        Generates code from IR, extracts IR from generated code,
        and compares the two IRs.

        Args:
            ir: The IR to validate.

        Returns:
            RoundTripResult with validation details.

        Raises:
            GenerationError: If code generation fails.
            ValueError: If IR extraction fails.
        """
        # Step 1: Generate code from IR
        generated_code_obj = self.code_generator.generate(ir)
        generated_code = generated_code_obj.source_code

        # Step 2: Extract IR from generated code
        extracted_ir = self.ir_extractor.extract(generated_code)

        # Step 3: Compare IRs
        diff_result = self.ir_differ.diff(ir, extracted_ir)

        return RoundTripResult(
            original_ir=ir,
            generated_code=generated_code,
            extracted_ir=extracted_ir,
            diff_result=diff_result,
        )
