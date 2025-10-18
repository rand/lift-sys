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
        "constraints": {
            "type": "array",
            "description": "Phase 7: Explicit constraints on code generation behavior",
            "items": {
                "oneOf": [
                    {"$ref": "#/definitions/ReturnConstraint"},
                    {"$ref": "#/definitions/LoopBehaviorConstraint"},
                    {"$ref": "#/definitions/PositionConstraint"},
                ]
            },
            "default": [],
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
        },
        "ReturnConstraint": {
            "type": "object",
            "description": "Constraint ensuring computed values are explicitly returned",
            "properties": {
                "type": {
                    "type": "string",
                    "const": "return_constraint",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of the constraint",
                },
                "severity": {
                    "type": "string",
                    "enum": ["error", "warning"],
                    "default": "error",
                },
                "value_name": {
                    "type": "string",
                    "description": "Name of the value that must be returned (e.g., 'count', 'result')",
                },
                "requirement": {
                    "type": "string",
                    "enum": ["MUST_RETURN", "OPTIONAL_RETURN"],
                    "default": "MUST_RETURN",
                },
            },
            "required": ["type", "value_name"],
            "additionalProperties": False,
        },
        "LoopBehaviorConstraint": {
            "type": "object",
            "description": "Constraint enforcing specific loop behaviors",
            "properties": {
                "type": {
                    "type": "string",
                    "const": "loop_constraint",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of the constraint",
                },
                "severity": {
                    "type": "string",
                    "enum": ["error", "warning"],
                    "default": "error",
                },
                "search_type": {
                    "type": "string",
                    "description": "Type of search operation (first, last, all matches)",
                    "enum": ["FIRST_MATCH", "LAST_MATCH", "ALL_MATCHES"],
                    "default": "FIRST_MATCH",
                },
                "requirement": {
                    "type": "string",
                    "description": "Required loop behavior (early return, accumulate, transform)",
                    "enum": ["EARLY_RETURN", "ACCUMULATE", "TRANSFORM"],
                    "default": "EARLY_RETURN",
                },
                "loop_variable": {
                    "type": ["string", "null"],
                    "description": "Optional: Name of the loop variable for clarity",
                },
            },
            "required": ["type"],
            "additionalProperties": False,
        },
        "PositionConstraint": {
            "type": "object",
            "description": "Constraint specifying position requirements between elements",
            "properties": {
                "type": {
                    "type": "string",
                    "const": "position_constraint",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of the constraint",
                },
                "severity": {
                    "type": "string",
                    "enum": ["error", "warning"],
                    "default": "error",
                },
                "elements": {
                    "type": "array",
                    "description": "Elements whose positions are constrained (e.g., ['@', '.'])",
                    "items": {"type": "string"},
                },
                "requirement": {
                    "type": "string",
                    "description": "Required relationship between elements",
                    "enum": ["NOT_ADJACENT", "ORDERED", "MIN_DISTANCE", "MAX_DISTANCE"],
                    "default": "NOT_ADJACENT",
                },
                "min_distance": {
                    "type": "integer",
                    "description": "Minimum character distance between elements",
                    "default": 0,
                },
                "max_distance": {
                    "type": ["integer", "null"],
                    "description": "Maximum character distance between elements (None = unlimited)",
                },
            },
            "required": ["type", "elements"],
            "additionalProperties": False,
        },
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

**CRITICAL: Effects must be EXPLICIT about implementation details:**

1. **Explicit Return Statements - MANDATORY**:
   - Effects MUST specify ALL return paths, including error/not-found cases
   - Example: "After loop completes without finding value, explicitly return -1"
   - Never allow implicit None returns - always specify the return value

   **Return Value Examples** (ALWAYS include return effect if function returns value):

   GOOD (Explicit Return):
   - Effect 1: "Split the string by spaces"
   - Effect 2: "Count the words in the list"
   - Effect 3: "Return the count as an integer" ✓

   BAD (Missing Return):
   - Effect 1: "Split the string by spaces"
   - Effect 2: "Count the words in the list"
   - (No return effect - WRONG!) ✗

   **Return Effect Patterns** (Match return type from signature):
   - If signature returns int: "Return the count (int)"
   - If signature returns str: "Return the result string (str)"
   - If signature returns bool: "Return True if found, False otherwise (bool)"
   - If signature returns list[T]: "Return the filtered list (list[T])"
   - If signature returns Optional[T]: "Return the value if found, None otherwise (Optional[T])"

2. **Literal Values**:
   - When user says "return exactly 'X'", effects must emphasize literal return
   - Example: "In else clause, return the literal string 'other'" (not computed)
   - Be explicit: "return 'other'" not "return type name"

3. **Edge Cases**:
   - Effects must handle empty inputs: "If list is empty, return [value]"
   - Effects must handle all branches: "If condition, return X, else return Y"
   - Be explicit about what happens at boundaries

4. **Loop Patterns - CRITICAL for Search Operations**:

   **Pattern 1: FIRST_MATCH (Early Termination)**
   Use when: Finding first occurrence, any/all checks, existence checks

   Example (find_index):
   - Effect 1: "Iterate through list with enumerate starting at index 0"
   - Effect 2: "Check if current item matches condition"
   - Effect 3: "If match found, IMMEDIATELY return the index (inside loop)" ✓
   - Effect 4: "After loop completes without match, return -1" ✓

   Keywords indicating FIRST_MATCH:
   - "find first", "search for", "locate", "index of"
   - "any element", "exists", "contains"
   - "stop when", "return when found"

   **Pattern 2: LAST_MATCH (Full Iteration)**
   Use when: Finding last occurrence, accumulating, filtering

   Example (find_last_index):
   - Effect 1: "Iterate through entire list"
   - Effect 2: "Track the last matching index"
   - Effect 3: "After loop completes, return tracked index or -1"

   Keywords indicating LAST_MATCH:
   - "find last", "count all", "filter", "sum"
   - "accumulate", "collect all", "maximum", "minimum"

   **Pattern 3: ALL_MATCHES (Transform/Filter)**
   Use when: Building new collection, transforming all elements

   Example (filter_positive):
   - Effect 1: "Initialize empty result list"
   - Effect 2: "Iterate through all elements"
   - Effect 3: "Append matching elements to result"
   - Effect 4: "After loop completes, return result list"

   **Loop Termination Clarity**:
   - ALWAYS specify: "when found", "until condition", "for each element"
   - Early returns: "return X immediately when Y" or "break loop when Z"
   - Full iteration: "after processing all elements" or "when loop completes"

5. **Control Flow**:
   - Be explicit about if/elif/else structure
   - Specify exact order of checks
   - Specify exact return values for each branch

User's request:
{user_prompt}

Generate the IR as valid JSON matching the schema:"""


__all__ = ["IR_JSON_SCHEMA", "get_ir_schema", "get_prompt_for_ir_generation"]
