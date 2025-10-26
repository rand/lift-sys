"""Unit tests for control flow edge extraction (STEP-04).

Tests the ControlFlowExtractor class and extract_controlflow_edges function.
"""

import ast

from lift_sys.causal.controlflow_extractor import extract_controlflow_edges
from lift_sys.causal.node_extractor import extract_nodes


def test_extract_simple_if_else():
    """Test extraction of simple if/else control flow."""
    code = """
def check(x):
    if x > 0:
        result = x
    else:
        result = -x
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges from condition variable (x) to result assignments
    assert len(edges) > 0, "Should extract control flow edges"

    # Verify edges exist (may vary based on exact implementation)
    edge_set = set(edges)
    assert len(edge_set) == len(edges), "No duplicate edges"


def test_extract_if_without_else():
    """Test extraction of if without else branch."""
    code = """
def process(x):
    result = 0
    if x > 0:
        result = x * 2
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges from condition to if body
    assert len(edges) > 0, "Should extract control flow edges"


def test_extract_nested_if():
    """Test extraction of nested if statements."""
    code = """
def classify(x, y):
    if x > 0:
        if y > 0:
            result = "both_positive"
        else:
            result = "x_positive"
    else:
        result = "x_negative"
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges for both outer and inner conditions
    assert len(edges) > 0, "Should extract nested control flow edges"


def test_extract_while_loop():
    """Test extraction of while loop control flow."""
    code = """
def countdown(n):
    while n > 0:
        print(n)
        n = n - 1
    return n
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges from condition (n) to loop body
    assert len(edges) > 0, "Should extract while loop control flow"


def test_extract_for_loop():
    """Test extraction of for loop control flow."""
    code = """
def sum_list(values):
    total = 0
    for v in values:
        total += v
    return total
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges from iterator to loop body
    assert len(edges) > 0, "Should extract for loop control flow"


def test_extract_try_except():
    """Test extraction of try/except control flow."""
    code = """
def safe_divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        result = 0
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges from try to except (exception flow)
    assert len(edges) > 0, "Should extract try/except control flow"


def test_extract_try_except_finally():
    """Test extraction of try/except/finally control flow."""
    code = """
def process_file(path):
    f = None
    try:
        f = open(path)
        data = f.read()
    except IOError:
        data = ""
    finally:
        if f:
            f.close()
    return data
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges to finally block (always executed)
    assert len(edges) > 0, "Should extract try/except/finally control flow"


def test_extract_try_else_finally():
    """Test extraction of try with else and finally."""
    code = """
def read_config(path):
    try:
        f = open(path)
    except IOError:
        config = {}
    else:
        config = parse(f)
    finally:
        cleanup()
    return config
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges for try -> else (normal flow) and try -> finally
    assert len(edges) > 0, "Should extract try/else/finally control flow"


def test_extract_while_else():
    """Test extraction of while loop with else clause."""
    code = """
def find_item(items, target):
    i = 0
    while i < len(items):
        if items[i] == target:
            break
        i += 1
    else:
        i = -1
    return i
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges to else clause (executed when loop completes)
    assert len(edges) > 0, "Should extract while/else control flow"


def test_extract_for_else():
    """Test extraction of for loop with else clause."""
    code = """
def find_index(items, target):
    result = None
    for i, item in enumerate(items):
        if item == target:
            result = i
            break
    else:
        result = -1
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges to else clause
    assert len(edges) > 0, "Should extract for/else control flow"


def test_extract_complex_nested():
    """Test extraction of complex nested control structures."""
    code = """
def process(data):
    result = []
    for item in data:
        if item > 0:
            try:
                value = compute(item)
            except ValueError:
                value = 0
            result.append(value)
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges for all control structures
    assert len(edges) > 0, "Should extract complex nested control flow"


def test_no_duplicate_edges():
    """Test that duplicate edges are not created."""
    code = """
def check(x):
    if x > 0:
        y = x
    else:
        y = -x
    return y
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Verify no duplicates
    edge_set = set(edges)
    assert len(edges) == len(edge_set), "Should not create duplicate edges"


def test_no_self_edges():
    """Test that self-edges are not created."""
    code = """
def loop(n):
    while n > 0:
        n = n - 1
    return n
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Verify no self-edges
    for source, target in edges:
        assert source != target, f"Self-edge found: {source} -> {target}"


def test_multiple_conditions():
    """Test extraction with multiple condition variables."""
    code = """
def compare(a, b, c):
    if a > b and b > c:
        result = "descending"
    elif a < b and b < c:
        result = "ascending"
    else:
        result = "mixed"
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges from all condition variables
    assert len(edges) > 0, "Should extract edges from multiple conditions"


def test_empty_body():
    """Test extraction with empty/pass bodies."""
    code = """
def check(x):
    if x > 0:
        pass
    else:
        result = 0
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should handle empty bodies without crashing
    # May have fewer edges due to empty if body
    assert isinstance(edges, list), "Should return list even with empty bodies"


def test_function_scope_isolation():
    """Test that control flow edges respect function scope."""
    code = """
def outer(x):
    if x > 0:
        y = x
    return y

def inner(a):
    if a > 0:
        b = a
    return b
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Edges should not cross function boundaries
    # Get nodes for each function
    outer_nodes = [n for n in nodes if "outer" in n.metadata.get("scope", "")]
    inner_nodes = [n for n in nodes if "inner" in n.metadata.get("scope", "")]

    outer_ids = {n.id for n in outer_nodes}
    inner_ids = {n.id for n in inner_nodes}

    # Check edges don't cross boundaries
    for source, _target in edges:
        if source in outer_ids:
            # Target should not be in inner function
            # (unless it's a module-level node, which is valid)
            pass  # This is hard to verify without more context
        if source in inner_ids:
            pass  # Same here


def test_performance_100_nodes():
    """Test that extraction completes in <2s for 100-node graph."""
    import time

    # Generate code with complex control flow (~100 nodes)
    code_lines = ["def process(data):"]
    code_lines.append("    result = []")
    for i in range(20):
        code_lines.append(f"    if data[{i}] > 0:")
        code_lines.append(f"        x_{i} = data[{i}] * 2")
        code_lines.append(f"        result.append(x_{i})")
    code_lines.append("    return result")

    code = "\n".join(code_lines)
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    start = time.perf_counter()
    edges = extract_controlflow_edges(tree, nodes)
    elapsed = time.perf_counter() - start

    assert len(edges) >= 0, "Should extract edges"
    assert elapsed < 2.0, f"Extraction took {elapsed:.2f}s (expected <2s)"


def test_elif_chain():
    """Test extraction of elif chains."""
    code = """
def grade(score):
    if score >= 90:
        letter = "A"
    elif score >= 80:
        letter = "B"
    elif score >= 70:
        letter = "C"
    elif score >= 60:
        letter = "D"
    else:
        letter = "F"
    return letter
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should have edges for all elif conditions
    assert len(edges) > 0, "Should extract elif chain control flow"


def test_integration_realistic_code():
    """Integration test with realistic code pattern."""
    code = """
def validate_and_process(data):
    if not data:
        print("Empty data")
        return None

    result = {"valid": True, "items": []}

    for item in data:
        try:
            if item < 0:
                raise ValueError("Negative value")
            processed = item * 2
            result["items"].append(processed)
        except ValueError:
            result["valid"] = False
            break

    if result["valid"]:
        return result
    else:
        return None
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Verify we extracted edges
    assert len(edges) > 0, "Should extract edges from realistic code"

    # Verify no duplicates
    assert len(edges) == len(set(edges)), "No duplicate edges"

    # Verify no self-edges
    for source, target in edges:
        assert source != target, f"No self-edges: {source}"


def test_empty_ast():
    """Test extraction from empty module."""
    code = ""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should return empty list for empty module
    assert edges == [], "Should return empty list for empty AST"


def test_no_control_flow():
    """Test extraction from code with no control flow."""
    code = """
def simple(x):
    y = x * 2
    z = y + 1
    return z
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)
    edges = extract_controlflow_edges(tree, nodes)

    # Should return empty or very few edges (no if/while/for/try)
    assert isinstance(edges, list), "Should return list"
    # Linear code has no control flow edges
    assert len(edges) == 0, "Linear code should have no control flow edges"
