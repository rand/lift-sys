#!/usr/bin/env python3
"""
Test indentation logic locally without Modal calls.
"""


def test_indentation(statements):
    """Simulate the indentation logic."""
    indent = "    "
    control_flow_types = {
        "if_statement",
        "for_loop",
        "while_loop",
        "elif_statement",
        "else_statement",
    }
    indent_stack = [indent]

    result = []

    for i, stmt in enumerate(statements):
        code = stmt["code"].rstrip()
        stmt_type = stmt.get("type", "expression")

        if i > 0:
            prev_stmt = statements[i - 1]
            prev_type = prev_stmt.get("type", "expression")
            prev_code = prev_stmt["code"].rstrip()

            # Handle else/elif FIRST
            if (
                stmt_type in {"elif_statement", "else_statement"}
                or code.startswith("else")
                or code.startswith("elif")
            ):
                if len(indent_stack) > 1:
                    indent_stack.pop()

            # If previous was control flow ending with ':', increase indent
            if prev_type in control_flow_types and prev_code.endswith(":"):
                indent_stack.append(indent_stack[-1] + "    ")

        current_indent = indent_stack[-1]

        # Add rationale as comment
        if stmt.get("rationale"):
            result.append(f"{current_indent}# {stmt['rationale']}")

        # Add code
        result.append(f"{current_indent}{code}")

    return "\n".join(result)


# Test case 1: if-elif-else
print("=" * 70)
print("TEST 1: if-elif-else chain")
print("=" * 70)

statements1 = [
    {"type": "if_statement", "code": "if score >= 90:", "rationale": "Check for A"},
    {"type": "return", "code": "return 'A'", "rationale": "Return A"},
    {"type": "elif_statement", "code": "elif score >= 80:", "rationale": "Check for B"},
    {"type": "return", "code": "return 'B'", "rationale": "Return B"},
    {"type": "else_statement", "code": "else:", "rationale": "Default case"},
    {"type": "return", "code": "return 'F'", "rationale": "Return F"},
]

result1 = test_indentation(statements1)
print(result1)

# Check if valid
try:
    code1 = f"def test(score):\n{result1}"
    compile(code1, "<test>", "exec")
    print("\n✅ Valid Python!")
except SyntaxError as e:
    print(f"\n❌ Syntax error: {e}")

# Test case 2: for loop with nested if
print("\n" + "=" * 70)
print("TEST 2: for loop with nested if")
print("=" * 70)

statements2 = [
    {"type": "assignment", "code": "result = []", "rationale": "Initialize"},
    {"type": "for_loop", "code": "for x in items:", "rationale": "Iterate"},
    {"type": "if_statement", "code": "if x % 2 == 0:", "rationale": "Check even"},
    {"type": "assignment", "code": "result.append(x)", "rationale": "Add to result"},
    {"type": "return", "code": "return result", "rationale": "Return result"},
]

result2 = test_indentation(statements2)
print(result2)

# Check if valid
try:
    code2 = f"def test(items):\n{result2}"
    compile(code2, "<test>", "exec")
    print("\n✅ Valid Python!")
except SyntaxError as e:
    print(f"\n❌ Syntax error: {e}")

print("\n" + "=" * 70)
