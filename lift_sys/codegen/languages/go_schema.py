"""JSON schema for xgrammar-constrained Go code generation."""

from __future__ import annotations

from typing import Any

# JSON Schema for Go function implementation
# This schema enforces the structure of generated Go function implementations
GO_GENERATION_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "GoFunctionImplementation",
    "description": "Structured representation of a Go function implementation",
    "type": "object",
    "properties": {
        "implementation": {
            "type": "object",
            "description": "The actual function implementation",
            "properties": {
                "body_statements": {
                    "type": "array",
                    "description": "List of implementation statements. For variables declared in 'variables' array, use assignment statements (type='assignment') without var keywords.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of statement. Use 'assignment' for variables already declared in 'variables' array. Use 'var_declaration' only for new variables not in 'variables' array.",
                                "enum": [
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
                                ],
                            },
                            "code": {
                                "type": "string",
                                "description": "Go code for this statement. DO NOT include var keywords for variables already declared in 'variables' array. Use plain assignments like 'x = value' not 'var x = value'.",
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
                    "description": "Local variables to DECLARE at function start. These will be declared with var. Do NOT redeclare these in body_statements.",
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
                                "description": "Go type annotation",
                            },
                            "purpose": {
                                "type": ["string", "null"],
                                "description": "Purpose of this variable",
                            },
                        },
                        "required": ["name"],
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "imports": {
                    "type": "array",
                    "description": "Additional imports needed for implementation",
                    "items": {
                        "type": "object",
                        "properties": {
                            "package": {
                                "type": "string",
                                "description": "Package path to import",
                            },
                            "alias": {
                                "type": ["string", "null"],
                                "description": "Optional import alias (e.g., _ for side effects, . for dot import)",
                            },
                        },
                        "required": ["package"],
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "goroutines": {
                    "type": "array",
                    "description": "Goroutines spawned in this function",
                    "items": {
                        "type": "object",
                        "properties": {
                            "purpose": {
                                "type": "string",
                                "description": "What this goroutine does",
                            },
                            "function_call": {
                                "type": "string",
                                "description": "Function to run as goroutine",
                            },
                        },
                        "required": ["purpose", "function_call"],
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "channels": {
                    "type": "array",
                    "description": "Channels used in this function",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Channel variable name",
                            },
                            "element_type": {
                                "type": "string",
                                "description": "Type of elements in channel",
                            },
                            "direction": {
                                "type": "string",
                                "description": "Channel direction",
                                "enum": ["bidirectional", "send_only", "receive_only"],
                                "default": "bidirectional",
                            },
                            "buffered": {
                                "type": "boolean",
                                "description": "Whether channel is buffered",
                                "default": False,
                            },
                            "buffer_size": {
                                "type": ["integer", "null"],
                                "description": "Buffer size if buffered",
                            },
                        },
                        "required": ["name", "element_type"],
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "defer_statements": {
                    "type": "array",
                    "description": "Deferred cleanup statements",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to defer",
                            },
                            "rationale": {
                                "type": ["string", "null"],
                                "description": "Why this cleanup is needed",
                            },
                        },
                        "required": ["code"],
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "error_handling": {
                    "type": "object",
                    "description": "Error handling strategy",
                    "properties": {
                        "returns_error": {
                            "type": "boolean",
                            "description": "Whether function returns error",
                            "default": False,
                        },
                        "error_checks": {
                            "type": "array",
                            "description": "Explicit error checks in code",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {
                                        "type": "string",
                                        "description": "Where error comes from",
                                    },
                                    "handling": {
                                        "type": "string",
                                        "description": "How error is handled",
                                        "enum": ["return", "wrap", "log", "ignore", "panic"],
                                    },
                                },
                                "required": ["source", "handling"],
                                "additionalProperties": False,
                            },
                            "default": [],
                        },
                    },
                    "additionalProperties": False,
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
    },
    "required": ["implementation"],
    "additionalProperties": False,
}


def get_prompt_for_go_generation(
    ir_summary: str,
    signature: str,
    constraints: list[str] | None = None,
    effects: list[str] | None = None,
) -> str:
    """
    Build generation prompt for Go code.

    Args:
        ir_summary: High-level intent/summary from IR
        signature: Go function signature
        constraints: List of constraints/assertions from IR
        effects: List of effects describing operational semantics

    Returns:
        Prompt for LLM to generate Go implementation
    """
    prompt_parts = []

    # Intent and signature
    prompt_parts.append("Generate a Go implementation for the following specification:")
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
        "  Types: assignment, return, if_statement, for_loop, range_loop, defer_statement, go_statement, error_check, etc."
    )
    prompt_parts.append("- implementation.variables: Array of local variables (if needed)")
    prompt_parts.append("  Each variable has: name, type_hint, purpose")
    prompt_parts.append(
        "\nIMPORTANT: If you declare variables in 'variables' array, do NOT redeclare them in body_statements."
    )
    prompt_parts.append(
        "Use assignment (result = value) NOT var declarations (var result = value) for already-declared variables."
    )
    prompt_parts.append("\n- imports: Array of imports (if needed) with package, alias (optional)")
    prompt_parts.append("- goroutines: Array of concurrent goroutines (if needed)")
    prompt_parts.append("- channels: Array of channels used (if needed)")
    prompt_parts.append("- defer_statements: Array of cleanup defers (if needed)")
    prompt_parts.append(
        "- error_handling: Object describing error strategy (returns_error, error_checks)"
    )
    prompt_parts.append("\nGenerate clean, idiomatic Go code following Go best practices:")
    prompt_parts.append("- Use short variable declarations (:=) where appropriate")
    prompt_parts.append("- Check errors explicitly (if err != nil)")
    prompt_parts.append("- Use defer for cleanup (defer file.Close())")
    prompt_parts.append("- Use goroutines and channels for concurrency")
    prompt_parts.append("- Return errors, don't panic")

    return "\n".join(prompt_parts)
