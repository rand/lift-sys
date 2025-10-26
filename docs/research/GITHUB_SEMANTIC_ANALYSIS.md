# GitHub Semantic: Applicable Techniques for lift-sys

**Date**: 2025-10-15
**Source**: https://github.com/github/semantic
**Research**: Abstracting Definitional Interpreters (arXiv:1707.04755)

---

## Overview of GitHub Semantic

GitHub Semantic is a Haskell-based library for parsing, analyzing, and comparing source code across multiple languages. It leverages:
- **Tree-sitter** for language-agnostic parsing
- **Abstracting Definitional Interpreters (ADI)** for semantic analysis
- **Abstract interpretation** for static analysis
- **Functional programming** with strong type guarantees

**Key insight**: "Control flow is not dictated by the language, but by the data structures used"

---

## Core Techniques

### 1. Abstracting Definitional Interpreters (ADI)

**What it is**:
- Transform a high-level recursive evaluator into an abstract interpreter
- Use monadic style for composability and extensibility
- Inherit meta-language properties (like call-return matching)

**How it works**:
```haskell
-- Definitional interpreter (concrete)
eval :: Expr -> Value
eval (Add e1 e2) = eval e1 + eval e2

-- Abstract interpreter (finitized)
eval :: Expr -> Set AbstractValue
eval (Add e1 e2) = Set.cartesianProduct (+) (eval e1) (eval e2)
```

**Key properties**:
- **Pushdown control flow**: Precise call-return matching by leveraging meta-language stack
- **Collecting semantics**: Capture all possible program states/traces
- **Abstract interpretation**: Over-approximate behavior with finite abstractions
- **Termination**: Caching ensures analysis terminates

### 2. Tree-sitter Integration

**What it is**:
- Language-agnostic parser generator using grammar definitions
- Generates per-language syntax types from tree-sitter grammars
- More robust than language-specific parsers (like Python's `ast`)

**Advantages**:
- **Incremental parsing**: Efficient re-parsing on edits
- **Error recovery**: Produces partial trees even with syntax errors
- **Multi-language**: Single framework for all languages
- **Precise**: Preserves all syntax information

### 3. Data Types à la Carte

**What it is**:
- Extensible, composable data types using "open unions"
- Allows different syntax types to be combined without rewriting
- Enables language-agnostic analysis

**Pattern**:
```haskell
-- Open union of syntax constructors
type Syntax = Expr :+: Statement :+: Declaration

-- Can add new constructors without changing existing code
type ExtendedSyntax = Syntax :+: NewConstruct
```

### 4. Type-Driven Development

**Philosophy**:
- "Make illegal states unrepresentable"
- Use type system to prevent bugs at compile time
- Strong static typing eliminates runtime crashes

**Result**: 20k lines of code supporting multiple languages with ~zero runtime errors

---

## Applicable Techniques for lift-sys

### ✅ IMMEDIATE: Definitional Interpreter for IR Validation

**Current problem**: IR may be semantically invalid (holes, inconsistent types) before code generation

**Solution**: Implement a simple interpreter for our Semantic IR that executes it symbolically

```python
from lift_sys.ir.models import SemanticIR, IRNode, IRHole

class IRInterpreter:
    """Execute IR symbolically to validate semantics before code generation."""

    def execute(self, ir: SemanticIR) -> ExecutionResult:
        """
        Execute IR in abstract domain to check:
        - All branches reachable
        - All holes filled with valid values
        - Types consistent across control flow
        - Return values match signature
        """
        env = AbstractEnvironment()

        for step in ir.execution_flow:
            result = self._eval_step(step, env)
            if isinstance(result, AbstractError):
                return ExecutionResult(valid=False, error=result)

        return ExecutionResult(valid=True)
```

**Benefits**:
- **Catch semantic errors BEFORE code generation**
- **Validate hole-filling produces consistent values**
- **Ensure control flow is correct**
- **Abstract execution is fast** (no actual computation)

**Implementation effort**: 2-3 days

---

### ✅ IMMEDIATE: Abstract Interpretation for Generated Code

**Current problem**: Generated code may have runtime bugs not caught by AST validation

**Solution**: Run abstract interpreter on generated code to check invariants

```python
class AbstractCodeValidator:
    """Abstract interpretation of generated Python code."""

    def validate(self, code: str, test_cases: list) -> ValidationResult:
        """
        Execute code with abstract values:
        - Track value ranges (e.g., int: -∞..+∞, narrowed by conditionals)
        - Check for division by zero
        - Verify list bounds
        - Ensure return paths
        """
        tree = ast.parse(code)
        abstract_env = AbstractEnvironment()

        # Execute with abstract values
        for test in test_cases:
            abstract_inputs = self._abstract_inputs(test)
            result = self._abstract_eval(tree, abstract_inputs, abstract_env)

            if result.has_error:
                return ValidationResult(valid=False, errors=result.errors)

        return ValidationResult(valid=True)
```

**Examples**:
```python
# Detect potential errors
def find_index(lst, value):
    for i in range(len(lst)):
        if lst[i] == value:  # Abstract: i ∈ [0, len(lst)-1], safe
            return i
    return -1

# vs buggy version
def buggy_find(lst, value):
    for i in range(len(lst) + 1):  # ← Abstract detects: i may be len(lst)
        if lst[i] == value:  # ← UNSAFE: out of bounds when i == len(lst)
            return i
```

**Benefits**:
- **Catch array bounds, division by zero, type errors**
- **Faster than running actual tests** (no execution)
- **More coverage than concrete tests** (explores all paths)

**Implementation effort**: 3-4 days

---

### 🔄 MEDIUM TERM: Tree-sitter for Code Parsing

**Current approach**: Python's `ast` module for parsing generated code

**Problem**:
- Only works for Python
- No error recovery (fails on syntax errors)
- No incremental parsing

**Solution**: Use tree-sitter for parsing generated code

```python
from tree_sitter import Language, Parser

class TreeSitterValidator:
    """Use tree-sitter for robust, language-agnostic parsing."""

    def __init__(self):
        self.python_language = Language('build/languages.so', 'python')
        self.parser = Parser()
        self.parser.set_language(self.python_language)

    def parse_and_validate(self, code: str) -> ParseResult:
        """
        Parse code with error recovery.
        Returns partial tree even if syntax errors exist.
        """
        tree = self.parser.parse(bytes(code, 'utf8'))

        # Check for ERROR nodes
        errors = self._find_error_nodes(tree.root_node)

        if errors:
            return ParseResult(valid=False, errors=errors, tree=tree)

        return ParseResult(valid=True, tree=tree)
```

**Benefits**:
- **Error recovery**: Get parse tree even with syntax errors
- **Multi-language support**: Future-proof for other languages
- **Incremental**: Efficient re-parsing during repair
- **Precise**: Better error messages

**Implementation effort**: 1 week

---

### 🔄 MEDIUM TERM: Type-Driven IR Design

**Current approach**: Python dataclasses with type hints

**Problem**:
- Type hints not enforced at runtime
- Easy to create invalid IR states
- Holes can exist indefinitely

**Solution**: Use stricter validation and sealed types

```python
from typing import Literal, Union
from pydantic import BaseModel, validator

class FilledIRNode(BaseModel):
    """IR node guaranteed to have no holes."""
    type: Literal["filled"]
    value: Union[int, str, bool, list]  # Concrete values only

    class Config:
        frozen = True  # Immutable

class UnfilledIRNode(BaseModel):
    """IR node with explicit holes."""
    type: Literal["unfilled"]
    holes: list[IRHole]

    class Config:
        frozen = True

# Type system prevents mixing filled and unfilled
def code_generator(ir: FilledIRNode) -> str:
    """Only accepts fully-filled IR - impossible to pass unfilled IR."""
    ...
```

**Benefits**:
- **Impossible to generate code from unfilled IR**
- **Type checker catches errors**
- **Self-documenting** (types encode invariants)

**Implementation effort**: 3-5 days (refactor IR models)

---

### 🎯 LONG TERM: Monadic IR Transformations

**Current approach**: Imperative hole-filling and IR transformations

**Problem**:
- Hard to compose transformations
- Error handling scattered
- Difficult to reason about intermediate states

**Solution**: Use monadic pattern for IR transformations

```python
from typing import TypeVar, Generic, Callable
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class IRResult(Generic[T]):
    """Result of IR transformation."""
    value: T | None
    errors: list[str]

    def bind(self, f: Callable[[T], 'IRResult']) -> 'IRResult':
        """Monadic bind: chain transformations."""
        if self.errors:
            return IRResult(None, self.errors)
        return f(self.value)

    @staticmethod
    def pure(value: T) -> 'IRResult[T]':
        """Lift value into IRResult."""
        return IRResult(value, [])

# Use it
def fill_holes(ir: SemanticIR) -> IRResult[SemanticIR]:
    return (
        IRResult.pure(ir)
        .bind(validate_structure)
        .bind(infer_types)
        .bind(fill_missing_values)
        .bind(validate_consistency)
    )
```

**Benefits**:
- **Composable transformations**
- **Explicit error propagation**
- **Easier to test** (pure functions)
- **Easier to reason about**

**Implementation effort**: 1-2 weeks (redesign transformation pipeline)

---

## Comparison: GitHub Semantic vs lift-sys

| Aspect | GitHub Semantic | lift-sys (current) | lift-sys (proposed) |
|--------|----------------|-------------------|-------------------|
| **Parsing** | Tree-sitter (multi-language) | Python `ast` | Tree-sitter |
| **Analysis** | Abstract interpretation | AST-based validation | Abstract interpretation + AST |
| **Type safety** | Haskell type system | Python type hints | Pydantic + stricter validation |
| **IR validation** | Definitional interpreter | Text-based checks | IR interpreter |
| **Composition** | Monadic | Imperative | Monadic transformations |
| **Error handling** | Type-driven | Runtime checks | Type-driven + abstract |
| **Code generation** | N/A (analysis tool) | AI + AST repair | AI + interpretation + repair |

---

## Recommended Implementation Order

### Phase 4 (Current): AST-Based Repair ✅
**Status**: IMPLEMENTED
**Approach**: Deterministic AST transformations for known bug patterns

### Phase 5: IR Interpreter
**Priority**: HIGH
**Effort**: 2-3 days
**Impact**: Catch IR semantic errors before code generation

**Steps**:
1. Create `IRInterpreter` class
2. Implement abstract execution for IR nodes
3. Validate control flow and hole consistency
4. Integrate before code generation

### Phase 6: Abstract Code Validator
**Priority**: MEDIUM-HIGH
**Effort**: 3-4 days
**Impact**: Detect runtime bugs statically

**Steps**:
1. Create `AbstractCodeValidator` class
2. Implement abstract value tracking
3. Check bounds, division, type consistency
4. Integrate after AST repair

### Phase 7: Tree-sitter Integration
**Priority**: MEDIUM
**Effort**: 1 week
**Impact**: More robust parsing, error recovery

### Phase 8: Type-Driven IR
**Priority**: MEDIUM
**Effort**: 3-5 days
**Impact**: Prevent invalid IR states

### Phase 9: Monadic Transformations
**Priority**: LOW (refactoring)
**Effort**: 1-2 weeks
**Impact**: Cleaner, more composable code

---

## Key Insights for lift-sys

### 1. Validate Semantics Before Syntax
- GitHub Semantic: Analyze code semantically before worrying about syntax
- lift-sys: **Validate IR semantics before generating code**
- Implementation: IR interpreter that checks consistency

### 2. Use Deterministic Tools Where Possible
- GitHub Semantic: Deterministic parsing and analysis
- lift-sys: **Already doing this with AST repair** ✅
- Extend: Add abstract interpretation for more coverage

### 3. Make Invalid States Unrepresentable
- GitHub Semantic: Haskell types prevent invalid programs
- lift-sys: **Use Pydantic to enforce IR invariants**
- Benefit: Bugs caught at "compile time" (IR generation)

### 4. Separate Concerns
- GitHub Semantic: Parsing → Analysis → Output
- lift-sys: **IR generation → Validation → Code generation → Repair**
- Add: IR interpretation between validation and code generation

### 5. Compose Transformations
- GitHub Semantic: Monadic composition of effects
- lift-sys: **Consider monadic IR transformations** for cleaner code

---

## Expected Impact

### Current State (Phase 4)
- **70-80%** success rate
- AST repair fixes known patterns
- AI generation + deterministic repair

### With IR Interpreter (Phase 5)
- **Expected: 85-90%**
- Catch semantic errors before code generation
- Fewer wasted generation attempts
- Better error messages

### With Abstract Interpretation (Phase 6)
- **Expected: 90-95%**
- Catch runtime bugs statically
- More coverage than concrete tests
- Complementary to AST repair

### Full Integration (Phases 5-9)
- **Expected: 95%+**
- Layered validation:
  1. IR interpreter (semantics)
  2. Code generation (AI)
  3. Abstract interpretation (runtime safety)
  4. AST repair (known patterns)
  5. Concrete tests (verification)

---

## References

1. **Abstracting Definitional Interpreters** (2017)
   Darais, Labich, Nguyen, Van Horn
   https://arxiv.org/abs/1707.04755

2. **GitHub Semantic**
   https://github.com/github/semantic

3. **Tree-sitter**
   https://tree-sitter.github.io/tree-sitter/

4. **Data Types à la Carte** (2008)
   Wouter Swierstra
   http://www.cs.ru.nl/~W.Swierstra/Publications/DataTypesALaCarte.pdf

---

## Bottom Line

**GitHub Semantic shows**: Deterministic program analysis techniques can reliably catch bugs that AI-based approaches miss.

**For lift-sys**: Complement AI code generation with:
1. ✅ **AST-based repair** (Phase 4 - DONE)
2. 🎯 **IR interpretation** (Phase 5 - NEXT)
3. 🎯 **Abstract interpretation** (Phase 6)
4. 🔄 **Tree-sitter** (Phase 7)
5. 🔄 **Type-driven IR** (Phase 8)

This creates a **hybrid AI + formal methods system** that combines:
- **AI**: Creative code generation
- **Formal**: Deterministic validation and repair

Expected result: **90-95%+ success rate** with layered validation catching different bug classes.
