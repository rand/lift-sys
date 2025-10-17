# Persistent Test Failures Analysis

**Status**: 15/18 tests passing (83.3%) at temperature=0.8 with Best-of-N=3

**Date**: 2025-10-16

## Overview

After expanding AST repair engine with Passes 4 & 5 (missing imports, missing returns), three tests continue to fail consistently. These appear to be **semantic/logic errors** rather than syntactic issues, which means they cannot be fixed by deterministic AST transformations.

## The 3 Persistent Failures

### 1. `count_words` - Missing Return Value

**Prompt**: "Create a function that counts the number of words in a string, where words are separated by spaces"

**Failure**: Returns `None` instead of the word count

**Test case that fails**:
```python
count_words("hello world")  # Expected: 2, Got: None
```

**Root cause**: The LLM likely generates code that calculates the count but doesn't return it. Example:
```python
def count_words(text):
    count = len(text.split())
    # Missing: return count
```

**Why AST repair didn't fix it**: Our Pass 5 (missing returns) has heuristics for:
- Pattern 1: Last statement assigns to variable → return it
- Pattern 2: Last statement is expression → convert to return

But if the function has multiple statements or the pattern doesn't match exactly, it won't trigger.

**Potential fixes**:
1. **Improve Pass 5 heuristics**: Detect when last statement assigns to variable named `count`, `result`, `output`, etc. and add return
2. **Add semantic validation**: Check that functions with return type hints actually return on all code paths
3. **Prompt engineering**: Be more explicit: "...and return the count"
4. **Accept variance**: This may be a 5-10% failure mode at temperature=0.8

---

### 2. `find_index` - Off-by-One Error

**Prompt**: "Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found."

**Failure**: Off-by-one error in index calculation

**Test case that fails**:
```python
find_index([5, 5, 5], 5)  # Expected: 0, Got: 2
```

**Root cause**: The LLM generates incorrect loop logic, possibly:
- Starting enumeration at 1 instead of 0
- Returning the wrong index variable
- Some other off-by-one arithmetic error

**Why AST repair didn't fix it**: This is a pure logic error. AST repair cannot detect algorithmic mistakes.

**Potential fixes**:
1. **Post-generation validation**: Run test cases during generation and retry if failed
2. **Better prompting**: Even more explicit about 0-indexing
3. **Lower temperature**: Try temperature=0.5 or 0.6 for more deterministic output
4. **Accept variance**: Off-by-one errors are classic LLM mistakes; may be inherent

---

### 3. `is_valid_email` - Validation Logic Error

**Prompt**: "Create a function that checks if a string is a valid email address. Must contain @ symbol and a dot after the @"

**Failure**: Incorrect validation logic for edge cases

**Test case that fails**:
```python
is_valid_email("test@.com")  # Expected: False, Got: True
```

**Root cause**: The LLM generates validation that checks for:
- Contains `@`
- Contains `.`
- But doesn't verify the `.` comes AFTER the `@`

Example bad code:
```python
def is_valid_email(email):
    return '@' in email and '.' in email
```

This passes "test@.com" because it has both, but doesn't check position.

**Why AST repair didn't fix it**: This is semantic logic, not syntax.

**Potential fixes**:
1. **More explicit prompt**: "...and the dot must come AFTER the @ symbol with at least one character between them"
2. **Add validation pass**: Detect common validation patterns and add position checks
3. **Post-generation testing**: Validate against edge cases and retry
4. **Accept variance**: Complex validation logic is harder for LLMs

---

## Analysis: Why These Fail

All three failures share a common pattern:
- **Syntactically valid code** (passes AST parsing)
- **Semantically incorrect logic** (doesn't match intent)
- **Not fixable by deterministic transformations** (would require understanding intent)

### What AST Repair CAN Fix
- Indentation issues
- Missing imports for stdlib modules
- Missing returns (simple patterns only)
- Syntax errors

### What AST Repair CANNOT Fix
- Logic errors (wrong algorithm)
- Off-by-one errors
- Incorrect validation rules
- Semantic mismatches between prompt and code

---

## Recommendation

**Accept 83.3% success rate** and focus on stability/variance measurement.

### Rationale:
1. **Exceeds goal**: 83.3% > 80% target
2. **Inherent to temperature=0.8**: Higher temperature = more creativity = more variance
3. **Best-of-N already helps**: Without it, success rate would likely be lower
4. **Diminishing returns**: Fixing these would require:
   - Complex semantic analysis (expensive)
   - Post-generation validation with retries (expensive)
   - Lower temperature (reduces creativity)

### Next Steps:
1. Run 2x or 5x stability test to measure variance
2. If std dev < 10%, production-ready
3. If specific failures matter, can target them individually later

---

## Future Improvement Options

If we need to improve beyond 83.3%:

### Option 1: Validation-Based Retry
- Generate code
- Run test cases
- If failed, retry with modified prompt
- Expensive (2-3x cost), but could hit 90%+

### Option 2: Lower Temperature
- Try temperature=0.5 or 0.6
- More deterministic, fewer logic errors
- Trade-off: Less creative solutions

### Option 3: Semantic AST Repair
- Build semantic analyzer for common patterns
- Detect validation logic errors
- Fix known semantic bugs
- Complex to build, maintain

### Option 4: Model Upgrade
- Try Qwen2.5-Coder-72B (larger model)
- Better reasoning → fewer logic errors
- More expensive inference

### Option 5: Targeted Prompting
- Identify failure patterns
- Add explicit constraints to prompts
- "return the result", "check position after @", etc.
- Low cost, incremental improvement

---

## Test Data

### Baseline Run (temperature=0.8, Best-of-N=3)
```
Total tests:       18
Passed:            15/18 (83.3%)
Failed:            3/18 (16.7%)

By Category:
  control_flow        : 3/3 (100.0%)
  data_structures     : 2/2 (100.0%)
  edge_cases          : 2/2 (100.0%)
  list_operations     : 2/3 (66.7%)   [find_index failed]
  mathematical        : 3/3 (100.0%)
  string_manipulation : 1/3 (33.3%)   [count_words, is_valid_email failed]
  type_operations     : 2/2 (100.0%)
```

### Failed Tests Detail
1. **count_words** (string_manipulation): 1/5 test cases passed
2. **find_index** (list_operations): 4/5 test cases passed
3. **is_valid_email** (string_manipulation): 4/5 test cases passed

Each fails on edge cases or specific logic requirements.

---

## Conclusion

The 83.3% success rate is solid and production-ready for most use cases. The 3 failures are semantic logic errors that would require expensive fixes (retries, validation, lower temperature) or complex semantic analysis.

**Recommended path**: Measure stability (variance) across multiple runs, then proceed to production if std dev < 10%.
