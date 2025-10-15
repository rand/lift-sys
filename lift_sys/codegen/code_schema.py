"""JSON schema for xgrammar-constrained code generation."""

from __future__ import annotations

from typing import Any

# JSON Schema for Python function implementation
# This schema enforces the structure of generated function implementations
CODE_GENERATION_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "FunctionImplementation",
    "description": "Structured representation of a Python function implementation",
    "type": "object",
    "properties": {
        "implementation": {
            "type": "object",
            "description": "The actual function implementation",
            "properties": {
                "body_statements": {
                    "type": "array",
                    "description": "List of implementation statements",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of statement",
                                "enum": [
                                    "assignment",
                                    "return",
                                    "if_statement",
                                    "for_loop",
                                    "while_loop",
                                    "function_call",
                                    "expression",
                                    "comment",
                                ],
                            },
                            "code": {
                                "type": "string",
                                "description": "Python code for this statement",
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
                    "description": "Local variables used in implementation",
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
                                "description": "Variable type hint",
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
                        "description": "Names to import",
                        "items": {"type": "string"},
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
                        "pattern": "^[a-z_][a-z0-9_]*$",
                    },
                    "signature": {
                        "type": "string",
                        "description": "Function signature",
                    },
                    "body": {
                        "type": "string",
                        "description": "Function body",
                    },
                },
                "required": ["name", "signature", "body"],
                "additionalProperties": False,
            },
            "default": [],
        },
    },
    "required": ["implementation"],
    "additionalProperties": False,
}


def get_code_generation_schema() -> dict[str, Any]:
    """Get the code generation JSON schema for xgrammar."""
    return CODE_GENERATION_SCHEMA


def get_prompt_for_code_generation(
    ir_summary: str, signature: str, constraints: list[str], effects: list[str] | None = None
) -> str:
    """
    Generate a system prompt for code generation from IR.

    Args:
        ir_summary: Summary of what the function should do
        signature: Function signature
        constraints: List of constraints (assertions, preconditions)
        effects: Ordered list of operational steps/effects the function should perform

    Returns:
        Formatted prompt for LLM code generation
    """
    constraints_text = "\n".join(f"  - {c}" for c in constraints) if constraints else "  - None"

    # Include effects as implementation steps if provided
    effects_section = ""
    if effects:
        effects_text = "\n".join(f"  {i + 1}. {effect}" for i, effect in enumerate(effects))
        effects_section = f"""
Implementation Steps (MUST FOLLOW IN ORDER):
---------------------------------------------
{effects_text}

IMPORTANT: Your implementation MUST follow these steps in the exact order specified.
Each step corresponds to an operation the function should perform. Do not skip steps
or reorder them. The effects describe the operational semantics that must be preserved.
"""

    return f"""You are an expert Python programmer. Generate a complete, correct implementation for the following function.

Function Specification:
-----------------------
Purpose: {ir_summary}

Signature: {signature}

Constraints:
{constraints_text}
{effects_section}
Requirements:
-------------
1. Generate ONLY the function body (not the signature or docstring)
2. The implementation must be complete and correct
3. Honor all constraints and assertions
4. STRICTLY follow the implementation steps if provided (they are NOT optional)
5. Use clear, idiomatic Python code
6. Include appropriate error handling
7. Use efficient algorithms where possible
8. Add inline comments for complex logic

Output Format:
--------------
Provide the implementation as a JSON object with:
- implementation.body_statements: List of code statements
- implementation.algorithm: High-level algorithm description
- imports: Any additional imports needed
- helper_functions: Any helper functions needed

Each statement should have:
- type: Type of statement (assignment, return, if_statement, etc.)
- code: Python code for the statement
- rationale: Why this statement is needed (optional)

Generate the implementation as valid JSON:"""


__all__ = ["CODE_GENERATION_SCHEMA", "get_code_generation_schema", "get_prompt_for_code_generation"]
