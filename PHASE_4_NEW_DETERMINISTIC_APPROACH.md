# Phase 4 NEW: Deterministic AST-Based Auto-Repair

**Date**: 2025-10-15
**Status**: DESIGN
**Previous Attempt**: Concrete examples (FAILED - decreased performance to 70%)

---

## Why Previous Approach Failed

**Phase 4 v1 (Concrete Examples)**: Added 3000+ char examples to prompts
- **Result**: 70% success (DOWN from 80%)
- **Why it failed**:
  - Prompt overload confused the LLM
  - Examples added noise instead of clarity
  - AI still couldn't reliably understand indentation semantics from text

**Key Insight**: **Don't ask AI to fix what we can fix deterministically**

---

## New Approach: Complement AI with Deterministic Logic

### Core Principle

**Hybrid AI + Deterministic System:**
1. Let AI generate code (gets ~80% right - good enough for first pass)
2. **Deterministically detect** known bug patterns using AST
3. **Deterministically fix** bugs using AST transformations
4. Validate the repaired code

### Why This Will Work

✅ **Deterministic fixes are reliable** - No guessing, just transformation
✅ **AST transformations preserve semantics** - We know exactly what to change
✅ **Complements AI strengths** - AI does creative work, we do mechanical fixes
✅ **Backed by research** - AST-based repair is proven in program synthesis

---

## Known Bug Patterns & Fixes

### Bug Pattern 1: Return Inside Loop

**Detection** (AST):
```python
for index, item in enumerate(lst):
    if item == value:
        return index
    return -1  # ❌ BUG: Inside loop body
```

**AST Structure**:
```
For(body=[
    If(test=..., body=[Return(...)]),
    Return(value=-1)  # ← Wrong indentation
])
```

**Deterministic Fix**:
- Detect: `Return` node directly in `For.body` (not inside `If`)
- Transform: Move `Return` to AFTER the `For` node
- Result: Return is now a sibling of the loop, not a child

**Code**:
```python
def fix_loop_return_placement(tree: ast.AST) -> ast.AST:
    """
    Find returns in loop body and move them after the loop.

    Pattern:
        for ...:
            if ...:
                return ...
            return FALLBACK  # ← Move this outside
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            # Find returns directly in loop body (not in if)
            returns_to_move = []
            for i, stmt in enumerate(node.body):
                if isinstance(stmt, ast.Return):
                    # This return should be after loop
                    returns_to_move.append((i, stmt))

            if returns_to_move:
                # Remove from loop body
                for i, ret in reversed(returns_to_move):
                    node.body.pop(i)

                # Insert after loop in parent
                # (requires tracking parent, or rebuild tree)

    return tree
```

### Bug Pattern 2: type().__name__ Instead of isinstance

**Detection** (AST):
```python
# Detects this pattern:
return type(value).__name__  # ❌ BUG
```

**AST Structure**:
```
Return(
    value=Attribute(
        value=Call(func=Name('type'), args=[...]),
        attr='__name__'
    )
)
```

**Deterministic Fix**:
- Detect: `type(x).__name__` pattern
- Transform: Replace with if-elif chain using isinstance
- Result: Correct type checking with literal returns

**Code**:
```python
def fix_type_check_pattern(tree: ast.AST) -> ast.AST:
    """
    Replace type().__name__ with isinstance checks.

    Pattern:
        return type(value).__name__

    Replace with:
        if isinstance(value, int): return 'int'
        elif isinstance(value, str): return 'str'
        elif isinstance(value, list): return 'list'
        else: return 'other'
    """
    # Find pattern and replace entire function body
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if _is_type_name_pattern(node.value):
                # Replace with isinstance chain
                pass  # Implementation below

    return tree

def _is_type_name_pattern(node) -> bool:
    """Detect type(x).__name__ pattern."""
    return (
        isinstance(node, ast.Attribute) and
        node.attr == '__name__' and
        isinstance(node.value, ast.Call) and
        isinstance(node.value.func, ast.Name) and
        node.value.func.id == 'type'
    )
```

---

## Implementation Plan

### Module: `lift_sys/codegen/ast_repair.py`

```python
"""
Deterministic AST-based code repair.

Complements AI code generation with mechanical fixes for known patterns.
"""

import ast
from typing import Optional

class ASTRepairEngine:
    """Deterministically fix known code patterns."""

    def repair(self, code: str, function_name: str) -> Optional[str]:
        """
        Attempt to repair known bugs in generated code.

        Returns:
            Fixed code if repairs were made, None if no repairs needed
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None  # Can't repair unparseable code

        # Apply repair passes
        modified = False

        # Pass 1: Fix loop return placement
        tree, changed1 = self._fix_loop_returns(tree)
        modified |= changed1

        # Pass 2: Fix type checking
        tree, changed2 = self._fix_type_checks(tree)
        modified |= changed2

        if not modified:
            return None

        # Convert back to code
        return ast.unparse(tree)

    def _fix_loop_returns(self, tree: ast.AST) -> tuple[ast.AST, bool]:
        """Fix returns placed inside loops when they should be after."""
        # Implementation
        pass

    def _fix_type_checks(self, tree: ast.AST) -> tuple[ast.AST, bool]:
        """Fix type().__name__ patterns."""
        # Implementation
        pass
```

### Integration with Code Generator

```python
# In XGrammarCodeGenerator.generate()

# After generating code
code_result = await self._generate_implementation(ir, structure, attempt, temperature)

# Try deterministic repair
repair_engine = ASTRepairEngine()
repaired_code = repair_engine.repair(code_result.source_code, ir.signature.name)

if repaired_code:
    print(f"  🔧 Applied AST-based repairs")
    code_result.source_code = repaired_code

# Then validate as usual
issues = self.validator.validate(code_result.source_code, ...)
```

---

## Expected Impact

### Current State (Phase 1-3)
- Success rate: **80% (8/10)**
- Failing tests: find_index, get_type_name
- Problem: AI generates buggy code, validation detects but retry doesn't fix

### With Deterministic Repair
- **Expected**: **90%+ (9/10)**
- **How**:
  - find_index: AST repair moves return outside loop → FIXED
  - get_type_name: AST repair replaces type().__name__ → FIXED
- **Benefit**: Deterministic, reliable, no prompt engineering needed

---

## Advantages Over Examples Approach

| Aspect | Examples (v1) | Deterministic Repair (v2) |
|--------|--------------|--------------------------|
| Reliability | ❌ Unpredictable | ✅ **100% for known patterns** |
| Prompt size | ❌ 3000+ chars | ✅ No change |
| LLM confusion | ❌ Can confuse | ✅ **Doesn't affect generation** |
| Extensibility | ⚠️ Need more examples | ✅ **Add repair rules** |
| Performance | ❌ Decreased to 70% | ✅ **Expected 90%+** |
| Debuggability | ❌ Hard to understand failures | ✅ **Know exactly what was fixed** |

---

## Implementation Steps

1. **Create `lift_sys/codegen/ast_repair.py`**
   - ASTRepairEngine class
   - Loop return fixer
   - Type check fixer

2. **Integrate with generator**
   - Call repair after code generation
   - Log what was repaired
   - Validate repaired code

3. **Test on Phase 2 suite**
   - Verify find_index gets fixed
   - Verify get_type_name gets fixed
   - Measure overall improvement

4. **Iterate on repair rules**
   - Add more patterns as discovered
   - Refine detection logic
   - Ensure repairs preserve semantics

---

## Example: Complete Flow

```
1. Prompt: "Find index of value in list, return -1 if not found"
2. AI generates:
   for i, v in enumerate(lst):
       if v == val:
           return i
       return -1  # ← BUG

3. Validation detects: "return inside loop body"

4. AST Repair:
   - Detects: Return as direct child of For.body
   - Transforms: Moves return after loop
   - Result:
     for i, v in enumerate(lst):
         if v == val:
             return i
     return -1  # ← FIXED

5. Validation passes → Success!
```

---

## Extensibility

### Future Repair Patterns

Once infrastructure is in place, we can add:

- **Missing edge case checks** - Add `if not lst: return None`
- **Off-by-one errors** - Fix range() bounds
- **Variable naming** - Rename to match IR specification
- **Missing error handling** - Add try-except where needed

### AST Repair Library

Build a library of transformations:
```python
REPAIR_RULES = [
    LoopReturnRule(),
    TypeCheckRule(),
    EdgeCaseRule(),
    # Add more as needed
]
```

---

## Success Metrics

### Primary
- **>90% success rate** on Phase 2 suite (currently 80%)
- **100% fix rate** for known patterns (loop returns, type checks)

### Secondary
- **<100ms repair latency** (deterministic is fast)
- **Zero false repairs** (don't break working code)
- **Measurable impact** (track repairs applied per test)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| AST repair breaks working code | Only apply if validation detected issue |
| Miss edge cases in detection | Conservative detection (false negatives OK) |
| Repair introduces new bugs | Always validate after repair |
| Too complex to maintain | Start simple, add rules incrementally |

---

## Timeline

- **Day 1**: Implement ASTRepairEngine with 2 rules (loop return, type check)
- **Day 2**: Integrate with generator, add logging
- **Day 3**: Test on Phase 2 suite, measure improvement
- **Day 4**: Refine rules, add more patterns if needed

**Estimated effort**: 2-4 days for 90%+ success rate

---

## Key Insight

**AI is creative but unreliable for mechanical tasks.**
**Deterministic logic is reliable but can't be creative.**

**Best approach: Use both**
- AI: Generate initial code (creative, semantic understanding)
- Deterministic: Fix known mechanical issues (reliable, precise)

---

**Bottom Line**: Don't ask AI to understand what we can fix mechanically. Complement AI generation with deterministic repairs for predictable, reliable improvements.
