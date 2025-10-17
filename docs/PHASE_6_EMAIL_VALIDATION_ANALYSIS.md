# Phase 6: Email Validation Failure Analysis & Solutions

## Problem Summary

The `is_valid_email` function failed validation across all 3 regeneration attempts despite clear error feedback.

### Generated Code (All Attempts)

```python
def is_valid_email(email: str) -> bool:
    if '@' not in email:
        return False
    if '.' not in email:
        return False
    if email.index('@') > email.rindex('.'):
        return False
    return True
```

### The Bug

**Test case**: `test@.com`
**Expected**: `False` (dot immediately after @ is invalid)
**Got**: `True` (incorrect)

**Why it fails:**
- `email.index('@')` = 4
- `email.rindex('.')` = 5
- Check `4 > 5` = `False`, so doesn't return False
- Code returns True (wrong!)

### Root Cause

**Semantic mismatch** between IR and test expectations:
- **IR says**: "Check that dot comes after @" (positional ordering)
- **Test expects**: "Dot must not be immediately adjacent to @" (adjacency check)
- **LLM implements**: Positional check (`index('@') > rindex('.')`)
- **Missing logic**: Adjacency check (`rindex('.') - index('@') > 1`)

## Why LLM Regeneration Failed

### Attempt 1-3: Same Bug Pattern

**Error feedback provided**:
```
Effect test: 'test@.com' should be invalid (dot immediately after @)
Input: {'email': 'test@.com'}
Expected: False
Got: True
```

**Why LLM didn't fix it:**

1. **Ambiguous phrasing**: "dot immediately after @" is descriptive but not prescriptive
2. **No explicit solution hint**: Doesn't say "check distance between @ and ."
3. **Confirmation bias**: LLM sees its check `email.index('@') > email.rindex('.')` and thinks "I'm already checking that dot comes after @"
4. **Temperature doesn't help**: Higher temperature just adds noise, doesn't address the semantic gap

### LLM's Mental Model (Inferred)

The LLM likely thinks:
- "I need to ensure dot comes after @" ✓ (already doing this)
- "The test is failing, but my logic seems right"
- "Maybe it's an edge case with my index comparison?" (increases temperature, tries again)
- **Never considers**: "Maybe I need to check the *distance* between @ and ."

## Deterministic Solutions

### Solution 1: Pattern-Based AST Repair

**Approach**: Detect email validation pattern in AST and auto-fix adjacency bugs

```python
class EmailValidationRepair(ASTTransformer):
    """Detect and fix email validation adjacency bugs."""

    def visit_FunctionDef(self, node):
        # Detect email validation function
        if not self._is_email_validation(node):
            return node

        # Find the index comparison pattern
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Compare):
                if self._is_index_comparison(stmt, '@', '.'):
                    # Found: email.index('@') > email.rindex('.')
                    # Need to add adjacency check
                    return self._add_adjacency_check(node, stmt)

        return node

    def _add_adjacency_check(self, func_node, comparison_node):
        """
        Transform:
            if email.index('@') > email.rindex('.'):
                return False

        To:
            at_pos = email.index('@')
            dot_pos = email.rindex('.')
            if at_pos >= dot_pos or dot_pos - at_pos == 1:
                return False
        """
        # Generate improved check
        new_check = ast.parse("""
at_pos = email.index('@')
dot_pos = email.rindex('.')
if at_pos >= dot_pos or dot_pos - at_pos == 1:
    return False
""").body

        # Replace old comparison with new check
        return self._replace_in_function(func_node, comparison_node, new_check)
```

**Pros**:
- Fully deterministic - always fixes this pattern
- No LLM calls needed
- Fast execution

**Cons**:
- Only handles this specific pattern
- Brittle to code variations

---

### Solution 2: Enhanced Error Feedback with Explicit Hints

**Approach**: Detect "adjacency" failures and provide explicit implementation guidance

```python
def _create_regeneration_feedback(self, validation_result, attempt_num):
    """Enhanced feedback with pattern detection."""

    # Detect email adjacency bug
    email_adjacency_failures = [
        f for f in validation_result.failed_tests
        if 'email' in str(f.test_case.description).lower()
        and '@.' in str(f.test_case.inputs.get('email', ''))
    ]

    if email_adjacency_failures:
        feedback_parts.append("""
⚠️  EMAIL ADJACENCY BUG DETECTED

The test 'test@.com' is failing because your code checks if dot comes AFTER @,
but doesn't check if they are ADJACENT (next to each other).

CURRENT CODE LIKELY HAS:
    if email.index('@') > email.rindex('.'):
        return False

PROBLEM: For 'test@.com', @ is at index 4, . is at index 5
    - Check: 4 > 5 = False, so doesn't return False
    - Code incorrectly returns True

SOLUTION: Check both position AND distance:
    at_pos = email.index('@')
    dot_pos = email.rindex('.')
    if at_pos >= dot_pos:  # Dot must come after @
        return False
    if dot_pos - at_pos == 1:  # Must not be adjacent
        return False

Or more concisely:
    if at_pos >= dot_pos or dot_pos - at_pos == 1:
        return False
""")
```

**Pros**:
- Provides explicit solution template
- LLM can copy-paste the pattern
- Educational - explains the bug

**Cons**:
- Still relies on LLM to implement
- May not generalize to other adjacency bugs

---

### Solution 3: Test Case Enhancement

**Approach**: Generate additional test cases that make the requirement explicit

```python
def _generate_email_validation_tests(self, ir):
    """Generate comprehensive email validation tests."""

    tests = [
        # ... existing tests ...

        # EXPLICIT adjacency tests
        TestCase(
            inputs={"email": "test@.com"},
            expected_output=False,
            description="CRITICAL: @ and . must have at least 1 char between (test@.com is invalid)"
        ),
        TestCase(
            inputs={"email": "test@x.com"},
            expected_output=True,
            description="@ and . with 1 char between is valid (test@x.com)"
        ),
        TestCase(
            inputs={"email": "test@xy.com"},
            expected_output=True,
            description="@ and . with 2+ chars between is valid (test@xy.com)"
        ),
    ]

    return tests
```

**Pros**:
- Makes requirement crystal clear through examples
- No code changes to generator needed
- LLM can infer pattern from test variations

**Cons**:
- More tests = slower validation
- Still relies on LLM comprehension

---

### Solution 4: Few-Shot Examples in Feedback

**Approach**: Include working email validation code in regeneration feedback

```python
def _create_regeneration_feedback(self, validation_result, attempt_num):
    """Add few-shot examples for common patterns."""

    if self._is_email_validation_failure(validation_result):
        feedback_parts.append("""
⚠️  EMAIL VALIDATION FAILURE

Here's a working example of proper email validation:

```python
def is_valid_email(email: str) -> bool:
    # Check for @ and .
    if '@' not in email or '.' not in email:
        return False

    # Get positions
    at_pos = email.index('@')
    dot_pos = email.rindex('.')

    # Dot must come after @, with at least 1 char between
    if at_pos >= dot_pos or dot_pos - at_pos == 1:
        return False

    # @ must not be first, . must not be last
    if at_pos == 0 or dot_pos == len(email) - 1:
        return False

    return True
```

Apply this pattern to your implementation.
""")
```

**Pros**:
- Provides concrete working solution
- LLM can adapt the pattern
- Handles multiple edge cases

**Cons**:
- May reduce LLM creativity
- Could be seen as "giving away the answer"

---

### Solution 5: Regex Suggestion

**Approach**: For email validation specifically, suggest using regex

```python
def _create_regeneration_feedback(self, validation_result, attempt_num):
    """Suggest regex for email validation."""

    if self._is_email_validation_failure(validation_result) and attempt_num >= 2:
        feedback_parts.append("""
💡  SUGGESTION: Use regex for robust email validation

Email validation has many edge cases. Consider using regex:

```python
import re

def is_valid_email(email: str) -> bool:
    # Simple pattern: text @ text . text
    pattern = r'^[^@]+@[^@.]+\.[^@.]+$'
    return bool(re.match(pattern, email))
```

This pattern ensures:
- Characters before @
- At least one char between @ and .
- At least one char after .
""")
```

**Pros**:
- Correct solution for email validation
- Handles many edge cases automatically
- Common real-world approach

**Cons**:
- Requires importing `re` module
- May not be available in restricted environments
- Doesn't teach the underlying logic

---

## Recommended Hybrid Approach

Combine multiple solutions for maximum effectiveness:

### Priority 1: Pattern-Based AST Repair (Deterministic)

Add email validation pattern to Phase 4 AST Repair Engine:

```python
# In lift_sys/codegen/ast_repair.py

def repair_email_validation_adjacency(self, tree, func_name):
    """
    Detect and fix email validation adjacency bugs.

    Pattern: if email.index('@') > email.rindex('.')
    Fix: Add adjacency check
    """
    class EmailAdjacencyFixer(ast.NodeTransformer):
        def visit_If(self, node):
            # Detect the pattern
            if self._is_email_index_comparison(node.test):
                # Add adjacency check
                return self._add_adjacency_check(node)
            return self.generic_visit(node)

    fixer = EmailAdjacencyFixer()
    return fixer.visit(tree)
```

### Priority 2: Enhanced Feedback (LLM Guidance)

Improve `ValidatedCodeGenerator._create_regeneration_feedback()`:

```python
# Detect specific bug patterns
if self._is_email_adjacency_bug(validation_result):
    feedback += EXPLICIT_EMAIL_ADJACENCY_FIX  # Solution template
elif self._is_missing_return_bug(validation_result):
    feedback += EXPLICIT_RETURN_STATEMENT_FIX
# ... more patterns ...
```

### Priority 3: Better Test Cases (Prevention)

Enhance `TestCaseGenerator._generate_effect_tests()` for email validation:

```python
# Add explicit adjacency tests with clear descriptions
tests.append(TestCase(
    inputs={params[0].name: "test@.com"},
    expected_output=False,
    description="@ and . must NOT be adjacent (need at least 1 char between)"
))
```

## Expected Impact

With hybrid approach:
- **AST Repair catches it**: 95% chance of fix before LLM regeneration
- **Enhanced feedback fixes it**: 80% chance on retry if AST repair missed it
- **Better tests prevent it**: 70% chance LLM generates correct code initially

**Combined success rate**: ~99% for email validation pattern

## Implementation Cost

- **AST Repair addition**: 2-3 hours (add pattern, test, integrate)
- **Feedback enhancement**: 1-2 hours (pattern detection, templates)
- **Test case improvement**: 1 hour (add adjacency tests)

**Total**: 4-6 hours for complete solution

---

**Conclusion**: The is_valid_email failure is caused by a semantic gap between "positional ordering" and "adjacency checking". The LLM can't bridge this gap with feedback alone. Deterministic AST repair is the most reliable solution, with enhanced feedback as a backup.
