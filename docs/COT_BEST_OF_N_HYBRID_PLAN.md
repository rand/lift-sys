# Chain-of-Thought + Best-of-N Hybrid Plan

**Status**: 📋 **READY TO IMPLEMENT** - Use if Best-of-N alone doesn't reach 90%+
**Created**: October 16, 2025
**Priority**: Medium (defer until after Best-of-N testing)

---

## Executive Summary

This plan combines two test-time compute techniques for maximum IR generation quality:

1. **Chain-of-Thought (CoT)**: Prompt model to reason about specification before generating IR
2. **Best-of-N**: Generate N candidates with CoT, pick best via scoring

**Expected Improvement**: +20-30% over baseline (72% → 92-100%)

**Trade-offs**:
- ✅ Highest quality (best test-time compute approach)
- ❌ 4-5x cost (3 candidates × longer CoT prompts)
- ⏱️ 1.5-2x latency (parallel generation mitigates)

---

## Part 1: Chain-of-Thought Prompting

### CoT Prompt Design

**Goal**: Force model to explicitly reason about:
1. Exact literal values mentioned
2. Python-specific quirks
3. Edge cases and boundaries
4. All return paths

**Implementation**:

```python
def get_cot_prompt_for_ir_generation(user_prompt: str) -> str:
    """
    Generate a Chain-of-Thought prompt for IR generation.

    Instructs model to think step-by-step before generating the IR.
    """
    return f"""You are an expert at converting natural language specifications into formal intermediate representations (IR).

**IMPORTANT**: Before generating the IR, you MUST analyze the specification step-by-step.

## Step 1: Identify Exact Literal Values

Look for specific strings, numbers, or values the user explicitly mentioned:
- "return 'X'" → Mark 'X' as LITERAL (not computed or formatted)
- "exactly 'Y'" → Mark 'Y' as EXACT literal
- "the string 'Z'" → Mark 'Z' as literal

**Critical**: If a function must return a specific string, it must be a LITERAL string in the code, not computed via type(value).__name__ or str(type(value)) or any other dynamic method.

## Step 2: Detect Python-Specific Quirks

Check for language-specific edge cases that require special handling:

**Bool vs Int Quirk**:
- In Python, isinstance(True, int) returns True (bool is subclass of int)
- If checking both bool and int types, MUST check bool BEFORE int
- Example: isinstance(value, bool) must come before isinstance(value, int)

**Mutable vs Immutable**:
- Lists, dicts, sets: mutable (function can modify in-place or return new)
- Strings, tuples, numbers: immutable (must return new value)
- Specify which approach in effects

**Falsy Values**:
- Empty string "" vs None vs 0 vs False - all are falsy but different
- Be explicit about which to check: "if value is None:" vs "if not value:"

**Division**:
- / returns float (5/2 = 2.5)
- // returns int (5//2 = 2)
- Specify which one is intended

## Step 3: Enumerate Edge Cases

List ALL boundary conditions and special cases:

**Empty inputs**:
- Empty list []
- Empty string ""
- Zero 0
- None

**Boundary values**:
- First/last element
- Min/max values
- Exact threshold (e.g., "8 characters" → check len() == 8, < 8, > 8)

**Error conditions**:
- Invalid input (can't convert, wrong type)
- Missing data (None, not found)
- Out of range

## Step 4: List ALL Return Paths

Enumerate every possible return statement:

**Success path**: What's returned on successful operation?
**Error paths**: What's returned on each error condition?
**Edge cases**: What's returned for boundary conditions?

**CRITICAL**: Never rely on implicit None returns. Every code path must have an explicit return statement specified in effects.

---

## YOUR REASONING

Please write your step-by-step analysis here before generating the IR:

**Step 1 - Literal Values**:
<List all exact literals mentioned>

**Step 2 - Python Quirks**:
<Identify any quirks that apply>

**Step 3 - Edge Cases**:
<List all edge cases to handle>

**Step 4 - Return Paths**:
<Enumerate all return statements>

---

## GENERATED IR

Now, based on your reasoning above, generate the IR as valid JSON:

**User's Specification**:
{user_prompt}

**JSON IR**:
"""
```

---

### Example CoT Reasoning

**Prompt**: "Create a function that validates password length. Return 'too short' if less than 8 characters, otherwise return 'valid'."

**Expected CoT Reasoning**:

```
**Step 1 - Literal Values**:
- 'too short' → LITERAL string (user specified exact value)
- 'valid' → LITERAL string (user specified exact value)

**Step 2 - Python Quirks**:
- None apply (no type checking, no mutable data structures)

**Step 3 - Edge Cases**:
- Empty string "" → len("") = 0 < 8 → 'too short'
- Exactly 8 characters → len() = 8, not < 8 → 'valid'
- Very long passwords → len() >> 8 → 'valid'

**Step 4 - Return Paths**:
1. If len(password) < 8: return LITERAL 'too short'
2. Else: return LITERAL 'valid'

Total: 2 return paths, both explicit
```

**Generated IR** (with reasoning embedded):

```json
{
  "intent": {
    "summary": "Validate password meets minimum length requirement",
    "rationale": "Ensure passwords are at least 8 characters for security"
  },
  "signature": {
    "name": "validate_password_length",
    "parameters": [
      {"name": "password", "type_hint": "str", "description": "Password to validate"}
    ],
    "returns": "str"
  },
  "effects": [
    {
      "description": "If len(password) < 8, return the LITERAL string 'too short' (not 'Password is too short' or any formatted message)"
    },
    {
      "description": "Otherwise (len(password) >= 8), return the LITERAL string 'valid'"
    }
  ],
  "assertions": [
    {"predicate": "result in ['too short', 'valid']", "rationale": "Only two possible return values"},
    {"predicate": "validate_password_length('') == 'too short'", "rationale": "Empty password is too short"},
    {"predicate": "validate_password_length('12345678') == 'valid'", "rationale": "Exactly 8 chars is valid"}
  ]
}
```

---

## Part 2: CoT + Best-of-N Integration

### Hybrid Translator Implementation

**File**: `lift_sys/forward_mode/cot_best_of_n_translator.py`

```python
"""Chain-of-Thought + Best-of-N hybrid IR translator."""

from __future__ import annotations

import asyncio

from ..ir.models import IntermediateRepresentation
from ..providers.base import BaseProvider
from .best_of_n_translator import BestOfNIRTranslator


def get_cot_prompt_for_ir_generation(user_prompt: str) -> str:
    """Generate CoT prompt (full implementation as shown above)."""
    # ... (full prompt from above)
    pass


class CoTBestOfNTranslator:
    """
    Hybrid translator combining Chain-of-Thought reasoning with Best-of-N sampling.

    This is the highest-quality test-time compute approach:
    1. Each candidate uses CoT reasoning to think before generating
    2. N candidates are generated in parallel
    3. Best candidate selected via quality scoring

    Cost: 4-5x baseline (N candidates × longer CoT prompts)
    Expected improvement: +20-30% over baseline
    """

    def __init__(
        self,
        provider: BaseProvider,
        n_candidates: int = 3,
        temperature: float = 0.5,
    ):
        """
        Initialize CoT + Best-of-N translator.

        Args:
            provider: LLM provider
            n_candidates: Number of candidates to generate (default: 3)
            temperature: Sampling temperature for diversity (default: 0.5)
        """
        self.provider = provider
        self.n_candidates = n_candidates
        self.temperature = temperature

        # Use Best-of-N translator as base
        self.best_of_n = BestOfNIRTranslator(
            provider=provider,
            n_candidates=n_candidates,
            temperature=temperature,
        )

    async def translate(
        self,
        prompt: str,
        language: str = "python",
        max_retries: int = 1,
    ) -> IntermediateRepresentation:
        """
        Translate using CoT reasoning + Best-of-N sampling.

        Args:
            prompt: User's natural language description
            language: Target programming language
            max_retries: Number of retries per candidate

        Returns:
            Best IntermediateRepresentation with CoT reasoning
        """
        print(f"\n🧠 CoT + Best-of-N: Generating {self.n_candidates} candidates with reasoning...")

        # Enhance prompt with CoT instructions
        cot_prompt = get_cot_prompt_for_ir_generation(prompt)

        # Use Best-of-N translator with CoT prompt
        # The base translator will generate N candidates in parallel,
        # each using the CoT prompt to reason before generating IR
        ir = await self.best_of_n.translate(
            prompt=cot_prompt,  # Enhanced with CoT
            language=language,
            max_retries=max_retries,
        )

        return ir


__all__ = ["CoTBestOfNTranslator", "get_cot_prompt_for_ir_generation"]
```

---

## Part 3: Enhanced Scoring with CoT

### CoT-Aware Quality Scoring

**Extend** the scoring function to reward CoT reasoning:

```python
def _score_ir_with_cot_bonus(
    self, ir: IntermediateRepresentation, prompt: str
) -> float:
    """
    Score IR quality with bonus for CoT reasoning indicators.

    Additional scoring criteria for CoT:
    - Explicit reasoning in effects: +10 per effect with explanation
    - Multi-step logic: +5 if effects show sequential reasoning
    - Quirk awareness: +15 if Python quirks explicitly mentioned
    - Comprehensive assertions: +5 per edge case covered

    Args:
        ir: IntermediateRepresentation to score
        prompt: Original user prompt

    Returns:
        Quality score (higher is better)
    """
    # Base score (from BestOfNIRTranslator._score_ir)
    score = self._base_score_ir(ir, prompt)

    # CoT bonus: Effects with explicit reasoning
    reasoning_keywords = [
        "because",
        "to ensure",
        "this handles",
        "critical",
        "important",
        "note that",
        "must",
        "required",
    ]

    for effect in ir.effects:
        desc = effect.description.lower()
        if any(keyword in desc for keyword in reasoning_keywords):
            score += 10

    # Multi-step logic bonus
    if len(ir.effects) >= 3:
        # Check if effects show sequential logic (if, elif, else)
        effect_text = " ".join(e.description for e in ir.effects)
        if ("if" in effect_text and "else" in effect_text) or "elif" in effect_text:
            score += 5

    # Python quirk awareness bonus (higher weight for CoT)
    quirk_phrases = [
        "bool before int",
        "isinstance quirk",
        "check bool first",
        "bool is subclass of int",
    ]

    ir_text = str(ir).lower()
    for phrase in quirk_phrases:
        if phrase in ir_text:
            score += 15  # Higher bonus for explicit quirk awareness

    # Comprehensive assertions bonus
    # Count edge case keywords in assertions
    edge_case_coverage = 0
    edge_keywords = ["empty", "none", "zero", "boundary", "invalid", "error"]

    for assertion in ir.assertions:
        for keyword in edge_keywords:
            if keyword in assertion.predicate.lower():
                edge_case_coverage += 1
                break

    score += edge_case_coverage * 5

    return score
```

---

## Part 4: Testing and Validation

### A/B Comparison Test

**Compare** three approaches on same test set:

```python
async def compare_translators(test_prompts: list[str]):
    """Compare vanilla, Best-of-N, and CoT+Best-of-N."""

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize({})

    results = {
        "vanilla": [],
        "best_of_n": [],
        "cot_hybrid": [],
    }

    # Initialize translators
    vanilla = XGrammarIRTranslator(provider)
    best_of_n = BestOfNIRTranslator(provider, n_candidates=3)
    cot_hybrid = CoTBestOfNTranslator(provider, n_candidates=3)

    for prompt in test_prompts:
        print(f"\n{'='*70}")
        print(f"Testing: {prompt[:60]}...")

        # Vanilla (baseline)
        ir_vanilla = await vanilla.translate(prompt)
        score_vanilla = score_ir_quality(ir_vanilla, prompt)
        results["vanilla"].append(score_vanilla)

        # Best-of-N
        ir_best_of_n = await best_of_n.translate(prompt)
        score_best_of_n = score_ir_quality(ir_best_of_n, prompt)
        results["best_of_n"].append(score_best_of_n)

        # CoT + Best-of-N
        ir_cot = await cot_hybrid.translate(prompt)
        score_cot = score_ir_quality(ir_cot, prompt)
        results["cot_hybrid"].append(score_cot)

        print(f"Scores: Vanilla={score_vanilla:.1f}, Best-of-N={score_best_of_n:.1f}, CoT+Best-of-N={score_cot:.1f}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Vanilla:       Avg={sum(results['vanilla'])/len(results['vanilla']):.1f}")
    print(f"Best-of-N:     Avg={sum(results['best_of_n'])/len(results['best_of_n']):.1f}")
    print(f"CoT+Best-of-N: Avg={sum(results['cot_hybrid'])/len(results['cot_hybrid']):.1f}")

    return results
```

**Expected Results** (Phase 3):
- Vanilla: 72% success
- Best-of-N (N=3): 82-86% success (+10-14%)
- CoT + Best-of-N: 88-94% success (+16-22%)

---

## Part 5: Cost and Performance Analysis

### Cost Breakdown

**Per IR Generation**:

| Component | Vanilla | Best-of-N (N=3) | CoT + Best-of-N (N=3) |
|-----------|---------|-----------------|----------------------|
| Input tokens | 800 | 800 × 3 = 2,400 | 1,500 × 3 = 4,500 |
| Output tokens | 600 | 600 × 3 = 1,800 | 600 × 3 = 1,800 |
| **Total tokens** | **1,400** | **4,200** | **6,300** |
| **Cost multiplier** | **1x** | **3x** | **4.5x** |

**Absolute costs** (Qwen3-30B on A100-80GB @ $4/hr):
- Vanilla: ~$0.0025/IR
- Best-of-N (N=3): ~$0.0075/IR (3x)
- CoT + Best-of-N (N=3): ~$0.0112/IR (4.5x)

**ROI Analysis** (assuming 100 IRs/month):
- Vanilla: $0.25/month → 72% success
- Best-of-N: $0.75/month → 82-86% success ($0.50 extra for +10-14%)
- CoT + Best-of-N: $1.12/month → 88-94% success ($0.87 extra for +16-22%)

**Verdict**: Extremely cost-effective for quality improvement ($0.87/month for +20% quality)

---

### Latency Breakdown

**Sequential CoT** (worst case):
- CoT reasoning: +0.5s per candidate
- Total: (2.5s + 0.5s) × 3 sequential = 9s

**Parallel CoT** (actual implementation):
- 3 candidates in parallel
- Latency: max(candidate_times) ≈ 2.5s + 0.5s = 3s
- **Latency multiplier**: 1.5-2x (not 3x!)

**Acceptable for offline processing** (<10s total)

---

## Part 6: Implementation Checklist

### Step 1: Implement CoT Prompt (2-3 hours)
- [ ] Write full `get_cot_prompt_for_ir_generation()` function
- [ ] Add step-by-step reasoning template
- [ ] Include Python quirks checklist
- [ ] Test on sample prompts (verify CoT output)

### Step 2: Create CoT + Best-of-N Translator (1-2 hours)
- [ ] Implement `CoTBestOfNTranslator` class
- [ ] Integrate with existing `BestOfNIRTranslator`
- [ ] Add CoT-aware scoring bonus
- [ ] Unit tests for translator

### Step 3: Integration Testing (2-3 hours)
- [ ] Test on Phase 2 (10 tests)
- [ ] Test on Phase 3 (18 tests)
- [ ] Compare vs vanilla and Best-of-N
- [ ] Measure cost and latency

### Step 4: Optimize if Needed (2-4 hours)
- [ ] Tune temperature for CoT (0.5 → 0.4 if too diverse)
- [ ] Adjust scoring weights
- [ ] Reduce N if 3 candidates too expensive (try N=2)
- [ ] Test on edge cases

**Total Effort**: 7-12 hours

---

## Part 7: Decision Criteria

### When to Use CoT + Best-of-N

**Use if**:
- ✅ Best-of-N alone achieves <88% success
- ✅ Need >90% success rate
- ✅ Can afford 4.5x cost (~$0.01/IR)
- ✅ Latency <10s is acceptable
- ✅ Production volume <10k IRs/month (otherwise fine-tune)

**Skip if**:
- ✅ Best-of-N achieves ≥88% success
- ✅ Budget is very tight (use Best-of-N only)
- ✅ Need <5s latency (use vanilla or Best-of-N)
- ✅ High volume (>10k/month) → fine-tuning more cost-effective

---

## Part 8: Monitoring and Iteration

### Metrics to Track

```python
def track_cot_effectiveness(results: list[dict]):
    """Track CoT-specific metrics."""

    metrics = {
        "cot_reasoning_quality": [],  # Judged by manual review
        "literal_string_accuracy": [],  # Detected in generated IR
        "python_quirk_handling": [],  # Detected in effects/assertions
        "edge_case_coverage": [],  # Count of edge cases in assertions
        "overall_success_rate": [],  # Phase 3 test pass rate
    }

    for result in results:
        ir = result['ir']

        # Manual quality review (1-10 scale)
        reasoning_quality = manual_review_cot_reasoning(ir)
        metrics["cot_reasoning_quality"].append(reasoning_quality)

        # Automated checks
        has_literals = detect_literal_markers(ir)
        metrics["literal_string_accuracy"].append(1 if has_literals else 0)

        handles_quirks = detect_python_quirks(ir)
        metrics["python_quirk_handling"].append(1 if handles_quirks else 0)

        edge_case_count = count_edge_cases(ir)
        metrics["edge_case_coverage"].append(edge_case_count)

        test_passed = run_phase3_test(ir, result['prompt'])
        metrics["overall_success_rate"].append(1 if test_passed else 0)

    # Summary
    print("CoT Effectiveness Metrics:")
    print(f"  Reasoning Quality:       {sum(metrics['cot_reasoning_quality']) / len(metrics['cot_reasoning_quality']):.1f}/10")
    print(f"  Literal String Accuracy: {sum(metrics['literal_string_accuracy']) / len(metrics['literal_string_accuracy']) * 100:.1f}%")
    print(f"  Python Quirk Handling:   {sum(metrics['python_quirk_handling']) / len(metrics['python_quirk_handling']) * 100:.1f}%")
    print(f"  Avg Edge Cases/IR:       {sum(metrics['edge_case_coverage']) / len(metrics['edge_case_coverage']):.1f}")
    print(f"  Overall Success Rate:    {sum(metrics['overall_success_rate']) / len(metrics['overall_success_rate']) * 100:.1f}%")
```

**Target Metrics**:
- CoT reasoning quality: ≥8/10
- Literal string accuracy: ≥90%
- Python quirk handling: ≥85%
- Avg edge cases/IR: ≥4
- Overall success rate: ≥90%

---

## Conclusion

**Status**: ✅ Ready to implement if Best-of-N alone doesn't reach 90%+

**Expected Timeline**: 1-2 days (7-12 hours implementation + testing)

**Expected Results**: 88-94% Phase 3 success (target: ≥90%)

**Cost**: 4.5x baseline (~$0.01/IR) - extremely cheap for 20% quality improvement

**Recommended Sequence**:
1. Test Best-of-N first (Week 1-2)
2. If Best-of-N achieves 85-89%: Implement CoT hybrid (Week 2-3)
3. If Best-of-N achieves ≥90%: Skip CoT (not needed)

**This plan is ready to execute as soon as Best-of-N results are known.**
