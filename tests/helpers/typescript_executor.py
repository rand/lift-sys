"""Helper module for executing TypeScript code in tests.

This module provides utilities to execute generated TypeScript code
with test inputs and capture results, similar to the Python code execution
approach used in EquivalenceChecker.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExecutionResult:
    """Result of TypeScript code execution."""

    success: bool
    stdout: str
    stderr: str
    returncode: int
    duration_seconds: float
    output: Any | None = None
    error: str | None = None


def execute_typescript(
    code: str,
    test_inputs: dict[str, Any],
    timeout_seconds: int = 5,
    use_ts_node: bool = True,
) -> ExecutionResult:
    """
    Execute TypeScript code with test inputs and return result.

    This function:
    1. Extracts the function name from TypeScript code
    2. Creates a wrapper that calls the function with test inputs
    3. Writes code to temporary file
    4. Executes with Node.js (via ts-node or tsc + node)
    5. Captures stdout/stderr and returns structured result
    6. Cleans up temporary files

    Args:
        code: TypeScript code snippet containing function definition
        test_inputs: Dictionary of function arguments
        timeout_seconds: Maximum execution time (default: 5s)
        use_ts_node: If True, use ts-node for direct execution.
                     If False, compile with tsc then run with node.

    Returns:
        ExecutionResult with execution details and output

    Example:
        >>> code = '''
        ... function add(a: number, b: number): number {
        ...     return a + b;
        ... }
        ... '''
        >>> result = execute_typescript(code, {"a": 2, "b": 3})
        >>> result.success
        True
        >>> result.output
        5
    """
    import time

    start_time = time.time()

    # Extract function name from code
    func_name = _extract_function_name(code)
    if not func_name:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="Could not extract function name from code",
            returncode=1,
            duration_seconds=time.time() - start_time,
            error="Could not extract function name",
        )

    # Create wrapper code that calls the function and prints result
    wrapper = _create_wrapper_code(code, func_name, test_inputs)

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False, encoding="utf-8") as f:
        f.write(wrapper)
        code_file = f.name

    try:
        if use_ts_node:
            # Execute with ts-node (faster, no compilation step)
            result = _execute_with_ts_node(code_file, timeout_seconds)
        else:
            # Compile with tsc then execute with node
            result = _execute_with_tsc(code_file, timeout_seconds)

        duration = time.time() - start_time

        # Parse output if successful
        output = None
        error = None
        if result.returncode == 0 and result.stdout.strip():
            try:
                output = json.loads(result.stdout.strip())
            except json.JSONDecodeError as e:
                error = f"Failed to parse JSON output: {e}"

        if result.returncode != 0:
            error = result.stderr or "Execution failed"

        return ExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            duration_seconds=duration,
            output=output,
            error=error,
        )

    finally:
        # Clean up temp file
        try:
            os.unlink(code_file)
            # Also clean up .js file if tsc was used
            js_file = code_file.replace(".ts", ".js")
            if os.path.exists(js_file):
                os.unlink(js_file)
        except Exception:
            pass  # Best effort cleanup


def _extract_function_name(code: str) -> str | None:
    """
    Extract function name from TypeScript code.

    Supports multiple TypeScript function declaration patterns:
    - function foo() { ... }
    - const foo = () => { ... }
    - export function foo() { ... }
    - async function foo() { ... }

    Args:
        code: TypeScript code snippet

    Returns:
        Function name or None if not found
    """
    import re

    # Try multiple patterns
    patterns = [
        r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",  # function foo()
        r"const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=",  # const foo =
        r"let\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=",  # let foo =
        r"export\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",  # export function foo()
        r"export\s+const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=",  # export const foo =
    ]

    for pattern in patterns:
        match = re.search(pattern, code)
        if match:
            return match.group(1)

    return None


def _create_wrapper_code(code: str, func_name: str, test_inputs: dict[str, Any]) -> str:
    """
    Create wrapper TypeScript code that executes function and prints result.

    Args:
        code: Original TypeScript code
        func_name: Name of function to call
        test_inputs: Dictionary of function arguments

    Returns:
        Wrapper code as string
    """
    # Convert test inputs to TypeScript object literal
    inputs_json = json.dumps(test_inputs)

    wrapper = f"""
{code}

// Execute function with test input
(async () => {{
    try {{
        const testInputs = {inputs_json};
        const result = await {func_name}(...Object.values(testInputs));
        console.log(JSON.stringify(result));
        process.exit(0);
    }} catch (error) {{
        console.error(JSON.stringify({{ __error__: String(error) }}));
        process.exit(1);
    }}
}})();
"""
    return wrapper


def _execute_with_ts_node(code_file: str, timeout_seconds: int) -> subprocess.CompletedProcess:
    """
    Execute TypeScript file with ts-node.

    Args:
        code_file: Path to TypeScript file
        timeout_seconds: Execution timeout

    Returns:
        subprocess.CompletedProcess result
    """
    return subprocess.run(
        ["npx", "ts-node", code_file],
        capture_output=True,
        timeout=timeout_seconds,
        text=True,
    )


def _execute_with_tsc(code_file: str, timeout_seconds: int) -> subprocess.CompletedProcess:
    """
    Execute TypeScript file by compiling with tsc then running with node.

    Args:
        code_file: Path to TypeScript file
        timeout_seconds: Execution timeout

    Returns:
        subprocess.CompletedProcess result combining compilation and execution
    """
    # First compile with tsc
    compile_result = subprocess.run(
        ["npx", "tsc", code_file, "--outDir", str(Path(code_file).parent)],
        capture_output=True,
        timeout=timeout_seconds,
        text=True,
    )

    if compile_result.returncode != 0:
        return compile_result

    # Then execute with node
    js_file = code_file.replace(".ts", ".js")
    return subprocess.run(
        ["node", js_file],
        capture_output=True,
        timeout=timeout_seconds,
        text=True,
    )


def check_typescript_runtime_available() -> tuple[bool, str]:
    """
    Check if TypeScript runtime (ts-node or tsc + node) is available.

    Returns:
        Tuple of (available, message)
    """
    # Check for ts-node
    try:
        result = subprocess.run(
            ["npx", "ts-node", "--version"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        if result.returncode == 0:
            return True, f"ts-node available: {result.stdout.strip()}"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check for tsc + node
    try:
        tsc_result = subprocess.run(
            ["npx", "tsc", "--version"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        node_result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        if tsc_result.returncode == 0 and node_result.returncode == 0:
            return (
                True,
                f"tsc + node available: tsc {tsc_result.stdout.strip()}, node {node_result.stdout.strip()}",
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return False, "Neither ts-node nor tsc+node available"
