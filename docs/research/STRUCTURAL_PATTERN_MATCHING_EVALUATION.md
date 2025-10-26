# Structural Pattern Matching Tools: Evaluation for lift-sys

**Date**: October 16, 2025
**Status**: 📊 **EVALUATION COMPLETE**
**Tools Evaluated**: Comby, ast-grep, Semgrep

---

## Executive Summary

This document evaluates structural pattern matching tools (Comby, ast-grep, Semgrep) for potential integration with lift-sys. These tools enable **structural code search and rewriting** using pattern-based templates with holes - conceptually similar to lift-sys's TypedHole system but for code transformation rather than generation.

**Key Finding**: **ast-grep is the most promising tool for lift-sys integration**, offering:
- ✅ Better Python support (tree-sitter parser)
- ✅ Library API (Python and Node.js bindings)
- ✅ Fast (Rust-based, parallel processing)
- ✅ Easy integration (`pip install ast-grep-cli`)

**Recommended Use Cases**:
1. **Reverse Mode**: Extract IR patterns from existing code
2. **Code Repair**: Pattern-based bug fixing (enhance AST repair)
3. **Validation**: Verify generated code matches expected patterns
4. **Constraint Mining**: Extract reusable patterns for typed holes

---

## Part 1: Comby Overview

### What is Comby?

**Comby** is a structural code search and replace tool that supports nearly every programming language.

**Core Innovation**: Uses **holes** (`:[name]`) to match code structures, not just text patterns.

**Example**:
```bash
# Match: failUnlessEqual(x, y)
# Replace: assertEqual(x, y)
comby 'failUnlessEqual(:[a],:[b])' 'assertEqual(:[a],:[b])' example.py
```

**Pattern**: `:[a]` and `:[b]` are holes that match any code fragment while preserving structure.

### How Comby Works

**Architecture**:
- Written in OCaml
- Uses lightweight parsing (not full AST)
- Understands balanced delimiters, strings, comments
- Respects language structure without full semantic analysis

**Pattern Syntax**:

```
:[hole]           # Matches any code fragment
:[hole~regex]     # Matches with regex constraint
...               # Anonymous hole (match but don't capture)
```

**Matching Semantics**:
- **Lazy matching**: Finds shortest match
- **Balanced delimiters**: Respects `()`, `[]`, `{}`
- **Syntax-aware**: Understands strings, comments

**Example Patterns**:

```python
# Match if statements with any condition
if (:[condition]): :[body]

# Match function calls with specific argument count
foo(:[arg1], :[arg2])

# Match with regex constraint (numbers only)
bar(:[num~\d+])
```

### Comby Features

**1. Rules Language**:
```yaml
rule:
  match: if (:[x] == :[x])
  rewrite: if True  # x == x is always true
```

**2. Custom Language Definitions** (JSON):
```json
{
  "user_defined_delimiters": [["begin", "end"]],
  "user_defined_comments": [["(*", "*)"]],
  "user_defined_strings": [["'", "'"]]
}
```

**3. Fresh Identifier Generation**:
```
# Generate unique identifiers during rewrite
:[fresh_id()]
```

**4. Programmatic API** (OCaml):
```ocaml
Matcher.all ~template ~source  (* Find all matches *)
Rewriter.all ~rewrite_template ~matches  (* Apply rewrites *)
```

### Comby Limitations

**❌ No indentation-sensitive language support**
- Python, Haskell not fully supported
- Requires special handling for whitespace

**❌ Not semantically aware**
- Doesn't understand types, scopes, data flow
- Can miss matches or generate invalid code

**❌ Complex queries are hard**
- Limited logical operators
- Can't express "function that doesn't call X"

**❌ Python support is weak**
- Better suited for C-like languages

---

## Part 2: Analogies to lift-sys

### Conceptual Similarities

| Comby Concept | lift-sys Equivalent | Purpose |
|---------------|---------------------|---------|
| `:[hole]` | `TypedHole` | Variable placeholder in pattern |
| Pattern template | IR signature/effects | Structure specification |
| Rewrite template | Code generation | Transformation output |
| Rules language | Constraints | Validation and transformation rules |
| Balanced delimiters | AST structure | Syntax awareness |

### Key Insight: Inverse Operations

**Comby**: Pattern matching for **code transformation** (code → code)
```
Pattern: if (:[x] == :[x])  →  Rewrite: if True
```

**lift-sys**: Typed holes for **code generation** (IR → code)
```
TypedHole: <?param_type: str?>  →  Generated: "int"
```

**Potential Synergy**: Use Comby-style patterns for **reverse mode** (code → IR)
```
Code: def add(x: int, y: int) -> int: return x + y
Pattern: def :[name](:[params]): return :[expr]
Extract IR: {
  "signature": {"name": "add", "parameters": ["x: int", "y: int"]},
  "effects": [{"description": "return x + y"}]
}
```

---

## Part 3: Potential Use Cases in lift-sys

### Use Case 1: Reverse Mode (Code-to-IR Extraction)

**Goal**: Extract IR from existing Python code

**Current Challenge**: No systematic way to parse code into IR

**Comby Solution**:
```python
# Define patterns for common code structures
patterns = [
    {
        "pattern": "def :[name](:[params]) -> :[return_type]:\n    return :[body]",
        "extract": {
            "signature.name": ":[name]",
            "signature.parameters": ":[params]",
            "signature.returns": ":[return_type]",
            "effects": [{"description": "return :[body]"}]
        }
    },
    {
        "pattern": "if :[condition]:\n    :[then_branch]\nelse:\n    :[else_branch]",
        "extract": {
            "effects": [
                {"description": "if :[condition]: :[then_branch]"},
                {"description": "else: :[else_branch]"}
            ]
        }
    }
]

# Apply patterns to extract IR
code = """
def validate_age(age: int) -> str:
    if age >= 18:
        return 'adult'
    else:
        return 'minor'
"""

ir = extract_ir_from_code(code, patterns)
```

**Benefits**:
- Systematic IR extraction from codebases
- Build IR corpus from existing code
- Enable bidirectional translation (code ↔ IR)

### Use Case 2: Code Repair with Patterns

**Goal**: Enhance AST repair engine with pattern-based fixes

**Current Approach**: Deterministic AST transformations in `ast_repair.py`

**Enhanced Approach**:
```python
repair_patterns = [
    {
        # Fix: type(value).__name__ → 'other'
        "pattern": "return type(:[value]).__name__",
        "rewrite": "return 'other'",
        "condition": "function_name.startswith('get_type')"
    },
    {
        # Fix: isinstance check order (bool before int)
        "pattern": "isinstance(:[v], int) or isinstance(:[v], bool)",
        "rewrite": "isinstance(:[v], bool) or isinstance(:[v], int)"
    },
    {
        # Fix: missing return in branches
        "pattern": "if :[cond]:\n    :[then]\nelse:\n    :[else_no_return]",
        "rewrite": "if :[cond]:\n    :[then]\nelse:\n    :[else_no_return]\n    return None",
        "condition": "not has_return(:[else_no_return])"
    }
]
```

**Benefits**:
- Declarative repair rules (easier to maintain)
- Pattern library for common bugs
- Composable repair strategies

### Use Case 3: Generated Code Validation

**Goal**: Verify generated code matches expected patterns

**Current Approach**: AST validation, assertion checking

**Enhanced Approach**:
```python
validation_patterns = [
    {
        "name": "type_checker_returns_literal",
        "pattern": "def get_type_name(:[params]):\n    :[body~.*return '[^']+'].*",
        "description": "Type checker must return literal strings"
    },
    {
        "name": "no_computed_types",
        "pattern": ":[any~.*type\(.*\).__name__.*]",
        "violation": True,  # This pattern should NOT match
        "message": "Must not compute types dynamically"
    },
    {
        "name": "proper_bool_check",
        "pattern": "isinstance(:[v], bool).*isinstance(:[v], int)",
        "description": "Bool check must come before int check"
    }
]

def validate_generated_code(code: str, patterns: list) -> ValidationResult:
    """Validate code against pattern constraints."""
    for pattern in patterns:
        if pattern.get("violation"):
            # This pattern should NOT match
            if comby.match(pattern["pattern"], code):
                return ValidationResult(
                    passed=False,
                    message=pattern["message"]
                )
        else:
            # This pattern SHOULD match
            if not comby.match(pattern["pattern"], code):
                return ValidationResult(
                    passed=False,
                    message=f"Missing: {pattern['description']}"
                )
    return ValidationResult(passed=True)
```

**Benefits**:
- Declarative validation rules
- Catch semantic errors early
- Complement AST and assertion validation

### Use Case 4: Constraint Mining from Codebases

**Goal**: Extract reusable patterns to build constraint library

**Approach**:
```python
# Mine patterns from successful code examples
def mine_constraints_from_repo(repo_path: str) -> list[Constraint]:
    """Extract common patterns as constraints."""

    # Find all type-checking functions
    type_checkers = comby.find(
        pattern="def get_type_name(:[params]):\n    :[body]",
        path=repo_path
    )

    constraints = []
    for match in type_checkers:
        # Extract patterns from successful implementations
        if "isinstance" in match.body:
            # Extract isinstance patterns
            checks = comby.find(
                pattern="isinstance(:[var], :[type])",
                source=match.body
            )

            # Build constraint from pattern
            constraint = Constraint(
                predicate=f"uses isinstance checks for {[c.type for c in checks]}",
                examples=[match.body],
                source="mined_from_codebase"
            )
            constraints.append(constraint)

    return constraints
```

**Benefits**:
- Learn from existing codebases
- Build constraint library automatically
- Improve IR generation quality

### Use Case 5: Template-Based Generation (Alternative to LLM)

**Goal**: Use patterns for simple, deterministic generation

**Approach**:
```python
generation_templates = {
    "type_checker": """
def get_type_name(value: Any) -> str:
    if isinstance(value, bool):
        return 'other'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, str):
        return 'str'
    elif isinstance(value, list):
        return 'list'
    else:
        return 'other'
""",

    "validator": """
def validate_:[field](:[field]: :[type]) -> bool:
    if not isinstance(:[field], :[type]):
        return False
    :[additional_checks]
    return True
"""
}

def generate_from_template(ir: IntermediateRepresentation) -> str:
    """Generate code from template if IR matches known pattern."""

    # Check if IR matches template pattern
    if is_type_checker(ir):
        template = generation_templates["type_checker"]
        # Fill in template holes from IR
        return fill_template(template, ir)

    # Fall back to LLM generation
    return llm_generate(ir)
```

**Benefits**:
- Fast, deterministic generation for common patterns
- No LLM cost for template-based generation
- Guaranteed correctness for known patterns

---

## Part 4: Integration Approaches

### Approach 1: CLI Tool Integration (Simplest)

**Method**: Call Comby as subprocess

**Implementation**:
```python
import subprocess
import json

class CombyIntegration:
    """CLI-based Comby integration."""

    def match(self, pattern: str, source: str) -> list[dict]:
        """Find matches using Comby CLI."""
        result = subprocess.run(
            ["comby", pattern, "-stdin", "-json-lines"],
            input=source,
            capture_output=True,
            text=True
        )

        matches = [json.loads(line) for line in result.stdout.split("\n") if line]
        return matches

    def rewrite(self, pattern: str, rewrite: str, source: str) -> str:
        """Apply rewrite using Comby CLI."""
        result = subprocess.run(
            ["comby", pattern, rewrite, "-stdin"],
            input=source,
            capture_output=True,
            text=True
        )
        return result.stdout
```

**Pros**:
- ✅ Simple to implement
- ✅ No dependencies (just install Comby)
- ✅ Works with any Comby version

**Cons**:
- ❌ Subprocess overhead
- ❌ Limited error handling
- ❌ Can't customize matching logic

### Approach 2: Python Bindings (Moderate)

**Method**: Use comby-python library

**Installation**:
```bash
pip install comby
```

**Implementation**:
```python
from comby import Comby

class CombyPythonIntegration:
    """Python bindings integration."""

    def __init__(self):
        self.comby = Comby()

    def match(self, pattern: str, source: str, language: str = "python") -> list:
        """Find matches using Python API."""
        return self.comby.matches(
            template=pattern,
            source=source,
            matcher=language
        )

    def rewrite(self, pattern: str, rewrite: str, source: str) -> str:
        """Apply rewrite using Python API."""
        return self.comby.rewrite(
            match_template=pattern,
            rewrite_template=rewrite,
            source=source
        )
```

**Pros**:
- ✅ No subprocess overhead
- ✅ Better error handling
- ✅ More Pythonic API

**Cons**:
- ❌ Requires comby-python installation
- ❌ Still limited Python language support
- ❌ Maintenance depends on bindings

### Approach 3: Inspired Reimplementation (Most Control)

**Method**: Implement Comby-like pattern matching in Python

**Approach**:
```python
class PatternMatcher:
    """Comby-inspired pattern matching for Python."""

    def __init__(self):
        self.hole_pattern = re.compile(r':\[([^\]]+)\]')

    def compile_pattern(self, pattern: str) -> dict:
        """Convert Comby pattern to regex + AST constraints."""
        # Extract holes
        holes = self.hole_pattern.findall(pattern)

        # Convert to regex with capture groups
        regex = pattern
        for hole in holes:
            # Handle regex constraints: :[hole~regex]
            if '~' in hole:
                name, constraint = hole.split('~')
                regex = regex.replace(f':[{hole}]', f'(?P<{name}>{constraint})')
            else:
                # Default: match any characters (lazy)
                regex = regex.replace(f':[{hole}]', f'(?P<{hole}>.*?)')

        return {
            'holes': holes,
            'regex': re.compile(regex, re.DOTALL),
            'ast_constraints': self._extract_ast_constraints(pattern)
        }

    def match(self, pattern: str, source: str) -> list[dict]:
        """Find matches respecting Python AST structure."""
        compiled = self.compile_pattern(pattern)

        # Regex match
        text_matches = compiled['regex'].finditer(source)

        # Filter by AST constraints
        ast_matches = []
        for match in text_matches:
            if self._validate_ast_constraints(match, compiled['ast_constraints']):
                ast_matches.append(match.groupdict())

        return ast_matches

    def _validate_ast_constraints(self, match, constraints) -> bool:
        """Validate match respects AST structure (balanced parens, etc.)."""
        # Check balanced delimiters
        for hole_name, hole_value in match.groupdict().items():
            if not self._is_balanced(hole_value):
                return False
        return True

    def _is_balanced(self, text: str) -> bool:
        """Check if delimiters are balanced."""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}

        for char in text:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack or pairs[stack.pop()] != char:
                    return False

        return len(stack) == 0
```

**Pros**:
- ✅ Full control over implementation
- ✅ Can optimize for Python
- ✅ No external dependencies (Comby)
- ✅ Can integrate with existing AST tools

**Cons**:
- ❌ Significant implementation effort
- ❌ Must maintain our own implementation
- ❌ May miss edge cases Comby handles

---

## Part 5: Alternative Tools Analysis

### Alternative 1: ast-grep 🌟 **RECOMMENDED**

**What is ast-grep?**
- Rust-based structural search and replace tool
- Uses tree-sitter for real parsing (not lightweight like Comby)
- Supports 20+ languages including **Python**
- Blazing fast (parallel Rust implementation)

**Key Advantages over Comby**:
- ✅ **Better Python support** (tree-sitter parser)
- ✅ **AST-aware** (understands syntax and semantics)
- ✅ **Library API** (Python and Node.js bindings)
- ✅ **Fast** (Rust + parallel processing)
- ✅ **Easy install**: `pip install ast-grep-cli`

**Example Usage**:
```bash
# Search
ast-grep -p '$A && $A()' -r '$A?.()'

# Python API
from ast_grep_py import SgRoot

root = SgRoot("your_code.py", "python")
node = root.root()
matches = node.find_all(pattern="isinstance($VAR, $TYPE)")
```

**Pattern Syntax**:
```
$VAR         # Match any variable
$FUNC()      # Match function call
$A && $A     # Match repeated pattern
```

**Comparison with Comby**:

| Feature | Comby | ast-grep |
|---------|-------|----------|
| Python Support | ❌ Limited | ✅ Full (tree-sitter) |
| AST Awareness | ⚠️ Lightweight | ✅ Full AST |
| Library API | ⚠️ OCaml + Python bindings | ✅ Native Python/Node |
| Performance | ✅ Fast | ✅ Faster (Rust + parallel) |
| Installation | Homebrew/Docker | `pip install` |
| Language Support | ~Every language | 20+ languages |

**Verdict**: **ast-grep is superior for lift-sys** due to better Python support and library API.

### Alternative 2: Semgrep

**What is Semgrep?**
- Security-focused static analysis tool
- AST-based pattern matching
- Large collection of security rules

**Key Features**:
- ✅ Excellent Python support
- ✅ AST-based autofix (96.4% success rate)
- ✅ Advanced features (deep-semgrep, equivalence)
- ✅ Large rule database

**Limitations**:
- ❌ Security-focused (may be overkill)
- ❌ Slower than ast-grep for code transformation
- ❌ No library API (CLI only)
- ❌ Heavier tool (more complex)

**Use Cases**:
- Security analysis of generated code
- Finding vulnerabilities in IR transformations
- Compliance checking

**Verdict**: **Useful for security analysis**, but **ast-grep better for transformation**.

### Alternative 3: GritQL

**What is GritQL?**
- Embedded query language for code transformation
- Logic programming features (clauses, operations)
- More powerful than Comby

**Features**:
- ✅ Powerful query language
- ✅ Logic programming constructs
- ✅ Imperative operations

**Limitations**:
- ❌ Newer, less mature
- ❌ Steeper learning curve
- ❌ Limited Python bindings

**Verdict**: **Interesting but premature** for lift-sys.

---

## Part 6: Recommendations

### Primary Recommendation: ast-grep

**Use ast-grep for lift-sys integration** because:

1. **Better Python Support**
   - Tree-sitter parser (full AST)
   - Handles indentation-sensitive syntax
   - Understands Python semantics

2. **Library API**
   - Native Python bindings
   - jQuery-like tree traversal
   - Easy integration

3. **Performance**
   - Rust-based (parallel processing)
   - Faster than Comby
   - Scales to large codebases

4. **Easy Integration**
   - `pip install ast-grep-cli`
   - No OCaml dependencies
   - Good documentation

### Recommended Use Cases (Priority Order)

**1. Code Repair (High Priority)**
- Enhance `ast_repair.py` with pattern-based fixes
- Declare repair rules in YAML/JSON
- More maintainable than AST transformations

**2. Generated Code Validation (High Priority)**
- Validate code matches expected patterns
- Catch semantic errors early
- Complement assertion checking

**3. Reverse Mode (Medium Priority)**
- Extract IR from existing code
- Build IR corpus for training
- Enable bidirectional translation

**4. Constraint Mining (Medium Priority)**
- Learn patterns from codebases
- Build reusable constraint library
- Improve IR generation

**5. Template-Based Generation (Low Priority)**
- Deterministic generation for simple cases
- Reduce LLM costs
- Guaranteed correctness

### Integration Strategy

**Phase 1: Proof of Concept (1-2 weeks)**
1. Install ast-grep: `pip install ast-grep-cli`
2. Create pattern library for common repairs
3. Integrate with `ast_repair.py`
4. Benchmark against current approach

**Phase 2: Pattern-Based Validation (2-3 weeks)**
1. Define validation patterns for generated code
2. Integrate with `CodeValidator`
3. Add pattern-based checks to pipeline
4. Measure improvement in code quality

**Phase 3: Reverse Mode (3-4 weeks)**
1. Define extraction patterns for IR
2. Build code-to-IR translator
3. Test on benchmark codebases
4. Integrate with IR generation pipeline

**Phase 4: Constraint Mining (Ongoing)**
1. Mine patterns from successful generations
2. Build constraint library
3. Use constraints to improve IR quality
4. Continuously expand pattern library

### Why Not Comby?

**Comby limitations for lift-sys**:
- ❌ Weak Python support (no indentation awareness)
- ❌ OCaml dependency (harder to integrate)
- ❌ Less AST-aware than ast-grep
- ❌ Python bindings less mature

**However, Comby concepts are valuable**:
- ✅ Hole-based pattern syntax
- ✅ Rewrite rules language
- ✅ Declarative transformations

**Solution**: Use **ast-grep** (better tool) with **Comby-inspired patterns** (better API).

---

## Part 7: Implementation Sketch

### Pattern-Based Code Repair with ast-grep

**File**: `lift_sys/codegen/pattern_repair.py`

```python
"""Pattern-based code repair using ast-grep."""

from __future__ import annotations

import subprocess
import json
from dataclasses import dataclass
from typing import Any

try:
    from ast_grep_py import SgRoot
    AST_GREP_AVAILABLE = True
except ImportError:
    AST_GREP_AVAILABLE = False


@dataclass
class RepairPattern:
    """Pattern-based repair rule."""

    name: str
    pattern: str           # ast-grep pattern to match
    rewrite: str          # Rewrite template
    condition: str | None = None  # Optional condition
    priority: int = 0     # Higher priority = applied first


class PatternBasedRepair:
    """Repair code using ast-grep patterns."""

    # Standard repair patterns
    PATTERNS = [
        RepairPattern(
            name="fix_computed_types",
            pattern="return type($VAR).__name__",
            rewrite="return 'other'",
            priority=10
        ),
        RepairPattern(
            name="fix_bool_int_order",
            pattern="isinstance($VAR, int) or isinstance($VAR, bool)",
            rewrite="isinstance($VAR, bool) or isinstance($VAR, int)",
            priority=5
        ),
        RepairPattern(
            name="add_missing_return",
            pattern="""
if $COND:
    $THEN
else:
    $ELSE
""",
            rewrite="""
if $COND:
    $THEN
else:
    $ELSE
    return None
""",
            condition="not has_return($ELSE)",
            priority=3
        )
    ]

    def __init__(self, use_library: bool = True):
        """Initialize repair engine."""
        self.use_library = use_library and AST_GREP_AVAILABLE

    def repair(self, code: str, function_name: str) -> str | None:
        """Apply pattern-based repairs to code."""

        # Sort patterns by priority
        patterns = sorted(self.PATTERNS, key=lambda p: p.priority, reverse=True)

        repaired = code
        repairs_applied = []

        for pattern in patterns:
            # Check condition if specified
            if pattern.condition and not self._check_condition(pattern.condition, repaired):
                continue

            # Apply repair
            result = self._apply_pattern(pattern, repaired)

            if result and result != repaired:
                repairs_applied.append(pattern.name)
                repaired = result

        if repairs_applied:
            print(f"  🔧 Applied pattern repairs: {', '.join(repairs_applied)}")
            return repaired

        return None

    def _apply_pattern(self, pattern: RepairPattern, code: str) -> str | None:
        """Apply single pattern using ast-grep."""

        if self.use_library:
            # Use Python library
            return self._apply_with_library(pattern, code)
        else:
            # Use CLI
            return self._apply_with_cli(pattern, code)

    def _apply_with_library(self, pattern: RepairPattern, code: str) -> str | None:
        """Apply pattern using ast-grep Python library."""
        try:
            root = SgRoot(code, "python")

            # Find matches
            matches = root.root().find_all(pattern=pattern.pattern)

            if not matches:
                return None

            # Apply rewrites
            result = code
            for match in reversed(matches):  # Reverse to preserve positions
                # Replace match with rewrite
                start = match.range().start
                end = match.range().end

                # Substitute variables in rewrite
                rewrite_text = pattern.rewrite
                for var, value in match.get_match().items():
                    rewrite_text = rewrite_text.replace(f"${var}", value.text())

                result = result[:start] + rewrite_text + result[end:]

            return result

        except Exception as e:
            print(f"  ⚠️ Pattern repair failed: {e}")
            return None

    def _apply_with_cli(self, pattern: RepairPattern, code: str) -> str | None:
        """Apply pattern using ast-grep CLI."""
        try:
            result = subprocess.run(
                [
                    "ast-grep",
                    "-p", pattern.pattern,
                    "-r", pattern.rewrite,
                    "--stdin",
                    "-l", "python"
                ],
                input=code,
                capture_output=True,
                text=True,
                check=True
            )

            if result.stdout and result.stdout != code:
                return result.stdout

            return None

        except subprocess.CalledProcessError:
            return None

    def _check_condition(self, condition: str, code: str) -> bool:
        """Check if condition is satisfied."""
        # Simple condition checking
        # Could be enhanced with more sophisticated logic

        if condition.startswith("not has_return"):
            # Extract code to check from condition
            # condition = "not has_return($ELSE)"
            return "return" not in code

        # Add more condition handlers as needed
        return True


__all__ = ["PatternBasedRepair", "RepairPattern"]
```

### Integration with Existing Repair

**File**: `lift_sys/codegen/ast_repair.py` (enhanced)

```python
from .pattern_repair import PatternBasedRepair

class ASTRepairEngine:
    """Enhanced repair with both AST and pattern-based fixes."""

    def __init__(self):
        self.pattern_repair = PatternBasedRepair()

    def repair(self, code: str, function_name: str) -> str | None:
        """Apply both AST and pattern-based repairs."""

        # Try pattern-based repair first (more declarative)
        pattern_result = self.pattern_repair.repair(code, function_name)
        if pattern_result:
            code = pattern_result

        # Then apply AST-based repairs (more complex cases)
        ast_result = self._ast_based_repair(code, function_name)
        if ast_result:
            code = ast_result

        return code if (pattern_result or ast_result) else None
```

---

## Part 8: Conclusion

### Summary

**Comby** introduced valuable concepts (hole-based patterns, rewrite rules) but has limitations for Python-focused work. **ast-grep** is a superior alternative with:

- ✅ Better Python support (tree-sitter)
- ✅ Library API (Python bindings)
- ✅ Faster performance (Rust)
- ✅ Easier integration (`pip install`)

### Recommendations

**1. Use ast-grep, not Comby**
- Better fit for lift-sys
- More maintainable
- Faster and more accurate

**2. Start with Code Repair**
- Immediate value (enhance `ast_repair.py`)
- Clear use case
- Easy to measure success

**3. Expand to Validation**
- Pattern-based checks
- Complement existing validation
- Catch semantic errors

**4. Consider Reverse Mode**
- Extract IR from code
- Build training corpus
- Enable bidirectional translation

**5. Mine Constraints**
- Learn from successful code
- Build pattern library
- Improve generation quality

### Next Steps

1. **Proof of Concept** (This Week)
   - Install ast-grep: `pip install ast-grep-cli`
   - Create 3-5 repair patterns
   - Test on Phase 3 failures

2. **Integration** (Week 2)
   - Integrate with `ast_repair.py`
   - Add pattern-based validation
   - Measure improvement

3. **Expansion** (Week 3+)
   - Add more patterns
   - Build reverse mode
   - Mine constraints from repos

### Key Takeaway

**Comby's concepts (hole-based patterns, rewrite rules) are valuable for lift-sys, but ast-grep is the better tool for implementation.** Use ast-grep with Comby-inspired pattern syntax to enhance code repair, validation, and potentially enable reverse mode (code-to-IR extraction).

---

**Evaluation Complete**: October 16, 2025
**Recommendation**: Integrate ast-grep for pattern-based code repair and validation
**Priority**: High (complements existing constraint propagation work)
