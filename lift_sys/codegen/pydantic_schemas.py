"""Pydantic models for constrained code generation across all languages.

This module provides Pydantic models that replace JSON schemas for llguidance/Guidance.
Each language (TypeScript, Rust, Go, Java) has its own set of models representing the
structured output expected from LLM code generation.

Models are organized by language with shared patterns:
- Statement models for body_statements
- Variable models for local variables
- Implementation models for the core function body
- Top-level output models wrapping implementation + metadata

All models use frozen=False to allow mutation during generation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ============================================================================
# TypeScript Models
# ============================================================================


class TypeScriptStatement(BaseModel):
    """A single statement in TypeScript function body.

    For variables already declared in 'variables' array, use type='assignment'
    without const/let/var keywords. Use plain assignments like 'x = value'.
    """

    type: Literal[
        "assignment",
        "return",
        "if_statement",
        "for_loop",
        "while_loop",
        "function_call",
        "expression",
        "comment",
        "const_declaration",
        "let_declaration",
        "arrow_function",
    ] = Field(
        ...,
        description="Type of statement. Use 'assignment' for already-declared variables.",
    )
    code: str = Field(
        ...,
        description="TypeScript code for this statement. Do NOT include const/let/var for already-declared variables.",
    )
    rationale: str | None = Field(None, description="Why this statement is needed")


class TypeScriptVariable(BaseModel):
    """Local variable declaration for TypeScript function.

    Variables declared here will be declared at function start with their
    declaration_type. Do NOT redeclare these in body_statements.
    """

    name: str = Field(..., description="Variable name", pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    type_hint: str | None = Field(None, description="TypeScript type annotation")
    purpose: str | None = Field(None, description="Purpose of this variable")
    declaration_type: Literal["const", "let", "var"] = Field(
        "let", description="Variable declaration type"
    )


class TypeScriptComplexity(BaseModel):
    """Time and space complexity analysis."""

    time: str | None = Field(None, description="Time complexity (e.g., O(n), O(log n))")
    space: str | None = Field(None, description="Space complexity (e.g., O(1), O(n))")


class TypeScriptImplementation(BaseModel):
    """Core implementation of a TypeScript function."""

    body_statements: list[TypeScriptStatement] = Field(
        ...,
        min_length=1,
        description="List of implementation statements",
    )
    variables: list[TypeScriptVariable] = Field(
        default_factory=list,
        description="Local variables to declare at function start",
    )
    algorithm: str | None = Field(None, description="High-level description of the algorithm used")
    complexity: TypeScriptComplexity | None = Field(None, description="Time and space complexity")


class TypeScriptImport(BaseModel):
    """TypeScript import statement."""

    module: str = Field(..., description="Module to import from")
    names: list[str] = Field(..., description="Names to import (or * for default/namespace)")
    import_type: Literal["named", "default", "namespace", "type_only"] = Field(
        "named", description="Type of import"
    )


class TypeScriptHelperFunction(BaseModel):
    """Helper function needed for TypeScript implementation."""

    name: str = Field(..., description="Helper function name", pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    signature: str = Field(..., description="Function signature with TypeScript types")
    body: str = Field(..., description="Function body")
    is_async: bool = Field(False, description="Whether this is an async function")


class TypeScriptTypeDefinition(BaseModel):
    """Custom type definition or interface."""

    name: str = Field(..., description="Type or interface name")
    definition: str = Field(..., description="Complete type definition")


class TypeScriptOutput(BaseModel):
    """Top-level output for TypeScript code generation."""

    implementation: TypeScriptImplementation = Field(
        ..., description="The actual function implementation"
    )
    imports: list[TypeScriptImport] = Field(
        default_factory=list,
        description="Additional imports needed for implementation",
    )
    helper_functions: list[TypeScriptHelperFunction] = Field(
        default_factory=list,
        description="Helper functions needed for implementation",
    )
    type_definitions: list[TypeScriptTypeDefinition] = Field(
        default_factory=list,
        description="Custom type definitions or interfaces needed",
    )


# ============================================================================
# Rust Models
# ============================================================================


class RustStatement(BaseModel):
    """A single statement in Rust function body.

    For variables already declared in 'variables' array, use type='assignment'
    without let/mut keywords. Use plain assignments like 'x = value'.
    """

    type: Literal[
        "assignment",
        "return",
        "if_statement",
        "match_expression",
        "for_loop",
        "while_loop",
        "loop",
        "function_call",
        "expression",
        "comment",
        "let_declaration",
        "mut_declaration",
        "closure",
        "macro_invocation",
    ] = Field(
        ...,
        description="Type of statement. Use 'assignment' for already-declared variables.",
    )
    code: str = Field(
        ...,
        description="Rust code for this statement. Do NOT include let/mut for already-declared variables.",
    )
    rationale: str | None = Field(None, description="Why this statement is needed")


class RustVariable(BaseModel):
    """Local variable declaration for Rust function.

    Variables declared here will be declared at function start with their
    mutability. Do NOT redeclare these in body_statements.
    """

    name: str = Field(..., description="Variable name", pattern=r"^[a-z_][a-z0-9_]*$")
    type_hint: str | None = Field(None, description="Rust type annotation")
    purpose: str | None = Field(None, description="Purpose of this variable")
    mutability: Literal["mut", "immutable"] = Field("immutable", description="Variable mutability")


class RustComplexity(BaseModel):
    """Time and space complexity analysis."""

    time: str | None = Field(None, description="Time complexity (e.g., O(n), O(log n))")
    space: str | None = Field(None, description="Space complexity (e.g., O(1), O(n))")


class RustImplementation(BaseModel):
    """Core implementation of a Rust function."""

    body_statements: list[RustStatement] = Field(
        ...,
        min_length=1,
        description="List of implementation statements",
    )
    variables: list[RustVariable] = Field(
        default_factory=list,
        description="Local variables to declare at function start",
    )
    algorithm: str | None = Field(None, description="High-level description of the algorithm used")
    complexity: RustComplexity | None = Field(None, description="Time and space complexity")


class RustImport(BaseModel):
    """Rust use statement."""

    path: str = Field(
        ..., description="Module path to import from (e.g., 'std::collections::HashMap')"
    )
    items: list[str] = Field(
        default_factory=list, description="Items to import (* for glob import)"
    )
    alias: str | None = Field(None, description="Optional alias (as SomeName)")


class RustHelperFunction(BaseModel):
    """Helper function needed for Rust implementation."""

    name: str = Field(..., description="Helper function name", pattern=r"^[a-z_][a-z0-9_]*$")
    signature: str = Field(..., description="Function signature with Rust types")
    body: str = Field(..., description="Function body")
    is_generic: bool = Field(False, description="Whether this function has generic parameters")


class RustTypeDefinition(BaseModel):
    """Custom type definition (struct, enum, type alias)."""

    name: str = Field(..., description="Type name")
    definition: str = Field(..., description="Complete type definition")


class RustLifetime(BaseModel):
    """Lifetime parameter for Rust function."""

    name: str = Field(
        ...,
        description="Lifetime name (without apostrophe, e.g., 'a' not \"'a\")",
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    purpose: str | None = Field(None, description="Why this lifetime is needed")


class RustTraitBound(BaseModel):
    """Trait bound for generic parameter."""

    parameter: str = Field(..., description="Generic parameter name")
    traits: list[str] = Field(..., description="Traits that parameter must implement")


class RustErrorHandling(BaseModel):
    """Error handling strategy for Rust function."""

    uses_result: bool = Field(False, description="Whether function returns Result<T, E>")
    uses_option: bool = Field(False, description="Whether function returns Option<T>")
    error_type: str | None = Field(None, description="Custom error type if using Result")
    uses_question_mark: bool = Field(
        False, description="Whether ? operator is used for error propagation"
    )


class RustOutput(BaseModel):
    """Top-level output for Rust code generation."""

    implementation: RustImplementation = Field(
        ..., description="The actual function implementation"
    )
    imports: list[RustImport] = Field(
        default_factory=list,
        description="Use statements needed for implementation",
    )
    helper_functions: list[RustHelperFunction] = Field(
        default_factory=list,
        description="Helper functions needed for implementation",
    )
    type_definitions: list[RustTypeDefinition] = Field(
        default_factory=list,
        description="Custom type definitions (structs, enums, type aliases) needed",
    )
    lifetimes: list[RustLifetime] = Field(
        default_factory=list,
        description="Lifetime parameters needed (if any)",
    )
    trait_bounds: list[RustTraitBound] = Field(
        default_factory=list,
        description="Trait bounds for generic parameters (if any)",
    )
    error_handling: RustErrorHandling | None = Field(None, description="Error handling strategy")


# ============================================================================
# Go Models
# ============================================================================


class GoStatement(BaseModel):
    """A single statement in Go function body.

    For variables already declared in 'variables' array, use type='assignment'
    without var keywords. Use plain assignments like 'x = value'.
    """

    type: Literal[
        "assignment",
        "return",
        "if_statement",
        "for_loop",
        "range_loop",
        "function_call",
        "expression",
        "comment",
        "var_declaration",
        "short_declaration",
        "defer_statement",
        "go_statement",
        "error_check",
        "switch_statement",
        "select_statement",
    ] = Field(
        ...,
        description="Type of statement. Use 'assignment' for already-declared variables.",
    )
    code: str = Field(
        ...,
        description="Go code for this statement. Do NOT include var for already-declared variables.",
    )
    rationale: str | None = Field(None, description="Why this statement is needed")


class GoVariable(BaseModel):
    """Local variable declaration for Go function.

    Variables declared here will be declared at function start with var.
    Do NOT redeclare these in body_statements.
    """

    name: str = Field(..., description="Variable name", pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    type_hint: str | None = Field(None, description="Go type annotation")
    purpose: str | None = Field(None, description="Purpose of this variable")


class GoComplexity(BaseModel):
    """Time and space complexity analysis."""

    time: str | None = Field(None, description="Time complexity (e.g., O(n), O(log n))")
    space: str | None = Field(None, description="Space complexity (e.g., O(1), O(n))")


class GoImport(BaseModel):
    """Go import statement."""

    package: str = Field(..., description="Package path to import")
    alias: str | None = Field(
        None,
        description="Optional import alias (e.g., _ for side effects, . for dot import)",
    )


class GoGoroutine(BaseModel):
    """Goroutine spawned in the function."""

    purpose: str = Field(..., description="What this goroutine does")
    function_call: str = Field(..., description="Function to run as goroutine")


class GoChannel(BaseModel):
    """Channel used in the function."""

    name: str = Field(..., description="Channel variable name")
    element_type: str = Field(..., description="Type of elements in channel")
    direction: Literal["bidirectional", "send_only", "receive_only"] = Field(
        "bidirectional", description="Channel direction"
    )
    buffered: bool = Field(False, description="Whether channel is buffered")
    buffer_size: int | None = Field(None, description="Buffer size if buffered")


class GoDeferStatement(BaseModel):
    """Deferred cleanup statement."""

    code: str = Field(..., description="Code to defer")
    rationale: str | None = Field(None, description="Why this cleanup is needed")


class GoErrorCheck(BaseModel):
    """Explicit error check in Go code."""

    source: str = Field(..., description="Where error comes from")
    handling: Literal["return", "wrap", "log", "ignore", "panic"] = Field(
        ..., description="How error is handled"
    )


class GoErrorHandling(BaseModel):
    """Error handling strategy for Go function."""

    returns_error: bool = Field(False, description="Whether function returns error")
    error_checks: list[GoErrorCheck] = Field(
        default_factory=list, description="Explicit error checks in code"
    )


class GoImplementation(BaseModel):
    """Core implementation of a Go function."""

    body_statements: list[GoStatement] = Field(
        ...,
        min_length=1,
        description="List of implementation statements",
    )
    variables: list[GoVariable] = Field(
        default_factory=list,
        description="Local variables to declare at function start",
    )
    imports: list[GoImport] = Field(
        default_factory=list,
        description="Additional imports needed for implementation",
    )
    goroutines: list[GoGoroutine] = Field(
        default_factory=list,
        description="Goroutines spawned in this function",
    )
    channels: list[GoChannel] = Field(
        default_factory=list,
        description="Channels used in this function",
    )
    defer_statements: list[GoDeferStatement] = Field(
        default_factory=list,
        description="Deferred cleanup statements",
    )
    error_handling: GoErrorHandling | None = Field(None, description="Error handling strategy")
    algorithm: str | None = Field(None, description="High-level description of the algorithm used")
    complexity: GoComplexity | None = Field(None, description="Time and space complexity")


class GoOutput(BaseModel):
    """Top-level output for Go code generation."""

    implementation: GoImplementation = Field(..., description="The actual function implementation")


# ============================================================================
# Java Models
# ============================================================================


class JavaStatement(BaseModel):
    """A single statement in Java method body.

    For variables already declared in 'variables' array, use type='assignment'
    without type declarations. Use plain assignments like 'x = value'.
    """

    type: Literal[
        "assignment",
        "return",
        "if_statement",
        "for_loop",
        "while_loop",
        "function_call",
        "expression",
        "comment",
        "variable_declaration",
        "try_catch",
        "throw_statement",
        "enhanced_for_loop",
        "switch_statement",
        "break_statement",
        "continue_statement",
    ] = Field(
        ...,
        description="Type of statement. Use 'assignment' for already-declared variables.",
    )
    code: str = Field(
        ...,
        description="Java code for this statement. Do NOT include type declarations for already-declared variables.",
    )
    rationale: str | None = Field(None, description="Why this statement is needed")


class JavaVariable(BaseModel):
    """Local variable declaration for Java method.

    Variables declared here will be declared at function start with their
    Java types. Do NOT redeclare these in body_statements.
    """

    name: str = Field(..., description="Variable name", pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    type_hint: str = Field(..., description="Java type (e.g., int, String, List<Integer>)")
    purpose: str | None = Field(None, description="Purpose of this variable")
    is_final: bool = Field(False, description="Whether variable is final (immutable)")


class JavaComplexity(BaseModel):
    """Time and space complexity analysis."""

    time: str | None = Field(None, description="Time complexity (e.g., O(n), O(log n))")
    space: str | None = Field(None, description="Space complexity (e.g., O(1), O(n))")


class JavaImplementation(BaseModel):
    """Core implementation of a Java method."""

    body_statements: list[JavaStatement] = Field(
        ...,
        min_length=1,
        description="List of implementation statements",
    )
    variables: list[JavaVariable] = Field(
        default_factory=list,
        description="Local variables to declare at method start",
    )
    algorithm: str | None = Field(None, description="High-level description of the algorithm used")
    complexity: JavaComplexity | None = Field(None, description="Time and space complexity")


class JavaImport(BaseModel):
    """Java import statement."""

    package: str = Field(..., description="Package to import (e.g., java.util.List, java.io.*)")
    is_static: bool = Field(False, description="Whether this is a static import")


class JavaHelperMethod(BaseModel):
    """Helper method needed for Java implementation."""

    name: str = Field(..., description="Helper method name", pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    signature: str = Field(..., description="Method signature with Java types and modifiers")
    body: str = Field(..., description="Method body")
    access_modifier: Literal["private", "protected", "public", "package-private"] = Field(
        "private", description="Access modifier for the method"
    )


class JavaAnnotation(BaseModel):
    """Java annotation for the method."""

    name: str = Field(..., description="Annotation name (without @)")
    parameters: str | None = Field(None, description="Annotation parameters if any")


class JavaGeneric(BaseModel):
    """Generic type parameter for Java method."""

    type_parameter: str = Field(..., description="Type parameter name (e.g., T, K, V)")
    bounds: str | None = Field(None, description="Type bounds if any (e.g., extends Number)")


class JavaCatchClause(BaseModel):
    """Catch clause in try-catch block."""

    exception_type: str = Field(..., description="Exception type to catch")
    variable_name: str = Field(..., description="Exception variable name")
    body: str = Field(..., description="Catch block body")


class JavaTryCatchBlock(BaseModel):
    """Try-catch-finally block in Java implementation."""

    try_body: str = Field(..., description="Code in try block")
    catch_clauses: list[JavaCatchClause] = Field(default_factory=list, description="Catch clauses")
    finally_body: str | None = Field(None, description="Finally block body")


class JavaExceptionHandling(BaseModel):
    """Exception handling patterns used in Java implementation."""

    checked_exceptions: list[str] = Field(
        default_factory=list,
        description="Checked exceptions that method throws",
    )
    try_catch_blocks: list[JavaTryCatchBlock] = Field(
        default_factory=list,
        description="Try-catch-finally blocks in the implementation",
    )


class JavaOutput(BaseModel):
    """Top-level output for Java code generation."""

    implementation: JavaImplementation = Field(..., description="The actual method implementation")
    imports: list[JavaImport] = Field(
        default_factory=list,
        description="Additional imports needed for implementation",
    )
    helper_methods: list[JavaHelperMethod] = Field(
        default_factory=list,
        description="Helper methods needed for implementation",
    )
    annotations: list[JavaAnnotation] = Field(
        default_factory=list,
        description="Annotations for the method (e.g., @Override, @Deprecated)",
    )
    generics: list[JavaGeneric] = Field(
        default_factory=list,
        description="Generic type parameters for the method (e.g., <T>, <K, V>)",
    )
    exception_handling: JavaExceptionHandling | None = Field(
        None, description="Exception handling patterns used in implementation"
    )
    access_modifier: Literal["private", "protected", "public", "package-private"] = Field(
        "public", description="Access modifier for the method"
    )
