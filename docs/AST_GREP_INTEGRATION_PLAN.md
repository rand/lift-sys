# ast-grep Integration: Implementation Plan

**Date**: October 16, 2025
**Status**: 📋 **READY TO START**
**Priority**: High (complements constraint propagation)
**Timeline**: 4-6 weeks (phased approach)

---

## Executive Summary

This plan details the integration of **ast-grep** into lift-sys for pattern-based code repair, validation, and reverse mode (code-to-IR extraction). ast-grep provides structural pattern matching using tree-sitter parsers with full Python support.

**Vision**: Enhance lift-sys code generation pipeline with declarative pattern-based transformations and validation.

**Approach**: Three-phase implementation focusing on high-value use cases first:
1. **Phase 1**: Pattern-Based Code Repair (2 weeks)
2. **Phase 2**: Pattern-Based Validation (2 weeks)
3. **Phase 3**: Reverse Mode Foundation (2 weeks)

**Success Metrics**:
- >95% code repair success rate (vs 90% current)
- >98% validation accuracy
- Reduce false positives in validation by 50%
- Extract IR from 80%+ of benchmark functions

---

## Part 1: Context and Motivation

### Current Challenges

**1. Code Repair Limitations**
- Current `ast_repair.py` uses hardcoded AST transformations
- Difficult to maintain and extend
- No declarative way to specify repairs
- Limited pattern coverage

**2. Validation Gaps**
- Assertion checking catches runtime errors
- AST validation catches syntax errors
- Missing: **semantic pattern validation**
- Can't easily check "code should follow pattern X"

**3. No Reverse Mode**
- Can't extract IR from existing code
- No systematic way to learn from codebases
- Missing bidirectional translation

### Why ast-grep?

**Better than Comby for lift-sys**:
- ✅ Full Python support (tree-sitter parser)
- ✅ Understands indentation-sensitive syntax
- ✅ Native Python library API
- ✅ Faster (Rust + parallel processing)
- ✅ Easy install (`pip install ast-grep-cli`)

**Better than manual AST manipulation**:
- ✅ Declarative pattern syntax
- ✅ Easier to maintain
- ✅ More expressive
- ✅ Can compose patterns

### High-Value Use Cases

**Priority 1: Pattern-Based Code Repair**
- Replace hardcoded AST fixes with declarative patterns
- Easier to add new repair rules
- More maintainable
- **Impact**: Improve repair success rate 90% → 95%+

**Priority 2: Pattern-Based Validation**
- Validate generated code matches expected patterns
- Catch semantic errors early
- Reduce false positives
- **Impact**: Improve validation accuracy, reduce retries

**Priority 3: Reverse Mode (Foundation)**
- Extract IR from Python code
- Build IR corpus from existing codebases
- Enable learning from real code
- **Impact**: Improve IR quality through constraint mining

---

## Part 2: Phase 1 - Pattern-Based Code Repair

**Timeline**: 2 weeks
**Goal**: Enhance `ast_repair.py` with declarative pattern-based repairs

### 2.1 Infrastructure Setup (Days 1-2)

**Tasks**:

1. **Install ast-grep**
```bash
uv add ast-grep-cli
uv add ast-grep-py  # Python bindings
```

2. **Create module structure**
```
lift_sys/
  repair/
    __init__.py
    pattern_repair.py      # Pattern-based repair engine
    patterns/
      __init__.py
      common.py            # Common repair patterns
      type_checking.py     # Type-checking specific patterns
      control_flow.py      # Control flow patterns
```

3. **Set up pattern library format**
```yaml
# Example pattern file: patterns/type_checking.yaml
patterns:
  - name: fix_computed_types
    description: Replace type(x).__name__ with literal 'other'
    pattern: return type($VAR).__name__
    rewrite: return 'other'
    priority: 10
    applies_to:
      - "get_type_name"
      - "check_type"

  - name: fix_bool_int_order
    description: Check isinstance(bool) before isinstance(int)
    pattern: isinstance($VAR, int) or isinstance($VAR, bool)
    rewrite: isinstance($VAR, bool) or isinstance($VAR, int)
    priority: 5
```

**Deliverable**: Infrastructure ready, ast-grep installed and tested

### 2.2 Core Pattern Repair Engine (Days 3-5)

**File**: `lift_sys/repair/pattern_repair.py`

**Implementation**:

```python
"""Pattern-based code repair using ast-grep."""

from __future__ import annotations

import subprocess
import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
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
    description: str
    pattern: str
    rewrite: str
    priority: int = 0
    applies_to: list[str] = field(default_factory=list)
    condition: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> RepairPattern:
        """Load pattern from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            pattern=data["pattern"],
            rewrite=data["rewrite"],
            priority=data.get("priority", 0),
            applies_to=data.get("applies_to", []),
            condition=data.get("condition"),
            metadata=data.get("metadata", {})
        )


class PatternLibrary:
    """Manages collection of repair patterns."""

    def __init__(self):
        self.patterns: list[RepairPattern] = []
        self._load_builtin_patterns()

    def _load_builtin_patterns(self):
        """Load built-in patterns from YAML files."""
        patterns_dir = Path(__file__).parent / "patterns"

        if not patterns_dir.exists():
            return

        for yaml_file in patterns_dir.glob("*.yaml"):
            self.load_from_file(yaml_file)

    def load_from_file(self, path: Path):
        """Load patterns from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        for pattern_data in data.get("patterns", []):
            pattern = RepairPattern.from_dict(pattern_data)
            self.patterns.append(pattern)

    def get_applicable_patterns(
        self,
        function_name: str | None = None
    ) -> list[RepairPattern]:
        """Get patterns applicable to given function."""
        if function_name is None:
            return self.patterns

        applicable = []
        for pattern in self.patterns:
            if not pattern.applies_to:
                # No restrictions, applies to all
                applicable.append(pattern)
            elif any(fn in function_name for fn in pattern.applies_to):
                # Function name matches
                applicable.append(pattern)

        # Sort by priority (higher first)
        return sorted(applicable, key=lambda p: p.priority, reverse=True)


class PatternRepairEngine:
    """Apply pattern-based repairs using ast-grep."""

    def __init__(self, use_library: bool = True):
        """Initialize repair engine."""
        self.use_library = use_library and AST_GREP_AVAILABLE
        self.library = PatternLibrary()
        self.stats = {
            "total_repairs": 0,
            "patterns_applied": {},
            "failures": []
        }

    def repair(
        self,
        code: str,
        function_name: str | None = None
    ) -> tuple[str | None, list[str]]:
        """
        Apply pattern-based repairs to code.

        Returns:
            (repaired_code, repairs_applied)
        """
        patterns = self.library.get_applicable_patterns(function_name)

        if not patterns:
            return None, []

        repaired = code
        repairs_applied = []

        for pattern in patterns:
            # Check condition if specified
            if pattern.condition and not self._check_condition(
                pattern.condition, repaired, function_name
            ):
                continue

            # Apply repair
            result = self._apply_pattern(pattern, repaired)

            if result and result != repaired:
                repairs_applied.append(pattern.name)
                repaired = result

                # Update stats
                self.stats["total_repairs"] += 1
                self.stats["patterns_applied"][pattern.name] = (
                    self.stats["patterns_applied"].get(pattern.name, 0) + 1
                )

        return (repaired, repairs_applied) if repairs_applied else (None, [])

    def _apply_pattern(
        self,
        pattern: RepairPattern,
        code: str
    ) -> str | None:
        """Apply single pattern."""
        if self.use_library:
            return self._apply_with_library(pattern, code)
        else:
            return self._apply_with_cli(pattern, code)

    def _apply_with_library(
        self,
        pattern: RepairPattern,
        code: str
    ) -> str | None:
        """Apply pattern using ast-grep Python library."""
        try:
            root = SgRoot(code, "python")
            node = root.root()

            # Find all matches
            matches = node.find_all(pattern=pattern.pattern)

            if not matches:
                return None

            # Apply rewrites (reverse order to preserve positions)
            result = code
            for match in reversed(list(matches)):
                # Get match range
                start = match.range().start.0
                end = match.range().end.0

                # Build rewrite by substituting variables
                rewrite_text = pattern.rewrite
                env = match.get_env()

                for var_name in env.keys():
                    var_node = env.get(var_name)
                    if var_node:
                        var_text = var_node.text()
                        rewrite_text = rewrite_text.replace(f"${var_name}", var_text)

                # Apply rewrite
                result = result[:start] + rewrite_text + result[end:]

            return result

        except Exception as e:
            self.stats["failures"].append({
                "pattern": pattern.name,
                "error": str(e)
            })
            return None

    def _apply_with_cli(
        self,
        pattern: RepairPattern,
        code: str
    ) -> str | None:
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
                check=True,
                timeout=5
            )

            if result.stdout and result.stdout != code:
                return result.stdout

            return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.stats["failures"].append({
                "pattern": pattern.name,
                "error": str(e)
            })
            return None

    def _check_condition(
        self,
        condition: str,
        code: str,
        function_name: str | None
    ) -> bool:
        """Check if condition is satisfied."""
        # Simple condition evaluation
        # Can be extended with more sophisticated logic

        if condition.startswith("has_return"):
            return "return" in code

        if condition.startswith("not has_return"):
            return "return" not in code

        if condition.startswith("function_contains"):
            # Extract substring from condition
            # e.g., "function_contains('isinstance')"
            substring = condition.split("'")[1]
            return substring in code

        return True

    def get_statistics(self) -> dict:
        """Get repair statistics."""
        return self.stats.copy()


__all__ = ["PatternRepairEngine", "RepairPattern", "PatternLibrary"]
```

**Tasks**:
- [ ] Implement `PatternRepairEngine` class
- [ ] Add library-based pattern application (ast-grep-py)
- [ ] Add CLI-based fallback
- [ ] Implement condition checking
- [ ] Add statistics tracking
- [ ] Unit tests for pattern application

**Deliverable**: Working pattern repair engine

### 2.3 Built-in Repair Patterns (Days 6-8)

**File**: `lift_sys/repair/patterns/type_checking.yaml`

```yaml
patterns:
  - name: fix_computed_types_typename
    description: Replace type(x).__name__ with literal 'other'
    pattern: return type($VAR).__name__
    rewrite: return 'other'
    priority: 10
    applies_to:
      - "get_type"
      - "check_type"
      - "type_name"

  - name: fix_computed_types_str
    description: Replace str(type(x)) with literal 'other'
    pattern: return str(type($VAR))
    rewrite: return 'other'
    priority: 10
    applies_to:
      - "get_type"
      - "check_type"

  - name: fix_bool_int_order_or
    description: Check isinstance(bool) before isinstance(int) in or chains
    pattern: isinstance($VAR, int) or isinstance($VAR, bool)
    rewrite: isinstance($VAR, bool) or isinstance($VAR, int)
    priority: 8

  - name: fix_bool_int_order_if
    description: Check isinstance(bool) before isinstance(int) in if/elif
    pattern: |
      if isinstance($VAR, int):
          $THEN
      elif isinstance($VAR, bool):
          $ELSE
    rewrite: |
      if isinstance($VAR, bool):
          $ELSE
      elif isinstance($VAR, int):
          $THEN
    priority: 8

  - name: fix_missing_else_return
    description: Add return None to else branches without return
    pattern: |
      if $COND:
          return $VAL1
      else:
          $BODY
    rewrite: |
      if $COND:
          return $VAL1
      else:
          $BODY
          return None
    priority: 5
    condition: "not has_return($BODY)"
```

**File**: `lift_sys/repair/patterns/common.yaml`

```yaml
patterns:
  - name: fix_undefined_variable
    description: Replace undefined variables with None
    pattern: return $VAR
    rewrite: return None
    priority: 3
    condition: "$VAR not in defined_variables"

  - name: fix_double_return
    description: Remove duplicate return statements
    pattern: |
      return $VAL
      return $VAL
    rewrite: return $VAL
    priority: 4

  - name: fix_unreachable_code
    description: Remove code after return
    pattern: |
      return $VAL
      $UNREACHABLE
    rewrite: return $VAL
    priority: 2
```

**Tasks**:
- [ ] Create type_checking.yaml with 5-8 patterns
- [ ] Create common.yaml with 3-5 patterns
- [ ] Test patterns on Phase 3 failures
- [ ] Validate pattern correctness
- [ ] Document pattern library

**Deliverable**: Comprehensive pattern library

### 2.4 Integration with Existing Repair (Days 9-10)

**File**: `lift_sys/codegen/ast_repair.py` (enhanced)

```python
from lift_sys.repair.pattern_repair import PatternRepairEngine

class ASTRepairEngine:
    """Enhanced repair with pattern-based and AST-based fixes."""

    def __init__(self):
        # Phase 1: Pattern-based repair (declarative)
        self.pattern_engine = PatternRepairEngine()

        # Phase 2: AST-based repair (complex cases)
        self._initialize_ast_repair()

    def repair(self, code: str, function_name: str) -> str | None:
        """
        Apply repairs in order:
        1. Pattern-based (fast, declarative)
        2. AST-based (complex transformations)

        Returns repaired code or None if no repairs needed.
        """
        original = code

        # Phase 1: Pattern-based repair
        pattern_result, repairs_applied = self.pattern_engine.repair(
            code, function_name
        )

        if pattern_result:
            code = pattern_result
            print(f"  🔧 Pattern repairs: {', '.join(repairs_applied)}")

        # Phase 2: AST-based repair (existing logic)
        ast_result = self._ast_based_repair(code, function_name)

        if ast_result:
            code = ast_result
            print(f"  🔧 AST repairs applied")

        return code if code != original else None

    def _ast_based_repair(self, code: str, function_name: str) -> str | None:
        """Existing AST-based repair logic."""
        # ... existing implementation ...
        pass
```

**Tasks**:
- [ ] Integrate `PatternRepairEngine` with `ASTRepairEngine`
- [ ] Add logging for pattern repairs
- [ ] Update repair pipeline to use patterns first
- [ ] Maintain backward compatibility
- [ ] Integration tests

**Deliverable**: Integrated pattern-based repair in pipeline

### 2.5 Testing and Validation (Days 11-14)

**Tests to Create**:

1. **Unit Tests**: `tests/unit/test_pattern_repair.py`
```python
def test_fix_computed_types():
    """Test pattern fixes type(x).__name__."""
    code = "return type(value).__name__"
    engine = PatternRepairEngine()
    result, repairs = engine.repair(code, "get_type_name")

    assert result == "return 'other'"
    assert "fix_computed_types_typename" in repairs

def test_fix_bool_int_order():
    """Test pattern fixes isinstance order."""
    code = "isinstance(x, int) or isinstance(x, bool)"
    engine = PatternRepairEngine()
    result, repairs = engine.repair(code, "check_type")

    assert "isinstance(x, bool)" in result
    assert result.index("bool") < result.index("int")
```

2. **Integration Tests**: `tests/integration/test_pattern_repair_integration.py`
```python
async def test_pattern_repair_on_phase3_failures():
    """Test pattern repair on actual Phase 3 failures."""
    # Load Phase 3 test cases that failed
    failures = load_phase3_failures()

    successes = 0
    for test_case in failures:
        ir = test_case.ir
        generator = XGrammarCodeGenerator(provider)

        code = await generator.generate(ir)

        if test_case.validate(code):
            successes += 1

    # Should improve success rate from 90% to 95%+
    assert successes / len(failures) >= 0.95
```

3. **Pattern Library Tests**: `tests/unit/test_pattern_library.py`
```python
def test_load_patterns_from_yaml():
    """Test loading patterns from YAML files."""
    library = PatternLibrary()

    assert len(library.patterns) > 0
    assert any(p.name == "fix_computed_types_typename" for p in library.patterns)

def test_pattern_priority_ordering():
    """Test patterns are sorted by priority."""
    library = PatternLibrary()
    patterns = library.get_applicable_patterns("get_type_name")

    priorities = [p.priority for p in patterns]
    assert priorities == sorted(priorities, reverse=True)
```

**Benchmarking**:

```python
def benchmark_pattern_repair():
    """Benchmark pattern repair vs AST repair."""
    test_cases = load_repair_test_cases()

    # Pattern-based repair
    pattern_engine = PatternRepairEngine()
    pattern_times = []
    for code in test_cases:
        start = time.time()
        pattern_engine.repair(code, "test_function")
        pattern_times.append(time.time() - start)

    # AST-based repair
    ast_engine = ASTRepairEngine()
    ast_times = []
    for code in test_cases:
        start = time.time()
        ast_engine._ast_based_repair(code, "test_function")
        ast_times.append(time.time() - start)

    print(f"Pattern repair avg: {sum(pattern_times)/len(pattern_times):.4f}s")
    print(f"AST repair avg: {sum(ast_times)/len(ast_times):.4f}s")
```

**Tasks**:
- [ ] Write 15+ unit tests
- [ ] Write 5+ integration tests
- [ ] Test on Phase 3 failures
- [ ] Benchmark performance
- [ ] Measure success rate improvement
- [ ] Document results

**Success Metrics**:
- >95% test coverage for pattern_repair.py
- >95% success rate on Phase 3 failures (vs 90% baseline)
- Pattern repair faster than AST repair
- Zero regressions on existing tests

**Deliverable**: Fully tested pattern-based repair system

---

## Part 3: Phase 2 - Pattern-Based Validation

**Timeline**: 2 weeks
**Goal**: Add pattern-based validation to catch semantic errors early

### 3.1 Pattern Validator Infrastructure (Days 1-3)

**File**: `lift_sys/validation/pattern_validator.py`

```python
"""Pattern-based validation using ast-grep."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml

try:
    from ast_grep_py import SgRoot
    AST_GREP_AVAILABLE = True
except ImportError:
    AST_GREP_AVAILABLE = False


@dataclass
class ValidationPattern:
    """Pattern for code validation."""

    name: str
    description: str
    pattern: str
    violation: bool = False  # True if pattern should NOT match
    severity: str = "error"  # error, warning, info
    message: str | None = None
    applies_to: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> ValidationPattern:
        """Load pattern from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            pattern=data["pattern"],
            violation=data.get("violation", False),
            severity=data.get("severity", "error"),
            message=data.get("message"),
            applies_to=data.get("applies_to", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class ValidationIssue:
    """Validation issue found by pattern."""

    pattern_name: str
    severity: str
    message: str
    location: tuple[int, int] | None = None  # (line, column)
    matched_text: str | None = None


@dataclass
class ValidationResult:
    """Result of pattern validation."""

    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def has_errors(self) -> bool:
        """Check if result has errors."""
        return any(i.severity == "error" for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if result has warnings."""
        return any(i.severity == "warning" for i in self.issues)


class PatternValidator:
    """Validate code using ast-grep patterns."""

    def __init__(self):
        self.patterns: list[ValidationPattern] = []
        self._load_builtin_patterns()

    def _load_builtin_patterns(self):
        """Load built-in validation patterns."""
        patterns_dir = Path(__file__).parent / "validation_patterns"

        if not patterns_dir.exists():
            return

        for yaml_file in patterns_dir.glob("*.yaml"):
            self.load_from_file(yaml_file)

    def load_from_file(self, path: Path):
        """Load patterns from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        for pattern_data in data.get("patterns", []):
            pattern = ValidationPattern.from_dict(pattern_data)
            self.patterns.append(pattern)

    def validate(
        self,
        code: str,
        function_name: str | None = None
    ) -> ValidationResult:
        """Validate code against patterns."""
        applicable_patterns = self._get_applicable_patterns(function_name)

        issues = []

        for pattern in applicable_patterns:
            pattern_issues = self._check_pattern(code, pattern)
            issues.extend(pattern_issues)

        # Result passes if no errors
        passed = not any(i.severity == "error" for i in issues)

        return ValidationResult(passed=passed, issues=issues)

    def _get_applicable_patterns(
        self,
        function_name: str | None
    ) -> list[ValidationPattern]:
        """Get patterns applicable to function."""
        if function_name is None:
            return self.patterns

        applicable = []
        for pattern in self.patterns:
            if not pattern.applies_to:
                applicable.append(pattern)
            elif any(fn in function_name for fn in pattern.applies_to):
                applicable.append(pattern)

        return applicable

    def _check_pattern(
        self,
        code: str,
        pattern: ValidationPattern
    ) -> list[ValidationIssue]:
        """Check single pattern against code."""
        if not AST_GREP_AVAILABLE:
            return []

        try:
            root = SgRoot(code, "python")
            node = root.root()
            matches = list(node.find_all(pattern=pattern.pattern))

            # Violation pattern: should NOT match
            if pattern.violation:
                if matches:
                    # Found matches for violation pattern - this is bad
                    issues = []
                    for match in matches:
                        message = pattern.message or f"Violation: {pattern.description}"
                        issues.append(ValidationIssue(
                            pattern_name=pattern.name,
                            severity=pattern.severity,
                            message=message,
                            matched_text=match.text()
                        ))
                    return issues
                else:
                    # No matches for violation pattern - good
                    return []

            # Required pattern: SHOULD match
            else:
                if not matches:
                    # Should match but didn't - this is bad
                    message = pattern.message or f"Missing: {pattern.description}"
                    return [ValidationIssue(
                        pattern_name=pattern.name,
                        severity=pattern.severity,
                        message=message
                    )]
                else:
                    # Matches as expected - good
                    return []

        except Exception as e:
            # Pattern check failed
            return [ValidationIssue(
                pattern_name=pattern.name,
                severity="warning",
                message=f"Pattern check failed: {e}"
            )]


__all__ = ["PatternValidator", "ValidationPattern", "ValidationResult", "ValidationIssue"]
```

**Tasks**:
- [ ] Implement `PatternValidator` class
- [ ] Support violation patterns (should NOT match)
- [ ] Support required patterns (SHOULD match)
- [ ] Add severity levels (error, warning, info)
- [ ] Unit tests for validator

**Deliverable**: Pattern validator infrastructure

### 3.2 Validation Pattern Library (Days 4-6)

**File**: `lift_sys/validation/validation_patterns/type_checking.yaml`

```yaml
patterns:
  # Violation patterns (should NOT match)
  - name: no_computed_types_typename
    description: Type checkers must not compute types dynamically
    pattern: type($VAR).__name__
    violation: true
    severity: error
    message: "Must not use type(x).__name__ - use literal strings instead"
    applies_to:
      - "get_type"
      - "check_type"
      - "type_name"

  - name: no_computed_types_str
    description: Type checkers must not use str(type(x))
    pattern: str(type($VAR))
    violation: true
    severity: error
    message: "Must not use str(type(x)) - use literal strings instead"
    applies_to:
      - "get_type"
      - "check_type"

  - name: no_class_attribute
    description: Must not use __class__ attribute
    pattern: $VAR.__class__
    violation: true
    severity: error
    message: "Must not use __class__ attribute"

  # Required patterns (SHOULD match)
  - name: has_literal_return_strings
    description: Type checkers should return literal strings
    pattern: return '$STRING'
    violation: false
    severity: warning
    message: "Type checker should return literal strings"
    applies_to:
      - "get_type"
      - "check_type"

  - name: proper_bool_int_order
    description: Check isinstance(bool) before isinstance(int)
    pattern: |
      if isinstance($VAR, bool):
          $THEN
      elif isinstance($VAR, int):
          $ELSE
    violation: false
    severity: warning
    message: "Good: bool checked before int (Python quirk)"
```

**File**: `lift_sys/validation/validation_patterns/general.yaml`

```yaml
patterns:
  - name: no_undefined_variables
    description: All variables should be defined
    pattern: return $UNDEFINED
    violation: true
    severity: error
    message: "Variable may be undefined"
    # This is a simple check, would need more sophisticated analysis

  - name: all_branches_return
    description: All branches in if/else should have returns
    pattern: |
      if $COND:
          return $VAL1
      else:
          $BODY
    violation: false
    severity: warning
    message: "Else branch should have explicit return"

  - name: no_unreachable_code
    description: No code after return statements
    pattern: |
      return $VAL
      $UNREACHABLE
    violation: true
    severity: warning
    message: "Unreachable code after return"

  - name: consistent_return_types
    description: Function should have consistent return types
    pattern: |
      def $FUNC($PARAMS):
          $BODY
    # Would need custom logic to check return type consistency
    violation: false
    severity: info
```

**Tasks**:
- [ ] Create type_checking.yaml with 8-10 validation patterns
- [ ] Create general.yaml with 5-7 validation patterns
- [ ] Test patterns on generated code
- [ ] Validate pattern accuracy
- [ ] Document pattern semantics

**Deliverable**: Comprehensive validation pattern library

### 3.3 Integration with Code Generation (Days 7-9)

**File**: `lift_sys/codegen/xgrammar_generator.py` (enhanced)

```python
from lift_sys.validation.pattern_validator import PatternValidator

class XGrammarCodeGenerator:
    """Enhanced with pattern-based validation."""

    def __init__(self, provider: BaseProvider, config: CodeGeneratorConfig | None = None):
        # ... existing initialization ...
        self.pattern_validator = PatternValidator()  # Add pattern validator

    async def generate(
        self,
        ir: IntermediateRepresentation,
        max_retries: int = 5,
        use_multishot: bool = False,
        test_cases: list | None = None,
        temperature: float = 0.3,
    ) -> GeneratedCode:
        """Generate with pattern validation."""

        # ... existing code generation ...

        for attempt in range(max_retries):
            # ... generate code ...

            # Phase 4.5: Pattern-based validation (before AST repair)
            pattern_result = self.pattern_validator.validate(
                complete_code,
                function_name=ir.signature.name
            )

            if pattern_result.has_errors():
                if attempt < max_retries - 1:
                    print(f"  ⚠️ Pattern validation failed: {len(pattern_result.issues)} issue(s)")

                    # Show first 3 errors
                    for issue in [i for i in pattern_result.issues if i.severity == "error"][:3]:
                        print(f"    - {issue.message}")
                        if issue.matched_text:
                            print(f"      Matched: {issue.matched_text}")

                    # Build feedback for retry
                    feedback_parts = ["\n\nPattern validation failures:"]
                    for issue in pattern_result.issues[:5]:
                        feedback_parts.append(f"- {issue.message}")

                    self._validation_feedback = "\n".join(feedback_parts)
                    continue  # Retry

            # Pattern validation passed or only warnings
            if pattern_result.has_warnings():
                print(f"  ⚠️ Pattern validation warnings: {len([i for i in pattern_result.issues if i.severity == 'warning'])} warning(s)")

            # Continue with existing validation pipeline
            # (AST repair, assertion checking, etc.)
            ...
```

**Tasks**:
- [ ] Integrate `PatternValidator` into generation pipeline
- [ ] Add pattern validation before AST repair
- [ ] Provide feedback for pattern violations
- [ ] Track pattern validation metrics
- [ ] Integration tests

**Deliverable**: Pattern validation integrated in pipeline

### 3.4 Testing and Benchmarking (Days 10-14)

**Tests**:

1. **Unit Tests**: `tests/unit/test_pattern_validator.py`
```python
def test_violation_pattern_catches_error():
    """Test violation pattern correctly identifies errors."""
    code = "return type(value).__name__"
    validator = PatternValidator()
    result = validator.validate(code, "get_type_name")

    assert not result.passed
    assert result.has_errors()
    assert any("computed types" in i.message.lower() for i in result.issues)

def test_required_pattern_validates():
    """Test required pattern validation."""
    code = """
if isinstance(x, bool):
    return 'other'
elif isinstance(x, int):
    return 'int'
"""
    validator = PatternValidator()
    result = validator.validate(code, "get_type_name")

    # Should pass (bool checked before int)
    assert result.passed or not result.has_errors()
```

2. **Integration Tests**: `tests/integration/test_pattern_validation.py`
```python
async def test_pattern_validation_reduces_retries():
    """Test pattern validation catches errors early."""
    # Test cases that previously failed validation
    test_cases = load_problematic_test_cases()

    retry_counts = []
    for test_case in test_cases:
        generator = XGrammarCodeGenerator(provider)
        code = await generator.generate(test_case.ir, max_retries=5)

        # Track how many retries were needed
        retry_counts.append(generator.stats.get("retries", 0))

    # Pattern validation should reduce average retries
    avg_retries = sum(retry_counts) / len(retry_counts)
    assert avg_retries < 2.0  # Should be less than baseline
```

**Benchmarking**:

```python
def benchmark_validation_accuracy():
    """Measure pattern validation accuracy."""
    # True positives: correctly identified errors
    # False positives: incorrectly flagged valid code
    # True negatives: correctly passed valid code
    # False negatives: missed actual errors

    test_cases = {
        "valid_code": [...],      # Should pass
        "invalid_code": [...],    # Should fail
    }

    validator = PatternValidator()

    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0

    for code in test_cases["valid_code"]:
        result = validator.validate(code)
        if result.passed:
            true_negatives += 1
        else:
            false_positives += 1

    for code in test_cases["invalid_code"]:
        result = validator.validate(code)
        if not result.passed:
            true_positives += 1
        else:
            false_negatives += 1

    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)

    print(f"Precision: {precision:.2%}")
    print(f"Recall: {recall:.2%}")
```

**Tasks**:
- [ ] Write 20+ unit tests
- [ ] Write 10+ integration tests
- [ ] Measure validation accuracy (precision, recall)
- [ ] Benchmark false positive rate
- [ ] Compare with baseline validation
- [ ] Document results

**Success Metrics**:
- >98% validation accuracy
- <5% false positive rate
- Reduce average retries by 30%+
- Zero regressions on existing tests

**Deliverable**: Fully tested pattern validation system

---

## Part 4: Phase 3 - Reverse Mode Foundation

**Timeline**: 2 weeks
**Goal**: Extract IR from Python code using patterns

### 4.1 IR Extraction Patterns (Days 1-4)

**File**: `lift_sys/reverse/extraction_patterns.yaml`

```yaml
patterns:
  # Function signature extraction
  - name: simple_function
    description: Extract simple function signature
    pattern: |
      def $FUNC_NAME($PARAMS) -> $RETURN_TYPE:
          $BODY
    extract:
      signature.name: $FUNC_NAME
      signature.parameters: $PARAMS
      signature.returns: $RETURN_TYPE

  - name: function_with_docstring
    description: Extract function with docstring
    pattern: |
      def $FUNC_NAME($PARAMS) -> $RETURN_TYPE:
          """$DOCSTRING"""
          $BODY
    extract:
      signature.name: $FUNC_NAME
      signature.parameters: $PARAMS
      signature.returns: $RETURN_TYPE
      intent.summary: $DOCSTRING

  # Effect patterns
  - name: simple_return
    description: Extract simple return statement
    pattern: return $EXPR
    extract:
      effects:
        - description: "return $EXPR"

  - name: conditional_return
    description: Extract if/else returns
    pattern: |
      if $COND:
          return $THEN_VAL
      else:
          return $ELSE_VAL
    extract:
      effects:
        - description: "if $COND: return $THEN_VAL"
        - description: "else: return $ELSE_VAL"

  # Assertion patterns
  - name: isinstance_check
    description: Extract isinstance checks as constraints
    pattern: if isinstance($VAR, $TYPE):
    extract:
      assertions:
        - predicate: "isinstance($VAR, $TYPE)"
          rationale: "Type check for $VAR"

  - name: value_comparison
    description: Extract value comparisons
    pattern: if $VAR $OP $VALUE:
    extract:
      assertions:
        - predicate: "$VAR $OP $VALUE"
```

**File**: `lift_sys/reverse/ir_extractor.py`

```python
"""Extract IR from Python code using ast-grep patterns."""

from __future__ import annotations

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from ast_grep_py import SgRoot

from ..ir.models import (
    IntermediateRepresentation,
    IntentClause,
    SigClause,
    Parameter,
    EffectClause,
    AssertClause,
    Metadata
)


@dataclass
class ExtractionPattern:
    """Pattern for IR extraction."""

    name: str
    description: str
    pattern: str
    extract: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict) -> ExtractionPattern:
        return cls(
            name=data["name"],
            description=data["description"],
            pattern=data["pattern"],
            extract=data["extract"]
        )


class IRExtractor:
    """Extract IR from Python code."""

    def __init__(self):
        self.patterns: list[ExtractionPattern] = []
        self._load_patterns()

    def _load_patterns(self):
        """Load extraction patterns."""
        patterns_file = Path(__file__).parent / "extraction_patterns.yaml"

        if patterns_file.exists():
            with open(patterns_file) as f:
                data = yaml.safe_load(f)

            for pattern_data in data.get("patterns", []):
                pattern = ExtractionPattern.from_dict(pattern_data)
                self.patterns.append(pattern)

    def extract(self, code: str) -> IntermediateRepresentation | None:
        """Extract IR from Python code."""

        root = SgRoot(code, "python")
        node = root.root()

        # Extract components
        signature = self._extract_signature(node)
        if not signature:
            return None

        intent = self._extract_intent(node)
        effects = self._extract_effects(node)
        assertions = self._extract_assertions(node)

        return IntermediateRepresentation(
            intent=intent,
            signature=signature,
            effects=effects,
            assertions=assertions,
            metadata=Metadata(
                origin="reverse_mode",
                language="python"
            )
        )

    def _extract_signature(self, node) -> SigClause | None:
        """Extract function signature."""
        # Find function definition
        for pattern in self.patterns:
            if "signature" in pattern.extract:
                matches = node.find_all(pattern=pattern.pattern)

                for match in matches:
                    env = match.get_env()

                    # Extract function name
                    func_name_node = env.get("FUNC_NAME")
                    if not func_name_node:
                        continue

                    func_name = func_name_node.text()

                    # Extract parameters
                    params_node = env.get("PARAMS")
                    parameters = self._parse_parameters(
                        params_node.text() if params_node else ""
                    )

                    # Extract return type
                    return_type_node = env.get("RETURN_TYPE")
                    return_type = return_type_node.text() if return_type_node else None

                    return SigClause(
                        name=func_name,
                        parameters=parameters,
                        returns=return_type
                    )

        return None

    def _extract_intent(self, node) -> IntentClause:
        """Extract function intent from docstring."""
        # Try to find docstring
        for pattern in self.patterns:
            if "intent.summary" in pattern.extract:
                matches = node.find_all(pattern=pattern.pattern)

                for match in matches:
                    env = match.get_env()
                    docstring_node = env.get("DOCSTRING")

                    if docstring_node:
                        return IntentClause(
                            summary=docstring_node.text(),
                            rationale="Extracted from docstring"
                        )

        # Fallback: generic intent
        return IntentClause(
            summary="Function extracted from code",
            rationale="No docstring found"
        )

    def _extract_effects(self, node) -> list[EffectClause]:
        """Extract effects from function body."""
        effects = []

        # Find return statements
        for pattern in self.patterns:
            if "effects" in pattern.extract:
                matches = node.find_all(pattern=pattern.pattern)

                for match in matches:
                    # Build effect description from pattern
                    effect_templates = pattern.extract["effects"]

                    for template in effect_templates:
                        desc = self._fill_template(
                            template["description"],
                            match.get_env()
                        )

                        effects.append(EffectClause(description=desc))

        return effects

    def _extract_assertions(self, node) -> list[AssertClause]:
        """Extract assertions from checks in code."""
        assertions = []

        # Find isinstance checks, comparisons, etc.
        for pattern in self.patterns:
            if "assertions" in pattern.extract:
                matches = node.find_all(pattern=pattern.pattern)

                for match in matches:
                    assertion_templates = pattern.extract["assertions"]

                    for template in assertion_templates:
                        predicate = self._fill_template(
                            template["predicate"],
                            match.get_env()
                        )

                        rationale = self._fill_template(
                            template.get("rationale", ""),
                            match.get_env()
                        )

                        assertions.append(AssertClause(
                            predicate=predicate,
                            rationale=rationale if rationale else None
                        ))

        return assertions

    def _parse_parameters(self, params_str: str) -> list[Parameter]:
        """Parse parameter string into Parameter objects."""
        if not params_str or params_str.strip() == "":
            return []

        parameters = []
        for param in params_str.split(","):
            param = param.strip()

            if ":" in param:
                # Type-annotated parameter
                name, type_hint = param.split(":", 1)
                parameters.append(Parameter(
                    name=name.strip(),
                    type_hint=type_hint.strip()
                ))
            else:
                # No type annotation
                parameters.append(Parameter(
                    name=param,
                    type_hint="Any"
                ))

        return parameters

    def _fill_template(self, template: str, env) -> str:
        """Fill template with values from match environment."""
        result = template

        for var_name in env.keys():
            var_node = env.get(var_name)
            if var_node:
                var_text = var_node.text()
                result = result.replace(f"${var_name}", var_text)

        return result


__all__ = ["IRExtractor", "ExtractionPattern"]
```

**Tasks**:
- [ ] Create extraction pattern library
- [ ] Implement `IRExtractor` class
- [ ] Support function signature extraction
- [ ] Support effect extraction
- [ ] Support assertion extraction
- [ ] Unit tests for extraction

**Deliverable**: Basic IR extraction from code

### 4.2 Testing and Validation (Days 5-8)

**Tests**: `tests/unit/test_ir_extractor.py`

```python
def test_extract_simple_function():
    """Test extracting IR from simple function."""
    code = """
def add(x: int, y: int) -> int:
    return x + y
"""

    extractor = IRExtractor()
    ir = extractor.extract(code)

    assert ir is not None
    assert ir.signature.name == "add"
    assert len(ir.signature.parameters) == 2
    assert ir.signature.returns == "int"
    assert len(ir.effects) > 0

def test_extract_function_with_docstring():
    """Test extracting intent from docstring."""
    code = """
def validate_age(age: int) -> str:
    \"\"\"Check if age is valid for adult status.\"\"\"
    if age >= 18:
        return 'adult'
    else:
        return 'minor'
"""

    extractor = IRExtractor()
    ir = extractor.extract(code)

    assert ir is not None
    assert "valid" in ir.intent.summary.lower()
    assert len(ir.effects) >= 2  # if and else branches
```

**Integration with Benchmarks**:

```python
def test_extract_ir_from_benchmark_functions():
    """Test IR extraction on benchmark functions."""
    benchmark_dir = Path("benchmarks/nontrivial")

    extractor = IRExtractor()
    successful_extractions = 0
    total_functions = 0

    for py_file in benchmark_dir.glob("*.py"):
        with open(py_file) as f:
            code = f.read()

        ir = extractor.extract(code)

        total_functions += 1
        if ir and ir.signature.name:
            successful_extractions += 1

    # Should successfully extract IR from 80%+ of functions
    success_rate = successful_extractions / total_functions
    assert success_rate >= 0.80
```

**Tasks**:
- [ ] Write 15+ unit tests
- [ ] Test on benchmark functions
- [ ] Measure extraction accuracy
- [ ] Compare extracted IR with hand-written IR
- [ ] Document limitations

**Success Metrics**:
- Extract valid IR from 80%+ of functions
- Signature extraction: >95% accuracy
- Effect extraction: >70% accuracy
- Enable constraint mining in future phases

**Deliverable**: Working reverse mode foundation

### 4.3 Documentation and Examples (Days 9-14)

**Documentation**: `docs/REVERSE_MODE_GUIDE.md`

```markdown
# Reverse Mode: Code-to-IR Extraction

Extract IntermediateRepresentation from existing Python code.

## Usage

```python
from lift_sys.reverse import IRExtractor

code = """
def validate_password(password: str) -> bool:
    \"\"\"Check if password meets security requirements.\"\"\"
    if len(password) < 8:
        return False
    return True
"""

extractor = IRExtractor()
ir = extractor.extract(code)

print(ir.signature.name)  # "validate_password"
print(ir.intent.summary)  # "Check if password meets..."
```

## Extraction Patterns

Patterns are defined in YAML and specify how to map code structures to IR elements.

## Limitations

- Does not handle all Python syntax
- Complex control flow may not extract perfectly
- Relies on patterns matching code structure
```

**Tasks**:
- [ ] Write user guide for reverse mode
- [ ] Create examples showing extraction
- [ ] Document limitations
- [ ] Add troubleshooting guide

**Deliverable**: Complete reverse mode documentation

---

## Part 5: Integration and Rollout

### 5.1 Configuration and Feature Flags

**File**: `lift_sys/config.py` (enhanced)

```python
@dataclass
class RepairConfig:
    """Configuration for code repair."""

    enable_pattern_repair: bool = True
    enable_ast_repair: bool = True
    pattern_repair_first: bool = True
    max_patterns_per_code: int = 10


@dataclass
class ValidationConfig:
    """Configuration for validation."""

    enable_pattern_validation: bool = True
    pattern_validation_severity: str = "error"  # error, warning, info
    fail_on_pattern_violations: bool = True


@dataclass
class ReverseConfig:
    """Configuration for reverse mode."""

    enable_ir_extraction: bool = False  # Experimental
    extraction_confidence_threshold: float = 0.7
```

### 5.2 Metrics and Monitoring

**Track**:
- Pattern repair success rate
- Pattern validation accuracy
- False positive rate
- Average retries per generation
- IR extraction success rate

**File**: `lift_sys/metrics/pattern_metrics.py`

```python
class PatternMetrics:
    """Track pattern-based operations metrics."""

    def __init__(self):
        self.repair_stats = {
            "total_attempts": 0,
            "successful_repairs": 0,
            "patterns_applied": {},
            "failures": []
        }

        self.validation_stats = {
            "total_validations": 0,
            "passed": 0,
            "errors_found": 0,
            "warnings_found": 0,
            "false_positives": 0
        }

    def record_repair(self, success: bool, patterns: list[str]):
        """Record repair attempt."""
        self.repair_stats["total_attempts"] += 1

        if success:
            self.repair_stats["successful_repairs"] += 1

        for pattern in patterns:
            self.repair_stats["patterns_applied"][pattern] = (
                self.repair_stats["patterns_applied"].get(pattern, 0) + 1
            )

    def get_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "repair_success_rate": (
                self.repair_stats["successful_repairs"] /
                self.repair_stats["total_attempts"]
                if self.repair_stats["total_attempts"] > 0 else 0
            ),
            "validation_pass_rate": (
                self.validation_stats["passed"] /
                self.validation_stats["total_validations"]
                if self.validation_stats["total_validations"] > 0 else 0
            )
        }
```

### 5.3 Rollout Plan

**Week 1-2**: Phase 1 (Pattern Repair)
- Deploy pattern repair behind feature flag
- Enable for 10% of generations
- Monitor success rate
- Gradually increase to 100%

**Week 3-4**: Phase 2 (Pattern Validation)
- Deploy pattern validation
- Start with warnings only
- Monitor false positive rate
- Promote to errors when validated

**Week 5-6**: Phase 3 (Reverse Mode)
- Deploy as experimental feature
- Enable only for testing
- Gather feedback
- Iterate on extraction patterns

---

## Part 6: Success Criteria

### Phase 1: Pattern-Based Repair

**Must Have**:
- [x] Pattern repair engine implemented
- [x] 5+ built-in repair patterns
- [x] Integration with existing repair pipeline
- [x] >90% test coverage
- [ ] >95% repair success rate (baseline: 90%)

**Nice to Have**:
- [ ] Pattern repair faster than AST repair
- [ ] Pattern library extensible via YAML
- [ ] User-defined patterns supported

### Phase 2: Pattern-Based Validation

**Must Have**:
- [x] Pattern validator implemented
- [x] 10+ validation patterns
- [x] Integration with generation pipeline
- [x] >90% test coverage
- [ ] >98% validation accuracy
- [ ] <5% false positive rate

**Nice to Have**:
- [ ] Validation warnings don't block generation
- [ ] Pattern violations provide helpful feedback
- [ ] Custom validation patterns supported

### Phase 3: Reverse Mode

**Must Have**:
- [x] IR extractor implemented
- [x] Basic extraction patterns
- [x] >70% test coverage
- [ ] Extract IR from 80%+ of benchmark functions

**Nice to Have**:
- [ ] Extract high-quality IR from complex functions
- [ ] Support advanced Python features
- [ ] Generate training data from codebases

---

## Part 7: Risks and Mitigation

### Risk 1: ast-grep Python bindings unstable

**Probability**: Low
**Impact**: High
**Mitigation**:
- Implement CLI fallback
- Pin ast-grep-py version
- Contribute fixes upstream if needed

### Risk 2: Patterns too brittle

**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Start with simple patterns
- Add complexity incrementally
- Test extensively on real code

### Risk 3: False positives in validation

**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Start with warnings, not errors
- Monitor false positive rate
- Iterate on pattern accuracy

### Risk 4: Performance overhead

**Probability**: Low
**Impact**: Low
**Mitigation**:
- Benchmark pattern operations
- Use library API (faster than CLI)
- Cache pattern compilation

---

## Part 8: Future Enhancements

### Beyond Phase 3

**1. Constraint Mining**
- Mine patterns from successful generations
- Build constraint library automatically
- Improve IR quality through learning

**2. Advanced Reverse Mode**
- Extract more sophisticated IR
- Support complex control flow
- Handle edge cases better

**3. Interactive Repair**
- Suggest repairs to user
- Allow user to select patterns
- Learn from user choices

**4. Pattern Composition**
- Combine multiple patterns
- Create pattern hierarchies
- Build domain-specific pattern libraries

---

## Conclusion

This plan provides a structured, phased approach to integrating ast-grep into lift-sys:

**Phase 1** (2 weeks): Pattern-based code repair
**Phase 2** (2 weeks): Pattern-based validation
**Phase 3** (2 weeks): Reverse mode foundation

**Total Timeline**: 4-6 weeks
**Total Effort**: 80-120 hours

**Expected Outcomes**:
- 95%+ code repair success (vs 90% baseline)
- 98%+ validation accuracy
- <5% false positive rate
- Foundation for reverse mode and constraint mining

The phased approach allows for early validation and iteration, with each phase delivering standalone value while building toward the complete vision.

**Ready to begin Phase 1!**
