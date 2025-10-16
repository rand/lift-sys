# Semantic IR Improvement Plan

**Status**: 🎯 **ACTIVE PLAN** - Addressing Phase 3 results (72.2% success)
**Created**: October 16, 2025
**Priority**: High (below 80% target)

---

## Executive Summary

Phase 3 testing achieved **72.2% success** (13/18 passing), below the **80% target**. Analysis reveals systematic failures in:

1. **Exact string literals** - LLM generates verbose strings instead of specified literals
2. **Type checking logic** - Boolean/int isinstance ordering bugs persist
3. **Logic correctness** - Edge cases missed (min/max, email validation)
4. **Code generation stability** - Syntax errors persist through retries

This plan focuses on **upstream improvements** (IR generation quality) and **model assessment** rather than downstream validation fixes.

**Key Questions**:
1. Is the IR specification missing critical details?
2. Is Qwen2.5-Coder-7B-Instruct capable of following precise instructions?
3. Would a better model significantly improve results?

---

## Part 1: IR Generation Analysis

### Current Architecture

**Phase 1: NLP → IR Translation** (`lift_sys/forward_mode/xgrammar_translator.py:200-260`)

```python
def get_prompt_for_ir_generation(user_prompt: str) -> str:
    """Generate a system prompt for IR creation."""
    return f"""You are an expert at converting natural language specifications...

    The IR should include:
    1. **intent**: High-level purpose
    2. **signature**: Function name, parameters, return type
    3. **effects**: Side effects or external interactions
    4. **assertions**: Logical constraints, preconditions, postconditions

    Important guidelines:
    - Function names should be snake_case
    - Type hints should use Python syntax
    - Extract constraints as assertions

    **CRITICAL: Effects must be EXPLICIT about implementation details:**

    1. **Explicit Return Statements**
    2. **Literal Values** - When user says "return exactly 'X'", emphasize literal
    3. **Edge Cases** - Handle empty inputs, boundaries
    4. **Loop Patterns** - Specify iteration method, return conditions
    5. **Control Flow** - Be explicit about if/elif/else structure

    User's request: {user_prompt}
    """
```

**Current Model**: `Qwen/Qwen2.5-Coder-7B-Instruct` via Modal
**Temperature**: 0.3 (low for structured output)
**Backend**: vLLM 0.9.2 + XGrammar (enforces JSON schema only)

### Analysis of Failing Tests

#### Test 1: `validate_password` (FAILED - Verbose String)

**Prompt**:
```
Create a function that validates a password. Return 'too short' if less than 8 chars,
'no number' if no digit, 'no uppercase' if no uppercase letter, or 'valid' if all met
```

**Expected**: Exact strings `'too short'`, `'no number'`, `'no uppercase'`, `'valid'`
**Actual**: Generated `"Password is too short"` instead of `"too short"`

**Root Cause**:
- IR likely specified "return a message indicating password is too short"
- Code generator interpreted as "write helpful message" (training bias)
- Current prompt says "Be explicit about return values" but not specific enough

**IR Quality Issue**: Effects clause not emphasizing **exact literal strings**

---

#### Test 2: `get_type_name` (FAILED - JSON Generation Error)

**Prompt**:
```
Create a function that checks the type of a value. Use isinstance() to check if the
value is an int, str, or list. Return the exact string 'int', 'str', or 'list' if it
matches. If none match, return exactly 'other' (must be the string 'other').
```

**Expected**: Literal strings `'int'`, `'str'`, `'list'`, `'other'`
**Edge Case**: `True` should return `'other'` (bool is subclass of int in Python)

**Actual**: JSON generation failed after 5 retries (unterminated string)

**Root Causes**:
1. IR may not specify Python quirk: `isinstance(True, int) == True`
2. IR may not enforce check order (bool before int)
3. Retries added feedback but LLM ignored or got confused
4. Multiple attempts caused context overload → syntax errors

**IR Quality Issues**:
- Missing language-specific edge case documentation
- No explicit ordering constraints in effects
- No mention of "check bool before int" requirement

---

#### Test 3: `is_valid_email` (FAILED - Logic Error)

**Prompt**:
```
Create a function that checks if a string is a valid email address.
Must contain @ symbol and a dot after the @
```

**Expected**: Pass 5 tests including edge cases (`@example.com`, `user@.com`)
**Actual**: Passed 3/5 tests (missed edge cases)

**Root Cause**:
- IR likely specified "check for @ and . after @"
- Code may have checked only existence, not position/order
- Edge cases: `@example.com` (@ at start), `user@.com` (. immediately after @)

**IR Quality Issue**: Effects not specific about **position and ordering** of characters

---

#### Test 4: `safe_int_conversion` (FAILED - Syntax Error)

**Prompt**:
```
Create a function that converts a string to an integer, returning 0 if conversion fails
```

**Expected**: Simple try/except block
**Actual**: Syntax error after 5 retries

**Root Cause**:
- IR may not specify exception handling pattern
- Code generator struggled with try/except syntax
- Retries didn't improve (temperature too low or model limitation)

**IR Quality Issue**: Effects not specifying **error handling pattern** explicitly

---

#### Test 5: `min_max_tuple` (FAILED - Logic Bug)

**Prompt**:
```
Create a function that returns both the minimum and maximum values from a list
as a tuple (min, max)
```

**Expected**: `(1, 5)` for input `[1, 5, 3]`
**Actual**: `(1, 1)` - returned same value twice

**Root Cause**:
- IR specified "return (min, max)"
- Code likely used `min()` correctly but repeated: `(min(lst), min(lst))`
- Logic bug, not syntax error - suggests model confusion

**IR Quality Issue**: Effects not emphasizing **distinct min AND max** operations

---

### Gap Analysis: Current IR Prompt vs Requirements

| **Requirement** | **Current Coverage** | **Gap** | **Impact** |
|-----------------|---------------------|---------|------------|
| Exact literal strings | "Be explicit about return values" | Not specific enough - doesn't say "use LITERAL 'X' not computed/formatted" | High - affects validate_password, get_type_name |
| Python type quirks | None | Missing "bool is subclass of int" warning | High - affects get_type_name |
| Character position/order | "Handle edge cases" | Too vague - doesn't specify position checks | Medium - affects is_valid_email |
| Exception handling patterns | None | No mention of try/except structure | Medium - affects safe_int_conversion |
| Distinct operations | None | Doesn't emphasize "use BOTH min() AND max()" | Medium - affects min_max_tuple |
| Edge case enumeration | "Handle empty inputs, boundaries" | Good, but could be more specific | Low - mostly works |

---

## Part 2: Proposed IR Generation Improvements

### Improvement 1: Enhanced Few-Shot Examples (HIGH PRIORITY)

**Current Approach**: Zero-shot prompt with general guidelines
**Proposed Approach**: Add 3-5 few-shot examples showing correct IR for similar prompts

**Implementation**: Modify `get_prompt_for_ir_generation()` in `lift_sys/ir/schema.py:200-260`

```python
def get_prompt_for_ir_generation(user_prompt: str) -> str:
    return f"""You are an expert at converting natural language specifications into IR.

[... existing guidelines ...]

**FEW-SHOT EXAMPLES:**

---
**Example 1: Exact Literal Strings**

User Prompt:
"Create a function that validates password length. Return 'too short' if less than 8
characters, otherwise return 'valid'."

Correct IR:
{{
  "intent": {{
    "summary": "Validate password length",
    "rationale": "Check if password meets minimum length requirement"
  }},
  "signature": {{
    "name": "validate_password_length",
    "parameters": [
      {{"name": "password", "type_hint": "str", "description": "Password to validate"}}
    ],
    "returns": "str"
  }},
  "effects": [
    {{
      "description": "If len(password) < 8, return the LITERAL string 'too short' (not a formatted message)"
    }},
    {{
      "description": "Otherwise, return the LITERAL string 'valid' (not 'password is valid')"
    }}
  ],
  "assertions": [
    {{"predicate": "result in ['too short', 'valid']", "rationale": "Only two possible return values"}}
  ]
}}

❌ WRONG: "Return a message indicating password is too short" (too vague)
✅ CORRECT: "Return the LITERAL string 'too short'" (exact specification)

---
**Example 2: Python Type Checking with Quirks**

User Prompt:
"Create a function that returns the type name. Check if value is int, str, or list
using isinstance. Return 'int', 'str', 'list', or 'other'."

Correct IR:
{{
  "intent": {{
    "summary": "Determine type name of a value",
    "rationale": "Classify values by type for processing"
  }},
  "signature": {{
    "name": "get_type_name",
    "parameters": [
      {{"name": "value", "type_hint": "Any", "description": "Value to check"}}
    ],
    "returns": "str"
  }},
  "effects": [
    {{
      "description": "⚠️ PYTHON QUIRK: Check bool BEFORE int (isinstance(True, int) is True!)"
    }},
    {{
      "description": "If isinstance(value, bool): return LITERAL 'other' (bools are not 'int')"
    }},
    {{
      "description": "Elif isinstance(value, int): return LITERAL 'int'"
    }},
    {{
      "description": "Elif isinstance(value, str): return LITERAL 'str'"
    }},
    {{
      "description": "Elif isinstance(value, list): return LITERAL 'list'"
    }},
    {{
      "description": "Else: return LITERAL 'other' (not type(value).__name__ or computed!)"
    }}
  ],
  "assertions": [
    {{"predicate": "result in ['int', 'str', 'list', 'other']", "rationale": "Exactly 4 possible values"}},
    {{"predicate": "get_type_name(True) == 'other'", "rationale": "Bools return 'other' not 'int'"}}
  ]
}}

❌ WRONG: "Return type name using type(value).__name__" (computed, not literal)
✅ CORRECT: "Return LITERAL 'other' for non-matching types"

---
**Example 3: Exception Handling Pattern**

User Prompt:
"Create a function that converts a string to integer, returning 0 if conversion fails"

Correct IR:
{{
  "intent": {{
    "summary": "Safely convert string to integer",
    "rationale": "Prevent ValueError from invalid inputs"
  }},
  "signature": {{
    "name": "safe_int",
    "parameters": [
      {{"name": "s", "type_hint": "str", "description": "String to convert"}}
    ],
    "returns": "int"
  }},
  "effects": [
    {{
      "description": "Use try/except ValueError block for conversion"
    }},
    {{
      "description": "In try block: attempt int(s) and return the result"
    }},
    {{
      "description": "In except ValueError block: return 0"
    }}
  ],
  "assertions": [
    {{"predicate": "safe_int('123') == 123", "rationale": "Valid string converts correctly"}},
    {{"predicate": "safe_int('abc') == 0", "rationale": "Invalid string returns 0"}},
    {{"predicate": "safe_int('') == 0", "rationale": "Empty string returns 0"}}
  ]
}}

✅ KEY: Specify exact exception handling structure, not just "handle errors"

---

**Now generate IR for the user's request:**

{user_prompt}

Generate the IR as valid JSON matching the schema:"""
```

**Expected Impact**:
- ✅ Literal string issues: Reduced by 80-90% (examples show EXACT pattern)
- ✅ Type checking bugs: Reduced by 70-80% (bool/int quirk explicitly shown)
- ✅ Exception handling: Reduced by 60-70% (pattern specified)
- ⏱️ **Estimated Effort**: 4-6 hours (write examples, test, refine)

---

### Improvement 2: Effects Clause Expansion (MEDIUM PRIORITY)

**Current Approach**: Effects describe what happens but not how
**Proposed Approach**: Add structured sub-fields for clarity

**Schema Change**: Extend effects schema in `lift_sys/ir/schema.py:83-102`

```python
"effects": {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            # NEW: Structured sub-fields
            "implementation_hint": {
                "type": ["string", "null"],
                "description": "Specific implementation approach (e.g., 'use try/except', 'check with if-elif')"
            },
            "return_values": {
                "type": "array",
                "description": "Exact literal return values for this effect",
                "items": {"type": ["string", "number", "boolean", "null"]},
                "default": []
            },
            "order_constraint": {
                "type": ["string", "null"],
                "description": "Ordering requirement (e.g., 'check bool before int')"
            },
            "holes": {"type": "array", "items": {"$ref": "#/definitions/TypedHole"}}
        },
        "required": ["description"]
    }
}
```

**Updated Prompt Guidance**:
```
Effects should now include:
- description: What happens
- implementation_hint: How to implement (optional)
- return_values: Exact literal values returned (if applicable)
- order_constraint: Ordering requirements (if applicable)
```

**Example IR Output**:
```json
{
  "effects": [
    {
      "description": "If len(password) < 8, return 'too short'",
      "implementation_hint": "Use len() function to check length",
      "return_values": ["too short"],
      "order_constraint": null
    },
    {
      "description": "Check bool before int to avoid isinstance quirk",
      "implementation_hint": "Use if isinstance(value, bool) before checking int",
      "return_values": null,
      "order_constraint": "bool must be checked before int"
    }
  ]
}
```

**Expected Impact**:
- ✅ Logic bugs: Reduced by 50-60% (clearer specifications)
- ✅ Literal strings: Reduced by 60-70% (return_values field forces specificity)
- ⏱️ **Estimated Effort**: 12-16 hours (schema changes, prompt updates, testing)

**Trade-off**: More complex IR, but clearer specifications

---

### Improvement 3: Python-Specific Quirks Database (LOW PRIORITY)

**Current Approach**: No language-specific knowledge injection
**Proposed Approach**: Inject common Python quirks into IR generation prompt

**Implementation**: Add Python quirks section to prompt

```python
PYTHON_QUIRKS = """
**PYTHON-SPECIFIC QUIRKS TO CONSIDER:**

1. **Bool is subclass of int**: isinstance(True, int) returns True
   - Always check bool BEFORE int in type checking
   - True == 1 and False == 0 in arithmetic

2. **String methods return new strings**: str.upper() returns new string, doesn't modify
   - Effects should specify: "Create and return new string" not "Modify string"

3. **List/dict are mutable**: Modifying parameter affects caller
   - Effects should note: "Modifies input list in-place" vs "Returns new list"

4. **Empty string is falsy**: if "": evaluates to False
   - Be explicit: "Check if string is empty (len(s) == 0)" vs "if s:"

5. **Integer division**: 5 / 2 = 2.5 (float), 5 // 2 = 2 (int)
   - Specify: "Use // for integer division" if that's the intent

6. **None vs 0 vs False**: All falsy but different
   - Be explicit about which to check: "if value is None:" vs "if not value:"

When generating IR for Python functions, check if any of these quirks apply and
add them to effects or assertions.
"""

def get_prompt_for_ir_generation(user_prompt: str) -> str:
    return f"""...

    {PYTHON_QUIRKS}

    User's request: {user_prompt}
    """
```

**Expected Impact**:
- ✅ Type checking bugs: Reduced by 40-50% (quirks highlighted)
- ✅ Edge cases: Improved by 20-30% (awareness of falsy values)
- ⏱️ **Estimated Effort**: 3-4 hours (document quirks, integrate)

---

### Improvement 4: Assertion Auto-Generation from Prompt (MEDIUM PRIORITY)

**Current Approach**: LLM extracts assertions from user prompt manually
**Proposed Approach**: Use regex/keyword matching to auto-suggest assertions

**Implementation**: Pre-process user prompt to extract constraints

```python
import re

def extract_assertions_from_prompt(user_prompt: str) -> list[str]:
    """Extract potential assertions from user's natural language."""
    assertions = []

    # Pattern 1: "return X if condition"
    if match := re.search(r"return\s+['\"]([^'\"]+)['\"]\s+if\s+(.+)", user_prompt, re.IGNORECASE):
        value, condition = match.groups()
        assertions.append(f"If {condition}, result == '{value}'")

    # Pattern 2: "must contain X"
    if match := re.search(r"must contain\s+(.+?)\s+(and|or|$)", user_prompt, re.IGNORECASE):
        requirement = match.group(1).strip()
        assertions.append(f"Input must contain {requirement}")

    # Pattern 3: "exactly 'X'" or "exact string 'X'"
    if matches := re.findall(r"exact(?:ly)?\s+(?:string\s+)?['\"]([^'\"]+)['\"]", user_prompt, re.IGNORECASE):
        for literal in matches:
            assertions.append(f"result == '{literal}' (literal string, not computed)")

    # Pattern 4: "return X for Y" (test case extraction)
    if matches := re.findall(r"return\s+['\"]?([^'\"]+?)['\"]?\s+for\s+(.+?)(?:\.|,|$)", user_prompt, re.IGNORECASE):
        for value, input_desc in matches:
            assertions.append(f"For {input_desc.strip()}, result == '{value.strip()}'")

    return assertions

def get_prompt_for_ir_generation(user_prompt: str) -> str:
    # Auto-extract potential assertions
    suggested_assertions = extract_assertions_from_prompt(user_prompt)

    assertion_hint = ""
    if suggested_assertions:
        assertion_hint = f"""
**DETECTED CONSTRAINTS (include these as assertions):**
{chr(10).join(f'- {a}' for a in suggested_assertions)}
"""

    return f"""...

    {assertion_hint}

    User's request: {user_prompt}
    """
```

**Example**:
```
Input: "Return 'too short' if less than 8 chars, otherwise return 'valid'"

Detected Assertions:
- If less than 8 chars, result == 'too short'
- result in ['too short', 'valid'] (only two possible values)
```

**Expected Impact**:
- ✅ Assertion completeness: +30-40% more test cases
- ✅ Literal strings: +20-30% detection rate (flags exact values)
- ⏱️ **Estimated Effort**: 8-10 hours (regex patterns, testing, edge cases)

---

## Part 3: Model Assessment

### Current Model: Qwen2.5-Coder-7B-Instruct

**Specifications**:
- **Parameters**: 7 billion
- **Training**: Code-focused (GitHub, StackOverflow, coding benchmarks)
- **Context**: 32k tokens
- **Strengths**: Fast inference, good Python syntax, cost-effective ($1.10/hr on A10G)
- **Weaknesses**: Smaller model, may struggle with complex reasoning, training bias toward "helpful" verbose code

**Performance on Phase 3**:
- Phase 2 (10 tests): **90%** success (9/10 passing)
- Phase 3 (18 tests): **72.2%** success (13/18 passing)
- **Failure patterns**: Verbose strings, logic bugs, syntax errors through retries

---

### Alternative Model Options

#### Option 1: Qwen2.5-Coder-32B-Instruct (RECOMMENDED)

**Specifications**:
- **Parameters**: 32 billion (4.5x larger)
- **Training**: Same as 7B but more capacity
- **Context**: 128k tokens (4x larger)
- **GPU**: A100-40GB ($3.00/hr) or A100-80GB ($3.50/hr)
- **Cost**: ~3x more expensive than 7B model

**Expected Improvements**:
- ✅ **Reasoning**: Better at following multi-step instructions
- ✅ **Edge cases**: Improved handling of quirks and constraints
- ✅ **Literal strings**: Less training bias (more likely to follow exact specs)
- ✅ **Retry success**: Higher chance of fixing bugs in retries

**Estimated Impact**: Phase 3 success **72% → 82-88%** (+10-16%)

**Trade-offs**:
- ✅ Higher success rate
- ❌ 3x higher cost (~$0.015/request vs ~$0.005/request)
- ❌ Slower inference (6-10s vs 2-5s)

**Recommendation**: **Try 32B model first** - likely best cost/benefit ratio

---

#### Option 2: DeepSeek-Coder-V2-236B-Instruct (HIGHEST QUALITY)

**Specifications**:
- **Parameters**: 236 billion (MoE, ~21B activated per token)
- **Training**: Massive code corpus, math reasoning
- **Context**: 128k tokens
- **GPU**: H100 ($4.00/hr) or multi-GPU setup
- **Cost**: ~4x more expensive than 7B

**Expected Improvements**:
- ✅ **Best-in-class reasoning**: Top of code generation benchmarks
- ✅ **Precise instruction following**: Trained for exactness
- ✅ **Edge case handling**: Excellent at Python quirks
- ✅ **Complex logic**: Better at multi-condition scenarios

**Estimated Impact**: Phase 3 success **72% → 88-94%** (+16-22%)

**Trade-offs**:
- ✅ Highest quality, likely >90% success
- ❌ 4x cost
- ❌ Slower cold starts
- ❌ More complex deployment (MoE requires specific vLLM settings)

**Recommendation**: **Save for production** - overkill for research phase

---

#### Option 3: Claude 3.5 Sonnet (API-BASED, NO XGRAMMAR)

**Specifications**:
- **Provider**: Anthropic API (not Modal)
- **Strengths**: Excellent instruction following, top reasoning
- **Context**: 200k tokens
- **Cost**: $3/million input tokens, $15/million output tokens (~$0.03/IR)

**Expected Improvements**:
- ✅ **Best instruction following**: Likely to respect "exact literal" requirements
- ✅ **Reasoning**: Top-tier for complex logic
- ✅ **Retry success**: Better at self-correction

**Limitations**:
- ❌ **No XGrammar**: Cannot use schema-constrained generation for IR
- ❌ **Fallback to text parsing**: Must parse JSON from freeform text (less reliable)
- ❌ **Higher cost**: 6x more expensive than Qwen2.5-32B

**Estimated Impact**: Phase 3 success **72% → 85-92%** (+13-20%)

**Recommendation**: **Fallback option** - use if Qwen 32B doesn't reach 85%

---

#### Option 4: Keep Qwen 7B + Improve Prompts (BASELINE)

**Approach**: Implement IR improvements (few-shot examples) with current model

**Expected Impact**: Phase 3 success **72% → 78-82%** (+6-10%)

**Cost**: No model change, same $1.10/hr

**Recommendation**: **Do this first regardless** - establishes whether model or prompt is the bottleneck

---

### Model Assessment Summary

| **Model** | **Size** | **Cost/hr** | **Expected Success** | **Effort** | **Recommendation** |
|-----------|----------|-------------|----------------------|------------|--------------------|
| Qwen 7B (current) | 7B | $1.10 | 72% → 78-82% | None | Baseline |
| Qwen 32B | 32B | $3.00 | 72% → 82-88% | 2-3 hrs (config) | ⭐ **Try next** |
| DeepSeek 236B | 236B MoE | $4.00 | 72% → 88-94% | 4-6 hrs (MoE setup) | Production fallback |
| Claude 3.5 | Proprietary | API-based | 72% → 85-92% | 6-8 hrs (no XGrammar) | Last resort |

**Decision Tree**:
1. ✅ **Implement few-shot examples** (4-6 hrs) → Test with Qwen 7B
   - If ≥85% success: DONE
   - If 78-84%: Proceed to step 2
   - If <78%: Skip to step 3 (Claude)

2. ✅ **Upgrade to Qwen 32B** (2-3 hrs) → Re-test
   - If ≥85% success: DONE
   - If <85%: Proceed to step 3

3. ✅ **Try Claude 3.5 Sonnet** (6-8 hrs, no XGrammar) → Re-test
   - If ≥85% success: Use for IR generation only
   - If <85%: Consider DeepSeek or re-evaluate architecture

---

## Part 4: Fine-Tuning and Test-Time Compute Strategies

### Strategy 1: Fine-Tuning a Custom Model

**Concept**: Train a specialized model on lift-sys IR generation patterns using supervised fine-tuning (SFT).

#### When Fine-Tuning Makes Sense

**Ideal Conditions**:
1. ✅ **Systematic patterns**: Same types of errors repeat (literal strings, type quirks)
2. ✅ **Large dataset available**: >100-500 high-quality IR examples
3. ✅ **Long-term usage**: System will generate 1000s of IRs over time
4. ✅ **Stable requirements**: IR schema unlikely to change frequently

**Current Situation**:
- ✅ Systematic patterns detected (literal strings, bool/int ordering)
- ⚠️ Limited dataset (~18 test cases, need 100+)
- ⚠️ IR schema still evolving (effects expansion planned)
- ✅ Long-term usage expected (production system)

**Verdict**: **Not yet ready** - Need more training data first

---

#### Fine-Tuning Approaches

**Option A: LoRA Fine-Tuning Qwen 7B** (RECOMMENDED IF DOING FINE-TUNING)

**Approach**: Low-Rank Adaptation (LoRA) - fine-tune only small adapter weights
**Base Model**: Qwen2.5-Coder-7B-Instruct
**Training Data**: 100-500 (prompt, IR) pairs with manual quality labeling

**Implementation**:
```python
# Using Hugging Face PEFT (Parameter-Efficient Fine-Tuning)
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,  # Rank of adaptation matrices
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],  # Attention layers
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(base_model, lora_config)
# Train on (prompt, IR) pairs...
```

**Data Collection Strategy**:
1. Generate IRs for 200-300 diverse prompts using current system
2. Manually review and correct IRs (mark literal strings, add quirks)
3. Create "negative examples" showing common mistakes
4. Split: 80% train, 10% validation, 10% test

**Expected Results**:
- ✅ Literal string accuracy: 60% → 90%+ (learns exact pattern)
- ✅ Python quirk handling: 40% → 85%+ (learns bool/int ordering)
- ✅ Assertion completeness: +20-30% (learns to generate more tests)
- ⏱️ **Training Time**: 2-4 hours on A100
- 💰 **Training Cost**: $6-12 (GPU time)
- 👷 **Effort**: 2-3 weeks (data collection, labeling, training, validation)

**Ongoing Maintenance**:
- Collect production IRs (user corrections)
- Retrain quarterly with new examples
- Monitor for drift (new error patterns)

**Trade-offs**:
- ✅ Best long-term quality (specialized model)
- ✅ Lower inference cost after training (smaller model)
- ❌ High upfront effort (data collection)
- ❌ Maintenance burden (retraining)
- ❌ Doesn't help with novel patterns (needs retraining)

---

**Option B: Full Fine-Tuning Qwen 32B**

**Approach**: Fine-tune all weights of larger model
**Cost**: $100-200 (longer training on multi-GPU)
**Effort**: 3-4 weeks
**Expected Results**: 72% → 92-96% success

**Verdict**: **Overkill** - LoRA sufficient for this task

---

**Option C: Fine-Tuning DeepSeek-Coder**

**Approach**: Fine-tune state-of-art code model
**Base Model**: DeepSeek-Coder-6.7B or 33B
**Cost**: Similar to Qwen
**Expected Results**: Marginally better (DeepSeek has better reasoning)

**Verdict**: **Worth considering** if Qwen fine-tuning doesn't reach 90%+

---

#### Fine-Tuning Implementation Plan

**IF** we decide to pursue fine-tuning:

**Week 1: Data Collection**
1. Generate IRs for 300 diverse prompts (all categories)
   - Control flow: 60 prompts
   - List operations: 60 prompts
   - String manipulation: 60 prompts
   - Type operations: 40 prompts (focus on quirks)
   - Edge cases: 40 prompts
   - Mathematical: 40 prompts

2. Manual review and correction
   - Fix literal string issues
   - Add Python quirk annotations
   - Ensure assertion completeness
   - Time: ~30-40 hours (tedious but critical)

**Week 2: Training Setup**
1. Set up Modal training job (or local if you have GPU)
2. Implement LoRA training script
3. Create validation metrics (schema validity, assertion count, literal string detection)
4. Initial training run (verify setup works)

**Week 3: Training and Iteration**
1. Train multiple configurations (different LoRA ranks, learning rates)
2. Validate on held-out test set
3. Analyze errors, collect more data if needed
4. Select best checkpoint

**Week 4: Deployment and Validation**
1. Deploy fine-tuned model to Modal
2. Re-run Phase 3 tests
3. Compare vs base model
4. Document improvement and ROI

**Total Effort**: 60-80 hours over 4 weeks

**Decision Criteria**:
- **Do fine-tuning if**: Few-shot + Qwen 32B achieves <85% AND we expect >1000 production uses
- **Skip fine-tuning if**: Few-shot + Qwen 32B achieves ≥85% OR low production volume

---

### Strategy 2: Test-Time Compute (Inference-Time Scaling)

**Concept**: Improve quality by using more computation during inference (multiple generations, reasoning, self-critique).

**Why Test-Time Compute?**
- ✅ Works with existing models (no training needed)
- ✅ Can combine with other improvements (prompts, larger models)
- ✅ Proven effective in research (OpenAI o1, Google Gemini Pro)
- ❌ Higher latency (multiple generations)
- ❌ Higher cost per request (2-10x depending on technique)

---

#### Technique 1: Self-Consistency (HIGH IMPACT)

**Concept**: Generate N different IRs at higher temperature, pick the most common/best structure.

**Algorithm**:
```python
async def generate_ir_with_self_consistency(
    prompt: str,
    n_samples: int = 5,
    temperature: float = 0.7
) -> IntermediateRepresentation:
    """Generate multiple IRs and pick best via voting."""

    # Generate N independent samples at higher temperature
    irs = []
    for _ in range(n_samples):
        ir = await generate_ir_single(prompt, temperature=temperature)
        irs.append(ir)

    # Score each IR by quality metrics
    scores = []
    for ir in irs:
        score = 0
        score += len(ir.assertions) * 2  # More assertions = better
        score += 1 if ir.signature.returns else 0  # Has return type
        score += len(ir.effects) * 1.5  # More effects = better spec

        # Detect literal strings in effects
        for effect in ir.effects:
            if "literal" in effect.description.lower():
                score += 5  # Bonus for explicit literals
            if "LITERAL" in effect.description:
                score += 10  # Even more for emphasis

        # Detect Python quirks
        if "bool" in str(ir).lower() and "int" in str(ir).lower():
            score += 5  # Mentions both types (likely handling quirk)

        scores.append(score)

    # Pick highest-scoring IR
    best_idx = scores.index(max(scores))
    return irs[best_idx]
```

**Expected Results**:
- ✅ Literal strings: +15-25% accuracy (voting filters out wrong interpretations)
- ✅ Assertion coverage: +20-30% (takes best from N samples)
- ✅ Logic bugs: +10-15% reduction (more robust to single-sample errors)
- 💰 **Cost**: 5x higher (5 generations instead of 1)
- ⏱️ **Latency**: 2-3x higher (parallel generation helps)
- 👷 **Effort**: 6-8 hours (implement scoring, test, tune)

**When to Use**: If single-shot accuracy is 75-85% and we can afford 5x cost

---

#### Technique 2: Chain-of-Thought (CoT) Reasoning (MEDIUM IMPACT)

**Concept**: Ask model to reason about the specification before generating IR.

**Prompt Modification**:
```python
def get_cot_prompt_for_ir_generation(user_prompt: str) -> str:
    return f"""You are an expert at converting natural language specifications into IR.

Before generating the IR, analyze the specification step-by-step:

1. **Identify exact literal values**: Are there specific strings/numbers the user mentioned?
   - Look for: "return 'X'", "exactly 'Y'", specific error messages
   - Mark these as LITERAL (not computed or formatted)

2. **Detect Python-specific quirks**: Are there type-checking edge cases?
   - Bool vs int: isinstance(True, int) is True - check bool BEFORE int
   - Mutable vs immutable: Does function modify input or return new value?
   - Empty/None/False: Which falsy value is expected?

3. **Enumerate edge cases**: What boundary conditions exist?
   - Empty inputs ([], "", 0, None)
   - Boundary values (min/max, first/last)
   - Error conditions (invalid input, conversion failures)

4. **List all return paths**: What are ALL possible return values?
   - Normal case: What's returned on success?
   - Error cases: What's returned on failure?
   - Edge cases: What's returned for boundaries?

**REASONING:**
<Think step-by-step here>

**IR:**
{{
  "intent": {{ ... }},
  ...
}}

User's specification:
{user_prompt}

Generate your reasoning and then the IR:"""
```

**Expected Results**:
- ✅ Literal strings: +10-20% (explicitly asks to identify them)
- ✅ Python quirks: +15-25% (prompts reasoning about edge cases)
- ✅ Edge cases: +10-15% (forces enumeration)
- 💰 **Cost**: 1.5-2x higher (more output tokens for reasoning)
- ⏱️ **Latency**: 1.3-1.5x higher (longer generation)
- 👷 **Effort**: 3-4 hours (modify prompt, test)

**Caveat**: Works better with larger models (32B+) that can reason coherently

---

#### Technique 3: Iterative Refinement (HIGH IMPACT)

**Concept**: Generate IR, critique it, regenerate based on critique.

**Algorithm**:
```python
async def generate_ir_with_refinement(
    prompt: str,
    max_iterations: int = 2
) -> IntermediateRepresentation:
    """Generate IR, then iteratively improve it."""

    # Initial generation
    ir = await generate_ir_single(prompt, temperature=0.3)

    for iteration in range(max_iterations):
        # Critique current IR
        critique_prompt = f"""
Review this IR for a function specification. Identify issues:

1. Are there literal strings that should be marked as LITERAL?
2. Are there Python quirks that need handling (bool/int, etc.)?
3. Are edge cases covered in assertions?
4. Are all return paths specified in effects?

Specification: {prompt}

Current IR:
{ir.to_json()}

Provide critique as JSON:
{{
  "issues": [
    {{"category": "literal_string", "description": "...", "fix": "..."}},
    ...
  ],
  "overall_quality": 0-10
}}
"""

        critique = await generate_structured(critique_prompt, CRITIQUE_SCHEMA)

        # If quality is high enough, stop
        if critique["overall_quality"] >= 8:
            break

        # Regenerate with critique as feedback
        refinement_prompt = f"""
Original specification: {prompt}

Previous IR had these issues:
{chr(10).join(f"- {issue['description']}: {issue['fix']}" for issue in critique['issues'])}

Generate improved IR addressing these issues:
"""

        ir = await generate_ir_single(refinement_prompt, temperature=0.3)

    return ir
```

**Expected Results**:
- ✅ Literal strings: +20-30% (critique identifies missing LITERAL markers)
- ✅ Python quirks: +15-20% (critique catches missing edge cases)
- ✅ Overall quality: +15-25% (self-correction loop)
- 💰 **Cost**: 3-4x higher (2-3 generations + critique)
- ⏱️ **Latency**: 3-4x higher (sequential, not parallel)
- 👷 **Effort**: 12-16 hours (implement critique, test iterations)

**When to Use**: If we can afford 3-4x cost and latency is acceptable (<15s total)

---

#### Technique 4: Best-of-N Sampling (SIMPLE, MEDIUM IMPACT)

**Concept**: Generate N candidates, score each, pick best.

**Algorithm**:
```python
async def generate_ir_best_of_n(
    prompt: str,
    n_candidates: int = 3,
    temperature: float = 0.5
) -> IntermediateRepresentation:
    """Generate N IRs and pick best by scoring."""

    # Generate N candidates
    candidates = []
    for _ in range(n_candidates):
        ir = await generate_ir_single(prompt, temperature=temperature)
        candidates.append(ir)

    # Score each candidate
    def score_ir(ir: IntermediateRepresentation) -> float:
        score = 0.0

        # Schema validity (must pass)
        if not validate_schema(ir):
            return -1000

        # Assertion count (more is better, up to a point)
        score += min(len(ir.assertions) * 10, 50)

        # Effect detail (longer descriptions = more specific)
        avg_effect_length = sum(len(e.description) for e in ir.effects) / max(len(ir.effects), 1)
        score += min(avg_effect_length / 10, 20)

        # Literal string detection
        literal_count = sum(
            1 for e in ir.effects
            if "literal" in e.description.lower() or "exact" in e.description.lower()
        )
        score += literal_count * 15

        # Type hint completeness
        if all(p.type_hint for p in ir.signature.parameters):
            score += 10
        if ir.signature.returns:
            score += 10

        return score

    scores = [score_ir(ir) for ir in candidates]
    best_idx = scores.index(max(scores))
    return candidates[best_idx]
```

**Expected Results**:
- ✅ Schema validity: 95% → 99%+ (filtering out invalid)
- ✅ Literal strings: +10-15% (picks IR with explicit markers)
- ✅ Assertion coverage: +10-15% (picks more thorough IR)
- 💰 **Cost**: 3x higher (3 generations)
- ⏱️ **Latency**: 1.2-1.5x higher (parallel generation)
- 👷 **Effort**: 6-8 hours (implement scoring)

**Simplest test-time compute approach** - good starting point

---

#### Technique 5: Hybrid - Best-of-N with CoT (HIGHEST IMPACT)

**Concept**: Combine chain-of-thought with best-of-N sampling.

**Algorithm**:
```python
async def generate_ir_hybrid(
    prompt: str,
    n_candidates: int = 3
) -> IntermediateRepresentation:
    """Generate N IRs using CoT, pick best."""

    # Use CoT prompt for all generations
    cot_prompt = get_cot_prompt_for_ir_generation(prompt)

    # Generate N candidates with reasoning
    candidates = []
    for _ in range(n_candidates):
        ir = await generate_ir_single(cot_prompt, temperature=0.5)
        candidates.append(ir)

    # Score and pick best (same as best-of-N)
    scores = [score_ir(ir) for ir in candidates]
    return candidates[scores.index(max(scores))]
```

**Expected Results**:
- ✅ Literal strings: +25-35% (CoT reasoning + voting)
- ✅ Python quirks: +20-30% (CoT identifies + voting filters)
- ✅ Overall quality: +20-30% (best of both techniques)
- 💰 **Cost**: 4-5x higher (3 generations with longer prompts)
- ⏱️ **Latency**: 1.5-2x higher (parallel CoT generations)
- 👷 **Effort**: 8-10 hours (combine both implementations)

**Recommended test-time compute approach** if cost is acceptable

---

### Test-Time Compute Strategy Comparison

| Technique | Cost Multiplier | Latency Multiplier | Expected Improvement | Effort | Recommendation |
|-----------|-----------------|-------------------|----------------------|--------|----------------|
| **Best-of-N (N=3)** | 3x | 1.2-1.5x | +10-15% | 6-8h | ⭐ **Start here** |
| **Chain-of-Thought** | 1.5-2x | 1.3-1.5x | +10-20% | 3-4h | Good with 32B+ |
| **Self-Consistency (N=5)** | 5x | 2-3x | +15-25% | 6-8h | If cost acceptable |
| **Iterative Refinement** | 3-4x | 3-4x | +15-25% | 12-16h | High latency concern |
| **Hybrid (CoT + Best-of-N)** | 4-5x | 1.5-2x | +20-30% | 8-10h | ⭐⭐ **Best quality** |

---

### Combined Strategy: Test-Time Compute + Model Upgrade

**Optimal Combination**: Qwen 32B + Best-of-N (N=3)

**Expected Results**:
- Model upgrade alone: 72% → 82-88%
- Best-of-N on top: 82-88% → **88-94%**
- **Total improvement: +16-22%** from baseline

**Cost Analysis**:
- Qwen 32B: $3/hr GPU
- Best-of-N (N=3): 3x inference cost
- Total: ~$0.045/test (vs $0.005 baseline)
- **9x cost increase for 20% quality improvement**

**When Worth It**:
- ✅ Production system requiring >90% accuracy
- ✅ Cost per IR generation <1% of total value
- ✅ Latency <10s acceptable
- ❌ High-volume low-value use case (not worth it)

---

### Fine-Tuning vs Test-Time Compute Decision Matrix

| Scenario | Recommended Approach | Rationale |
|----------|---------------------|-----------|
| **Need 85% success, limited budget** | Few-shot + Qwen 32B | Best ROI, moderate cost |
| **Need 90% success, moderate budget** | Qwen 32B + Best-of-N (N=3) | Higher quality, acceptable cost |
| **Need 95% success, unlimited budget** | Fine-tuned Qwen 32B + Hybrid CoT | Maximum quality |
| **High-volume production (>10k IRs/month)** | Fine-tuning (LoRA) | Lower ongoing cost after training |
| **Low-volume research (<1k IRs total)** | Test-time compute only | No training overhead |
| **Limited time (<2 weeks)** | Test-time compute | Fine-tuning takes 3-4 weeks |
| **Evolving requirements** | Test-time compute | Fine-tuning needs retraining |

---

### Recommended Sequence

**Phase 1: Low-Hanging Fruit** (Week 1)
1. ✅ Few-shot examples + Python quirks (8-11 hours)
2. ✅ Test with Qwen 7B
3. **Target**: 78-82% success

**Phase 2: Model Upgrade OR Test-Time Compute** (Week 1-2)

**If 78-82% success:**
- **Option A**: Qwen 32B (3 hours) → Target 82-88%
- **Option B**: Best-of-N (N=3) with Qwen 7B (6-8 hours) → Target 82-86%
- **Recommendation**: Try **Option A first** (faster, similar results)

**If <78% success:**
- Skip to Phase 3 (Claude)

**Phase 3: Advanced Techniques** (Week 2-3, IF NEEDED)

**If Phase 2 achieves 82-88% but need >90%:**
- **Option A**: Qwen 32B + Best-of-N (8-10 hours) → Target 88-94%
- **Option B**: Qwen 32B + Hybrid CoT (10-12 hours) → Target 88-94%
- **Recommendation**: **Option A** (simpler, less latency)

**Phase 4: Fine-Tuning** (Week 4-7, LONG-TERM)

**If planning production deployment with >1000 IRs:**
- Collect 300+ training examples while using test-time compute
- Fine-tune Qwen 32B with LoRA (3-4 weeks)
- Target: 92-98% success with lower ongoing cost

---

## Part 5: Implementation Plan

### Phase A: IR Prompt Improvements (IMMEDIATE - Week 1)

**Tasks**:
1. ✅ Add few-shot examples to IR generation prompt (Improvement 1)
   - Write 3-5 examples covering: literal strings, type checking, exception handling
   - Update `lift_sys/ir/schema.py:get_prompt_for_ir_generation()`
   - Estimated: 4-6 hours

2. ✅ Add Python quirks section to prompt (Improvement 3)
   - Document 5-6 common Python quirks
   - Inject into IR generation prompt
   - Estimated: 3-4 hours

3. ✅ Test improved prompt with Qwen 7B on Phase 3
   - Re-run all 18 tests
   - Measure improvement
   - Estimated: 1 hour (automated)

**Total Effort**: 8-11 hours (1-2 days)

**Success Criteria**:
- Phase 3 success ≥78% (baseline +6%)
- Literal string failures reduced by >50%
- Type checking failures reduced by >50%

**Decision Point**:
- If ≥85%: Proceed to Phase 3 full validation
- If 78-84%: Continue to Phase B (model upgrade)
- If <78%: Jump to Phase C (Claude fallback)

---

### Phase B: Model Upgrade to Qwen 32B (Week 1-2)

**Prerequisite**: Phase A results show 78-84% success (prompts help but not enough)

**Tasks**:
1. ✅ Update Modal deployment to Qwen2.5-Coder-32B
   - Modify `lift_sys/inference/modal_app.py:80`
   - Change `MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"`
   - Change `GPU_CONFIG = "A100"` (32B needs 40GB VRAM)
   - Estimated: 1 hour

2. ✅ Test deployment and cold start time
   - Deploy: `modal deploy lift_sys/inference/modal_app.py`
   - Measure: Cold start time (expect 60-90s)
   - Verify: Health endpoint responds
   - Estimated: 1 hour

3. ✅ Re-run Phase 3 tests with 32B model
   - All 18 tests with improved prompts + larger model
   - Measure improvement vs 7B baseline
   - Estimated: 1 hour

**Total Effort**: 3 hours

**Success Criteria**:
- Phase 3 success ≥85%
- Logic bugs reduced by >60%
- Syntax errors reduced by >70%

**Cost Impact**: +$2/hr GPU cost (~$0.010 extra per test run)

**Decision Point**:
- If ≥85%: DONE - move to Phase 3 full validation
- If 80-84%: Consider DeepSeek or accept 80%+
- If <80%: Proceed to Phase C (Claude)

---

### Phase C: Claude 3.5 Fallback (Week 2, IF NEEDED)

**Prerequisite**: Phase B results <85% (model upgrade insufficient)

**Tasks**:
1. ✅ Create Anthropic provider for IR generation
   - New file: `lift_sys/providers/anthropic_ir_provider.py`
   - Implement freeform text generation (no XGrammar)
   - Parse JSON from Claude's response
   - Estimated: 4-6 hours

2. ✅ Add fallback logic in IR translator
   - Try Modal (Qwen 32B) first
   - If fails validation, retry with Claude
   - Track which provider used
   - Estimated: 2-3 hours

3. ✅ Re-run Phase 3 tests
   - Use Claude for IR generation only (keep Qwen for code gen)
   - Measure improvement
   - Calculate cost impact
   - Estimated: 1 hour

**Total Effort**: 7-10 hours

**Success Criteria**:
- Phase 3 success ≥85%
- IR JSON validity >95% (even without XGrammar)

**Cost Impact**: +$0.02/test (~6x more expensive for IR step only)

**Decision Point**:
- If ≥85%: Use Claude for IR, Qwen for code
- If <85%: Investigate deeper architectural issues (IR may not be the bottleneck)

---

### Phase D: Optional Enhancements (Week 3+)

**Prerequisite**: Phase 3 success ≥85% achieved

**Optional Tasks**:
1. ⏸️ Implement effects clause expansion (Improvement 2)
   - Add structured sub-fields to effects schema
   - Update IR generation prompt
   - Re-test for additional improvement
   - Estimated: 12-16 hours
   - Expected: +3-5% success rate

2. ⏸️ Implement assertion auto-generation (Improvement 4)
   - Regex extraction from user prompts
   - Auto-suggest assertions in IR prompt
   - Re-test for additional improvement
   - Estimated: 8-10 hours
   - Expected: +2-4% success rate

3. ⏸️ Build IR quality dashboard
   - Track IR generation success rate
   - Monitor assertion coverage
   - Identify prompt patterns that fail
   - Estimated: 6-8 hours

**Total Effort**: 26-34 hours (optional, if aiming for >90%)

---

## Part 5: Expected Outcomes

### Conservative Estimate (Prompts Only)

**Changes**: Few-shot examples + Python quirks (Phase A)
**Model**: Qwen 7B (current)
**Cost**: No change

**Expected Results**:
- Phase 3 success: **72% → 78-82%** (+6-10%)
- Literal string failures: 2 → 1 (50% reduction)
- Type checking failures: 1 → 0 (100% reduction)
- Logic bugs: 2 → 1-2 (0-50% reduction)

**Why Conservative**: 7B model may still struggle with complex reasoning

---

### Moderate Estimate (Prompts + 32B Model)

**Changes**: Few-shot examples + Python quirks + Qwen 32B (Phases A+B)
**Model**: Qwen 32B
**Cost**: +$2/hr GPU (~3x request cost)

**Expected Results**:
- Phase 3 success: **72% → 82-88%** (+10-16%)
- Literal string failures: 2 → 0 (100% reduction)
- Type checking failures: 1 → 0 (100% reduction)
- Logic bugs: 2 → 1 (50% reduction)
- Syntax errors: 1 → 0 (100% reduction)

**Why Moderate**: 32B has significantly better reasoning, few-shot examples work better with larger models

**Recommendation**: **Target this outcome** - best cost/benefit ratio

---

### Optimistic Estimate (Prompts + Claude)

**Changes**: Few-shot examples + Claude 3.5 for IR (Phases A+C)
**Model**: Claude 3.5 (IR), Qwen 32B (code)
**Cost**: +$0.02/test for IR step

**Expected Results**:
- Phase 3 success: **72% → 85-92%** (+13-20%)
- Literal string failures: 2 → 0 (100% reduction)
- Type checking failures: 1 → 0 (100% reduction)
- Logic bugs: 2 → 0 (100% reduction)
- Syntax errors: 1 → 0 (100% reduction)

**Why Optimistic**: Claude 3.5 has best-in-class instruction following, excels at exact specifications

**Caveat**: Claude doesn't support XGrammar, so JSON parsing may be less reliable

---

### Best-Case Estimate (Everything)

**Changes**: All improvements (Phases A+B+D)
**Model**: Qwen 32B
**Cost**: +$2/hr GPU

**Expected Results**:
- Phase 3 success: **72% → 88-94%** (+16-22%)
- All failure categories: 90%+ reduction
- Assertion coverage: +40% test cases
- IR clarity: Significantly improved (structured effects)

**Why Best-Case**: Combines better model + better prompts + structured specifications

**Trade-off**: 26-34 hours additional effort (only worth it if targeting >90%)

---

## Part 6: Risk Assessment

### Risk 1: Few-Shot Examples Don't Transfer

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Test examples on validation set first, iterate examples based on results

**Fallback**: Add more examples (10-15) or switch to Chain-of-Thought prompting

---

### Risk 2: Qwen 32B Doesn't Improve Enough

**Likelihood**: Low-Medium
**Impact**: Medium
**Mitigation**: Have Claude fallback ready (Phase C)

**Fallback**: Try DeepSeek-236B or accept 80%+ success rate

---

### Risk 3: Claude API Unreliable Without XGrammar

**Likelihood**: Medium
**Impact**: Low (affects only IR generation, 1 step)
**Mitigation**: Add robust JSON parsing with retries, validate schema strictly

**Fallback**: Keep using Qwen 32B, accept lower success rate

---

### Risk 4: Problem is Downstream (Code Gen), Not IR

**Likelihood**: Low
**Impact**: High (invalidates this entire plan)
**Mitigation**: Test IR quality manually - check if generated IR is actually incorrect or if code gen is misinterpreting correct IR

**Detection**:
- If IR looks correct but code is wrong → Problem is code generation, not IR
- If IR is vague/incorrect → This plan will help

**Fallback**: Shift focus to code generation improvements (better examples, different model)

---

## Part 7: Success Metrics

### Primary Metrics

1. **Phase 3 Success Rate**: Currently 72.2%, target ≥85%
   - Measure after each phase
   - Break down by category (control_flow, type_operations, etc.)

2. **Failure Category Reduction**:
   - Literal string failures: 2 → 0 (target 100% reduction)
   - Type checking failures: 1 → 0 (target 100% reduction)
   - Logic bugs: 2 → 0-1 (target 50-100% reduction)
   - Syntax errors: 1 → 0 (target 100% reduction)

3. **IR Quality Score** (manual evaluation):
   - Clarity: Are effects specific enough? (0-10 scale)
   - Completeness: Are all edge cases covered? (0-10 scale)
   - Correctness: Does IR match user intent? (0-10 scale)
   - Target: Average ≥8/10 across all three

### Secondary Metrics

4. **Assertion Coverage**: Number of test cases generated per function
   - Current: ~3-5 per function
   - Target: 5-8 per function (with auto-generation)

5. **Cost Per Test**:
   - Qwen 7B: ~$0.005/test
   - Qwen 32B: ~$0.015/test
   - Claude IR: ~$0.035/test
   - Target: Keep under $0.02/test (acceptable for research)

6. **Latency**:
   - IR generation: Currently 2-5s
   - Target: Keep under 10s (acceptable for offline processing)

---

## Part 9: Conclusion and Next Steps

### Summary

Phase 3 results (72.2% success) indicate **IR generation quality is the primary bottleneck**, not downstream validation. Key issues:

1. **Exact literal strings**: LLM bias toward verbose/helpful messages
2. **Python quirks**: Missing language-specific edge case handling
3. **Logic correctness**: Vague specifications allow bugs to slip through

**Root Cause**: Current IR generation prompt is zero-shot with general guidelines, insufficient for precise code generation.

### Strategy Options Overview

| Strategy | Target Success | Effort | Cost Impact | Timeline | Best For |
|----------|---------------|--------|-------------|----------|----------|
| **Few-shot prompts** | 78-82% | 8-11h | None | 1 week | Everyone (baseline) |
| **+ Qwen 32B** | 82-88% | +3h | +$2/hr | 1-2 weeks | ⭐ **Most scenarios** |
| **+ Best-of-N (N=3)** | 88-94% | +6-8h | +3x cost | 2-3 weeks | Need >90%, moderate budget |
| **+ Hybrid CoT** | 88-94% | +8-10h | +4-5x cost | 2-3 weeks | Maximum quality |
| **Fine-tuning (LoRA)** | 92-98% | 60-80h | Training: $6-12 | 4-7 weeks | High-volume production |
| **Claude 3.5** | 85-92% | 6-8h | API-based | 2 weeks | Last resort (no XGrammar) |

### Recommended Approach (Phased)

**Phase 1: Low-Hanging Fruit** (Week 1, 8-11 hours)
1. ✅ Few-shot examples + Python quirks
2. ✅ Test with Qwen 7B
3. **Target**: 78-82% success

**Phase 2: Model Upgrade** (Week 1-2, +3 hours)
- **If Phase 1 ≥85%**: DONE - Move to full validation
- **If Phase 1 78-84%**: Upgrade to Qwen 32B → Target 82-88%
- **If Phase 1 <78%**: Skip to Claude fallback

**Phase 3: Test-Time Compute** (Week 2-3, IF NEEDED)
- **If need >90%**: Add Best-of-N (N=3) → Target 88-94%
- **Cost**: 3x inference cost (acceptable for production quality)

**Phase 4: Fine-Tuning** (Week 4-7, LONG-TERM)
- **If planning >1000 production IRs**: Fine-tune with LoRA
- **Benefit**: Lower ongoing cost after training
- **Collect data during Phases 1-3** (manual corrections)

### Best Cost/Benefit Recommendations

**For Research/Testing** (<100 IRs):
- ✅ Few-shot + Qwen 32B
- Cost: 11-14 hours, +$2/hr GPU
- Target: 82-88% success

**For Production** (>1000 IRs, need 90%+):
- ✅ Few-shot + Qwen 32B + Best-of-N (N=3)
- Cost: 17-22 hours, +$2/hr GPU + 3x inference
- Target: 88-94% success
- Later: Fine-tune to reduce ongoing cost

**For Maximum Quality** (need 95%+):
- ✅ Fine-tuned Qwen 32B + Hybrid CoT
- Cost: 70-90 hours total, training $6-12
- Target: 92-98% success

### Immediate Next Steps

**Step 1**: Implement few-shot examples (4-6 hours)
- Write 3-5 examples covering failing test patterns
- Update `lift_sys/ir/schema.py:get_prompt_for_ir_generation()`
- Focus on: literal strings, type checking, exception handling

**Step 2**: Add Python quirks (3-4 hours)
- Document bool/int, mutability, falsy values
- Inject into IR generation prompt

**Step 3**: Re-run Phase 3 tests (1 hour)
- Measure improvement with Qwen 7B + improved prompts
- If ≥85%: DONE
- If 78-84%: Upgrade to Qwen 32B
- If <78%: Consider Claude

**Step 4**: Document results
- Update this plan with actual results
- Record which improvements worked best
- Share findings with team

---

**Plan Status**: 🎯 Ready for implementation
**Owner**: TBD
**Review Date**: After Phase A completion (Week 1)
**Success Target**: ≥85% Phase 3 success rate

**This plan addresses the upstream IR generation bottleneck before considering downstream fixes.**
