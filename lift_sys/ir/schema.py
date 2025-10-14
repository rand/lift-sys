"""JSON schema for lift-sys IR, compatible with xgrammar constrained generation."""

from typing import Any

# JSON Schema for lift-sys IntermediateRepresentation
# This schema enforces the structure during LLM generation via xgrammar
IR_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "IntermediateRepresentation",
    "description": "lift-sys intermediate representation for function specifications",
    "type": "object",
    "properties": {
        "intent": {
            "type": "object",
            "description": "High-level description of what the function should do",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief summary of the function's purpose",
                    "minLength": 10,
                },
                "rationale": {
                    "type": ["string", "null"],
                    "description": "Detailed explanation of why this function is needed",
                },
                "holes": {
                    "type": "array",
                    "description": "Ambiguities or uncertainties in the intent",
                    "items": {"$ref": "#/definitions/TypedHole"},
                    "default": [],
                },
            },
            "required": ["summary"],
            "additionalProperties": False,
        },
        "signature": {
            "type": "object",
            "description": "Function signature with parameters and return type",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Function name (snake_case for Python)",
                    "pattern": "^[a-z_][a-z0-9_]*$",
                },
                "parameters": {
                    "type": "array",
                    "description": "Function parameters",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Parameter name",
                                "pattern": "^[a-z_][a-z0-9_]*$",
                            },
                            "type_hint": {
                                "type": "string",
                                "description": "Python type hint (e.g., 'int', 'str', 'list[int]')",
                            },
                            "description": {
                                "type": ["string", "null"],
                                "description": "Parameter description",
                            },
                        },
                        "required": ["name", "type_hint"],
                        "additionalProperties": False,
                    },
                },
                "returns": {
                    "type": ["string", "null"],
                    "description": "Return type hint",
                },
                "holes": {
                    "type": "array",
                    "description": "Ambiguities in the signature",
                    "items": {"$ref": "#/definitions/TypedHole"},
                    "default": [],
                },
            },
            "required": ["name", "parameters"],
            "additionalProperties": False,
        },
        "effects": {
            "type": "array",
            "description": "Side effects or external interactions",
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the side effect",
                    },
                    "holes": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/TypedHole"},
                        "default": [],
                    },
                },
                "required": ["description"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "assertions": {
            "type": "array",
            "description": "Logical assertions (preconditions, postconditions, invariants)",
            "items": {
                "type": "object",
                "properties": {
                    "predicate": {
                        "type": "string",
                        "description": "Logical predicate (e.g., 'x > 0', 'result != None')",
                    },
                    "rationale": {
                        "type": ["string", "null"],
                        "description": "Why this assertion is needed",
                    },
                    "holes": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/TypedHole"},
                        "default": [],
                    },
                },
                "required": ["predicate"],
                "additionalProperties": False,
            },
            "default": [],
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata about the IR",
            "properties": {
                "source_path": {
                    "type": ["string", "null"],
                    "description": "Source file path",
                },
                "language": {
                    "type": ["string", "null"],
                    "description": "Target programming language",
                },
                "origin": {
                    "type": ["string", "null"],
                    "description": "Origin of the IR (e.g., 'prompt', 'reverse', 'refinement')",
                },
                "evidence": {
                    "type": "array",
                    "description": "Evidence supporting the IR",
                    "items": {"type": "object"},
                    "default": [],
                },
            },
            "additionalProperties": False,
        },
    },
    "required": ["intent", "signature"],
    "additionalProperties": False,
    "definitions": {
        "TypedHole": {
            "type": "object",
            "description": "Explicit representation of unknown or ambiguous information",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Unique identifier for this hole",
                },
                "type_hint": {
                    "type": "string",
                    "description": "Expected type of information to fill this hole",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what's missing",
                    "default": "",
                },
                "constraints": {
                    "type": "object",
                    "description": "Constraints on acceptable values",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "kind": {
                    "type": "string",
                    "description": "Category of hole",
                    "enum": ["intent", "signature", "effect", "assertion", "implementation"],
                    "default": "intent",
                },
            },
            "required": ["identifier", "type_hint"],
            "additionalProperties": False,
        }
    },
}


def get_ir_schema() -> dict[str, Any]:
    """Get the IR JSON schema for xgrammar constrained generation."""
    return IR_JSON_SCHEMA


def get_prompt_for_ir_generation(user_prompt: str) -> str:
    """
    Generate a system prompt that instructs the LLM to create IR from user input.

    Args:
        user_prompt: Natural language description from user

    Returns:
        Formatted prompt for LLM with IR schema instructions
    """
    return f"""You are an expert at converting natural language specifications into formal intermediate representations (IR).

Given a natural language description of a function, generate a JSON object following the lift-sys IR schema.

The IR should include:
1. **intent**: High-level purpose (summary and optional rationale)
2. **signature**: Function name, parameters with types, and return type
3. **effects**: Side effects or external interactions (if any)
4. **assertions**: Logical constraints, preconditions, or postconditions (if any)
5. **metadata**: Language and origin information

Important guidelines:
- Function names should be snake_case for Python
- Parameter names should be descriptive and snake_case
- Type hints should use Python syntax (int, str, list[int], dict[str, Any], etc.)
- If type information is ambiguous, use a TypedHole to mark it
- Extract any constraints or requirements as assertions
- Be specific and complete

User's request:
{user_prompt}

Generate the IR as valid JSON matching the schema:"""


__all__ = ["IR_JSON_SCHEMA", "get_ir_schema", "get_prompt_for_ir_generation"]
