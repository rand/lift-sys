# IR-to-Code Translation Architecture

**Design Document for lift-sys-24**
**Created**: October 13, 2025
**Updated**: October 14, 2025
**Status**: Partially Implemented (Week 3-4 complete, Constrained Generation Added)
**Owner**: Code Generation Team

---

## 🚨 CRITICAL REQUIREMENT: Constrained Generation for IR → Code

**IR → Code generation MUST use constrained generation with XGrammar**, just like Prompt → IR:

- **Schema**: `CODE_GENERATION_SCHEMA` enforces valid implementation structure
- **Benefit 1**: Speculative parallel decoding (vLLM optimization when using XGrammar)
- **Benefit 2**: Guaranteed schema-valid output (no JSON parsing failures)
- **Benefit 3**: Higher quality, more consistent code generation
- **Implementation**: `XGrammarCodeGenerator.generate()` now checks `provider.capabilities.structured_output` and uses `generate_structured()` when available

**Files Updated** (October 14, 2025):
- `lift_sys/codegen/xgrammar_generator.py` - Added constrained generation path
- `lift_sys/providers/modal_provider.py` - Implemented abstract methods for structured output
- `lift_sys/inference/modal_app.py` - Updated to support both IR and Code schemas

**Next Step**: Deploy updated Modal app to enable end-to-end constrained generation for both Prompt → IR and IR → Code.

---

## Implementation Status

**✅ Week 3-4 Implementation Complete** (October 14, 2025)

An initial working implementation has been completed using the xgrammar approach:

- **`lift_sys/codegen/xgrammar_generator.py`**: XGrammarCodeGenerator that wraps the existing CodeGenerator
  - Generates complete function implementations (not stubs)
  - Uses JSON schema for structured code generation
  - 100% syntax validity achieved (10/10 tests)

- **`lift_sys/codegen/code_schema.py`**: JSON schema for implementation generation
  - Defines structure for body_statements, variables, algorithm, complexity
  - Supports multiple statement types (assignment, return, if_statement, for_loop, etc.)

- **`lift_sys/codegen/semantic_generator.py`**: SemanticCodeGenerator with context awareness
  - PoC 2 validated: 1.17x average quality improvement with semantic context
  - Foundation for Week 5-6 ChatLSP integration

This document describes the full long-term architecture vision. The current implementation provides core functionality, and future work will expand toward the comprehensive component-based architecture described below.

**Next Steps**: Week 5-6 will add ChatLSP integration for semantic context, building on the semantic_generator foundation.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Goals and Non-Goals](#goals-and-non-goals)
3. [Architecture Overview](#architecture-overview)
4. [Component Interfaces](#component-interfaces)
5. [Design Decisions](#design-decisions)
6. [API Contracts](#api-contracts)
7. [Error Handling](#error-handling)
8. [Extension Points](#extension-points)
9. [Testing Strategy](#testing-strategy)
10. [Open Questions](#open-questions)

---

## Executive Summary

This document defines the architecture for translating Intermediate Representations (IRs) into executable Python code. The IR-to-code translator bridges the gap between abstract specifications and concrete implementations, enabling the forward mode workflow to generate deployable code from finalized IRs.

**Key Principles:**

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Composability**: Components can be used independently or combined
3. **Extensibility**: Easy to add support for new languages or code patterns
4. **Testability**: Every component has clear inputs/outputs for unit testing
5. **Roundtrip Fidelity**: Generated code should reverse-lift back to equivalent IR

---

## Goals and Non-Goals

### Goals

✅ **Generate syntactically valid Python code** from complete IRs
✅ **Inject assertions** as runtime checks in generated code
✅ **Handle effects** (I/O, mutations, exceptions) correctly
✅ **Resolve types** from IR type hints to Python type annotations
✅ **Preserve intent** through docstrings and comments
✅ **Support incremental generation** for streaming/progress updates
✅ **Enable round-trip validation** (code → IR → compare)

### Non-Goals

❌ Code optimization or performance tuning
❌ Multi-language support in initial version (Python only)
❌ Automatic bug fixing or code repair
❌ GUI or interactive code editing
❌ Integration with external build systems

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    CodeGenerator (Facade)                    │
│  • Orchestrates all components                              │
│  • Manages generation pipeline                              │
│  • Handles errors and validation                            │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬───────────────┐
         ▼           ▼           ▼               ▼
    ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────┐
    │  Type   │ │Assertion│ │  Effect  │ │ DocString    │
    │Resolver │ │Injector │ │ Handler  │ │ Generator    │
    └─────────┘ └─────────┘ └──────────┘ └──────────────┘
         │           │           │               │
         └───────────┴───────────┴───────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  CodeBuilder   │
            │  (AST/string)  │
            └────────────────┘
                     │
                     ▼
              Generated Python
```

### Component Responsibilities

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **CodeGenerator** | Orchestrate generation pipeline | `IntermediateRepresentation` | `GeneratedCode` |
| **TypeResolver** | Convert IR types to Python types | `str` (type hint) | `TypeAnnotation` |
| **AssertionInjector** | Convert assertions to runtime checks | `List[AssertClause]` | `List[str]` (code lines) |
| **EffectHandler** | Generate effect-handling code | `List[EffectClause]` | `EffectCode` |
| **DocstringGenerator** | Create function documentation | `IntentClause` | `str` (docstring) |
| **CodeBuilder** | Build AST or format code strings | Components | `str` (formatted code) |

---

## Component Interfaces

### 1. CodeGenerator (Facade)

The main entry point for IR-to-code translation.

```python
from dataclasses import dataclass
from typing import Protocol
from pathlib import Path

from lift_sys.ir.models import IntermediateRepresentation


@dataclass
class GeneratedCode:
    """Result of code generation."""

    source_code: str
    """The generated Python source code."""

    language: str = "python"
    """Target language (always 'python' for now)."""

    ir_version: int | None = None
    """Version of the IR this was generated from."""

    metadata: dict[str, object] = field(default_factory=dict)
    """Additional metadata (imports, dependencies, etc.)."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings during generation."""


@dataclass
class CodeGeneratorConfig:
    """Configuration for code generation."""

    inject_assertions: bool = True
    """Whether to inject runtime assertion checks."""

    assertion_mode: str = "assert"  # "assert" | "raise" | "log"
    """How to handle assertion violations."""

    include_docstrings: bool = True
    """Whether to generate docstrings from intent."""

    include_type_hints: bool = True
    """Whether to include type annotations."""

    format_code: bool = True
    """Whether to format generated code (e.g., with black)."""

    preserve_metadata: bool = True
    """Whether to include IR metadata as comments."""

    target_python_version: str = "3.10"
    """Target Python version for compatibility."""


class CodeGenerator:
    """Main facade for IR-to-code translation."""

    def __init__(
        self,
        config: CodeGeneratorConfig | None = None,
        type_resolver: TypeResolver | None = None,
        assertion_injector: AssertionInjector | None = None,
        effect_handler: EffectHandler | None = None,
        docstring_generator: DocstringGenerator | None = None,
    ):
        """Initialize with optional custom components."""
        self.config = config or CodeGeneratorConfig()
        self.type_resolver = type_resolver or DefaultTypeResolver()
        self.assertion_injector = assertion_injector or DefaultAssertionInjector()
        self.effect_handler = effect_handler or DefaultEffectHandler()
        self.docstring_generator = docstring_generator or DefaultDocstringGenerator()

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
        ...

    def generate_streaming(
        self,
        ir: IntermediateRepresentation
    ) -> Iterator[GenerationEvent]:
        """Generate code with progress events for streaming.

        Useful for long-running generations or UI progress updates.

        Yields:
            GenerationEvent: Progress updates and final result.
        """
        ...

    def validate_ir(self, ir: IntermediateRepresentation) -> ValidationResult:
        """Check if IR is ready for code generation.

        Returns:
            ValidationResult with any issues found.
        """
        ...


@dataclass
class GenerationEvent:
    """Event emitted during streaming generation."""

    stage: str  # "signature" | "body" | "assertions" | "formatting" | "complete"
    message: str
    progress: float  # 0.0 to 1.0
    partial_code: str | None = None
    result: GeneratedCode | None = None
```

**Design Rationale:**

- **Facade Pattern**: Simplifies the interface for users while maintaining component modularity
- **Dependency Injection**: Allows custom implementations of each component
- **Streaming Support**: Enables progress updates for long-running generations
- **Validation First**: Catches errors before attempting generation

---

### 2. TypeResolver

Converts IR type hints to Python type annotations.

```python
from typing import Protocol
from dataclasses import dataclass


@dataclass
class TypeAnnotation:
    """Resolved type annotation for Python code."""

    annotation: str
    """The Python type annotation string (e.g., "list[int]")."""

    imports: set[str] = field(default_factory=set)
    """Required imports (e.g., {"from typing import List"})."""

    is_generic: bool = False
    """Whether this is a generic type."""

    origin_type: str | None = None
    """Origin type for generics (e.g., "list" for "list[int]")."""


class TypeResolver(Protocol):
    """Protocol for resolving IR type hints to Python types."""

    def resolve(self, type_hint: str) -> TypeAnnotation:
        """Resolve a type hint from IR to Python annotation.

        Args:
            type_hint: Type hint string from IR (e.g., "list[int]", "str | None")

        Returns:
            TypeAnnotation with resolved type and required imports.

        Raises:
            TypeResolutionError: If type cannot be resolved.
        """
        ...

    def resolve_parameter_type(self, param: Parameter) -> TypeAnnotation:
        """Resolve type for a function parameter.

        Convenience method that may apply parameter-specific logic.
        """
        ...

    def resolve_return_type(self, return_hint: str | None) -> TypeAnnotation:
        """Resolve return type annotation.

        Returns TypeAnnotation("None") if return_hint is None.
        """
        ...


class DefaultTypeResolver:
    """Default implementation of TypeResolver for Python 3.10+."""

    def __init__(self, target_version: str = "3.10"):
        """Initialize with target Python version.

        Args:
            target_version: Python version string (e.g., "3.10", "3.11")
        """
        self.target_version = target_version
        self._type_map = self._build_type_map()

    def resolve(self, type_hint: str) -> TypeAnnotation:
        """Resolve type hint with Python 3.10+ syntax."""
        # Handle union types: "str | None"
        # Handle generics: "list[int]", "dict[str, int]"
        # Handle complex types: "Callable[[int], str]"
        # Map IR types to Python types
        ...

    def _build_type_map(self) -> dict[str, str]:
        """Build mapping of IR types to Python types.

        Returns:
            Dictionary mapping IR type names to Python type names.
        """
        return {
            "string": "str",
            "integer": "int",
            "boolean": "bool",
            "array": "list",
            "dictionary": "dict",
            # ... more mappings
        }
```

**Design Rationale:**

- **Protocol-based**: Allows alternative implementations (e.g., for Python 3.9 compatibility)
- **Import tracking**: Automatically tracks required imports for generated code
- **Version-aware**: Can generate compatible syntax for different Python versions
- **Type mapping**: Bridges IR type vocabulary to Python types

---

### 3. AssertionInjector

Converts IR assertions into runtime checks.

```python
from typing import Protocol, Literal
from dataclasses import dataclass

from lift_sys.ir.models import AssertClause


AssertionMode = Literal["assert", "raise", "log", "comment"]


@dataclass
class InjectedAssertion:
    """An assertion injected into generated code."""

    code_lines: list[str]
    """Lines of code implementing the assertion."""

    position: str  # "precondition" | "postcondition" | "invariant"
    """Where this assertion should be placed."""

    original_predicate: str
    """Original assertion predicate from IR."""

    rationale: str | None = None
    """Optional explanation for the assertion."""


class AssertionInjector(Protocol):
    """Protocol for injecting assertions into generated code."""

    def inject(
        self,
        assertion: AssertClause,
        mode: AssertionMode = "assert"
    ) -> InjectedAssertion:
        """Convert an assertion clause to executable code.

        Args:
            assertion: The assertion clause from IR.
            mode: How to handle assertion violations.

        Returns:
            InjectedAssertion with code and metadata.
        """
        ...

    def inject_all(
        self,
        assertions: list[AssertClause],
        mode: AssertionMode = "assert"
    ) -> list[InjectedAssertion]:
        """Inject multiple assertions."""
        ...


class DefaultAssertionInjector:
    """Default implementation for Python assertion injection."""

    def inject(
        self,
        assertion: AssertClause,
        mode: AssertionMode = "assert"
    ) -> InjectedAssertion:
        """Inject assertion as Python code.

        Examples:
        - assert mode: `assert x > 0, "x must be positive"`
        - raise mode: `if not (x > 0): raise ValueError("x must be positive")`
        - log mode: `if not (x > 0): logger.warning("Assertion failed: x > 0")`
        - comment mode: `# Assertion: x > 0 (x must be positive)`
        """
        predicate = assertion.predicate
        rationale = assertion.rationale or "Assertion from specification"

        if mode == "assert":
            code = f'assert {predicate}, "{rationale}"'
            return InjectedAssertion(
                code_lines=[code],
                position=self._infer_position(assertion),
                original_predicate=predicate,
                rationale=rationale,
            )
        elif mode == "raise":
            code = f'if not ({predicate}):\n    raise ValueError("{rationale}")'
            return InjectedAssertion(
                code_lines=code.split("\n"),
                position=self._infer_position(assertion),
                original_predicate=predicate,
                rationale=rationale,
            )
        # ... other modes

    def _infer_position(self, assertion: AssertClause) -> str:
        """Infer where assertion should be placed.

        Uses heuristics based on assertion content:
        - References to parameters → precondition
        - References to return value → postcondition
        - References to self/state → invariant
        """
        predicate = assertion.predicate.lower()

        if any(kw in predicate for kw in ["return", "result", "output"]):
            return "postcondition"
        elif any(kw in predicate for kw in ["self.", "state", "invariant"]):
            return "invariant"
        else:
            return "precondition"
```

**Design Rationale:**

- **Multiple modes**: Supports different assertion strategies (development vs. production)
- **Position inference**: Automatically determines where to place assertions
- **Preserves rationale**: Includes explanation for better debugging
- **Flexible output**: Can generate different assertion styles

---

### 4. EffectHandler

Generates code to handle effects (I/O, state mutations, exceptions).

```python
from typing import Protocol
from dataclasses import dataclass

from lift_sys.ir.models import EffectClause


@dataclass
class EffectCode:
    """Code generated to handle effects."""

    setup_lines: list[str] = field(default_factory=list)
    """Code to run before function body (e.g., open files)."""

    teardown_lines: list[str] = field(default_factory=list)
    """Code to run after function body (e.g., close files)."""

    error_handling: list[str] = field(default_factory=list)
    """Exception handling code."""

    imports: set[str] = field(default_factory=set)
    """Required imports for effect handling."""

    needs_context_manager: bool = False
    """Whether code needs to be wrapped in try/finally or with."""


class EffectHandler(Protocol):
    """Protocol for handling effects in generated code."""

    def handle(self, effect: EffectClause) -> EffectCode:
        """Generate code to handle a single effect.

        Args:
            effect: Effect clause from IR.

        Returns:
            EffectCode with setup/teardown.
        """
        ...

    def handle_all(self, effects: list[EffectClause]) -> EffectCode:
        """Handle multiple effects, merging setup/teardown."""
        ...


class DefaultEffectHandler:
    """Default effect handler for Python."""

    def handle(self, effect: EffectClause) -> EffectCode:
        """Generate effect-handling code.

        Recognizes common patterns:
        - "reads from file X" → open file for reading
        - "writes to file X" → open file for writing
        - "queries database" → connection setup/teardown
        - "calls external API" → error handling
        - "modifies state" → no special handling (Python default)
        - "raises exception" → try/except pattern
        """
        description = effect.description.lower()

        # File I/O patterns
        if "read" in description and "file" in description:
            return self._handle_file_read(effect)
        elif "write" in description and "file" in description:
            return self._handle_file_write(effect)

        # Database patterns
        elif "database" in description or "sql" in description:
            return self._handle_database(effect)

        # API patterns
        elif "api" in description or "http" in description:
            return self._handle_api_call(effect)

        # Exception patterns
        elif "raises" in description or "exception" in description:
            return self._handle_exception(effect)

        # Default: no special handling
        else:
            return EffectCode()

    def _handle_file_read(self, effect: EffectClause) -> EffectCode:
        """Generate code for reading from files."""
        # Extract filename from effect description or holes
        filename_param = self._extract_filename(effect)

        return EffectCode(
            setup_lines=[],  # Using context manager instead
            teardown_lines=[],
            error_handling=[
                "except FileNotFoundError:",
                "    raise FileNotFoundError(f\"File {{{filename_param}}} not found\")",
            ],
            imports={"from pathlib import Path"},
            needs_context_manager=True,
        )

    def _extract_filename(self, effect: EffectClause) -> str:
        """Extract filename parameter from effect."""
        # Check holes for filename
        for hole in effect.holes:
            if "file" in hole.identifier.lower():
                return hole.identifier
        # Default
        return "filename"
```

**Design Rationale:**

- **Pattern matching**: Recognizes common effect patterns in descriptions
- **Composable**: Can combine multiple effects with merged setup/teardown
- **Context-aware**: Determines if context managers or try/finally needed
- **Extensible**: Easy to add new effect patterns

---

### 5. DocstringGenerator

Creates function documentation from intent clauses.

```python
from typing import Protocol
from dataclasses import dataclass

from lift_sys.ir.models import IntentClause, SigClause


@dataclass
class Docstring:
    """Generated docstring for a function."""

    content: str
    """The formatted docstring content."""

    style: str = "google"  # "google" | "numpy" | "sphinx"
    """Docstring style used."""


class DocstringGenerator(Protocol):
    """Protocol for generating docstrings from IR."""

    def generate(
        self,
        intent: IntentClause,
        signature: SigClause
    ) -> Docstring:
        """Generate docstring from intent and signature.

        Args:
            intent: The intent clause describing purpose.
            signature: The function signature for parameter docs.

        Returns:
            Formatted docstring.
        """
        ...


class DefaultDocstringGenerator:
    """Default docstring generator using Google style."""

    def __init__(self, style: str = "google"):
        """Initialize with docstring style."""
        self.style = style

    def generate(
        self,
        intent: IntentClause,
        signature: SigClause
    ) -> Docstring:
        """Generate Google-style docstring."""
        lines = []

        # Summary (from intent)
        lines.append(f'"""{intent.summary}')

        # Extended description (from rationale)
        if intent.rationale:
            lines.append("")
            lines.append(intent.rationale)

        # Args section
        if signature.parameters:
            lines.append("")
            lines.append("Args:")
            for param in signature.parameters:
                desc = param.description or "TODO: Add description"
                lines.append(f"    {param.name}: {desc}")

        # Returns section
        if signature.returns:
            lines.append("")
            lines.append("Returns:")
            lines.append(f"    {signature.returns}: TODO: Add description")

        lines.append('"""')

        content = "\n".join(lines)
        return Docstring(content=content, style=self.style)
```

**Design Rationale:**

- **Multiple styles**: Supports different docstring conventions
- **Intent-driven**: Uses IR intent as primary documentation source
- **TODO markers**: Indicates where manual documentation is needed
- **Standard format**: Follows Python conventions for IDE support

---

## Design Decisions

### 1. AST vs. String Generation

**Decision**: Use string-based generation with optional AST formatting.

**Rationale**:
- **Pros**: Simpler to implement, easier to debug, faster for simple cases
- **Cons**: Harder to ensure syntactic correctness, more manual formatting
- **Mitigation**: Use Python `ast` module for validation, `black` for formatting

**Alternatives considered**:
- Pure AST generation (too complex for initial version)
- Template-based generation (not flexible enough for assertions/effects)

### 2. Assertion Modes

**Decision**: Support multiple assertion modes (assert/raise/log/comment).

**Rationale**:
- Development: Use `assert` for easy debugging
- Production: Use `raise` to avoid assertions being optimized away
- Monitoring: Use `log` for observability
- Documentation: Use `comment` for specification reference

### 3. Type Resolution Strategy

**Decision**: Map IR types to Python 3.10+ native types.

**Rationale**:
- Python 3.10+ has native union types (`str | None`)
- Generics use built-in types (`list[int]` not `List[int]`)
- Cleaner syntax, better IDE support
- Can add compatibility layer for older Python if needed

### 4. Effect Handling

**Decision**: Pattern-match effect descriptions rather than structured effect types.

**Rationale**:
- Current IR uses free-text effect descriptions
- Pattern matching is flexible and extensible
- Can add structured effects in future IR versions
- Fallback to no special handling for unknown patterns

### 5. Code Formatting

**Decision**: Optional formatting with `black` or similar tools.

**Rationale**:
- Generated code should be readable
- Let established tools handle formatting
- Avoid reinventing formatting logic
- Makes round-trip comparison easier

---

## API Contracts

### GenerationError Hierarchy

```python
class GenerationError(Exception):
    """Base exception for code generation errors."""
    pass


class IncompleteIRError(GenerationError):
    """IR contains unresolved typed holes."""

    def __init__(self, holes: list[TypedHole]):
        self.holes = holes
        hole_ids = ", ".join(h.identifier for h in holes)
        super().__init__(f"IR contains unresolved holes: {hole_ids}")


class TypeResolutionError(GenerationError):
    """Cannot resolve a type hint to Python type."""

    def __init__(self, type_hint: str, reason: str):
        self.type_hint = type_hint
        self.reason = reason
        super().__init__(f"Cannot resolve type '{type_hint}': {reason}")


class InvalidIRError(GenerationError):
    """IR is structurally invalid."""

    def __init__(self, ir: IntermediateRepresentation, reason: str):
        self.ir = ir
        self.reason = reason
        super().__init__(f"Invalid IR: {reason}")
```

### Validation Contract

```python
@dataclass
class ValidationResult:
    """Result of IR validation before generation."""

    is_valid: bool
    """Whether IR is ready for code generation."""

    errors: list[str] = field(default_factory=list)
    """Blocking errors that prevent generation."""

    warnings: list[str] = field(default_factory=list)
    """Non-blocking issues to be aware of."""

    unresolved_holes: list[TypedHole] = field(default_factory=list)
    """Typed holes that must be resolved."""

    missing_types: list[str] = field(default_factory=list)
    """Parameters or returns without type hints."""
```

---

## Error Handling

### Error Recovery Strategy

1. **Validation Phase**: Catch errors before generation starts
   - Check for unresolved holes
   - Verify type hints are resolvable
   - Validate signature completeness

2. **Generation Phase**: Fail fast with clear error messages
   - Stop on first critical error
   - Collect warnings for non-critical issues
   - Include context in error messages (line numbers, component)

3. **Fallback Behavior**:
   - Unresolvable type → `Any` with warning
   - Unknown effect → No special handling with warning
   - Malformed assertion → Comment with warning

### Error Context

```python
@dataclass
class GenerationContext:
    """Context for error reporting during generation."""

    current_component: str  # "signature" | "body" | "assertions" | etc.
    current_ir: IntermediateRepresentation
    generated_lines: list[str]
    errors: list[str]
    warnings: list[str]

    def add_error(self, message: str) -> None:
        """Add error with context."""
        self.errors.append(f"[{self.current_component}] {message}")

    def add_warning(self, message: str) -> None:
        """Add warning with context."""
        self.warnings.append(f"[{self.current_component}] {message}")
```

---

## Extension Points

### 1. Custom Type Resolvers

Users can provide custom type resolvers for domain-specific types:

```python
class CustomTypeResolver:
    """Resolver for domain-specific types."""

    def resolve(self, type_hint: str) -> TypeAnnotation:
        if type_hint.startswith("User"):
            return TypeAnnotation(
                annotation="UserModel",
                imports={"from myapp.models import UserModel"},
            )
        # Fallback to default resolver
        return default_resolver.resolve(type_hint)


generator = CodeGenerator(
    config=config,
    type_resolver=CustomTypeResolver(),
)
```

### 2. Custom Assertion Injectors

Support custom assertion frameworks:

```python
class PytestAssertionInjector:
    """Use pytest assertions for better error messages."""

    def inject(self, assertion: AssertClause, mode: str) -> InjectedAssertion:
        # Generate pytest-compatible assertions
        ...
```

### 3. Language-Specific Generators

Future support for other languages:

```python
class TypeScriptCodeGenerator(CodeGenerator):
    """Generate TypeScript instead of Python."""

    def __init__(self, config: TSCodeGeneratorConfig):
        super().__init__(
            config=config,
            type_resolver=TypeScriptTypeResolver(),
            assertion_injector=TypeScriptAssertionInjector(),
            # ...
        )
```

### 4. Custom Effect Handlers

Domain-specific effect handling:

```python
class AsyncEffectHandler(DefaultEffectHandler):
    """Handle async effects with await/async."""

    def handle(self, effect: EffectClause) -> EffectCode:
        if "async" in effect.description.lower():
            # Generate async/await code
            ...
        return super().handle(effect)
```

---

## Testing Strategy

### Unit Tests

Each component must have comprehensive unit tests:

1. **TypeResolver Tests**:
   - Built-in types: `str`, `int`, `list[int]`
   - Union types: `str | None`, `int | float`
   - Generic types: `dict[str, list[int]]`
   - Callable types: `Callable[[int], str]`
   - Edge cases: `Any`, `None`, invalid types

2. **AssertionInjector Tests**:
   - All assertion modes: assert, raise, log, comment
   - Position inference: precondition, postcondition, invariant
   - Complex predicates: logical operators, nested conditions
   - Edge cases: empty assertions, malformed predicates

3. **EffectHandler Tests**:
   - File I/O effects
   - Database effects
   - API call effects
   - Exception effects
   - Unknown effects (fallback)

4. **DocstringGenerator Tests**:
   - Simple intent → docstring
   - Intent with rationale
   - Multiple parameters
   - Return type documentation

5. **CodeGenerator Integration Tests**:
   - Simple function generation
   - Function with assertions
   - Function with effects
   - Complex function (all features)
   - Error cases: invalid IR, unresolved holes

### Round-Trip Tests

Critical for validating generation quality:

```python
def test_roundtrip_simple_function():
    """Generate code and verify it lifts back to equivalent IR."""

    # Start with IR
    original_ir = IntermediateRepresentation(
        intent=IntentClause(summary="Add two numbers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter("a", "int"),
                Parameter("b", "int"),
            ],
            returns="int",
        ),
    )

    # Generate code
    generator = CodeGenerator()
    result = generator.generate(original_ir)
    code = result.source_code

    # Reverse lift
    lifter = SpecificationLifter()
    extracted_ir = lifter.lift_code_string(code)

    # Compare IRs
    assert extracted_ir.signature.name == original_ir.signature.name
    assert len(extracted_ir.signature.parameters) == len(original_ir.signature.parameters)
    assert extracted_ir.signature.returns == original_ir.signature.returns
    # ... more assertions
```

### Property-Based Tests

Use hypothesis for property testing:

```python
from hypothesis import given, strategies as st

@given(
    name=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1),
    num_params=st.integers(min_value=0, max_value=10),
)
def test_generated_code_is_valid_python(name: str, num_params: int):
    """Generated code should always be syntactically valid."""

    # Build IR with random parameters
    ir = build_random_ir(name, num_params)

    # Generate code
    generator = CodeGenerator()
    result = generator.generate(ir)

    # Validate syntax
    try:
        ast.parse(result.source_code)
    except SyntaxError as e:
        pytest.fail(f"Generated invalid Python: {e}")
```

---

## Open Questions

### 1. How to handle code that requires external dependencies?

**Status**: Open
**Options**:
- A) Generate import statements, assume dependencies are installed
- B) Track dependencies in metadata, let user handle installation
- C) Generate dependency declarations (requirements.txt, pyproject.toml)

**Recommendation**: Start with (A), add (B) in metadata, defer (C) to future work

### 2. How to handle class generation?

**Status**: Open
**Context**: Current IR represents functions, not classes

**Options**:
- A) Extend IR to support class specifications
- B) Generate standalone functions, let user wrap in classes
- C) Infer class structure from multiple related IRs

**Recommendation**: Start with (B), design class IR in parallel track

### 3. How to handle async functions?

**Status**: Open
**Options**:
- A) Detect async from effect descriptions ("awaits X")
- B) Add explicit `async: bool` field to IR
- C) Generate both sync and async versions

**Recommendation**: (A) for MVP, (B) for robustness

### 4. How to preserve comments and formatting from original code?

**Status**: Open
**Context**: Round-trip validation may require preserving human-added comments

**Options**:
- A) Store comments in IR metadata, restore during generation
- B) Don't preserve comments, regenerate from intent
- C) Use structured comments (docstrings only)

**Recommendation**: (B) for MVP, (A) as enhancement

### 5. How to handle partial IRs (e.g., for iterative refinement)?

**Status**: Open
**Context**: User may want to see generated code before all holes are resolved

**Options**:
- A) Generate partial code with TODO markers for holes
- B) Refuse to generate until IR is complete
- C) Generate stub implementations for unresolved parts

**Recommendation**: (C) for better developer experience

---

## Next Steps

### Immediate Actions (lift-sys-25)

1. **Implement DefaultTypeResolver**:
   - Basic type mapping (string → str, integer → int, etc.)
   - Union types (str | None)
   - Generic types (list[int])

2. **Implement CodeGenerator facade**:
   - Orchestrate components
   - Generate function signature
   - Generate function body
   - Add docstrings

3. **Implement DocstringGenerator**:
   - Google-style docstrings
   - Extract summary from intent
   - Document parameters

4. **Basic testing**:
   - Unit tests for each component
   - Integration test for simple function generation

### Follow-Up Work (lift-sys-26, lift-sys-27)

- Implement DefaultAssertionInjector (lift-sys-26)
- Implement DefaultEffectHandler
- Build round-trip validator (lift-sys-27)
- Add formatting with black
- Comprehensive test suite

---

## References

- [IR Models](../lift_sys/ir/models.py) - Current IR data structures
- [IR Parser](../lift_sys/ir/parser.py) - IR parsing logic
- [Reverse Mode Lifter](../lift_sys/reverse_mode/lifter.py) - Code → IR extraction
- [Forward-Reverse Integration Plan](FORWARD_REVERSE_INTEGRATION_PLAN.md) - Overall roadmap
- [Integration Issues Summary](INTEGRATION_ISSUES_SUMMARY.md) - Issue tracking

---

**Document Version**: 1.0
**Last Updated**: October 13, 2025
**Review Status**: Ready for implementation
