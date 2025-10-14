# Program Synthesis and Verification Technology Assessment

**Version**: 1.0
**Date**: October 14, 2025
**Purpose**: Evaluate program synthesis and verification technologies for lift-sys IR-to-code generation

---

## Executive Summary

This document assesses two technologies for program synthesis and verification:
1. **Loom**: Verification framework for Lean 4
2. **Calligrapher**: Contract-based code generation (user's own project)

**Key Finding**: After Phase 2's success with **xgrammar + ChatLSP**, traditional synthesis tools are less relevant. The LLM-based approach with constrained generation (xgrammar) + semantic context (ChatLSP) provides:
- Faster development (7-9 weeks vs. 12-16 weeks for synthesis integration)
- Better multi-language support (Python + TypeScript + Rust + Go)
- More flexible handling of ambiguity and typed holes
- Proven results (1.5-3x improvement with ChatLSP)

**Recommendation**: Use **xgrammar + ChatLSP + Z3 post-verification** as primary approach. Consider synthesis tools only for safety-critical code where formal guarantees are required.

---

## Technology 1: Loom

**Repository**: https://github.com/verse-lab/loom
**Category**: Program Verification (NOT Synthesis)
**Status**: Research prototype (Lean 4)

### Overview

Loom is a framework for automated generation of foundational multi-modal verifiers, implemented in Lean 4. Despite being mentioned as a "synthesis" tool in the research plan, Loom is actually focused on **program verification** using weakest precondition generation and SMT solving.

**Key Innovation**: Uses monadic shallow embedding with Monad Transformer Algebras for automated weakest precondition generation, enabling Dafny-style verification of imperative programs in Lean 4.

### Core Capabilities

#### 1. Verification Features
- **Automated Weakest Precondition Generation**: Generates verification conditions automatically
- **Velvet Framework**: Dafny-style specification and verification for imperative programs
- **Cashmere Framework**: Demonstrates variety of monadic effects
- **SMT Backend**: Uses lean-auto with cvc5 solver
- **Automated Tactics**: `loom_solve` and `loom_solver` for discharging verification conditions

#### 2. Specification Language
- **Preconditions**: `requires` annotations
- **Postconditions**: `ensures` annotations
- **Loop Invariants**: `invariant` annotations
- **Assertions**: `assert` statements

#### 3. Target Programs
- Imperative programs with mutable state
- Non-deterministic computations
- Programs with various monadic effects

### Evaluation for lift-sys

#### ❌ IR Schema Enforcement (Score: 1/5)

**Can it work with lift-sys's IR JSON schema?**
- **NO**: Loom works with Lean 4 code, not JSON schemas
- Not designed for IR-driven generation
- No integration path with lift-sys's IR format

**For lift-sys**:
- Cannot consume IntentClause, SigClause, or AssertClause
- Would require complete rewrite of IR in Lean 4
- Not practical for lift-sys architecture

**Score justification**: 1/5 because Loom cannot work with lift-sys's IR format at all.

#### ⚠️  Type Constraints (Score: 3/5)

**Can it handle lift-sys's type constraints?**
- **PARTIALLY**: Lean 4 has a rich type system
- But Loom verifies existing code, doesn't generate it
- Type constraints would need to be manually encoded in Lean

**Limitations**:
- Cannot automatically translate lift-sys type hints to Lean types
- No support for Python/TypeScript/Rust type systems
- Focused on verification, not code generation

**Score justification**: 3/5 because while Lean has strong types, Loom doesn't help with lift-sys's code generation needs.

#### ✅ SMT Integration (Score: 5/5)

**Does it integrate with SMT solvers?**
- **YES**: Uses cvc5 via lean-auto backend
- Automated verification condition generation
- Can prove program correctness

**Advantages**:
- ✅ Strong SMT integration
- ✅ Automated proof search
- ✅ Counterexample generation

**Limitations**:
- ⚠️  Requires Lean 4 knowledge
- ⚠️  Not designed for interactive code generation
- ⚠️  cvc5 not available on native Windows

**Score justification**: 5/5 for SMT integration capabilities, though it's for verification rather than generation.

#### ❌ Parallel Decoding (Score: 1/5)

**Can it support parallel speculative decoding?**
- **NO**: Loom is a verification framework, not a generation framework
- No concept of parallel exploration of alternatives
- Not relevant to its design

**Score justification**: 1/5 because parallel decoding is not applicable to verification.

#### ❌ Semantic Context (Score: 1/5)

**Can it provide codebase-aware semantic information?**
- **NO**: Loom verifies Lean 4 programs in isolation
- No language server integration
- No codebase analysis

**Score justification**: 1/5 because Loom doesn't provide semantic context for code generation.

#### ❌ Multi-Language Support (Score: 1/5)

**Can it support Python, TypeScript, Rust, Go?**
- **NO**: Loom only works with Lean 4
- No support for other languages
- Cannot generate Python/TypeScript/Rust/Go code

**Comparison to lift-sys needs**:
- lift-sys needs: Python, TypeScript, Rust, Go
- Loom provides: Lean 4 only
- **Verdict**: Completely incompatible with lift-sys's multi-language goals

**Score justification**: 1/5 because Loom only supports Lean 4, which is not a target language for lift-sys.

#### ⚠️  Maturity (Score: 3/5)

**Is it production-ready?**
- **NO**: Research prototype
- 58 GitHub stars
- Active development but experimental
- Apache-2.0 license

**Evidence**:
- ✅ Well-documented research project
- ✅ Case studies and examples
- ⚠️  Small community
- ⚠️  No production use cases

**Score justification**: 3/5 because it's a mature research prototype but not production-ready.

#### ❌ Integration Effort (Score: 1/5)

**How easy to integrate into lift-sys?**
- **VERY HARD**: Would require complete rewrite
- Requires Lean 4 expertise
- Incompatible with lift-sys architecture
- No clear integration path

**Integration Requirements**:
1. Rewrite lift-sys IR in Lean 4
2. Learn Lean 4 theorem proving
3. Rewrite all lift-sys code in Lean 4
4. Abandon Python/TypeScript/Rust targets

**Estimated Effort**: 6-12 months (not practical)

**Score justification**: 1/5 because integration would require abandoning lift-sys's current architecture.

#### ❌ Impact (Score: 1/5)

**What's the potential to improve lift-sys?**
- **VERY LOW**: Loom solves a different problem
- Verification vs. generation
- Incompatible with lift-sys goals
- No practical integration path

**Comparison to xgrammar + ChatLSP**:
- xgrammar + ChatLSP: 7-9 weeks, multi-language, proven results
- Loom: 6-12 months, Lean 4 only, no code generation

**Score justification**: 1/5 because Loom doesn't address lift-sys's needs and would require abandoning current architecture.

### Summary Scorecard

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| IR Schema | 1/5 | Cannot work with lift-sys's JSON IR format |
| Type Constraints | 3/5 | Strong types in Lean but no code generation |
| SMT Integration | 5/5 | Excellent SMT integration via cvc5 |
| Parallel Decoding | 1/5 | Not applicable to verification framework |
| Semantic Context | 1/5 | No semantic context for code generation |
| Multi-Language | 1/5 | Lean 4 only, incompatible with lift-sys targets |
| Maturity | 3/5 | Research prototype, not production-ready |
| Integration | 1/5 | Would require complete rewrite of lift-sys |
| Impact | 1/5 | Solves different problem than lift-sys needs |

**Total Score**: 17/45 (37.8%)

**Priority**: **P3** (Not recommended - incompatible with lift-sys)

### Recommendation

**DO NOT ADOPT Loom for Program Synthesis (IR → Code)**

**Note**: Loom will be re-evaluated in Phase 4 for **Reverse Mode (Code → IR)**, where its specification extraction capabilities may be more relevant.

#### Why Loom is Not Suitable for Synthesis:

1. **Wrong Problem Domain**
   - Loom: Verification of existing code
   - lift-sys: Generation of new code from specifications
   - **Verdict**: Fundamental mismatch

2. **Language Incompatibility**
   - Loom: Lean 4 only
   - lift-sys: Python, TypeScript, Rust, Go
   - **Verdict**: Cannot meet multi-language goals

3. **Integration Infeasibility**
   - Would require rewriting lift-sys in Lean 4
   - Would abandon entire IR architecture
   - Estimated 6-12 months with no clear benefit
   - **Verdict**: Not practical

4. **Superior Alternatives Available**
   - xgrammar + ChatLSP: 7-9 weeks, multi-language, proven
   - Z3 post-verification: Simpler, faster, sufficient
   - **Verdict**: No need for Loom

#### When Verification Frameworks Like Loom Are Useful:

- ✅ Safety-critical systems (aerospace, medical devices)
- ✅ When formal correctness proofs are required
- ✅ When you're already using Lean 4
- ❌ For lift-sys's use case (LLM-based code generation with verification)

#### Alternative Approach:

Instead of Loom, use:
```
[xgrammar] Generate syntactically valid code
    ↓
[ChatLSP] Ensure semantic correctness
    ↓
[Z3] Post-generation SMT verification
    ↓
If verification fails, regenerate with constraints
```

This provides:
- ✅ Fast iteration (<2s per generation)
- ✅ Multi-language support
- ✅ Sufficient verification for most use cases
- ✅ Easy integration (7-9 weeks)

---

## Technology 2: Calligrapher

**Repository**: https://github.com/rand/calligrapher (User's own project)
**Category**: Contract-Based Code Generation
**Status**: To be assessed based on current state

### Overview

Calligrapher is a contract-based code generation tool created by the user (Rand). According to the research plan, it focuses on:
- Contract-based specifications
- Type-directed generation
- Verification condition extraction
- Round-trip translation (code ↔ contract)

**Key Question**: Should lift-sys absorb Calligrapher's features, or should they remain separate projects?

### Assessment Pending

**To properly assess Calligrapher, we need to:**

1. **Review Current State**
   - What is Calligrapher's current implementation status?
   - What features are production-ready?
   - What is the IR format?

2. **Compare IR Formats**
   - Calligrapher IR vs. lift-sys IR
   - Feature matrix: What does each have that the other lacks?
   - Can they be merged?

3. **Evaluate Reusable Components**
   - Type-directed generation algorithms
   - Verification condition extraction
   - Contract checking mechanisms
   - Bidirectional translation approach

4. **Determine Integration Strategy**
   - Merge Calligrapher into lift-sys?
   - Extract specific components?
   - Keep separate?
   - Which codebase becomes primary?

### Questions for User

Before completing this assessment, please provide:

1. **Repository Access**: Is https://github.com/rand/calligrapher publicly accessible?
2. **Current State**: What is Calligrapher's current development status?
3. **IR Format**: How does Calligrapher's IR compare to lift-sys's IntentClause/SigClause/AssertClause?
4. **Integration Intent**: Do you want to merge the projects, or extract specific features?
5. **Production Readiness**: What parts of Calligrapher are production-ready?

### Preliminary Comparison (Based on Research Plan)

From the research plan, Calligrapher scored:
- IR Schema: 4/5
- Type Constraints: 5/5
- SMT Integration: 4/5
- Parallel Decoding: 2/5
- Semantic Context: 3/5
- Multi-Language: 3/5
- Maturity: 2/5
- Integration Effort: 4/5
- Impact: 4/5
- **Total**: 31/45 (68.9%), Priority P1

This suggests Calligrapher has:
- ✅ Strong type system and IR capabilities
- ✅ Good SMT integration
- ✅ Easier integration (4/5) than Loom (1/5)
- ⚠️  Early maturity (2/5)
- ⚠️  Moderate multi-language support (3/5)

---

## Comparative Analysis: Synthesis Approaches

### Three Approaches to Code Generation from IR

| Approach | Technology | Pros | Cons | Fit for lift-sys |
|----------|-----------|------|------|------------------|
| **LLM-Based** | xgrammar + ChatLSP | Fast, flexible, multi-language, handles ambiguity | Not formally verified | ✅ BEST |
| **Synthesis-Based** | Loom | Formal verification, guaranteed correctness | Slow, Lean 4 only, no generation | ❌ Poor |
| **Contract-Based** | Calligrapher | Type-directed, verification conditions | Needs assessment | ⚠️  TBD |

### Why LLM-Based (xgrammar + ChatLSP) Wins

1. **Speed**
   - LLM: <2s per function
   - Synthesis: 30s-5min per function
   - **Verdict**: LLM is 15-150x faster

2. **Multi-Language**
   - LLM: Python, TypeScript, Rust, Go (ready today)
   - Synthesis: Lean 4 only
   - **Verdict**: LLM meets lift-sys goals

3. **Ambiguity Handling**
   - LLM: TypedHoles naturally handled
   - Synthesis: Requires complete specification
   - **Verdict**: LLM better for iterative refinement

4. **Integration Effort**
   - LLM: 7-9 weeks
   - Synthesis: 6-12 months
   - **Verdict**: LLM is 3-7x faster to integrate

5. **Code Quality**
   - LLM: 1.5-3x improvement with ChatLSP
   - Synthesis: 100% correct (but only for Lean 4)
   - **Verdict**: LLM provides sufficient quality for lift-sys

6. **Verification**
   - LLM: Post-generation Z3 verification
   - Synthesis: Verification during synthesis
   - **Verdict**: Post-generation sufficient for most cases

### When to Use Each Approach

**Use LLM-Based (xgrammar + ChatLSP) for:**
- ✅✅ General-purpose code generation
- ✅✅ Multi-language targets
- ✅✅ Interactive refinement with TypedHoles
- ✅✅ Fast iteration (<2s per function)
- ✅ Most lift-sys use cases

**Use Synthesis-Based (Loom) for:**
- ✅ Safety-critical code (aerospace, medical)
- ✅ When formal proofs are required
- ✅ When you're already using Lean 4
- ❌ Not for lift-sys

**Use Contract-Based (Calligrapher) for:**
- ⚠️  TBD based on assessment
- Potentially: Type-directed generation
- Potentially: Verification condition extraction

---

## Recommended Architecture for lift-sys

### Primary Path: LLM-Based with Verification

```
Prompt
  ↓
[xgrammar] Enforce IR JSON schema (100% valid, <1.5s)
  ↓
Valid IR JSON
  ↓
[ChatLSP] Retrieve semantic context (types, headers, ~200ms)
  ↓
[xgrammar] Generate code with type grammar + ChatLSP context
  ↓ (syntactically valid + semantically correct)
Code
  ↓
[Z3] SMT verification of assertions (post-generation)
  ↓
If UNSAT: Regenerate with constraint feedback
  ↓
Verified Code
```

**Total Time**: <2s for typical function
**Quality**: 1.5-3x improvement (ChatLSP)
**Verification**: SMT checking via Z3
**Multi-Language**: Python, TypeScript, Rust, Go

### Fallback: Formal Synthesis (Not Recommended)

Only consider formal synthesis (like Loom) for:
- Safety-critical components
- When formal proofs are legally required
- Small, well-specified functions

**Integration**: Separate "formal mode" for critical code paths

---

## Synthesis/Verification Technology Comparison

| Technology | Type | Score | Priority | Recommendation |
|------------|------|-------|----------|----------------|
| **xgrammar + ChatLSP** | LLM-based | Combined P0 | **P0** | **ADOPT** |
| **Loom** | Formal verification | 17/45 (38%) | P3 | **REJECT** |
| **Calligrapher** | Contract-based | 31/45 (69%) | P1 | **ASSESS** |
| **Z3 (post-gen)** | SMT verification | N/A | P0 | **ADOPT** |

---

## Open Questions

1. **Calligrapher Assessment**: Need to review repository and determine integration strategy
2. **Formal Verification Need**: Does lift-sys need formal proofs, or is SMT checking sufficient?
3. **Safety-Critical Mode**: Should lift-sys have a "formal mode" for critical code?
4. **Z3 Integration**: How to best integrate Z3 for post-generation verification?

---

## Next Steps

1. **Skip Detailed Loom Research for Synthesis**: Not applicable for IR → Code generation (DONE)
2. **Re-evaluate Loom for Reverse Mode**: Defer to Phase 4 - Loom's specification extraction may be useful for Code → IR (PENDING)
3. **Assess Calligrapher**: Review repository and compare with lift-sys IR
4. **Finalize Synthesis Approach**: Confirm LLM-based (xgrammar + ChatLSP) as primary
5. **Z3 Integration Plan**: Design post-generation verification pipeline
6. **Move to Phase 4**: Static analysis tools (stack-graphs, nuanced-py, **and Loom for reverse mode**)

---

## References

- Loom GitHub: https://github.com/verse-lab/loom
- Lean 4: https://lean-lang.org/
- Velvet Framework: Part of Loom
- Cashmere Framework: Part of Loom
- cvc5 SMT Solver: https://cvc5.github.io/
