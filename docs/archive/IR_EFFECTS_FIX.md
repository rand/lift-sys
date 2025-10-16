# IR Effects Fix: Enforcing Logic Correctness Through Operational Semantics

**Date**: October 15, 2025
**Status**: ✅ Implemented, Testing in Progress

## The Problem

### Initial State
- **Compilation Rate**: 100% ✅
- **Execution Success**: 60-80% ❌
- **Root Cause**: IR Effects were not being used during code generation

### What Was Missing

The code generation process was only using:
1. **Intent Summary** - High-level "what" the function should do
2. **Signature** - Parameter names and return types
3. **Assertions** - Logical constraints and preconditions

But **critically missing**:
4. **Effects** - Step-by-step operational semantics (the "how")

### User Feedback

> "a huge part of the point of using the IR to guide constrained parallel speculative decoding is to really enforce logic correctness in the generated code – we need to do better than 80%"

The user identified that the IR should be **CONSTRAINING** the LLM generation to enforce logic correctness, not just guiding it with high-level intent.

## The Solution

### What Are Effects?

**Effects** in the IR describe the operational semantics - the ordered sequence of operations the function must perform:

```python
@dataclass(slots=True)
class EffectClause:
    description: str  # Step-by-step operation description
    holes: list[TypedHole] = field(default_factory=list)
    provenance: Provenance | None = None
```

**Example** - For `find_index(lst, value)`:
1. "Iterate through the list using enumerate to get index and item pairs"
2. "Check if current item equals the target value"
3. "If match found, return the index immediately"
4. "After loop completes, return -1 to indicate value not found"

These effects specify:
- **What** operations to perform
- **In what order** they should occur
- **What** the operational semantics must preserve

### Implementation Changes

#### 1. Extract Effects from IR

**File**: `lift_sys/codegen/xgrammar_generator.py:153-155`

```python
# Extract effects as ordered implementation steps
# Effects describe the operational semantics - the "how" not just the "what"
effects = [effect.description for effect in ir.effects]
```

#### 2. Pass Effects to Prompt Generation

**File**: `lift_sys/codegen/xgrammar_generator.py:157-163`

```python
# Get generation prompt with effects to constrain the implementation
prompt = get_prompt_for_code_generation(
    ir_summary=ir.intent.summary,
    signature=structure["signature"],
    constraints=constraints,
    effects=effects if effects else None,  # Now included!
)
```

#### 3. Update Prompt Template

**File**: `lift_sys/codegen/code_schema.py:158-163, 176-187`

Added `effects` parameter and implementation steps section:

```python
def get_prompt_for_code_generation(
    ir_summary: str,
    signature: str,
    constraints: list[str],
    effects: list[str] | None = None  # New parameter
) -> str:
```

When effects are provided, the prompt now includes:

```
Implementation Steps (MUST FOLLOW IN ORDER):
---------------------------------------------
  1. [First effect description]
  2. [Second effect description]
  ...

IMPORTANT: Your implementation MUST follow these steps in the exact order specified.
Each step corresponds to an operation the function should perform. Do not skip steps
or reorder them. The effects describe the operational semantics that must be preserved.
```

#### 4. Strengthen Requirements

**File**: `lift_sys/codegen/code_schema.py:205`

Added explicit requirement:

```
4. STRICTLY follow the implementation steps if provided (they are NOT optional)
```

## How This Enforces Correctness

### Before: Unconstrained Logic
```
LLM Input:
- Purpose: "Find index of value in list"
- Signature: find_index(lst: list[int], value: int) -> int

LLM Output: *guesses* the implementation
- Might use wrong parameter order
- Might use wrong return values
- Might use wrong algorithm
```

### After: Constrained by Effects
```
LLM Input:
- Purpose: "Find index of value in list"
- Signature: find_index(lst: list[int], value: int) -> int
- Implementation Steps:
  1. Iterate through list using enumerate
  2. Check if item equals target value
  3. Return index if match found
  4. Return -1 after loop completes

LLM Output: *must follow* the specified steps
- Forced to use enumerate
- Forced to check equality
- Forced to return correct values
- Forced to use correct control flow
```

## The Fundamental Principle

**IR + XGrammar = Constrained Generation**

The IR doesn't just describe **what** the code should do - it describes **how** it should do it through effects. XGrammar then constrains the generation to follow those operational semantics.

This is the core purpose of the system:
- **IR**: Captures operational semantics as effects
- **XGrammar**: Enforces schema-valid output structure
- **Effects**: Constrain the logic to match the IR's operational semantics

Together, they enforce **logic correctness** through constrained generation.

## Expected Impact

### Before Fix
- Compilation: 100%
- Execution: 60-80%
- Logic correctness: Unconstrained (LLM guesses)

### After Fix
- Compilation: 100% (unchanged)
- Execution: **Expected >85-90%** (testing in progress)
- Logic correctness: **Constrained by IR effects**

### Why This Should Help

1. **Eliminates guesswork** - LLM no longer guesses the algorithm
2. **Enforces ordering** - Steps must be followed in sequence
3. **Preserves semantics** - Operational semantics from IR are preserved
4. **Matches intent** - Generated code matches the IR's operational description

## Testing

**Current**: Running Phase 2 tests (10 comprehensive tests)
**Previous Results**: 60-80% execution success
**Expected**: Significant improvement beyond 80%

**Previously Failing Tests**:
1. `find_index` - Wrong parameter order/logic
2. `get_type_name` - Wrong return string format
3. `factorial` - Returned None instead of values
4. `clamp_value` - Returned None for most cases

These failures were due to LLM choosing wrong logic. With effects constraining the generation, these should now pass.

## Next Steps

1. ✅ Implement IR effects extraction
2. ✅ Update prompt generation to include effects
3. ✅ Commit and push changes
4. ⏳ Validate with Phase 2 tests
5. ⏳ Document results
6. ⏳ If successful, proceed to Phase 3

## Conclusion

This fix addresses the fundamental architectural issue: the IR was designed to constrain generation through operational semantics (effects), but we weren't using them. Now that effects are included in the prompt and emphasized as mandatory steps, the LLM generation is properly constrained by the IR.

This is exactly what the user was pointing out - we need to **leverage the IR to enforce logic correctness**, not just hope the LLM generates correct code.
