"""JSON schema for xgrammar-constrained TypeScript code generation."""

from __future__ import annotations

from typing import Any

# JSON Schema for TypeScript function implementation
# This schema enforces the structure of generated TypeScript function implementations
TYPESCRIPT_GENERATION_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "TypeScriptFunctionImplementation",
    "description": "Structured representation of a TypeScript function implementation",
    "type": "object",
    "properties": {
        "implementation": {
            "type": "object",
            "description": "The actual function implementation",
            "properties": {
                "body_statements": {
                    "type": "array",
                    "description": "List of implementation statements. For variables declared in 'variables' array, use assignment statements (type='assignment') without const/let/var keywords.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of statement. Use 'assignment' for variables already declared in 'variables' array. Use 'const_declaration' or 'let_declaration' only for new variables not in 'variables' array.",
                                "enum": [
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
                                ],
                            },
                            "code": {
                                "type": "string",
                                "description": "TypeScript code for this statement. DO NOT include const/let/var keywords for variables already declared in 'variables' array. Use plain assignments like 'x = value' not 'const x = value'.",
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
                    "description": "Local variables to DECLARE at function start. These will be declared with their declaration_type (const/let/var). Do NOT redeclare these in body_statements.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Variable name",
                                "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
                            },
                            "type_hint": {
                                "type": ["string", "null"],
                                "description": "TypeScript type annotation",
                            },
                            "purpose": {
                                "type": ["string", "null"],
                                "description": "Purpose of this variable",
                            },
                            "declaration_type": {
                                "type": "string",
                                "description": "Variable declaration type",
                                "enum": ["const", "let", "var"],
                                "default": "let",
                            },
                        },
                        "required": ["name"],
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
                    "module": {
                        "type": "string",
                        "description": "Module to import from",
                    },
                    "names": {
                        "type": "array",
                        "description": "Names to import (or * for default/namespace)",
                        "items": {"type": "string"},
                    },
                    "import_type": {
                        "type": "string",
                        "description": "Type of import",
                        "enum": ["named", "default", "namespace", "type_only"],
                        "default": "named",
                    },
                },
                "required": ["module", "names"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "helper_functions": {
            "type": "array",
            "description": "Helper functions needed for implementation",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Helper function name",
                        "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
                    },
                    "signature": {
                        "type": "string",
                        "description": "Function signature with TypeScript types",
                    },
                    "body": {
                        "type": "string",
                        "description": "Function body",
                    },
                    "is_async": {
                        "type": "boolean",
                        "description": "Whether this is an async function",
                        "default": False,
                    },
                },
                "required": ["name", "signature", "body"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "type_definitions": {
            "type": "array",
            "description": "Custom type definitions or interfaces needed",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Type or interface name",
                    },
                    "definition": {
                        "type": "string",
                        "description": "Complete type definition",
                    },
                },
                "required": ["name", "definition"],
                "additionalProperties": False,
            },
            "default": [],
        },
    },
    "required": ["implementation"],
    "additionalProperties": False,
}


def get_prompt_for_typescript_generation(
    ir_summary: str,
    signature: str,
    constraints: list[str] | None = None,
    effects: list[str] | None = None,
) -> str:
    """
    Build generation prompt for TypeScript code.

    Args:
        ir_summary: High-level intent/summary from IR
        signature: TypeScript function signature
        constraints: List of constraints/assertions from IR
        effects: List of effects describing operational semantics

    Returns:
        Prompt for LLM to generate TypeScript implementation
    """
    prompt_parts = []

    # Intent and signature
    prompt_parts.append("Generate a TypeScript implementation for the following specification:")
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
        "  Types: assignment, return, if_statement, for_loop, while_loop, function_call, etc."
    )
    prompt_parts.append("- implementation.variables: Array of local variables (if needed)")
    prompt_parts.append("  Each variable has: name, type_hint, purpose, declaration_type")
    prompt_parts.append(
        "\nIMPORTANT: If you declare variables in 'variables' array, do NOT redeclare them in body_statements."
    )
    prompt_parts.append(
        "Use assignment (product = value) NOT const/let declarations (const product = value) for already-declared variables."
    )
    prompt_parts.append("\n- imports: Array of imports (if needed) with module, names, import_type")
    prompt_parts.append("- helper_functions: Array of helper functions (if needed)")
    prompt_parts.append("- type_definitions: Array of custom types/interfaces (if needed)")
    prompt_parts.append("\nGenerate clean, idiomatic TypeScript code.")

    return "\n".join(prompt_parts)
