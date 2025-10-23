"""JSON schema for xgrammar-constrained Rust code generation."""

from __future__ import annotations

from typing import Any

# JSON Schema for Rust function implementation
# This schema enforces the structure of generated Rust function implementations
RUST_GENERATION_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "RustFunctionImplementation",
    "description": "Structured representation of a Rust function implementation",
    "type": "object",
    "properties": {
        "implementation": {
            "type": "object",
            "description": "The actual function implementation",
            "properties": {
                "body_statements": {
                    "type": "array",
                    "description": "List of implementation statements. For variables declared in 'variables' array, use assignment statements (type='assignment') without let/mut keywords.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of statement. Use 'assignment' for variables already declared in 'variables' array. Use 'let_declaration' or 'mut_declaration' only for new variables not in 'variables' array.",
                                "enum": [
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
                                ],
                            },
                            "code": {
                                "type": "string",
                                "description": "Rust code for this statement. DO NOT include let/mut keywords for variables already declared in 'variables' array. Use plain assignments like 'x = value' not 'let x = value'.",
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
                    "description": "Local variables to DECLARE at function start. These will be declared with their mutability (mut/immutable). Do NOT redeclare these in body_statements.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Variable name",
                                "pattern": "^[a-z_][a-z0-9_]*$",
                            },
                            "type_hint": {
                                "type": ["string", "null"],
                                "description": "Rust type annotation",
                            },
                            "purpose": {
                                "type": ["string", "null"],
                                "description": "Purpose of this variable",
                            },
                            "mutability": {
                                "type": "string",
                                "description": "Variable mutability",
                                "enum": ["mut", "immutable"],
                                "default": "immutable",
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
            "description": "Use statements needed for implementation",
            "items": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Module path to import from (e.g., 'std::collections::HashMap')",
                    },
                    "items": {
                        "type": "array",
                        "description": "Items to import (* for glob import)",
                        "items": {"type": "string"},
                    },
                    "alias": {
                        "type": ["string", "null"],
                        "description": "Optional alias (as SomeName)",
                    },
                },
                "required": ["path"],
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
                        "pattern": "^[a-z_][a-z0-9_]*$",
                    },
                    "signature": {
                        "type": "string",
                        "description": "Function signature with Rust types",
                    },
                    "body": {
                        "type": "string",
                        "description": "Function body",
                    },
                    "is_generic": {
                        "type": "boolean",
                        "description": "Whether this function has generic parameters",
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
            "description": "Custom type definitions (structs, enums, type aliases) needed",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Type name",
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
        "lifetimes": {
            "type": "array",
            "description": "Lifetime parameters needed (if any)",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Lifetime name (without apostrophe, e.g., 'a' not \"'a\")",
                        "pattern": "^[a-z][a-z0-9_]*$",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Why this lifetime is needed",
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "trait_bounds": {
            "type": "array",
            "description": "Trait bounds for generic parameters (if any)",
            "items": {
                "type": "object",
                "properties": {
                    "parameter": {
                        "type": "string",
                        "description": "Generic parameter name",
                    },
                    "traits": {
                        "type": "array",
                        "description": "Traits that parameter must implement",
                        "items": {"type": "string"},
                    },
                },
                "required": ["parameter", "traits"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "error_handling": {
            "type": "object",
            "description": "Error handling strategy",
            "properties": {
                "uses_result": {
                    "type": "boolean",
                    "description": "Whether function returns Result<T, E>",
                    "default": False,
                },
                "uses_option": {
                    "type": "boolean",
                    "description": "Whether function returns Option<T>",
                    "default": False,
                },
                "error_type": {
                    "type": ["string", "null"],
                    "description": "Custom error type if using Result",
                },
                "uses_question_mark": {
                    "type": "boolean",
                    "description": "Whether ? operator is used for error propagation",
                    "default": False,
                },
            },
            "additionalProperties": False,
        },
    },
    "required": ["implementation"],
    "additionalProperties": False,
}


def get_prompt_for_rust_generation(
    ir_summary: str,
    signature: str,
    constraints: list[str] | None = None,
    effects: list[str] | None = None,
) -> str:
    """
    Build generation prompt for Rust code.

    Args:
        ir_summary: High-level intent/summary from IR
        signature: Rust function signature
        constraints: List of constraints/assertions from IR
        effects: List of effects describing operational semantics

    Returns:
        Prompt for LLM to generate Rust implementation
    """
    prompt_parts = []

    # Intent and signature
    prompt_parts.append("Generate a Rust implementation for the following specification:")
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
        "  Types: assignment, return, if_statement, match_expression, for_loop, while_loop, loop, etc."
    )
    prompt_parts.append("- implementation.variables: Array of local variables (if needed)")
    prompt_parts.append("  Each variable has: name, type_hint, purpose, mutability")
    prompt_parts.append(
        "\nIMPORTANT: If you declare variables in 'variables' array, do NOT redeclare them in body_statements."
    )
    prompt_parts.append(
        "Use assignment (result = value) NOT let declarations (let result = value) for already-declared variables."
    )
    prompt_parts.append("\n- imports: Array of use statements (if needed) with path, items, alias")
    prompt_parts.append("- helper_functions: Array of helper functions (if needed)")
    prompt_parts.append("- type_definitions: Array of custom types/structs/enums (if needed)")
    prompt_parts.append("- lifetimes: Array of lifetime parameters (if needed)")
    prompt_parts.append("- trait_bounds: Array of trait bounds for generics (if needed)")
    prompt_parts.append(
        "- error_handling: Object describing error handling (uses_result, uses_option, error_type, uses_question_mark)"
    )
    prompt_parts.append("\nGenerate idiomatic Rust code following these patterns:")
    prompt_parts.append("- Use Result<T, E> for fallible operations")
    prompt_parts.append("- Use Option<T> for nullable values")
    prompt_parts.append("- Prefer immutable bindings (no mut unless needed)")
    prompt_parts.append("- Use match for pattern matching")
    prompt_parts.append("- Use ? operator for error propagation")
    prompt_parts.append("- Follow snake_case naming conventions")
    prompt_parts.append("- Add explicit type annotations for clarity")

    return "\n".join(prompt_parts)
