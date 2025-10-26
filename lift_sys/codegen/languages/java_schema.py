"""JSON schema for xgrammar-constrained Java code generation."""

from __future__ import annotations

from typing import Any

# JSON Schema for Java function implementation
# This schema enforces the structure of generated Java function implementations
JAVA_GENERATION_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "JavaFunctionImplementation",
    "description": "Structured representation of a Java function implementation",
    "type": "object",
    "properties": {
        "implementation": {
            "type": "object",
            "description": "The actual function implementation",
            "properties": {
                "body_statements": {
                    "type": "array",
                    "description": "List of implementation statements. For variables declared in 'variables' array, use assignment statements (type='assignment') without type declarations.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of statement. Use 'assignment' for variables already declared in 'variables' array. Use 'variable_declaration' only for new variables not in 'variables' array.",
                                "enum": [
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
                                ],
                            },
                            "code": {
                                "type": "string",
                                "description": "Java code for this statement. DO NOT include type declarations for variables already declared in 'variables' array. Use plain assignments like 'x = value' not 'int x = value'.",
                            },
                            "rationale": {
                                "type": ["string", "null"],
                                "description": "Why this statement is needed",
                            },
                        },
                        "required": ["type", "code"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                },
                "variables": {
                    "type": "array",
                    "description": "Local variables to DECLARE at function start. These will be declared with their Java types. Do NOT redeclare these in body_statements.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Variable name",
                                "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
                            },
                            "type_hint": {
                                "type": "string",
                                "description": "Java type (e.g., int, String, List<Integer>)",
                            },
                            "purpose": {
                                "type": ["string", "null"],
                                "description": "Purpose of this variable",
                            },
                            "is_final": {
                                "type": "boolean",
                                "description": "Whether variable is final (immutable)",
                                "default": False,
                            },
                        },
                        "required": ["name", "type_hint"],
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "algorithm": {
                    "type": ["string", "null"],
                    "description": "High-level description of the algorithm used",
                },
                "complexity": {
                    "type": "object",
                    "description": "Time and space complexity",
                    "properties": {
                        "time": {
                            "type": ["string", "null"],
                            "description": "Time complexity (e.g., O(n), O(log n))",
                        },
                        "space": {
                            "type": ["string", "null"],
                            "description": "Space complexity (e.g., O(1), O(n))",
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "required": ["body_statements"],
            "additionalProperties": False,
        },
        "imports": {
            "type": "array",
            "description": "Additional imports needed for implementation",
            "items": {
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "Package to import (e.g., java.util.List, java.io.*)",
                    },
                    "is_static": {
                        "type": "boolean",
                        "description": "Whether this is a static import",
                        "default": False,
                    },
                },
                "required": ["package"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "helper_methods": {
            "type": "array",
            "description": "Helper methods needed for implementation",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Helper method name",
                        "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
                    },
                    "signature": {
                        "type": "string",
                        "description": "Method signature with Java types and modifiers",
                    },
                    "body": {
                        "type": "string",
                        "description": "Method body",
                    },
                    "access_modifier": {
                        "type": "string",
                        "description": "Access modifier for the method",
                        "enum": ["private", "protected", "public", "package-private"],
                        "default": "private",
                    },
                },
                "required": ["name", "signature", "body"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "annotations": {
            "type": "array",
            "description": "Annotations for the method (e.g., @Override, @Deprecated)",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Annotation name (without @)",
                    },
                    "parameters": {
                        "type": ["string", "null"],
                        "description": "Annotation parameters if any",
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "generics": {
            "type": "array",
            "description": "Generic type parameters for the method (e.g., <T>, <K, V>)",
            "items": {
                "type": "object",
                "properties": {
                    "type_parameter": {
                        "type": "string",
                        "description": "Type parameter name (e.g., T, K, V)",
                    },
                    "bounds": {
                        "type": ["string", "null"],
                        "description": "Type bounds if any (e.g., extends Number)",
                    },
                },
                "required": ["type_parameter"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "exception_handling": {
            "type": "object",
            "description": "Exception handling patterns used in implementation",
            "properties": {
                "checked_exceptions": {
                    "type": "array",
                    "description": "Checked exceptions that method throws",
                    "items": {"type": "string"},
                    "default": [],
                },
                "try_catch_blocks": {
                    "type": "array",
                    "description": "Try-catch-finally blocks in the implementation",
                    "items": {
                        "type": "object",
                        "properties": {
                            "try_body": {"type": "string"},
                            "catch_clauses": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "exception_type": {"type": "string"},
                                        "variable_name": {"type": "string"},
                                        "body": {"type": "string"},
                                    },
                                },
                            },
                            "finally_body": {"type": ["string", "null"]},
                        },
                    },
                    "default": [],
                },
            },
            "additionalProperties": False,
        },
        "access_modifier": {
            "type": "string",
            "description": "Access modifier for the method",
            "enum": ["private", "protected", "public", "package-private"],
            "default": "public",
        },
    },
    "required": ["implementation"],
    "additionalProperties": False,
}


def get_prompt_for_java_generation(
    ir_summary: str,
    signature: str,
    constraints: list[str] | None = None,
    effects: list[str] | None = None,
) -> str:
    """
    Build generation prompt for Java code.

    Args:
        ir_summary: High-level intent/summary from IR
        signature: Java method signature
        constraints: List of constraints/assertions from IR
        effects: List of effects describing operational semantics

    Returns:
        Prompt for LLM to generate Java implementation
    """
    prompt_parts = []

    # Intent and signature
    prompt_parts.append("Generate a Java implementation for the following specification:")
    prompt_parts.append(f"\nIntent: {ir_summary}")
    prompt_parts.append(f"\nTarget signature:\n{signature}")

    # Effects (operational semantics)
    if effects:
        prompt_parts.append("\nImplementation should follow these operational steps:")
        for i, effect in enumerate(effects, 1):
            prompt_parts.append(f"  {i}. {effect}")

    # Constraints
    if constraints:
        prompt_parts.append("\nConstraints to satisfy:")
        for constraint in constraints:
            prompt_parts.append(f"  - {constraint}")

    # Generation instructions
    prompt_parts.append(
        "\nProvide the implementation as a JSON object with the following structure:"
    )
    prompt_parts.append("- implementation.body_statements: Array of statements to execute")
    prompt_parts.append("  Each statement has: type, code, rationale (optional)")
    prompt_parts.append(
        "  Types: assignment, return, if_statement, for_loop, while_loop, try_catch, throw_statement, etc."
    )
    prompt_parts.append("- implementation.variables: Array of local variables (if needed)")
    prompt_parts.append("  Each variable has: name, type_hint, purpose, is_final")
    prompt_parts.append(
        "\nIMPORTANT: If you declare variables in 'variables' array, do NOT redeclare them in body_statements."
    )
    prompt_parts.append(
        "Use assignment (result = value) NOT declarations (int result = value) for already-declared variables."
    )
    prompt_parts.append(
        "\n- imports: Array of imports (if needed) with package path and is_static flag"
    )
    prompt_parts.append("- helper_methods: Array of helper methods (if needed)")
    prompt_parts.append("- annotations: Array of method annotations (if needed)")
    prompt_parts.append("- generics: Array of generic type parameters (if needed)")
    prompt_parts.append(
        "- exception_handling: Exception handling patterns (checked exceptions, try-catch blocks)"
    )
    prompt_parts.append("- access_modifier: Method access level (public, private, protected)")
    prompt_parts.append("\nGenerate clean, idiomatic Java code following best practices.")

    return "\n".join(prompt_parts)
