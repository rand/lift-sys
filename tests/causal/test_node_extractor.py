"""Unit tests for AST node extraction (STEP-02).

Tests the NodeExtractor class and extract_nodes function.
"""

import ast

from lift_sys.causal.node_extractor import NodeType, extract_nodes


def test_extract_simple_function():
    """Test extraction of a simple function definition."""
    code = """
def process(x):
    return x * 2
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Should extract: function, return
    assert len(nodes) >= 2

    func_nodes = [n for n in nodes if n.type == NodeType.FUNCTION]
    assert len(func_nodes) == 1
    assert func_nodes[0].name == "process"
    assert func_nodes[0].id == "func:process"
    assert "args" in func_nodes[0].metadata
    assert func_nodes[0].metadata["args"] == ["x"]

    return_nodes = [n for n in nodes if n.type == NodeType.RETURN]
    assert len(return_nodes) == 1
    assert return_nodes[0].metadata["scope"] == "process"


def test_extract_variable_assignment():
    """Test extraction of variable assignments."""
    code = """
def compute(a, b):
    x = a + b
    y = x * 2
    return y
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    var_nodes = [n for n in nodes if n.type == NodeType.VARIABLE]
    assert len(var_nodes) == 2

    var_names = {n.name for n in var_nodes}
    assert var_names == {"x", "y"}

    # Check scoping
    for var_node in var_nodes:
        assert var_node.metadata["scope"] == "compute"


def test_extract_nested_functions():
    """Test extraction of nested function definitions."""
    code = """
def outer(x):
    def inner(y):
        return y + 1
    return inner(x)
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    func_nodes = [n for n in nodes if n.type == NodeType.FUNCTION]
    assert len(func_nodes) == 2

    func_ids = {n.id for n in func_nodes}
    assert "func:outer" in func_ids
    assert "func:outer.inner" in func_ids

    # Check nested function scope
    inner_node = next(n for n in func_nodes if n.name == "inner")
    assert inner_node.metadata["scope"] == "outer"


def test_extract_side_effects():
    """Test extraction of side effect nodes (print, etc.)."""
    code = """
def process(data):
    print("Processing")
    result = data * 2
    print("Done")
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    effect_nodes = [n for n in nodes if n.type == NodeType.EFFECT]
    assert len(effect_nodes) == 2

    for effect_node in effect_nodes:
        assert effect_node.metadata["function"] == "print"
        assert effect_node.metadata["scope"] == "process"


def test_extract_async_function():
    """Test extraction of async function definitions."""
    code = """
async def fetch_data(url):
    result = await get(url)
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    func_nodes = [n for n in nodes if n.type == NodeType.FUNCTION]
    assert len(func_nodes) == 1
    assert func_nodes[0].name == "fetch_data"
    assert func_nodes[0].metadata.get("async") is True


def test_extract_augmented_assignment():
    """Test extraction of augmented assignments (+=, -=, etc.)."""
    code = """
def accumulate(values):
    total = 0
    for v in values:
        total += v
    return total
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    var_nodes = [n for n in nodes if n.type == NodeType.VARIABLE]
    var_names = {n.name for n in var_nodes}
    assert "total" in var_names

    # Check augmented assignment metadata
    total_nodes = [n for n in var_nodes if n.name == "total"]
    aug_assign_nodes = [n for n in total_nodes if n.metadata.get("ast_type") == "AugAssign"]
    assert len(aug_assign_nodes) >= 1


def test_extract_module_level_variables():
    """Test extraction of module-level variables."""
    code = """
CONFIG = {"debug": True}
MAX_SIZE = 100

def process():
    return MAX_SIZE
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    var_nodes = [n for n in nodes if n.type == NodeType.VARIABLE]
    var_names = {n.name for n in var_nodes}
    assert "CONFIG" in var_names
    assert "MAX_SIZE" in var_names

    # Module-level variables should have __module__ scope
    config_node = next(n for n in var_nodes if n.name == "CONFIG")
    assert config_node.metadata["scope"] == "__module__"


def test_no_duplicate_nodes():
    """Test that duplicate nodes are not created."""
    code = """
def process(x):
    y = x + 1
    y = y * 2  # Reassignment
    return y
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Count nodes by ID
    node_ids = [n.id for n in nodes]
    assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs found"


def test_multiple_returns():
    """Test extraction of multiple return statements."""
    code = """
def check(x):
    if x > 0:
        return x
    else:
        return -x
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    return_nodes = [n for n in nodes if n.type == NodeType.RETURN]
    assert len(return_nodes) == 2

    # Each return should have unique ID based on line number
    return_ids = {n.id for n in return_nodes}
    assert len(return_ids) == 2


def test_decorators():
    """Test extraction of decorated functions."""
    code = """
@property
def name(self):
    return self._name

@staticmethod
def create():
    return MyClass()
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    func_nodes = [n for n in nodes if n.type == NodeType.FUNCTION]
    assert len(func_nodes) == 2

    # Check decorators are captured
    for func_node in func_nodes:
        assert "decorators" in func_node.metadata
        assert len(func_node.metadata["decorators"]) > 0


def test_performance_100_nodes():
    """Test that extraction completes in <100ms for 100-node AST."""
    import time

    # Generate code with ~100 nodes
    code_lines = ["def process(x):"]
    for i in range(50):
        code_lines.append(f"    var_{i} = x + {i}")
    code_lines.append("    return var_49")

    code = "\n".join(code_lines)
    tree = ast.parse(code)

    start = time.perf_counter()
    nodes = extract_nodes(tree)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(nodes) >= 50, "Should extract at least 50 nodes"
    assert elapsed_ms < 100, f"Extraction took {elapsed_ms:.2f}ms (expected <100ms)"


def test_extract_nodes_integration():
    """Integration test with realistic code."""
    code = """
def validate(data):
    if not data:
        print("Empty data")
        return None

    result = {"valid": True}
    for item in data:
        if item < 0:
            result["valid"] = False
            break

    return result

def process(input_data):
    validated = validate(input_data)
    if validated and validated["valid"]:
        output = compute(input_data)
        return output
    return None

def compute(values):
    total = sum(values)
    average = total / len(values)
    return average
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Verify we extracted all types
    node_types = {n.type for n in nodes}
    assert NodeType.FUNCTION in node_types
    assert NodeType.VARIABLE in node_types
    assert NodeType.RETURN in node_types
    assert NodeType.EFFECT in node_types

    # Verify function count
    func_nodes = [n for n in nodes if n.type == NodeType.FUNCTION]
    func_names = {n.name for n in func_nodes}
    assert func_names == {"validate", "process", "compute"}

    # Verify line numbers are captured
    for node in nodes:
        assert node.line > 0
